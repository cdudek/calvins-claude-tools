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


@pytest.mark.parametrize("layout", ["x", "archive/x", "archive/2026/2026-11/x"])
def test_one_resolver_finds_a_change_in_every_layout_and_none_once_it_is_removed(tmp_path: Path, layout: str) -> None:
    sys.path.insert(0, str(SKILL / "templates/hooks"))
    import pass_proof

    changes = tmp_path / "changes"
    folder = changes / layout.replace("x", "2026-11-01-x")
    folder.mkdir(parents=True)
    assert pass_proof.change_paths(changes, "2026-11-01-x") == [folder]
    assert pass_proof.change_paths(changes, "../x") == [] and pass_proof.change_paths(changes, "archive") == []
    import shutil

    shutil.rmtree(changes)
    changes.mkdir()
    assert pass_proof.change_paths(changes, "2026-11-01-x") == []  # removed after merge: nothing to read


def test_status_and_the_hook_read_the_same_layouts() -> None:
    hook = (SKILL / "templates/hooks/pr-gate.sh").read_text()
    status = (SKILL / "scripts/sdlc_status.py").read_text()
    assert 'proof("LAYOUTS")' in hook and "change_paths(base, change_id)" in status


from test_sdlc_status import BRANCH, PASS, _gate as _status_gate, _goal, repo  # noqa: E402, F401
from test_sdlc_status import ID as SID  # noqa: E402

import sdlc_status  # noqa: E402


def test_a_milestone_the_plan_does_not_have_is_no_pass_and_invents_no_pr(repo: Path) -> None:  # noqa: F811
    _status_gate(repo, PASS)
    (repo / "changes" / SID / "plan.md").write_text(
        "## Milestones\n\n| # | what |\n|---|---|\n| M1 | a |\n| M2 | b |\n"
    )
    code, line = _goal(repo, {}, n=99)
    assert (code, line) == (1, f"GOAL {SID} OPEN no-such-milestone:99")
    assert "plan.md" in sdlc_status.blocker(SID, line) and "`" in sdlc_status.blocker(SID, line)


def test_the_project_hint_names_the_project_slug_not_the_change_id(repo: Path) -> None:  # noqa: F811
    decisions = repo / "changes" / SID / "decisions.json"
    data = json.loads(decisions.read_text())
    decisions.write_text(json.dumps({**data, "project": {"slug": "big", "branch": True}}))
    assert sdlc_status.subject_of(repo / "changes" / SID, "project") == "big"
    assert sdlc_status.subject_of(repo / "changes" / SID, "milestone") == SID
    assert "verify_gate.py project big" in sdlc_status.blocker("big", "GOAL x OPEN project-gate-pass", scope="project")


def test_goal_and_map_leave_the_tree_clean(repo: Path) -> None:  # noqa: F811
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=_env())
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"], cwd=repo, check=True, env=_env(), capture_output=True)
    for args in (("map",), ("goal", ID), ("ids", ID)):
        subprocess.run([sys.executable, str(SKILL / "scripts/sdlc_status.py"), *args], cwd=repo, capture_output=True, env=_env())
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, env=_env()).stdout
    assert status == "", status


# --- the states/edges file: equal to the code, and no state without a way out ---------------------

STATES = json.loads((SKILL / "references/states.json").read_text())["states"]


def _flags() -> set[str]:
    import re

    src = (SKILL / "scripts/sdlc_status.py").read_text()
    return {"pr-" + f for f in re.findall(r'return "[a-z-]+", "([a-z-]+)"', src)} | {"pr-not-merged-or-armed"}


def test_the_states_file_covers_every_goal_reason_and_pr_flag() -> None:
    blocks = set(sdlc_status.BLOCKS)
    assert blocks <= set(STATES), sorted(blocks - set(STATES))
    flags = _flags()
    assert flags <= set(STATES), sorted(flags - set(STATES))


def test_no_state_is_a_dead_end() -> None:
    for name, s in STATES.items():
        if s["kind"] == "terminal":
            continue
        assert s["to"], f"{name} has no edge out"
        assert s["command"].strip(), f"{name} names no command"
        assert all(t in STATES for t in s["to"]), f"{name} leads to an unknown state"
    reach = {"done"}
    grew = True
    while grew:  # every state must reach the terminal one
        grew = False
        for name, s in STATES.items():
            if name not in reach and any(t in reach for t in s["to"]):
                reach.add(name)
                grew = True
    assert set(STATES) == reach, sorted(set(STATES) - reach)


def test_the_security_review_runs_per_milestone_from_the_recorded_start(repo: Path) -> None:  # noqa: F811
    (repo / "changes" / SID / "lock.json").write_text(json.dumps({"sha": "c" * 40}))
    assert sdlc_status.security_base(repo / "changes" / SID) == "c" * 40
    out = subprocess.run([sys.executable, str(SKILL / "scripts/sdlc_status.py"), "base", SID], cwd=repo, capture_output=True, text=True, env=_env())
    assert out.stdout.strip() == "c" * 40
    stages = " ".join((SKILL / "references/stages.md").read_text().split())
    assert "runs at every milestone close" in stages and "sdlc_status.py base <id>" in stages
    assert "runs only on the goal's last milestone" not in stages
