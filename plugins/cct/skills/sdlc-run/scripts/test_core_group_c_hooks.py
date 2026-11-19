"""Group C, pr-gate.sh: the final project sync, the one-go hotfix push and the PR tuple (S5, S6, F4)."""

from __future__ import annotations

import json
from pathlib import Path

from test_pr_gate import ID, _commit, _git, _local, _pass, _pass_project, _run, repo  # noqa: F401


def _master_moves(repo: Path) -> None:
    """The default branch advanced after the project branch was cut."""
    _git(repo, "checkout", "-q", "master")
    _commit(repo, "src/other.ts", "x\n")
    _git(repo, "push", "-q", "origin", "master")
    _git(repo, "checkout", "-q", "project/trial")


def test_the_final_project_sync_is_pushed_once_it_passed_the_project_gate_S5(repo: Path) -> None:  # noqa: F811
    _local(repo, None)
    _master_moves(repo)
    push = "git push -u origin project/trial"
    _pass_project(repo)
    r = _run(repo, push)  # a pass, but the default branch is not in it
    assert r.returncode == 2 and "only through milestone PRs" in r.stderr and "VERIFY PASS project" in r.stderr
    _git(repo, "merge", "-q", "--no-edit", "master")
    assert _run(repo, push).returncode == 2  # the pass is for the head before the sync
    _pass_project(repo)
    assert _run(repo, push).returncode == 0
    _commit(repo, "src/late.ts", "late\n")
    assert _run(repo, push).returncode == 2  # one verified push, not an open door


def _hotfix(repo: Path, recorded: bool = True, head: str = "hotfix/trial") -> None:
    _git(repo, "checkout", "-qb", "hotfix/trial", "master")
    sha = _commit(repo, "src/fix.ts", "fix\n")
    if recorded:
        state = repo / "changes" / ID / "state"
        state.mkdir()
        (state / "heads.json").write_text(json.dumps({"hotfix": {"head": head, "base": "master", "sha": sha}}))


def test_a_recorded_hotfix_head_is_pushed_inside_a_one_go_goal_S6(repo: Path) -> None:  # noqa: F811
    _hotfix(repo)
    assert _run(repo, "git push -u origin hotfix/trial", goal=True).returncode == 0


def test_a_hotfix_push_without_its_record_or_after_more_code_stays_refused_S6(repo: Path) -> None:  # noqa: F811
    _hotfix(repo, recorded=False)
    assert _run(repo, "git push -u origin hotfix/trial", goal=True).returncode == 2
    _hotfix_record = repo / "changes" / ID / "state"
    _hotfix_record.mkdir()
    sha = _git(repo, "rev-parse", "HEAD")
    (_hotfix_record / "heads.json").write_text(json.dumps({"hotfix": {"head": "hotfix/trial", "base": "master", "sha": sha}}))
    assert _run(repo, "git push -u origin hotfix/trial", goal=True).returncode == 0
    _commit(repo, "src/more.ts", "more\n")
    assert _run(repo, "git push -u origin hotfix/trial", goal=True).returncode == 2


def test_a_record_for_another_head_or_a_disabled_hotfix_opens_nothing_S6(repo: Path) -> None:  # noqa: F811
    _hotfix(repo, head="hotfix/other")
    assert _run(repo, "git push -u origin hotfix/trial", goal=True).returncode == 2
    _hotfix_ok = repo / "changes" / ID / "state" / "heads.json"
    sha = _git(repo, "rev-parse", "HEAD")
    _hotfix_ok.write_text(json.dumps({"hotfix": {"head": "hotfix/trial", "base": "master", "sha": sha}}))
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "hotfix": False}))
    assert _run(repo, "git push -u origin hotfix/trial", goal=True).returncode == 2


def test_a_milestone_pr_whose_head_cannot_be_resolved_is_refused_F4(repo: Path) -> None:  # noqa: F811
    r = _run(repo, "gh pr create --base master --head milestone/trial-9 --title t --body b")
    assert r.returncode == 2 and "milestone/trial-9" in r.stderr and "cannot" in r.stderr
