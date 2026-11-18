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
