"""Usage: pytest scripts/test_db.py

db.py builds its docker, psql and cloud commands from sdlc.json. Everything here checks the commands
it would run (`--print` runs nothing); the one live test needs Docker and skips without it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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
    assert any("CREATE DATABASE sdlc_tmpl" in x for x in lines)
    migrate = next(x for x in lines if "pnpm db:migrate" in x)
    assert "DATABASE_URL=postgresql://postgres@127.0.0.1:55432/sdlc_tmpl" in migrate
    assert any("COMMENT ON DATABASE sdlc_tmpl IS" in x and "migrations:" in x for x in lines)


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
    assert sql and "CREATE DATABASE sdlc_job_" in sql[0]
    assert one != two, "two jobs never share a database name"
    assert "pg_terminate_backend" in one, "the template must have no connection when copied"


def test_test_run_creates_runs_and_drops_with_the_url_in_the_env(tmp_path: Path) -> None:
    out = _db(_repo(tmp_path, {"test": TEST}), "test", "run", "--print", "--", "pytest", "-q")
    assert out.returncode == 0, out.stderr
    lines = out.stdout.splitlines()
    job = next(x for x in lines if "pytest -q" in x)
    assert "DATABASE_URL=postgresql://postgres@127.0.0.1:55432/sdlc_job_" in job
    assert "DROP DATABASE IF EXISTS sdlc_job_" in lines[-1], "the copy goes away afterwards"


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


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is not installed")
def test_live_template_copy_is_fast(tmp_path: Path) -> None:
    ok = subprocess.run(["docker", "info"], capture_output=True).returncode == 0
    if not ok:
        pytest.skip("Docker is not running")
    cfg = dict(TEST, container=f"sdlc-test-pg-{os.getpid()}", port=55000 + os.getpid() % 900)
    cfg["migrate"] = "true"
    repo = _repo(tmp_path, {"test": cfg})
    try:
        assert _db(repo, "test", "prepare").returncode == 0
        import time

        start = time.time()
        made = _db(repo, "test", "create")
        assert made.returncode == 0, made.stderr
        assert time.time() - start < 2
        assert _db(repo, "test", "drop", made.stdout.split()[0]).returncode == 0
    finally:
        subprocess.run(["docker", "rm", "-f", cfg["container"]], capture_output=True)
