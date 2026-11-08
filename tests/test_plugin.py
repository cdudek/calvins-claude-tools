"""plugins/cct is the source of truth: it must pass the naming and reference checks, keep its mirrored files in
step and name no OMR-internal thing.
Run: python3 -m unittest discover -s tests"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins/cct"
sys.path.insert(0, str(ROOT / "scripts"))
import taxonomy as t  # noqa: E402

MIRRORS = (  # two copies that must stay identical from the first rule down
    ("skills/linear-manage/references/prd-template.md", "skills/product-prd-write/template.md"),
    ("skills/product-workitem-write/references/requirements-grammar.md", "skills/sdlc-run/references/requirements-grammar.md"),
)


class Plugin(unittest.TestCase):
    def test_names_frontmatter_and_references(self):
        self.assertEqual(t.check_plugin(PLUGIN), [])

    def test_mirrored_files_are_identical(self):
        for canon, mirror in MIRRORS:
            a, b = ((PLUGIN / p).read_text() for p in (canon, mirror))
            self.assertEqual(a[a.find("\n---\n"):], b[b.find("\n---\n"):], f"{mirror} no longer matches {canon}")

    def test_no_private_or_internal_names(self):
        r = subprocess.run(["git", "grep", "-nIiE", r"\bomr\b|omr-|ramp106|KIT_READ_TOKEN", "--", ".", ":!tests/test_plugin.py", ":!*.pdf"],
                           cwd=ROOT, capture_output=True, text=True, errors="replace")
        self.assertEqual(r.stdout, "")


if __name__ == "__main__":
    unittest.main()
