"""Group C, pr-gate.sh: the final project sync, the one-go hotfix push and the PR tuple (S5, S6, F4)."""

from __future__ import annotations

import json
from pathlib import Path

from test_pr_gate import ID, _commit, _git, _local, _pass_project, _run


def _master_moves(pr_repo: Path) -> None:
    """The default branch advanced after the project branch was cut."""
    _git(pr_repo, "checkout", "-q", "master")
    _commit(pr_repo, "src/other.ts", "x\n")
    _git(pr_repo, "push", "-q", "origin", "master")
    _git(pr_repo, "checkout", "-q", "project/trial")


def test_the_final_project_sync_is_pushed_once_it_passed_the_project_gate_S5(pr_repo: Path) -> None:
    _local(pr_repo, None)
    _master_moves(pr_repo)
    push = "git push -u origin project/trial"
    _pass_project(pr_repo)
    r = _run(pr_repo, push)  # a pass, but the default branch is not in it
    assert r.returncode == 2 and "only through milestone PRs" in r.stderr and "VERIFY PASS project" in r.stderr
    _git(pr_repo, "merge", "-q", "--no-edit", "master")
    assert _run(pr_repo, push).returncode == 2  # the pass is for the head before the sync
    _pass_project(pr_repo)
    assert _run(pr_repo, push).returncode == 0
    _commit(pr_repo, "src/late.ts", "late\n")
    assert _run(pr_repo, push).returncode == 2  # one verified push, not an open door


def _hotfix(pr_repo: Path, recorded: bool = True, head: str = "hotfix/trial", kind: str = "hotfix", passed: bool = True) -> None:
    _git(pr_repo, "checkout", "-qb", "hotfix/trial", "master")
    sha = _commit(pr_repo, "src/fix.ts", "fix\n")
    change = pr_repo / "changes" / ID
    (change / "decisions.json").write_text(json.dumps({"milestone": {"slug": "trial", "kind": kind}}))
    if passed:
        verify = change / "verify"
        verify.mkdir(exist_ok=True)
        (verify / "report.json").write_text(json.dumps({"scope": "feature", "sha": sha, "result": f"VERIFY PASS feature {ID} {sha}", "change": ID, "owner": "", "format": 3}))
    if recorded:
        state = change / "state"
        state.mkdir(exist_ok=True)
        (state / "heads.json").write_text(json.dumps({"hotfix": {"head": head, "base": "master", "sha": sha}}))


def test_a_recorded_hotfix_head_is_pushed_inside_a_one_go_goal_S6(pr_repo: Path) -> None:
    _hotfix(pr_repo)
    assert _run(pr_repo, "git push -u origin hotfix/trial", goal=True).returncode == 0


def test_a_hotfix_push_without_its_record_or_after_more_code_stays_refused_S6(pr_repo: Path) -> None:
    _hotfix(pr_repo, recorded=False)
    assert _run(pr_repo, "git push -u origin hotfix/trial", goal=True).returncode == 2
    _hotfix_record = pr_repo / "changes" / ID / "state"
    _hotfix_record.mkdir()
    sha = _git(pr_repo, "rev-parse", "HEAD")
    (_hotfix_record / "heads.json").write_text(json.dumps({"hotfix": {"head": "hotfix/trial", "base": "master", "sha": sha}}))
    assert _run(pr_repo, "git push -u origin hotfix/trial", goal=True).returncode == 0
    _commit(pr_repo, "src/more.ts", "more\n")
    assert _run(pr_repo, "git push -u origin hotfix/trial", goal=True).returncode == 2


def test_a_record_for_another_head_or_a_disabled_hotfix_opens_nothing_S6(pr_repo: Path) -> None:
    _hotfix(pr_repo, head="hotfix/other")
    assert _run(pr_repo, "git push -u origin hotfix/trial", goal=True).returncode == 2
    _hotfix_ok = pr_repo / "changes" / ID / "state" / "heads.json"
    sha = _git(pr_repo, "rev-parse", "HEAD")
    _hotfix_ok.write_text(json.dumps({"hotfix": {"head": "hotfix/trial", "base": "master", "sha": sha}}))
    cfg = json.loads((pr_repo / "sdlc.json").read_text())
    (pr_repo / "sdlc.json").write_text(json.dumps({**cfg, "hotfix": False}))
    assert _run(pr_repo, "git push -u origin hotfix/trial", goal=True).returncode == 2


def test_a_milestone_pr_whose_head_cannot_be_resolved_is_refused_F4(pr_repo: Path) -> None:
    r = _run(pr_repo, "gh pr create --base master --head milestone/trial-9 --title t --body b")
    assert r.returncode == 2 and "milestone/trial-9" in r.stderr and "cannot" in r.stderr


def test_a_hotfix_record_without_a_feature_pass_opens_nothing_S6(pr_repo: Path) -> None:
    _hotfix(pr_repo, passed=False)
    assert _run(pr_repo, "git push -u origin hotfix/trial", goal=True).returncode == 2


def test_a_change_that_is_not_a_hotfix_has_no_hotfix_route_S6(pr_repo: Path) -> None:
    _hotfix(pr_repo, kind="new")
    assert _run(pr_repo, "git push -u origin hotfix/trial", goal=True).returncode == 2
