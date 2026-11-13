"""Failing suite output must be visible while passing suites remain quiet."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PluginTestRunner(unittest.TestCase):
    def run_suite(self, content):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "plugins/cct/hooks").mkdir(parents=True)
            (root / "plugins/cct/skills").mkdir()
            shutil.copy2(ROOT / "scripts/run-plugin-tests.sh", root / "scripts")
            (root / "plugins/cct/hooks/test_example.sh").write_text(content)
            return subprocess.run(
                ["bash", "scripts/run-plugin-tests.sh"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

    def run_mod_block(self, claude_script, env_extra):
        """The script's agent-tracker block, in a temp root that holds the mod folder and a stub `claude`."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "plugins/agent-tracker").mkdir(parents=True)
            (root / ".claude-plugin").mkdir()
            (root / ".claude-plugin/marketplace.json").write_text("{}")
            shutil.copy2(ROOT / "scripts/run-plugin-tests.sh", root / "scripts")
            stubs = root / "stubs"
            stubs.mkdir()
            if claude_script is not None:
                stub = stubs / "claude"
                stub.write_text("#!/bin/sh\n" + claude_script)
                stub.chmod(0o755)
            env = {k: v for k, v in os.environ.items() if k != "CI"}
            env.update(env_extra, PATH=f"{stubs}:/usr/bin:/bin")
            return subprocess.run(["bash", "scripts/run-plugin-tests.sh"], cwd=root, capture_output=True, text=True, check=False, env=env)

    def test_mod_checks_print_two_ok_lines(self):
        result = self.run_mod_block("echo noisy-detail; exit 0\n", {})
        self.assertEqual(result.returncode, 0)
        self.assertIn("ok   agent-tracker: validate", result.stdout)
        self.assertIn("ok   agent-tracker: test", result.stdout)
        self.assertNotIn("noisy-detail", result.stdout)

    def test_mod_check_failure_prints_output_and_fails(self):
        result = self.run_mod_block('echo type-error-detail; [ "$2" = test ] && exit 1; exit 0\n', {})
        self.assertEqual(result.returncode, 1)
        self.assertIn("ok   agent-tracker: validate", result.stdout)
        self.assertIn("FAIL agent-tracker: test", result.stdout)
        self.assertIn("type-error-detail", result.stdout)

    def test_missing_claude_skips_in_ci_and_fails_elsewhere(self):
        ci = self.run_mod_block(None, {"CI": "true"})
        self.assertEqual(ci.returncode, 0)
        self.assertIn("skip agent-tracker: claude CLI not found", ci.stdout)
        local = self.run_mod_block(None, {})
        self.assertEqual(local.returncode, 1)
        self.assertIn("FAIL agent-tracker: claude CLI not found", local.stdout)

    def test_passing_suite_output_is_quiet(self):
        result = self.run_suite("echo passing-detail; exit 0\n")
        self.assertEqual(result.returncode, 0)
        self.assertIn("ok   hooks/test_example.sh", result.stdout)
        self.assertNotIn("passing-detail", result.stdout)

    def test_failing_suite_prints_stdout_and_stderr(self):
        result = self.run_suite(
            "echo assertion-detail; echo failure-detail >&2; exit 1\n"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL hooks/test_example.sh", result.stdout)
        self.assertIn("assertion-detail", result.stdout)
        self.assertIn("failure-detail", result.stdout)


if __name__ == "__main__":
    unittest.main()
