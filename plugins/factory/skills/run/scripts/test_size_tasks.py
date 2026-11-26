import copy
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "size-tasks.py"


def task(i, n, files=None):
    return {"id": i, "covers": ["req-1"], "files": files or [f"f{k}.py" for k in range(n)], "check": "pytest", "needs": []}


PLAN = {"change": "2026-11-24-x", "base": "main", "goalTurns": 12, "requirements": ["req-1"], "milestones": [
    {"id": "M1", "layer": "components", "covers": ["req-1"], "tasks": [task("T1", 3), task("T2", 2)]},
    {"id": "M2", "layer": "backend", "covers": ["req-1"], "tasks": [task("T3", 3), task("T4", 5), task("T5", 9)]},
    {"id": "M3", "layer": "screens", "covers": ["req-1"], "risky": True, "tasks": [task("T6", 1)]},
    {"id": "M4", "layer": "rest", "covers": ["req-1"], "tasks": [task("T7", 1, ["db/migrations/001.sql"])]},
    {"id": "M5", "layer": "rest", "covers": []},
]}


def write(tmp_path, plan):
    f = tmp_path / "plan.md"
    f.write_text("# Plan\n\n```json cfactory\n" + json.dumps(plan) + "\n```\n\n## Log\n")
    return f


def size(f, *a):
    return subprocess.run([sys.executable, str(SCRIPT), str(f), *a], capture_output=True, text=True)


def test_rules_and_output(tmp_path):
    p = size(write(tmp_path, PLAN))
    assert p.returncode == 0
    assert p.stdout.splitlines() == [
        "T1 files=3 risky=no -> haiku high", "T2 files=2 risky=no -> haiku high", "M1 verifier -> sonnet high",
        "T3 files=3 risky=no -> haiku high", "T4 files=5 risky=no -> sonnet medium", "T5 files=9 risky=no -> sonnet high",
        "M2 verifier -> opus high",
        "T6 files=1 risky=yes -> sonnet high", "M3 verifier -> opus high",
        "T7 files=1 risky=yes -> sonnet high", "M4 verifier -> opus high"]


def test_write_sets_fields_and_keeps_existing(tmp_path):
    plan = copy.deepcopy(PLAN)
    plan["milestones"][0]["tasks"][0].update(model="opus", effort="low")
    f = write(tmp_path, plan)
    assert size(f, "--write").returncode == 0
    text = f.read_text()
    assert text.startswith("# Plan\n") and text.endswith("```\n\n## Log\n")
    out = json.loads(text.split("```json cfactory\n")[1].split("```")[0])
    t1, t2 = out["milestones"][0]["tasks"]
    assert (t1["model"], t1["effort"]) == ("opus", "low") and (t2["model"], t2["effort"]) == ("haiku", "high")
    assert out["milestones"][0]["verifier"] == {"model": "sonnet", "effort": "high"}
    assert "verifier" not in out["milestones"][4]
    assert size(f).returncode == 0
