"""Keep all PR producers on the shared readable Decision4 contract."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDLC = ROOT / "plugins/cct/skills/sdlc-run"
spec = importlib.util.spec_from_file_location(
    "decision4_assets", SDLC / "scripts/decision4_assets.py"
)
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class Decision4Assets(unittest.TestCase):
    def test_blueprints_ship_the_same_writing_rules_and_section(self):
        templates = list(
            (ROOT / "plugins/cct/blueprint").glob("*/.github/PULL_REQUEST_TEMPLATE.md")
        )
        self.assertEqual(len(templates), 4)
        for path in templates:
            text = path.read_text()
            self.assertEqual(
                text[
                    text.index("<!--\nDecision4 writing rules:") : text.index(
                        "</details>"
                    )
                    + len("</details>")
                ]
                + "\n",
                assets.pr_section(),
                str(path),
            )

    def test_refresh_preserves_surrounding_sections_and_is_idempotent(self):
        before = "## What\nCustom description\n\n"
        after = "\n## Decision record\n- **Chose:** Keep the existing owner decision.\n\n## Verification\n- [ ] Human review\n"
        old = before + assets.HEADING + "\n**Repair** — old wording\n" + after
        refreshed = assets.merge_pr_template(old)
        self.assertTrue(refreshed.startswith(before))
        self.assertTrue(refreshed.endswith(after))
        self.assertEqual(refreshed.count(assets.HEADING), 1)
        self.assertIn("**Recovery steps**", refreshed)
        self.assertEqual(refreshed.count("## Decision record"), 1)
        self.assertEqual(assets.merge_pr_template(refreshed), refreshed)

    def test_comment_before_repo_sections_preserves_them(self):
        prefix = "## What\n\n- **Change:** Keep existing wording.\n\n## Rules touched\n\n- **Rules:** INTERACTION.md ids.\n\n## Verification\n\n- [ ] Human review\n\n"
        comment = "<!--\nDecision4 writing rules:\nOld instructions.\n-->\n"
        old = comment + prefix + assets.HEADING + "\n**Repair** — old recovery\n"
        refreshed = assets.merge_pr_template(old)
        self.assertTrue(refreshed.startswith(prefix))
        self.assertEqual(refreshed.count("## Rules touched"), 1)
        self.assertIn("- [ ] Human review", refreshed)
        self.assertEqual(assets.merge_pr_template(refreshed), refreshed)

    def test_pr_writers_and_reviewers_consult_the_same_rules(self):
        for relative in (
            "git-pr-run/SKILL.md",
            "github-manage/SKILL.md",
            "sdlc-run/references/stages.md",
            "sdlc-run/references/adopt.md",
            "project-repository-run/SKILL.md",
            "review-code-run/references/pr-context-loading.md",
            "review-feedback-run/references/pr-gather.md",
            "review-feedback-run/references/pr-finalize.md",
        ):
            self.assertIn(
                "decision4-pr.md",
                (ROOT / "plugins/cct/skills" / relative).read_text(),
                relative,
            )


if __name__ == "__main__":
    unittest.main()
