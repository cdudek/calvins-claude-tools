"""sdlc_status.py map: milestones, features and stage, read from the files and nothing else."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "sdlc_status.py"
ID = "2026-10-09-redesign-r2"
ROWS = "\n".join(
    f"| {n} | {ID} | feature {n} | url | {'merged' if n < 3 else 'building' if n == 3 else 'todo'} |"
    for n in range(1, 11)
)


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    change = repo / "changes" / ID
    change.mkdir(parents=True)
    (repo / "docs" / "designs").mkdir(parents=True)
    (repo / "sdlc.json").write_text("{}")
    (repo / "docs" / "designs" / "redesign.md").write_text(
        "# Design: Redesign\n\n## Milestones\n\n- R1 foundations: 2026-10-01-redesign-r1\n"
        f"- R2 editor: {ID}\n- R3 export\n- R4 polish\n"
    )
    (change / "decisions.json").write_text(
        json.dumps(
            {
                "design": "docs/designs/redesign.md",
                "milestone": {"kind": "new", "slug": "redesign-r2"},
            }
        )
    )
    (change / "milestone.md").write_text(
        "---\nmilestone: redesign-r2\n---\n\n## Features\n\n| # | Change | Feature | PR | State |\n"
        f"|---|---|---|---|---|\n{ROWS}\n\n## Done\n"
    )
    (change / "lock.json").write_text("{}")
    subprocess.run(
        ["git", "init", "-q", "-b", "feat/redesign-r2"], cwd=repo, check=True, env=_env()
    )
    return repo


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=_env(),
    )


def test_map_shows_both_levels_and_the_stage(repo: Path) -> None:
    out = _run(repo, "map").stdout
    assert "Redesign  M2 of 4" in out and "2 of 10 merged  ✓✓◐○○○○○○○" in out
    assert "stage  5/7 Build" in out


def test_stage_comes_from_the_files(repo: Path) -> None:
    change = repo / "changes" / ID
    (change / "lock.json").unlink()
    stages = []
    for step in (
        lambda: None,
        lambda: (change / "intent.md").write_text("---\nstatus: approved\n---\n"),
        lambda: (change / "facts.md").write_text("# Facts\n"),
        lambda: (change / "plan.md").write_text("# Plan: Redesign\n"),
        lambda: (change / "lock.json").write_text("{}"),
    ):
        step()
        stages.append(_run(repo, "map").stdout.split("stage  ")[1][:3])
    assert stages == ["1/7", "2/7", "3/7", "4/7", "5/7"]


def test_map_finds_the_only_open_change_off_its_branch(repo: Path) -> None:
    subprocess.run(["git", "checkout", "-q", "-b", "other"], cwd=repo, check=True, env=_env())
    assert "Redesign  M2 of 4" in _run(repo, "map").stdout


def test_map_writes_nothing(repo: Path) -> None:
    before = sorted(p.name for p in (repo / "changes" / ID).iterdir())
    _run(repo, "map")
    assert sorted(p.name for p in (repo / "changes" / ID).iterdir()) == before


def test_the_removed_verbs_are_refused(repo: Path) -> None:
    for verb in ("set", "line", "name"):
        assert _run(repo, verb).returncode == 2


# --- goal: the one line a /goal condition matches --------------------------------------------

sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(SCRIPT.parent.parent / "templates" / "scripts"))
import sdlc_status  # noqa: E402

BRANCH = "milestone/redesign-r2-1"
GATE = "a" * 40
MOVED = "b" * 40
PASS = f"VERIFY PASS milestone {ID} {GATE}"


def _pr(
    state: str = "MERGED",
    head: str = GATE,
    armed: bool = False,
    number: int = 7,
    base: str = "main",
    labels: tuple[str, ...] = (),
) -> list:
    return [
        {
            "number": number,
            "baseRefName": base,
            "labels": [{"name": name} for name in labels],
            "headRefOid": head,
            "state": state,
            "mergedAt": "2026-11-11T10:00:00Z" if state == "MERGED" else None,
            "autoMergeRequest": {"mergeMethod": "MERGE"} if armed else None,
            "labels": [{"name": n} for n in labels],
        }
    ]


def _gh(prs: dict[str, list | None]):
    def gh(root: Path, *args: str):
        return prs.get(args[args.index("--head") + 1], [])

    return gh


def _bound(repo: Path, scope: str, milestone: int | None = None) -> dict:
    """What the gate adds to a report: the change, the owning project and (milestone) its number,
    by default the plan's last milestone."""
    from verify_gate import project_branch  # noqa: PLC0415

    cfg = json.loads((repo / "sdlc.json").read_text()) if (repo / "sdlc.json").exists() else {}
    change = repo / "changes" / ID
    out = {} if scope == "project" else {"change": ID, "owner": project_branch(change, cfg)}
    if scope == "milestone":
        out["milestone"] = milestone or max(sdlc_status.planned(change), 1)
    return out


def _gate(repo: Path, result: str, scope: str = "milestone", milestone: int | None = None, **over) -> None:
    out = repo / "changes" / ID / "verify"
    out.mkdir(exist_ok=True)
    report = {"scope": scope, "id": ID, "result": result, **_bound(repo, scope, milestone), **over}
    if result.split()[1:2] == ["PASS"]:
        report["sha"] = result.split()[-1]
    (out / "report.json").write_text(json.dumps(report))


def _goal(repo: Path, prs, scope: str = "milestone", n: int | None = None):
    return sdlc_status.goal(repo, repo / "changes" / ID, scope, n, gh=_gh(prs))


def test_goal_done_when_the_pr_merged_on_the_gated_head(repo: Path) -> None:
    _gate(repo, PASS)
    code, line = _goal(repo, {BRANCH: _pr()})
    assert (code, line) == (0, f"GOAL {ID} DONE pr=7 state=merged gate={GATE}")


def test_goal_done_when_the_pr_is_open_with_auto_merge_armed(repo: Path) -> None:
    _gate(repo, PASS)
    code, line = _goal(repo, {BRANCH: _pr("OPEN", armed=True)})
    assert (code, line) == (0, f"GOAL {ID} DONE pr=7 state=armed gate={GATE}")


def test_goal_blocked_on_a_blocked_gate(repo: Path) -> None:
    _gate(repo, "VERIFY BLOCKED reason=protected-path")
    code, line = _goal(repo, {BRANCH: _pr()})
    assert (code, line) == (3, f"GOAL {ID} BLOCKED reason=protected-path")


def test_goal_ignores_a_blocked_gate_of_another_scope(repo: Path) -> None:
    _gate(repo, "VERIFY BLOCKED reason=env", scope="feature")
    assert _goal(repo, {BRANCH: _pr()})[1] == f"GOAL {ID} OPEN milestone-gate-pass"


def test_goal_open_without_a_pr(repo: Path) -> None:
    _gate(repo, PASS)
    assert _goal(repo, {}) == (1, f"GOAL {ID} OPEN no-pr:{BRANCH}")


def test_goal_open_when_the_pr_is_neither_merged_nor_armed(repo: Path) -> None:
    _gate(repo, PASS)
    pr = _pr("OPEN", labels=("ship",))  # tiered, labelled: arming is now the next step
    assert _goal(repo, {BRANCH: pr}) == (1, f"GOAL {ID} OPEN pr-7-not-merged-or-armed")


def test_goal_open_without_a_passing_gate(repo: Path) -> None:
    assert _goal(repo, {BRANCH: _pr()}) == (1, f"GOAL {ID} OPEN milestone-gate-pass")
    _gate(repo, f"VERIFY FAIL milestone {ID} check=unit")
    assert _goal(repo, {BRANCH: _pr()})[0] == 1


def test_goal_open_when_the_gate_passed_on_another_head_than_the_pr(repo: Path) -> None:
    _gate(repo, PASS)
    assert _goal(repo, {BRANCH: _pr(head=MOVED)}) == (1, f"GOAL {ID} OPEN gate-sha-not-pr-7-head")


def test_goal_compares_the_pr_head_not_the_local_head(repo: Path) -> None:
    """A record written after the merge moves local HEAD; the PR's head is what the gate passed."""
    _gate(repo, PASS)
    (repo / "archived.md").write_text("moved on\n")
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=_env())
    subprocess.run(["git", *ident, "commit", "-qm", "a"], cwd=repo, check=True, env=_env())
    subprocess.run(["git", *ident, "commit", "-qm", "b", "--allow-empty"], cwd=repo, env=_env())
    assert _goal(repo, {BRANCH: _pr()})[0] == 0


def test_goal_open_on_an_open_record(repo: Path) -> None:
    _gate(repo, PASS)
    change = repo / "changes" / ID
    (change / "findings.md").write_text("## Round 1\n\n- [ ] race in the cart total\n")
    assert _goal(repo, {BRANCH: _pr()}) == (1, f"GOAL {ID} OPEN findings-open")
    (change / "findings.md").write_text("## Round 1\n\n- [x] race in the cart total\n")
    (change / "validation.md").write_text("| fact | verdict |\n|---|---|\n| F1 | not met |\n")
    assert _goal(repo, {BRANCH: _pr()}) == (1, f"GOAL {ID} OPEN validation-not-met")


def test_goal_lists_every_missing_item(repo: Path) -> None:
    (repo / "changes" / ID / "findings.md").write_text("- [ ] open\n")
    assert _goal(repo, {}) == (
        1,
        f"GOAL {ID} OPEN milestone-gate-pass,no-pr:{BRANCH},findings-open",
    )


def test_goal_never_done_when_gh_is_unavailable(repo: Path) -> None:
    _gate(repo, PASS)
    assert _goal(repo, {BRANCH: None}) == (1, f"GOAL {ID} OPEN gh-unavailable")


def test_goal_needs_every_milestone_pr_of_the_plan(repo: Path) -> None:
    (repo / "changes" / ID / "plan.md").write_text(
        "## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n"
        "| M1 a | F1 | none |\n| M2 b | F2 | none |\n"
    )
    _gate(repo, PASS)
    prs = {BRANCH: _pr(number=6), "milestone/redesign-r2-2": _pr(number=7)}
    assert _goal(repo, prs)[1].startswith(f"GOAL {ID} DONE pr=7")
    assert _goal(repo, {BRANCH: _pr(number=6)}) == (
        1,
        f"GOAL {ID} OPEN no-pr:milestone/redesign-r2-2",
    )
    assert _goal(repo, {"milestone/redesign-r2-2": _pr()}, n=2)[0] == 0


def test_goal_feature_reads_the_feature_prs_row_and_a_feature_gate(repo: Path) -> None:
    (repo / "changes" / ID / "plan.md").write_text(
        "## Feature PRs\n\n| # | Feature | Facts | Branch | State |\n|---|---|---|---|---|\n"
        "| 1 | cart | F1 | `redesign-r2/1-cart` | todo |\n"
    )
    _gate(repo, f"VERIFY PASS feature {ID} {GATE}", scope="feature")
    pr = _pr("OPEN", armed=True, base="milestone/redesign-r2")  # a feature goes into its milestone
    code, line = _goal(repo, {"redesign-r2/1-cart": pr}, "feature", 1)
    assert (code, line) == (0, f"GOAL {ID} DONE pr=7 state=armed gate={GATE}")
    assert _goal(repo, {}, "feature", 2) == (1, f"GOAL {ID} OPEN no-branch-for-feature-2")


def test_goal_cli_prints_one_line_and_exits_1_when_gh_fails(repo: Path, tmp_path: Path) -> None:
    _gate(repo, PASS)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "gh").write_text("#!/bin/sh\nexit 1\n")
    (bin_dir / "gh").chmod(0o755)
    path = f"{bin_dir}{os.pathsep}{Path(shutil.which('git') or '/usr/bin/git').parent}"
    run = subprocess.run(
        [sys.executable, str(SCRIPT), "goal", ID],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**_env(), "PATH": path},
    )
    first, second = run.stdout.strip().splitlines()
    assert (run.returncode, first) == (1, f"GOAL {ID} OPEN gh-unavailable")
    assert second.startswith("Blocking: GitHub cannot be reached")


def test_goal_cli_refuses_bad_arguments(repo: Path) -> None:
    assert _run(repo, "goal").returncode == 2
    assert _run(repo, "goal", ID, "--feature").returncode == 2
    assert _run(repo, "goal", ID, "--feature", "x").returncode == 2


# --- goal: the one blocking thing, as a sentence ------------------------------------------------


def test_blocker_names_what_why_who_and_the_exact_step(repo: Path) -> None:
    line = f"GOAL {ID} OPEN milestone-gate-pass,no-pr:{BRANCH}"
    assert sdlc_status.blocker(ID, line) == (
        "Blocking: the milestone gate has not passed, because no VERIFY PASS is recorded for it; "
        f"the agent runs `python3 scripts/verify_gate.py milestone {ID}`."
    )
    assert "gh pr create --head " + BRANCH in sdlc_status.blocker(ID, f"GOAL {ID} OPEN no-pr:{BRANCH}")
    assert sdlc_status.blocker(ID, f"GOAL {ID} OPEN pr-7-not-merged-or-armed") == (
        "Blocking: PR 7 is open without auto-merge, because nothing armed it; "
        "the agent runs `gh pr merge 7 --merge --auto`."
    )
    assert "you run" in sdlc_status.blocker(ID, f"GOAL {ID} BLOCKED reason=protected-path")
    assert sdlc_status.blocker(ID, f"GOAL {ID} DONE pr=7 state=merged gate={GATE}") == ""


def test_goal_never_asks_to_arm_a_closed_or_gated_ask_pr(repo: Path) -> None:
    """3.21.0 (F2): arming comes after the owner's disposition, so a closed PR and an Ask-tier PR
    are named for what they are, and the blocker never recommends `gh pr merge --auto`."""
    _gate(repo, PASS)
    for pr, reason in (
        (_pr("CLOSED"), "pr-7-closed"),
        (_pr("OPEN", labels=("ask",)), "pr-7-awaits-owner"),
    ):
        assert _goal(repo, {BRANCH: pr}) == (1, f"GOAL {ID} OPEN {reason}")
        out = sdlc_status.blocker(ID, f"GOAL {ID} OPEN {reason}")
        assert out.startswith("Blocking: PR 7") and "gh pr merge" not in out and "--auto" not in out


def test_blocker_for_a_feature_names_the_feature_gate_and_its_pr(repo: Path) -> None:
    out = sdlc_status.blocker(ID, f"GOAL {ID} OPEN feature-gate-pass", "feature")
    assert "the feature gate has not passed" in out and f"verify_gate.py feature {ID}" in out
    out = sdlc_status.blocker(ID, f"GOAL {ID} OPEN pr-7-not-merged-or-armed", "feature")
    assert "gh pr merge 7 --squash --auto" in out
    out = sdlc_status.blocker(ID, f"GOAL {ID} OPEN gate-sha-not-pr-7-head", "feature")
    assert "PR 7" in out and f"verify_gate.py feature {ID}" in out


EMITTED = [
    "milestone-gate-pass",
    "feature-gate-pass",
    "no-branch-for-milestone-1",
    "no-branch-for-feature-2",
    f"no-pr:{BRANCH}",
    "pr-7-not-merged-or-armed",
    "pr-7-held",
    "pr-7-awaits-owner",
    "pr-7-awaits-tier",
    "pr-7-closed",
    "gate-sha-not-pr-7-head",
    "gh-unavailable",
    "no-change-folder",
    "findings-open",
    "validation-not-met",
    "not-converged",
]


@pytest.mark.parametrize("scope", ["milestone", "feature"])
def test_every_reason_the_goal_emits_gets_a_real_sentence(scope: str) -> None:
    for reason in EMITTED:
        out = sdlc_status.blocker(ID, f"GOAL {ID} OPEN {reason}", scope)
        assert out.startswith("Blocking: ") and "the goal check lists it" not in out, reason


def test_every_reason_the_gate_blocks_on_gets_a_real_sentence() -> None:
    sys.path.insert(0, str(SCRIPT.parent.parent / "templates" / "scripts"))
    from verify_gate import REASONS

    for reason in sorted(REASONS):
        out = sdlc_status.blocker(ID, f"GOAL {ID} BLOCKED reason={reason}")
        assert out.startswith("Blocking: ") and "the goal check lists it" not in out, reason


def test_blocker_never_recommends_a_repo_local_status_script(repo: Path) -> None:
    for reason in EMITTED + ["no-progress", "attempts", "not-approved"]:
        assert " scripts/sdlc_status.py" not in sdlc_status.blocker(ID, f"GOAL {ID} OPEN {reason}")
    assert "${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py" in sdlc_status.blocker(
        ID, f"GOAL {ID} OPEN no-change-folder"
    )


def test_goal_cli_says_what_blocks_a_goal_without_a_change_folder(repo: Path) -> None:
    out = _run(repo, "goal", "no-such-change").stdout.splitlines()
    assert out[0] == "GOAL no-such-change OPEN no-change-folder"
    assert out[1].startswith("Blocking: there is no change folder") and len(out) == 2


def test_goal_cli_feature_scope_reaches_the_sentence(repo: Path) -> None:
    out = _run(repo, "goal", ID, "--feature", "1").stdout.splitlines()
    assert f"verify_gate.py feature {ID}" in out[1], out


def test_goal_cli_adds_the_sentence_only_when_the_goal_is_not_done(repo: Path) -> None:
    out = _run(repo, "goal", ID).stdout.splitlines()
    assert out[0].startswith(f"GOAL {ID} OPEN") and out[1].startswith("Blocking: ")
    assert len(out) == 2


# --- ids: every id with its meaning and where it is decided ----------------------------------


def test_ids_print_meaning_and_file(repo: Path) -> None:
    change = repo / "changes" / ID
    (change / "intent.md").write_text(
        "| # | Date | Source | Words | Screen | Res |\n|---|---|---|---|---|---|\n"
        '| A1 | 2026-11-18 | chat | "Sort the list by date" | none | none |\n\n'
        "| # | When | I want | So I can | Evidence |\n|---|---|---|---|---|\n"
        "| J1 | I open the list | newest first | find it fast | reported (A1) |\n"
    )
    (change / "facts.md").write_text(
        "- [ ] **F1** (A1; rules none) When the list opens, the system shall sort by date. Tag: `@F1`.\n"
        "- [ ] **N1** (A1) The system shall answer in under 200 ms.\n"
    )
    (change / "questions.md").write_text(
        "- **Q1 (2026-11-18) When to lock the tests?** The plan says lock after feature 1.\n"
        "Later: see B19 and Q1.\n"
    )
    out = _run(repo, "ids", ID).stdout.splitlines()
    assert 'A1   "Sort the list by date"  (intent.md)' in out
    assert (
        "J1   When I open the list, I want newest first, so I can find it fast  (intent.md)" in out
    )
    assert "F1   When the list opens, the system shall sort by date.  (facts.md)" in out
    assert "N1   The system shall answer in under 200 ms.  (facts.md)" in out
    assert "Q1   When to lock the tests?  (questions.md)" in out
    assert out[-1] == "no definition found for: B19"


def test_ids_say_so_when_there_are_none(repo: Path) -> None:
    assert _run(repo, "ids", ID).stdout.strip() == "no ids in this change yet"


# --- readme: the reading map -------------------------------------------------------------------


def test_readme_gives_three_entry_points_and_a_row_per_document(repo: Path) -> None:
    change = repo / "changes" / ID
    (change / "intent.md").write_text("# Intent\n")
    (change / "handover.md").write_text("# Handover\n")
    r = _run(repo, "readme", ID)
    assert r.returncode == 0
    text = (change / "README.md").read_text()
    assert "- **Understand the change:** read [intent.md](intent.md)." in text
    assert (
        "- **Review it:** read facts.md (not written yet), then plan.md (not written yet)." in text
    )
    assert "stage 5/7 Build; read [handover.md](handover.md)." in text
    rows = [ln for ln in text.splitlines() if ln.startswith("| ") and "---" not in ln]
    assert any("What are we building, and why?" in r and r.endswith("| yes |") for r in rows)
    above, below = text.split("## For agents")
    assert "decisions.json" in below and "verify/" in below and "analyze.md" in below
    assert "analyze.md" not in above and "facts.md" in above


def test_readme_is_regenerated_and_never_lists_itself_as_an_id_source(repo: Path) -> None:
    change = repo / "changes" / ID
    _run(repo, "readme", ID)
    first = (change / "README.md").read_text()
    (change / "handover-2.md").write_text("# later\n")
    _run(repo, "readme", ID)
    assert (change / "README.md").read_text() != first
    assert "[handover-2.md](handover-2.md)" in (change / "README.md").read_text()
    assert _run(repo, "ids", ID).stdout.strip() == "no ids in this change yet"


# --- goal in local milestones mode (sdlc.json milestones.merge: "local") ---------------------


def _commit(repo: Path, name: str) -> str:
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    (repo / name).write_text(name)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=_env())
    subprocess.run(["git", *ident, "commit", "-qm", name], cwd=repo, check=True, env=_env())
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, env=_env()
    ).stdout.strip()


def _local_project(repo: Path, merge: str | None = "local") -> None:
    """A project with a branch; the sdlc.json carries `milestones.merge` unless merge is None."""
    (repo / "sdlc.json").write_text(json.dumps({"milestones": {"merge": merge}} if merge else {}))
    decisions = repo / "changes" / ID / "decisions.json"
    data = json.loads(decisions.read_text())
    decisions.write_text(json.dumps({**data, "project": {"slug": "big", "branch": True}}))


def _no_gh(root: Path, *args: str):
    raise AssertionError(f"gh must not be called in local mode: {args}")


def test_goal_local_milestone_is_done_when_the_gate_head_is_in_the_project_branch(
    repo: Path,
) -> None:
    _local_project(repo)
    gate = _commit(repo, "m1.txt")
    subprocess.run(["git", "branch", "project/big"], cwd=repo, check=True, env=_env())
    _gate(repo, f"VERIFY PASS milestone {ID} {gate}")
    code, line = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert (code, line) == (0, f"GOAL {ID} DONE merged=project/big gate={gate}")


def test_goal_local_milestone_is_open_until_it_is_merged_into_the_project(repo: Path) -> None:
    _local_project(repo)
    before = _commit(repo, "base.txt")
    subprocess.run(["git", "branch", "project/big"], cwd=repo, check=True, env=_env())
    gate = _commit(repo, "m1.txt")  # the milestone moved past the project branch
    _gate(repo, f"VERIFY PASS milestone {ID} {gate}")
    want = (1, f"GOAL {ID} OPEN gate-not-merged-into-project/big")
    assert sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh) == want
    assert before != gate
    subprocess.run(["git", "branch", "-D", "project/big"], cwd=repo, check=True, env=_env())
    assert sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh) == want


def test_goal_local_milestone_still_needs_a_gate_pass_and_closed_records(repo: Path) -> None:
    _local_project(repo)
    _commit(repo, "m1.txt")
    subprocess.run(["git", "branch", "project/big"], cwd=repo, check=True, env=_env())
    got = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert got == (1, f"GOAL {ID} OPEN milestone-gate-pass")
    _gate(repo, "VERIFY BLOCKED reason=attempts")
    got = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert got == (3, f"GOAL {ID} BLOCKED reason=attempts")


@pytest.mark.parametrize("merge", [None, "pr"])
def test_goal_without_local_mode_still_wants_the_milestone_pr(
    repo: Path, merge: str | None
) -> None:
    _local_project(repo, merge)
    gate = _commit(repo, "m1.txt")
    subprocess.run(["git", "branch", "project/big"], cwd=repo, check=True, env=_env())
    _gate(repo, f"VERIFY PASS milestone {ID} {gate}")
    assert _goal(repo, {}) == (1, f"GOAL {ID} OPEN no-pr:{BRANCH}")
    assert _goal(repo, {BRANCH: _pr(head=gate, base="project/big")})[0] == 0


def test_goal_local_mode_without_a_project_uses_the_milestone_pr(repo: Path) -> None:
    (repo / "sdlc.json").write_text(json.dumps({"milestones": {"merge": "local"}}))
    _gate(repo, PASS)
    assert _goal(repo, {}) == (1, f"GOAL {ID} OPEN no-pr:{BRANCH}")
    assert _goal(repo, {BRANCH: _pr()})[0] == 0


def _project_gate(repo: Path, result: str) -> None:
    out = repo / ".git" / "sdlc" / "projects" / "big" / "verify"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(
        json.dumps({"scope": "project", "id": "big", "result": result})
    )


PROJECT_BRANCH = "project/big"


def test_goal_project_is_done_when_its_pr_merged_or_armed_on_the_gated_head(repo: Path) -> None:
    _local_project(repo)
    _project_gate(repo, f"VERIFY PASS project big {GATE}")
    for pr, state in ((_pr(), "merged"), (_pr("OPEN", armed=True), "armed")):
        got = _goal(repo, {PROJECT_BRANCH: pr}, "project")
        assert got == (0, f"GOAL {ID} DONE pr=7 state={state} gate={GATE}")


def test_goal_project_open_states(repo: Path) -> None:
    _local_project(repo)
    assert _goal(repo, {}, "project") == (
        1,
        f"GOAL {ID} OPEN project-gate-pass,no-pr:{PROJECT_BRANCH}",
    )
    _project_gate(repo, f"VERIFY PASS project big {GATE}")
    assert _goal(repo, {PROJECT_BRANCH: _pr("OPEN", labels=("ship",))}, "project") == (
        1,
        f"GOAL {ID} OPEN pr-7-not-merged-or-armed",
    )
    assert _goal(repo, {PROJECT_BRANCH: _pr(head=MOVED)}, "project") == (
        1,
        f"GOAL {ID} OPEN gate-sha-not-pr-7-head",
    )
    _project_gate(repo, "VERIFY BLOCKED reason=env")
    assert _goal(repo, {PROJECT_BRANCH: _pr()}, "project") == (3, f"GOAL {ID} BLOCKED reason=env")


def test_goal_project_without_a_project_branch_is_open(repo: Path) -> None:
    assert _goal(repo, {}, "project") == (1, f"GOAL {ID} OPEN project-gate-pass,no-project-branch")


def test_goal_cli_reads_the_project_flag(repo: Path) -> None:
    r = _run(repo, "goal", ID, "--project")
    assert (
        r.returncode == 1
        and r.stdout.splitlines()[0] == f"GOAL {ID} OPEN project-gate-pass,no-project-branch"
    )


def _sh(repo: Path, *args: str) -> str:
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    return subprocess.run(
        ["git", *ident, *args], cwd=repo, check=True, env=_env(), capture_output=True, text=True
    ).stdout.strip()


def test_goal_local_waits_for_every_planned_milestone_F2(repo: Path) -> None:
    """The report is the last gate run only: M1 merged and passed must not finish M2."""
    _local_project(repo)
    (repo / "changes" / ID / "plan.md").write_text(
        "# Plan: R\n\n## Milestones\n\n| # | what |\n|---|---|\n| M1 | a |\n| M2 | b |\n"
    )
    _commit(repo, "base.txt")
    _sh(repo, "branch", "project/big")
    _sh(repo, "checkout", "-qb", "milestone/redesign-r2-1")
    m1 = _commit(repo, "m1.txt")
    _sh(repo, "branch", "-f", "project/big", m1)  # M1 merged
    _sh(repo, "checkout", "-qb", "milestone/redesign-r2-2")
    _commit(repo, "m2.txt")  # M2 built, not merged
    _gate(repo, f"VERIFY PASS milestone {ID} {m1}", milestone=1)
    folder = repo / "changes" / ID
    # M1's report is not M2's pass: it is named missing too
    want = (1, f"GOAL {ID} OPEN milestone-gate-pass,merge-missing:milestone/redesign-r2-2")
    assert sdlc_status.goal(repo, folder, "milestone", 2, gh=_no_gh) == want
    assert sdlc_status.goal(repo, folder, "milestone", None, gh=_no_gh) == want
    assert sdlc_status.goal(repo, folder, "milestone", 1, gh=_no_gh)[0] == 0


def _receipt(repo: Path, n: int, sha: str, verdict: str = "PASS", change: str = ID) -> None:
    out = repo / "changes" / ID / "verify"
    out.mkdir(exist_ok=True)
    result = f"VERIFY {verdict} milestone {change} {sha}"
    receipt = {"scope": "milestone", "change": change, "result": result, "sha": sha}
    receipt.update(_bound(repo, "milestone", n))
    receipt["change"] = change
    (out / f"milestone-{n}.json").write_text(json.dumps(receipt))


def _two_milestones(repo: Path) -> tuple[str, str]:
    """M1 merged into project/big; M2 built on its own branch, not merged."""
    _local_project(repo)
    (repo / "changes" / ID / "plan.md").write_text(
        "# Plan: R\n\n## Milestones\n\n| # | what |\n|---|---|\n| M1 | a |\n| M2 | b |\n"
    )
    _commit(repo, "base.txt")
    _sh(repo, "branch", "project/big")
    _sh(repo, "checkout", "-qb", "milestone/redesign-r2-1")
    m1 = _commit(repo, "m1.txt")
    _sh(repo, "branch", "-f", "project/big", m1)
    _sh(repo, "checkout", "-qb", "milestone/redesign-r2-2")
    return m1, _commit(repo, "m2.txt")


def test_goal_local_milestone_is_done_by_its_receipt_after_the_branch_is_deleted(
    repo: Path,
) -> None:
    m1, m2 = _two_milestones(repo)
    _sh(repo, "branch", "-f", "project/big", m2)
    _sh(repo, "checkout", "-q", "project/big")
    _sh(repo, "branch", "-D", "milestone/redesign-r2-1", "milestone/redesign-r2-2")
    _receipt(repo, 1, m1)
    _receipt(repo, 2, m2)
    _gate(repo, f"VERIFY PASS milestone {ID} {m2}")
    got = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert got == (0, f"GOAL {ID} DONE merged=project/big gate={m2}")


def test_goal_local_names_the_milestone_with_no_receipt(repo: Path) -> None:
    m1, _ = _two_milestones(repo)
    _sh(repo, "checkout", "-q", "project/big")
    _sh(repo, "branch", "-D", "milestone/redesign-r2-1", "milestone/redesign-r2-2")
    _receipt(repo, 1, m1)
    _gate(repo, f"VERIFY PASS milestone {ID} {m1}")
    got = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert got == (1, f"GOAL {ID} OPEN merge-missing:milestone/redesign-r2-2")
    assert "verify_gate.py milestone" in sdlc_status.blocker(ID, got[1])


def test_goal_local_receipt_whose_head_is_not_in_the_project_branch_is_open(repo: Path) -> None:
    m1, m2 = _two_milestones(repo)
    _receipt(repo, 1, m1)
    _receipt(repo, 2, m2)  # M2 passed its gate but never merged
    _gate(repo, f"VERIFY PASS milestone {ID} {m1}")
    got = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert got == (1, f"GOAL {ID} OPEN receipt-not-merged:2")


def test_goal_local_receipt_copied_from_another_milestone_is_rejected(repo: Path) -> None:
    m1, m2 = _two_milestones(repo)
    _sh(repo, "branch", "-f", "project/big", m2)
    _sh(repo, "checkout", "-q", "project/big")
    _sh(repo, "branch", "-D", "milestone/redesign-r2-1", "milestone/redesign-r2-2")
    _receipt(repo, 1, m1)
    out = repo / "changes" / ID / "verify"
    (out / "milestone-2.json").write_text((out / "milestone-1.json").read_text())  # M1's, as M2's
    _gate(repo, f"VERIFY PASS milestone {ID} {m2}")
    got = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert got == (1, f"GOAL {ID} OPEN receipt-not-merged:2")


def test_goal_local_receipt_for_another_change_is_rejected(repo: Path) -> None:
    m1, m2 = _two_milestones(repo)
    _sh(repo, "branch", "-f", "project/big", m2)
    _sh(repo, "checkout", "-q", "project/big")
    _sh(repo, "branch", "-D", "milestone/redesign-r2-1", "milestone/redesign-r2-2")
    _receipt(repo, 1, m1)
    _receipt(repo, 2, m2, change="2026-01-01-other")
    _gate(repo, f"VERIFY PASS milestone {ID} {m2}")
    got = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert got == (1, f"GOAL {ID} OPEN receipt-not-merged:2")


def test_goal_local_receipt_needs_the_branch_ancestry_while_the_branch_exists(repo: Path) -> None:
    m1, m2 = _two_milestones(repo)
    _sh(repo, "checkout", "-q", "milestone/redesign-r2-1")
    _sh(repo, "branch", "-f", "project/big", m1)
    _receipt(repo, 1, m1)
    _receipt(repo, 2, m1)  # a valid-looking receipt, but milestone/redesign-r2-2 is not merged
    _gate(repo, f"VERIFY PASS milestone {ID} {m1}")
    got = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert got == (1, f"GOAL {ID} OPEN merge-missing:milestone/redesign-r2-2")


def test_goal_project_pr_must_target_the_default_branch_F11(repo: Path) -> None:
    _local_project(repo)
    (repo / "sdlc.json").write_text(
        json.dumps({"defaultBranch": "main", "milestones": {"merge": "local"}})
    )
    _project_gate(repo, f"VERIFY PASS project big {GATE}")
    wrong = [{**_pr()[0], "baseRefName": "project/other"}]
    got = _goal(repo, {PROJECT_BRANCH: wrong}, "project")
    assert got == (1, f"GOAL {ID} OPEN pr-7-wrong-base")
    assert _goal(repo, {PROJECT_BRANCH: _pr()}, "project")[0] == 0


def test_goal_accepts_a_records_only_commit_after_the_gate_F10(repo: Path) -> None:
    _gate(repo, PASS.replace(GATE, base := _commit(repo, "code.txt")))
    (repo / "changes" / "archive").mkdir()
    head = _commit(repo, "changes/archive/moved.md")
    assert _goal(repo, {BRANCH: _pr(head=head)})[0] == 0
    late = _commit(repo, "more-code.txt")
    assert _goal(repo, {BRANCH: _pr(head=late)}) == (
        1,
        f"GOAL {ID} OPEN gate-sha-not-pr-7-head",
    )
    assert base != head


def test_goal_finds_an_archived_change_by_id_F10(repo: Path) -> None:
    folder = repo / "changes"
    (folder / "archive" / "2026" / "2026-11").mkdir(parents=True)
    (folder / ID).rename(folder / "archive" / "2026" / "2026-11" / ID)
    got = _run(repo, "goal", ID)
    assert "no-change-folder" not in got.stdout


def test_readme_refuses_paths_outside_the_changes_folder(repo: Path) -> None:
    (repo / "README.md").write_text("project readme\n")
    for bad in ("..", "../..", str(repo), "archive", "does-not-exist"):
        r = _run(repo, "readme", bad)
        assert r.returncode == 2, bad
    assert (repo / "README.md").read_text() == "project readme\n"
    assert not (repo / "changes" / "README.md").exists()


def test_readme_replaces_only_a_generated_readme(repo: Path) -> None:
    readme = repo / "changes" / ID / "README.md"
    readme.write_text("# Written by hand\n")
    r = _run(repo, "readme", ID)
    assert r.returncode == 2 and "not generated" in r.stdout
    assert readme.read_text() == "# Written by hand\n"
    readme.unlink()
    assert _run(repo, "readme", ID).returncode == 0
    (repo / "changes" / ID / "handover.md").write_text("# h\n")
    assert _run(repo, "readme", ID).returncode == 0
    assert "handover.md" in readme.read_text()


def test_readme_rewrites_nothing_when_the_content_is_the_same(repo: Path) -> None:
    readme = repo / "changes" / ID / "README.md"
    _run(repo, "readme", ID)
    os.utime(readme, (1, 1))
    r = _run(repo, "readme", ID)
    assert r.returncode == 0 and "unchanged" in r.stdout
    assert readme.stat().st_mtime == 1


# --- reading map and glossary: the real folder, the named column ---------------------------------


def test_glossary_reads_the_finding_and_challenge_columns_not_the_longest_cell(repo: Path) -> None:
    change = repo / "changes" / ID
    long_where = "plan.md ## Approach, the paragraph that starts with the export and goes on"
    (change / "analyze.md").write_text(
        "| ID | Severity | Pass | Where | Finding | Status |\n|---|---|---|---|---|---|\n"
        f"| X1 | HIGH | coverage | {long_where} | The plan misses the export step. | open |\n"
    )
    (change / "challenge.md").write_text(
        "| ID | Severity | Lens | Where | Challenge | Status |\n|---|---|---|---|---|---|\n"
        f"| H1 | HIGH | simpler | {long_where} | A cron job would do. | answered, see plan |\n"
    )
    (change / "plan.md").write_text("Because (X1) and (H1) we wait.\n")
    out = _run(repo, "ids", ID).stdout.splitlines()
    assert "X1   The plan misses the export step.  (analyze.md)" in out
    assert "H1   A cron job would do.  (challenge.md)" in out


def test_readme_lists_the_standard_spec_files_and_names_every_other_file(repo: Path) -> None:
    change = repo / "changes" / ID
    (change / "spec").mkdir()
    for name in ("brief", "ia", "interaction", "sitemap"):
        (change / "spec" / f"{name}.md").write_text("# x\n")
    (change / "notes.md").write_text("# mine\n")
    (change / "spec" / "extra.md").write_text("# mine\n")
    (change / "verify").mkdir()
    (change / "verify" / "report.json").write_text("{}")
    _run(repo, "readme", ID)
    text = (change / "README.md").read_text()
    for name in ("brief", "ia", "interaction", "sitemap"):
        assert f"[spec/{name}.md](spec/{name}.md)" in text
    other = text.split("## Other files in this folder")[1]
    assert "[notes.md](notes.md)" in other and "[spec/extra.md](spec/extra.md)" in other
    assert "spec/brief.md" not in other and "report.json" not in other


@pytest.mark.parametrize(
    ("names", "latest"),
    [
        (["handover.md", "handover-2.md"], "handover-2.md"),
        (["handover-2.md", "handover-10.md", "handover-9.md"], "handover-10.md"),
        (["handover-2026-11-20.md", "handover-2026-11-18.md", "handover-3.md"], "handover-2026-11-20.md"),
    ],
)
def test_readme_points_at_the_latest_handover(repo: Path, names: list[str], latest: str) -> None:
    change = repo / "changes" / ID
    for n in names:
        (change / n).write_text("# h\n")
    _run(repo, "readme", ID)
    assert f"read [{latest}]({latest})." in (change / "README.md").read_text()


def test_the_milestone_report_template_links_the_glossary() -> None:
    template = SCRIPT.parent.parent / "templates" / "change" / "milestone.md"
    assert "sdlc_status.py ids" in template.read_text()


# --- Review finding 8: an Ask PR is never DONE before the owner's acceptance; Hold blocks ------


def _owner(repo: Path, tmp_path: Path, key: str, label: str, monkeypatch, n: int = 1) -> None:
    """The owner's answer to `Change <id>, finding <key>: ...` in the transcript Claude Code keeps."""
    import datetime as dt
    import re

    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    folder = home / ".claude/projects" / re.sub(r"[^A-Za-z0-9]", "-", str(repo.resolve()))
    folder.mkdir(parents=True, exist_ok=True)
    q = f"Change {ID}, finding {key}: accept the milestone?"
    stamp = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=n)).isoformat()
    rows = [
        {"type": "assistant", "timestamp": stamp, "message": {"content": [{
            "type": "tool_use", "id": f"t{n}", "name": "AskUserQuestion",
            "input": {"questions": [{"question": q, "options": [{"label": "Accept milestone"}, {"label": "Hold"}]}]}}]}},
        {"type": "user", "timestamp": stamp, "toolUseResult": {"answers": {q: label}},
         "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{n}", "content": "ok"}]}},
    ]  # fmt: skip
    with (folder / "session.jsonl").open("a") as out:
        out.write("".join(json.dumps(r) + "\n" for r in rows))


@pytest.mark.parametrize("armed", [False, True])
def test_an_ask_pr_armed_or_not_is_never_done_without_the_owners_acceptance(
    repo: Path, tmp_path: Path, monkeypatch, armed: bool
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    _gate(repo, PASS)
    pr = _pr("OPEN", armed=armed, labels=("ask",))
    assert _goal(repo, {BRANCH: pr}) == (1, f"GOAL {ID} OPEN pr-7-awaits-owner")
    _owner(repo, tmp_path, "PR7", "Accept milestone", monkeypatch)
    sys.modules["marks"]._ANSWERS.clear()  # one process per call in real use; this test spans two
    assert _goal(repo, {BRANCH: _pr("OPEN", armed=True, labels=("ask",))})[0] == 0


def test_a_recorded_hold_blocks_done_and_arming(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _gate(repo, PASS)
    _owner(repo, tmp_path, "PR7", "Hold", monkeypatch)
    for pr in (_pr("OPEN", armed=True, labels=("ask",)), _pr("OPEN", labels=("ask",))):  # the transcript is read for ask PRs
        assert _goal(repo, {BRANCH: pr}) == (1, f"GOAL {ID} OPEN pr-7-held")
    for pr in (_pr("OPEN", armed=True, labels=("ship", "hold")), _pr("OPEN", labels=("show", "hold"))):  # others: the label
        assert _goal(repo, {BRANCH: pr}) == (1, f"GOAL {ID} OPEN pr-7-held")
    assert "nothing arms it" in sdlc_status.blocker(ID, f"GOAL {ID} OPEN pr-7-held")
    assert "gh pr merge" not in sdlc_status.blocker(ID, f"GOAL {ID} OPEN pr-7-held")


def test_status_never_recommends_arming_before_the_tier_label_exists(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    _gate(repo, PASS)
    flow = repo / ".github" / "workflows"  # the tier workflow is what sets the label
    flow.mkdir(parents=True)
    (flow / "ship-show-ask.yml").write_text("name: tier\n")
    assert _goal(repo, {BRANCH: _pr("OPEN")}) == (1, f"GOAL {ID} OPEN pr-7-awaits-tier")
    out = sdlc_status.blocker(ID, f"GOAL {ID} OPEN pr-7-awaits-tier")
    assert "gh pr merge" not in out and "tier label" in out
    assert _goal(repo, {BRANCH: _pr("OPEN", labels=("ship",))}) == (
        1, f"GOAL {ID} OPEN pr-7-awaits-workflow"
    )  # fmt: skip
    (flow / "ship-show-ask.yml").unlink()  # no workflow: nothing sets a label, the agent arms it
    assert _goal(repo, {BRANCH: _pr("OPEN")}) == (1, f"GOAL {ID} OPEN pr-7-not-merged-or-armed")
    (repo / "sdlc.json").write_text(json.dumps({"tiers": False}))
    assert _goal(repo, {BRANCH: _pr("OPEN")}) == (1, f"GOAL {ID} OPEN pr-7-not-merged-or-armed")


# 3.20.1 (review findings 1, 2, 5, 6).
def test_goal_wants_the_exact_parent_as_the_base_of_every_scope_F1(repo: Path) -> None:
    _local_project(repo, "pr")  # the milestone belongs to project/big
    gate = _commit(repo, "m1.txt")
    _sh(repo, "branch", "project/big")
    _gate(repo, f"VERIFY PASS milestone {ID} {gate}")
    got = _goal(repo, {BRANCH: _pr(head=gate)})  # GitHub chose the default branch
    assert got == (1, f"GOAL {ID} OPEN pr-7-wrong-base")
    assert "gh pr edit 7 --base project/big" in sdlc_status.blocker(ID, got[1], "milestone", "project/big")
    assert _goal(repo, {BRANCH: _pr(head=gate, base="project/big")})[0] == 0


def test_the_missing_pr_instruction_carries_the_exact_base_F1(repo: Path) -> None:
    _local_project(repo, "pr")
    sentence = sdlc_status.blocker(ID, f"GOAL {ID} OPEN no-pr:{BRANCH}", "milestone", "project/big")
    assert f"gh pr create --head {BRANCH} --base project/big --fill" in sentence
    assert sdlc_status.parent_of(repo / "changes" / ID, {"defaultBranch": "main"}, "project") == "main"
    feature = sdlc_status.parent_of(repo / "changes" / ID, {}, "feature", "redesign-r2/1-cart")
    assert feature == "milestone/redesign-r2"
    assert sdlc_status.parent_of(repo / "changes" / ID, {}, "feature", "hotfix/x") == "main"


def _open_pr_goal(repo: Path, cfg: dict, labels: tuple[str, ...], base: str = "main") -> str:
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    _gate(repo, PASS)
    prs = {BRANCH: _pr("OPEN", labels=labels, base=base)}
    return _goal(repo, prs)[1].rsplit(" ", 1)[1]


def test_an_unarmed_ask_pr_waits_for_a_person_not_for_an_arm_command_F2(repo: Path) -> None:
    code = _open_pr_goal(repo, {}, ("ask",))  # askGatesMerge defaults to on
    assert code == "pr-7-awaits-owner"
    sentence = sdlc_status.blocker(ID, f"GOAL {ID} OPEN {code}")
    assert "gh pr merge" not in sentence and "AskUserQuestion" in sentence


def test_ask_that_does_not_gate_the_merge_is_left_to_the_workflow_F2(repo: Path) -> None:
    flow = repo / ".github" / "workflows"
    flow.mkdir(parents=True)
    (flow / "ship-show-ask.yml").write_text("name: tier\n")
    assert _open_pr_goal(repo, {"askGatesMerge": False}, ("ask",)) == "pr-7-awaits-workflow"
    sentence = sdlc_status.blocker(ID, f"GOAL {ID} OPEN pr-7-awaits-workflow")
    assert "gh pr merge" not in sentence


def test_an_unarmed_pr_in_a_repo_without_the_workflow_is_armed_with_merge_F2(repo: Path) -> None:
    assert _open_pr_goal(repo, {}, ()) == "pr-7-not-merged-or-armed"
    for scope, flag in (("milestone", "--merge"), ("project", "--merge"), ("feature", "--squash")):
        sentence = sdlc_status.blocker(ID, f"GOAL {ID} OPEN pr-7-not-merged-or-armed", scope)
        assert f"gh pr merge 7 {flag} --auto" in sentence


def test_goal_honours_the_milestone_branch_prefix_F5(repo: Path) -> None:
    _local_project(repo)
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["milestones"]["branchPrefix"] = "ms/"
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    (repo / "changes" / ID / "plan.md").write_text(
        "# Plan: R\n\n## Milestones\n\n| # | what |\n|---|---|\n| M1 | a |\n"
    )
    _commit(repo, "base.txt")
    _sh(repo, "branch", "project/big")
    _sh(repo, "checkout", "-qb", "ms/redesign-r2-1")
    m1 = _commit(repo, "m1.txt")
    _sh(repo, "branch", "-f", "project/big", m1)
    _gate(repo, f"VERIFY PASS milestone {ID} {m1}")  # legacy: no receipt
    got = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert got == (0, f"GOAL {ID} DONE merged=project/big gate={m1}")


def test_goal_refuses_a_locked_input_edited_after_the_gate_F6(repo: Path) -> None:
    (repo / "changes" / ID / "facts.md").write_text("F1 the first\n")
    gated = _commit(repo, "code.txt")
    _gate(repo, f"VERIFY PASS milestone {ID} {gated}")
    (repo / "changes" / ID / "facts.md").write_text("F1 something easier\n")
    head = _commit(repo, f"changes/{ID}/handover.md")
    assert _goal(repo, {BRANCH: _pr(head=head)}) == (1, f"GOAL {ID} OPEN gate-sha-not-pr-7-head")


def test_a_live_file_and_its_archive_copy_void_the_pass(repo: Path) -> None:
    # changes/<id>/facts.md and changes/archive/<id>/facts.md fold onto one key. Before the fix the
    # unchanged archive copy overwrote the live one, so an edit to the locked live file went unseen.
    sys.path.insert(0, str(SCRIPT.parent.parent / "templates" / "hooks"))
    import pass_proof

    archived = repo / "changes" / "archive" / ID / "facts.md"
    archived.parent.mkdir(parents=True)
    for f in (repo / "changes" / ID / "facts.md", archived):
        f.write_text("F1 the first\n")
    _commit(repo, f"changes/archive/{ID}/facts.md")
    gated = _commit(repo, "code.txt")
    (repo / "changes" / ID / "facts.md").write_text("F1 something easier\n")
    head = _commit(repo, f"changes/{ID}/facts.md")
    assert pass_proof.proves(repo, "changes", gated, head) is False


# --- 3.20.2: round-2 review (findings 5, 6, H2, H3, M3) --------------------------------------
M2_BRANCH = "milestone/redesign-r2-2"
SHA2 = "c" * 40


def _plan(repo: Path, milestones: int = 2) -> None:
    rows = "".join(f"| M{i} | m |\n" for i in range(1, milestones + 1))
    (repo / "changes" / ID / "plan.md").write_text(
        f"# Plan: R\n\n## Milestones\n\n| # | what |\n|---|---|\n{rows}"
    )


def test_a_wrong_base_comes_before_the_arming_remedy_H2(repo: Path) -> None:
    _gate(repo, PASS)
    code, line = _goal(repo, {BRANCH: _pr("OPEN", base="project/other")})
    assert code == 1 and line.split("OPEN ")[1].split(",")[0] == "pr-7-wrong-base"
    sentence = sdlc_status.blocker(ID, line, "milestone", "main")
    assert "gh pr edit 7 --base main" in sentence and "gh pr merge" not in sentence


def test_a_wrong_base_hotfix_pr_is_told_the_default_branch_M3(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "changes" / ID / "plan.md").write_text(
        "# Plan: R\n\n## Feature PRs\n\n| # | change | feature | branch |\n|---|---|---|---|\n"
        "| 1 | x | y | hotfix/x |\n"
    )
    _gate(repo, f"VERIFY PASS feature {ID} {GATE}", scope="feature")
    pr = _pr("OPEN", base="milestone/redesign-r2")
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "gh").write_text(f"#!/bin/sh\necho '{json.dumps(pr)}'\n")
    (fake / "gh").chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.chdir(repo)
    assert sdlc_status.goal_main([ID, "--feature", "1"]) == 1
    out = capsys.readouterr().out
    assert "gh pr edit 7 --base main" in out and "gh pr merge" not in out




def _stale_receipts(repo: Path, verdict: str, result: str) -> Path:
    """Receipt files a 3.20.1-3.20.4 gate left in the git dir: 3.20.5 never reads them."""
    common = Path(_sh(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    out = common / "sdlc" / "receipts" / ID
    out.mkdir(parents=True)
    (out / ".first").write_text("2026-01-01T00:00:00+00:00")
    record = {"scope": "milestone", "milestone": 1, "change": ID, "sha": GATE, "verdict": verdict, "result": result}
    (out / "milestone-1.json").write_text(json.dumps(record))
    (out / "garbage.json").write_text("not json")
    return out


def test_a_receipt_file_in_the_git_dir_neither_grants_nor_blocks_a_goal_3_20_5(repo: Path) -> None:
    _stale_receipts(repo, "pass", PASS)
    assert _goal(repo, {BRANCH: _pr()}) == (1, f"GOAL {ID} OPEN milestone-gate-pass")  # no report: not done
    _gate(repo, PASS)
    assert _goal(repo, {BRANCH: _pr()}) == (0, f"GOAL {ID} DONE pr=7 state=merged gate={GATE}")


def test_a_failed_receipt_file_does_not_undo_a_passing_report_3_20_5(repo: Path) -> None:
    _stale_receipts(repo, "fail", f"VERIFY FAIL milestone {ID} check=unit")
    _gate(repo, PASS)
    assert _goal(repo, {BRANCH: _pr()}) == (0, f"GOAL {ID} DONE pr=7 state=merged gate={GATE}")


def test_a_report_gated_as_another_milestone_is_no_pass_3_20_5(repo: Path) -> None:
    _plan(repo, 2)
    _gate(repo, PASS, milestone=1)
    prs = {"milestone/redesign-r2-1": _pr(), "milestone/redesign-r2-2": _pr(number=8)}
    assert "milestone-gate-pass" in _goal(repo, prs)[1]  # the goal's last milestone is 2
    assert "milestone-gate-pass" in _goal(repo, prs, n=2)[1]
    assert "milestone-gate-pass" not in _goal(repo, prs, n=1)[1]


@pytest.mark.parametrize("dropped", ["change", "milestone", "owner"])
def test_a_report_without_its_bindings_is_no_pass_3_20_5(repo: Path, dropped: str) -> None:
    _gate(repo, PASS)
    path = repo / "changes" / ID / "verify" / "report.json"
    data = json.loads(path.read_text())
    path.write_text(json.dumps({k: v for k, v in data.items() if k != dropped}))
    assert _goal(repo, {BRANCH: _pr()}) == (1, f"GOAL {ID} OPEN milestone-gate-pass")


def test_a_report_gated_for_another_project_is_no_pass_3_20_5(repo: Path) -> None:
    _gate(repo, PASS, owner="project/elsewhere")
    assert _goal(repo, {BRANCH: _pr()}) == (1, f"GOAL {ID} OPEN milestone-gate-pass")


def test_a_local_receipt_for_another_project_or_moved_tip_is_not_done_3_20_5(repo: Path) -> None:
    m1, m2 = _two_milestones(repo)
    _sh(repo, "branch", "-f", "project/big", m2)
    _receipt(repo, 1, m1)
    _receipt(repo, 2, m2)
    _sh(repo, "checkout", "-q", "project/big")
    path = repo / "changes" / ID / "verify" / "milestone-2.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), "owner": "project/elsewhere"}))
    got = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert got[0] == 1 and "receipt-not-merged:2" in got[1]
    _receipt(repo, 2, m2)
    _sh(repo, "checkout", "-q", "milestone/redesign-r2-2")
    (repo / "src.py").write_text("moved\n")  # code after the gate, branch tip still inside project/big? no
    _sh(repo, "add", ".")
    _sh(repo, "commit", "-qm", "code after the gate")
    _sh(repo, "branch", "-f", "project/big", "milestone/redesign-r2-2")
    got = sdlc_status.goal(repo, repo / "changes" / ID, "milestone", None, gh=_no_gh)
    assert got[0] == 1 and "gate-sha-not-tip:milestone/redesign-r2-2" in got[1]


# --- a kept older gate never writes change/owner/milestone: its reports are read the old way ----


def _repo_gate(repo: Path, text: str) -> None:
    (repo / "scripts").mkdir(exist_ok=True)
    (repo / "scripts" / "verify_gate.py").write_text(text)


def _strip_bindings(repo: Path) -> None:
    _gate(repo, PASS)
    path = repo / "changes" / ID / "verify" / "report.json"
    data = json.loads(path.read_text())
    path.write_text(json.dumps({k: v for k, v in data.items() if k not in ("change", "milestone", "owner")}))


def test_a_report_from_a_kept_older_gate_is_read_the_old_way(repo: Path) -> None:
    _repo_gate(repo, "def finish(report):\n    report['result'] = 'x'\n")  # a gate that never binds
    _strip_bindings(repo)
    assert _goal(repo, {BRANCH: _pr()})[0] == 0


@pytest.mark.parametrize(
    "gate",
    [
        "report['change'], report['owner'] = a, b\n",
        'report["owner"] = project_branch(change, cfg)\n',
        "WRITES_BINDINGS = True  # report names change, owner, milestone\n",
    ],
)
def test_the_bindings_are_required_when_the_installed_gate_writes_them(repo: Path, gate: str) -> None:
    _repo_gate(repo, gate)
    _strip_bindings(repo)
    assert _goal(repo, {BRANCH: _pr()}) == (1, f"GOAL {ID} OPEN milestone-gate-pass")
