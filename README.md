# human-writing

Rules, a skill and a hook that keep Claude's habits out of what we write with it: commit messages, PRs, issues, review replies, docs, status updates, emails and posts.

The rules start from the StoryScope study (arXiv 2604.03136), which compared 61,608 human and AI stories and found Claude the easiest model to recognise: even intensity, one uniform voice, conventional structure, explained morals and quiet wrap-up endings. Its other finding matters more. Stripping surface tics like clichés didn't stop detection, so the rules cover the shape of a text as well as its words. The word-level tells come from other measurements, with Claude's own listed first: em dashes (about 32 per 10,000 words against 5 for people), "actually" and "genuinely", "Here's" openers, arrows in prose, title headings. Most published lists were built on ChatGPT output and miss Claude. Details and sources are in [skills/human-writing/references](skills/human-writing/references).

## What's in it

- `skills/human-writing/WRITING.md` holds the rules. Every Claude Code session loads them.
- `skills/human-writing/SKILL.md` is the skill: a two-pass revision process and before-and-after examples. Claude picks it up when it drafts something for other people, or run it as `/human-writing:human-writing`.
- `skills/human-writing/scripts/lint_writing.py` is the linter. Plain Python 3, no dependencies.
- `hooks/` holds the hook. Before Claude runs `git commit`, `gh pr create` and friends, writes a markdown file, or sends something through an MCP tool, the hook lints the text. When it finds an error it stops the call and tells Claude what to rewrite.
- `claude-ai/personal-preferences.md` is a short version of the rules for the claude.ai profile.
- `dist/` has upload zips for claude.ai.

## Set it up

### Claude Code on a machine

```sh
git clone https://github.com/hanzlamateen/claude-human-writing ~/.claude/skills/human-writing
~/.claude/skills/human-writing/install.sh
```

Claude Code loads any plugin folder under `~/.claude/skills/` by itself (it shows up as `human-writing@skills-dir`), straight from the checkout. `install.sh` adds one import to `~/.claude/CLAUDE.md` so the rules reach subagents too. If you clone somewhere else, `install.sh` links that checkout into `~/.claude/skills/`. Restart Claude Code afterwards.

Switching Claude accounts on the same machine changes nothing here: the plugin and `CLAUDE.md` belong to the machine, not the account.

### A claude.ai account

Do this once per account. It covers chat on the web, desktop and phone, and Claude Code on any machine signed in to that account. In Claude Code the account copy is synced in as `human-writing@synced`, hooks included (Claude Code 2.1.273 or newer).

1. Go to Customize > Plugins > Add > Add marketplace, enter `hanzlamateen/claude-human-writing`, then add the `human-writing` plugin. The repo is public, so there's no GitHub account to connect. Add > Upload plugin with `dist/human-writing-plugin.zip` works too, but then updates are manual.
2. Paste `claude-ai/personal-preferences.md` into Settings > Profile, under personal preferences. Chat loads the skill only when a request matches it, and the preferences cover everything else.

Where a machine has both the checkout and the synced copy, Claude Code loads the checkout and skips the synced one.

### Claude Code without cloning

```sh
claude plugin marketplace add hanzlamateen/claude-human-writing
claude plugin install human-writing@human-writing
```

That gives you the hook and the skill. The plugin's SessionStart hook loads the rules into each session, since there's no `CLAUDE.md` import in this setup. Subagents don't see them; the hook still checks their output.

## Update

`git -C ~/.claude/skills/human-writing pull`, then restart Claude Code. On claude.ai, open the plugin and choose Check for updates, or turn on Sync automatically. After you edit the skill, run `python3 tools/build_dist.py` so the zips match.

## Turn it down or off

- `HUMAN_WRITING_HOOK=off` in the environment disables the hook. `HUMAN_WRITING_HOOK=strict` makes warnings block too.
- `claude plugin disable human-writing@skills-dir` turns off the whole plugin on a machine.
- `./install.sh --uninstall` removes the `CLAUDE.md` import and the link.

## What the hook checks

Errors stop the tool call: em dashes (and spaced en dashes or ` -- ` used as one), chatbot phrases such as "I hope this helps" or "You're absolutely right", "delve" and a few other near-certain tells, and AI attribution lines. Warnings ride along in the same message so Claude can fix them in the same pass, but they don't block: contrast reframes, stock words, colon drumrolls, "-ing" tails, hedge stacks, bold-label lists, the stock "Summary / Test plan" PR layout.

It looks at the text in `git commit` and `git tag` messages, at titles and bodies of `gh pr`, `gh issue` and `gh release` commands (`--body-file` and heredocs too) and at `gh api` calls that send a body. For markdown and text files it checks the lines a Write or Edit adds, not the ones already there, so a teammate's old em dash never forces a rewrite. MCP tools whose names say they send or create something are covered too.

It skips anything in backticks or code fences, short quoted strings (quote real UI text and error messages that way), files under `~/.claude` and Claude's scratch folders, and non-prose files.

## Lint a draft yourself

```sh
python3 skills/human-writing/scripts/lint_writing.py draft.md
pbpaste | python3 skills/human-writing/scripts/lint_writing.py -      # or from the clipboard
```

Run it over `WRITING.md` and it will complain, because the rules quote the phrases they ban.

## Tests

```sh
python3 -m unittest discover -s tests -v
```
