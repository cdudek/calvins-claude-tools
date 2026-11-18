"""Usage: pytest scripts/test_fast_close.py

Text contracts for the fast milestone close (3.21.0): the pieces that name who runs a heavy
check must agree, because two owners of one check means it runs twice. Reads files only.
"""

from __future__ import annotations

import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
CCT = SKILL.parents[1]


def flat(path: Path) -> str:
    """The file with every run of whitespace collapsed, so a wrapped sentence still matches."""
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


STAGES = flat(SKILL / "references/stages.md")
PLAN = flat(SKILL / "templates/change/plan.md")
SKILL_MD = flat(SKILL / "SKILL.md")
BUILDER = flat(CCT / "agents/sdlc-feature-builder.md")
CLOSE = BUILDER.split("## Mode: close", 1)[1].split("## Never edit", 1)[0]


# 1. One full-suite owner
def test_the_gate_is_the_only_full_suite_runner_in_the_close_builder() -> None:
    assert "only runner of the full suite" in CLOSE
    assert "unit and E2E suites" not in CLOSE  # no separate pre-gate full run


def test_stages_do_not_start_a_standalone_full_e2e_beside_the_review() -> None:
    assert "Start the full E2E run at the same time as the review" not in STAGES
    assert "the full E2E starts with it" not in STAGES
    assert "the full E2E suite once, ×3 only for changed and flaky specs" not in STAGES.split(
        "## Stage 6 — Milestone", 1
    )[1].split("2a.", 1)[0]


def test_stages_name_the_gate_as_the_one_full_suite_owner() -> None:
    assert "`verify_gate.py milestone` is the only runner of the full suite" in STAGES


def test_plan_and_skill_close_text_name_the_gate_as_owner() -> None:
    assert "only runner of the full suite" in PLAN
    assert "only runner of the full suite" in SKILL_MD


def test_the_codex_close_does_not_check_before_and_after_the_fix_parts() -> None:
    for text in (STAGES, SKILL_MD):
        assert "Claude checks, Codex fix parts, Claude checks and gate again" not in text
        assert "runs the checks and the gate again" not in text


def test_stages_say_the_gate_runs_evidence_checks_before_the_suites() -> None:
    assert "offline evidence checks first" in STAGES


# 4. Findings straight to one fix round
_at = STAGES.index("4. One fix round at milestone close")
STEP4 = STAGES[_at : STAGES.index("5. Reopen recaptured images", _at)]


def test_the_fix_round_reviews_once_explicitly_and_never_starts_a_fresh_review() -> None:
    assert "cct:review-code-run changes <parent> --codex" in STAGES
    assert "never starts a fresh review" in STEP4
    assert "no `cct:review-fix-run`" in STEP4  # it opens with a review of its own
    assert "cct:review-fix-run 1" not in STAGES
    assert "state directory" in STEP4 and "joined findings" in STEP4


def test_the_close_builder_fixes_from_the_joined_findings_and_never_reviews() -> None:
    assert "joined findings" in CLOSE and "review state directory" in CLOSE
    assert "never start a review" in CLOSE


def test_residual_findings_get_one_durable_disposition() -> None:
    for text in (STEP4, flat(SKILL / "references/convergence.md")):
        assert "## Dispositions" in text
        for word in ("accepted", "deferred", "blocked"):
            assert word in text
    assert "second fix round" not in SKILL_MD or "no second fix round" in SKILL_MD.lower()


# 5. One budget
CONVERGENCE = flat(SKILL / "references/convergence.md")
QUALITY = flat(SKILL / "references/quality-passes.md")
BUILD = flat(CCT / "skills/ux-build-validate/references/build.md")
BUILD_SKILL = flat(CCT / "skills/ux-build-validate/SKILL.md")


def test_the_texts_agree_on_one_fix_round_at_milestone_close() -> None:
    for name, text in (
        ("stages", STEP4),
        ("convergence", CONVERGENCE),
        ("quality-passes", QUALITY),
        ("build.md", BUILD),
        ("ux-build-validate", BUILD_SKILL),
    ):
        assert "one fix round at milestone close" in text.lower(), name


def test_no_text_still_says_three_fix_rounds() -> None:
    assert "up to three fix rounds" not in BUILD
    assert "two or three rounds" not in BUILD
    assert "two fix rounds per screen per design-system release" in CONVERGENCE.lower()


# 6. Auto-merge only after the owner or visual disposition
def test_nothing_is_armed_before_the_required_disposition() -> None:
    assert "Arm only after" in STAGES
    assert "never arm an `ask`-labelled or a closed PR" in STAGES
    assert "never arm an `ask`-labelled or a closed PR" in SKILL_MD
    before_push = STAGES.split("**Never idle on CI.**", 1)[1].split("Agents run", 1)[0]
    assert "after the owner and visual dispositions" in before_push
