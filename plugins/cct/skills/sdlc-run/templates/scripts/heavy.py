"""The heavy-job queue: builds, app servers, browser tests, captures and the full test suite take a
slot; everything else runs without one.

    python3 scripts/heavy.py run [--slots N] [--auto] [--wait-timeout S] [--run-timeout S] [--kind K] -- CMD...
    python3 scripts/heavy.py submit [same options] -- CMD...   # detached: prints a job id and returns
    python3 scripts/heavy.py wait JOB [--timeout S]            # exit code of the job; 75 on the deadline
    python3 scripts/heavy.py status                            # who holds a slot, who waits
    python3 scripts/heavy.py classify -- CMD...                # heavy or light
    python3 scripts/heavy.py guard-main [--hook]               # main folder refusal; as a hook: a helper's unqueued heavy call

One heavy job at a time per machine by default (`sdlc.json` `heavy.slots`, env SDLC_HEAVY_SLOTS or
`--slots`). Tickets live in `<git common dir>/sdlc-heavy/`, so every worktree of a repo shares one
queue; first come, first served. A ticket whose process is dead is dropped, whether it held a slot
or waited, so a killed helper never blocks the line. A waiter prints who holds the slot (pid, command,
worktree, age). The job gets SDLC_HEAVY_SLOT, SDLC_APP_PORT and SDLC_STUB_PORT (`heavy.portBase` +
10 x slot, +1), so ports come from the slot, never from the worktree path. A job started under a held
slot (the env marker SDLC_HEAVY_HOLDER names a live process) passes straight through, so
`verify_gate.py milestone` run inside a slot does not wait for itself.

Deadlines (never wait forever): `--wait-timeout` (config `heavy.waitTimeout`, default 1800 s) exits 75
naming the holder; `--run-timeout` (`heavy.runTimeout`, default 3600 s) kills the job and exits 124.
0 turns a deadline off. Env SDLC_HEAVY_DIR moves the queue (tests).

Written by `sdlc-run adopt` from the kit; edit the kit, not this copy. stdlib only (POSIX: fcntl).
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

WAIT_TIMEOUT = 75  # EX_TEMPFAIL: the slot was never free; nothing ran
RUN_TIMEOUT = 124  # the same code timeout(1) uses
GUARD_REFUSED = 3
DEFAULTS = {"slots": 1, "waitTimeout": 1800, "runTimeout": 3600, "portBase": 4100}
# Heavy: builds, app servers, browsers, captures. Light checks (lint, types, unit tests on a
# touched file, a database test against the local container) never wait. The full test suite is
# heavy, but "full" is the repo's word: list its command in `heavy.patterns` (checks.milestone
# commands belong there).
HEAVY = (
    r"\b(build|next\s+dev|vite|storybook|playwright|cypress|e2e|capture|screenshots?)\b"
    r"|\b(pnpm|npm|yarn|bun)\s+(run\s+)?(dev|start|serve)\b"
)


def git_out(*args: str, cwd: str | None = None) -> str:
    res = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)
    return res.stdout.strip() if res.returncode == 0 else ""


def config() -> dict:
    cfg = dict(DEFAULTS)
    root = git_out("rev-parse", "--show-toplevel") or os.getcwd()
    try:
        data = json.loads((Path(root) / "sdlc.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    section = data.get("heavy") if isinstance(data, dict) else None
    cfg.update(section if isinstance(section, dict) else {})
    if os.environ.get("SDLC_HEAVY_SLOTS"):
        cfg["slots"] = int(os.environ["SDLC_HEAVY_SLOTS"])
    return cfg


def queue_dir() -> Path:
    if os.environ.get("SDLC_HEAVY_DIR"):
        return Path(os.environ["SDLC_HEAVY_DIR"])
    common = git_out("rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common or ".git") / "sdlc-heavy"


def alive(pid: int) -> bool:
    # shortcut: a recycled PID looks alive, so a dead holder's ticket can outlive it until that
    # PID exits; upgrade to a start-time check if that is ever seen.
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Queue:
    def __init__(self, root: Path, slots: int) -> None:
        self.root, self.slots = root, max(1, slots)
        (root / "tickets").mkdir(parents=True, exist_ok=True)

    def _locked(self):
        f = open(self.root / "queue.lock", "a+")
        fcntl.flock(f, fcntl.LOCK_EX)
        return f

    def _live(self) -> list[tuple[Path, dict]]:
        """Tickets in arrival order; the dead ones are removed on the way."""
        out = []
        for path in sorted((self.root / "tickets").glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = None
            if isinstance(data, dict) and isinstance(data.get("pid"), int) and alive(data["pid"]):
                out.append((path, data))
            else:
                path.unlink(missing_ok=True)
        return out

    def enter(self, cmd: list[str], kind: str) -> Path:
        path = self.root / "tickets" / f"{time.time_ns():020d}-{os.getpid()}.json"
        data = {
            "pid": os.getpid(), "cmd": cmd, "kind": kind, "since": time.time(),
            "worktree": git_out("rev-parse", "--show-toplevel") or os.getcwd(), "slot": None,
        }  # fmt: skip
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def try_take(self, ticket: Path) -> tuple[int | None, list[dict]]:
        """(slot, []) when this ticket is among the first `slots` live ones, else (None, holders)."""
        with self._locked():
            live = self._live()
            names = [p for p, _ in live]
            if ticket not in names:
                raise RuntimeError("ticket vanished")
            ahead = names.index(ticket)
            if ahead < self.slots:
                used = {d["slot"] for p, d in live if p != ticket and d.get("slot") is not None}
                slot = next(i for i in range(self.slots) if i not in used)
                data = dict(live[ahead][1], slot=slot, started=time.time())
                ticket.write_text(json.dumps(data), encoding="utf-8")
                return slot, []
            return None, [d for _, d in live[: self.slots]]

    def leave(self, ticket: Path) -> None:
        ticket.unlink(missing_ok=True)


def holder_text(holders: list[dict]) -> str:
    return "; ".join(
        f"pid {h['pid']} `{' '.join(h.get('cmd', []))}` in {h.get('worktree', '?')} "
        f"for {int(time.time() - h.get('started', h.get('since', time.time())))}s"
        for h in holders
    )


def acquire(cmd: list[str], kind: str, cfg: dict, wait_timeout: float):
    """(queue, ticket, slot), or exit 75 once the wait deadline passes."""
    q = Queue(queue_dir(), int(cfg["slots"]))
    ticket = q.enter(cmd, kind)
    poll = float(os.environ.get("SDLC_HEAVY_POLL", "1"))
    deadline = time.time() + wait_timeout if wait_timeout > 0 else None
    told = False
    try:
        while True:
            slot, holders = q.try_take(ticket)
            if slot is not None:
                return q, ticket, slot
            if not told:
                print(f"heavy: waiting for a slot held by {holder_text(holders)}", file=sys.stderr)
                told = True
            if deadline is not None and time.time() > deadline:
                q.leave(ticket)
                print(
                    f"heavy: no slot after {wait_timeout:g}s (held by {holder_text(holders)}); "
                    "nothing ran. Wait for the holder or raise heavy.waitTimeout.",
                    file=sys.stderr,
                )
                sys.exit(WAIT_TIMEOUT)
            time.sleep(poll)
    except BaseException:
        q.leave(ticket)
        raise


def is_heavy(cmd: list[str], cfg: dict) -> bool:
    text = " ".join(cmd)
    patterns = [HEAVY] + [p for p in cfg.get("patterns", []) if isinstance(p, str)]
    return any(re.search(p, text) for p in patterns)


def run_command(cmd: list[str], env: dict, run_timeout: float) -> int:
    proc = subprocess.Popen(cmd, env=env, start_new_session=True)

    def stop(signum, _frame) -> None:
        kill_group(proc)
        sys.exit(128 + signum)

    old = signal.signal(signal.SIGTERM, stop)
    try:
        return proc.wait(timeout=run_timeout if run_timeout > 0 else None)
    except subprocess.TimeoutExpired:
        kill_group(proc)
        print(
            f"heavy: run deadline of {run_timeout:g}s passed; the job was killed. "
            "Hand the unchanged evidence to its owner or raise heavy.runTimeout.",
            file=sys.stderr,
        )
        return RUN_TIMEOUT
    except KeyboardInterrupt:
        kill_group(proc)
        raise
    finally:
        signal.signal(signal.SIGTERM, old)


def kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    proc.wait()


def cmd_run(args, cmd: list[str]) -> int:
    cfg = config()
    env = dict(os.environ)
    held = env.get("SDLC_HEAVY_HOLDER", "")
    wait = cfg["waitTimeout"] if args.wait_timeout is None else args.wait_timeout
    run = cfg["runTimeout"] if args.run_timeout is None else args.run_timeout
    if args.slots:
        cfg["slots"] = args.slots
    if (held.isdigit() and alive(int(held))) or (args.auto and not is_heavy(cmd, cfg)):
        return run_command(cmd, env, run)  # already under a slot, or a light command
    q, ticket, slot = acquire(cmd, args.kind, cfg, wait)
    port = int(cfg["portBase"]) + 10 * slot
    env.update(
        SDLC_HEAVY_HOLDER=str(os.getpid()), SDLC_HEAVY_SLOT=str(slot),
        SDLC_APP_PORT=str(port), SDLC_STUB_PORT=str(port + 1),
    )  # fmt: skip
    try:
        return run_command(cmd, env, run)
    finally:
        q.leave(ticket)


def write_result(job: Path | None, status: str, code: int) -> None:
    if job:
        (job / "result.json").write_text(
            json.dumps({"status": status, "exit": code, "finished": time.time()}), encoding="utf-8"
        )


def cmd_run_job(args, cmd: list[str]) -> int:
    job = Path(args.job) if args.job else None
    try:
        code = cmd_run(args, cmd)
    except SystemExit as e:  # the wait deadline, or a signal
        code = e.code if isinstance(e.code, int) else 1
    status = {0: "done", WAIT_TIMEOUT: "wait-timeout", RUN_TIMEOUT: "timeout"}.get(code, "failed")
    write_result(job, status, code)
    return code


def cmd_submit(args, cmd: list[str]) -> int:
    job_id = f"{time.time_ns()}"
    job = queue_dir() / "jobs" / job_id
    job.mkdir(parents=True)
    argv = [
        sys.executable,
        os.path.abspath(__file__),
        "run",
        "--job",
        str(job),
        "--kind",
        args.kind,
    ]
    for flag, value in (("--slots", args.slots), ("--wait-timeout", args.wait_timeout),
                        ("--run-timeout", args.run_timeout)):  # fmt: skip
        if value is not None:
            argv += [flag, str(value)]
    if args.auto:
        argv.append("--auto")
    with open(job / "log.txt", "wb") as log:
        proc = subprocess.Popen(
            argv + ["--", *cmd], stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True,
        )  # fmt: skip
    (job / "job.json").write_text(json.dumps({"pid": proc.pid, "cmd": cmd}), encoding="utf-8")
    print(f"{job_id} log={job / 'log.txt'} result={job / 'result.json'}")
    return 0


def cmd_wait(args) -> int:
    job = queue_dir() / "jobs" / args.job
    deadline = time.time() + args.timeout if args.timeout > 0 else None
    poll = float(os.environ.get("SDLC_HEAVY_POLL", "1"))
    while not (job / "result.json").exists():
        info = {}
        try:
            info = json.loads((job / "job.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        if not job.is_dir() or (
            info.get("pid") and not alive(info["pid"]) and not (job / "result.json").exists()
        ):
            time.sleep(poll)  # the result may be landing now
            if (job / "result.json").exists():
                break
            print(
                f"heavy: job {args.job} is gone without a result; see {job / 'log.txt'}",
                file=sys.stderr,
            )
            return 1
        if deadline is not None and time.time() > deadline:
            print(f"heavy: job {args.job} not finished after {args.timeout:g}s", file=sys.stderr)
            return WAIT_TIMEOUT
        time.sleep(poll)
    result = json.loads((job / "result.json").read_text(encoding="utf-8"))
    print(f"{result['status']} exit={result['exit']} log={job / 'log.txt'}")
    return int(result["exit"])


def cmd_status() -> int:
    q = Queue(queue_dir(), int(config()["slots"]))
    with q._locked():
        live = q._live()
    if not live:
        print("heavy: idle")
    for _, d in live:
        state = f"holding slot {d['slot']}" if d.get("slot") is not None else "waiting"
        print(f"{state}: pid {d['pid']} `{' '.join(d.get('cmd', []))}` in {d.get('worktree', '?')}")
    return 0


READ_ONLY = {"git", "gh", "cat", "ls", "head", "tail", "grep", "rg", "echo", "find", "sed", "cd", "test", "wc"}
QUEUED = r"heavy\.py\s+(run|submit)\b"


def unqueued_heavy(command: str, cfg: dict) -> bool:
    """A heavy shell command that does not go through the queue. A line is split into its segments;
    reading and version-control tools are never heavy (a commit message may say "build")."""
    if re.search(QUEUED, command):
        return False
    for segment in re.split(r"&&|\|\||[;|\n]", command):
        words = segment.split()
        while words and re.fullmatch(r"\w+=\S*", words[0]):  # leading VAR=value
            words = words[1:]
        if words and words[0] not in READ_ONLY and is_heavy([segment], cfg):
            return True
    return False


def cmd_guard(args) -> int:
    """Without --hook: helper commands never run in the main working folder (exit 3). With --hook, a
    PreToolUse payload on stdin: refuse (exit 2) only a subagent's heavy command that does not go
    through the queue. A subagent's call carries `agent_id`; every field is read defensively, since
    the owner's own session may omit it, and anything unreadable is allowed."""
    if not args.hook:
        cwd = os.getcwd()
        gitdir = git_out("rev-parse", "--path-format=absolute", "--absolute-git-dir", cwd=cwd)
        common = git_out("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=cwd)
        if gitdir and gitdir == common:
            print(
                f"heavy: {cwd} is the main working folder. A helper works in its own worktree: "
                "run `git worktree list`, `cd` into the one your prompt names and repeat the command.",
                file=sys.stderr,
            )
            return GUARD_REFUSED
        return 0
    try:
        payload = json.load(sys.stdin)
        agent = payload.get("agent_id")
        command = (payload.get("tool_input") or {}).get("command")
    except (ValueError, AttributeError):
        return 0
    if not agent or not isinstance(command, str) or not unqueued_heavy(command, config()):
        return 0
    print(
        "heavy: a helper's heavy command goes through the queue, one at a time per machine. "
        f"Run it as `python3 scripts/heavy.py run -- {command.strip()}` (or `submit`, then `wait`).",
        file=sys.stderr,
    )
    return 2


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[:1]):
        print(__doc__)
        return 0
    cmd: list[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, cmd = argv[:i], argv[i + 1 :]
    ap = argparse.ArgumentParser(prog="heavy.py")
    sub = ap.add_subparsers(dest="verb", required=True)
    for name in ("run", "submit"):
        p = sub.add_parser(name)
        p.add_argument("--slots", type=int)
        p.add_argument("--auto", action="store_true")
        p.add_argument("--wait-timeout", type=float)
        p.add_argument("--run-timeout", type=float)
        p.add_argument("--kind", default="job")
        if name == "run":
            p.add_argument("--job")
    sub.add_parser("classify")
    sub.add_parser("status")
    w = sub.add_parser("wait")
    w.add_argument("job")
    w.add_argument("--timeout", type=float, default=0)
    g = sub.add_parser("guard-main")
    g.add_argument("--hook", action="store_true")
    args = ap.parse_args(argv)
    if args.verb in ("run", "submit", "classify") and not cmd:
        ap.error(f"{args.verb} needs a command after `--`")
    if args.verb == "run":
        return cmd_run_job(args, cmd)
    if args.verb == "submit":
        return cmd_submit(args, cmd)
    if args.verb == "classify":
        print("heavy" if is_heavy(cmd, config()) else "light")
        return 0
    if args.verb == "wait":
        return cmd_wait(args)
    if args.verb == "status":
        return cmd_status()
    return cmd_guard(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
