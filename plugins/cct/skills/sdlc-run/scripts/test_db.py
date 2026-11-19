"""Usage: pytest scripts/test_db.py

db.py builds its docker, psql and cloud commands from sdlc.json. Everything here checks the commands
it would run (`--print` runs nothing); the one live test needs Docker and skips without it.
"""

from __future__ import annotations

import importlib.util
import json
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

DB = Path(__file__).resolve().parents[1] / "templates/scripts/db.py"
TEST = {
    "image": "postgres:17", "container": "sdlc-test-pg", "port": 55432, "template": "sdlc_tmpl",
    "migrate": "pnpm db:migrate", "migrations": ["db/migrations/*.sql"],
}  # fmt: skip
DEV = {
    "identity": "tool whoami", "name": "dev_{identity}", "proxyCheck": "tool proxy-up",
    "proxy": "tool proxy start --port 5433", "exists": "tool db has {db}",
    "create": "tool db create {db}", "migrate": "pnpm db:migrate",
    "url": "postgresql://{identity}@127.0.0.1:5433/{db}",
}  # fmt: skip


def _repo(tmp_path: Path, db: dict) -> Path:
    repo = tmp_path / "repo"
    (repo / "db/migrations").mkdir(parents=True)
    (repo / "db/migrations/001.sql").write_text("create table a (id int);")
    (repo / "sdlc.json").write_text(json.dumps({"db": db}))
    return repo


def _db(repo: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    e = {k: v for k, v in os.environ.items() if not k.startswith("SDLC_")}
    e["SDLC_DB_ENGINE"] = "docker"  # the printed commands are checked as docker commands
    e.update(env or {})
    return subprocess.run(
        [sys.executable, str(DB), *args], capture_output=True, text=True, cwd=repo, env=e
    )


def test_test_prepare_builds_the_container_template_and_migration_commands(tmp_path: Path) -> None:
    out = _db(_repo(tmp_path, {"test": TEST}), "test", "prepare", "--print")
    assert out.returncode == 0, out.stderr
    lines = out.stdout.splitlines()
    run = next(x for x in lines if x.startswith("docker run"))
    assert "--name sdlc-test-pg" in run and "127.0.0.1:55432:5432" in run and "postgres:17" in run
    assert "POSTGRES_HOST_AUTH_METHOD=trust" in run, "local throwaway: no password to leak"
    assert any("pg_isready" in x for x in lines)
    assert any("CREATE DATABASE sdlc_tmpl_" in x for x in lines)
    migrate = next(x for x in lines if "pnpm db:migrate" in x)
    assert "DATABASE_URL=postgresql://postgres@127.0.0.1:55432/sdlc_tmpl_" in migrate
    assert any("COMMENT ON DATABASE sdlc_tmpl_" in x and "migrations:" in x for x in lines)


def test_a_changed_migration_changes_the_template_hash(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"test": TEST})

    def comment() -> str:
        out = _db(repo, "test", "prepare", "--print").stdout
        return next(x for x in out.splitlines() if "COMMENT ON" in x)

    before = comment()
    assert comment() == before
    (repo / "db/migrations/002.sql").write_text("create table b (id int);")
    assert comment() != before


def test_each_job_gets_a_unique_copy_made_from_the_template(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"test": TEST})
    one = _db(repo, "test", "create", "--print").stdout
    two = _db(repo, "test", "create", "--print").stdout
    sql = [x for x in one.splitlines() if "TEMPLATE sdlc_tmpl" in x]
    assert sql and "CREATE DATABASE sdlc_job_" in sql[0], "no owner: a name nothing sweeps on its own"
    assert one != two, "two jobs never share a database name"
    owned = _db(repo, "test", "create", "--owner-pid", "4242", "--print").stdout
    assert "CREATE DATABASE sdlc_own_4242_" in owned, "the owner's pid is in the name"
    assert "pg_terminate_backend" in one, "the template must have no connection when copied"


def test_test_run_creates_runs_and_drops_with_the_url_in_the_env(tmp_path: Path) -> None:
    out = _db(_repo(tmp_path, {"test": TEST}), "test", "run", "--print", "--", "pytest", "-q")
    assert out.returncode == 0, out.stderr
    lines = out.stdout.splitlines()
    job = next(x for x in lines if "pytest -q" in x)
    assert "DATABASE_URL=postgresql://postgres@127.0.0.1:55432/sdlc_own_" in job
    assert "DROP DATABASE IF EXISTS sdlc_own_" in lines[-1], "the copy goes away afterwards"


def test_names_are_validated_before_they_reach_sql(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"test": TEST})
    res = _db(repo, "test", "drop", "x; DROP DATABASE postgres", "--print")
    assert res.returncode == 2 and "database name" in res.stderr
    bad = dict(TEST, template="a b")
    res = _db(_repo(tmp_path / "b", {"test": bad}), "test", "prepare", "--print")
    assert res.returncode == 2


def test_missing_config_names_the_key(tmp_path: Path) -> None:
    res = _db(_repo(tmp_path, {}), "test", "prepare", "--print")
    assert res.returncode == 2 and "sdlc.json db.test" in res.stderr


def test_dev_ensure_builds_proxy_create_and_migrate_with_the_developers_identity(
    tmp_path: Path,
) -> None:
    out = _db(
        _repo(tmp_path, {"dev": DEV}),
        "dev",
        "ensure",
        "--print",
        env={"SDLC_DB_IDENTITY": "Ann.Lee"},
    )
    assert out.returncode == 0, out.stderr
    lines = out.stdout.splitlines()
    assert "tool proxy start --port 5433" in lines, "starts the proxy when it is not up"
    assert "tool db has dev_ann_lee" in lines and "tool db create dev_ann_lee" in lines
    migrate = next(x for x in lines if "pnpm db:migrate" in x)
    assert "DATABASE_URL=postgresql://ann_lee@127.0.0.1:5433/dev_ann_lee" in migrate
    assert "password" not in out.stdout.lower() and "token" not in out.stdout.lower()


def test_dev_config_gaps_are_named(tmp_path: Path) -> None:
    gap = {k: v for k, v in DEV.items() if k != "create"}
    res = _db(_repo(tmp_path, {"dev": gap}), "dev", "ensure", "--print")
    assert res.returncode == 2 and "db.dev.create" in res.stderr


os.environ["SDLC_DB_ENGINE"] = "docker"  # the fakes below speak docker; engine choice is tested on its own


def _cli(monkeypatch, cfg: dict, env: str | None, have: set[str]) -> str:
    monkeypatch.delenv("SDLC_DB_ENGINE", raising=False)
    if env:
        monkeypatch.setenv("SDLC_DB_ENGINE", env)
    monkeypatch.setattr(mod.shutil, "which", lambda n: f"/bin/{n}" if n in have else None)
    return mod.TestDb({"container": "c", "port": 1, "template": "t", **cfg}, mod.Runner(True)).cli


def test_podman_when_docker_is_missing(monkeypatch) -> None:
    assert _cli(monkeypatch, {}, None, {"podman"}) == "podman"


def test_docker_wins_when_both_exist(monkeypatch) -> None:
    assert _cli(monkeypatch, {}, None, {"docker", "podman"}) == "docker"


def test_config_and_env_override(monkeypatch) -> None:
    assert _cli(monkeypatch, {"engine": "podman"}, None, {"docker"}) == "podman"
    assert _cli(monkeypatch, {}, "podman", {"docker"}) == "podman"


# --- the fake docker: a dict of databases, no Docker needed ---------------------------------------

_spec = importlib.util.spec_from_file_location("sdlc_db", DB)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


class Fake:
    """Stands in for Runner: answers docker and psql from a dict; state may live in a file."""

    dry = False

    def __init__(self, container: str = "absent", dbs: dict | None = None, path: Path | None = None,
                 not_ready: int = 0, delay: float = 0.0, image: str = "postgres:17",
                 hostport: int = 55432, start_fails: bool = False) -> None:  # fmt: skip
        self.path, self.delay, self.not_ready = path, delay, not_ready
        self.image, self.hostport, self.start_fails = image, hostport, start_fails
        self.st = {"container": container, "dbs": dict(dbs or {}), "log": []}
        if path and not path.exists():
            self.save()

    def load(self) -> None:
        if self.path:
            self.st = json.loads(self.path.read_text())

    def save(self) -> None:
        if self.path:
            self.path.write_text(json.dumps(self.st))

    def log(self, *event: str) -> None:
        self.st["log"].append(" ".join(event))

    def events(self, prefix: str) -> list[str]:
        self.load()
        return [e for e in self.st["log"] if e.startswith(prefix)]

    def probe(self, argv: list[str]) -> bool:
        self.load()
        if self.not_ready > 0:
            self.not_ready -= 1
            return False
        return self.st["container"] == "running"


    def run(self, argv, env=None, check=True):
        self.load()
        out = ""
        rc = 0
        if argv[:2] == ["docker", "inspect"]:
            ports = '{"5432/tcp":[{"HostIp":"127.0.0.1","HostPort":"' + str(self.hostport) + '"}]}'
            rc, out = (
                (1, "")
                if self.st["container"] == "absent"
                else (0, f"{'true' if self.st['container'] == 'running' else 'false'}|{self.image}|{ports}")
            )
        elif argv[:2] == ["docker", "start"]:
            if self.start_fails:
                return subprocess.CompletedProcess(argv, 1, "", "boom")
            self.st["container"] = "running"
            self.log("start")
        elif argv[:3] == ["docker", "rm", "-f"]:
            self.st["container"] = "absent"
            self.st["dbs"] = {}
            self.log("rm")
        elif argv[:2] == ["docker", "run"]:
            time.sleep(self.delay)
            self.st["container"] = "running"
            self.log("run")
        elif argv[:2] == ["docker", "exec"]:
            out = self.sql(argv[-1])
        else:
            time.sleep(self.delay)
            self.log("migrate", (env or {}).get("DATABASE_URL", ""))
        self.save()
        return subprocess.CompletedProcess(argv, rc, out, "")

    def stream(self, argv, env=None, cwd=None):
        self.log("stream", " ".join(argv))
        return 7

    def sql(self, q: str) -> str:
        dbs = self.st["dbs"]
        if "shobj_description" in q:
            return dbs.get(re.search(r"datname = '(\w+)'", q).group(1)) or ""
        if q == "SELECT datname FROM pg_database":
            return "\n".join(["postgres", *dbs])
        if m := re.match(r"CREATE DATABASE (\w+)(?: TEMPLATE (\w+))?$", q):
            if m[2]:
                assert dbs.get(m[2]), f"clone from unpublished template {m[2]}"
                self.log("clone", m[1], m[2])
            dbs[m[1]] = ""
        elif m := re.match(r"DROP DATABASE IF EXISTS (\w+)$", q):
            dbs.pop(m[1], None)
            self.log("drop", m[1])
        elif m := re.match(r"COMMENT ON DATABASE (\w+) IS '(.*)'$", q):
            dbs[m[1]] = m[2]
        return ""


def _tdb(tmp_path: Path, fake: Fake, files: dict[str, str] | None = None, monkeypatch=None):
    repo = tmp_path / f"r{len(list(tmp_path.glob('r*')))}"
    (repo / "db/migrations").mkdir(parents=True)
    for name, body in (files or {"001.sql": "create table a (id int);"}).items():
        (repo / "db/migrations" / name).write_text(body)
    monkeypatch.chdir(repo)
    return mod.TestDb(dict(TEST), fake)


@pytest.fixture(autouse=False)
def state(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("SDLC_DB_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)
    return tmp_path / "state"


def test_two_migration_sets_get_two_templates_and_never_drop_each_other(
    tmp_path: Path, state: Path, monkeypatch
) -> None:
    fake = Fake()
    a = _tdb(tmp_path, fake, {"001.sql": "a"}, monkeypatch)
    ta = a.tmpl
    a.prepare()
    b = _tdb(tmp_path, fake, {"001.sql": "b"}, monkeypatch)
    tb = b.tmpl
    b.prepare()
    assert ta != tb and ta.startswith("sdlc_tmpl_") and tb.startswith("sdlc_tmpl_")
    assert fake.st["dbs"][ta].startswith("migrations:") and fake.st["dbs"][tb]
    assert [e for e in fake.events("drop") if e.split()[1] in (ta, tb)] == [
        f"drop {ta}",
        f"drop {tb}",
    ], "only the IF EXISTS guard on its own fresh name, never the other set's template"
    a_again = _tdb(tmp_path, fake, {"001.sql": "a"}, monkeypatch)
    a_again.prepare()
    assert len(fake.events("migrate")) == 2, "a published template is never rebuilt"
    a_again.create("job_a")
    assert fake.events("clone") == [f"clone job_a {ta}"]


def test_concurrent_prepare_starts_the_container_and_builds_once(
    tmp_path: Path, state: Path, monkeypatch
) -> None:
    fake = Fake(path=tmp_path / "fake.json", delay=0.3)
    _tdb(tmp_path, fake, monkeypatch=monkeypatch)  # repo + chdir; processes inherit the cwd

    def worker() -> None:
        cfg = dict(TEST)
        mod.TestDb(cfg, Fake(path=tmp_path / "fake.json", delay=0.3)).prepare()

    ctx = multiprocessing.get_context("fork")
    procs = [ctx.Process(target=worker) for _ in range(2)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(30)
        assert p.exitcode == 0
    assert len(fake.events("run")) == 1, "the second process waited for the first"
    assert len(fake.events("migrate")) == 1, "and found the template already published"


def test_one_failed_probe_never_removes_a_running_container(
    tmp_path: Path, state: Path, monkeypatch
) -> None:
    fake = Fake(container="running", not_ready=2)
    _tdb(tmp_path, fake, monkeypatch=monkeypatch).start_container()
    assert fake.events("rm") == [] and fake.events("run") == []
    busy = Fake(container="running", not_ready=40)  # running but slow to answer: wait, still no rm
    _tdb(tmp_path, busy, monkeypatch=monkeypatch).start_container()
    assert busy.events("rm") == [] and busy.events("run") == []
    stuck = Fake(container="running", not_ready=10**6)
    with pytest.raises(mod.ConfigError, match="running but not ready"):
        _tdb(tmp_path, stuck, monkeypatch=monkeypatch).start_container()
    assert stuck.events("rm") == []


def test_a_stopped_container_is_started_never_removed_and_an_absent_one_run(
    tmp_path: Path, state: Path, monkeypatch
) -> None:
    stopped = Fake(container="stopped")
    _tdb(tmp_path, stopped, monkeypatch=monkeypatch).start_container()
    assert stopped.events("rm") == [] and stopped.events("run") == []
    assert stopped.events("start") == ["start"]
    absent = Fake()
    _tdb(tmp_path, absent, monkeypatch=monkeypatch).start_container()
    assert absent.events("rm") == [] and absent.events("run") == ["run"]


@pytest.mark.parametrize(
    "fake, why",
    [
        (Fake(container="stopped", image="redis:7"), "belongs to something else"),
        (Fake(container="stopped", hostport=1234), "belongs to something else"),
        (Fake(container="stopped", start_fails=True), "start` failed"),
    ],
)
def test_a_stopped_container_that_differs_or_will_not_start_is_a_named_conflict(
    tmp_path: Path, state: Path, monkeypatch, fake: Fake, why: str
) -> None:
    with pytest.raises(mod.ConfigError, match=why) as e:
        _tdb(tmp_path, fake, monkeypatch=monkeypatch).start_container()
    assert "sdlc-test-pg" in str(e.value), "the message names the container"
    assert fake.events("rm") == [] and fake.events("run") == [], "never replaced"


def test_sweep_drops_dead_owners_copies_and_old_templates_only(
    tmp_path: Path, state: Path, monkeypatch
) -> None:
    now = int(time.time())
    dead_pid = subprocess.run([sys.executable, "-c", "import os;print(os.getpid())"],
                              capture_output=True, text=True).stdout.strip()  # fmt: skip
    old = now - 7200
    fake = Fake(container="running", dbs={
        f"sdlc_own_{dead_pid}_{old}_1": "",            # owner dead, past the grace: dropped
        f"sdlc_own_{dead_pid}_{now}_2": "",            # owner dead but copy just made: kept
        f"sdlc_own_{os.getpid()}_{old}_3": "",         # owner alive: kept
        "sdlc_job_999999_1": "",                        # 3.21 name, no owner marker: kept
        f"sdlc_job_{dead_pid}_{old}_4": "",            # 3.21 name with a dead pid in it: kept
        "sdlc_tmpl_0123456789abcdef": "migrations:x",  # other hash, never seen: starts its clock
        "sdlc_tmpl_fedcba9876543210": "migrations:y",  # other hash, used 8 days ago: dropped
        "customers": "",                                # not ours: never touched
    })  # fmt: skip
    db = _tdb(tmp_path, fake, monkeypatch=monkeypatch)
    state.mkdir(parents=True)
    (state / "sdlc-test-pg.json").write_text(
        json.dumps({"sdlc_tmpl_fedcba9876543210": time.time() - 8 * 86400})
    )
    gone = db.sweep()
    assert sorted(gone) == sorted([f"sdlc_own_{dead_pid}_{old}_1", "sdlc_tmpl_fedcba9876543210"])
    kept = set(fake.st["dbs"])
    assert {"customers", "sdlc_tmpl_0123456789abcdef", f"sdlc_own_{os.getpid()}_{old}_3",
            f"sdlc_own_{dead_pid}_{now}_2", "sdlc_job_999999_1", f"sdlc_job_{dead_pid}_{old}_4"} <= kept  # fmt: skip
    assert fake.events("run") == [], "sweep never starts a container"
    assert sorted(db.sweep(all_unowned=True)) == sorted(["sdlc_job_999999_1", f"sdlc_job_{dead_pid}_{old}_4"])


def test_a_long_template_prefix_gets_a_bounded_name_that_keeps_prefixes_apart(
    tmp_path: Path, state: Path, monkeypatch
) -> None:
    fits = _tdb(tmp_path, Fake(), monkeypatch=monkeypatch)
    assert fits.tmpl.startswith("sdlc_tmpl_") and len(fits.tmpl) <= 63
    a, b = "a" * 47, "a" * 46 + "b"  # 47 + _ + 16 hash = 64: too long as it was
    names = []
    for prefix in (a, b):
        d = _tdb(tmp_path, Fake(), monkeypatch=monkeypatch)
        d.template = prefix
        names.append(d.tmpl)
    assert all(len(n) <= 63 and mod.NAME.match(n) for n in names) and names[0] != names[1]


def test_prepare_sweeps_and_remembers_the_templates_last_use(
    tmp_path: Path, state: Path, monkeypatch
) -> None:
    old = int(time.time()) - 7200
    fake = Fake(container="running", dbs={f"sdlc_own_999999_{old}_1": "", "sdlc_job_999999_1": ""})
    db = _tdb(tmp_path, fake, monkeypatch=monkeypatch)
    db.prepare()
    assert f"sdlc_own_999999_{old}_1" not in fake.st["dbs"]
    assert "sdlc_job_999999_1" in fake.st["dbs"], "a copy with no owner is never swept by prepare"
    used = json.loads((state / "sdlc-test-pg.json").read_text())
    assert db.tmpl in used and time.time() - used[db.tmpl] < 60


def test_test_run_streams_and_keeps_the_exit_code(tmp_path: Path, state: Path, monkeypatch) -> None:
    fake = Fake(container="running")
    _tdb(tmp_path, fake, monkeypatch=monkeypatch)
    args = type("A", (), {"verb": "run", "cmd": ["pytest"], "name": None, "cwd": "/x"})
    monkeypatch.setattr(mod, "section", lambda *a: dict(TEST))
    assert mod.cmd_test(args, fake) == 7
    assert fake.events("stream") == ["stream pytest"]
    assert fake.events("drop")[-1].startswith(f"drop sdlc_own_{os.getpid()}_"), "owned by the run itself, dropped after"


def test_runner_stream_inherits_output_and_returns_the_status(capfd) -> None:
    rc = mod.Runner(False).stream(["sh", "-c", "echo out; echo err >&2; exit 3"])
    seen = capfd.readouterr()
    assert rc == 3 and seen.out == "out\n" and seen.err == "err\n"


def test_sdlc_json_is_read_from_the_repo_root_not_the_cwd(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"test": TEST})
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    sub = repo / "db"
    out = _db(sub, "test", "prepare", "--print")
    assert out.returncode == 0, out.stderr
    assert "CREATE DATABASE sdlc_tmpl_" in out.stdout


_ENGINE = shutil.which("docker") and "docker" or shutil.which("podman") and "podman"


@pytest.mark.skipif(
    not _ENGINE or os.environ.get("SDLC_DB_LIVE") != "1",
    reason="live database test: set SDLC_DB_LIVE=1 with Docker or Podman running",
)
def test_live_template_copy_is_fast(tmp_path: Path) -> None:
    if subprocess.run([_ENGINE, "info"], capture_output=True).returncode != 0:
        pytest.skip(f"{_ENGINE} is not running")
    cfg = dict(TEST, container=f"sdlc-test-pg-{os.getpid()}", port=55000 + os.getpid() % 900)
    cfg["migrate"], cfg["engine"] = "true", _ENGINE
    repo = _repo(tmp_path, {"test": cfg})
    try:
        assert _db(repo, "test", "prepare").returncode == 0
        start = time.time()
        made = _db(repo, "test", "create")
        assert made.returncode == 0, made.stderr
        assert time.time() - start < 2, f"a copy took {time.time() - start:.2f}s"
        assert _db(repo, "test", "drop", made.stdout.split()[0]).returncode == 0
    finally:
        subprocess.run([_ENGINE, "rm", "-f", cfg["container"]], capture_output=True)
