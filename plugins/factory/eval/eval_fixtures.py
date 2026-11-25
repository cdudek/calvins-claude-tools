"""Synthetic fixtures for the eval tests: a tiny git repo with a factory change, fake streams, fake results."""
import json
import subprocess
import sys
from pathlib import Path

SLUG = "2026-01-05-double"
PLAN = f"""# Plan: {SLUG}

## Outcome
Callers can double a number with the app. Covers the doubling rule (req-1).

## Milestones
### M1 backend: doubling
- **Result:** double(2) returns 4.

```json cfactory
{{"change": "{SLUG}", "base": "main", "goalTurns": 8, "requirements": ["req-1"],
 "milestones": [
   {{"id": "M1", "layer": "backend", "covers": ["req-1"],
    "tasks": [
      {{"id": "T1", "covers": ["req-1"], "files": ["src/app.py", "tests/test_double.py"], "check": "python3 -m pytest -q tests", "needs": []}}]}}]}}
```

## Progress log
### 2000-01-01 10:00, M1, planned
- **Next action:** build.

### 2999-01-01 10:00, M1, SHIPPED
- A later fix that must not leak into the eval.
"""
DELTA = "## ADDED\n- app/R1: When double is called with a number, the system shall return twice the number. [I1]\n"
INTENT_OLD = "# Intent\n\n## Outcome\n- I1: Callers can double a number.\n"
SOLUTION = "def double(x):\n    return 2 * x\n"
HIDDEN = "from src.app import double\n\n\ndef test_double():\n    assert double(2) == 4\n"
SUITE = f"{sys.executable} -m pytest -q -p no:cacheprovider tests"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def write(root, name, text):
    p = Path(root) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def source_repo(tmp):
    """(repo, start sha, reference sha): start has the plan with old ids; reference adds the solution and a hidden test."""
    repo = Path(tmp) / "src-repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    write(repo, "src/__init__.py", "")
    write(repo, "src/app.py", "def noop():\n    return None\n")
    write(repo, "tests/__init__.py", "")
    write(repo, "tests/test_noop.py", "from src.app import noop\n\n\ndef test_noop():\n    assert noop() is None\n")
    write(repo, f"changes/{SLUG}/plan.md", PLAN)
    write(repo, f"changes/{SLUG}/delta.md", DELTA)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "start")
    start = git(repo, "rev-parse", "HEAD")
    write(repo, "src/app.py", "def noop():\n    return None\n\n\n" + SOLUTION)
    write(repo, "tests/test_double.py", HIDDEN)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "reference")
    return repo, start, git(repo, "rev-parse", "HEAD")


def prepare(tmp, extra=()):
    """Run prepare_task on the source repo; returns (task dir, repo, start, reference)."""
    import prepare_task
    repo, start, ref = source_repo(tmp)
    scen = Path(tmp) / "scen"
    write(scen, "doubles.md", "milestone: M1\nGiven a number, the app doubles it.\n")
    out = Path(tmp) / "task"
    prepare_task.main([str(repo), "--start", start, "--reference", ref, "--task-id", "t1", "--plan", f"changes/{SLUG}/plan.md", "--out", str(out),
                       "--suite-cmd", SUITE, "--scenarios", str(scen), "--intent-from-outcome", "--port-env", "APP_PORT",
                       "--db-name", "evaldb_{run}", "--db-env", "DB_NAME", *extra])
    return out, repo, start, ref


# ---- fake streams

def asst(msg_id, model, content, parent=None, usage=None):
    return {"type": "assistant", "parent_tool_use_id": parent, "message": {"id": msg_id, "model": model, "role": "assistant", "content": content,
            "usage": usage or {"input_tokens": 10, "output_tokens": 100, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 100}}}


def tool(tid, name, inp):
    return {"type": "tool_use", "id": tid, "name": name, "input": inp}


def result_of(tid, text, err=False):
    return {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "is_error": err, "content": text}]}}


def mu(model, cost, i=10, o=100, cr=1000, cc=100):
    return {"inputTokens": i, "outputTokens": o, "cacheReadInputTokens": cr, "cacheCreationInputTokens": cc, "costUSD": cost}


def stream(goal_set=True, verdict="met", last_edit_then_test=True, state="HOLD: pushed", verdict_pass=True, error=None):
    ev = [{"type": "system", "subtype": "init"}]
    if goal_set:
        ev.append({"type": "assistant", "message": {"id": "s1", "model": "<synthetic>", "content": [{"type": "text", "text": "Goal set: Met when any one of these is true."}]}})
    ev += [
        asst("m1", "claude-sonnet-5-5", [tool("A1", "Agent", {"subagent_type": "factory:builder", "description": "build T1"})]),
        asst("b1", "claude-sonnet-5-5", [tool("E1", "Edit", {"file_path": "src/app.py"})], parent="A1"),
        asst("b1", "claude-sonnet-5-5", [tool("E1", "Edit", {"file_path": "src/app.py"})], parent="A1"),  # same message id again: counted once
        result_of("E1", "ok"),
    ]
    if last_edit_then_test:
        ev += [asst("b2", "claude-sonnet-5-5", [tool("T1", "Bash", {"command": "python3 -m pytest -q tests"})], parent="A1"), result_of("T1", "1 passed")]
    ev += [
        asst("m2", "claude-sonnet-5-5", [tool("A2", "Agent", {"subagent_type": "factory:verifier", "description": "verify"})]),
        asst("v1", "claude-opus-5-5", [tool("V1", "Bash", {"command": "ls"})], parent="A2"),
        result_of("A2", "all fine\nVERDICT: PASS" if verdict_pass else "bad\nVERDICT: FAIL"),
    ]
    if verdict:
        ev.append({"type": "assistant", "message": {"id": "s2", "model": "<synthetic>", "content": [{"type": "text", "text": f"Goal {verdict}: the condition is evaluated"}]}})
    ev.append({"type": "result", "subtype": "error_during_execution" if error else "success", "is_error": bool(error), "result": error or state,
               "terminal_reason": "completed", "num_turns": 7, "duration_ms": 120000, "total_cost_usd": 3.0, "permission_denials": [{"tool_name": "Bash"}],
               "modelUsage": {"claude-sonnet-5-5": mu("s", 1.0), "claude-opus-5-5": mu("o", 1.5), "claude-haiku-5-5": mu("h", 0.5, i=5, o=50, cr=500, cc=50)}})
    return ev


def write_stream(path, events):
    Path(path).write_text("\n".join(json.dumps(e) for e in events) + "\n")


def fake_run(root, run_id, arm, block, hidden, cost, minutes, start=0.0, stage="1", task="t1", valid=True, infra=None, verdict="PASS", cascade=None, tier=None):
    d = Path(root) / stage / run_id
    d.mkdir(parents=True)
    run = {"run_id": run_id, "stage": stage, "task_id": task, "arm": arm, "block": block, "wall_s": minutes * 60, "start_epoch": start,
           "end_epoch": start + minutes * 60, "infra_failure": infra, "timeout": False, "cascade_id": cascade, "tier": tier}
    grade = {"run_id": run_id, "arm": arm, "valid": valid, "invalid_reason": None if valid else "the goal was never set", "hidden_frac": hidden,
             "solved": hidden == 1, "cost_total": cost, "tokens": {"input": 1, "output": 2, "cache_read": 3, "cache_creation": 4}, "end_state": "HOLD",
             "verifier_verdict": verdict, "verifier_false_pass": verdict == "PASS" and hidden < 1, "goal_met": True, "goal_met_not_solved": hidden < 1,
             "cache_hit": 0.9, "cost_by_role": {"coordinator": cost * 0.2, "builder": cost * 0.3, "verifier": cost * 0.5},
             "goal_evaluator_models": ["claude-haiku-5-5"], "regression": False, "integrity_violations": 0, "unverified_exit": False}
    (d / "run.json").write_text(json.dumps(run))
    (d / "grade.json").write_text(json.dumps(grade))


def fake_results(root, repeats=2):
    """default, the eight Plackett-Burman arms and a cascade, with an effect built in: factor A (cheaper verifier) halves cost."""
    import random
    import configs
    rng = random.Random(0)
    n = 0
    arms = ["default"] + [f"pb{i}" for i in range(1, 9)]
    for b in range(1, repeats + 1):
        for a in arms:
            lv = configs.pb_levels(a)
            cost = 10 * (0.5 if lv and lv["A"] == 1 else 1) * rng.uniform(0.95, 1.05)
            fake_run(root, f"{a}-{b}", a, b, 1.0 if rng.random() > 0.2 else 0.5, cost, 30 * rng.uniform(0.9, 1.1), start=n * 100.0)
            n += 1
    fake_run(root, "c-t0", "always_cheap", 1, 0.5, 1.0, 5, stage="3", cascade="c", tier=0)
    fake_run(root, "c-t1", "default", 1, 1.0, 9.0, 30, stage="3", cascade="c", tier=1)
    fake_run(root, "bad", "pb1", 9, 1.0, 5.0, 20, valid=False)
    fake_run(root, "rl", "pb1", 9, 0.0, 0.0, 1, infra="rate-limit")
