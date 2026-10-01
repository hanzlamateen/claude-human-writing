#!/usr/bin/env bash
# Set up human-writing for Claude Code on this machine.
#
#   ./install.sh               make Claude Code load this checkout as a plugin, and import the
#                              writing rules from ~/.claude/CLAUDE.md
#   ./install.sh --uninstall   undo both
#
# Safe to run again. Claude Code loads the plugin in place, so a later `git pull` is the
# whole update; restart Claude Code (or run /reload-plugins) to pick it up.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
dest="$cfg/skills/human-writing"
claude_md="$cfg/CLAUDE.md"
rules="$dest/skills/human-writing/WRITING.md"
begin="<!-- human-writing:begin -->"
end="<!-- human-writing:end -->"

tilde() {
  case "$1" in
    "$HOME"/*) printf '~/%s' "${1#"$HOME"/}" ;;
    *) printf '%s' "$1" ;;
  esac
}

remove_block() {
  [ -f "$claude_md" ] || return 0
  python3 - "$claude_md" "$begin" "$end" <<'PY'
import re, sys
path, b, e = sys.argv[1:4]
text = open(path, encoding="utf-8").read()
new = re.sub(r"\n*" + re.escape(b) + r".*?" + re.escape(e) + r"[ \t]*\n?", "\n", text, flags=re.S)
if new != text:
    open(path, "w", encoding="utf-8").write(new.rstrip("\n") + "\n")
PY
}

if [ "${1:-}" = "--uninstall" ]; then
  remove_block
  echo "Removed the writing-rules import from $claude_md"
  if [ -L "$dest" ]; then
    rm "$dest"
    echo "Removed the link $dest"
  elif [ -d "$dest" ]; then
    echo "$dest is a real checkout, so it stays. Delete it, or run: claude plugin disable human-writing@skills-dir"
  fi
  echo "Restart Claude Code to apply."
  exit 0
fi

command -v python3 >/dev/null || { echo "python3 is required (the hooks are Python)." >&2; exit 1; }

# 1. Claude Code loads any plugin directory under ~/.claude/skills/ as <name>@skills-dir.
mkdir -p "$cfg/skills"
current="$(cd "$dest" 2>/dev/null && pwd -P || true)"
if [ "$current" != "$here" ]; then
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    echo "$dest already exists and points somewhere else. Move it away and run this again." >&2
    exit 1
  fi
  ln -s "$here" "$dest"
  echo "Linked $(tilde "$dest") -> $here"
fi

# 2. Import the rules in the global CLAUDE.md, so the main session and every subagent get them.
#    (Without this, the plugin's SessionStart hook loads them into the main session only.)
remove_block
touch "$claude_md"
printf '\n%s\n## Writing style\n@%s\n%s\n' "$begin" "$(tilde "$rules")" "$end" >> "$claude_md"
echo "Added the import of $(tilde "$rules") to $(tilde "$claude_md")"

echo "Done. Restart Claude Code, or run /reload-plugins in an open session."
