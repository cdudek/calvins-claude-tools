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
        for piece in ("settings.json", "AGENTS.md", "boundary-map.yaml"):
            self.assertIn(piece, out)
        run(self.root, "--yes")
        self.assertEqual(run(self.root, "--check")[0], 0)
        self.assertIn("Habitat Thinking, CC BY 4.0.", (self.root / "AGENTS.md").read_text())
        self.assertEqual(ps.map_problems((self.root / "boundary-map.yaml").read_text()), [])

    def test_existing_map_is_not_overwritten_and_bad_shape_is_reported(self):
        (self.root / "boundary-map.yaml").write_text("version: 1\nentries:\n  - select: {paths: [a]}\n    floor: Nope\n")
        run(self.root, "--yes")
        self.assertIn("Nope", (self.root / "boundary-map.yaml").read_text())
        code, out = run(self.root, "--check")
        self.assertEqual(code, 1)
        self.assertIn("unknown floor 'Nope'", out)

    def test_new_repo_gets_only_the_pinned_shared_reference(self):
        self.assertEqual(run(self.root, "--yes")[0], 0)
        template = (self.root / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
        self.assertIn("Decision4 writing rules:", template)
        self.assertIn("## How hard is it to undo this PR after merging?", template)
        self.assertIn("**Recovery steps**\n\n1.", template)
        self.assertIn("## Decision record", template)
        workflow = (self.root / ".github/workflows/decision4.yml").read_text()
        self.assertIn("cdudek/blueprints/.github/workflows/decision4-check.yml@", workflow)
        self.assertNotIn("steps:", workflow)
        self.assertFalse((self.root / ".github/scripts/decision4.py").exists())
        self.assertFalse((self.root / "tests/decision4").exists())
        self.assertEqual(run(self.root, "--check")[0], 0)

    def test_existing_template_and_runner_keep_repo_content(self):
        (self.root / ".github").mkdir()
        template = self.root / ".github/pull_request_template.md"
        template.write_text("## Custom checklist\n- [ ] Human review\n")
        runner = self.root / "tests/decision4/run.sh"
        runner.parent.mkdir(parents=True)
        runner.write_text("# repo-owned invocation\n")
        run(self.root, "--yes")
        self.assertIn("## Custom checklist\n- [ ] Human review", template.read_text())
        self.assertIn("Decision4 writing rules:", template.read_text())
        self.assertNotIn("PULL_REQUEST_TEMPLATE.md", [p.name for p in (self.root / ".github").iterdir()])
        self.assertEqual(runner.read_text(), "# repo-owned invocation\n")
        before = template.read_text()
        run(self.root, "--yes")
        self.assertEqual(template.read_text(), before)

    def test_pointer_mode_when_an_import_carries_the_contract(self):
        (self.root / "AGENTS.md").write_text(ps.CONTRACT)
        (self.root / "CLAUDE.md").write_text("# Repo\n@AGENTS.md\n")
        run(self.root, "--yes")
        text = (self.root / "CLAUDE.md").read_text()
        self.assertIn("@AGENTS.md", text)
        self.assertNotIn("Decision4 handoff contract (v1)", text)
        self.assertNotIn("Unattended runs", text)
        # carried by the import: the check passes even without the pointer
        (self.root / "CLAUDE.md").write_text("# Repo\n@AGENTS.md\n")
        self.assertEqual(run(self.root, "--check")[0], 0)

    def test_wrong_contract_version_is_a_problem(self):
        (self.root / "CLAUDE.md").write_text("## Decision4 handoff contract (v2)\n")
        self.assertEqual(run(self.root, "--check")[0], 1)

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
