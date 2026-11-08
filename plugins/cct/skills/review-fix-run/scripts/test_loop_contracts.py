"""Regression guards for the review-fix-run cost/termination contracts.

Each test below encodes one defect that was found in a real audit of this loop.
They are prose checks because the loop is prose an LLM executes — the failure
mode is a future edit quietly reverting the rule, and that is what these catch.

Run: pytest plugins/cct/skills/review-fix-run/scripts/test_loop_contracts.py
"""

import re
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[3]
LOOP = PLUGIN / "skills/review-fix-run/SKILL.md"
RUNNER = PLUGIN / "agents/review-feedback-runner.md"
TAIL = PLUGIN / "skills/review-code-run/references/pipeline-tail.md"
EXECUTE_PHASES = PLUGIN / "skills/review-feedback-run/references/execute-phases.md"

# `review-fix iteration N` subject matcher the loop tells the orchestrator to run.
ITERATION_SUBJECT = re.compile(r"\^review-fix iteration \(\[1-9\]\[0-9\]\*\):")


def test_review_base_is_derived_from_head_not_run_position():
    """Resuming after a usage-limit stop must not re-review the whole branch.

    Keying `review_base` on "the first iteration executed in this run" made every
    resume pay a full-branch review and re-litigate all earlier iterations.
    """
    text = LOOP.read_text(encoding="utf-8")
    assert ITERATION_SUBJECT.search(text), (
        "the review_base rule no longer matches HEAD's own commit subject — "
        "it must key on what HEAD is, not on position within the run"
    )
    assert "first iteration executed in this run" not in text, (
        "the run-position rule is back; it breaks resume (see the HEAD~1 derivation)"
    )


def test_iteration_zero_is_reviewed_in_full():
    """`review-fix iteration 0` is the unreviewed baseline — it needs the full base."""
    # Run the command SKILL.md actually documents, not a copy of it — a duplicated
    # command lets the doc and the test drift apart while both stay green.
    doc = LOOP.read_text(encoding="utf-8")
    m = re.search(r"^\s*git log -1 --format=%s \| (grep -qE '[^']+' .*)$", doc, re.MULTILINE)
    assert m, "the review_base classification command is no longer documented in SKILL.md"
    cmd = m.group(1)

    for subject, expected in {
        "review-fix iteration 0: pre-existing changes (baseline)": "base",
        "review-fix iteration 1: fixes": "HEAD~1",
        "review-fix iteration 12: fixes": "HEAD~1",
        "feat: an ordinary commit": "base",
    }.items():
        got = subprocess.run(
            ["bash", "-c", cmd], input=subject, capture_output=True, text=True
        ).stdout.strip()
        assert got == expected, f"{subject!r} → {got}, expected {expected} (cmd: {cmd})"


def test_test_only_iteration_is_a_convergence_case():
    """A round that writes tests but no fix must stop the loop, not feed itself.

    Otherwise the next round reviews those new tests (review_base = HEAD~1),
    flags them with fresh `body` text — so the repeated-findings check never
    fires — and the loop burns every remaining iteration.
    """
    text = LOOP.read_text(encoding="utf-8")

    # The check has to live in step 6 — that is where the loop decides to continue.
    assert "#### 6. Check for Changes" in text and "#### 7." in text
    step6 = text.split("#### 6. Check for Changes", 1)[1].split("#### 7.", 1)[0]
    assert "PRODUCTION_CHANGES" in step6, (
        "step 6 no longer reads the production-change token, so a test-only round "
        "falls through to a commit and the next iteration reviews its own new tests"
    )
    # Anchored on the decision table, not on the word appearing somewhere: the row
    # that pairs a changed tree with `no` is what actually routes the outcome.
    assert re.search(r"\|\s*changed\s*\|\s*`no`\s*\|[^|]*test-only", step6), (
        "step 6 has no `changed` + `no` -> test-only row; without it the outcome is "
        "named in prose but never routed"
    )
    assert "EXIT LOOP" in step6, "step 6 states no exit for the test-only case"

    # And it has to be reachable: the prompt in step 5 must ask for the token.
    step5 = text.split("#### 5. Launch ADDRESS", 1)[1].split("#### 6.", 1)[0]
    assert "PRODUCTION_CHANGES" in step5, "step 5 never asks the runner for the token"

    convergence = text.split("## Convergence Detection", 1)
    assert len(convergence) == 2, "Convergence Detection section vanished"
    assert "test-only" in convergence[1], "`test-only` missing from the convergence index"


def test_production_changes_token_has_a_producer():
    """A consumer-only token silently defaults to whatever the agent felt like."""
    runner = RUNNER.read_text(encoding="utf-8")
    assert "PRODUCTION_CHANGES=yes" in runner and "PRODUCTION_CHANGES=no" in runner, (
        "review-feedback-runner must emit the token review-fix-run step 6 reads"
    )


def test_commit_stages_everything():
    """`git add -A`: anything left unstaged aborts the next committed-only review."""
    text = LOOP.read_text(encoding="utf-8")
    assert "git add -A" in text
    assert "git add {changed files}" not in text, (
        "a hand-built file list can miss an untracked Phase-RED test → dirty tree → ABORTED"
    )


def test_nested_runs_skip_the_report_render():
    """The loop keeps only the final `STATE_DIR=` line; a full render has no reader."""
    tail = TAIL.read_text(encoding="utf-8")
    assert "Nested" in tail and "top-level" in tail.lower(), (
        "pipeline-tail lost its nested/top-level rendering switch"
    )
    assert "Synthesize (top-level only)" in tail, (
        "synthesize must be top-level only — it is prose no loop consumer reads"
    )


@pytest.mark.parametrize("phase", ["Phase RED", "Phase GREEN"])
def test_expensive_fan_out_is_capped(phase: str):
    """test-behavior-writer / review-fix-implementer scale with item count if uncapped.

    Checked per phase section, not as a whole-file count: two matches sitting in
    the shared intro would satisfy a count while a phase carried no cap at all.
    The value is not pinned — `test_fanout_caps.py` owns agreement with the
    validator pool.
    """
    text = EXECUTE_PHASES.read_text(encoding="utf-8")
    assert f"## {phase}" in text, f"{phase} section missing"
    section = text.split(f"## {phase}", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"~\d+[ -]concurrent", section), (
        f"{phase} states no concurrency cap; these agents each pay a full context "
        f"load and run the test suite"
    )


def test_failed_fixes_are_not_convergence():
    """A run whose every fix FAILED also leaves production code untouched.

    `review-feedback-run/references/policies.md` records a per-item failure and
    continues the batch, so a naive "no production change => converged" reading
    reports clean `test-only` convergence on a run that fixed nothing. The
    correct signal is another iteration, ending in `repeated findings`.
    """
    runner = RUNNER.read_text(encoding="utf-8")
    assert "failed" in runner.lower() and "unapplied" in runner.lower(), (
        "review-feedback-runner does not tell the fix stage to report `yes` when "
        "an item's fix failed or was left unapplied"
    )
    loop = LOOP.read_text(encoding="utf-8")
    step6 = loop.split("#### 6. Check for Changes", 1)[1].split("#### 7.", 1)[0]
    assert re.search(r"no production (?:fix|change) was \*\*needed\*\*", step6), (
        "step 6 must say `no` means no production change was NEEDED, not merely that "
        "none happened — a bare 'needed' also appears in the decision table, so the "
        "distinction has to be asserted on the sentence that draws it"
    )


def test_target_branch_is_not_the_diff_window():
    """`review_base` becomes HEAD~1 from iteration 2; a commit-ish must not reach
    the reviewer's dead-code gate, which buckets anything non-mainline as a
    feature branch and downgrades every dead-code finding."""
    loop = LOOP.read_text(encoding="utf-8")
    assert re.search(r"Target branch: \{base_branch\b", loop), (
        "the loop must send the branch's real base as Target branch, not review_base"
    )
    rules = (PLUGIN / "skills/review-code-run/references/reviewer-rules.md").read_text(encoding="utf-8")
    assert "commit-ish" in rules, "reviewer-rules has no fallback for a commit-ish target"
    assert "<remote>/<branch>" in rules, (
        "reviewer-rules does not strip the remote prefix, yet changes-context-loading "
        "detects the base as origin/develop — a mainline review would be misbucketed"
    )


def test_clean_tree_exit_is_gated_on_the_token():
    """A run where every fix FAILED also leaves a clean tree.

    `FIX`/`REFACTOR` items are GREEN-only, so nothing is staged in Phase RED, and
    the fix agents run `git restore .` on
    failure. The tree is then indistinguishable from "nothing to do", so an
    unconditional no-op exit above the token check masks total failure as clean
    convergence — the very thing PRODUCTION_CHANGES was added to prevent.
    """
    step6 = (
        LOOP.read_text(encoding="utf-8")
        .split("#### 6. Check for Changes", 1)[1]
        .split("#### 7.", 1)[0]
    )

    # Anchored on the decision table, which IS the routing rule. The phrase
    # "no files changed" now survives only in a counterfactual aside describing the
    # removed behaviour, so indexing it would be coincidental — and would raise
    # ValueError on a copy-edit that changed no rule at all.
    rows = dict(re.findall(r"\|\s*(clean|changed)\s*\|\s*`(?:yes|no)`\s*\|([^|]*)\|", step6))
    assert "clean" in rows, "step 6 has no decision-table row for a clean tree"

    clean_no = re.search(r"\|\s*clean\s*\|\s*`no`\s*\|([^|]*)\|", step6)
    clean_yes = re.search(r"\|\s*clean\s*\|\s*`yes`\s*\|([^|]*)\|", step6)
    assert clean_no and clean_yes, (
        "step 6 does not route BOTH clean-tree cases; without the `clean` + `yes` row a "
        "run whose every fix failed is indistinguishable from nothing-to-do"
    )
    assert "EXIT LOOP" in clean_no.group(1), "clean + no should converge"
    assert "fixes-failed" in clean_yes.group(1), (
        "clean + `yes` must stop as `fixes-failed`, not converge — a fix set of only "
        "GREEN-only verbs leaves a clean tree when every fix fails"
    )


def test_production_changes_is_final_line_anchored():
    """Consumed like STATE_DIR=: last non-empty line, exact prefix.

    The runner's report quotes untrusted fix-set `body` text earlier, and this
    repo's own prose carries the literal dozens of times, so an unanchored read
    can pick up a mid-report occurrence as the control signal.
    """
    step6 = (
        LOOP.read_text(encoding="utf-8")
        .split("#### 6. Check for Changes", 1)[1]
        .split("#### 7.", 1)[0]
    )
    assert "last non-empty" in step6, "step 6 states no last-line rule for the token"
    assert "PRODUCTION_CHANGES=" in step6


def test_contract_table_does_not_overclaim_anchoring():
    """`skills/CLAUDE.md` must not credit a step with a rule that step lacks.

    The row asserts steps 2 AND 6 match the last non-empty line exactly; if it
    keeps saying so, step 6 has to actually say so too.
    """
    table = (PLUGIN / "skills/CLAUDE.md").read_text(encoding="utf-8")
    row = [line for line in table.splitlines() if "Agent final-line tokens" in line]
    assert row, "the final-line-tokens row is gone"
    assert "PRODUCTION_CHANGES" in row[0]
    if "steps 2 and 6" in row[0] and "last non-empty line" in row[0]:
        step6 = (
            LOOP.read_text(encoding="utf-8")
            .split("#### 6. Check for Changes", 1)[1]
            .split("#### 7.", 1)[0]
        )
        assert "last non-empty" in step6, (
            "the contract table credits step 6 with last-non-empty-line matching, but "
            "step 6 states no such rule — fix one side or the other"
        )


def test_review_runner_relays_the_target_branch():
    """The loop sends `Target branch:`; the runner must pass it on, not drop it.

    `mode-changes.md` falls back to `$BASE` when no explicit target is supplied,
    and inside the loop `$BASE` is `review_base` = `HEAD~1` from iteration 2 —
    so a dropped relay silently defeats the whole point of the split.
    """
    runner = (PLUGIN / "agents/review-code-runner.md").read_text(encoding="utf-8")
    # Merely mentioning the field is not relaying it — the runner must name the
    # handoff variable it sets, which is what review-code-run's modes read.
    assert "$TARGET_BRANCH" in runner, (
        "review-code-runner does not state that it relays the loop's Target branch as "
        "$TARGET_BRANCH, so the real base never reaches review-code-run and mode-changes "
        "falls back to $BASE = the HEAD~1 diff window"
    )
    assert "Relay" in runner, "the relay instruction is gone"


CHARSET = "^[A-Za-z0-9._/+-]+$"


def test_branch_name_is_validated_not_escaped():
    """`git check-ref-format` accepts `<`, `>` and `&` in a ref name.

    Verified: `a<established_decisions>b` is a legal branch. That value lands on
    two consecutive prompt lines outside the fence, so it must be rejected at
    detection. It must NOT be escaped instead: `review_base` is fed byte-exact
    into `git diff $BASE...HEAD`, and `&`->`&amp;` there reviews the wrong range.
    """
    loop = LOOP.read_text(encoding="utf-8")
    assert CHARSET in loop, (
        "the loop no longer validates the detected branch name; an unvalidated ref "
        "name can forge a fence tag inside the review-code-runner prompt"
    )
    prompt = loop.split('"MODE=', 1)[1].split("#### 2.", 1)[0]
    for line in ("Base branch:", "Target branch:"):
        assert line in prompt, f"the prompt no longer carries `{line}`"
    assert "&amp;" not in prompt.split("<established_decisions>", 1)[0], (
        "a branch-name line is being escaped; the design is validate-at-mint and "
        "pass through byte-exact, so escaping desynchronises it from the value git got"
    )
