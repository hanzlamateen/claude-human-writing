"""Run with: python3 -m unittest discover -s tests -v   (from the repo root)"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "check_outgoing.py")
SESSION = os.path.join(ROOT, "hooks", "session_start.py")
sys.path.insert(0, os.path.join(ROOT, "skills", "human-writing", "scripts"))
from lint_writing import lint  # noqa: E402

EM = chr(0x2014)  # kept out of the source on purpose
EN = chr(0x2013)


def run_hook(payload, env=None):
    e = dict(os.environ)
    e.pop("HUMAN_WRITING_HOOK", None)
    e.update(env or {})
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True, env=e)
    if not p.stdout.strip():
        return "allow", ""
    out = json.loads(p.stdout)["hookSpecificOutput"]
    return out["permissionDecision"], out["permissionDecisionReason"]


def bash(cmd, cwd="/tmp"):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd}


class LintTests(unittest.TestCase):
    def rules(self, text, **kw):
        return {f.rule for f in lint(text, **kw).findings}

    def test_em_dash_is_error(self):
        rep = lint(f"The build broke {EM} again.")
        self.assertEqual([f.rule for f in rep.errors], ["em-dash"])

    def test_dashes_in_code_and_tables_are_ignored(self):
        text = f"Run `a {EM} b` here.\n\n```\nx {EM} y\n```\n\n| a | {EM} |\n|---|---|\n"
        self.assertEqual(lint(text).errors, [])

    def test_number_range_en_dash_is_fine(self):
        self.assertEqual(lint(f"Pages 3{EN}5 cover it.").errors, [])
        self.assertIn("spaced-en-dash", self.rules(f"It works {EN} mostly."))

    def test_chatbot_phrases(self):
        self.assertIn("chatbot-phrase", self.rules("Fixed it. I hope this helps!"))
        self.assertIn("chatbot-phrase", self.rules("You're absolutely right, the test was wrong."))

    def test_contrast_reframe(self):
        self.assertIn("contrast-reframe", self.rules("This is not just a fix, but a new way to ship."))
        self.assertIn("contrast-reframe", self.rules("It's not a bug, it's a missing check."))
        self.assertIn("contrast-reframe", self.rules("This isn't about speed. It's about trust."))

    def test_colon_reveal_skips_plain_labels(self):
        self.assertIn("colon-reveal", self.rules("The catch: it only runs on Linux."))
        self.assertIn("colon-reveal", self.rules("Tried three things. The fix: a lock."))
        self.assertNotIn("colon-reveal", self.rules("Result: 495 passed, 1 skipped."))

    def test_stock_words_are_warnings_only(self):
        rep = lint("We leverage a robust, seamless pipeline.")
        self.assertEqual(rep.errors, [])
        self.assertIn("stock-word", {f.rule for f in rep.warnings})

    def test_delve_is_error(self):
        self.assertIn("stock-phrase", {f.rule for f in lint("Let's delve into the logs.").errors})

    def test_default_pr_template(self):
        self.assertIn("default-pr-template", self.rules("## Summary\n- a\n\n## Test plan\n- [ ] b\n"))

    def test_uniform_sentences(self):
        same = " ".join(["The service reads the config file and starts the worker pool."] * 9)
        self.assertIn("uniform-sentences", self.rules(same))

    def test_claude_specific_patterns(self):
        self.assertIn("claude-intensifiers", self.rules("It actually works now. Honestly, the old path was genuinely broken."))
        self.assertNotIn("claude-intensifiers", self.rules("It actually works now, after the second patch landed on main."))
        self.assertIn("claude-opener", self.rules("Here's what changed in the build."))
        self.assertIn("contrast-reframe", self.rules("This wasn't a bug. It was a missing check."))
        self.assertIn("signpost", self.rules("Honest caveat: I only tested Linux."))
        self.assertIn("signpost", self.rules("That log line is the smoking gun."))
        self.assertIn("arrows", self.rules("Click Save " + chr(0x2192) + " the dialog closes."))
        self.assertIn("stock-phrase", self.rules("Tidied the module while preserving behaviour."))
        self.assertIn("stock-phrase", self.rules("The docs are now clear and concise."))
        self.assertIn("stock-phrase", self.rules("Our test user is Sarah Chen."))
        self.assertIn("ing-tail", self.rules("The cache now persists, making it easier to debug."))

    def test_heading_checks(self):
        self.assertIn("title-case-heading", self.rules("## How We Fixed The Pairing Flow\n\nText."))
        self.assertNotIn("title-case-heading", self.rules("## How we fixed the pairing flow\n\nText."))
        self.assertIn("title-heading", self.rules("# Pairing fix\n\nShort body."))
        self.assertIn("changelog-heading", self.rules("## What changed in v3\n\nStuff."))
        self.assertNotIn("changelog-heading", self.rules("## What changed\n\nStuff."))

    def test_varied_text_is_clean(self):
        text = (
            "Sign-in broke for new users on Tuesday. Nobody could get past the code screen, because the "
            "Portal rejected every pairing code older than ten seconds and the email took about thirty to arrive. "
            "I raised the limit to five minutes.\n\nStill not sure why staging didn't show it. Probably the faster mail relay there."
        )
        rep = lint(text)
        self.assertEqual(rep.errors, [])
        self.assertEqual(rep.warnings, [])


class HookTests(unittest.TestCase):
    def test_git_commit_with_em_dash_is_denied(self):
        decision, reason = run_hook(bash(f'git commit -m "Fix the build {EM} it was broken"'))
        self.assertEqual(decision, "deny")
        self.assertIn("em-dash", reason)

    def test_clean_commit_is_allowed(self):
        self.assertEqual(run_hook(bash('git add -A && git commit -m "Fix the build: pin otplib to 12"'))[0], "allow")

    def test_heredoc_commit(self):
        cmd = 'git commit -m "$(cat <<\'EOF\'\nAdd the thing\n\nThis delves into the cache.\nEOF\n)"'
        self.assertEqual(run_hook(bash(cmd))[0], "deny")

    def test_gh_pr_body_and_title(self):
        self.assertEqual(run_hook(bash('gh pr create --title "Fix" --body "I hope this helps"'))[0], "deny")
        self.assertEqual(run_hook(bash(f'gh pr create --title "Fix {EM} sign-in" --body "Plain."'))[0], "deny")
        self.assertEqual(run_hook(bash(f'gh pr merge 12 --squash --subject "a {EM} b"'))[0], "deny")

    def test_body_file(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "body.md"), "w") as fh:
                fh.write(f"Two fixes {EM} both small.\n")
            self.assertEqual(run_hook(bash("gh pr create --title Fix --body-file body.md", cwd=d))[0], "deny")
            self.assertEqual(run_hook(bash("git commit -F body.md", cwd=d))[0], "deny")

    def test_body_file_from_heredoc(self):
        cmd = f"gh issue create --title Bug --body-file - <<'EOF'\nIt fails {EM} every time.\nEOF"
        self.assertEqual(run_hook(bash(cmd))[0], "deny")

    def test_gh_api_comment(self):
        cmd = f'gh api repos/o/r/pulls/1/comments/2/replies -f body="Great question {EM} yes"'
        self.assertEqual(run_hook(bash(cmd))[0], "deny")
        self.assertEqual(run_hook(bash('gh api repos/o/r/pulls/1 --jq .title'))[0], "allow")

    def test_git_global_options_and_combined_flags(self):
        self.assertEqual(run_hook(bash(f'git -C /repo commit -am "msg {EM} x"'))[0], "deny")
        self.assertEqual(run_hook(bash("git commit --amend --no-edit"))[0], "allow")

    def test_non_publishing_commands_are_ignored(self):
        self.assertEqual(run_hook(bash(f'grep -rn "{EM}" docs/'))[0], "allow")
        self.assertEqual(run_hook(bash(f'echo "{EM} hi" && ls'))[0], "allow")

    def test_backticked_text_is_not_checked(self):
        cmd = 'git commit -m "Show the `Retry ' + EM + ' 3 left` label again"'
        self.assertEqual(run_hook(bash(cmd))[0], "allow")

    def test_table_placeholder_cell(self):
        body = f"| Case | Before |\\n|---|---|\\n| pinch | {EM} |"
        self.assertEqual(run_hook(bash(f'gh pr create --title Fix --body "{body}"'))[0], "allow")

    def test_write_markdown_only_new_lines(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "README.md")
            new = {"tool_name": "Write", "tool_input": {"file_path": path, "content": f"# Tool\n\nFast {EM} and small.\n"}}
            self.assertEqual(run_hook(new)[0], "deny")
            with open(path, "w") as fh:
                fh.write(f"# Tool\n\nOld line {EM} by a teammate.\n")
            keep = {"tool_name": "Write", "tool_input": {"file_path": path, "content": f"# Tool\n\nOld line {EM} by a teammate.\n\nNew plain line.\n"}}
            self.assertEqual(run_hook(keep)[0], "allow")

    def test_edit_markdown_context_lines(self):
        edit = {"tool_name": "Edit", "tool_input": {
            "file_path": "/tmp/x/docs/guide.md",
            "old_string": f"Old {EM} line\nsecond",
            "new_string": f"Old {EM} line\nsecond, now fixed"}}
        self.assertEqual(run_hook(edit)[0], "allow")
        edit["tool_input"]["new_string"] = f"Old {EM} line\nsecond {EM} now fixed"
        self.assertEqual(run_hook(edit)[0], "deny")

    def test_skipped_paths_and_code_files(self):
        mem = os.path.expanduser("~/.claude/projects/x/memory/note.md")
        self.assertEqual(run_hook({"tool_name": "Write", "tool_input": {"file_path": mem, "content": f"a {EM} b"}})[0], "allow")
        self.assertEqual(run_hook({"tool_name": "Write", "tool_input": {"file_path": "/tmp/x/a.py", "content": f"# a {EM} b"}})[0], "allow")

    def test_mcp_send_tools(self):
        send = {"tool_name": "mcp__claude_ai_Gmail__send_message",
                "tool_input": {"to": "a@b.c", "body": f"Thanks for the notes {EM} all fixed now."}}
        self.assertEqual(run_hook(send)[0], "deny")
        query = {"tool_name": "mcp__cf__d1_database_query", "tool_input": {"sql": f"select 'a {EM} b' as x from t where y = 1"}}
        self.assertEqual(run_hook(query)[0], "allow")

    def test_off_and_strict_modes(self):
        cmd = bash(f'git commit -m "a {EM} b"')
        self.assertEqual(run_hook(cmd, {"HUMAN_WRITING_HOOK": "off"})[0], "allow")
        warn_only = bash('git commit -m "We leverage the new cache"')
        self.assertEqual(run_hook(warn_only)[0], "allow")
        self.assertEqual(run_hook(warn_only, {"HUMAN_WRITING_HOOK": "strict"})[0], "deny")

    def test_garbage_input_never_blocks(self):
        p = subprocess.run([sys.executable, HOOK], input="not json", capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout), (0, ""))


class SessionStartTests(unittest.TestCase):
    def run_start(self, claude_md):
        with tempfile.TemporaryDirectory() as cfg:
            if claude_md is not None:
                with open(os.path.join(cfg, "CLAUDE.md"), "w") as fh:
                    fh.write(claude_md)
            env = dict(os.environ, CLAUDE_CONFIG_DIR=cfg, CLAUDE_PLUGIN_ROOT=ROOT)
            return subprocess.run([sys.executable, SESSION], capture_output=True, text=True, env=env).stdout

    def test_injects_rules_without_import(self):
        out = self.run_start("## Git\n- something\n")
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("em dash", ctx.lower())
        self.assertLess(len(ctx), 10000)

    def test_silent_when_claude_md_imports_rules(self):
        self.assertEqual(self.run_start("## Writing\n@~/.claude/skills/human-writing/skills/human-writing/WRITING.md\n"), "")


if __name__ == "__main__":
    unittest.main()
