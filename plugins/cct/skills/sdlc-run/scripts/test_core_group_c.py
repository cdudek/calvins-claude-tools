"""Group C: the known goal issues, a removed change folder, persisted heads and bases, HANDOFF."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from test_sdlc_status import BRANCH, GATE, ID, MOVED, PASS, _gate, _goal, _plan, _pr, _run, repo  # noqa: F401

import sdlc_status

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "templates" / "scripts"))
import verify_gate  # noqa: E402


# --- known issues ------------------------------------------------------------------------------


def test_feature_pr_mode_asks_for_the_milestone_branch_without_a_number(repo: Path) -> None:  # noqa: F811
    (repo / "sdlc.json").write_text(json.dumps({"delivery": "feature-prs"}))
    _gate(repo, PASS)
    assert _goal(repo, {}) == (1, f"GOAL {ID} OPEN no-pr:milestone/redesign-r2")
    assert _goal(repo, {"milestone/redesign-r2": _pr()}) == (0, f"GOAL {ID} DONE pr=7 state=merged gate={GATE}")


def test_milestone_one_stays_done_after_milestone_two_passed(repo: Path) -> None:  # noqa: F811
    _plan(repo, 2)
    _gate(repo, PASS, milestone=1)
    folder = repo / "changes" / ID / "verify"
    shutil.copy(folder / "report.json", folder / "milestone-1.json")  # the receipt the gate keeps
    _gate(repo, f"VERIFY PASS milestone {ID} {MOVED}", milestone=2)  # report.json now holds M2
    prs = {BRANCH: _pr(), "milestone/redesign-r2-2": _pr(number=8, head=MOVED)}
    assert _goal(repo, prs, n=1) == (0, f"GOAL {ID} DONE pr=7 state=merged gate={GATE}")
    assert _goal(repo, prs, n=2)[0] == 0


def test_a_milestone_without_a_receipt_still_needs_its_own_report(repo: Path) -> None:  # noqa: F811
    _plan(repo, 2)
    _gate(repo, f"VERIFY PASS milestone {ID} {MOVED}", milestone=2)
    assert "milestone-gate-pass" in _goal(repo, {BRANCH: _pr()}, n=1)[1]


def test_a_check_after_a_wall_never_moves_over_it() -> None:
    checks = [
        {"name": "x", "run": "x", "after": ["late"]},
        {"name": "wall", "run": "w", "serial": True},
        {"name": "late", "run": "l"},
    ]
    order = [c["name"] for c in verify_gate.order_checks(checks, {}, ID)]
    assert order == ["x", "wall", "late"]


def test_after_still_orders_checks_inside_one_segment() -> None:
    checks = [{"name": "tsc", "run": "tsc", "after": ["codegen"]}, {"name": "codegen", "run": "codegen"}]
    assert [c["name"] for c in verify_gate.order_checks(checks, {}, ID)] == ["codegen", "tsc"]


BODY = "- **Requirement (F13):** Filters stay readable, see F13.\n"
DEFINED = "- [ ] **F13** (A1) Filters stay readable.\n"


def _lint(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SKILL / "templates/scripts/verify_gate.py"), "lint", ID, "--pr-body", "-"],
        cwd=repo, input=BODY, capture_output=True, text=True,
    )  # fmt: skip


@pytest.mark.parametrize("where", ["archive/2026/2026-11", "archive", "gone"])
def test_lint_pr_body_works_once_the_change_folder_is_archived_or_removed(repo: Path, where: str) -> None:  # noqa: F811
    live = repo / "changes" / ID
    (live / "facts.md").write_text(DEFINED)
    if where == "gone":
        shutil.rmtree(live)
    else:
        target = repo / "changes" / where / ID
        target.parent.mkdir(parents=True)
        shutil.move(str(live), str(target))
    r = _lint(repo)
    assert r.returncode == 1 and "pr-body: id F13 outside brackets" in r.stdout, (r.stdout, r.stderr)


# --- a removed change folder whose PR merged -----------------------------------------------------


def _merged(head: str, number: int = 7) -> dict:
    return {"number": number, "headRefName": head, "state": "MERGED"}


def test_a_removed_folder_whose_pr_merged_reads_done(repo: Path) -> None:  # noqa: F811
    code, line = sdlc_status.goal_removed(repo, ID, "milestone", None, gh=lambda root, *a: [_merged(BRANCH)])
    assert (code, line) == (0, f"GOAL {ID} DONE pr=7 state=merged folder=removed")


def test_a_removed_folder_with_no_merged_pr_is_still_no_change_folder(repo: Path) -> None:  # noqa: F811
    assert sdlc_status.goal_removed(repo, ID, "milestone", None, gh=lambda root, *a: [_merged("feat/other")]) is None
    assert sdlc_status.goal_removed(repo, ID, "milestone", None, gh=lambda root, *a: []) is None


def test_a_removed_folder_is_never_done_without_the_merged_pr_when_gh_fails(repo: Path) -> None:  # noqa: F811
    assert sdlc_status.goal_removed(repo, ID, "milestone", None, gh=lambda root, *a: None) is None


def test_a_removed_milestone_n_needs_its_own_merged_head(repo: Path) -> None:  # noqa: F811
    gh = lambda root, *a: [_merged("milestone/redesign-r2-2", 9)]  # noqa: E731
    assert sdlc_status.goal_removed(repo, ID, "milestone", 1, gh=gh) is None
    assert sdlc_status.goal_removed(repo, ID, "milestone", 2, gh=gh) == (0, f"GOAL {ID} DONE pr=9 state=merged folder=removed")


def test_the_cli_reads_a_removed_folder_as_done(repo: Path, tmp_path: Path) -> None:  # noqa: F811
    import os

    shutil.rmtree(repo / "changes" / ID)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    out = json.dumps([_merged(BRANCH)])
    (bin_dir / "gh").write_text(f"#!/bin/sh\necho '{out}'\n")
    (bin_dir / "gh").chmod(0o755)
    path = f"{bin_dir}{os.pathsep}{Path(shutil.which('git') or '/usr/bin/git').parent}"
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {"PATH": path}
    run = subprocess.run([sys.executable, str(SKILL / "scripts/sdlc_status.py"), "goal", ID], cwd=repo, capture_output=True, text=True, env=env)
    assert (run.returncode, run.stdout.strip()) == (0, f"GOAL {ID} DONE pr=7 state=merged folder=removed")


# --- persisted heads and bases (S5 to S8) ---------------------------------------------------------

import test_verify_gate as tvg  # noqa: E402


def _heads(repo: Path, data: dict, where: str = "state/heads.json") -> None:
    path = repo / "changes" / ID / where
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data))


def test_a_milestone_pass_records_its_head_and_base(tmp_path: Path) -> None:
    repo = tvg._milestone_repo(tmp_path)
    tvg._git(repo, "checkout", "-q", "-b", "milestone/trial-2")
    tvg._commit_files(repo, validation_md="| F1 | x | y | z | met |\n")
    r = tvg._gate(repo, "milestone", tvg.ID)
    assert tvg._last(r).startswith(f"VERIFY PASS milestone {tvg.ID}"), r.stdout
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    saved = json.loads((repo / "changes" / tvg.ID / "state" / "heads.json").read_text())
    assert saved["milestones"]["2"] == {"head": "milestone/trial-2", "base": "main", "sha": head}


def test_a_failed_milestone_run_records_nothing(tmp_path: Path) -> None:
    repo = tvg._milestone_repo(tmp_path)
    tvg._git(repo, "checkout", "-q", "-b", "milestone/trial-1")
    (repo / "changes" / tvg.ID / "validation.md").write_text("| F1 | x | y | z | not met |\n")
    tvg._git(repo, "commit", "-qam", "unproven")
    assert not tvg._last(tvg._gate(repo, "milestone", tvg.ID)).startswith("VERIFY PASS")
    assert not (repo / "changes" / tvg.ID / "state" / "heads.json").exists()


def test_a_hotfix_feature_pass_records_the_hotfix_head(tmp_path: Path) -> None:
    repo = tvg._repo(tmp_path, ["true"])
    tvg._approve(repo)
    tvg._git(repo, "checkout", "-q", "-b", "hotfix/trial")
    r = tvg._gate(repo, "feature", tvg.ID)
    assert tvg._last(r).startswith("VERIFY PASS feature"), r.stdout
    saved = json.loads((repo / "changes" / tvg.ID / "state" / "heads.json").read_text())
    assert saved["hotfix"]["head"] == "hotfix/trial" and saved["hotfix"]["base"] == "main"


@pytest.mark.parametrize("where", ["state/heads.json", "heads.json"])
def test_the_goal_reads_the_recorded_head_and_base_new_place_first(repo: Path, where: str) -> None:  # noqa: F811
    _gate(repo, PASS)
    _heads(repo, {"milestones": {"1": {"head": "release/custom-1", "base": "project/x"}}}, where)
    prs = {"release/custom-1": _pr(base="project/x")}
    assert _goal(repo, prs) == (0, f"GOAL {ID} DONE pr=7 state=merged gate={GATE}")
    assert _goal(repo, {BRANCH: _pr()})[1] == f"GOAL {ID} OPEN no-pr:release/custom-1"  # not the derived name


def test_a_recorded_base_that_the_pr_does_not_target_is_a_wrong_base(repo: Path) -> None:  # noqa: F811
    _gate(repo, PASS)
    _heads(repo, {"milestones": {"1": {"head": BRANCH, "base": "project/x"}}})
    assert "pr-7-wrong-base" in _goal(repo, {BRANCH: _pr(base="main")})[1]


def test_without_a_record_the_derived_name_and_the_parent_stand(repo: Path) -> None:  # noqa: F811
    _gate(repo, PASS)
    assert _goal(repo, {BRANCH: _pr()})[0] == 0


def _hotfix_change(repo: Path, enabled: bool = True) -> None:
    decisions = repo / "changes" / ID / "decisions.json"
    decisions.write_text(json.dumps({"milestone": {"kind": "hotfix", "slug": "redesign-r2"}}))
    if not enabled:
        (repo / "sdlc.json").write_text(json.dumps({"hotfix": False}))
    _heads(repo, {"hotfix": {"head": "hotfix/redesign-r2", "base": "main", "sha": GATE}})
    _gate(repo, f"VERIFY PASS feature {ID} {GATE}", scope="feature")


def test_a_hotfix_goal_follows_the_recorded_hotfix_head_to_the_default_branch(repo: Path) -> None:  # noqa: F811
    _hotfix_change(repo)
    assert _goal(repo, {"hotfix/redesign-r2": _pr()}) == (0, f"GOAL {ID} DONE pr=7 state=merged gate={GATE}")
    assert _goal(repo, {"hotfix/redesign-r2": _pr("OPEN", base="project/x")})[1].startswith(f"GOAL {ID} OPEN pr-7-wrong-base")
    assert _goal(repo, {})[1] == f"GOAL {ID} OPEN no-pr:hotfix/redesign-r2"


def test_a_disabled_hotfix_has_no_hotfix_route(repo: Path) -> None:  # noqa: F811
    _hotfix_change(repo, enabled=False)
    assert "milestone-gate-pass" in _goal(repo, {"hotfix/redesign-r2": _pr()})[1]


def _main_branch(repo: Path) -> str:
    sha = tvg._git  # noqa: F841
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base"], cwd=repo, check=True)
    subprocess.run(["git", "branch", "-f", "main"], cwd=repo, check=True)
    return subprocess.run(["git", "rev-parse", "main"], cwd=repo, capture_output=True, text=True).stdout.strip()


def _branchless(repo: Path) -> None:
    decisions = repo / "changes" / ID / "decisions.json"
    data = json.loads(decisions.read_text())
    decisions.write_text(json.dumps({**data, "project": {"slug": "big", "branch": False}}))


def _status(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(repo, *args)


def test_a_branchless_project_is_done_once_integrated_and_accepted(repo: Path) -> None:  # noqa: F811
    _branchless(repo)
    sha = _main_branch(repo)
    assert _goal(repo, {}, scope="project")[1].endswith("no-project-branch")
    assert _status(repo, "record", ID, "project", "--sha", sha).returncode == 0
    assert "project-not-accepted" in _goal(repo, {}, scope="project")[1]
    assert _status(repo, "record", ID, "project", "--sha", sha, "--accepted").returncode == 0
    assert _goal(repo, {}, scope="project") == (0, f"GOAL {ID} DONE project=big integrated={sha}")


def test_the_project_record_refuses_a_sha_that_is_not_in_the_default_branch(repo: Path) -> None:  # noqa: F811
    _branchless(repo)
    _main_branch(repo)
    r = _status(repo, "record", ID, "project", "--sha", "f" * 40, "--accepted")
    assert r.returncode == 1 and "not in main" in r.stdout
    assert not (repo / "changes" / ID / "state" / "heads.json").exists()


def test_a_recorded_project_sha_that_left_the_default_branch_is_not_integrated(repo: Path) -> None:  # noqa: F811
    _branchless(repo)
    _main_branch(repo)
    _heads(repo, {"project": {"sha": "f" * 40, "accepted": True}})
    assert "project-not-integrated" in _goal(repo, {}, scope="project")[1]
