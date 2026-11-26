import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

import eval_fixtures as fx
import prepare_task

CHECK = Path(__file__).resolve().parents[2] / "plugins/factory/skills/run/scripts/check-plan.py"


class Prepare(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out, self.repo, self.start, self.ref = fx.prepare(self.tmp.name)

    def test_task_json_and_hidden_tests(self):
        t = json.loads((self.out / "task.json").read_text())
        self.assertEqual((t["start"], t["reference"], t["slug"]), (self.start, self.ref, fx.SLUG))
        self.assertEqual(t["hidden_tests"], ["tests/test_double.py"])
        self.assertEqual((self.out / "hidden-tests/tests/test_double.py").read_text(), fx.HIDDEN)
        self.assertEqual(t["reference_stat"]["nontest_files"], ["src/app.py"])
        self.assertTrue((self.out / "scenarios/doubles.md").exists())

    def test_tarball_has_no_history_and_no_future_plan_entries(self):
        with tarfile.open(self.out / "start.tar.gz") as tf:
            names = tf.getnames()
            tf.extractall(self.tmp.name + "/x", filter="data")
        self.assertFalse([n for n in names if n.startswith(".git")])
        self.assertNotIn("tests/test_double.py", names, "the hidden test is not in the start tree")
        plan = (Path(self.tmp.name) / "x" / f"changes/{fx.SLUG}/plan.md").read_text()
        self.assertIn("### 2000-01-01", plan)
        self.assertNotIn("2999", plan)
        self.assertNotIn("must not leak", plan)

    def test_intent_from_outcome_and_migration_make_the_plan_pass_the_check(self):
        root = Path(self.tmp.name) / "x"
        with tarfile.open(self.out / "start.tar.gz") as tf:
            tf.extractall(root, filter="data")
        intent = (root / f"changes/{fx.SLUG}/intent.md").read_text()
        self.assertIn("- outcome-1: Callers can double a number", intent)
        delta = (root / f"changes/{fx.SLUG}/delta.md").read_text()
        self.assertIn("- req-1:", delta)
        self.assertNotIn("app/R1", delta)
        r = subprocess.run([sys.executable, str(CHECK), str(root / f"changes/{fx.SLUG}/plan.md")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("PLAN OK", r.stdout)

    def test_strip_progress_keeps_earlier_entries_and_other_sections(self):
        text = "## Progress log\n### 2026-01-01 a\nkeep\n### 2026-02-01 b\ndrop\n## Next\nstay\n"
        out = prepare_task.strip_progress(text, "2026-01-15")
        self.assertIn("keep", out)
        self.assertNotIn("drop", out)
        self.assertIn("stay", out)

    def test_out_inside_repo_refused(self):
        with self.assertRaises(SystemExit):
            prepare_task.main([str(self.repo), "--start", self.start, "--reference", self.ref, "--task-id", "x", "--plan", f"changes/{fx.SLUG}/plan.md",
                               "--out", str(self.repo / "task")])

    def prepare_variant(self, *extra):
        """A second task from the same repo, where the reference also adds a test that already passes at the start commit."""
        if not (self.repo / "tests/test_free.py").exists():
            fx.write(self.repo, "tests/test_free.py", "from src.app import noop\n\n\ndef test_free():\n    assert noop() is None\n")
            fx.git(self.repo, "add", "-A")
            fx.git(self.repo, "commit", "-q", "-m", "free")
        out = Path(self.tmp.name) / "task2"
        prepare_task.main([str(self.repo), "--start", self.start, "--reference", fx.git(self.repo, "rev-parse", "HEAD"), "--task-id", "t2", "--plan",
                           f"changes/{fx.SLUG}/plan.md", "--out", str(out), "--suite-cmd", fx.SUITE, *extra])
        return json.loads((out / "task.json").read_text()), out

    def test_env_and_exclude_glob(self):
        fx.write(self.repo, "assets/shot.png", "big")
        fx.git(self.repo, "add", "-A")
        fx.git(self.repo, "commit", "-q", "-m", "asset")
        start = fx.git(self.repo, "rev-parse", "HEAD")
        out = Path(self.tmp.name) / "task3"
        prepare_task.main([str(self.repo), "--start", start, "--reference", start, "--task-id", "t3", "--plan", f"changes/{fx.SLUG}/plan.md", "--out", str(out),
                           "--env", "TEST_DATABASE_URL=postgres://u@127.0.0.1:5433/{db}", "--env", "TAG={run}", "--exclude-glob", "assets/*"])
        self.assertEqual(json.loads((out / "task.json").read_text())["env"], {"TEST_DATABASE_URL": "postgres://u@127.0.0.1:5433/{db}", "TAG": "{run}"})
        with tarfile.open(out / "start.tar.gz") as tf:
            names = tf.getnames()
        self.assertNotIn("assets/shot.png", names)
        self.assertIn("src/app.py", names)
        with self.assertRaises(SystemExit):
            prepare_task.main([str(self.repo), "--start", start, "--reference", start, "--task-id", "t3", "--plan", f"changes/{fx.SLUG}/plan.md", "--out", str(out), "--env", "nope"])

    def test_prove_splits_failing_and_already_passing_hidden_files(self):
        t, _ = self.prepare_variant("--prove")
        self.assertEqual(t["fail_to_pass"], ["tests/test_double.py"])
        self.assertEqual(t["pass_to_pass_hidden"], ["tests/test_free.py"])

    def test_fail_to_pass_lists_given_by_hand(self):
        t, _ = self.prepare_variant("--fail-to-pass", "tests/test_double.py")
        self.assertEqual((t["fail_to_pass"], t["pass_to_pass_hidden"]), (["tests/test_double.py"], ["tests/test_free.py"]))
        with self.assertRaises(SystemExit):
            self.prepare_variant("--fail-to-pass", "tests/other.py")

    def test_no_proof_leaves_the_lists_out(self):
        self.assertNotIn("fail_to_pass", json.loads((self.out / "task.json").read_text()))
        self.assertEqual(json.loads((self.out / "task.json").read_text())["env"], {})


if __name__ == "__main__":
    unittest.main()
