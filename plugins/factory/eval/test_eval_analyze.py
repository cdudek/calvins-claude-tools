import math
import random
import tempfile
import unittest
from pathlib import Path

import analyze
import eval_fixtures as fx


class Math(unittest.TestCase):
    def test_pass_k(self):
        self.assertAlmostEqual(analyze.pass_k(3, 4, 1), 0.75)
        self.assertAlmostEqual(analyze.pass_k(3, 4, 2), 3 / 6)
        self.assertAlmostEqual(analyze.pass_k(3, 4, 4), 0.0)
        self.assertAlmostEqual(analyze.pass_k(4, 4, 4), 1.0)
        self.assertTrue(math.isnan(analyze.pass_k(2, 4, 5)))

    def test_beta_comparison(self):
        rng = random.Random(1)
        self.assertGreater(analyze.beta_gt(8, 8, 0, 8, rng), 0.99)
        self.assertAlmostEqual(analyze.beta_gt(4, 8, 4, 8, rng), 0.5, delta=0.03)
        self.assertAlmostEqual(analyze.beta_gt(1, 1, 0, 1, rng), 5 / 6, delta=0.03)  # Beta(2,1) vs Beta(1,2)

    def test_bootstrap_interval(self):
        m, lo, hi = analyze.boot_ci([1.0] * 20, random.Random(1), 500)
        self.assertEqual((m, lo, hi), (1.0, 1.0, 1.0))
        m, lo, hi = analyze.boot_ci([0.0, 1.0] * 10, random.Random(1), 2000)
        self.assertTrue(lo < 0.5 < hi)

    def test_judge_against_the_band(self):
        self.assertEqual(analyze.judge(-0.02, 0.03, 0.05), "equivalent")
        self.assertEqual(analyze.judge(0.1, 0.2, 0.05), "higher")
        self.assertEqual(analyze.judge(-0.2, -0.1, 0.05), "lower")
        self.assertEqual(analyze.judge(-0.1, 0.2, 0.05), "unclear")

    def test_parallel_load_and_adjustment(self):
        rows = [{"arm": "a", "start_epoch": 0, "end_epoch": 600, "wall_min": 10}, {"arm": "a", "start_epoch": 0, "end_epoch": 600, "wall_min": 20},
                {"arm": "a", "start_epoch": 1000, "end_epoch": 1600, "wall_min": 10}]
        analyze.parallel_load(rows)
        self.assertEqual([r["load"] for r in rows], [2.0, 2.0, 1.0])
        b = analyze.load_adjust(rows)
        self.assertEqual(rows[2]["time_adj_min"], 10)  # load 1 is left as it is
        self.assertIsInstance(b, float)


class Whole(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        fx.fake_results(self.tmp.name)
        self.res, self.use = analyze.analyze(self.tmp.name, B=300)

    def test_invalid_and_infra_runs_are_excluded_and_listed(self):
        self.assertEqual({e["run_id"] for e in self.res["excluded"]}, {"bad", "rl"})
        self.assertNotIn("bad", {r["run_id"] for r in self.use})

    def test_summary_columns_and_pass_k(self):
        s = self.res["summary"]["default"]
        self.assertEqual(s["n"], 3 - 1)
        self.assertEqual(len(s["pass_k"]), s["n"])
        self.assertIn("p_dominated", s)
        self.assertIsNone(s["p_beats_default"])
        self.assertIsNotNone(self.res["summary"]["pb1"]["p_beats_default"])

    def test_cascade_is_one_row_with_summed_cost(self):
        c = self.res["summary"]["cascade"]
        self.assertEqual(c["n"], 1)
        self.assertAlmostEqual(c["cost"], 10.0)
        self.assertEqual(c["solved"], 1)

    def test_screening_finds_the_built_in_cost_effect(self):
        e = self.res["effects"]["cost"]
        self.assertLess(e["A"]["effect"], -3)
        self.assertLess(e["A"]["hi"], 0)
        self.assertLess(abs(e["B"]["effect"]), 1.5)

    def test_comparison_has_note_for_small_n_and_both_time_views(self):
        v = self.res["summary"]["pb1"]["vs_default"]
        self.assertIn("n < 10", v["note"])
        for k in ("log_cost", "log_time", "log_time_adj", "time_min", "time_adj_min", "hidden"):
            self.assertIn(k, v)

    def test_tables_written(self):
        for f in ("table.csv", "summary.csv", "comparisons.csv", "effects.csv", "analysis.json"):
            self.assertTrue((Path(self.tmp.name) / f).exists(), f)

    def test_confusion_and_taxonomy(self):
        self.assertIn("goal evaluator", self.res["confusion"])
        self.assertIn("infrastructure", self.res["taxonomy"]["pb1"])
        self.assertFalse(self.res["evaluator_varies"])


if __name__ == "__main__":
    unittest.main()
