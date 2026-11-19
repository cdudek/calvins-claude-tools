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


# ---------------------------------------------------------------- the gate runs under the queue

import os  # noqa: E402
import shlex  # noqa: E402
import time  # noqa: E402

from test_verify_gate import ID as GID  # noqa: E402
from test_verify_gate import _approve, _env, _git, _last, _repo  # noqa: E402

HEAVY = SCRIPTS / "heavy.py"


def _milestone(tmp_path: Path, checks: list, **extra: object) -> Path:
    repo = _repo(tmp_path, [])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": checks}, **extra}))
    _git(repo, "commit", "-qam", "milestone checks")
    _approve(repo)
    return repo


def _run_gate(repo: Path, queue: Path, *prefix: str, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    env = {**_env(), "SDLC_HEAVY_DIR": str(queue), "SDLC_HEAVY_SLOTS": "1", "SDLC_HEAVY_POLL": "0.1"}
    return subprocess.run(
        [*prefix, sys.executable, str(SCRIPTS / "verify_gate.py"), "milestone", GID],
        cwd=repo, capture_output=True, text=True, env=env, timeout=timeout,
    )  # fmt: skip


def test_a_heavy_check_runs_in_a_slot_and_a_light_one_does_not(tmp_path: Path) -> None:
    seen = tmp_path / "seen"
    repo = _milestone(
        tmp_path,
        [
            {"name": "light", "run": f"echo \"light=$SDLC_HEAVY_SLOT\" >> {seen}"},
            {"name": "build", "run": f"echo \"build=$SDLC_HEAVY_SLOT\" >> {seen}"},
        ],
    )
    r = _run_gate(repo, tmp_path / "queue")
    assert _last(r).startswith(f"VERIFY PASS milestone {GID}"), r.stdout + r.stderr
    lines = set(seen.read_text().split())
    assert lines == {"light=", "build=0"}, lines


def test_a_gate_already_inside_a_slot_passes_straight_through(tmp_path: Path) -> None:
    repo = _milestone(tmp_path, [{"name": "build", "run": "echo build"}])
    r = _run_gate(
        repo, tmp_path / "queue", sys.executable, str(HEAVY), "run", "--wait-timeout", "5", "--", timeout=60
    )
    assert _last(r).startswith(f"VERIFY PASS milestone {GID}"), r.stdout + r.stderr


def test_a_slot_that_never_frees_is_an_env_handoff_naming_the_holder(tmp_path: Path) -> None:
    queue = tmp_path / "queue"
    repo = _milestone(tmp_path, [{"name": "build", "run": "echo build"}], heavy={"waitTimeout": 1})
    env = {**_env(), "SDLC_HEAVY_DIR": str(queue), "SDLC_HEAVY_SLOTS": "1"}
    holder = subprocess.Popen(
        [sys.executable, str(HEAVY), "run", "--", "sleep", "30"], cwd=repo, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )  # fmt: skip
    try:
        for _ in range(100):  # until the holder has its slot
            if list(queue.glob("*")):
                break
            time.sleep(0.1)
        r = _run_gate(repo, queue)
    finally:
        holder.kill()
        holder.wait()
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env", r.stdout + r.stderr
    assert "sleep" in r.stdout and "build" in r.stdout


def test_a_failed_preflight_stops_the_gate_before_the_first_heavy_command(tmp_path: Path) -> None:
    ran = tmp_path / "ran"
    repo = _milestone(
        tmp_path,
        [{"name": "build", "run": f"touch {shlex.quote(str(ran))}"}],
        preflight={"tools": ["no-such-tool-for-this-test"]},
    )
    r = _run_gate(repo, tmp_path / "queue")
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env", r.stdout + r.stderr
    assert "no-such-tool-for-this-test" in r.stdout and not ran.exists()
    assert os.path.exists(repo / "changes" / GID / "verify" / "report.json")
