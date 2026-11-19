"""Speed B (core): approval artifacts and the milestone graph, evidence at the close, timeouts,
the one change resolver and the states/edges file."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_verify_gate import GATE, ID, _approve, _commit_files, _env, _gate, _git, _last, _milestone_repo, _repo

SKILL = Path(__file__).resolve().parents[1]


def _vg():
    sys.path.insert(0, str(GATE.parent))
    spec = importlib.util.spec_from_file_location("vg_b", GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _plan(repo: Path, rows: str) -> None:
    (repo / "changes" / ID / "plan.md").write_text(
        f"## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n{rows}"
    )
    _git(repo, "commit", "-qam", "plan")


@pytest.mark.parametrize(
    ("rows", "needle"),
    [
        ("| M1 a | F1 | M1 |\n", "M1 needs itself"),
        ("| M1 a | F1 | M2 |\n| M2 b | F1 | M1 |\n", "circular"),
        ("| M1 a | F1 | M7 |\n", "unknown"),
        ("| M1 a | F1 | none |\n| M1 b | F1 | none |\n", "twice"),
    ],
)
def test_approve_refuses_a_milestone_graph_that_cannot_be_built(tmp_path: Path, rows: str, needle: str) -> None:
    repo = _repo(tmp_path, ["true"])
    _plan(repo, rows)
    r = _gate(repo, "approve", ID)
    assert r.returncode == 1 and needle in r.stdout, r.stdout


def test_approve_accepts_a_dag(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    _plan(repo, "| M1 a | F1 | none |\n| M2 b | F1 | M1 |\n| M3 c | F1 | M1, M2 |\n")
    assert _gate(repo, "approve", ID).returncode == 0


@pytest.mark.parametrize("gone", ["facts.md", "plan.md"])
def test_approve_requires_the_facts_and_the_plan(tmp_path: Path, gone: str) -> None:
    repo = _repo(tmp_path, ["true"])
    (repo / "changes" / ID / gone).unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "gone")
    r = _gate(repo, "approve", ID)
    assert r.returncode == 1 and gone in r.stdout


def test_approve_refuses_feature_prs_with_local_milestones_and_a_project_branch(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "delivery": "feature-prs", "milestones": {"merge": "local"}}))
    (repo / "changes" / ID / "decisions.json").write_text(json.dumps({"size": "S", "project": {"slug": "p", "branch": True}}))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "conflicting modes")
    r = _gate(repo, "approve", ID)
    assert r.returncode == 1 and "feature-prs" in r.stdout and "local" in r.stdout


def test_a_strict_milestone_needs_a_findings_file_with_its_converged_line(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    (repo / "changes" / ID / "findings.md").unlink()  # validation.md exists, findings.md does not
    _git(repo, "commit", "-qam", "no findings")
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=not-converged"
    _commit_files(repo, findings_md="## Blocking\n\n- [x] **B1** done\n")  # a file with no Converge section
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=not-converged"
    _commit_files(repo, findings_md="## Converge\n\nConverged: round 1\n")
    assert _last(_gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")


def test_a_check_that_outlives_its_timeout_fails_and_is_named(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [{"name": "slow", "run": "sleep 5", "timeout": 1}])
    _approve(repo)
    r = _gate(repo, "feature", ID)
    assert _last(r) == f"VERIFY FAIL feature {ID} check=slow" and "timed out after 1s" in r.stdout


def test_a_pass_cached_while_the_tree_moved_is_not_reused(tmp_path: Path) -> None:
    mover = "echo x >> moved.txt && git add moved.txt && git -c user.name=t -c user.email=t@t commit -qm moved"
    repo = _repo(tmp_path, [{"name": "mover", "run": mover}])
    _approve(repo)
    assert _last(_gate(repo, "feature", ID)) == f"VERIFY FAIL feature {ID} check=moved"
    _git(repo, "reset", "-q", "--hard", "HEAD~1")  # back to the starting tree
    r = _gate(repo, "feature", ID)
    assert "cached" not in r.stdout, r.stdout


def test_an_origin_whose_default_branch_cannot_be_seen_is_an_environment_handoff(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    _git(repo, "remote", "add", "origin", str(tmp_path / "nowhere.git"))
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "defaultBranch": "master"}))
    # sdlc.json is not locked except its checks; approve was done on the same checks
    _git(repo, "commit", "-qam", "default branch")
    r = _gate(repo, "milestone", ID)
    assert _last(r) == "VERIFY BLOCKED reason=env" and "origin/master" in r.stdout, r.stdout
