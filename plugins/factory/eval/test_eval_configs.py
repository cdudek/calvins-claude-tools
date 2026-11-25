import itertools
import unittest

import configs


class Configs(unittest.TestCase):
    def test_pb_design_is_balanced_and_orthogonal(self):
        m = configs.PB_MATRIX
        self.assertEqual((len(m), len(m[0])), (8, 7))
        for j in range(7):
            col = [row[j] for row in m]
            self.assertEqual(sum(col), 0, "each factor runs 4 times at each level")
        for a, b in itertools.combinations(range(7), 2):
            self.assertEqual(sum(row[a] * row[b] for row in m), 0, f"columns {a} and {b} are orthogonal")

    def test_pb_arms_apply_the_alternative_levels(self):
        base = configs.get("default")
        self.assertEqual(configs.pb_levels("default"), None)
        for i in range(1, 9):
            arm, lv = configs.get(f"pb{i}"), configs.pb_levels(f"pb{i}")
            self.assertEqual(arm["roles"]["verifier"][0], "sonnet" if lv["A"] == 1 else base["roles"]["verifier"][0])
            self.assertEqual(arm["roles"]["builder"][1], "high" if lv["B"] == 1 else "medium")
            self.assertEqual(arm["advisor"], "opus" if lv["C"] == 1 else None)
            self.assertEqual(arm["context"], "raw" if lv["D"] == 1 else "spec")
            self.assertEqual(arm["parallel"], 1 if lv["E"] == 1 else 3)
            self.assertEqual(arm["reviewer"], "codex-astra" if lv["F"] == 1 else "opus")
            self.assertEqual(arm["roles"]["verifier"][1], "medium" if lv["G"] == 1 else "high")
            self.assertEqual(arm["roles"]["coordinator"], base["roles"]["coordinator"], "the coordinator is not a factor")

    def test_grid_is_builder_only(self):
        grid = configs.grid_arms()
        self.assertEqual(len(grid), 9)
        self.assertEqual({a["roles"]["builder"] for a in grid}, {(m, e) for m in ("haiku", "sonnet", "opus") for e in ("low", "medium", "high")})
        for a in grid:
            self.assertEqual(set(a["ablate"]), {"verifier", "security"})
            self.assertEqual(a["roles"]["coordinator"], ("sonnet", "medium"))
        self.assertEqual(configs.STAGES["grid"], [a["name"] for a in grid])

    def test_stages_and_cascade_resolve(self):
        for names in configs.STAGES.values():
            for n in names:
                configs.get(n)
        for n in configs.get("cascade")["cascade"]:
            configs.get(n)
        self.assertEqual(configs.get("always_cheap")["roles"]["builder"][0], "haiku")
        self.assertEqual(configs.get("plain_sonnet")["harness"], "plain")

    def test_bad_arm_refused(self):
        with self.assertRaises(ValueError):
            configs.make("x", ablate=["nothing"])
        with self.assertRaises(KeyError):
            configs.get("nope")


if __name__ == "__main__":
    unittest.main()
