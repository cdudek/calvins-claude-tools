"""sdlc_status.py map: milestones, features and stage, read from the files and nothing else."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "templates" / "scripts" / "sdlc_status.py"
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
import sdlc_status  # noqa: E402

BRANCH = "milestone/redesign-r2-1"
GATE = "a" * 40
MOVED = "b" * 40
PASS = f"VERIFY PASS milestone {ID} {GATE}"


def _pr(state: str = "MERGED", head: str = GATE, armed: bool = False, number: int = 7) -> list:
    return [
        {
            "number": number,
            "headRefOid": head,
            "state": state,
            "mergedAt": "2026-11-11T10:00:00Z" if state == "MERGED" else None,
            "autoMergeRequest": {"mergeMethod": "MERGE"} if armed else None,
        }
    ]


def _gh(prs: dict[str, list | None]):
    def gh(root: Path, *args: str):
        return prs.get(args[args.index("--head") + 1], [])

    return gh


def _gate(repo: Path, result: str, scope: str = "milestone") -> None:
    out = repo / "changes" / ID / "verify"
    out.mkdir(exist_ok=True)
    (out / "report.json").write_text(json.dumps({"scope": scope, "id": ID, "result": result}))


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
    assert _goal(repo, {BRANCH: _pr("OPEN")}) == (1, f"GOAL {ID} OPEN pr-7-not-merged-or-armed")


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
    code, line = _goal(repo, {"redesign-r2/1-cart": _pr("OPEN", armed=True)}, "feature", 1)
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
    assert (run.returncode, run.stdout.strip()) == (1, f"GOAL {ID} OPEN gh-unavailable")


def test_goal_cli_refuses_bad_arguments(repo: Path) -> None:
    assert _run(repo, "goal").returncode == 2
    assert _run(repo, "goal", ID, "--feature").returncode == 2
    assert _run(repo, "goal", ID, "--feature", "x").returncode == 2
