"""The heavy-job queue: builds, app servers, browser tests, captures and the full test suite take a
slot; everything else runs without one.

    python3 scripts/heavy.py run [--slots N] [--auto] [--wait-timeout S] [--run-timeout S] [--kind K] -- CMD...
    python3 scripts/heavy.py submit [same options] -- CMD...   # detached: prints a job id and returns
    python3 scripts/heavy.py wait JOB [--timeout S]            # exit code of the job; 75 on the deadline
    python3 scripts/heavy.py status                            # who holds a slot, who waits
    python3 scripts/heavy.py classify -- CMD...                # heavy or light
    python3 scripts/heavy.py prune                             # drop job logs older than 7 days and orphaned jobs
    python3 scripts/heavy.py guard-main [--hook]               # main folder refusal; as a hook: a helper's unqueued heavy call or write in the main folder

One heavy job at a time per machine by default (`sdlc.json` `heavy.slots`, env SDLC_HEAVY_SLOTS or
`--slots`). Tickets live in one per-user machine folder, `${SDLC_HEAVY_DIR:-${XDG_STATE_HOME:-
$HOME/.local/state}/sdlc/heavy}`, so every worktree of every repo shares one queue and one set of
slots and ports; first come, first served. Each ticket names its repo, worktree and job process group.
A ticket whose wrapper process is dead is dropped, whether it held a slot or waited, and its process
group is killed first, so a killed helper never blocks the line and never leaves a job running behind
a free slot. A waiter prints who holds the slot (pid, command, worktree, age). The job gets SDLC_HEAVY_SLOT, SDLC_APP_PORT and SDLC_STUB_PORT (`heavy.portBase` +
10 x slot, +1), so ports come from the slot, never from the worktree path. A job started under a held
slot (the env marker SDLC_HEAVY_HOLDER names a live process) passes straight through, so
`verify_gate.py milestone` run inside a slot does not wait for itself.

Deadlines (never wait forever): `--wait-timeout` (config `heavy.waitTimeout`, default 1800 s) exits 75
naming the holder; `--run-timeout` (`heavy.runTimeout`, default 3600 s) kills the job and exits 124.
0 turns a deadline off. The milestone gate waits without a deadline while the holder is within its own
run deadline (see `acquire(patient=True)`). Env SDLC_HEAVY_DIR moves the queue (tests).

Written by `sdlc-run adopt` from the kit; edit the kit, not this copy. stdlib only (POSIX: fcntl).
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

WAIT_TIMEOUT = 75  # EX_TEMPFAIL: the slot was never free; nothing ran
RUN_TIMEOUT = 124  # the same code timeout(1) uses
GUARD_REFUSED = 3
DEFAULTS = {"slots": 1, "waitTimeout": 1800, "runTimeout": 3600, "portBase": 4100}
# Heavy is decided by the program and the script it runs, never by a word anywhere in the line: a
# build, an app server, a browser test, a capture, the full test suite (`npm test`), a smoke run and
# the milestone close. Light: lint, format, typecheck, a unit test of touched files (`vitest run x`,
# `pytest`), git. A repo's own full-suite or E2E commands go in `heavy.patterns` (regexes over the
# command line; `adopt` seeds them from `checks.milestone`).
HEAVY_NAMES = {
    "build", "dev", "start", "serve", "preview", "test", "e2e", "capture", "screenshot",
    "screenshots", "smoke", "storybook", "playwright", "cypress",
}  # fmt: skip
HEAVY_PROGRAMS = {"playwright", "cypress", "storybook", "vite", "webpack"}
NEXT_HEAVY = {"build", "dev", "start"}
PACKAGE_MANAGERS = {"npm", "pnpm", "yarn", "bun"}
OPTION_ARGS = {"--filter", "-F", "--prefix", "--dir", "-C", "--cwd", "--workspace", "-w", "-p", "--package"}
MAVEN_GRADLE_HEAVY = {
    "build", "test", "package", "verify", "install", "assemble", "check", "integration-test", "bootRun",
}  # fmt: skip
ENV_ASSIGN = re.compile(r"\w+=\S*")


def heavy_name(name: str) -> bool:
    """A script or target whose first segment says it is heavy: `build`, `test:e2e`, `smoke:background`."""
    return re.split(r"[:_.\-]", name)[0] in HEAVY_NAMES


def words(args: list[str]) -> list[str]:
    """The positional words: options are dropped, and the value of an option that takes one."""
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a.startswith("-"):
            skip = a in OPTION_ARGS
        else:
            out.append(a)
    return out


def program_heavy(argv: list[str]) -> bool:
    while argv and ENV_ASSIGN.fullmatch(argv[0]):
        argv = argv[1:]
    if not argv:
        return False
    prog, rest = os.path.basename(argv[0]), argv[1:]
    stem = os.path.splitext(prog)[0]
    w = words(rest)
    if prog in PACKAGE_MANAGERS:
        if w[:1] == ["workspace"]:  # yarn workspace NAME run build
            w = w[2:]
        if w[:1] in (["exec"], ["dlx"], ["x"]):
            return program_heavy(w[1:])
        if w[:1] in (["run"], ["run-script"]):
            return len(w) > 1 and heavy_name(w[1])
        return bool(w) and heavy_name(w[0])
    if prog == "cargo":
        sub = [a for a in w if not a.startswith("+")][:1]  # `cargo +nightly build`
        return bool(sub) and sub[0] in ("build", "test", "bench", "nextest")
    if prog == "go":
        return w[:1] in (["build"], ["test"])
    if prog in ("mvn", "mvnw", "gradle", "gradlew"):
        return bool(set(w) & MAVEN_GRADLE_HEAVY)
    if prog == "uv" and w[:1] == ["build"]:
        return True
    if prog in ("npx", "bunx", "pnpx"):
        return program_heavy(w)
    if prog in ("uv", "poetry", "pipenv") and w[:1] == ["run"]:
        return program_heavy(rest[rest.index("run") + 1 :])
    if prog == "next":
        return w[:1] != [] and w[0] in NEXT_HEAVY
    if prog in HEAVY_PROGRAMS:
        return True
    if prog in ("make", "gmake", "just", "task"):
        return any(heavy_name(t) for t in w)
    if stem == "verify_gate":  # the milestone close is the heaviest job there is
        return bool({"milestone", "project"} & set(w))
    if prog.startswith("python") or prog in ("node", "sh", "bash", "zsh", "dash", "tsx", "ts-node", "deno"):
        it = iter(rest)
        for a in it:
            if a == "-m":
                return heavy_name(next(it, "").split(".")[0])
            if a in ("-c", "-e", "--eval", "-p"):
                return False
            if not a.startswith("-"):
                name = os.path.splitext(os.path.basename(a))[0]
                if name == "verify_gate":
                    return bool({"milestone", "project"} & set(words(rest[rest.index(a) + 1 :])))
                return name != "test" and heavy_name(name)
        return False
    if os.path.splitext(prog)[1] in (".py", ".sh", ".mjs", ".js", ".ts"):  # an executable script
        return stem != "test" and heavy_name(stem)
    return False


def git_out(*args: str, cwd: str | None = None) -> str:
    try:
        res = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)
    except OSError:  # no such folder (a `cd` to a place that does not exist yet)
        return ""
    return res.stdout.strip() if res.returncode == 0 else ""


def config(root: str | None = None) -> dict:
    cfg = dict(DEFAULTS)
    root = root or git_out("rev-parse", "--show-toplevel") or os.getcwd()
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
    state = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    return Path(state) / "sdlc" / "heavy"  # one per user: every repo on the machine shares the slots


def repo_identity() -> str:
    """The main checkout every worktree of this repo shares (the common git dir's parent)."""
    common = git_out("rev-parse", "--path-format=absolute", "--git-common-dir")
    if common.endswith("/.git"):
        return common[: -len("/.git")]
    return git_out("rev-parse", "--show-toplevel") or os.getcwd()


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


def proc_start(pid: int) -> str:
    """When the process began, as `ps` prints it ("" when there is no such process): with the id it
    names one process, so a recycled id is never taken for the one that died."""
    try:
        res = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True)
    except OSError:
        return ""
    return res.stdout.strip() if res.returncode == 0 else ""


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
                if isinstance(data, dict):
                    kill_ticket_groups(data)  # the wrapper died; its jobs must not outlive the slot
                path.unlink(missing_ok=True)
        return out

    def enter(self, cmd: list[str], kind: str, cap: float = 0) -> Path:
        """`cap` is the holder's own run deadline in seconds (0: none); a waiter reads it to tell a
        job that is merely long from one that outlived its own deadline. Arrival order is the file name,
        made under the lock that publishes the ticket, so a slow entrant never sorts ahead of one that
        already holds a slot."""
        data = {
            "pid": os.getpid(), "cmd": cmd, "kind": kind, "since": time.time(), "cap": cap,
            "repo": repo_identity(), "worktree": git_out("rev-parse", "--show-toplevel") or os.getcwd(),
            "slot": None, "pgid": None, "pstart": "", "groups": {},
        }  # fmt: skip
        with self._locked():  # a scan holds the lock; it never sees a ticket half written
            path = self.root / "tickets" / f"{time.time_ns():020d}-{os.getpid()}.json"
            self._write(path, data)
        return path

    @staticmethod
    def _write(path: Path, data: dict) -> None:
        tmp = path.with_name(f".{path.name}.tmp")  # not *.json: a scan skips it
        tmp.write_text(json.dumps(data), encoding="utf-8")
        os.replace(tmp, path)

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
                slot = next((i for i in range(self.slots) if i not in used), None)
                if slot is not None:  # none free: an entrant that published late is still waiting
                    self._write(ticket, dict(live[ahead][1], slot=slot, started=time.time()))
                    return slot, []
            return None, [d for _, d in live if d.get("slot") is not None] or [d for _, d in live[: self.slots]]

    def update(self, ticket: Path, mutate) -> None:
        """Rewrite one ticket under the lock: `mutate(data)` changes the dict in place."""
        with self._locked():
            try:
                data = json.loads(ticket.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return
            mutate(data)
            self._write(ticket, data)

    def record_pgid(self, ticket: Path, pgid: int) -> None:
        """Name the job's process group on the ticket (with its leader's start time), so a dead
        wrapper's job can be killed."""
        self.update(ticket, lambda d: d.update(pgid=pgid, pstart=proc_start(pgid)))

    def track_group(self, ticket: Path, pgid: int, on: bool = True) -> None:
        """Every check the close starts is a session of its own; the ticket lists the live ones, so the
        reaper and `leave` can stop them before the slot is reused."""
        start = proc_start(pgid) if on else ""

        def mutate(d: dict) -> None:
            groups = d.setdefault("groups", {})
            if on:
                groups[str(pgid)] = start
            else:
                groups.pop(str(pgid), None)

        self.update(ticket, mutate)

    def leave(self, ticket: Path) -> None:
        """Stop whatever the ticket still lists, then free the slot."""
        try:
            kill_ticket_groups(json.loads(ticket.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        ticket.unlink(missing_ok=True)


def kill_pgid(pgid: object, start: object = None) -> None:
    """SIGKILL a group, unless its leader id now belongs to another process (a recycled id): when a
    process with that id exists and began at another time than recorded, leave it alone. A group whose
    leader is gone but has members cannot have had its id recycled, so it is still ours."""
    if isinstance(pgid, int) and pgid > 1 and pgid != os.getpgrp():
        now = proc_start(pgid)
        if isinstance(start, str) and start and now and now != start:
            return
        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def kill_ticket_groups(data: dict) -> None:
    kill_pgid(data.get("pgid"), data.get("pstart"))
    groups = data.get("groups")
    for g, start in (groups.items() if isinstance(groups, dict) else []):
        if str(g).isdigit():
            kill_pgid(int(g), start)


class SlotTimeout(Exception):
    """The wait deadline passed with the slot still held; nothing ran."""


def holder_text(holders: list[dict]) -> str:
    return "; ".join(
        f"pid {h['pid']} `{' '.join(h.get('cmd', []))}` in {h.get('worktree', '?')} "
        f"for {int(time.time() - h.get('started', h.get('since', time.time())))}s"
        for h in holders
    )


def stuck(holders: list[dict], grace: float) -> bool:
    """Every holder outlived its own run deadline (plus `grace`): the queue is dead, not busy."""
    now = time.time()
    return all(
        h.get("cap") and now - h.get("started", h.get("since", now)) > h["cap"] + grace for h in holders
    )


def acquire(cmd: list[str], kind: str, cfg: dict, wait_timeout: float, cap: float = 0, patient: bool = False):
    """(queue, ticket, slot), or SlotTimeout once the wait deadline passes. `patient` (the milestone
    gate) keeps waiting while a holder is within its own run deadline and counts the wait deadline
    only once every holder is past it, so a long close never gives up on a busy machine."""
    q = Queue(queue_dir(), int(cfg["slots"]))
    ticket = q.enter(cmd, kind, cap)
    poll = float(os.environ.get("SDLC_HEAVY_POLL", "1"))
    grace = float(os.environ.get("SDLC_HEAVY_GRACE", "60"))
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
            if patient and wait_timeout > 0 and not stuck(holders, grace):
                deadline = time.time() + wait_timeout
            if deadline is not None and time.time() > deadline:
                q.leave(ticket)
                raise SlotTimeout(
                    f"heavy: no slot after {wait_timeout:g}s (held by {holder_text(holders)}); "
                    "nothing ran. Wait for the holder or raise heavy.waitTimeout."
                )
            time.sleep(poll)
    except BaseException:
        q.leave(ticket)
        raise


def is_heavy(cmd: list[str], cfg: dict) -> bool:
    if any(re.search(p, " ".join(cmd)) for p in cfg.get("patterns", []) if isinstance(p, str)):
        return True
    return any(program_heavy(argv) for seg in shell_segments(shlex.join(cmd)) for argv in inner_argv(seg))


def run_command(cmd: list[str], env: dict, run_timeout: float, on_start=None) -> int:
    proc = subprocess.Popen(cmd, env=env, start_new_session=True)
    if on_start:
        on_start(proc.pid)  # the group id equals the pid: a session of its own

    def stop(signum, _frame) -> None:
        kill_group(proc)
        sys.exit(128 + signum)

    signals = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)
    old = {s: signal.signal(s, stop) for s in signals}
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
    finally:
        for s, handler in old.items():
            signal.signal(s, handler)


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
    try:
        q, ticket, slot = acquire(cmd, args.kind, cfg, wait, cap=run)
    except SlotTimeout as e:
        print(e, file=sys.stderr)
        sys.exit(WAIT_TIMEOUT)
    port = int(cfg["portBase"]) + 10 * slot
    env.update(
        SDLC_HEAVY_HOLDER=str(os.getpid()), SDLC_HEAVY_SLOT=str(slot),
        SDLC_APP_PORT=str(port), SDLC_STUB_PORT=str(port + 1),
        SDLC_HEAVY_TICKET=str(ticket),  # a close inside the slot lists its checks' groups here
    )  # fmt: skip
    try:
        return run_command(cmd, env, run, lambda pgid: q.record_pgid(ticket, pgid))
    finally:
        q.leave(ticket)  # also stops every group the job listed on it


def write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.tmp")  # a reader never sees half a file
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_result(job: Path | None, status: str, code: int) -> None:
    if job:
        write_atomic(
            job / "result.json", json.dumps({"status": status, "exit": code, "finished": time.time()})
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
    env = {k: v for k, v in os.environ.items() if k != "SDLC_HEAVY_HOLDER"}  # a submit inside a slot still queues
    with open(job / "log.txt", "wb") as log:
        proc = subprocess.Popen(
            argv + ["--", *cmd], stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True, env=env,
        )  # fmt: skip
    write_atomic(job / "job.json", json.dumps({"pid": proc.pid, "cmd": cmd}))
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


JOB_KEEP_DAYS = 7


def prune_jobs() -> int:
    """Drop job folders older than a week, and orphans: no result and a wrapper that is gone (it died
    before it could write one). A finished job's result stays until a week old, so `wait` can read it."""
    jobs, gone, now = queue_dir() / "jobs", 0, time.time()
    for job in jobs.glob("*") if jobs.is_dir() else []:
        try:
            info = json.loads((job / "job.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            info = {}
        pid = info.get("pid")
        try:
            age = now - job.stat().st_mtime
        except OSError:  # another prune removed it first
            continue
        finished = (job / "result.json").exists()
        if not finished and isinstance(pid, int) and alive(pid):
            continue  # still running: its result has yet to be written, however old
        orphan = not finished
        if age > JOB_KEEP_DAYS * 86400 or (orphan and age > 60):  # a job just submitted has no pid yet
            shutil.rmtree(job, ignore_errors=True)
            gone += 1
    return gone


def cmd_prune() -> int:
    print(f"heavy: pruned {prune_jobs()} job folder(s)")
    return 0


READ_ONLY = {"git", "gh", "cat", "ls", "head", "tail", "grep", "rg", "echo", "sed", "cd", "test", "wc"}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", ";;"}
OPTION_VALUES = {"xargs": {"-n", "-I", "-P", "-L", "-d", "-E", "-s"}, "nice": {"-n"}, "env": {"-u", "-C", "-S"}}


def shell_segments(command: str) -> list[list[str]]:
    """The command split into argv lists at ; && || | & and parentheses. A guard for a careless agent,
    not a sandbox: an unparseable line is one segment of its plain words."""
    out: list[list[str]] = [[]]
    for line in command.split("\n"):  # a newline separates commands, whatever the quoting
        lex = shlex.shlex(line, posix=True, punctuation_chars=True)
        lex.whitespace_split, lex.commenters = True, "#"
        try:
            tokens = list(lex)
        except ValueError:
            tokens = line.split()
        out.append([])
        for token in tokens:
            if token in SEPARATORS:
                out.append([])
            else:
                out[-1].append(token)
    return [seg for seg in out if seg]


def inner_argv(argv: list[str]) -> list[list[str]]:
    """The commands a segment really runs. An argv the unwrapper cannot resolve stays itself."""
    return _inner(argv) or ([argv] if argv else [])


def _inner(argv: list[str]) -> list[list[str]]:
    """Wrappers (env, timeout, nice, nohup, time, command, exec, xargs, sh -c, bash -c, find -exec,
    env -S) are looked through to their inner command."""
    while argv and re.fullmatch(r"\w+=\S*", argv[0]):  # leading VAR=value
        argv = argv[1:]
    if not argv:
        return []
    first = os.path.basename(argv[0])
    rest = argv[1:]
    if first in ("sh", "bash", "zsh", "dash"):
        for i, a in enumerate(rest):
            if a.startswith("-") and "c" in a[1:] and i + 1 < len(rest):
                return [seg for line in shell_segments(rest[i + 1]) for seg in inner_argv(line)]
        return [argv]
    if first == "find":
        for i, a in enumerate(rest):
            if a in ("-exec", "-execdir", "-ok", "-okdir"):
                return inner_argv([t for t in rest[i + 1 :]][: next((j for j, t in enumerate(rest[i + 1 :]) if t in (";", "+")), None)])
        return [argv]
    if first in ("env", "timeout", "nice", "nohup", "time", "command", "exec", "xargs"):
        values = OPTION_VALUES.get(first, set())
        if first == "env":
            for j, a in enumerate(rest):  # env -S "cmd args": the string is a command line of its own
                if a in ("-S", "--split-string") and j + 1 < len(rest):
                    return inner_argv([w for line in shell_segments(rest[j + 1]) for w in line] + rest[j + 2 :])
                if a.startswith("--split-string="):
                    return inner_argv([w for line in shell_segments(a.split("=", 1)[1]) for w in line] + rest[j + 1 :])
                if a.startswith("-S") and len(a) > 2:
                    return inner_argv([w for line in shell_segments(a[2:]) for w in line] + rest[j + 1 :])
        i = 0
        while i < len(rest) and (rest[i].startswith("-") or re.fullmatch(r"\w+=\S*", rest[i])):
            i += 2 if rest[i] in values else 1
        if first == "timeout" and i < len(rest):
            i += 1  # the duration
        return inner_argv(rest[i:])
    return [argv]


def is_queued(argv: list[str]) -> bool:
    """`heavy.py run|submit ...` as the segment's own argv (after an interpreter), never a word elsewhere."""
    at = 1 if os.path.basename(argv[0]).startswith("python") else 0
    return len(argv) > at + 1 and os.path.basename(argv[at]) == "heavy.py" and argv[at + 1] in ("run", "submit")


def is_self_queued(argv: list[str]) -> bool:
    """The kit's own close takes its slot itself: `verify_gate.py milestone|project`, bare, through an
    interpreter or by path. Wrapping it in `heavy.py run` would put the wait ahead of preflight."""
    at = 1 if os.path.basename(argv[0]).startswith("python") else 0
    return (
        len(argv) > at
        and os.path.splitext(os.path.basename(argv[at]))[0] == "verify_gate"
        and bool({"milestone", "project"} & set(words(argv[at + 1 :])))
    )


def unqueued_heavy(command: str, cfg: dict) -> bool:
    """A heavy command in the line that does not go through the queue. Reading and version-control tools
    are never heavy (a commit message may say "build")."""
    for segment in shell_segments(command):
        for argv in inner_argv(segment):
            if os.path.basename(argv[0]) in READ_ONLY or is_queued(argv) or is_self_queued(argv):
                continue
            if is_heavy(argv, cfg):
                return True
    return False


GIT_MUTATING = {
    "commit", "add", "merge", "checkout", "switch", "reset", "stash", "push", "rebase", "rm", "mv",
    "restore", "clean", "cherry-pick", "pull", "apply", "am", "revert",
}  # fmt: skip
FILE_WRITERS = {"tee", "cp", "mv", "rm", "mkdir", "rmdir", "touch", "truncate", "dd", "install", "ln", "chmod", "rsync", "patch"}
INSTALLS = {
    "npm": {"install", "i", "add", "ci", "remove", "uninstall", "update", "link"},
    "pnpm": {"install", "i", "add", "remove", "update", "link"},
    "yarn": {"install", "add", "remove", "upgrade", "link"},
    "bun": {"install", "i", "add", "remove", "update"},
    "pip": {"install", "uninstall"}, "pip3": {"install", "uninstall"},
    "uv": {"add", "sync", "remove", "lock"}, "poetry": {"install", "add", "remove", "update"},
    "bundle": {"install", "add", "update"}, "cargo": {"add", "install", "update"},
}  # fmt: skip
TEST_RUNNERS = {"pytest", "vitest", "jest", "rspec"}
REDIRECTS = {">", ">>", ">|", "&>", "&>>"}


def git_parts(args: list[str]) -> tuple[str, list[str], str]:
    """(subcommand, its arguments, the -C directory) of a git command line."""
    where, i = "", 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-C" and i + 1 < len(args):
            where = args[i + 1]
        i += 2 if args[i] in ("-C", "-c", "--git-dir", "--work-tree", "--namespace") else 1
    return (args[i], args[i + 1 :], where) if i < len(args) else ("", [], where)


def mutates(argv: list[str], cfg: dict) -> bool:
    """A command that changes files, history, installed packages or build output. Reading is never one."""
    while argv and ENV_ASSIGN.fullmatch(argv[0]):
        argv = argv[1:]
    if not argv:
        return False
    prog, rest = os.path.basename(argv[0]), argv[1:]
    if prog == "git":
        sub, args, _ = git_parts(rest)
        if sub == "worktree":
            return args[:1] in (["add"], ["remove"], ["move"], ["prune"])
        if sub == "branch":
            flags = {a for a in args if a.startswith("-")}
            return bool(flags & {"-D", "-d", "-m", "-M", "-c", "-C", "-f", "--delete", "--move", "--copy", "--force"}) or (
                bool(words(args)) and not flags & {"--list", "-l"}
            )
        return sub in GIT_MUTATING
    if prog == "sed":
        return any(a == "--in-place" or a.startswith("--in-place=") or re.fullmatch(r"-[a-zA-Z]*i\S*", a) for a in rest)
    if prog in FILE_WRITERS:
        return True
    w = words(rest)
    if w[:1] and w[0] in INSTALLS.get(prog, ()):
        return True
    if prog == "uv" and w[:2] == ["pip", "install"]:
        return True
    return prog in TEST_RUNNERS or (not is_queued(argv) and not is_self_queued(argv) and is_heavy(argv, cfg))


def redirect_target(argv: list[str]) -> str | None:
    """The file a `>` writes, or None (no redirect, /dev/null, or a descriptor copy such as 2>&1)."""
    for i, a in enumerate(argv[:-1]):
        if a in REDIRECTS and argv[i + 1] != "/dev/null" and not argv[i + 1].startswith("&"):
            return argv[i + 1]
    return None


def writes_in_main(command: str, payload_cwd: str, cfg: dict | None = None) -> bool:
    """A helper's command that changes the main working folder: file writes, redirects, mutating git,
    package installs, builds and tests that run there. Reading is fine. The shell starts in the main
    folder on every call, so a `cd` moves the check with it: only a command whose folder (after the
    `cd`, resolved) is the main folder counts. A destination the line computes (`$VAR`) is not followed."""
    cfg, cwd = cfg or {}, payload_cwd
    cache: dict[str, bool] = {}

    def in_main(path: str | None) -> bool:
        return bool(path) and cache.setdefault(path, in_main_folder(path))

    for seg in shell_segments(command):
        for argv in inner_argv(seg):
            prog = os.path.basename(argv[0])
            if prog in ("cd", "pushd"):
                target = argv[1] if len(argv) > 1 else "~"
                unknown = any(c in target for c in "$`") or target == "-"
                cwd = None if unknown or cwd is None else os.path.realpath(os.path.join(cwd, os.path.expanduser(target)))
                continue
            where = cwd
            if prog == "git":
                dash_c = git_parts(argv[1:])[2]
                where = os.path.realpath(os.path.join(cwd, os.path.expanduser(dash_c))) if dash_c and cwd else cwd
            if not in_main(where):
                continue
            if mutates(argv, cfg):
                return True
        # a redirect writes even from a read-only tool; its folder is the target's, not the line's
        for argv in inner_argv(seg):
            target = redirect_target(argv)
            if target and cwd:
                if in_main(os.path.dirname(os.path.realpath(os.path.join(cwd, os.path.expanduser(target))))):
                    return True
    return False


def in_main_folder(cwd: str) -> bool:
    gitdir = git_out("rev-parse", "--path-format=absolute", "--absolute-git-dir", cwd=cwd)
    common = git_out("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=cwd)
    return bool(gitdir) and gitdir == common


MAIN_REFUSED = (
    "heavy: {cwd} is the main working folder. A helper works in its own worktree: "
    "run `git worktree list`, `cd` into the one your prompt names and repeat the command."
)


def cmd_guard(args) -> int:
    """Without --hook: helper commands never run in the main working folder (exit 3). With --hook, a
    PreToolUse payload on stdin, for a subagent's call only (it carries `agent_id`; every field is read
    defensively, since the owner's own session may omit it, and anything unreadable is allowed): refuse
    with exit 2, the code Claude Code treats as a block, a heavy command that does not go through the
    queue, and any command that writes to the main working folder (see `writes_in_main`)."""
    if not args.hook:
        cwd = os.getcwd()
        if in_main_folder(cwd):
            print(MAIN_REFUSED.format(cwd=cwd), file=sys.stderr)
            return GUARD_REFUSED
        return 0
    try:
        payload = json.load(sys.stdin)
        agent = payload.get("agent_id")
        command = (payload.get("tool_input") or {}).get("command")
        cwd = payload.get("cwd")
    except (ValueError, AttributeError):
        return 0
    if not agent or not isinstance(command, str):
        return 0
    cfg = config()
    if unqueued_heavy(command, cfg):
        print(
            "heavy: a helper's heavy command goes through the queue, one at a time per machine. "
            f"Run it as `python3 scripts/heavy.py run -- {command.strip()}` (or `submit`, then `wait`).",
            file=sys.stderr,
        )
        return 2
    cwd = cwd if isinstance(cwd, str) and cwd else os.getcwd()
    if writes_in_main(command, cwd, cfg):
        print(MAIN_REFUSED.format(cwd=cwd), file=sys.stderr)
        return 2
    return 0


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
    sub.add_parser("prune")
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
    if args.verb == "prune":
        return cmd_prune()
    return cmd_guard(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
