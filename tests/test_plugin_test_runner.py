"""Failing suite output must be visible while passing suites remain quiet."""

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
