"""docs/sdlc-run.md is the newcomer page: it must state a version no older than the skill's, describe
all seven stages and link only files that exist.
Run: python3 -m unittest discover -s tests"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs/sdlc-run.md"
SKILL = ROOT / "plugins/cct/skills/sdlc-run/SKILL.md"
STAGES = ("Intent", "UX plan", "Facts", "Tech plan", "Build", "Milestone", "Outcome")


def version(pattern: str, text: str) -> tuple[int, ...]:
    m = re.search(pattern, text, re.M)
    assert m, f"no version found by {pattern}"
    return tuple(int(n) for n in m.group(1).split("."))


class SdlcRunPage(unittest.TestCase):
    def test_the_page_is_not_behind_the_skill(self):
        page = version(r"^Describes sdlc-run (\d+\.\d+\.\d+)", PAGE.read_text())
        skill = version(r"^  version: (\d+\.\d+\.\d+)", SKILL.read_text())
        self.assertGreaterEqual(page, skill, "docs/sdlc-run.md describes an older sdlc-run than SKILL.md: update it")

    def test_every_stage_says_what_you_get_who_acts_how_long_and_an_example(self):
        text = PAGE.read_text()
        for n, name in enumerate(STAGES, 1):
            m = re.search(rf"^### {n} {name}\n(.*?)(?=^##|\Z)", text, re.M | re.S)
            self.assertTrue(m, f"stage {n} {name} has no section")
            for label in ("You get", "Who acts", "Typical time", "Example"):
                self.assertIn(f"**{label}:**", m.group(1), f"stage {n} {name} lacks {label}")

    def test_no_link_is_dead(self):
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", PAGE.read_text()):
            if "://" not in target:
                self.assertTrue((PAGE.parent / target).exists(), f"dead link: {target}")

    def test_every_cct_agent_or_skill_it_names_exists(self):
        cct = ROOT / "plugins/cct"
        for name in set(re.findall(r"`cct:([a-z0-9-]+)", PAGE.read_text())):
            found = (cct / "agents" / f"{name}.md").exists() or (cct / "skills" / name).is_dir()
            self.assertTrue(found, f"the page names cct:{name}, which does not exist")


if __name__ == "__main__":
    unittest.main()
