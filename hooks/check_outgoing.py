#!/usr/bin/env python3
"""PreToolUse hook: catch AI-writing tells before text leaves the machine.

What it reads:
  Bash        git commit / git tag messages; gh pr|issue create, edit, comment, review,
              close, merge; gh release create|edit; gh api calls that send a body or title.
              Inline flags, heredocs and --body-file / -F files all count.
  Write/Edit  .md .mdx .markdown .txt .rst .adoc files, only the lines being added.
              Skips ~/.claude (memory, plans) and Claude's scratch folders.
  MCP tools   tools whose name says they send or create something (send, reply,
              comment, post, draft, message, create, publish, share).

It denies the tool call when the text has errors (em dashes, chatbot phrases,
AI attribution) and lists warnings in the same message so one rewrite fixes both.

HUMAN_WRITING_HOOK=off turns it off; HUMAN_WRITING_HOOK=strict blocks on warnings too.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LINTER_DIR = os.path.join(os.path.dirname(HERE), "skills", "human-writing", "scripts")

PROSE_EXT = {".md", ".mdx", ".markdown", ".txt", ".rst", ".adoc"}
MAX_FILE = 1_000_000

PUBLISH = re.compile(
    r"\bgit\b(?:\s+-[cC]\s+\S+)*\s+(?:commit|tag)\b"
    r"|\bgh\s+(?:pr|issue)\s+(?:create|new|edit|comment|review|close|merge|reopen)\b"
    r"|\bgh\s+release\s+(?:create|new|edit)\b"
    r"|\bgh\s+api\b"
)
HEREDOC = re.compile(
    r"<<(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2[^\n]*\n(.*?)\n[ \t]*\3[ \t]*(?=\n|$)",
    re.S,
)
API_TEXT_KEYS = {"body", "title", "message", "description", "notes", "text", "content", "comment"}
MCP_SENDS = re.compile(r"send|reply|comment|post|draft|message|create|publish|share", re.I)


def read_file(path: str, cwd: str) -> str:
    if not path or path == "-":
        return ""
    full = path if os.path.isabs(path) else os.path.join(cwd, os.path.expanduser(path))
    try:
        if os.path.getsize(full) > MAX_FILE:
            return ""
        with open(full, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def split_segments(tokens):
    seg = []
    for t in tokens:
        if t in {"&&", "||", ";", "|", "&", "(", ")", ";;", "|&"}:
            if seg:
                yield seg
            seg = []
        else:
            seg.append(t)
    if seg:
        yield seg


def texts_from_bash(command: str, cwd: str):
    if not PUBLISH.search(command):
        return []
    bodies = {}

    def stash(m):
        key = f"__HEREDOC_{len(bodies)}__"
        bodies[key] = m.group(4)
        return f" {key} "

    stripped = HEREDOC.sub(stash, command)
    import shlex

    try:
        lex = shlex.shlex(stripped, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        # Unbalanced quotes: fall back to every heredoc and quoted string.
        quoted = [a or b for a, b in re.findall(r'"([^"]{8,})"|\'([^\']{8,})\'', stripped)]
        return [t for t in list(bodies.values()) + quoted if t.strip()]

    out = []

    def add_value(v: str):
        hits = [k for k in bodies if k in v]
        if hits:
            out.extend(bodies[k] for k in hits)
        elif v and not v.startswith("$"):
            out.append(v)

    for seg in split_segments(tokens):
        # Drop leading VAR=value assignments and wrappers like `env`, `command`.
        while seg and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", seg[0]) or seg[0] in {"env", "command", "builtin", "time"}):
            seg = seg[1:]
        if len(seg) < 2:
            continue
        prog = os.path.basename(seg[0])
        rest = seg[1:]
        if prog == "git":
            # skip global options such as -C dir and -c key=value
            while rest and rest[0] in {"-C", "-c"} and len(rest) > 1:
                rest = rest[2:]
            if not rest or rest[0] not in {"commit", "tag"}:
                continue
            kind = "git"
        elif prog == "gh":
            if len(rest) < 2:
                continue
            if rest[0] in {"pr", "issue", "release"}:
                kind = "gh"
            elif rest[0] == "api":
                kind = "api"
            else:
                continue
        else:
            continue

        i = 0
        while i < len(rest):
            t = rest[i]
            nxt = rest[i + 1] if i + 1 < len(rest) else ""
            if kind == "git":
                if t in {"-m", "--message"} or re.fullmatch(r"-[a-zA-Z]*m", t):
                    add_value(nxt); i += 2; continue
                if t.startswith("--message="):
                    add_value(t.split("=", 1)[1])
                elif t.startswith("-m") and len(t) > 2 and not t.startswith("--"):
                    add_value(t[2:])
                elif t in {"-F", "--file"}:
                    out.append(read_file(nxt, cwd)); i += 2; continue
                elif t.startswith("--file="):
                    out.append(read_file(t.split("=", 1)[1], cwd))
            elif kind == "gh":
                if t in {"-t", "--title", "-b", "--body", "-n", "--notes", "-c", "--comment", "--subject"}:
                    add_value(nxt); i += 2; continue
                if re.match(r"^--(title|body|notes|comment|subject)=", t):
                    add_value(t.split("=", 1)[1])
                elif t in {"-F", "--body-file", "--notes-file"}:
                    if nxt == "-":
                        out.extend(bodies.values())
                    else:
                        out.append(read_file(nxt, cwd))
                    i += 2; continue
                elif re.match(r"^--(body-file|notes-file)=", t):
                    out.append(read_file(t.split("=", 1)[1], cwd))
            elif kind == "api":
                if t in {"-f", "-F", "--field", "--raw-field"} and "=" in nxt:
                    key, val = nxt.split("=", 1)
                    if key.split("[")[0].lower() in API_TEXT_KEYS:
                        if t in {"-F", "--field"} and val.startswith("@"):
                            out.append(read_file(val[1:], cwd))
                        else:
                            add_value(val)
                    i += 2; continue
                if t == "--input":
                    raw = "\n".join(bodies.values()) if nxt == "-" else read_file(nxt, cwd)
                    out.extend(json_texts(raw))
                    i += 2; continue
            i += 1
    return [t for t in out if t and t.strip()]


def json_texts(raw: str):
    try:
        data = json.loads(raw)
    except ValueError:
        return [raw] if raw else []
    found = []

    def walk(x, key=""):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, k)
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
        elif isinstance(x, str) and key.lower() in API_TEXT_KEYS:
            found.append(x)

    walk(data)
    return found


def skipped_path(path: str) -> bool:
    p = os.path.realpath(os.path.expanduser(path))
    cfg = os.path.realpath(os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude"))
    if p == cfg or p.startswith(cfg + os.sep):
        return True
    if re.match(r"^/tmp/claude-\d+/", p) or f"{os.sep}scratchpad{os.sep}" in p:
        return True
    return f"{os.sep}node_modules{os.sep}" in p


def added_lines(new: str, old: str) -> str:
    before = {l.strip() for l in old.splitlines() if l.strip()}
    return "\n".join(l for l in new.splitlines() if l.strip() and l.strip() not in before)


def texts_from_edit(tool: str, ti: dict):
    path = ti.get("file_path") or ti.get("notebook_path") or ""
    if os.path.splitext(path)[1].lower() not in PROSE_EXT or skipped_path(path):
        return []
    if tool == "Write":
        old = read_file(path, "/")
        return [added_lines(ti.get("content", ""), old)]
    if tool == "Edit":
        return [added_lines(ti.get("new_string", ""), ti.get("old_string", ""))]
    if tool == "MultiEdit":
        return [added_lines(e.get("new_string", ""), e.get("old_string", "")) for e in ti.get("edits", [])]
    return []


def texts_from_mcp(tool: str, ti: dict):
    action = tool.split("__")[-1]
    if not MCP_SENDS.search(action):
        return []
    found = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str) and len(x.split()) >= 5 and not x.lstrip().startswith(("{", "[")):
            found.append(re.sub(r"<[^>]+>", " ", x) if re.search(r"</?[a-z][^>]*>", x) else x)

    walk(ti)
    return found


def main() -> int:
    mode = (os.environ.get("HUMAN_WRITING_HOOK") or "").lower()
    if mode in {"off", "0", "false", "disabled"}:
        return 0
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    tool = data.get("tool_name") or ""
    ti = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()

    if tool == "Bash":
        texts = texts_from_bash(ti.get("command", ""), cwd)
        rhythm = False
    elif tool in {"Write", "Edit", "MultiEdit"}:
        texts = texts_from_edit(tool, ti)
        rhythm = False
    elif tool.startswith("mcp__"):
        texts = texts_from_mcp(tool, ti)
        rhythm = False
    else:
        return 0
    text = "\n\n".join(t for t in texts if t and t.strip())
    if not text.strip():
        return 0

    # Imported only now: most tool calls have nothing to check, and loading the
    # linter's patterns is most of this hook's run time.
    sys.path.insert(0, LINTER_DIR)
    from lint_writing import format_findings, lint

    rep = lint(text, rhythm=rhythm)
    blocking = rep.errors + (rep.warnings if mode == "strict" else [])
    if not blocking:
        return 0

    listed = format_findings(rep.errors + rep.warnings, limit=12)
    extra = len(rep.findings) - len(listed)
    reason = (
        "human-writing check: this text reads as AI-written, so the call was stopped.\n"
        + "\n".join("  " + l for l in listed)
        + (f"\n  ...and {extra} more" if extra > 0 else "")
        + "\nRewrite the flagged sentences and fix the warnings while you're there, then run it again. "
        "Recast a sentence rather than trading its dash for a comma, colon or semicolon: split it in two, "
        "or reword it (\"Fix flaky test by waiting for the port\"). Text in backticks or short double "
        "quotes is not checked, so quote real error messages and UI strings that way."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never break the user's tool call because of a bug here
        print(f"human-writing hook error (ignored): {exc}", file=sys.stderr)
        sys.exit(0)
