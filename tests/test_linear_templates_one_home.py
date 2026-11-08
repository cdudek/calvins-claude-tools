"""The Linear templates live in linear-manage only; other skills point at them.
Run: python3 -m unittest discover -s tests"""
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "plugins/cct/skills"
HOME = SKILLS / "linear-manage/references"


class OneHome(unittest.TestCase):
    def test_no_other_skill_carries_a_copy(self):
        names = {f.name for f in HOME.glob("*-template.md")}
        copies = [str(f.relative_to(SKILLS)) for f in SKILLS.rglob("*-template.md") if f.name in names and HOME not in f.parents]
        self.assertEqual(copies, [])

    def test_the_pointers_resolve(self):
        for skill in ("arch-plan-write", "arch-decision-log", "project-plan-write", "project-report-write"):
            text = (SKILLS / skill / "SKILL.md").read_text()
            prefix = "${CLAUDE_PLUGIN_ROOT}/skills/linear-manage/references/"
            files = {w.split("`")[0] for w in text.split(prefix)[1:]}
            self.assertTrue(files, skill)
            for f in files:
                self.assertTrue((HOME / f).exists(), f"{skill}: {f}")


if __name__ == "__main__":
    unittest.main()
