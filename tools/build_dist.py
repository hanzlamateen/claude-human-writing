#!/usr/bin/env python3
"""Build the two upload files for claude.ai.

  dist/human-writing-plugin.zip   Customize > Plugins > Add > Upload plugin (skill + hooks)
  dist/human-writing-skill.zip    Customize > Skills > upload (the skill on its own)

The zips are deterministic (sorted entries, fixed timestamps), so rebuilding without
changes leaves them byte-for-byte the same. tests/test_dist.py checks they're current.
"""
import io
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAMP = (2026, 1, 1, 0, 0, 0)


def files_under(*parts):
    base = os.path.join(ROOT, *parts)
    if os.path.isfile(base):
        return [os.path.join(*parts)]
    out = []
    for d, dirs, names in os.walk(base):
        dirs[:] = sorted(x for x in dirs if x != "__pycache__")
        for n in sorted(names):
            if not n.endswith(".pyc"):
                out.append(os.path.relpath(os.path.join(d, n), ROOT))
    return out


def build(entries):
    """entries: list of (path in zip, path on disk relative to ROOT). Returns zip bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, rel in sorted(entries):
            info = zipfile.ZipInfo(arc, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if rel.endswith((".py", ".sh")) else 0o644
            info.external_attr = (0o100000 | mode) << 16
            with open(os.path.join(ROOT, rel), "rb") as fh:
                z.writestr(info, fh.read())
    return buf.getvalue()


def plugin_zip():
    rels = [os.path.join(".claude-plugin", "plugin.json"), "README.md", "LICENSE"]
    rels += files_under("hooks") + files_under("skills")
    return build([(r, r) for r in rels])


def skill_zip():
    skill = os.path.join("skills", "human-writing")
    rels = files_under(skill)
    return build([(os.path.join("human-writing", os.path.relpath(r, skill)), r) for r in rels])


TARGETS = {
    os.path.join("dist", "human-writing-plugin.zip"): plugin_zip,
    os.path.join("dist", "human-writing-skill.zip"): skill_zip,
}

if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    for rel, fn in TARGETS.items():
        data = fn()
        with open(os.path.join(ROOT, rel), "wb") as fh:
            fh.write(data)
        print(f"wrote {rel} ({len(data):,} bytes)")
    sys.exit(0)
