"""Usage: pytest scripts/test_sdd_hooks.py

chain-gate.sh and pr-gate.sh on a layout-4 change. The old layout keeps its rules.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "templates" / "hooks"
ID = "2026-11-20-retry"
GOAL = [{"type": "attachment", "attachment": {"type": "goal_status", "met": False, "sentinel": True}}]
APPROVED = "---\nstatus: approved\n---\n"


def make(tmp_path: Path, v4: bool = True) -> Path:
    repo = tmp_path / "repo"
    (repo / ".claude" / "hooks").mkdir(parents=True)
    for name in ("chain-gate.sh", "sdlc-config.sh", "goal_active.py", "block_state.py", "pass_proof.py"):
        shutil.copy(HOOKS / name, repo / ".claude" / "hooks" / name)
    (repo / "sdlc.json").write_text(json.dumps({"changesDir": "changes"}))
    c = repo / "changes" / ID
    c.mkdir(parents=True)
    d = {"size": "M", "milestone": {"kind": "single", "slug": "retry"}}
    if v4:
        (c / "decisions.json").write_text(json.dumps({**d, "layout": 4}))
        (c / "spec.md").write_text(APPROVED)
        (c / "tasks.md").write_text(APPROVED + "\n## Handover\n\nBuild T1.\n")
    else:
        (c / "decisions.json").write_text(json.dumps(d))
        (c / "intent.md").write_text(APPROVED)
        (c / "facts.md").write_text(APPROVED)
        (c / "plan.md").write_text(APPROVED + "\n## Goal handover\n\nDeliver.\n")
    (c / "lock.json").write_text(json.dumps({"layout": 4 if v4 else 3}))
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q", "-b", "feat/retry"], cwd=repo, check=True, env=env)
    return repo


def edit(repo: Path, file: str, **tool: str) -> subprocess.CompletedProcess[str]:
    t = repo.parent / "t.jsonl"
    t.write_text("".join(json.dumps(e) + "\n" for e in GOAL))
    payload = {"tool_input": {"file_path": file, **tool}, "transcript_path": str(t)}
    return subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / "chain-gate.sh")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)},
    )


RULE = "specs/billing/rules/R1.md"


@pytest.mark.parametrize("file", [RULE, ".sdlc/last-rule-id", f"changes/{ID}/spec.md"])
def test_rule_files_the_floor_and_the_spec_are_protected_after_approval(
    tmp_path: Path, file: str
) -> None:
    repo = make(tmp_path)
    r = edit(repo, file)
    assert r.returncode == 2 and "protectedEdit" in r.stderr
    p = repo / "changes" / ID / "decisions.json"
    p.write_text(json.dumps({**json.loads(p.read_text()), "protectedEdit": "owner: change it"}))
    assert edit(repo, file).returncode == 0


def _write_decisions(repo: Path, **d: object) -> subprocess.CompletedProcess[str]:
    return edit(repo, f"changes/{ID}/decisions.json", content=json.dumps(d))


def test_the_layout_comes_from_the_lock_not_from_decisions_json_or_file_presence(tmp_path: Path) -> None:
    repo = make(tmp_path)
    c = repo / "changes" / ID
    cur = json.loads((c / "decisions.json").read_text())
    r = _write_decisions(repo, **{k: v for k, v in cur.items() if k != "layout"})
    assert r.returncode == 2 and "protectedEdit" in r.stderr
    assert _write_decisions(repo, **cur, other="fine").returncode == 0  # layout unchanged
    old = {"old_string": '"layout": 4', "new_string": '"layout": 3'}
    assert edit(repo, f"changes/{ID}/decisions.json", **old).returncode == 2
    (c / "facts.md").write_text(APPROVED)  # file presence cannot switch it either
    assert edit(repo, f"changes/{ID}/spec.md").returncode == 2
    (c / "decisions.json").write_text(json.dumps({**cur, "protectedEdit": "owner: switch it"}))
    assert _write_decisions(repo, **{**cur, "layout": 3, "protectedEdit": "owner: switch it"}).returncode == 0


@pytest.mark.parametrize("v4", [True, False])
def test_a_lock_without_a_layout_protects_the_files_of_both_layouts(tmp_path: Path, v4: bool) -> None:
    repo = make(tmp_path, v4=v4)
    (repo / "changes" / ID / "lock.json").write_text("{}\n")
    for f in ("spec.md", "facts.md", "design.md", "done.json"):
        assert edit(repo, f"changes/{ID}/{f}").returncode == 2, f


def test_a_status_flip_of_a_rule_and_a_task_tick_stay_open(tmp_path: Path) -> None:
    repo = make(tmp_path)
    r = edit(repo, RULE, old_string="status: planned", new_string="status: live")
    assert r.returncode == 0, r.stderr
    assert edit(repo, f"changes/{ID}/tasks.md").returncode == 0


def test_the_old_layout_does_not_protect_rule_files_or_spec_md(tmp_path: Path) -> None:
    repo = make(tmp_path, v4=False)
    assert edit(repo, RULE).returncode == 0
    assert edit(repo, f"changes/{ID}/spec.md").returncode == 0


def test_layout_4_has_no_intent_or_facts_ordering_rule(tmp_path: Path) -> None:
    repo = make(tmp_path)
    (repo / "changes" / ID / "lock.json").unlink()
    assert edit(repo, f"changes/{ID}/spec/brief.md").returncode == 0
    assert edit(repo, f"changes/{ID}/design.md").returncode == 0  # no facts.md needed
    legacy = make(tmp_path / "old", v4=False)
    (legacy / "changes" / ID / "intent.md").write_text("---\nstatus: draft\n---\n")
    assert edit(legacy, f"changes/{ID}/spec/brief.md").returncode == 2


def test_the_layout_4_plan_gate_is_approved_status_on_the_three_documents(tmp_path: Path) -> None:
    repo = make(tmp_path)
    assert edit(repo, "src/app.py").returncode == 0
    (repo / "changes" / ID / "design.md").write_text("---\nstatus: draft\n---\n")
    r = edit(repo, "src/app.py")
    assert r.returncode == 2 and "design.md" in r.stderr
    (repo / "changes" / ID / "design.md").write_text(APPROVED)
    (repo / "changes" / ID / "spec.md").write_text("---\nstatus: draft\n---\n")
    r = edit(repo, "src/app.py")
    assert r.returncode == 2 and "spec.md" in r.stderr


# ------------------------------------------------------------------ outcomes ride along a pass

import sys  # noqa: E402

sys.path.insert(0, str(HOOKS))
import pass_proof  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()  # fmt: skip


def test_an_outcome_record_after_the_gate_keeps_the_pass_but_source_does_not(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "changes" / ID).mkdir(parents=True)
    (tmp_path / "changes" / ID / "lock.json").write_text("{}\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "gated")
    gated = _git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / ".sdlc" / "outcomes").mkdir(parents=True)
    (tmp_path / ".sdlc" / "outcomes" / f"{ID}.json").write_text("{}\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "outcome")
    assert pass_proof.proves(tmp_path, "changes", gated, _git(tmp_path, "rev-parse", "HEAD"))
    (tmp_path / "src.py").write_text("x = 1\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "source")
    assert not pass_proof.proves(tmp_path, "changes", gated, _git(tmp_path, "rev-parse", "HEAD"))


def test_readers_do_not_fail_when_a_change_folder_was_removed_after_merge(tmp_path: Path) -> None:
    assert pass_proof.change_paths(tmp_path / "changes", ID) == []
    (tmp_path / "sdlc.json").write_text("{}")
    (tmp_path / ".sdlc" / "outcomes").mkdir(parents=True)
    (tmp_path / ".sdlc" / "outcomes" / f"{ID}.json").write_text(json.dumps({"change": ID, "due": "2026-12-04"}))
    r = subprocess.run(
        ["bash", str(HOOKS.parents[1] / "scripts" / "status.sh"), "--shipped"],
        capture_output=True, text=True, env={**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)},
    )  # fmt: skip
    assert r.returncode == 0 and ID in r.stdout, r.stderr


# ------------------------------------------------------------------ state/ behind one reader


def test_the_hook_reads_state_and_protects_it_like_the_old_place(tmp_path: Path) -> None:
    repo = make(tmp_path)
    c = repo / "changes" / ID
    (c / "state").mkdir()
    (c / "decisions.json").rename(c / "state" / "intake.json")
    (c / "lock.json").rename(c / "state" / "lock.json")
    assert edit(repo, "src/app.py").returncode == 0  # decisions and lock found under state/
    for f in ("state/lock.json", "state/done.json", "lock.json", "spec.md"):
        r = edit(repo, f"changes/{ID}/{f}")
        assert r.returncode == 2 and "protectedEdit" in r.stderr, f
    cur = json.loads((c / "state" / "intake.json").read_text())
    r = edit(repo, f"changes/{ID}/state/intake.json", content=json.dumps({k: v for k, v in cur.items() if k != "layout"}))
    assert r.returncode == 2 and "layout" in r.stderr


# ------------------------------------------------------------------ one list of locked documents

sys.path.insert(0, str(HOOKS.parent / "scripts"))
import verify_gate  # noqa: E402

V4_TASKS = "## Tasks\n\n| Task | Rules | State |\n|---|---|---|\n| T1 build | R1 | todo |\n"


def _gated_layout4(repo: Path) -> str:
    c = repo / "changes" / ID
    c.mkdir(parents=True)
    for name, text in {"spec.md": "# s\n", "design.md": "# d\n", "tasks.md": V4_TASKS, "lock.json": "{}\n"}.items():
        (c / name).write_text(text)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "gated")
    return _git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("spec.md", "# s changed\n"),
        ("design.md", "# d changed\n"),
        ("tasks.md", V4_TASKS.replace("T1 build", "T1 build more")),
        ("done.json", "{}\n"),
    ],
)
def test_a_post_gate_edit_of_a_layout_4_document_voids_the_pass(tmp_path: Path, name: str, text: str) -> None:
    gated = _gated_layout4(tmp_path)
    (tmp_path / "changes" / ID / name).write_text(text)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "edit")
    assert not pass_proof.proves(tmp_path, "changes", gated, _git(tmp_path, "rev-parse", "HEAD"))


def test_a_tick_in_tasks_md_after_the_gate_keeps_the_pass(tmp_path: Path) -> None:
    gated = _gated_layout4(tmp_path)
    (tmp_path / "changes" / ID / "tasks.md").write_text(V4_TASKS.replace("todo", "done abc123"))
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "tick")
    assert pass_proof.proves(tmp_path, "changes", gated, _git(tmp_path, "rev-parse", "HEAD"))


@pytest.mark.parametrize("layout", [3, 4])
def test_the_pass_rule_the_hook_and_the_lock_hash_agree_on_the_locked_documents(tmp_path: Path, layout: int) -> None:
    c = tmp_path / "changes" / ID
    c.mkdir(parents=True)
    docs = (
        {"spec.md": "# s\n", "design.md": "# d\n", "tasks.md": V4_TASKS}
        if layout == 4
        else {"facts.md": "# f\n"}
    )
    for name, text in {**docs, "done.json": "{}\n"}.items():
        (c / name).write_text(text)
    (c / "decisions.json").write_text(json.dumps({"layout": layout}))
    hashed = {k for k in verify_gate.criteria_hash(c, []) if k.endswith((".md", ".json")) and "/" not in k}
    hashed -= {"plan.milestones", "decisions.routing"}
    locked = set(pass_proof.LOCKED_FILES[layout])
    assert hashed | {"lock.json"} == locked
    # the hook protects the same set, except tasks.md, which takes ticks
    repo = make(tmp_path / "hook", v4=layout == 4)
    for name in locked - set(pass_proof.TICKED_FILES):
        (repo / "changes" / ID / name).touch()
        r = edit(repo, f"changes/{ID}/{name}")
        assert r.returncode == 2 and "protectedEdit" in r.stderr, name


# ------------------------------------------------------------------ what a tick may and may not change

TICK_DOC = "# t\n\n## Tasks\n\n| Task | State |\n|---|---|\n| T1 build | todo |\n\n## Milestones\n\n| M | Facts |\n|---|---|\n| M1 | F1 |\n"


def _commit_all(repo: Path, msg: str = "edit") -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", msg)
    return _git(repo, "rev-parse", "HEAD")


def _gated_files(repo: Path, files: dict[str, str]) -> str:
    c = repo / "changes" / ID
    for name, text in files.items():
        (c / name).parent.mkdir(parents=True, exist_ok=True)
        (c / name).write_text(text)
    _git(repo, "init", "-q", "-b", "main")
    return _commit_all(repo, "gated")


@pytest.mark.parametrize(
    ("name", "old", "new"),
    [
        ("asks/session/tasks.md", "notes\n", "other notes\n"),  # evidence that is named tasks.md is still evidence
        ("tasks.md", TICK_DOC, TICK_DOC.replace("## Tasks", "## Handover")),  # approval no longer sees the rows
        ("tasks.md", TICK_DOC, TICK_DOC.replace("| T1 build | todo |\n", "")),
        ("tasks.md", TICK_DOC, TICK_DOC.replace("| M1 | F1 |", "| M1 | F1, F2 |")),  # the milestone allocation
        ("tasks.md", TICK_DOC, TICK_DOC.replace("## Milestones", "## Plan")),
    ],
)
def test_only_a_tick_of_the_top_level_task_rows_keeps_the_pass(tmp_path: Path, name: str, old: str, new: str) -> None:
    gated = _gated_files(tmp_path, {"spec.md": "# s\n", "tasks.md": TICK_DOC, name: old})
    (tmp_path / "changes" / ID / name).write_text(new)
    assert not pass_proof.proves(tmp_path, "changes", gated, _commit_all(tmp_path))


def test_a_tick_and_a_handover_edit_keep_the_pass(tmp_path: Path) -> None:
    gated = _gated_files(tmp_path, {"spec.md": "# s\n", "tasks.md": TICK_DOC})
    edited = TICK_DOC.replace("todo", "done abc123") + "\n## Handover\n\nresume at T2\n"
    (tmp_path / "changes" / ID / "tasks.md").write_text(edited)
    assert pass_proof.proves(tmp_path, "changes", gated, _commit_all(tmp_path))


def test_the_tick_rule_reads_the_rows_the_lock_hash_reads(tmp_path: Path) -> None:
    c = tmp_path / "changes" / ID
    c.mkdir(parents=True)
    (c / "spec.md").write_text("# s\n")
    for text in (TICK_DOC, TICK_DOC.replace("## Tasks", "## Handover"), TICK_DOC.replace("todo", "done x")):
        (c / "tasks.md").write_text(text)
        assert pass_proof.tasks_lock(text) == verify_gate.spec.lock_inputs(c)["tasks.md"]


def _lock(*keys: str) -> str:
    return json.dumps({"criteria": {k: "x" for k in keys}})


PLAN = "# p\n\n## Milestones\n\n| M | Facts |\n|---|---|\n| M1 | F1 |\n\n## Notes\n\nfree\n"


@pytest.mark.parametrize(
    ("file", "old", "new", "keys", "holds"),
    [
        ("plan.md", PLAN, PLAN.replace("| M1 | F1 |", "| M1 | F1, F2 |"), ("plan.milestones",), False),
        ("plan.md", PLAN, PLAN.replace("free", "still free"), ("plan.milestones",), True),
        ("plan.md", PLAN, PLAN.replace("| M1 | F1 |", "| M1 | F1, F2 |"), (), True),  # an older lock never locked it
        ("decisions.json", '{"size": "M"}', '{"size": "S"}', ("decisions.routing",), False),
        ("decisions.json", '{"size": "M"}', '{"size": "M", "visualSource": "x"}', ("decisions.routing",), False),
        ("decisions.json", '{"size": "M"}', '{"size": "M", "note": "x"}', ("decisions.routing",), True),
        ("decisions.json", '{"size": "M"}', '{"size": "S"}', (), True),
        ("state/intake.json", '{"size": "M"}', '{"size": "S"}', ("decisions.routing",), False),
        ("screens.json", '[{"id": "a"}]', '[{"id": "a"}, {"id": "b"}]', ("screens.json",), False),  # 3.25.0 inventory
        ("screens.json", '[{"id": "a"}]', '[{"id": "a"}, {"id": "b"}]', (), True),  # a lock that never hashed it
    ],
)
def test_the_pass_compares_what_the_lock_hashes_beyond_the_locked_files(
    tmp_path: Path, file: str, old: str, new: str, keys: tuple[str, ...], holds: bool
) -> None:
    gated = _gated_files(tmp_path, {"facts.md": "# f\n", "lock.json": _lock(*keys), file: old})
    (tmp_path / "changes" / ID / file).write_text(new)
    assert pass_proof.proves(tmp_path, "changes", gated, _commit_all(tmp_path)) is holds


def test_a_visual_app_lock_protects_screens_json_even_without_the_criteria_key(tmp_path: Path) -> None:
    lock = json.dumps({"criteria": {}, "visual": "app"})
    gated = _gated_files(tmp_path, {"facts.md": "# f\n", "lock.json": lock, "screens.json": '[{"id": "a"}]'})
    (tmp_path / "changes" / ID / "screens.json").write_text('[{"id": "b"}]')
    assert not pass_proof.proves(tmp_path, "changes", gated, _commit_all(tmp_path))


@pytest.mark.parametrize("criteria", [["screens.json"], "screens.json", 7, None])
def test_an_odd_typed_criteria_never_crashes_the_receipt_or_the_decision(tmp_path: Path, criteria: object) -> None:
    assert pass_proof.app_locked({"criteria": criteria}) is False  # not a dict: no key to find
    assert pass_proof.app_locked({"criteria": criteria, "visual": "app"}) is True
    lock = json.dumps({"criteria": criteria})
    gated = _gated_files(tmp_path, {"facts.md": "# f\n", "lock.json": lock, "screens.json": "[1]"})
    (tmp_path / "changes" / ID / "screens.json").write_text("[2]")
    assert pass_proof.proves(tmp_path, "changes", gated, _commit_all(tmp_path)) is True


@pytest.mark.parametrize("text", ["{not json", "[1, 2]", "7"])
def test_chain_gate_denies_when_the_lock_cannot_be_read_as_an_object(tmp_path: Path, text: str) -> None:
    repo = make(tmp_path)
    (repo / "changes" / ID / "lock.json").write_text(text)
    r = edit(repo, f"changes/{ID}/screens.json")
    assert r.returncode == 2 and "lock.json" in r.stderr


def test_chain_gate_survives_an_odd_typed_criteria(tmp_path: Path) -> None:
    repo = make(tmp_path)
    (repo / "changes" / ID / "lock.json").write_text(json.dumps({"layout": 4, "criteria": ["screens.json"]}))
    assert edit(repo, f"changes/{ID}/screens.json").returncode == 0


def test_chain_gate_protects_screens_json_after_an_app_approval(tmp_path: Path) -> None:
    repo = make(tmp_path)
    lock = repo / "changes" / ID / "lock.json"
    file = f"changes/{ID}/screens.json"
    assert edit(repo, file).returncode == 0  # an older lock never locked it
    lock.write_text(json.dumps({"layout": 4, "visual": "app", "criteria": {"screens.json": "x"}}))
    r = edit(repo, file)
    assert r.returncode == 2 and "protectedEdit" in r.stderr


@pytest.mark.parametrize("file", ["screens/approved.json", "screens/leads.list.empty.png"])
def test_chain_gate_protects_the_approved_screens_of_an_app_change(tmp_path: Path, file: str) -> None:
    repo = make(tmp_path)
    lock = repo / "changes" / ID / "lock.json"
    assert edit(repo, f"changes/{ID}/{file}").returncode == 0  # a change that never approved screens
    lock.write_text(json.dumps({"layout": 4, "visual": "app", "criteria": {}}))
    r = edit(repo, f"changes/{ID}/{file}")
    assert r.returncode == 2 and "protectedEdit" in r.stderr
    assert edit(repo, f"changes/{ID}/screens/some-record.json").returncode == 0  # the per-screen records stay open


ROWS = '[{"id": "a", "route": "/a", "design": ["b1"]}]'


def test_the_build_may_record_a_deviation_and_nothing_else_in_a_locked_screens_json(tmp_path: Path) -> None:
    repo = make(tmp_path)
    change = repo / "changes" / ID
    (change / "lock.json").write_text(json.dumps({"layout": 4, "visual": "app", "design": "inventory", "criteria": {}}))
    (change / "screens.json").write_text(ROWS)
    file = f"changes/{ID}/screens.json"
    note = '{"id": "a", "route": "/a", "design": ["b1"], "deviates": "no filter bar"}'
    assert edit(repo, file, old_string='{"id": "a", "route": "/a", "design": ["b1"]}', new_string=note).returncode == 2  # no design.json: locked
    (change / "design.json").write_text('{"source": "x", "boards": [{"id": "b1", "name": "B"}]}')
    assert edit(repo, file, old_string='{"id": "a", "route": "/a", "design": ["b1"]}', new_string=note).returncode == 0
    assert edit(repo, file, content=f"[{note}]").returncode == 0
    assert edit(repo, file, old_string='"/a"', new_string='"/b"').returncode == 2  # any other field stays locked
    assert edit(repo, file, old_string='["b1"]', new_string='[]').returncode == 2
    assert edit(repo, f"changes/{ID}/design.json", old_string="B", new_string="C").returncode == 2  # design.json is locked too


def _inventory_change(tmp_path: Path, design: str | None = "inventory") -> tuple[Path, str]:
    repo = make(tmp_path)
    change = repo / "changes" / ID
    lock = {"layout": 4, "visual": "app", "criteria": {}, **({"design": design} if design else {})}
    (change / "lock.json").write_text(json.dumps(lock))
    (change / "screens.json").write_text(ROWS)
    (change / "design.json").write_text('{"source": "x", "boards": [{"id": "b1", "name": "B"}]}')
    return repo, f"changes/{ID}/screens.json"


NOTE = '{"id": "a", "route": "/a", "design": ["b1"], "deviates": "no filter bar"}'
ROW = '{"id": "a", "route": "/a", "design": ["b1"]}'


@pytest.mark.parametrize(
    "tool",
    [
        {"edits": [{"old_string": '"/a"', "new_string": '"/b"'}]},  # MultiEdit: not simulated, was a no-op to the gate
        {"edits": [{"old_string": ROW, "new_string": NOTE}, {"old_string": '"/a"', "new_string": '"/b"'}]},
        {"edits": [{"old_string": ROW, "new_string": NOTE}, {"old_string": "", "new_string": "x"}]},
        {"edits": [{"old_string": ROW, "new_string": NOTE}, {"old_string": "nowhere", "new_string": "x"}]},
        {"edits": [{"old_string": ROW}]},
        {"edits": "x"},
        {"new_source": "[]"},  # a notebook-style payload
        {"old_string": "", "new_string": "[]"},
        {"old_string": "not in the file", "new_string": "x"},
        {"old_string": ROW},  # no new_string
        {"new_string": NOTE},  # no old_string
        {"content": f"[{NOTE}]", "new_source": "[]"},  # a valid deviation-only write plus a field the hook does not model
        {"old_string": ROW, "new_string": NOTE, "new_source": "[]"},
        {"old_string": ROW, "new_string": NOTE, "surprise": "x"},
        {"edits": [{"old_string": ROW, "new_string": NOTE, "surprise": "x"}]},
        {"edits": [{"old_string": ROW, "new_string": NOTE}], "surprise": "x"},
        {"content": ["list"]},
        {},
    ],
)
def test_a_payload_that_cannot_be_simulated_exactly_keeps_screens_json_locked(tmp_path: Path, tool: dict) -> None:
    repo, file = _inventory_change(tmp_path)
    assert edit(repo, file, **tool).returncode == 2


def test_an_edits_list_is_applied_in_order_and_may_only_add_deviations(tmp_path: Path) -> None:
    repo, file = _inventory_change(tmp_path)
    ok = {"edits": [{"old_string": ROW, "new_string": NOTE}, {"old_string": "no filter bar", "new_string": "fewer columns"}]}
    assert edit(repo, file, **ok).returncode == 0


def test_the_deviation_path_needs_the_lock_to_declare_the_inventory(tmp_path: Path) -> None:
    for design in (None, "other", "yes"):  # design.json exists, the lock never declared it
        repo, file = _inventory_change(tmp_path / str(design), design)
        assert edit(repo, file, old_string=ROW, new_string=NOTE).returncode == 2
    repo, file = _inventory_change(tmp_path / "ok")
    assert edit(repo, file, old_string=ROW, new_string=NOTE).returncode == 0


def test_a_deviation_edit_is_allowed_by_the_plan_lock_but_voids_the_pass(tmp_path: Path) -> None:
    lock = json.dumps({"criteria": {}, "visual": "app"})
    files = {"facts.md": "# f\n", "lock.json": lock, "screens.json": ROWS, "design.json": "{}"}
    gated = _gated_files(tmp_path, files)
    (tmp_path / "changes" / ID / "screens.json").write_text(ROWS.replace('"design"', '"deviates": "x", "design"'))
    assert not pass_proof.proves(tmp_path, "changes", gated, _commit_all(tmp_path))  # the owner has not accepted that text


def test_the_hook_and_the_gate_read_screens_json_without_its_deviations_the_same_way() -> None:
    for text in (ROWS, '{"entries": [{"id": "a", "deviates": "x", "route": "/a"}]}', "{not json", "[1]"):
        assert pass_proof.screens_core(text) == verify_gate.screens_core(text)
    assert pass_proof.screens_core('[{"id": "a", "deviates": "x"}]') == pass_proof.screens_core('[{"deviates": "y", "id": "a"}]')


def test_the_routing_fields_are_the_gates(tmp_path: Path) -> None:
    assert pass_proof.ROUTING == verify_gate.ROUTING


@pytest.mark.parametrize("name", ["Screens.json", "SCREENS.JSON", "screens/APPROVED.json", "Screens/approved.json", "Design.json"])
def test_the_locked_files_are_matched_whatever_the_capitalization(tmp_path: Path, name: str) -> None:
    repo, _ = _inventory_change(tmp_path)  # a case-insensitive volume opens the locked file under any spelling
    r = edit(repo, f"changes/{ID}/{name}", content="[]")
    assert r.returncode == 2 and "protectedEdit" in r.stderr, name


def test_a_multi_edit_cannot_change_the_layout_of_a_locked_change(tmp_path: Path) -> None:
    repo = make(tmp_path)
    file = f"changes/{ID}/decisions.json"
    text = (repo / file).read_text()
    assert edit(repo, file, edits=[{"old_string": '"layout": 4', "new_string": '"layout": 3'}]).returncode == 2
    assert edit(repo, file, edits=[{"old_string": '"size": "M"', "new_string": '"size": "M", "note": "x"'}]).returncode == 0, text
