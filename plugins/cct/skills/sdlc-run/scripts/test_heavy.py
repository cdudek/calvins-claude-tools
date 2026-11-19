"""Usage: pytest scripts/test_heavy.py

The heavy-job queue (locking, FIFO order, stale reclaim, re-entrancy, deadlines, detached jobs),
the main-folder guard and the evidence ledger. No Docker needed. Order is asserted from an
acquisition log, never from sleeps.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HEAVY = Path(__file__).resolve().parents[1] / "templates/scripts/heavy.py"
EVIDENCE = Path(__file__).resolve().parents[1] / "templates/scripts/evidence.py"


def _env(q: Path, **extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "SDLC_"))}
    env.update(SDLC_HEAVY_DIR=str(q), SDLC_HEAVY_POLL="0.05", PYTHONDONTWRITEBYTECODE="1", **extra)
    return env


def _heavy(q: Path, *args: str, **kw) -> subprocess.CompletedProcess[str]:
    env = kw.pop("env", None) or _env(q)
    return subprocess.run(
        [sys.executable, str(HEAVY), *args], capture_output=True, text=True, env=env, **kw
    )


def _popen(q: Path, *args: str, **extra: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, str(HEAVY), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_env(q, **extra),
    )


def _until(cond, what: str, limit: float = 10.0) -> None:
    end = time.time() + limit
    while time.time() < end:
        if cond():
            return
        time.sleep(0.02)
    raise AssertionError(f"timed out waiting for {what}")


def _holding(q: Path, gate: Path, log: Path, name: str) -> list[str]:
    """A job that logs `name start`, blocks until `gate` exists, then logs `name end`."""
    script = (
        f"echo {name} start >> {log}; while [ ! -e {gate} ]; do sleep 0.02; done; "
        f"echo {name} end >> {log}"
    )
    return ["run", "--", "sh", "-c", script]


def _tickets(q: Path) -> list[Path]:
    return sorted((q / "tickets").glob("*.json")) if (q / "tickets").is_dir() else []


def _dead_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def test_runs_a_job_and_returns_its_exit_code(tmp_path: Path) -> None:
    assert _heavy(tmp_path, "run", "--", "sh", "-c", "exit 0").returncode == 0
    assert _heavy(tmp_path, "run", "--", "sh", "-c", "exit 7").returncode == 7
    assert _tickets(tmp_path) == [], "the slot is released after every job"


def test_one_slot_serialises_in_arrival_order(tmp_path: Path) -> None:
    log, gates = tmp_path / "log", [tmp_path / f"g{i}" for i in range(3)]
    procs = []
    for i, gate in enumerate(gates):
        procs.append(_popen(tmp_path, *_holding(tmp_path, gate, log, f"j{i}")))
        _until(lambda n=i + 1: len(_tickets(tmp_path)) == n, f"ticket {i}")
    _until(lambda: log.exists() and "j0 start" in log.read_text(), "j0 start")
    assert log.read_text().splitlines() == ["j0 start"], "later jobs wait for the slot"
    for gate, proc, i in zip(gates, procs, range(3)):
        _until(lambda i=i: f"j{i} start" in log.read_text(), f"j{i} start")
        gate.touch()
        assert proc.wait(timeout=10) == 0
    assert log.read_text().splitlines() == [
        "j0 start", "j0 end", "j1 start", "j1 end", "j2 start", "j2 end",
    ]  # fmt: skip


def test_two_slots_run_two_jobs_at_once_with_distinct_slot_numbers(tmp_path: Path) -> None:
    log, gate = tmp_path / "log", tmp_path / "gate"
    script = f'echo "$SDLC_HEAVY_SLOT" >> {log}; while [ ! -e {gate} ]; do sleep 0.02; done'
    procs = [
        _popen(tmp_path, "run", "--slots", "2", "--", "sh", "-c", script) for _ in range(3)
    ]  # the third has to wait
    _until(lambda: log.exists() and len(log.read_text().split()) == 2, "two jobs running")
    assert sorted(log.read_text().split()) == ["0", "1"]
    assert len(_tickets(tmp_path)) == 3
    gate.touch()
    assert [p.wait(timeout=10) for p in procs] == [0, 0, 0]


def test_a_dead_holder_is_reclaimed_and_a_live_one_is_named(tmp_path: Path) -> None:
    (tmp_path / "tickets").mkdir()
    dead = tmp_path / "tickets" / f"{time.time_ns():020d}-{_dead_pid()}.json"
    dead.write_text(json.dumps({"pid": int(dead.stem.split("-")[1]), "cmd": ["old"], "slot": 0}))
    assert _heavy(tmp_path, "run", "--", "true").returncode == 0, "a dead PID never blocks"
    assert not dead.exists(), "and its ticket is dropped"

    holder = _popen(tmp_path, "run", "--", "sleep", "30")
    _until(lambda: len(_tickets(tmp_path)) == 1, "holder ticket")
    waited = _heavy(tmp_path, "run", "--wait-timeout", "0.3", "--", "true")
    assert waited.returncode == 75
    assert f"pid {holder.pid}" in waited.stderr and "sleep 30" in waited.stderr
    holder.kill()
    holder.wait()
    assert _heavy(tmp_path, "run", "--", "true").returncode == 0, "a killed holder is reclaimed"


def test_a_dead_waiter_does_not_hold_up_the_line(tmp_path: Path) -> None:
    (tmp_path / "tickets").mkdir()
    pid = _dead_pid()
    (tmp_path / "tickets" / f"{time.time_ns() - 10**9:020d}-{pid}.json").write_text(
        json.dumps({"pid": pid, "cmd": ["ghost"], "slot": None})
    )
    assert _heavy(tmp_path, "run", "--wait-timeout", "5", "--", "true").returncode == 0


def test_a_job_started_under_a_held_slot_passes_through(tmp_path: Path) -> None:
    out = _heavy(
        tmp_path, "run", "--wait-timeout", "2", "--", sys.executable, str(HEAVY), "run", "--",
        "echo", "nested",
    )  # fmt: skip
    assert out.returncode == 0 and "nested" in out.stdout, "no deadlock at one slot"


def test_slot_env_gives_ports_from_the_slot(tmp_path: Path) -> None:
    out = _heavy(
        tmp_path, "run", "--", "sh", "-c",
        'echo "$SDLC_HEAVY_SLOT $SDLC_APP_PORT $SDLC_STUB_PORT"',
    )  # fmt: skip
    assert out.stdout.split() == ["0", "4100", "4101"]


def test_run_deadline_kills_the_job(tmp_path: Path) -> None:
    res = _heavy(tmp_path, "run", "--run-timeout", "0.3", "--", "sleep", "30")
    assert res.returncode == 124 and "deadline" in res.stderr
    assert _tickets(tmp_path) == []


def test_config_slots_come_from_sdlc_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sdlc.json").write_text(json.dumps({"heavy": {"slots": 2, "portBase": 5000}}))
    out = _heavy(tmp_path / "q", "run", "--", "sh", "-c", 'echo "$SDLC_APP_PORT"', cwd=repo)
    assert out.stdout.strip() == "5000"


def test_classify_separates_heavy_from_light() -> None:
    def kind(*cmd: str) -> str:
        res = subprocess.run(
            [sys.executable, str(HEAVY), "classify", "--", *cmd], capture_output=True, text=True
        )
        return res.stdout.strip()

    for heavy in (
        ("pnpm", "build"), ("npx", "playwright", "test"), ("pnpm", "dev"),
        ("make", "e2e"), ("python3", "scripts/capture.py"),
    ):  # fmt: skip
        assert kind(*heavy) == "heavy", heavy
    for light in (("pnpm", "lint"), ("tsc", "--noEmit"), ("ruff", "check", "."), ("git", "status")):
        assert kind(*light) == "light", light


def test_auto_runs_a_light_command_without_a_slot(tmp_path: Path) -> None:
    gate = tmp_path / "gate"
    holder = _popen(tmp_path, *_holding(tmp_path, gate, tmp_path / "log", "h"))
    _until(lambda: len(_tickets(tmp_path)) == 1, "holder ticket")
    out = _heavy(tmp_path, "run", "--auto", "--wait-timeout", "0.3", "--", "echo", "light")
    assert out.returncode == 0 and "light" in out.stdout
    gate.touch()
    holder.wait(timeout=10)


def test_submit_returns_at_once_and_wait_reports_the_result(tmp_path: Path) -> None:
    sub = _heavy(tmp_path, "submit", "--", "sh", "-c", "echo built; exit 3")
    assert sub.returncode == 0
    job = sub.stdout.split()[0]
    res = _heavy(tmp_path, "wait", job, "--timeout", "10")
    assert res.returncode == 3, res.stderr
    result = json.loads((tmp_path / "jobs" / job / "result.json").read_text())
    assert result["status"] == "failed" and result["exit"] == 3
    assert "built" in (tmp_path / "jobs" / job / "log.txt").read_text()


def test_wait_deadline_for_an_unfinished_job(tmp_path: Path) -> None:
    job = _heavy(tmp_path, "submit", "--", "sleep", "30").stdout.split()[0]
    res = _heavy(tmp_path, "wait", job, "--timeout", "0.3")
    assert res.returncode == 75
    pid = json.loads((tmp_path / "jobs" / job / "job.json").read_text())["pid"]
    os.kill(pid, 15)


def test_status_lists_holder_and_waiters(tmp_path: Path) -> None:
    assert "idle" in _heavy(tmp_path, "status").stdout
    gate = tmp_path / "gate"
    holder = _popen(tmp_path, *_holding(tmp_path, gate, tmp_path / "log", "h"))
    _until(lambda: "slot 0" in _heavy(tmp_path, "status").stdout, "holder assigned a slot")
    waiter = _popen(tmp_path, "run", "--", "true")
    _until(lambda: len(_tickets(tmp_path)) == 2, "two tickets")
    out = _heavy(tmp_path, "status").stdout
    assert "holding" in out and "waiting" in out
    gate.touch()
    assert holder.wait(timeout=10) == 0 and waiter.wait(timeout=10) == 0


def _git(repo: Path, *args: str) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def _guard(cwd: Path, payload: dict | None = None) -> subprocess.CompletedProcess[str]:
    args = ["guard-main", "--hook"] if payload is not None else ["guard-main"]
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(
        [sys.executable, str(HEAVY), *args],
        capture_output=True, text=True, cwd=cwd, env=env,
        input=json.dumps(payload) if payload is not None else None,
    )  # fmt: skip


def test_guard_refuses_helper_commands_in_the_main_folder(tmp_path: Path) -> None:
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q")
    _git(
        main,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "i",
    )
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", "-b", "feat", str(wt))
    assert _guard(main).returncode == 3 and "main working folder" in _guard(main).stderr
    assert _guard(wt).returncode == 0
    # as a PreToolUse hook: only a subagent's call is refused, the owner's session is not
    # a read-only helper (a reviewer, an explorer) works in the main folder: the hook refuses only a
    # subagent's heavy call outside the queue, wherever it stands
    call = {"cwd": str(main), "agent_id": "a1", "tool_input": {"command": "pnpm build"}}
    assert _guard(main, call).returncode == 2
    assert _guard(main, {**call, "tool_input": {"command": "git status"}}).returncode == 0
    assert _guard(main, {"cwd": str(main), "tool_input": {"command": "pnpm build"}}).returncode == 0
    assert _guard(wt, {**call, "cwd": str(wt)}).returncode == 2


def _evidence(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(EVIDENCE), *args], capture_output=True, text=True)


def test_evidence_is_one_file_per_screen_and_stale_is_checked_per_key(tmp_path: Path) -> None:
    shot = tmp_path / "a.png"
    shot.write_bytes(b"png")
    cat = tmp_path / "en.json"
    cat.write_text(json.dumps({"home": {"title": "Hello", "cta": "Go"}, "other": {"x": "1"}}))
    ev = tmp_path / "evidence"
    for screen in ("home", "settings"):
        res = _evidence(
            "record", str(ev), screen, "--shot", str(shot), "--catalog", str(cat),
            "--keys", "home.title,home.cta",
        )  # fmt: skip
        assert res.returncode == 0, res.stderr
    assert sorted(p.name for p in ev.iterdir()) == ["home.json", "settings.json"]
    assert _evidence("stale", str(ev), "--catalog", str(cat)).returncode == 0

    cat.write_text(json.dumps({"home": {"title": "Hello", "cta": "Start"}, "other": {"x": "2"}}))
    res = _evidence("stale", str(ev), "--catalog", str(cat))
    assert res.returncode == 1
    assert "home: home.cta" in res.stdout and "settings: home.cta" in res.stdout
    assert "title" not in res.stdout, "an unchanged key never makes a screen stale"

    cat.write_text(json.dumps({"home": {"title": "Hello"}}))  # a deleted key counts as changed
    assert "home.cta" in _evidence("stale", str(ev), "--catalog", str(cat)).stdout


def test_evidence_screen_name_cannot_escape_the_folder(tmp_path: Path) -> None:
    res = _evidence("record", str(tmp_path / "ev"), "../x", "--keys", "")
    assert res.returncode != 0 and not (tmp_path / "x.json").exists()


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_the_usage(flag: str) -> None:
    out = subprocess.run([sys.executable, str(HEAVY), flag], capture_output=True, text=True)
    assert out.returncode == 0 and "heavy.py run" in out.stdout
