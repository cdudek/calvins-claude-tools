"""Regression guards for review-code-run contracts that a real audit found broken.

Two shapes of defect, both silent at runtime, which is why they need a guard.

First: a rule or script needs an input and the only file that could supply it
never does — the reviewer guesses, or GitHub drops a comment with no error.

Second: the posted comment. What a PR author reads is decided by one jq filter
and one layout section, and every failure there lands on somebody else's PR —
a thread over a variable name, an unconfirmed claim phrased as a defect, or a
finding posted without the reason the pipeline already computed.

Run: pytest plugins/cct/skills/review-code-run/scripts/test_review_pr_contracts.py
"""

import json
import re
import subprocess
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
REF = PLUGIN / "skills/review-code-run/references"
CMD = PLUGIN / "skills/review-code-run/references/commands"
SCRIPTS = PLUGIN / "skills/review-code-run/scripts"


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_target_branch_reaches_the_reviewer():
    """`reviewer-rules.md` gates dead-code severity on the review's target branch.

    The spawn template used to pass AXIS/surface/root only, so the gate had no
    input and the reviewer inferred a target — silently, and often wrongly.
    """
    spawn = read(REF / "review-subagent.md")
    assert "Target branch: <$TARGET_BRANCH>" in spawn, (
        "the spawn prompt no longer passes the target branch the dead-code gate needs"
    )
    consumer = read(PLUGIN / "agents/review-code-reviewer.md")
    assert "**Target branch**" in consumer, "review-code-reviewer no longer documents the input"
    rules = read(REF / "reviewer-rules.md")
    assert "`Target branch:`" in rules, (
        "reviewer-rules must name where the value comes from, not leave it to inference"
    )


def test_every_mode_sets_target_branch():
    """A handoff var only one mode sets is a null for the other two."""
    for mode, expected in [
        ("mode-pr.md", "$TARGET_BRANCH"),
        ("mode-changes.md", "$TARGET_BRANCH"),
        ("mode-files.md", "$TARGET_BRANCH"),
    ]:
        assert expected in read(REF / mode), f"{mode} does not set the handoff var"
    for lane in ["lane-deep.md", "lane-max.md"]:
        text = read(REF / lane)
        assert "$TARGET_BRANCH" in text, f"{lane} does not pass the var through to the reviewer"


def test_pr_quick_mints_side_before_posting():
    """`posting-findings.sh` is the only minter of `side`, and pr-quick never runs it.

    A null `DiffSide` is accepted by the GraphQL mutation and the thread is then
    dropped — the review posts with comments missing and no error surfaced.
    """
    text = read(CMD / "pr-quick.md")
    assert "side: RIGHT" in text, "pr-quick posts without minting `side`"
    assert "review-add-thread.sh" in text or "review-posting.md" in text


def test_truncating_diff_command_is_scoped_to_quick():
    """`gh pr diff` truncates on huge PRs; mode-pr says so and builds it locally."""
    text = read(REF / "pr-context-loading.md")
    match = re.search(r"^gh pr diff <pr_number>$", text, re.MULTILINE)
    assert match, "the full-diff command vanished from pr-context-loading"
    preceding = text[: match.start()].rsplit("\n\n", 1)[-1]
    assert "quick" in preceding.lower(), (
        "the unqualified `gh pr diff` is back — pr-deep/pr-max must not run it "
        "(truncation + whole diff in main context); mark it quick-only"
    )


def test_every_branch_mint_site_validates_the_name():
    """The rule lives in `skills/CLAUDE.md`; both minting modes must apply it.

    A ref name reaches a reviewer prompt unescaped by design, so the only thing
    standing between a forged fence tag and the prompt is this check.
    """
    charset = "^[A-Za-z0-9._/+-]+$"
    contract = (PLUGIN / "skills/CLAUDE.md").read_text(encoding="utf-8")
    assert charset in contract, "the canonical branch-name rule is gone from the contract doc"
    for mode in ["changes-context-loading.md", "mode-pr.md"]:
        assert charset in read(REF / mode), (
            f"{mode} mints a branch-name handoff without validating it"
        )
    spawn = read(REF / "review-subagent.md")
    assert "byte-exact" in spawn, (
        "review-subagent no longer states that the target branch is embedded without "
        "escaping — the pairing with mint-time validation is what makes that safe"
    )


def _rows(tmp_path, findings, verdicts):
    """Run the real script. A presence check on the jq source would pass on a
    partial revert, and this filter is the whole gate on what an author reads."""
    f = tmp_path / "findings.json"
    v = tmp_path / "verdicts.json"
    f.write_text(json.dumps({"findings": findings}), encoding="utf-8")
    v.write_text(json.dumps(verdicts), encoding="utf-8")
    out = subprocess.run(
        ["bash", str(SCRIPTS / "posting-findings.sh"), str(f), str(v)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def _post(tmp_path, findings, verdicts):
    return {item["id"] for item in _rows(tmp_path, findings, verdicts)}


def test_only_confirmed_findings_above_nit_are_postable(tmp_path):
    """Three exclusions decide what a PR author is made to read.

    Each one used to be absent, and each failure is silent: a nit becomes a
    thread and a notification over a variable name; an unverifiable claim is
    answered as a defect report; a demoted style call reads as a defect.
    """
    findings = [
        {
            "id": 1,
            "file": "a.rb",
            "line": 3,
            "severity": "critical",
            "dimension": "security",
            "body": "x",
            "confidence": 90,
            "reversibility": "cheap",
        },
        {
            "id": 2,
            "file": "a.rb",
            "line": 9,
            "severity": "suggestion",
            "dimension": "design",
            "body": "x",
            "confidence": 70,
            "reversibility": "entrenches",
        },
        {
            "id": 3,
            "file": "a.rb",
            "line": 12,
            "severity": "nit",
            "dimension": "style",
            "body": "x",
            "confidence": 80,
            "reversibility": "cheap",
        },
        {
            "id": 4,
            "file": "a.rb",
            "line": 20,
            "severity": "warning",
            "dimension": "bug",
            "body": "x",
            "confidence": 60,
            "reversibility": "cheap",
        },
        {
            "id": 5,
            "file": "a.rb",
            "line": 31,
            "severity": "suggestion",
            "dimension": "style",
            "body": "x",
            "confidence": 55,
            "reversibility": "cheap",
            "suppressed_reason": "style",
        },
    ]
    verdicts = [
        {"id": 1, "verdict": "confirmed"},
        {"id": 2, "verdict": "confirmed"},
        {"id": 3, "verdict": "confirmed"},
        {"id": 4, "verdict": "unverifiable"},
        {"id": 5, "verdict": "confirmed"},
    ]
    posted = _post(tmp_path, findings, verdicts)
    assert posted == {1, 2}, (
        f"expected only the confirmed critical and suggestion to be postable, got {posted}: "
        "3 is a nit, 4 is unverifiable, 5 is demoted — none may become a thread"
    )


def test_comment_layout_is_written_down_and_pointed_at():
    """`review-posting.md` posts `body` byte-exact, so the layout has exactly one home.

    Before Section C existed, nothing said what a posted comment contains: the
    reviewer's `body` went to GitHub raw, and `failure_scenario` — the field this
    pipeline requires precisely because reviewers omit the reason — never shipped.
    """
    section = read(REF / "finding-format.md")
    assert "## Section C — the posted comment" in section, "Section C is gone"
    for token in ["🔴", "🟠", "🟡", "`issue`", "`suggestion`", "```suggestion", "`F<id>`"]:
        assert token in section, f"Section C no longer specifies {token}"
    assert "`nit`" in section, "Section C must state that nit never posts"

    for consumer in [
        REF / "review-posting.md",
        REF / "posting-pipeline.md",
        REF / "reconcile-threads.md",
        CMD / "pr-quick.md",
    ]:
        assert "Section C" in read(consumer), (
            f"{consumer.name} composes or forwards a comment body without pointing at "
            "the layout — a second, drifting format starts here"
        )


def test_pr_quick_applies_the_exclusions_it_cannot_inherit():
    """`posting-findings.sh` needs a findings.json that pr-quick never writes.

    So the one mode with no validator is also the one mode where the exclusions
    have to be restated, or they simply do not happen.
    """
    text = read(CMD / "pr-quick.md")
    assert "posting-findings.sh" in text, "pr-quick no longer names the script it cannot run"
    assert re.search(r"[Dd]rop every `nit`", text), "pr-quick no longer drops nits"
    assert "unverified" in text, "pr-quick no longer routes unverified findings off the diff"


def test_the_comment_fields_survive_the_projection(tmp_path):
    """Phase 3 composes Section C from this array and from nothing else.

    `failure_scenario` is the comment's second sentence and `idiomatic_fix` is its
    suggestion block. Drop either from the jq filter and the comment still posts —
    one line, no reason, no fix — which is the defect Section C exists to end.
    Nothing errors on the way, so only this guard catches it.
    """
    row = _rows(
        tmp_path,
        [
            {
                "id": 1,
                "file": "a.rb",
                "line": 3,
                "severity": "critical",
                "dimension": "security",
                "body": "the query string is interpolated unsanitized",
                "failure_scenario": "a query of `%' OR 1=1 --` matches every row",
                "idiomatic_fix": "move the search into a scope on Review",
                "confidence": 90,
                "reversibility": "cheap",
            }
        ],
        [{"id": 1, "verdict": "confirmed"}],
    )[0]
    for field in ["body", "failure_scenario", "idiomatic_fix"]:
        assert row.get(field), (
            f"{field} is gone from the postable projection — the Section C comment "
            "loses its second sentence or its suggestion block, silently"
        )
