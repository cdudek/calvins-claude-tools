"""Speed A close (3.21.0), the core stream: lock format, plan parser, strict rows only for new locks."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_verify_gate import (
    GATE,
    ID,
    _approve,
    _commit_files,
    _env,
    _gate,
    _git,
    _last,
    _milestone_repo,
    _repo,
)

TEMPLATES = GATE.parent


def _vg():
    sys.path.insert(0, str(TEMPLATES))
    spec = importlib.util.spec_from_file_location("vg_under_test", GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _plan(cell: str, first: str = "M1 a") -> str:
    return f"## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n| {first} | {cell} | none |\n"


FACTS132 = [f"F{i}" for i in range(1, 133)]


@pytest.mark.parametrize(
    ("cell", "facts", "expected"),
    [
        ("rows 0 to 4, F1 to F132", FACTS132, FACTS132),  # real plan: agent-tracker
        ("F1 to F7", [f"F{i}" for i in range(1, 10)], [f"F{i}" for i in range(1, 8)]),
        ("F1-F7, F71", ["F1", "F7", "F8", "F71"], ["F1", "F7", "F71"]),
        ("F8-F20, F22-F34", ["F8", "F21", "F22", "F34", "F35"], ["F8", "F22", "F34"]),
        ("F1–F15, N1", ["F1", "F15", "F16", "N1"], ["F1", "F15", "N1"]),  # en dash
        ("F2, F3", ["F1", "F2", "F3"], ["F2", "F3"]),
    ],
)
def test_the_plan_parser_reads_ranges_of_the_real_plans(cell: str, facts: list, expected: list) -> None:
    assert _vg().row_facts(_plan(cell), 1, facts) == expected


def test_a_bare_number_milestone_row_is_row_one() -> None:
    plan = _plan("F1, F2", first="1")
    assert _vg().row_facts(plan, 1, ["F1", "F2", "F3"]) == ["F1", "F2"]


def test_a_one_milestone_plan_whose_cell_names_no_ids_owns_every_approved_fact() -> None:
    assert _vg().row_facts(_plan("rows 0 to 5, 74 facts"), 1, ["F1", "F2"]) == ["F1", "F2"]


def test_a_two_milestone_plan_with_an_unreadable_row_owns_nothing() -> None:
    plan = _plan("rows 0 to 5") + "| M2 b | F2 | M1 |\n"
    assert _vg().row_facts(plan, 1, ["F1", "F2"]) == []


def _old_lock(repo: Path) -> None:
    path = repo / "changes" / ID / "lock.json"
    lock = json.loads(path.read_text())
    lock.pop("format", None)
    lock["criteria"].pop("plan.milestones", None)
    lock["criteria"].pop("decisions.routing", None)
    lock.pop("manifest", None)
    path.write_text(json.dumps(lock))
    _git(repo, "commit", "-qam", "an older lock")


def test_approve_writes_the_lock_format_version() -> None:
    assert _vg().LOCK_FORMAT >= 3


def test_approve_writes_the_format_into_lock_json(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    lock = json.loads((repo / "changes" / ID / "lock.json").read_text())
    assert lock["format"] == _vg().LOCK_FORMAT


def test_a_new_approval_cannot_opt_out_by_deleting_the_records(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [])
    (repo / "changes" / ID / "done.json").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "no facts")
    r = _gate(repo, "approve", ID)  # approval requires its artifacts
    assert r.returncode == 1 and "done.json" in r.stdout


def test_a_new_lock_with_no_validation_rows_blocks(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    (repo / "changes" / ID / "validation.md").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "no validation")
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=validation-not-met"


def test_an_old_lock_is_never_blocked_for_missing_rows_and_gets_a_note(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    (repo / "changes" / ID / "validation.md").write_text("| F9 | other | y | z | met |\n")
    _git(repo, "commit", "-qam", "odd validation")
    _old_lock(repo)
    r = _gate(repo, "milestone", ID)
    assert _last(r).startswith(f"VERIFY PASS milestone {ID}"), r.stdout
    assert "upgrade gap" in r.stdout


def test_an_old_lock_with_an_unreadable_plan_row_uses_all_approved_facts(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    (repo / "changes" / ID / "plan.md").write_text(_plan("rows 0 to 5, 74 facts"))
    _git(repo, "commit", "-qam", "plan")
    _old_lock(repo)
    _git(repo, "checkout", "-q", "-b", "milestone/trial-1")
    r = _gate(repo, "milestone", ID)
    assert _last(r).startswith(f"VERIFY PASS milestone {ID}"), r.stdout


def test_a_four_cell_row_ending_in_met_has_no_evidence(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    _commit_files(repo, validation_md="| F1 | x | y | met |\n")
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=validation-not-met"


def test_the_gate_selects_facts_by_the_milestone_number_it_was_given(tmp_path: Path) -> None:
    """Not by the checked-out branch name alone: a configured branch prefix still selects the row."""
    repo = _milestone_repo(tmp_path)
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "milestones": {"branchPrefix": "m/"}}))
    # the checks are locked with the config: re-approve is the owner's job, so test the function
    mod = _vg()
    plan = _plan("F1") + "| M2 b | F2 | M1 |\n"
    assert mod.row_facts(plan, 2, ["F1", "F2"]) == ["F2"]


def _visual_milestone(tmp_path: Path) -> Path:
    repo = _repo(tmp_path, [])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": ["true"]}}))
    (repo / "changes" / ID / "decisions.json").write_text(
        json.dumps({"size": "M", "visualSource": "https://example.test/design"})
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "visual")
    _approve(repo)
    _commit_files(repo, validation_md="| F1 | x | y | z | met |\n")
    return repo


def test_editing_size_after_approval_cannot_waive_the_visual_review(tmp_path: Path) -> None:
    repo = _visual_milestone(tmp_path)
    assert _last(_gate(repo, "milestone", ID)) == f"VERIFY FAIL milestone {ID} check=ux-visual-required"
    path = repo / "changes" / ID / "decisions.json"
    path.write_text(json.dumps({"size": "none", "visualSource": "https://example.test/design"}))
    _git(repo, "commit", "-qam", "size none")
    r = _gate(repo, "milestone", ID)
    assert _last(r) == "VERIFY BLOCKED reason=protected-path" and "decisions.routing" in r.stdout


def test_a_size_none_decision_with_an_explicit_visual_source_still_needs_the_run(tmp_path: Path) -> None:
    mod = _vg()
    change = tmp_path / "changes" / ID
    change.mkdir(parents=True)
    (change / "decisions.json").write_text(json.dumps({"size": "none", "visualSource": "x"}))
    assert mod.visual_run_required(change, {}, tmp_path) is True


def test_malformed_decisions_json_on_a_new_lock_blocks_instead_of_reading_as_empty(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    (repo / "changes" / ID / "decisions.json").write_text("{broken")
    _git(repo, "commit", "-qam", "broken")
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=protected-path"


# --- the E2E rule, the preset repeats and the audit (round 2 findings 1, H7, M1, M2) -------------

SKILL = GATE.parents[2]


def _preset(name: str) -> dict:
    return json.loads((SKILL / "templates/presets" / f"{name}.json").read_text())


def _entry(name: str, stack: str) -> dict:
    return next(c for c in _preset(stack)["checks"]["milestone"] if isinstance(c, dict) and c["name"] == name)


def test_a_full_e2e_without_the_x3_repeat_is_not_approved(tmp_path: Path) -> None:
    from test_verify_gate import _e2e_repo

    repo = _e2e_repo(tmp_path, ["pytest -q", "uv run pytest e2e -q"])
    r = _gate(repo, "approve", ID)
    assert r.returncode == 1 and "repeat" in r.stdout


def test_an_e2e_suite_added_after_a_new_approval_blocks_the_milestone(tmp_path: Path) -> None:
    from test_verify_gate import _e2e_repo

    repo = _e2e_repo(tmp_path, ["true"], config=None)
    assert _gate(repo, "approve", ID).returncode == 0
    (repo / "e2e").mkdir()
    (repo / "e2e" / "a.spec.ts").write_text("x")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "e2e appears")
    _commit_files(repo, validation_md="| F1 | x | y | z | met |\n")
    r = _gate(repo, "milestone", ID)
    assert _last(r) == "VERIFY BLOCKED reason=env" and "full E2E" in r.stdout


@pytest.mark.parametrize("stack", ["node", "python"])
def test_a_repeat_fails_when_git_cannot_select_the_specs(tmp_path: Path, stack: str) -> None:
    """The diff is run before the pipe, so an unknown base is an error, never an empty selection."""
    repo = _repo(tmp_path, [])
    cmd = _entry("e2e-repeat", stack)["run"].replace("{base}", "origin/does-not-exist")
    bad = subprocess.run(cmd, shell=True, cwd=repo, capture_output=True, text=True, env=_env())
    assert bad.returncode != 0
    ok = subprocess.run(cmd.replace("origin/does-not-exist", "HEAD"), shell=True, cwd=repo, capture_output=True, text=True, env=_env())
    assert ok.returncode == 0, ok.stderr


def test_the_repeat_diffs_against_the_real_parent_branch(tmp_path: Path) -> None:
    mod = _vg()
    repo = _milestone_repo(tmp_path)
    change = repo / "changes" / ID
    (change / "decisions.json").write_text(json.dumps({"size": "S", "project": {"slug": "store"}}))
    _git(repo, "commit", "-qam", "project")
    _git(repo, "branch", "project/store")
    assert mod.parent_ref(change, {"defaultBranch": "master", "milestones": {"merge": "local"}}, repo) == "project/store"
    assert mod.parent_ref(change, {"defaultBranch": "master"}, repo) == "origin/master"
    cmd = mod.expand("git diff {base}...HEAD", ID, {"defaultBranch": "master"}, "project/store")
    assert cmd == "git diff project/store...HEAD"


def test_the_python_preset_keeps_e2e_out_of_the_plain_pytest_run() -> None:
    plain = next(c for c in _preset("python")["checks"]["milestone"] if isinstance(c, str) and "pytest" in c)
    assert "--ignore=e2e" in plain


@pytest.mark.parametrize("stack", ["node", "python"])
def test_audit_understands_the_preset_repeat_and_its_base_placeholder(tmp_path: Path, stack: str) -> None:
    from test_verify_gate import _audit, _audit_repo

    entry = _entry("e2e-repeat", stack)
    repo, env = _audit_repo(tmp_path, [entry], required=None)
    expanded = entry["run"].replace("{base}", "origin/master")
    verify = repo / "changes" / ID / "verify"
    verify.mkdir()
    (verify / "report.json").write_text(json.dumps({"sha": "abc1234def", "checks": [{"name": "e2e-repeat", "run": expanded, "status": "pass"}]}))
    r = _audit(repo, env)
    assert "never ran" not in r.stdout and "does not exist" not in r.stdout, r.stdout
