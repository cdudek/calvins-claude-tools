"""The SessionStart drift notice: one line when a repo that declares cct has drifted, silent otherwise, never blocks.
Run: python3 -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent / "plugins/cct"
HOOK = PLUGIN / "hooks/project-drift-check.py"
OK = {"extraKnownMarketplaces": {"cct": {"source": {"source": "github", "repo": "cdudek/calvins-claude-tools"}}},
      "enabledPlugins": {"cct@cct": True}}


def run(settings=None, raw=None):
    with tempfile.TemporaryDirectory() as d:
        if settings is not None or raw is not None:
            (Path(d) / ".claude").mkdir()
            (Path(d) / ".claude/settings.json").write_text(raw if raw is not None else json.dumps(settings))
        t = time.monotonic()
        r = subprocess.run([sys.executable, str(HOOK)], capture_output=True, text=True, cwd="/",
                           env={**os.environ, "CLAUDE_PROJECT_DIR": d}, timeout=10)
        return r, time.monotonic() - t


class DriftHook(unittest.TestCase):
    def assertSilent(self, r):
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_registered_on_session_start_with_a_short_timeout(self):
        entry = json.loads((PLUGIN / "hooks/hooks.json").read_text())["hooks"]["SessionStart"][0]["hooks"][0]
        self.assertIn("project-drift-check.py", entry["command"])
        self.assertLessEqual(entry["timeout"], 10)

    def test_silent_without_settings(self):
        self.assertSilent(run()[0])

    def test_silent_when_the_repo_does_not_declare_cct(self):
        self.assertSilent(run({"enabledPlugins": {"other@x": True}})[0])

    def test_silent_when_settings_are_fine(self):
        self.assertSilent(run(OK)[0])

    def test_one_line_when_cct_is_declared_but_not_enabled(self):
        r, _ = run({"extraKnownMarketplaces": OK["extraKnownMarketplaces"], "enabledPlugins": {"cct@cct": False}})
        self.assertEqual(r.returncode, 0)
        lines = r.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1)
        msg = json.loads(lines[0])["systemMessage"]
        self.assertIn("drifts", msg)
        self.assertIn("/cct:project-repository-run", msg)

    def test_one_line_when_the_marketplace_is_declared_but_the_plugin_is_not_enabled(self):
        r, _ = run({"extraKnownMarketplaces": OK["extraKnownMarketplaces"]})
        self.assertEqual(len(r.stdout.strip().splitlines()), 1)

    def test_a_broken_settings_file_never_blocks(self):
        self.assertSilent(run(raw="{not json")[0])

    def test_fast(self):
        self.assertLess(run(OK)[1], 2.0)


if __name__ == "__main__":
    unittest.main()
