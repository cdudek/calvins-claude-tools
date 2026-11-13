import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import project_setup as ps


def run(root, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = ps.main(["--root", str(root), *args])
    return code, out.getvalue()


class ProjectSetupTest(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        self.addCleanup(self._t.cleanup)

    def settings(self):
        return json.loads((self.root / ".claude/settings.json").read_text())

    def test_dry_run_writes_nothing(self):
        code, out = run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("PLAN", out)
        self.assertEqual(list(self.root.rglob("*")), [])
        run(self.root, "--yes", "--dry-run")
        self.assertEqual(list(self.root.rglob("*")), [])

    def test_merge_preserves_existing_keys(self):
        (self.root / ".claude").mkdir()
        (self.root / ".claude/settings.json").write_text(json.dumps(
            {"permissions": {"deny": ["Read(./.env)"]}, "enabledPlugins": {"x@y": True}}))
        run(self.root, "--yes", "--marketplace-ref", "v1.2.0")
        s = self.settings()
        self.assertEqual(s["permissions"], {"deny": ["Read(./.env)"]})
        self.assertTrue(s["enabledPlugins"]["x@y"] and s["enabledPlugins"]["cct@cct"])
        self.assertEqual(s["extraKnownMarketplaces"]["cct"]["source"],
                         {"source": "github", "repo": "cdudek/calvins-claude-tools", "ref": "v1.2.0"})

    def test_extra_plugin_needs_marketplace_source(self):
        code, out = run(self.root, "--yes", "--plugins", "cct@cct,plannotator@pm")
        self.assertEqual(code, 1)
        self.assertIn("--marketplace-source pm=", out)
        code, _ = run(self.root, "--yes", "--plugins", "plannotator@pm", "--marketplace-source", "pm=a/b")
        self.assertEqual(code, 0)
        self.assertEqual(self.settings()["extraKnownMarketplaces"]["pm"]["source"]["repo"], "a/b")

    def test_check_reports_missing_then_passes_after_apply(self):
        code, out = run(self.root, "--check")
        self.assertEqual(code, 1)
        self.assertIn("settings.json", out)
        run(self.root, "--yes")
        self.assertEqual(run(self.root, "--check")[0], 0)

    def test_decision4_files_are_added_once_and_never_required(self):
        (self.root / "CLAUDE.md").write_text("# Repo\n")
        code, out = run(self.root, "--check")
        self.assertNotIn("boundary-map", out)
        run(self.root, "--yes")
        self.assertIn("floor: Undo", (self.root / "boundary-map.yaml").read_text())
        agents = (self.root / "AGENTS.md").read_text()
        self.assertIn("## Decision4: how hard is this change to undo?", agents)
        self.assertIn("@AGENTS.md", (self.root / "CLAUDE.md").read_text())
        template = (self.root / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
        self.assertIn("## How hard is it to undo this PR after merging?", template)
        self.assertFalse((self.root / ".github/workflows").exists())
        self.assertFalse((self.root / "scripts").exists())
        run(self.root, "--yes")
        self.assertEqual((self.root / "AGENTS.md").read_text(), agents)

    def test_no_decision4_flag_skips_the_files(self):
        run(self.root, "--yes", "--no-decision4")
        self.assertFalse((self.root / "boundary-map.yaml").exists())

    def test_invalid_settings_json_stops_without_writing(self):
        (self.root / ".claude").mkdir()
        (self.root / ".claude/settings.json").write_text("{nope")
        with self.assertRaises(SystemExit):
            run(self.root, "--yes")
        self.assertEqual((self.root / ".claude/settings.json").read_text(), "{nope")

    def test_anti_slop_command_printed_for_typescript_only(self):
        self.assertNotIn("install-anti-slop", run(self.root)[1])
        (self.root / "tsconfig.json").write_text("{}")
        self.assertIn("install-anti-slop", run(self.root)[1])


if __name__ == "__main__":
    unittest.main()
