"""Two database helpers: a fast local one for tests, a personal cloud one for working data.

    python3 scripts/db.py test prepare                 # one local Postgres container + a migrated template
    python3 scripts/db.py test create [NAME]           # a private copy in under a second; prints "NAME URL"
    python3 scripts/db.py test drop NAME
    python3 scripts/db.py test sweep                   # drop copies of dead jobs and old templates
    python3 scripts/db.py test run -- CMD...           # create, run CMD with DATABASE_URL set, drop
    python3 scripts/db.py dev ensure                   # proxy up, your own database created once, migrated
    add --print to any verb: show the commands, run nothing

Why tests stay local: the database was never the slow part (builds, browsers and memory were); screen
checks reset their data before every screen and every query would pay a network round trip; tests drop
and recreate databases, which does not belong next to shared data; a local Postgres starts in seconds.

`sdlc.json` `db.test`: image, container, port, template (database name prefix; the template is `<template>_<migrations hash>`), migrate (a command that reads
DATABASE_URL), migrations (globs; a change rebuilds the template, so a stale template never serves
wrong tests). The container listens on 127.0.0.1 with trust auth: a throwaway with no password.

`sdlc.json` `db.dev`, every value a command or pattern for your own provider, nothing vendor-specific:
identity (prints who you are), name (default `dev_{identity}`), proxyCheck (exit 0 when the auth proxy
accepts connections), proxy (starts it), exists (exit 0 when `{db}` exists), create, migrate (reads
DATABASE_URL), url (a connection string with no password: the proxy and your own identity
authenticate). Env SDLC_DB_IDENTITY replaces the identity command. Nothing here prints a credential.

Written by `sdlc-run adopt` from the kit; edit the kit, not this copy. stdlib only.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import glob
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

NAME = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
EXIT_CONFIG = 2


class ConfigError(Exception):
    pass


def section(kind: str, required: tuple[str, ...]) -> dict:
    try:
        cfg = json.loads(Path("sdlc.json").read_text(encoding="utf-8")).get("db", {}).get(kind)
    except (OSError, ValueError, AttributeError):
        cfg = None
    if not isinstance(cfg, dict):
        raise ConfigError(f"sdlc.json db.{kind} is missing; see `python3 scripts/db.py --help`")
    for key in required:
        if not cfg.get(key):
            raise ConfigError(f"sdlc.json db.{kind}.{key} is missing")
    return cfg


def valid(name: str, what: str = "database name") -> str:
    if not NAME.match(name):
        raise ConfigError(f"{what} {name!r} must be lowercase letters, digits and _")
    return name


class Runner:
    """Runs argv lists, or only prints them (--print). `check` reports an exit status."""

    def __init__(self, dry: bool) -> None:
        self.dry = dry

    def show(self, argv: list[str], env: dict | None = None) -> str:
        pre = " ".join(f"{k}={shlex.quote(v)}" for k, v in (env or {}).items())
        return (pre + " " if pre else "") + " ".join(shlex.quote(a) for a in argv)

    def run(
        self, argv: list[str], env: dict | None = None, check: bool = True
    ) -> subprocess.CompletedProcess:
        if self.dry:
            print(self.show(argv, env))
            return subprocess.CompletedProcess(argv, 0, "", "")
        full = dict(os.environ, **(env or {}))
        res = subprocess.run(argv, env=full, capture_output=True, text=True)
        if check and res.returncode:
            sys.stderr.write(res.stderr or res.stdout)
            raise SystemExit(res.returncode)
        return res

    def stream(self, argv: list[str], env: dict | None = None, cwd: str | None = None) -> int:
        """Run with the caller's stdout and stderr, so output shows as it happens."""
        if self.dry:
            print(self.show(argv, env))
            return 0
        try:
            return subprocess.run(argv, env=dict(os.environ, **(env or {})), cwd=cwd).returncode
        except OSError as e:
            print(f"db: cannot run {argv[0]}: {e}", file=sys.stderr)
            return 127

    def probe(self, argv: list[str]) -> bool:
        """Exit 0 of a read-only question. A dry run prints it and answers no."""
        if self.dry:
            print(self.show(argv))
            return False
        return subprocess.run(argv, capture_output=True).returncode == 0


# --- test-db ----------------------------------------------------------------------------------

JOB = re.compile(r"^sdlc_job_(\d+)_(?:(\d{10})_)?\d+$")  # sdlc_job_<pid>_<epoch seconds>_<n>
JOB_GRACE = 3600  # a standalone `test create` exits at once; its copy outlives its pid by design
TEMPLATE_TTL = 7 * 86400


def state_dir() -> Path:
    base = os.environ.get("SDLC_DB_DIR")
    if not base:
        state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local/state")
        base = str(Path(state) / "sdlc/db")
    return Path(base)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class TestDb:
    __test__ = False  # not a pytest class

    def __init__(self, cfg: dict, runner: Runner) -> None:
        self.c, self.r = cfg, runner
        self.container = cfg["container"]
        self.port = int(cfg["port"])
        self.template = valid(cfg["template"])  # the prefix; the template itself is <prefix>_<hash>
        self.user = cfg.get("user", "postgres")
        # docker or podman: db.test.engine, then SDLC_DB_ENGINE, then whichever is installed
        self.cli = cfg.get("engine") or os.environ.get("SDLC_DB_ENGINE") or (
            "podman" if shutil.which("podman") and not shutil.which("docker") else "docker"
        )
        self.key = re.sub(r"[^A-Za-z0-9_.-]", "_", self.container)

    @property
    def tmpl(self) -> str:
        return valid(f"{self.template}_{self.migrations_hash()}")

    def url(self, name: str) -> str:
        return f"postgresql://{self.user}@127.0.0.1:{self.port}/{name}"

    def psql(self, sql: str, db: str = "postgres") -> subprocess.CompletedProcess:
        return self.r.run(
            [self.cli, "exec", self.container, "psql", "-U", self.user, "-d", db,
             "-v", "ON_ERROR_STOP=1", "-tAc", sql]
        )  # fmt: skip

    def migrations_hash(self) -> str:
        h = hashlib.sha256()
        for pattern in self.c.get("migrations", []):
            for f in sorted(p for p in glob.glob(pattern, recursive=True) if os.path.isfile(p)):
                h.update(f.encode())
                h.update(Path(f).read_bytes())
        return h.hexdigest()[:16]

    @contextlib.contextmanager
    def locked(self):
        """One writer per container on this machine: starting it and building a template."""
        if self.r.dry:
            yield
            return
        d = state_dir()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"{self.key}.lock", "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def used(self, update: dict | None = None) -> dict:
        """Last use per template, kept beside the lock; call with the lock held."""
        f = state_dir() / f"{self.key}.json"
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if update is not None and not self.r.dry:
            f.write_text(json.dumps(update), encoding="utf-8")
        return data

    def ready(self) -> bool:
        return self.r.probe([self.cli, "exec", self.container, "pg_isready", "-U", self.user])

    def wait_ready(self, tries: int) -> bool:
        for _ in range(tries):
            if self.ready():
                return True
            if self.r.dry:
                break
            time.sleep(0.5)
        return False

    def start_container(self) -> None:
        if self.wait_ready(3):  # one failed probe never condemns a container
            return
        state = self.r.run(
            [self.cli, "inspect", "-f", "{{.State.Running}}", self.container], check=False
        )
        exists, running = state.returncode == 0, state.stdout.strip() == "true"
        if exists and running:  # up but still starting, or busy: wait, never remove
            if self.wait_ready(60) or self.r.dry:
                return
            raise ConfigError(
                f"container {self.container} is running but not ready; "
                f"run `docker logs {self.container}`"
            )
        if exists:
            self.r.run([self.cli, "rm", "-f", self.container], check=False)
        self.r.run(
            [self.cli, "run", "-d", "--name", self.container,
             "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "-p", f"127.0.0.1:{self.port}:5432",
             self.c.get("image", "postgres:17")]
        )  # fmt: skip
        if not self.wait_ready(60) and not self.r.dry:
            raise ConfigError(
                f"container {self.container} never became ready; run `docker logs {self.container}`"
            )

    def disconnect(self, db: str) -> None:
        self.psql(
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{db}' AND pid <> pg_backend_pid()"
        )

    def _prepare(self) -> str:
        """Start the container and publish this migration set's template once. Lock held."""
        self.start_container()
        tmpl = self.tmpl
        want = f"migrations:{self.migrations_hash()}"
        have = (
            ""
            if self.r.dry
            else self.psql(
                f"SELECT shobj_description(oid, 'pg_database') FROM pg_database "
                f"WHERE datname = '{tmpl}'"
            ).stdout.strip()
        )
        # absent, or an unstamped leftover of a crashed build: only ever our own name
        if have != want:
            self.disconnect(tmpl)
            self.psql(f"DROP DATABASE IF EXISTS {tmpl}")
            self.psql(f"CREATE DATABASE {tmpl}")
            if self.c.get("migrate"):
                self.r.run(shlex.split(self.c["migrate"]), env={"DATABASE_URL": self.url(tmpl)})
            self.disconnect(tmpl)  # CREATE ... TEMPLATE fails while anything is connected
            self.psql(f"COMMENT ON DATABASE {tmpl} IS '{want}'")  # the stamp publishes it
        self.used({**self.used(), tmpl: time.time()})
        self._sweep()
        return tmpl

    def prepare(self) -> None:
        with self.locked():
            self._prepare()

    def create(self, name: str | None = None) -> str:
        name = valid(name or f"sdlc_job_{os.getpid()}_{int(time.time())}_{time.time_ns() % 10**6}")
        with self.locked():
            tmpl = self._prepare()
            self.disconnect(tmpl)
            self.psql(f"CREATE DATABASE {name} TEMPLATE {tmpl}")
        return name

    def drop(self, name: str) -> None:
        self.disconnect(valid(name))
        self.psql(f"DROP DATABASE IF EXISTS {name}")

    def _sweep(self) -> list[str]:
        """Drop copies whose process is gone and templates of old migration sets. Lock held."""
        now, keep, used, gone = time.time(), self.tmpl, self.used(), []
        old = re.compile(rf"^{re.escape(self.template)}(_[0-9a-f]{{16}})?$")
        for n in self.psql("SELECT datname FROM pg_database").stdout.split():
            if m := JOB.match(n):
                if not alive(int(m[1])) and now - int(m[2] or 0) > JOB_GRACE:
                    self.drop(n)
                    gone.append(n)
            elif n != keep and old.match(n):
                if now - used.setdefault(n, now) > TEMPLATE_TTL:
                    self.drop(n)
                    used.pop(n)
                    gone.append(n)
        self.used(used)
        return gone

    def sweep(self) -> list[str]:
        with self.locked():
            return self._sweep() if self.ready() else []


def cmd_test(args, runner: Runner) -> int:
    db = TestDb(section("test", ("container", "port", "template")), runner)
    if args.verb == "prepare":
        db.prepare()
    elif args.verb == "sweep":
        for n in db.sweep():
            print(f"dropped {n}")
    elif args.verb == "create":
        name = db.create(args.name)
        print(f"{name} {db.url(name)}")
    elif args.verb == "drop":
        db.drop(args.name)
    else:  # run: one job, one copy
        if not args.cmd:
            raise ConfigError("test run needs a command after `--`")
        name = db.create()
        try:
            return runner.stream(args.cmd, env={"DATABASE_URL": db.url(name)}, cwd=args.cwd)
        finally:
            db.drop(name)
    return 0


# --- dev-db -----------------------------------------------------------------------------------


def cmd_dev(args, runner: Runner) -> int:
    cfg = section("dev", ("identity", "proxyCheck", "proxy", "exists", "create", "migrate", "url"))
    who = os.environ.get("SDLC_DB_IDENTITY")
    if who is None:
        argv = shlex.split(cfg["identity"])
        who = (
            (runner.run(argv).stdout.strip() or "dev")
            if not runner.dry
            else (print(runner.show(argv)) or "dev")
        )
    identity = valid(re.sub(r"[^a-z0-9]+", "_", who.lower()).strip("_"), "identity")
    db = valid(cfg.get("name", "dev_{identity}").format(identity=identity))
    fill = lambda t: shlex.split(t.format(identity=identity, db=db))  # noqa: E731

    if not runner.probe(fill(cfg["proxyCheck"])):
        if runner.dry:
            print(runner.show(fill(cfg["proxy"])))
        else:
            subprocess.Popen(
                fill(cfg["proxy"]), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True,
            )  # fmt: skip
            for _ in range(60):
                if runner.probe(fill(cfg["proxyCheck"])):
                    break
                time.sleep(0.5)
            else:
                raise ConfigError(
                    "the auth proxy did not come up; run db.dev.proxy by hand to see why"
                )
    if not runner.probe(fill(cfg["exists"])):
        runner.run(fill(cfg["create"]))
    runner.run(
        fill(cfg["migrate"]), env={"DATABASE_URL": cfg["url"].format(identity=identity, db=db)}
    )
    print(f"dev-db: {db} ready")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    cmd: list[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, cmd = argv[:i], argv[i + 1 :]
    ap = argparse.ArgumentParser(prog="db.py")
    top = ap.add_subparsers(dest="kind", required=True)
    t = top.add_parser("test")
    t.add_argument("verb", choices=["prepare", "create", "drop", "run", "sweep"])
    t.add_argument("name", nargs="?")
    d = top.add_parser("dev")
    d.add_argument("verb", choices=["ensure"])
    for p in (t, d):
        p.add_argument("--print", action="store_true", dest="dry")
    args = ap.parse_args(argv)
    args.cmd, args.cwd = cmd, os.getcwd()
    top_level = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    ).stdout.strip()
    if top_level:  # sdlc.json and the migration globs are relative to the repo root
        os.chdir(top_level)
    if args.kind == "test" and args.verb == "drop" and not args.name:
        ap.error("drop needs a database name")
    runner = Runner(args.dry)
    try:
        return cmd_test(args, runner) if args.kind == "test" else cmd_dev(args, runner)
    except ConfigError as e:
        print(f"db: {e}", file=sys.stderr)
        return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
