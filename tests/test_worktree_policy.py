"""Worktree lifecycle and installation policy has one linked source of truth."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/cct"


class WorktreePolicy(unittest.TestCase):
    def test_install_question_is_canonical_and_entrypoints_link_it(self):
        policy = (PLUGIN / "references/worktree-usage.md").read_text()
        self.assertIn(
            "Install Worktrunk (brew install worktrunk && wt config shell install)? Recommended",
            policy,
        )
        for relative in (
            "skills/sdlc-run/SKILL.md",
            "skills/sdlc-run/references/stages.md",
            "skills/project-repository-run/SKILL.md",
        ):
            text = (PLUGIN / relative).read_text()
            self.assertIn("worktree-usage.md", text, relative)
            self.assertIn("preflight" if "sdlc-run" in relative else "installation", text)
        self.assertIn("Continue with Git", policy)
        self.assertIn("hooks and scripts never prompt", policy)

    def test_review_entrypoints_share_pr_head_and_path_entry_flow(self):
        for relative in (
            "skills/review-feedback-run/references/pr-worktree.md",
            "skills/review-code-run/references/mode-pr.md",
            "skills/review-dependency-run/references/commands/review.md",
        ):
            text = (PLUGIN / relative).read_text()
            self.assertIn("worktree-usage.md", text, relative)
            self.assertIn("--no-cd --format json", text, relative)
            self.assertIn("git worktree add", text, relative)
            self.assertIn("EnterWorktree path=", text, relative)
            self.assertNotIn("../dependabot-", text, relative)


if __name__ == "__main__":
    unittest.main()
