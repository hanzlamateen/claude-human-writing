import os
import sys
import unittest
import zipfile
import io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_dist  # noqa: E402


class DistTests(unittest.TestCase):
    def test_zips_are_current(self):
        for rel, fn in build_dist.TARGETS.items():
            with open(os.path.join(ROOT, rel), "rb") as fh:
                self.assertEqual(fh.read(), fn(), f"{rel} is stale: run python3 tools/build_dist.py")

    def test_plugin_zip_has_one_manifest_and_the_skill(self):
        names = zipfile.ZipFile(io.BytesIO(build_dist.plugin_zip())).namelist()
        self.assertEqual([n for n in names if n.endswith("plugin.json")], [".claude-plugin/plugin.json"])
        self.assertIn("skills/human-writing/SKILL.md", names)
        self.assertIn("hooks/hooks.json", names)

    def test_skill_zip_is_one_folder(self):
        names = zipfile.ZipFile(io.BytesIO(build_dist.skill_zip())).namelist()
        self.assertTrue(all(n.startswith("human-writing/") for n in names))
        self.assertIn("human-writing/SKILL.md", names)
        self.assertIn("human-writing/WRITING.md", names)


if __name__ == "__main__":
    unittest.main()
