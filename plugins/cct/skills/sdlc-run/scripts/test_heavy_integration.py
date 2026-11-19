"""Group B of 3.21.0: the heavy-job queue and fail-fast wired into the gate, the hooks and the
status code (docs/designs/heavy-integration.md), plus the two risks left by the layout-4 work."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from test_sdd_wiring import ID, TASKS, _change, approved, base_repo, commit, gate, last, rule, sh, v4  # noqa: F401

SCRIPTS = Path(__file__).resolve().parents[1] / "templates" / "scripts"


# ---------------------------------------------------------------- risk: no resolvable parent


def _lose_the_parent(repo: Path) -> None:
    """master is gone and the configured default never existed: nothing to diff against."""
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "defaultBranch": "trunk"}))
    commit(repo, "config")
    sh(repo, "git", "branch", "-m", "master", "elsewhere")


def test_approve_without_a_resolvable_parent_is_an_env_handoff_with_a_fix_line(tmp_path: Path) -> None:
    repo = base_repo(tmp_path)
    v4(repo)
    commit(repo)
    _lose_the_parent(repo)
    r = gate(repo, "approve", ID)
    assert r.returncode == 3, r.stdout + r.stderr
    assert last(r) == "APPROVE BLOCKED reason=env"
    assert "Fix:" in r.stdout and "trunk" in r.stdout and "Traceback" not in r.stderr


def test_the_milestone_gate_without_a_resolvable_parent_is_an_env_handoff(tmp_path: Path) -> None:
    repo = base_repo(tmp_path)
    c = v4(repo)
    approved(repo, c)
    rule(repo, "billing", 1)
    commit(repo)
    _lose_the_parent(repo)
    r = gate(repo, "milestone", ID)
    assert r.returncode == 3, r.stdout + r.stderr
    assert last(r) == "VERIFY BLOCKED reason=env"
    assert "Fix:" in r.stdout and "Traceback" not in r.stderr


# ---------------------------------------------------------------- risk: marks.py without spec.py


def test_marks_py_runs_without_spec_py_unless_layout_4_is_in_use(tmp_path: Path) -> None:
    lone = tmp_path / "lone"
    lone.mkdir()
    (lone / "marks.py").write_text((SCRIPTS / "marks.py").read_text())
    imported = subprocess.run(
        [sys.executable, "-c", "import marks"], cwd=lone, capture_output=True, text=True
    )
    assert imported.returncode == 0, imported.stderr
    repo = tmp_path / "repo"
    change = repo / "changes" / "2026-10-21-old"
    change.mkdir(parents=True)
    (repo / "sdlc.json").write_text("{}")
    r = subprocess.run(
        [sys.executable, str(lone / "marks.py"), "check", change.name],
        cwd=repo, capture_output=True, text=True,
    )  # fmt: skip
    assert "ModuleNotFoundError" not in r.stderr and "Traceback" not in r.stderr, r.stderr
