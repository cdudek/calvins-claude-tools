"""Usage: pytest scripts/test_preflight.py

preflight.py checks tools, auth, Docker and two config conflicts once, and prints one fix line per
failure. Each case runs it in a scratch repo with a PATH that holds only the fakes it needs.
"""

from __future__ import annotations

import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path

PRE = Path(__file__).resolve().parents[1] / "templates/scripts/preflight.py"


def _run(tmp: Path, cfg: dict, *, fakes: dict[str, int] | None = None):
    repo = tmp / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    # the machine's free disk is not under test, except in the disk tests below
    cfg = {**cfg, "preflight": {"minFreeGB": 0, **cfg.get("preflight", {})}}
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    bin_dir = tmp / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    for name, code in {"git": 0, **(fakes or {})}.items():
        f = bin_dir / name
        f.write_text(f"#!/bin/sh\nexit {code}\n")
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    env = {"PATH": str(bin_dir), "HOME": str(tmp)}  # only the fakes exist
    return subprocess.run(
        [sys.executable, str(PRE)], capture_output=True, text=True, cwd=repo, env=env
    )


def test_all_good_prints_one_ok_line(tmp_path: Path) -> None:
    res = _run(tmp_path, {"verify": "zzmake verify"}, fakes={"zzmake": 0})
    assert res.returncode == 0 and res.stdout.strip() == "PREFLIGHT OK"


def test_a_missing_tool_gets_one_fix_line(tmp_path: Path) -> None:
    res = _run(tmp_path, {"verify": "zzmake verify", "preflight": {"tools": ["uv"]}}, fakes={})
    assert res.returncode == 1
    fails = [x for x in res.stdout.splitlines() if x.startswith("FAIL")]
    assert len(fails) == 2 and any("uv" in x for x in fails) and any("zzmake" in x for x in fails)
    assert res.stdout.splitlines()[-1] == "PREFLIGHT FAIL 2"


def test_auth_checks_use_the_repos_own_fix_line(tmp_path: Path) -> None:
    cfg = {"preflight": {"auth": [{"name": "registry", "check": "authcheck", "fix": "tool login"}]}}
    res = _run(tmp_path, cfg, fakes={"authcheck": 1})
    assert "FAIL auth registry: tool login" in res.stdout and res.returncode == 1
    assert _run(tmp_path, cfg, fakes={"authcheck": 0}).returncode == 0


def test_docker_is_required_only_when_a_test_database_is_configured(tmp_path: Path) -> None:
    assert _run(tmp_path, {}, fakes={}).returncode == 0
    res = _run(tmp_path, {"db": {"test": {"container": "c", "port": 1, "template": "t"}}}, fakes={})
    assert "FAIL docker" in res.stdout and "Docker" in res.stdout
    res = _run(tmp_path, {"db": {"test": {}}}, fakes={"docker": 1})
    assert "FAIL docker" in res.stdout, "installed but not running is a failure too"
    assert _run(tmp_path, {"db": {"test": {}}}, fakes={"docker": 0}).returncode == 0


def test_D4_a_leftover_feature_prs_setting_is_not_a_config_failure(tmp_path: Path) -> None:
    cfg = {"delivery": "feature-prs", "milestones": {"merge": "local"}}
    assert "FAIL config delivery" not in _run(tmp_path, cfg).stdout


def test_S4_a_blocked_rule_without_a_message_has_no_route(tmp_path: Path) -> None:
    cfg = {
        "blocked": [
            {"match": "x"},
            {"match": "y", "message": "  "},
            {"match": "z", "message": "do w"},
        ]
    }
    res = _run(tmp_path, cfg)
    assert "FAIL config blocked[0]" in res.stdout and "FAIL config blocked[1]" in res.stdout
    assert "blocked[2]" not in res.stdout


def test_config_flag_checks_only_the_conflicts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sdlc.json").write_text(
        json.dumps({"verify": "zznothing run", "blocked": [{"match": "x"}]})
    )
    env = {"PATH": "/usr/bin:/bin"}
    res = subprocess.run(
        [sys.executable, str(PRE), "--config"], capture_output=True, text=True, cwd=repo, env=env
    )
    assert "FAIL config blocked[0]" in res.stdout and "FAIL tool" not in res.stdout


def test_low_free_disk_fails_with_the_free_gb_and_a_margin_warns(tmp_path: Path) -> None:
    free = shutil.disk_usage(tmp_path).free / 2**30
    res = _run(tmp_path, {"preflight": {"minFreeGB": free * 100}})
    line = next(x for x in res.stdout.splitlines() if x.startswith("FAIL disk"))
    assert f"{free:.0f}" in line or f"{free:.1f}" in line, line
    assert "minFreeGB" in line and res.returncode == 1
    warn = _run(tmp_path / "w", {"preflight": {"minFreeGB": free / 1.5}})
    assert any(x.startswith("WARN disk") for x in warn.stdout.splitlines()), warn.stdout
    assert warn.returncode == 0 and warn.stdout.splitlines()[-1] == "PREFLIGHT OK"
    fine = _run(tmp_path / "f", {"preflight": {"minFreeGB": free / 10}})
    assert fine.stdout.strip() == "PREFLIGHT OK"


def test_the_config_only_run_never_looks_at_the_disk(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sdlc.json").write_text("{}")
    env = {"PATH": str(tmp_path), "HOME": str(tmp_path)}
    out = subprocess.run(
        [sys.executable, str(PRE), "--config"], capture_output=True, text=True, cwd=repo, env=env
    )
    assert out.stdout.strip() == "PREFLIGHT OK", "CI's --config run never looks at the disk"


def test_the_selected_engine_is_the_one_probed(tmp_path: Path) -> None:
    cfg = {"db": {"test": {"engine": "podman"}}}
    ok = _run(tmp_path, cfg, fakes={"podman": 0, "docker": 1})
    assert ok.returncode == 0, "podman works; a broken docker is not asked"
    bad = _run(tmp_path, cfg, fakes={"podman": 1})
    assert "FAIL podman" in bad.stdout and "docker" not in bad.stdout.lower().replace("podman", "")
