"""Usage: pytest scripts/test_heavy.py

The heavy-job queue (locking, FIFO order, stale reclaim, re-entrancy, deadlines, detached jobs),
the main-folder guard and the evidence ledger. No Docker needed. Order is asserted from an
acquisition log, never from sleeps.
"""

from __future__ import annotations

import json
import os
import signal
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
    _until(lambda: len(_tickets(tmp_path)) == 3, "the third job waits with a ticket")
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


HEAVY_CMDS = [
    ("pnpm", "build"), ("npx", "playwright", "test"), ("pnpm", "dev"), ("make", "e2e"),
    ("python3", "scripts/capture.py"), ("npm", "test"), ("pnpm", "test"), ("yarn", "test:e2e"),
    ("npm", "run", "smoke:background"), ("pnpm", "run", "build"), ("npx", "next", "start"),
    ("pnpm", "exec", "playwright", "test", "--project", "x"), ("pnpm", "--filter", "web", "build"),
    ("python3", "scripts/verify_gate.py", "milestone", "x"), ("sh", "scripts/e2e.sh"),
    ("sh", "-c", "pnpm format:check && pnpm test"), ("npx", "vite", "build"),
]  # fmt: skip
LIGHT_CMDS = [
    ("pnpm", "lint"), ("tsc", "--noEmit"), ("ruff", "check", "."), ("git", "status"),
    ("prettier", "--check", "e2e/a.spec.ts"), ("pnpm", "lint", "e2e"),
    ("vitest", "run", "src/build/x.test.ts"), ("npx", "vitest", "run", "build.test.ts"),
    ("pnpm", "format:check"), ("pnpm", "typecheck"), ("python3", "-m", "pytest", "tests/test_build.py"),
    ("echo", "build"), ("git", "commit", "-m", "fix the build"), ("grep", "-r", "e2e", "."),
    ("sh", "-c", "pnpm lint && pnpm typecheck"), ("python3", "scripts/verify_gate.py", "feature", "x"),
]  # fmt: skip


@pytest.mark.parametrize("cmd", HEAVY_CMDS, ids=" ".join)
def test_classify_heavy_by_program_and_script(cmd: tuple[str, ...]) -> None:
    assert _classify(*cmd) == "heavy"


@pytest.mark.parametrize("cmd", LIGHT_CMDS, ids=" ".join)
def test_classify_light_by_program_and_script(cmd: tuple[str, ...]) -> None:
    assert _classify(*cmd) == "light"


def _classify(*cmd: str, cwd: Path | None = None) -> str:
    res = subprocess.run(
        [sys.executable, str(HEAVY), "classify", "--", *cmd], capture_output=True, text=True, cwd=cwd
    )
    return res.stdout.strip()


def test_the_repos_heavy_patterns_still_override(tmp_path: Path) -> None:
    (tmp_path / "sdlc.json").write_text(json.dumps({"heavy": {"patterns": [r"\bmy-suite\b"]}}))
    assert _classify("./my-suite", "--all", cwd=tmp_path) == "heavy"
    assert _classify("./other", cwd=tmp_path) == "light"


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


# ---------------------------------------------------------------- 3.22.0: the machine queue

def test_the_queue_is_one_per_user_and_names_repo_worktree_and_job_group(tmp_path: Path) -> None:
    home = tmp_path / "home"
    env = {k: v for k, v in _env(tmp_path).items() if k != "SDLC_HEAVY_DIR"}
    state = home / ".local" / "state" / "sdlc" / "heavy" / "tickets"
    for extra, where in (({"HOME": str(home)}, state), ({"HOME": str(home), "XDG_STATE_HOME": str(tmp_path / "x")}, tmp_path / "x" / "sdlc" / "heavy" / "tickets")):
        e = {k: v for k, v in env.items() if k != "XDG_STATE_HOME"} | extra
        res = _heavy(tmp_path, "run", "--", "sh", "-c", f"sleep 0.5; cat {where}/*.json", env=e)  # the wrapper lists the group just after the start
        ticket = json.loads(res.stdout)
        assert ticket["pid"] and ticket["pgid"] and ticket["repo"] and ticket["worktree"], res.stderr
        assert ticket["pgid"] != ticket["pid"], "the job's own group, not the wrapper's"


def test_the_old_git_dir_queue_is_ignored(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    old = repo / ".git" / "sdlc-heavy" / "tickets"
    old.mkdir(parents=True)
    (old / f"{time.time_ns():020d}-1.json").write_text(json.dumps({"pid": os.getpid(), "cmd": ["x"], "slot": 0}))
    env = {k: v for k, v in _env(tmp_path).items() if k != "SDLC_HEAVY_DIR"} | {"HOME": str(tmp_path / "h")}
    res = _heavy(tmp_path, "run", "--wait-timeout", "1", "--", "true", env=env, cwd=repo)
    assert res.returncode == 0, "a live ticket in the old place blocks nothing"


# ---------------------------------------------------------------- 3.22.0: kill the job, not only the wrapper

def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_a_dead_wrappers_job_is_killed_before_its_slot_is_freed(tmp_path: Path) -> None:
    job = subprocess.Popen(["sleep", "30"], start_new_session=True)
    (tmp_path / "tickets").mkdir()
    pid = _dead_pid()
    (tmp_path / "tickets" / f"{time.time_ns():020d}-{pid}.json").write_text(
        json.dumps({"pid": pid, "cmd": ["sleep"], "slot": 0, "pgid": job.pid})
    )
    assert _heavy(tmp_path, "run", "--", "true").returncode == 0
    assert job.wait(timeout=5) == -9, "the orphaned job was killed"


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGHUP, signal.SIGINT])
def test_a_signal_to_the_wrapper_kills_the_job_and_frees_the_slot(tmp_path: Path, sig: int) -> None:
    wrapper = _popen(tmp_path, "run", "--", "sleep", "30")
    _until(lambda: _tickets(tmp_path) and json.loads(_tickets(tmp_path)[0].read_text()).get("pgid"), "job started")
    pgid = json.loads(_tickets(tmp_path)[0].read_text())["pgid"]
    wrapper.send_signal(sig)
    assert wrapper.wait(timeout=10) == 128 + sig
    _until(lambda: not _alive(pgid), "the job to die")
    assert _heavy(tmp_path, "run", "--wait-timeout", "2", "--", "true").returncode == 0


def test_results_are_written_by_rename(tmp_path: Path) -> None:
    job = _heavy(tmp_path, "submit", "--", "true").stdout.split()[0]
    assert _heavy(tmp_path, "wait", job, "--timeout", "10").returncode == 0
    assert sorted(p.name for p in (tmp_path / "jobs" / job).iterdir()) == ["job.json", "log.txt", "result.json"]


def test_a_submit_inside_a_slot_still_queues(tmp_path: Path) -> None:
    out = tmp_path / "out"
    inner = (
        f"python3 {HEAVY} submit -- sh -c 'echo $SDLC_HEAVY_SLOT > {out}' > {tmp_path}/id; "
        f"sleep 1; test ! -e {out}"
    )  # the submitted job must be waiting behind this holder, not running at once
    assert _heavy(tmp_path, "run", "--", "sh", "-c", inner).returncode == 0
    job = (tmp_path / "id").read_text().split()[0]
    assert _heavy(tmp_path, "wait", job, "--timeout", "10").returncode == 0
    assert out.read_text().strip() == "0", "it ran later, in a slot of its own"


# ---------------------------------------------------------------- 3.22.0: a patient waiter

def _module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("heavy_under_test_q", HEAVY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hand_ticket(q: Path, pid: int, **extra: object) -> Path:
    (q / "tickets").mkdir(exist_ok=True)
    path = q / "tickets" / f"{time.time_ns() - 10**9:020d}-{pid}.json"
    path.write_text(json.dumps({"pid": pid, "cmd": ["held"], "slot": 0, "since": time.time(), "started": time.time(), **extra}))
    return path


def test_a_patient_waiter_has_no_deadline_while_the_holder_is_within_its_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading

    monkeypatch.setenv("SDLC_HEAVY_DIR", str(tmp_path))
    monkeypatch.setenv("SDLC_HEAVY_POLL", "0.05")
    mod = _module()
    held = _hand_ticket(tmp_path, os.getpid(), cap=0)  # alive, no run deadline
    threading.Timer(1.0, held.unlink).start()
    t0 = time.time()
    q, ticket, slot = mod.acquire(["gate"], "gate", {"slots": 1}, 0.3, patient=True)
    assert slot == 0 and time.time() - t0 >= 0.9, "waited past the 0.3 s wait deadline"
    q.leave(ticket)


def test_a_patient_waiter_still_times_out_on_a_holder_past_its_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SDLC_HEAVY_DIR", str(tmp_path))
    monkeypatch.setenv("SDLC_HEAVY_POLL", "0.05")
    monkeypatch.setenv("SDLC_HEAVY_GRACE", "0")
    mod = _module()
    _hand_ticket(tmp_path, os.getpid(), cap=1, started=time.time() - 100)
    with pytest.raises(mod.SlotTimeout, match="no slot after"):
        mod.acquire(["gate"], "gate", {"slots": 1}, 0.3, patient=True)
    assert len(_tickets(tmp_path)) == 1, "the waiter's own ticket is gone"
    with pytest.raises(mod.SlotTimeout):  # and an impatient waiter never waits past its deadline
        _hand_ticket(tmp_path, os.getpid(), cap=0)
        mod.acquire(["x"], "job", {"slots": 1}, 0.3)


# ---------------------------------------------------------------- 3.22.0: prune

def test_prune_drops_old_and_orphaned_jobs_and_keeps_the_rest(tmp_path: Path) -> None:
    jobs = tmp_path / "jobs"
    def job(name: str, age: float, pid: int | None, result: bool) -> Path:
        d = jobs / name
        d.mkdir(parents=True)
        if pid is not None:
            (d / "job.json").write_text(json.dumps({"pid": pid}))
        if result:
            (d / "result.json").write_text("{}")
        os.utime(d, (time.time() - age, time.time() - age))
        return d
    old = job("old", 8 * 86400, os.getpid(), True)
    orphan = job("orphan", 600, _dead_pid(), False)
    finished = job("finished", 600, _dead_pid(), True)
    running = job("running", 600, os.getpid(), False)
    fresh = job("fresh", 1, None, False)  # just submitted: no pid yet
    assert _heavy(tmp_path, "prune").returncode == 0
    assert [d.exists() for d in (old, orphan, finished, running, fresh)] == [False, False, True, True, True]


# ---------------------------------------------------------------- 3.22.0: the guard in hook mode

def test_the_hook_refuses_a_helpers_write_in_the_main_folder(tmp_path: Path) -> None:
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q")
    _git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", "-b", "feat", str(wt))

    def call(cmd: str, cwd: Path, agent: str | None = "a1") -> int:
        payload = {"cwd": str(cwd), "tool_input": {"command": cmd}}
        if agent:
            payload["agent_id"] = agent
        return _guard(cwd, payload).returncode

    assert call("pnpm install", main) == 2, "a write in the main folder blocks (exit 2), it does not just warn"
    assert call("touch x.txt", main) == 2
    assert call("echo hi > x.txt", main) == 2 and call("cat x.txt 2>/dev/null", main) == 0
    stderr = _guard(main, {"cwd": str(main), "agent_id": "a1", "tool_input": {"command": "touch x"}}).stderr
    assert "main working folder" in stderr
    for mutating in ("git commit -m x", "git add .", "git checkout -b y", "git stash", "git reset --hard",
                     "git push", "git rebase main", "git worktree add ../z", "git branch -D feat", "sed -i s/a/b/ f"):  # fmt: skip
        assert call(mutating, main) == 2, mutating
    for reading in ("git status", "git log -3", "git diff", "git branch", "git worktree list", "ls -la",
                    "pnpm lint", "grep -r x .", "git -C . show HEAD"):  # fmt: skip
        assert call(reading, main) == 0, reading
    assert call(f"cd {wt} && touch x", main) == 0, "the shell starts in the main folder; a cd leaves it"
    assert call(f"touch x && cd {wt}", main) == 2, "a write before the cd is still in the main folder"
    assert call("cd .. && touch x", main) == 0, "outside the main folder"
    assert call(f"cd {main} && touch x", wt) == 2, "a cd back into the main folder counts"
    assert call(f"git -C {wt} commit -m x", main) == 0 and call(f"git -C {main} commit -m x", wt) == 2
    assert call("touch x.txt", wt) == 0
    assert call("pnpm lint", main, agent=None) == 0, "the owner's own session is never refused"
    assert call("pnpm build", main) == 2, "an unqueued heavy command is still refused first"
    # the kit's self-queuing close is the one heavy command the hook lets through
    for gate in ("python3 scripts/verify_gate.py milestone m-1", "scripts/verify_gate.py project p",
                 "python3 /abs/x/scripts/verify_gate.py milestone m-1 --keep-going"):  # fmt: skip
        assert call(gate, wt) == 0 and call(gate, main) == 0, gate
    assert call("python3 scripts/verify_gate.py approve m-1", wt) == 0


def test_the_hook_fails_closed_on_a_cd_it_cannot_resolve(tmp_path: Path) -> None:
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q")
    _git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", "-b", "feat", str(wt))

    def call(cmd: str, cwd: Path) -> int:
        return _guard(cwd, {"cwd": str(cwd), "agent_id": "a1", "tool_input": {"command": cmd}}).returncode

    for unknown in ("cd $X && touch x", "cd `pwd` && touch x", "cd - && touch x", "cd \"$(dirname $F)\" && echo hi > x"):
        assert call(unknown, wt) == 2, unknown
        assert call(unknown, main) == 2, unknown
    assert call("cd $X && ls", wt) == 0, "reading is fine wherever it runs"
    assert call(f"cd $X && cd {wt} && touch x", main) == 0, "a later literal cd resolves it again"


@pytest.mark.parametrize("cmd", ["python3 -c print(1)", "node -e 1", "node --eval 1", "node -p 1", "python3 -c pass"])
def test_inline_interpreter_code_is_light_for_the_queue(cmd: str) -> None:
    assert _heavy_classify(cmd) == "light"


def test_inline_interpreter_code_counts_as_a_writer_only_in_the_main_folder(tmp_path: Path) -> None:
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q")
    _git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", "-b", "feat", str(wt))

    def call(cmd: str, cwd: Path) -> int:
        return _guard(cwd, {"cwd": str(cwd), "agent_id": "a1", "tool_input": {"command": cmd}}).returncode

    for inline in ("python3 -c 'open(\"x\", \"w\")'", "node -e 1", "node --eval 1", "node -p 1"):
        assert call(inline, main) == 2, inline
        assert call(inline, wt) == 0, inline
    assert call("cd $X && python3 -c pass", wt) == 2
    assert call(f"cd {wt} && python3 -c pass", main) == 0


def test_the_guard_reads_interpreter_flags_and_cd_options(tmp_path: Path) -> None:
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q")
    _git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", "-b", "feat", str(wt))

    def call(cmd: str, cwd: Path) -> int:
        return _guard(cwd, {"cwd": str(cwd), "agent_id": "a1", "tool_input": {"command": cmd}}).returncode

    for writer in ("python3 -X utf8 -c pass", "python3 -W ignore -c pass", "python3 -cprint(1)", "python3 -Ic pass",
                   "node --eval=1", "node --print 1", "node -r x -e 1", "node -pe 1"):  # fmt: skip
        assert call(writer, main) == 2, writer
        assert call(writer, wt) == 0, writer
    for reader in ("node -c app.js", "node --check app.js", "python3 -m pytest -p x", "python3 tool.py -c x", "node app.js -e 1"):
        assert call(reader, main) == 0, reader
    for unknown in ('cd -- "$X" && touch x', 'cd -P "$X" && touch x', "cd -L `pwd` && touch x"):
        assert call(unknown, wt) == 2, unknown
    assert call(f"cd -- {wt} && touch x", main) == 0 and call(f"cd -P {main} && touch x", wt) == 2
    # a computed cd leaves the folder unknown, but an absolute destination still names its own folder
    assert call("cd $X && echo hi > /tmp/sdlc-log.txt", wt) == 0
    assert call(f"cd $X && echo hi > {main}/x", wt) == 2
    assert call(f"cd $X && git -C {wt} commit -m x", main) == 0
    assert call(f"cd $X && git -C {main} commit -m x", wt) == 2


def test_inline_code_behind_a_runner_and_a_program_from_stdin_are_possible_writers(tmp_path: Path) -> None:
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q")
    _git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", "-b", "feat", str(wt))

    def call(cmd: str, cwd: Path) -> int:
        return _guard(cwd, {"cwd": str(cwd), "agent_id": "a1", "tool_input": {"command": cmd}}).returncode

    for writer in ("uv run python -c pass", "uv run --with x python3 -c pass", "poetry run python -c pass", "hatch run python -c pass",
                   "npx tsx -e 1", "npx --yes node -e 1", "pnpm exec node -p 1", "yarn dlx node --eval 1",
                   "python3 -", "node -", "python3 - arg", "uv run python -"):  # fmt: skip
        assert call(writer, main) == 2, writer
        assert call(writer, wt) == 0, writer
    for writer in ("uv run --python 3.12 python -c pass", "uv run --with rich python3 -c pass", "python3 <<EOF\nprint(1)\nEOF", "cat x.py | python3", "python3 < x.py"):
        assert call(writer, main) == 2, writer
    for reader in ("uv run python tool.py -c x", "npx prettier --check .", "pnpm exec node app.js -e 1", "yarn dlx cowsay hi",
                   "uv run rg python -c", "uv run --with rich rg node -e x", "python3 --version", "uv run python --version"):  # fmt: skip
        assert call(reader, main) == 0, reader


@pytest.mark.parametrize("cmd", [
    'npm exec -c "pnpm build"', "npm exec --call 'playwright test'", "npx -c 'vite build'", "npx --call='playwright test'",
    "npx -cvite", "pnpm exec -c 'pnpm build'", 'yarn exec "pnpm build"', "yarn exec -c 'vite build'",
    "bunx playwright test", "bun x vite build", "pipx run playwright test", "pdm run playwright test", "rye run playwright test",
    "bun run build", "npx --yes -c 'sh -c \"pnpm test\"'",
])  # fmt: skip
def test_a_runner_command_string_and_the_newer_runners_are_read_for_heavy_work(cmd: str) -> None:
    assert _heavy_classify(cmd) == "heavy", cmd


@pytest.mark.parametrize("cmd", ["npm exec -c 'pnpm lint'", "npx -c 'echo build'", "bunx prettier --check .", "pipx run black --check .", "pdm run rg build", "bun x tsc --noEmit"])
def test_a_runner_command_string_of_light_work_stays_light(cmd: str) -> None:
    assert _heavy_classify(cmd) == "light", cmd


def test_a_command_behind_any_runner_and_a_shape_the_parser_cannot_read_are_possible_writers(tmp_path: Path) -> None:
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q")
    _git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", "-b", "feat", str(wt))

    def call(cmd: str, cwd: Path) -> int:
        return _guard(cwd, {"cwd": str(cwd), "agent_id": "a1", "tool_input": {"command": cmd}}).returncode

    for writer in (
        'npm exec -c "rm -rf x"', "npm exec --call 'touch x'", "npx -c 'git commit -m x'", "npx --call='tee x'", "npx -ctouch", "pnpm exec -c 'rm x'",
        "yarn exec 'rm -rf x'", "yarn exec -c 'cp a b'", "npx -c 'node -e 1'", "npx -c 'echo hi; rm x'", "npx -c 'sh -c \"rm x\"'",
        "bunx cp a b", "bun x rm x", "bunx tsx -e 1", "bun x node -e 1", "pipx run rm x", "pipx run python -c 1", "pdm run rm x", "pdm run python -c pass",
        "rye run cp a b", "rye run python -", "uv run cp a b", "poetry run rm x", "npx --yes rm x", "pnpm dlx touch x",
        "npx --mystery-flag cp a b", "uv run --mystery cp a b", "pnpm exec -w cp a b", "npx -c",
    ):  # fmt: skip
        assert call(writer, main) == 2, writer
        assert call(writer, wt) == 0, writer
    for reader in ("npx -c 'echo hi'", "npx -y prettier --check .", "bunx cowsay hi", "bun x prettier --check .", "pipx run black --check .", "pdm run rg x",
                   "rye run rg x", "npm exec -c 'ls'", "uv run --with rich rg node -e x", "pnpm exec node app.js -e 1", "yarn dlx cowsay hi", "npx --no-install prettier -c .",
                   "npm exec --yes -- prettier --check ."):  # fmt: skip
        assert call(reader, main) == 0, reader


@pytest.mark.parametrize("cmd", [
    "cargo build", "cargo +nightly test", "uv build", "yarn workspace app run build", "go build ./...", "go test ./...",
    "mvn package", "./mvnw verify", "gradle build", "./gradlew test",
])  # fmt: skip
def test_real_build_and_test_commands_are_heavy(cmd: str) -> None:
    assert _heavy_classify(cmd) == "heavy"


@pytest.mark.parametrize("cmd", ["cargo fmt", "cargo clippy", "go vet ./...", "uv sync", "mvn -v", "yarn workspace app run lint"])
def test_neighbouring_light_commands_stay_light(cmd: str) -> None:
    assert _heavy_classify(cmd) == "light"


def _heavy_classify(cmd: str) -> str:
    import shlex

    out = subprocess.run([sys.executable, str(HEAVY), "classify", "--", *shlex.split(cmd)], capture_output=True, text=True)
    return out.stdout.strip()


def test_a_late_publisher_never_crashes_the_allocator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A ticket that sorts first but whose slot is already taken waits; it does not raise StopIteration."""
    monkeypatch.setenv("SDLC_HEAVY_DIR", str(tmp_path))
    mod = _module()
    q = mod.Queue(tmp_path, 1)
    t = tmp_path / "tickets"
    base = {"pid": os.getpid(), "cmd": ["x"], "kind": "job", "since": time.time(), "cap": 0}
    (t / "00000000000000000001-1.json").write_text(json.dumps({**base, "slot": None}))
    (t / "00000000000000000002-1.json").write_text(json.dumps({**base, "slot": 0}))
    slot, holders = q.try_take(t / "00000000000000000001-1.json")
    assert slot is None and holders and holders[0]["slot"] == 0


def test_the_arrival_name_is_made_under_the_publication_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDLC_HEAVY_DIR", str(tmp_path))
    mod = _module()
    q = mod.Queue(tmp_path, 1)
    a = q.enter(["a"], "job")
    b = q.enter(["b"], "job")
    assert a.name < b.name


def test_a_recycled_group_id_is_not_killed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDLC_HEAVY_DIR", str(tmp_path))
    mod = _module()
    victim = subprocess.Popen(["sleep", "30"], start_new_session=True)
    try:
        mod.kill_pgid(victim.pid, "Thu Jan  1 00:00:00 1970")  # recorded for another process: the id was recycled
        assert victim.poll() is None, "a different start time means a different process"
        mod.kill_pgid(victim.pid, mod.proc_start(victim.pid))
        assert victim.wait(5) != 0
    finally:
        victim.kill()


def test_leave_stops_every_group_the_ticket_lists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDLC_HEAVY_DIR", str(tmp_path))
    mod = _module()
    q = mod.Queue(tmp_path, 1)
    ticket = q.enter(["gate"], "gate")
    check = subprocess.Popen(["sleep", "30"], start_new_session=True)
    q.track_group(ticket, check.pid)
    other = subprocess.Popen(["sleep", "30"], start_new_session=True)
    q.track_group(ticket, other.pid)
    q.track_group(ticket, other.pid, on=False)  # finished checks are forgotten
    try:
        q.leave(ticket)
        assert check.wait(5) != 0 and other.poll() is None
    finally:
        other.kill()
        check.kill()


def test_a_cancelled_wrapper_leaves_no_check_behind(tmp_path: Path) -> None:
    """`heavy.py run -- <job that starts a session of its own and lists it on the ticket>`: SIGTERM to the wrapper."""
    pidfile = tmp_path / "check.pid"
    job = (
        "import os, subprocess, sys; sys.path.insert(0, os.path.dirname(os.environ['H'])); import heavy; "
        "q = heavy.Queue(heavy.queue_dir(), 1); "
        f"p = subprocess.Popen(['sleep', '60'], start_new_session=True); open({str(pidfile)!r}, 'w').write(str(p.pid)); "
        "q.track_group(__import__('pathlib').Path(os.environ['SDLC_HEAVY_TICKET']), p.pid); import time; time.sleep(60)"
    )
    wrapper = _popen(tmp_path, "run", "--", sys.executable, "-c", job, H=str(HEAVY))
    _until(lambda: pidfile.exists() and pidfile.read_text(), "the check to start")
    time.sleep(0.5)
    check = int(pidfile.read_text())
    assert _alive(check)
    wrapper.terminate()
    wrapper.wait(10)
    _until(lambda: not _alive(check), "the check to die with the cancelled wrapper")


def test_prune_never_removes_a_running_job_and_tolerates_a_vanished_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDLC_HEAVY_DIR", str(tmp_path))
    mod = _module()
    running = tmp_path / "jobs" / "running"
    running.mkdir(parents=True)
    (running / "job.json").write_text(json.dumps({"pid": os.getpid()}))
    os.utime(running, (time.time() - 30 * 86400,) * 2)
    gone = tmp_path / "jobs" / "gone"
    gone.mkdir()
    real = Path.stat

    def stat(self, *a, **k):  # another prune removed it between the listing and the stat
        if self.name == "gone":
            raise FileNotFoundError(self)
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "stat", stat)
    assert mod.prune_jobs() == 0 and running.exists()
