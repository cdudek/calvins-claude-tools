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
    for name in ("chain-gate.sh", "sdlc-config.sh", "goal_active.py", "block_state.py"):
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
    (c / "lock.json").write_text("{}\n")
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
