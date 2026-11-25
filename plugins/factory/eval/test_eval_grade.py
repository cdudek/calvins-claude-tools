import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import eval_fixtures as fx
import grade

FACTORY = Path(__file__).resolve().parent.parent


def parse(**kw):
    return grade.parse_stream(fx.stream(**kw), fx.SUITE)


class Metrics(unittest.TestCase):
    def test_subagent_attribution_and_cost_split(self):
        m = parse()
        r = m["cost_by_role"]
        self.assertEqual(set(r), {"coordinator", "builder", "verifier", "goal_evaluator"})
        self.assertAlmostEqual(sum(r.values()), m["cost_total"], places=6)
        self.assertAlmostEqual(r["verifier"], 1.5)  # the only Opus messages belong to the verifier subagent
        self.assertAlmostEqual(r["builder"], 0.5)
        self.assertAlmostEqual(r["goal_evaluator"], 0.5)  # Haiku tokens no stream message accounts for
        self.assertAlmostEqual(m["haiku_usage"]["claude-haiku-5-5"]["costUSD"], 0.5)
        self.assertEqual(m["subagent_tool_calls"], 3)
        self.assertEqual(m["tokens"]["output"], 500, "a message id repeated in the stream is counted once")
        self.assertAlmostEqual(m["cache_hit"], 5000 / 5550)
        self.assertEqual((m["coordinator_turns"], m["permission_denials"]), (7, 1))

    def test_end_states(self):
        for text, want in (("HOLD: pushed", "HOLD"), ("SHIPPED https://x", "SHIPPED"), ("BLOCKED: owner decides", "BLOCKED"), ("INCOMPLETE: next", "INCOMPLETE"), ("done", "none")):
            self.assertEqual(parse(state=text)["end_state"], want)

    def test_unverified_exit(self):
        self.assertFalse(parse()["unverified_exit"])
        self.assertTrue(parse(last_edit_then_test=False)["unverified_exit"], "no passing test run after the last edit")

    def test_verifier_verdict(self):
        self.assertEqual(parse()["verifier_verdict"], "PASS")
        self.assertEqual(parse(verdict_pass=False)["verifier_verdict"], "FAIL")

    def test_goal_checks(self):
        m = parse()
        self.assertTrue(m["goal_set"] and m["goal_evaluated"] and m["goal_met"])
        self.assertEqual(m["goal_evaluator_models"], ["claude-haiku-5-5"])
        self.assertGreater(m["goal_evaluator_cost"], 0)
        self.assertEqual(m["terminal_reason"], "completed")
        none = parse(goal_set=False)
        self.assertFalse(none["goal_set"] or none["goal_met"])
        self.assertFalse(parse(evaluator=False)["goal_evaluated"], "no unexplained Haiku usage: the goal was never evaluated")
        self.assertFalse(parse(state="done")["goal_met"], "completed, but the last message is no end state")

    def test_goal_probe_shape_evaluator_is_modelusage_minus_message_usage(self):
        m = grade.parse_stream(fx.probe_stream())
        self.assertTrue(m["goal_set"] and m["goal_evaluated"])
        # the evaluator's tokens: 4 input, 89 output, 13874 cache creation (weighted 1 / 5 / 1.25)
        ev = 4 * 1 + 89 * 5 + 13874 * 1.25
        total = 6 * 1 + 256 * 5 + 11633 * 0.1 + 29972 * 1.25
        self.assertAlmostEqual(m["goal_evaluator_weighted_tokens"], ev)
        self.assertAlmostEqual(m["goal_evaluator_cost"], 0.00519878 * ev / total, places=7)
        self.assertAlmostEqual(m["cost_by_role"]["coordinator"] + m["goal_evaluator_cost"], 0.00519878, places=7)

    def test_subagent_stats(self):
        ok = parse()
        self.assertEqual((ok["subagents_spawned"], ok["harness_violation"]), (2, False))
        self.assertTrue(parse(background=1)["harness_violation"])
        k = parse(killed=1)
        self.assertEqual(k["subagents_killed"], 1)
        self.assertTrue(k["harness_violation"])

    def test_blocked_and_infra_result(self):
        m = parse(state="BLOCKED: need a credential")
        self.assertEqual(m["end_state"], "BLOCKED")
        self.assertTrue(parse(error="rate limit")["has_result"])


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.task, self.src, self.start, self.ref = fx.prepare(self.tmp.name)
        lock = {"CFACTORY_EVAL_HEAVY_LOCK": str(Path(self.tmp.name) / "heavy.lock")}
        p = mock.patch.dict(os.environ, lock)
        p.start()
        self.addCleanup(p.stop)

    def make_run(self, solved, name="r1", **stream_kw):
        run = Path(self.tmp.name) / "results" / "0" / name
        repo = run / "repo"
        repo.mkdir(parents=True)
        with tarfile.open(self.task / "start.tar.gz") as tf:
            tf.extractall(repo, filter="data")
        fx.git(repo, "init", "-q", "-b", "main")
        fx.git(repo, "add", "-A")
        fx.git(repo, "commit", "-q", "-m", "start")
        base = fx.git(repo, "rev-parse", "HEAD")
        if solved:
            fx.write(repo, "src/app.py", "def noop():\n    return None\n\n\n" + fx.SOLUTION)
            fx.git(repo, "add", "-A")
            fx.git(repo, "commit", "-q", "-m", "fix")
        fx.write_stream(run / "stream.jsonl", fx.stream(**stream_kw))
        (run / "run.json").write_text(json.dumps({"run_id": name, "stage": "0", "task_id": "t1", "arm": "default", "wall_s": 600, "task_dir": str(self.task),
                                                  "repo": str(repo), "plugin": str(FACTORY), "base_sha": base, "expected_models": ["sonnet", "opus"]}))
        return run

    def test_solved_run(self):
        g = grade.grade_run(self.make_run(True), grader=lambda text, repo: (True, "ok"))
        self.assertEqual(g["hidden_frac"], 1.0)
        self.assertEqual(set(g["units"]), {"p2p:suite", "f2p:tests/test_double.py", "scenario:doubles"})
        self.assertTrue(g["solved"] and g["valid"])
        self.assertFalse(g["verifier_false_pass"])
        self.assertEqual(g["unexpected_models"], [])
        self.assertTrue((Path(self.tmp.name) / "results/0/r1/grade.json").exists())
        self.assertEqual(g["files_outside_plan"], [])
        self.assertIsInstance(g["integrity_violations"], int)

    def test_unsolved_run_flags_false_pass_and_goal_met_not_solved(self):
        g = grade.grade_run(self.make_run(False, "r2"), grader=lambda text, repo: (False, "not delivered"))
        self.assertAlmostEqual(g["hidden_frac"], 1 / 3)  # the old suite passes, the hidden file and the scenario fail
        self.assertFalse(g["solved"])
        self.assertTrue(g["verifier_false_pass"])
        self.assertTrue(g["goal_met_not_solved"])
        self.assertTrue(g["claimed_done_not_solved"])
        self.assertEqual(g["visible_hidden_gap"], 1 - 1 / 3)

    def test_run_without_a_goal_is_invalid(self):
        g = grade.grade_run(self.make_run(True, "r3", goal_set=False), grader=None)
        self.assertFalse(g["valid"])
        self.assertIn("goal was never set", g["invalid_reason"])

    def test_error_before_the_first_turn_ends_is_infrastructure_not_a_missing_evaluation(self):
        g = grade.grade_run(self.make_run(True, "r5", evaluator=False, error="boom"))
        self.assertFalse(g["valid"])
        self.assertTrue(g["infra_suspect"])
        g2 = grade.grade_run(self.make_run(True, "r6", evaluator=False))
        self.assertIn("never evaluated", g2["invalid_reason"])

    def test_infra_failure_is_skipped(self):
        run = self.make_run(True, "r4")
        meta = json.loads((run / "run.json").read_text())
        meta["infra_failure"] = "rate-limit"
        (run / "run.json").write_text(json.dumps(meta))
        g = grade.grade_run(run)
        self.assertFalse(g["valid"])
        self.assertIsNone(g["hidden_frac"])

    def test_parse_verdict(self):
        self.assertEqual(grade.parse_verdict('thinking\n{"pass": true, "evidence": "src/app.py"}'), (True, "src/app.py"))
        self.assertFalse(grade.parse_verdict("no json")[0])


if __name__ == "__main__":
    unittest.main()
