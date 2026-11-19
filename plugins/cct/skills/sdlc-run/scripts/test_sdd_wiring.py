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


# ------------------------------------------------------------------ milestone

VALIDATION = "| R1 | retry | ran | tests/test_retry.py::test_retry | met |\n"


def approved(repo: Path, c: Path) -> None:
    commit(repo)
    assert gate(repo, "approve", ID).returncode == 0
    (c / "validation.md").write_text(VALIDATION)
    (c / "findings.md").write_text("## Converge\n\nConverged: round 1\n")
    commit(repo)


def test_milestone_takes_its_facts_from_the_tasks_and_passes_when_the_rule_is_live_and_tested(
    tmp_path: Path,
) -> None:
    repo = base_repo(tmp_path)
    c = v4(repo)
    approved(repo, c)
    rule(repo, "billing", 1)  # planned to live at the milestone
    tfile(repo, "test_retry.py", "# @R1", "def test_retry(): pass")
    commit(repo)
    r = gate(repo, "milestone", ID)
    assert last(r).startswith(f"VERIFY PASS milestone {ID}"), r.stdout


def test_milestone_fails_on_spec_drift_a_changed_rule_without_its_test(tmp_path: Path) -> None:
    repo = base_repo(tmp_path, on_master=True)
    sh(repo, "git", "checkout", "-q", "milestone/retry")
    c = _change(repo, "S", tasks=TASKS)
    (c / "spec.md").write_text((c / "spec.md").read_text().replace("| new |", "| changed |"))
    rule(repo, "billing", 1, "When x, the system shall z.", status="planned")
    approved(repo, c)
    rule(repo, "billing", 1, "When x, the system shall z.")
    commit(repo)
    r = gate(repo, "milestone", ID)
    assert last(r) == f"VERIFY FAIL milestone {ID} check=spec", r.stdout
    assert "R1 changed but no test tagged @R1 changed with it" in r.stdout
    tfile(repo, "test_retry.py", "# @R1", "def test_retry(): assert True")
    commit(repo)
    assert last(gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")


# ------------------------------------------------------------------ status

STATUS = SKILL / "scripts" / "sdlc_status.py"


def status(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(STATUS), *args], cwd=repo, capture_output=True, text=True, env=_env()
    )


def test_status_reads_task_states_from_tasks_md_in_layout_4(tmp_path: Path) -> None:
    repo = base_repo(tmp_path)
    c = v4(repo)
    (c / "tasks.md").write_text(TASKS.replace("| todo |", "| done |", 1))
    out = status(repo, "map", ID).stdout
    assert "this milestone  1 of 2 merged" in out and "T1" in out and "T2" in out
    assert "stage  4/7" in out  # tasks.md is the plan
