"""The 3.21.0 fix round (cct#41 review): each test reproduces the review's scenario."""

# ruff: noqa: F811, F401, E402, I001 -- imported fixtures (repo) are used as test arguments
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from test_sdlc_status import BRANCH, GATE, ID, PASS, _gate, _goal, _owner, _pr, _sh, sdlc_status

STAMP = 1_000_000_000


def _write(path: Path, data: dict, mtime: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    os.utime(path, ns=(mtime * 10**9, mtime * 10**9))


def _bound_report(result: str, mtime: int, **over) -> dict:
    return {"scope": "milestone", "id": ID, "result": result, "sha": GATE, "change": ID, "owner": "", "milestone": 1, **over}


# --- 3: a newer failure from an older writer beats an older pass ------------------------------------


def _passed_with_3_21(repo: Path) -> Path:
    """M1 passed with the new gate: its receipt and the shared copy, both older than what follows."""
    verify = repo / "changes" / ID / "verify"
    report = _bound_report(PASS, STAMP, format=2)
    _write(verify / "milestone-1.json", report, STAMP)
    _write(repo / ".git/sdlc/passes" / ID / "milestone-1.json", report, STAMP)
    return verify


def test_a_newer_3_18_failure_beats_a_3_21_pass_H3(repo: Path) -> None:
    verify = _passed_with_3_21(repo)
    failure = _bound_report(f"VERIFY FAIL milestone {ID} check=unit", 0)  # 3.18: no `format`, report.json only
    del failure["sha"]
    _write(verify / "report.json", failure, STAMP + 100)
    code, line = _goal(repo, {BRANCH: _pr("OPEN", armed=True)}, n=1)
    assert code == 1 and "milestone-gate-pass" in line, (code, line)


def test_a_newer_pass_still_beats_an_older_failure_H3(repo: Path) -> None:
    verify = _passed_with_3_21(repo)
    failure = _bound_report(f"VERIFY FAIL milestone {ID} check=unit", 0)
    _write(verify / "report.json", failure, STAMP - 100)
    assert _goal(repo, {BRANCH: _pr("OPEN", armed=True)}, n=1)[0] == 0


# --- 4: an accepted Ask PR stays DONE once merged ---------------------------------------------------


def test_a_merged_ask_pr_the_owner_accepted_stays_done_H4(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _gate(repo, PASS)
    _owner(repo, tmp_path, "PR7", "Accept milestone", monkeypatch)
    armed = _goal(repo, {BRANCH: _pr("OPEN", armed=True, labels=("ask",))})
    assert armed[0] == 0, armed
    sdlc_status.sys.modules["marks"]._ANSWERS.clear()  # one process per poll in real use
    merged = _goal(repo, {BRANCH: _pr("MERGED", labels=("ask",))})
    assert merged == (0, f"GOAL {ID} DONE pr=7 state=merged gate={GATE}"), merged


def test_a_merged_ask_pr_without_an_answer_is_still_unsigned_H4(repo: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    _gate(repo, PASS)
    assert _goal(repo, {BRANCH: _pr("MERGED", labels=("ask",))}) == (1, f"GOAL {ID} OPEN pr-7-awaits-owner")


def test_a_merged_pr_the_owner_held_is_held_H4(repo: Path, tmp_path: Path, monkeypatch) -> None:
    _gate(repo, PASS)
    _owner(repo, tmp_path, "PR7", "Hold", monkeypatch)
    assert _goal(repo, {BRANCH: _pr("MERGED", labels=("ask",))}) == (1, f"GOAL {ID} OPEN pr-7-held")


# --- 5: a removed folder is DONE only when the whole project is ------------------------------------


def _merged(head: str, base: str, number: int) -> dict:
    return {"number": number, "headRefName": head, "baseRefName": base, "state": "MERGED"}


def _commit_plan(repo: Path, milestones: int) -> None:
    rows = "".join(f"| M{i} | m |\n" for i in range(1, milestones + 1))
    plan = repo / "changes" / ID / "plan.md"
    plan.write_text(f"# Plan: R\n\n## Milestones\n\n| # | what |\n|---|---|\n{rows}")
    _sh(repo, "add", "-A")
    _sh(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "plan")
    shutil.rmtree(repo / "changes" / ID)  # the owner's rule: removed after merge


def _removed(repo: Path, merged: list[dict], n: int | None = None):
    return sdlc_status.goal_removed(repo, ID, "milestone", n, gh=lambda root, *a: merged)


def test_one_merged_milestone_of_a_project_is_not_the_whole_goal_H5_no_plan(repo: Path) -> None:
    m1 = _merged("milestone/redesign-r2-1", "project/big", 5)
    assert _removed(repo, [m1]) is None  # merged into the project branch, M2 still open
    done = _removed(repo, [m1, _merged("project/big", "main", 9)])
    assert done == (0, f"GOAL {ID} DONE pr=9 state=merged folder=removed")


def test_every_planned_milestone_merged_is_done_and_one_is_not_H5_with_plan(repo: Path) -> None:
    _commit_plan(repo, 2)
    m1 = _merged("milestone/redesign-r2-1", "project/big", 5)
    m2 = _merged("milestone/redesign-r2-2", "project/big", 6)
    assert _removed(repo, [m1]) is None
    assert _removed(repo, [m1, m2])[0] == 0
    assert _removed(repo, [m1], n=1)[0] == 0  # asking about M1 alone: M1 merged is its answer


def test_a_milestone_merged_into_the_trunk_without_a_plan_is_done_H5(repo: Path) -> None:
    assert _removed(repo, [_merged("milestone/redesign-r2-1", "main", 5)])[0] == 0


# --- 10: the handoff beats the blocked report --------------------------------------------------------


def test_a_retry_cap_handoff_wins_over_the_blocked_gate_report_H10(repo: Path) -> None:
    _gate(repo, "VERIFY BLOCKED reason=attempts")
    change = repo / "changes" / ID
    path = sdlc_status.spec.state_path(change, "handoff.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"cap": "retries", "what": "w", "why": "y", "next": "n"}))
    code, line = sdlc_status.goal(repo, change, "milestone", None, gh=lambda root, *a: [])
    assert (code, line) == (4, f"GOAL {ID} HANDOFF cap=retries")


# --- 6: `spec.py outcome write` on the default layout reads intent.md --------------------------------

SPEC = Path(__file__).resolve().parents[1] / "templates/scripts/spec.py"


def _outcome(tmp_path: Path, files: dict[str, str], decisions: dict | None = None) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    change = repo / "changes" / ID
    change.mkdir(parents=True)
    for name, text in files.items():
        (change / name).write_text(text)
    if decisions:
        (change / "decisions.json").write_text(json.dumps(decisions))
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return subprocess.run(["python3", str(SPEC), "outcome", "write", f"changes/{ID}"], cwd=repo, capture_output=True, text=True)


def test_outcome_write_reads_intent_md_on_the_default_layout_H6(tmp_path: Path) -> None:
    intent = "# Intent\n\n## Success measure\n\n- **Measure:** signups, **target:** 100\n\n## Problem\n\nx\n"
    run = _outcome(tmp_path, {"intent.md": intent, "facts.md": "F1 x\n", "plan.md": "# Plan\n"})
    assert run.returncode == 0, run.stderr
    rec = json.loads((tmp_path / "repo/.sdlc/outcomes" / f"{ID}.json").read_text())
    assert "signups" in rec["measure"] and rec["rules"] == []


def test_outcome_write_still_reads_spec_md_on_layout_4_H6(tmp_path: Path) -> None:
    spec = "---\ncapabilities: [a]\n---\n# Spec\n\n## Success measure\n\n- **Measure:** orders\n\n## Requirements\n"
    run = _outcome(tmp_path, {"spec.md": spec}, {"layout": 4})
    assert run.returncode == 0, run.stderr
    assert "orders" in json.loads((tmp_path / "repo/.sdlc/outcomes" / f"{ID}.json").read_text())["measure"]


# --- 8: chain-gate.sh on a scope-S layout-4 change ---------------------------------------------------

from test_chain_gate import ID as HOOK_ID
from test_chain_gate import _edit as _hook_edit
from test_chain_gate import repo as hook_repo


def _layout_4(repo: Path, scope: str, tasks: str | None = None) -> None:
    change = repo / "changes" / HOOK_ID
    for old in ("intent.md", "facts.md", "plan.md"):
        (change / old).unlink()
    (change / "decisions.json").write_text(json.dumps({"layout": 4, "milestone": {"kind": "single", "slug": "trial"}}))
    (change / "lock.json").write_text(json.dumps({"layout": 4}))  # after approval the lock names the layout
    (change / "spec.md").write_text(f"---\nstatus: approved\nscope: {scope}\n---\n\n# Spec\n")
    if tasks is not None:
        (change / "tasks.md").write_text(tasks)


def test_a_scope_s_layout_4_change_needs_no_handover_to_edit_source_H8(hook_repo: Path) -> None:
    _layout_4(hook_repo, "S")
    done = _hook_edit(hook_repo, "src/app.ts", "active")
    assert done.returncode == 0, done.stdout + done.stderr
    assert _hook_edit(hook_repo, "src/app.ts", "none").returncode != 0  # the /goal rule still holds


def test_a_scope_m_layout_4_change_still_needs_its_handover_H8(hook_repo: Path) -> None:
    _layout_4(hook_repo, "M", "---\nstatus: approved\n---\n\n## Handover\n\n")
    blocked = _hook_edit(hook_repo, "src/app.ts", "active")
    assert blocked.returncode != 0 and "Handover" in blocked.stdout + blocked.stderr
    (hook_repo / "changes" / HOOK_ID / "tasks.md").write_text("---\nstatus: approved\n---\n\n## Handover\n\nDeliver it.\n")
    assert _hook_edit(hook_repo, "src/app.ts", "active").returncode == 0


# --- 7 and 9: the installed guardrail suites -----------------------------------------------------------

import shutil as _shutil

from test_adopt import _adopt, _env, _repo

V4_ID = "2026-11-19-v4-thing"
CHANGE_TESTS = "change or frontmatter or plan or intent or spec_lists"


def _v4_docs(scope: str) -> dict[str, str]:
    head = f"---\nlinear: none\ntype: spec\nchange: {V4_ID}\ndesign: null\nauthor: t@t\nstatus: approved\ncreated: 2026-11-19\nscope: {scope}\n---\n\n# Spec\n"
    other = lambda kind: f"---\ntype: {kind}\nchange: {V4_ID}\nauthor: t@t\nstatus: approved\ncreated: 2026-11-19\n---\n\n# {kind}\n"  # noqa: E731
    docs = {"spec.md": head}
    if scope in ("M", "L"):
        docs["tasks.md"] = other("tasks")
    if scope == "L":
        docs["design.md"] = other("design")
    return docs


def _adopted(tmp_path: Path, kind: str) -> Path:
    repo = _repo(tmp_path, kind)
    assert _adopt(repo).returncode == 0
    return repo


def _commit_all(repo: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=_env())
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"], cwd=repo, check=True, env=_env())


def _pytest_suite(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_sdlc.py", "-q", "-p", "no:cacheprovider", "-k", CHANGE_TESTS],
        cwd=repo, capture_output=True, text=True, env=_env(),
    )  # fmt: skip


@pytest.mark.parametrize("scope", ["S", "M", "L"])
def test_the_python_suite_accepts_a_layout_4_change_beside_an_old_one_H7(tmp_path: Path, scope: str) -> None:
    repo = _adopted(tmp_path, "python")
    change = repo / "changes" / V4_ID
    change.mkdir()
    for name, text in _v4_docs(scope).items():
        (change / name).write_text(text)
    (change / "decisions.json").write_text(json.dumps({"layout": 4}))
    _commit_all(repo)
    run = _pytest_suite(repo)
    assert run.returncode == 0, run.stdout[-1500:]


def test_the_python_suite_still_rejects_a_layout_4_change_missing_its_documents_H7(tmp_path: Path) -> None:
    repo = _adopted(tmp_path, "python")
    change = repo / "changes" / V4_ID
    change.mkdir()
    (change / "spec.md").write_text(_v4_docs("M")["spec.md"])  # scope M, no tasks.md
    _commit_all(repo)
    run = _pytest_suite(repo)
    assert run.returncode != 0 and "tasks.md" in run.stdout


def test_the_python_suite_passes_when_the_last_change_is_removed_H9(tmp_path: Path) -> None:
    repo = _adopted(tmp_path, "python")
    for folder in (repo / "changes").iterdir():
        if folder.name != "archive":
            _shutil.rmtree(folder)
    _commit_all(repo)
    run = _pytest_suite(repo)
    assert run.returncode == 0, run.stdout[-1500:]


@pytest.mark.skipif(not _shutil.which("vitest"), reason="vitest is not installed")
@pytest.mark.parametrize("case", ["layout-4", "no-change"])
def test_the_node_suite_accepts_layout_4_and_no_change_H7_H9(tmp_path: Path, case: str) -> None:
    repo = _adopted(tmp_path, "node")
    for folder in (repo / "changes").iterdir():
        if folder.name != "archive" and case == "no-change":
            _shutil.rmtree(folder)
    if case == "layout-4":
        change = repo / "changes" / V4_ID
        change.mkdir()
        for name, text in _v4_docs("L").items():
            (change / name).write_text(text)
        (change / "decisions.json").write_text(json.dumps({"layout": 4}))
    _commit_all(repo)
    run = subprocess.run(["vitest", "run", "tests/sdlc.test.ts", "-t", "changes"], cwd=repo, capture_output=True, text=True, env=_env())
    assert run.returncode == 0, run.stdout[-1500:] + run.stderr[-500:]


# --- 12: status.sh --current on layout 4 -------------------------------------------------------------

STATUS = Path(__file__).parent / "status.sh"


def _stage(repo: Path) -> str:
    out = subprocess.run(
        ["bash", str(STATUS), "--current"], capture_output=True, text=True, cwd=repo,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)},
    ).stdout  # fmt: skip
    line = next(line for line in out.splitlines() if "\tstate=" in line)
    return line.split("state=")[1].split("\t")[0]


def test_status_reads_the_layout_4_stage_from_its_documents_and_the_lock_H12(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    change = repo / "changes" / "2026-11-19-trial"
    change.mkdir(parents=True)
    (repo / "sdlc.json").write_text("{}")
    subprocess.run(["git", "init", "-q", "-b", "feat/trial"], cwd=repo, check=True, env=_env())
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x", "--allow-empty"], cwd=repo, check=True, env=_env())
    spec = change / "spec.md"
    spec.write_text("---\nstatus: draft\nscope: M\n---\n")
    assert _stage(repo) == "intent"  # not "facts" or "intent" by the absence of facts.md
    spec.write_text("---\nstatus: in-review\nscope: M\n---\n")
    assert _stage(repo) == "intent-in-review"
    spec.write_text("---\nstatus: approved\nscope: M\n---\n")
    assert _stage(repo) == "plan-draft"  # tasks.md is not written
    (change / "tasks.md").write_text("---\nstatus: approved\n---\n")
    assert _stage(repo) == "plan-draft"  # approved, but no lock
    (change / "state").mkdir()
    (change / "state" / "lock.json").write_text("{}")
    assert _stage(repo) == "build"
    spec.write_text("---\nstatus: approved\nscope: S\n---\n")
    (change / "tasks.md").unlink()
    assert _stage(repo) == "build"  # scope S: the spec alone and the lock


# --- 11: heavy.py writes its ticket inside the queue lock, atomically --------------------------------

import fcntl
import importlib.util
import threading

HEAVY_PY = Path(__file__).resolve().parents[1] / "templates/scripts/heavy.py"


def _heavy_module():
    spec = importlib.util.spec_from_file_location("heavy_under_test", HEAVY_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_ticket_is_written_only_while_the_queue_lock_is_held_H11(tmp_path: Path) -> None:
    heavy = _heavy_module()
    queue = heavy.Queue(tmp_path, 1)
    held = open(tmp_path / "queue.lock", "a+")
    fcntl.flock(held, fcntl.LOCK_EX)  # a status scan is inside the lock right now
    worker = threading.Thread(target=lambda: queue.enter(["x"], "run"))
    worker.start()
    worker.join(timeout=0.5)
    assert worker.is_alive() and not list((tmp_path / "tickets").iterdir())  # no half-written ticket to scan
    fcntl.flock(held, fcntl.LOCK_UN)
    worker.join(timeout=5)
    (ticket,) = (tmp_path / "tickets").glob("*.json")
    assert json.loads(ticket.read_text())["pid"] == os.getpid()
    assert sorted(p.name for p in (tmp_path / "tickets").iterdir()) == [ticket.name]  # no temp file is left


def test_a_scan_never_deletes_a_ticket_being_created_H11(tmp_path: Path) -> None:
    heavy = _heavy_module()
    queue = heavy.Queue(tmp_path, 1)
    made: list[Path] = []
    stop = threading.Event()

    def scan() -> None:
        while not stop.is_set():
            with queue._locked():
                queue._live()

    scanner = threading.Thread(target=scan)
    scanner.start()
    try:
        for _ in range(300):
            made.append(queue.enter(["x"], "run"))
    finally:
        stop.set()
        scanner.join()
    assert [p for p in made if not p.exists()] == []
