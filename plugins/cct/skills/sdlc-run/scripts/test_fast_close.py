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


def test_residual_findings_are_settled_by_the_owner_dialog() -> None:
    for text in (STEP4, flat(SKILL / "references/convergence.md")):
        assert "Change <change id>, finding <finding id>: " in text
        for label in ("Fix it now", "Accept as is", "Defer to milestone <n>", "Block the close"):
            assert f"`{label}`" in text
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


# 2. UX assessment without a PR
UX = flat(CCT / "skills/ux-assessment-run/SKILL.md")
CHANGE_SCOPE = UX.split("## scope=change", 1)[1]
DISPATCH = flat(CCT / "references/dispatch.md")


def test_the_assessment_takes_a_local_base_head_and_worktree() -> None:
    assert "scope=change base=<ref> head=<ref> [worktree=<path>]" in UX
    assert "scope=change [pr-number | pr-url]" in UX  # PR mode keeps its interface


def test_a_missing_pr_stops_only_the_pr_form() -> None:
    resolve = CHANGE_SCOPE.split("### 2.", 1)[0]
    stop = resolve.index("None: stop and say so")
    assert "PR form" in resolve[:stop], "the stop must sit inside the PR form"
    assert "never calls `gh`" in resolve  # the local form has no PR to find
    assert "git -C <worktree> diff --name-only <base>...<head>" in resolve


def test_every_child_pass_receives_base_head_and_worktree() -> None:
    assert "base, head and worktree" in CHANGE_SCOPE
    assert "git -C <worktree> diff <base>...<head>" in CHANGE_SCOPE
    assert "base, head and worktree" in DISPATCH
    for skill in ("ux-build-validate", "ux-rules-validate"):
        text = flat(CCT / f"skills/{skill}/SKILL.md")
        assert "base=<ref> head=<ref> worktree=<path>" in text, skill


def test_stage_6_calls_the_local_form_before_the_gate() -> None:
    assert "cct:ux-assessment-run scope=change base=<parent> head=<milestone head>" in STAGES
    assert STAGES.index("cct:ux-assessment-run scope=change base=<parent>") < STAGES.index(
        "5. Reopen recaptured images"
    )


def test_dispositions_are_bound_to_the_owners_structured_answer() -> None:
    assert "structured tool result" in STEP4 and "never typed text" in STEP4
    assert "never free text" in CONVERGENCE
    assert "| item | disposition | owner | reason | quote |" not in STAGES + CONVERGENCE


# 3. One capture manifest
VISUAL = flat(CCT / "references/visual-pass.md")
KEY = "build SHA, reference revision, screen, state, width and zoom"


def test_one_assessment_owns_the_captures_in_one_manifest() -> None:
    for name, text in (("convergence", CONVERGENCE), ("visual-pass", VISUAL), ("ux", UX)):
        assert "verify/shots/manifest.json" in text, name
        assert KEY in text, name
    assert "only the affected cells are captured again" in CONVERGENCE
    assert "stale `qa.md`" in CONVERGENCE


def test_stage_6_lists_the_assessment_once_and_lets_it_dispatch_the_specialists() -> None:
    stage6 = STAGES.split("## Stage 6 — Milestone", 1)[1].split("2a.", 1)[0]
    assert stage6.count("cct:ux-assessment-run") == 1
    assert "Also run `cct:ux-assessment-run`" not in stage6
    assert "dispatches the responsive, accessibility and build QA passes" in stage6


def test_the_answer_names_the_change_and_the_finding_and_no_env_picks_the_evidence() -> None:
    assert "Change <change id>, finding <finding id>: " in STEP4
    assert "SDLC_TRANSCRIPT" not in CONVERGENCE
    assert "latest answer wins" in STEP4


# 7. Tests first that can start before the UI exists
STAGE5 = STAGES.split("## Stage 5 — Build", 1)[1].split("## Records, gates and waiting", 1)[0]


def test_stage_5_starts_from_the_smallest_failing_assertion() -> None:
    assert "smallest failing assertion from the approved fact" in STAGE5
    assert "only after the surface exists" in STAGE5
    assert "live selectors" in STAGE5


def test_stage_5_names_an_executable_runner_not_the_rulebook() -> None:
    assert "`cct:test-e2e-policy` is a rulebook, not a runner" in STAGE5
    assert "`cct:test-e2e-policy` on the feature tags" not in STAGE5


def test_the_builder_writes_the_smallest_failing_assertion_first() -> None:
    assert "smallest failing assertion from the approved fact" in BUILDER


# 8. Fact proof is collected once, keyed, and reused
AUDITOR = flat(CCT / "agents/review-criteria-auditor.md")
STAGE6 = STAGES.split("## Stage 6 — Milestone", 1)[1].split("### Enforcement audit", 1)[0]


def test_builders_return_evidence_keyed_by_fact_tag_and_sha() -> None:
    assert "evidence keyed by fact, tag and tested SHA" in BUILDER
    assert "evidence keyed by fact, tag and tested SHA" in STAGES


def test_the_close_reuses_matching_evidence_and_exercises_only_the_rest() -> None:
    assert "reuses the final-suite evidence of every fact whose tag and tested SHA match" in STAGE6
    assert "only the behaviour no evidence covers and the seams between features" in STAGE6


def test_the_criteria_auditor_gets_an_explicit_criteria_input() -> None:
    assert "verify/ac.json" in STAGE6
    assert "ac.json" in AUDITOR


def test_the_threat_model_is_written_down() -> None:
    assert "protects against a careless or over-eager agent" in CONVERGENCE
    assert "someone with a shell" in CONVERGENCE and "out of scope" in CONVERGENCE
    assert "not a sandbox" in CONVERGENCE

