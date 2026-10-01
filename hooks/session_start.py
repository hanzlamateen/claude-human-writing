#!/usr/bin/env python3
"""SessionStart hook: load skills/human-writing/WRITING.md into the session.

Skipped when ~/.claude/CLAUDE.md already imports it (install.sh adds that import),
so the rules are never loaded twice. Without the import, for example on a machine
that only has the plugin synced from claude.ai, this is how the rules get in.
"""
import json
import os
import re
import sys

root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")

try:
    with open(os.path.join(cfg, "CLAUDE.md"), encoding="utf-8") as fh:
        if re.search(r"^\s*@\S*human-writing\S*/WRITING\.md\s*$", fh.read(), re.M):
            sys.exit(0)
except OSError:
    pass

try:
    with open(os.path.join(root, "skills", "human-writing", "WRITING.md"), encoding="utf-8") as fh:
        rules = fh.read()
except OSError:
    sys.exit(0)

print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": rules}}))
