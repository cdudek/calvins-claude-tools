"""Usage: pytest scripts/test_sdd_wiring.py

The gate, status and hooks wired to spec.py: layout 4 is checked, the old layout is not.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_spec import SPEC, TASKS, _change, commit, rule, sh, tfile

SKILL = Path(__file__).resolve().parents[1]
GATE = SKILL / "templates" / "scripts" / "verify_gate.py"
ID = "2026-11-20-retry"


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def gate(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE), *args], cwd=repo, capture_output=True, text=True, env=_env()
    )


def last(r: subprocess.CompletedProcess[str]) -> str:
    return r.stdout.strip().splitlines()[-1]


def base_repo(tmp_path: Path, on_master: bool = False) -> Path:
    """A repo on master; `on_master` puts R1 and its tagged test there already."""
    repo = tmp_path / "repo"
    repo.mkdir()
    sh(repo, "git", "init", "-q", "-b", "master")
    sh(repo, "git", "config", "user.email", "t@example.com")
    sh(repo, "git", "config", "user.name", "t")
    cfg = {"defaultBranch": "master", "checks": {"milestone": ["true"], "feature": ["true"]}}
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    (repo / "README.md").write_text("x\n")
    if on_master:
        rule(repo, "billing", 1)
        tfile(repo, "test_retry.py", "# @R1", "def test_retry(): pass")
    commit(repo, "init")
    sh(repo, "git", "checkout", "-q", "-b", "milestone/retry")
    return repo


def v4(repo: Path, **kw) -> Path:
    c = _change(repo, "S", tasks=TASKS, **kw)
    rule(repo, "billing", 1, status="planned")
    return c


# ------------------------------------------------------------------ approve


def test_approve_locks_the_spec_documents_and_derives_done_json_from_the_rules(tmp_path: Path) -> None:
    repo = base_repo(tmp_path)
    c = v4(repo)
    commit(repo)
    r = gate(repo, "approve", ID)
    assert r.returncode == 0, r.stdout
    crit = json.loads((c / "lock.json").read_text())["criteria"]
    assert {"spec.md", "tasks.md", "checks"} <= set(crit) and "facts.md" not in crit
    facts = json.loads((c / "done.json").read_text())["facts"]
    assert [(f["id"], f["tag"]) for f in facts] == [("R1", "@R1")]


def test_approve_refuses_what_the_consistency_check_refuses(tmp_path: Path) -> None:
    repo = base_repo(tmp_path)
    c = _change(repo, "S", a1="pending")
    commit(repo)
    r = gate(repo, "approve", ID)
    assert r.returncode == 1 and "still pending" in r.stdout
    assert last(r).startswith("APPROVE FAIL") and not (c / "lock.json").exists()
