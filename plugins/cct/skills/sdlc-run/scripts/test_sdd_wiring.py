"""Usage: pytest scripts/test_sdd_wiring.py

The gate, status and hooks wired to spec.py: layout 4 is checked, the old layout is not.
"""

from __future__ import annotations

import json
import os
import re
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
    assert json.loads((c / "lock.json").read_text())["layout"] == 4
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


# ------------------------------------------------------------------ the lock covers routing and rules


def locked(tmp_path: Path) -> tuple[Path, Path]:
    repo = base_repo(tmp_path)
    c = v4(repo)
    commit(repo)
    assert gate(repo, "approve", ID).returncode == 0
    commit(repo, "approved")
    assert last(gate(repo, "feature", ID)).startswith("VERIFY PASS")
    return repo, c


def test_layout_4_locks_the_routing_fields_of_decisions_json(tmp_path: Path) -> None:
    repo, c = locked(tmp_path)
    assert "decisions.routing" in json.loads((c / "lock.json").read_text())["criteria"]
    (c / "decisions.json").write_text('{"layout": 4, "size": "L"}')
    commit(repo, "edit routing")
    r = gate(repo, "feature", ID)
    assert last(r) == "VERIFY BLOCKED reason=protected-path" and "decisions.routing" in r.stdout


def test_layout_4_locks_each_approved_rule_by_id_and_content(tmp_path: Path) -> None:
    repo, c = locked(tmp_path)
    assert "rules/R1.md" in json.loads((c / "lock.json").read_text())["criteria"]
    rule(repo, "billing", 1)  # status planned -> live: not a change of the rule
    commit(repo, "live")
    assert last(gate(repo, "feature", ID)).startswith("VERIFY PASS")
    sh(repo, "git", "mv", "specs/billing", "specs/payments")  # same content, another capability
    commit(repo, "move")
    assert last(gate(repo, "feature", ID)).startswith("VERIFY PASS")
    rule(repo, "payments", 1, "When x, the system shall do something else.")
    commit(repo, "edit")
    r = gate(repo, "feature", ID)
    assert last(r) == "VERIFY BLOCKED reason=protected-path" and "rules/R1.md" in r.stdout


# ------------------------------------------------------------------ state/ behind one reader


def test_state_path_reads_the_new_place_first_and_the_old_second(tmp_path: Path) -> None:
    import spec

    (tmp_path / "decisions.json").write_text("{}")
    assert spec.state_path(tmp_path, "decisions.json") == tmp_path / "decisions.json"
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "intake.json").write_text('{"layout": 4}')  # decisions.json is intake.json there
    assert spec.state_path(tmp_path, "decisions.json") == tmp_path / "state" / "intake.json"
    assert spec.applies(tmp_path)
    assert spec.state_path(tmp_path, "lock.json") == tmp_path / "lock.json"  # neither exists: the old place
    (tmp_path / "state" / "lock.json").write_text("{}")
    assert spec.state_path(tmp_path, "lock.json") == tmp_path / "state" / "lock.json"


def test_the_gate_and_status_read_machine_files_from_state(tmp_path: Path) -> None:
    repo, c = locked(tmp_path)
    (c / "state").mkdir()
    for old, new in (("decisions.json", "intake.json"), ("lock.json", "lock.json"), ("done.json", "done.json")):
        sh(repo, "git", "mv", f"changes/{ID}/{old}", f"changes/{ID}/state/{new}")
    commit(repo, "state")
    assert last(gate(repo, "feature", ID)).startswith("VERIFY PASS")
    (c / "state" / "intake.json").write_text('{"layout": 4, "size": "L"}')
    commit(repo, "routing moved")
    assert last(gate(repo, "feature", ID)) == "VERIFY BLOCKED reason=protected-path"
    out = status(repo, "map", ID).stdout
    assert "stage  5/7" in out  # the lock is found under state/


# ------------------------------------------------------------------ CI runs the drift check


def _spec_steps(workflow: Path, job: str) -> tuple[dict, list[dict]]:
    import yaml

    doc = yaml.safe_load(workflow.read_text())
    return doc, doc["jobs"][job]["steps"]


@pytest.mark.parametrize(
    "path,job",
    [(SKILL / "templates/ci/github-actions.yml", "spec"), (SKILL.parents[3] / ".github/workflows/ci.yml", "tests")],
)
def test_ci_runs_the_spec_check_against_the_base_on_a_full_clone(path: Path, job: str) -> None:
    doc, steps = _spec_steps(path, job)
    checkout = next(s for s in steps if str(s.get("uses", "")).startswith("actions/checkout"))
    assert checkout["with"]["fetch-depth"] == 0
    run = next(s["run"] for s in steps if "scripts/spec.py check" in str(s.get("run", "")))
    assert re.search(r"--base \"?origin/", run)
    if job == "spec":  # the one required status waits for it
        assert "spec" in doc["jobs"]["check"]["needs"]
