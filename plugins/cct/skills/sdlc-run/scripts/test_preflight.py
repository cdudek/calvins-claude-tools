"""Usage: pytest scripts/test_preflight.py

preflight.py checks tools, auth, Docker and two config conflicts once, and prints one fix line per
failure. Each case runs it in a scratch repo with a PATH that holds only the fakes it needs.
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path

PRE = Path(__file__).resolve().parents[1] / "templates/scripts/preflight.py"


def _run(tmp: Path, cfg: dict, *, fakes: dict[str, int] | None = None):
    repo = tmp / "repo"
    repo.mkdir(parents=True, exist_ok=True)
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


def test_D4_feature_prs_with_local_milestones_is_refused_with_both_ways_out(tmp_path: Path) -> None:
    cfg = {"delivery": "feature-prs", "milestones": {"merge": "local"}}
    res = _run(tmp_path, cfg)
    assert "FAIL config delivery" in res.stdout
    assert 'milestones.merge "pr"' in res.stdout and 'delivery "one-go"' in res.stdout
    fine = {"delivery": "feature-prs", "milestones": {"merge": "pr"}}
    assert _run(tmp_path / "ok", fine).returncode == 0


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
