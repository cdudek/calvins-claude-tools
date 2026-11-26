#!/usr/bin/env python3
"""Usage: grade.py <run dir> [--grader codex|opus|none] [--grader-model M] [--retries 3]
Grades one run the same way for every arm. The arm's own verifier never decides quality.
  1. hidden tests: the files the task's reference commit added or changed are copied from the private task dir into the
     result tree and run. FAIL_TO_PASS are the task's `fail_to_pass` files (every hidden file when task.json has no such list,
     said in grade.json `hidden_basis`); `pass_to_pass_hidden` files and the repo's existing suite must still pass. Failing
     hidden files are retried (--retries) to strip E2E flakes.
  2. prose scenarios graded by one fixed grader (default Codex gpt-6.2-astra, read-only, blind to the arm).
  hidden_frac = passing fail_to_pass files / fail_to_pass files. scenario_frac = passing scenarios / scenarios (null without any),
  never mixed into hidden_frac. regression = the suite or a pass_to_pass_hidden file fails. solved = hidden_frac 1 and no regression.
Plus metrics read from stream.jsonl and the repo. Writes grade.json next to run.json. Heavy test steps hold the
global heavy lock (see heavy.py), so parallel runs never run E2E at the same time.
"""
import argparse
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import heavy

BLOCK = re.compile(r"^```json cfactory[ \t]*\n(.*?)^```", re.S | re.M)
STATES = ("SHIPPED", "HOLD", "BLOCKED", "INCOMPLETE")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
AGENT_TOOLS = {"Agent", "Task"}
TEST_CMD = re.compile(r"\b(pytest|vitest|jest|rspec|mocha|(npm|pnpm|yarn|bun)( run)? test|go test|cargo test|make test|playwright test|bin/rspec)\b")
WEIGHT = {"in": 1.0, "out": 5.0, "cr": 0.1, "cc": 1.25}  # relative token prices, used only to split a model's cost between roles
EXCLUDED = (".cfactory/", "changes/", "specs/")
COMPONENTS = (("input_tokens", "inputTokens", "in"), ("output_tokens", "outputTokens", "out"),
              ("cache_read_input_tokens", "cacheReadInputTokens", "cr"), ("cache_creation_input_tokens", "cacheCreationInputTokens", "cc"))


def plan_json(text):
    return json.loads(BLOCK.search(text).group(1))


def read_stream(path):
    out = []
    try:
        for line in Path(path).read_text(errors="replace").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    except OSError:
        pass
    return out


def texts(content):
    if isinstance(content, str):
        return [content]
    return [b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text"]


def state_in(text):
    ms = re.findall(r"^\W*(SHIPPED|HOLD|BLOCKED|INCOMPLETE)\b", text or "", re.M)
    return ms[-1] if ms else None


def end_state(stream_path):
    """The run's last SHIPPED / HOLD / BLOCKED / INCOMPLETE line, from the result event, else the last coordinator message."""
    last = None
    for e in read_stream(stream_path):
        if e.get("type") == "result" and state_in(e.get("result")):
            return state_in(e["result"])
        if e.get("type") == "assistant" and not e.get("parent_tool_use_id") and isinstance(e.get("message"), dict):
            last = state_in("\n".join(texts(e["message"].get("content")))) or last
    return last or "none"


def subagent_role(info):
    st = (info.get("subagent_type") or "").split(":")[-1]
    if st in ("builder", "verifier", "ux-verifier"):
        return st
    if re.search(r"security|astra", f"{info.get('description', '')} {info.get('prompt', '')}"[:600], re.I):
        return "security"
    return f"other:{st}" if st else "other"


def parse_stream(events, suite_cmd=""):
    """All metrics that come from the stream alone."""
    agents, msgs, tool_uses, results = {}, {}, [], {}
    result, synthetic, texts_by_role = None, [], defaultdict(list)
    for e in events:
        t, m = e.get("type"), e.get("message")
        if t == "result":
            result = e
        if not isinstance(m, dict):
            continue
        parent = e.get("parent_tool_use_id")
        if t == "assistant":
            if m.get("model") == "<synthetic>":
                synthetic.append("\n".join(texts(m.get("content"))))
                continue
            rec = msgs.setdefault(m.get("id") or id(e), {"parent": parent, "model": m.get("model"), "usage": defaultdict(int)})
            for k, v in (m.get("usage") or {}).items():
                if isinstance(v, int):
                    rec["usage"][k] = max(rec["usage"][k], v)  # one message streams as several events with the same id
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") not in {x[3] for x in tool_uses}:
                    tool_uses.append((len(tool_uses), b.get("name"), b.get("input") or {}, b.get("id"), parent))
                    if b.get("name") in AGENT_TOOLS:
                        agents[b["id"]] = b.get("input") or {}
        elif t == "user" and isinstance(m.get("content"), list):
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = (bool(b.get("is_error")), "\n".join(texts(b.get("content"))) if isinstance(b.get("content"), list) else str(b.get("content")))

    def role_of(parent):
        return "coordinator" if not parent else subagent_role(agents.get(parent, {}))

    tokens = defaultdict(int)
    weights = defaultdict(lambda: defaultdict(float))  # model -> role -> weight
    stream_tok = defaultdict(lambda: defaultdict(int))  # model -> component -> tokens the stream's messages show
    for rec in msgs.values():
        u = rec["usage"]
        for key, _, name in COMPONENTS:
            stream_tok[rec["model"]][name] += u.get(key, 0)
            tokens[name] += u.get(key, 0)
            weights[rec["model"]][role_of(rec["parent"])] += u.get(key, 0) * WEIGHT[name]
    denom = tokens["cr"] + tokens["cc"] + tokens["in"]
    r = result or {}
    mu = r.get("modelUsage") or {}
    cost_by_model = {k: v.get("costUSD", 0.0) for k, v in mu.items()}
    cost_by_role = defaultdict(float)
    evaluator_w = 0.0
    for model, cost in cost_by_model.items():
        w = dict(weights.get(model) or {})
        if "haiku" in model.lower():
            # The goal evaluator is the configured small fast model. Its spend is in modelUsage but not in any message's usage:
            # what modelUsage holds beyond the stream's own Haiku messages is the evaluator.
            ev = sum(max(0, mu[model].get(mk, 0) - stream_tok[model][n]) * WEIGHT[n] for _, mk, n in COMPONENTS)
            total = sum(mu[model].get(mk, 0) * WEIGHT[n] for _, mk, n in COMPONENTS)
            evaluator_w += ev
            if ev > 0 and total > 0:
                cost_by_role["goal_evaluator"] += cost * ev / total
                cost -= cost * ev / total
        if not w or sum(w.values()) == 0:
            if cost > 1e-9:
                cost_by_role["unattributed"] += cost
            continue
        for role, x in w.items():
            cost_by_role[role] += cost * x / sum(w.values())
    # unverified exit: no passing test run after the last edit (or no edit at all)
    last_edit = max((i for i, n, _, _, _ in tool_uses if n in EDIT_TOOLS), default=None)
    sc = shlex.split(suite_cmd)[:2] if suite_cmd else []
    def is_test(inp):
        c = (inp or {}).get("command", "")
        return bool(TEST_CMD.search(c)) or (bool(sc) and " ".join(sc) in c)
    passing_after = last_edit is not None and any(
        n == "Bash" and i > last_edit and is_test(inp) and tid in results and not results[tid][0] for i, n, inp, tid, _ in tool_uses)
    verdicts = []
    for i, n, inp, tid, parent in tool_uses:
        if n in AGENT_TOOLS and role_of(tid) == "verifier" and tid in results:
            verdicts += re.findall(r"VERDICT:\s*(PASS|FAIL)", results[tid][1])
    state = state_in(r.get("result")) or None
    state = state or end_state_from(events)
    # goal: the stream has no verdict events. It shows "Goal set: <condition>" as a synthetic message, and the evaluator's
    # spend appears only as Haiku usage in modelUsage that no message accounts for.
    set_msgs = [s for s in synthetic if re.match(r"\s*Goal set\b", s)]
    errored = result is None or bool(r.get("is_error")) or r.get("terminal_reason") not in (None, "completed")
    completed = result is not None and r.get("terminal_reason") == "completed" and not r.get("is_error")
    sa = r.get("subagent_stats") or {}
    killed, refused = sum((sa.get("killed") or {}).values()), sum((sa.get("refused") or {}).values())
    bg = sa.get("started_in_background", 0)
    return {
        "has_result": result is not None, "cost_total": r.get("total_cost_usd", 0.0), "cost_by_model": cost_by_model,
        "cost_by_role": dict(cost_by_role), "tokens": {"input": tokens["in"], "output": tokens["out"], "cache_read": tokens["cr"], "cache_creation": tokens["cc"]},
        "cache_hit": tokens["cr"] / denom if denom else None, "coordinator_turns": r.get("num_turns"),
        "coordinator_messages": sum(1 for x in msgs.values() if not x["parent"]),
        "subagent_tool_calls": sum(1 for *_, p in tool_uses if p), "duration_s": (r.get("duration_ms") or 0) / 1000,
        "permission_denials": len(r.get("permission_denials") or []), "end_state": state or "none",
        "edits": sum(1 for _, n, *_ in tool_uses if n in EDIT_TOOLS), "unverified_exit": not passing_after,
        "verifier_verdict": verdicts[-1] if verdicts else None, "models_seen": sorted(mu),
        "terminal_reason": r.get("terminal_reason"), "errored": errored,
        "subagents_spawned": sa.get("spawned", 0), "subagents_failed": sa.get("failed", 0), "subagents_killed": killed,
        "subagents_refused": refused, "subagents_started_in_background": bg, "subagents_by_type": sa.get("by_type") or {},
        "harness_violation": bool(killed or bg),  # a killed or backgrounded subagent breaks the foreground-only rule
        "goal_set": bool(set_msgs), "goal_set_text": set_msgs[0].strip()[:300] if set_msgs else None,
        "goal_evaluated": evaluator_w > 0, "goal_evaluator_weighted_tokens": evaluator_w,
        "goal_met": bool(set_msgs) and completed and (state or "none") != "none",
        "goal_met_source": "terminal_reason completed + end state line (the stream has no evaluator verdict)",
        "goal_evaluator_models": sorted(m for m in mu if "haiku" in m.lower()), "haiku_usage": {m: mu[m] for m in mu if "haiku" in m.lower()},
        "goal_evaluator_cost": cost_by_role.get("goal_evaluator", 0.0),
    }


def end_state_from(events):
    last = None
    for e in events:
        if e.get("type") == "assistant" and not e.get("parent_tool_use_id") and isinstance(e.get("message"), dict):
            last = state_in("\n".join(texts(e["message"].get("content")))) or last
    return last


# ---------------------------------------------------------------- repo and tests

def sh(cmd, cwd, env=None, timeout=3600):
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def git(repo, *args):
    return subprocess.run([*heavy.GIT, "-C", str(repo), *args], capture_output=True, text=True).stdout


def in_scope(path, allowed):
    return any(fnmatch.fnmatch(path, a) or path == a or path.startswith(a.rstrip("/") + "/") for a in allowed)


def repo_metrics(repo, base, plan_rel, task, plugin):
    nums = [l.split("\t") for l in git(repo, "diff", "--numstat", "--no-renames", base, "HEAD").splitlines() if l]
    files = [(p, a, r) for a, r, p in nums if not p.startswith(EXCLUDED)]
    add = sum(int(a) for _, a, _ in files if a.isdigit())
    rem = sum(int(r) for *_, r in files if r.isdigit())
    ref = task.get("reference_stat") or {}
    refsize = ref.get("added", 0) + ref.get("removed", 0)
    allowed = []
    try:
        for m in plan_json((Path(repo) / plan_rel).read_text()).get("milestones", []):
            for t in m.get("tasks", []):
                allowed += t.get("files", [])
    except (OSError, AttributeError, ValueError):
        pass
    # milestone mode against the approved start commit: the plan's own allowTestEdits and coordinator paths
    # (progress log entries) are legitimate; without the plan every allowed test edit would count as a violation
    cmd = ["bash", str(Path(plugin) / "skills/run/scripts/test-integrity.sh"), str(repo), base]
    if task.get("milestone") and (Path(repo) / plan_rel).is_file():
        cmd += [plan_rel, "--milestone", task["milestone"], "--approved", base, "--target", base]  # replay repo has no integration branch
    integ = subprocess.run(cmd, capture_output=True, text=True)
    return {"diff_files": len(files), "diff_lines": add + rem, "diff_ratio": (add + rem) / refsize if refsize else None,
            "files_outside_plan": [p for p, _, _ in files if not in_scope(p, allowed)] if allowed else [],
            "integrity_violations": len(re.findall(r"INTEGRITY FAIL", integ.stdout)), "integrity_output": integ.stdout[-1500:]}


def task_env(task, run_id, db, port):
    """The variables a run (and its grading) gets besides the port and database ones: task.json `env`, templates with {db} {port} {run}."""
    out = {}
    if db and task.get("dbEnv"):
        out[task["dbEnv"]] = db
    if port and task.get("portEnv"):
        out[task["portEnv"]] = str(port)
    for name, tmpl in (task.get("env") or {}).items():
        out[name] = str(tmpl).replace("{db}", db or "").replace("{port}", str(port or "")).replace("{run}", str(run_id))
    return out


def grade_tests(repo, task, task_dir, run, retries):
    """Units: p2p:suite, p2p:hidden:<file> (passed at start), f2p:<file> (fail_to_pass; every hidden file when the task has no list).
    Runs under the heavy lock, in a fresh database and the run's port."""
    db = run.get("db")
    env = {**os.environ, "CFACTORY_EVAL": "1", **task_env(task, run.get("run_id"), db, run.get("port"))}
    timeout = task.get("e2e_timeout_s", 1800) + 600
    units = {}
    hidden = task_dir / "hidden-tests"
    with heavy.locked():
        if db and task.get("dbCreate"):
            sh(task["dbCreate"].format(db=db), repo, env)
        try:
            if task.get("suite_cmd"):
                units["p2p:suite"] = sh(task["suite_cmd"], repo, env, timeout)[0] == 0
            if hidden.is_dir():
                shutil.copytree(hidden, repo, dirs_exist_ok=True)
            tmpl = task.get("hidden_cmd") or (task.get("suite_cmd", "") + " {files}")
            hidden_files = task.get("hidden_tests", [])
            p2p = set(task.get("pass_to_pass_hidden") or [])
            f2p = set(task["fail_to_pass"]) if "fail_to_pass" in task else set(hidden_files) - p2p
            for f in hidden_files:
                cmd = tmpl.format(files=shlex.quote(f))
                key = f"f2p:{f}" if f in f2p else f"p2p:hidden:{f}"
                units[key] = any(sh(cmd, repo, env, timeout)[0] == 0 for _ in range(max(1, retries)))
        finally:
            if db and task.get("dbDrop"):
                sh(task["dbDrop"].format(db=db), repo, env)
    return units


SCENARIO_PROMPT = """You grade one behaviour scenario against the code in the current directory. You are read-only: read code and tests, and judge
from them. Do not guess: if the code does not clearly deliver the scenario's outcome, it fails.

Scenario:
{scenario}

Reply with one JSON object on the last line, nothing after it: {{"pass": true or false, "evidence": "one or two sentences naming files"}}"""


def parse_verdict(out):
    for m in reversed(re.findall(r"\{[^{}]*\"pass\"[^{}]*\}", out or "")):
        try:
            d = json.loads(m)
            return bool(d["pass"]), str(d.get("evidence", ""))
        except (ValueError, KeyError):
            continue
    return False, "grader gave no verdict"


def make_grader(kind, model):
    """Returns f(scenario_text, repo) -> (pass, evidence). The grader sees the scenario and the code, never the arm."""
    def run(scenario, repo):
        prompt = SCENARIO_PROMPT.format(scenario=scenario)
        if kind == "codex":
            cmd = ["codex", "exec", "-m", model, "-c", "model_reasoning_effort=high", "-s", "read-only", "--ephemeral", "-C", str(repo), "-"]
        else:
            cmd = ["claude", "-p", "--model", model, "--effort", "high", "--permission-mode", "dontAsk", "--allowedTools", "Read,Grep,Glob", "--output-format", "text"]
        p = subprocess.run(cmd, input=prompt, cwd=repo, capture_output=True, text=True, timeout=1800)
        return parse_verdict(p.stdout)
    return run


def grade_scenarios(repo, task_dir, grader):
    out = {}
    for f in sorted((task_dir / "scenarios").glob("*.md")) if (task_dir / "scenarios").is_dir() else []:
        ok, ev = grader(f.read_text(), repo)
        out[f"scenario:{f.stem}"] = {"pass": ok, "evidence": ev}
    return out


# ---------------------------------------------------------------- the whole run

def grade_run(run_dir, grader=None, retries=3, task_dir=None):
    run_dir = Path(run_dir)
    run = json.loads((run_dir / "run.json").read_text())
    task_dir = Path(task_dir or run["task_dir"])
    task = json.loads((task_dir / "task.json").read_text())
    events = read_stream(run_dir / "stream.jsonl")
    g = {"run_id": run["run_id"], "arm": run["arm"], "stage": run["stage"], "task_id": run["task_id"], **parse_stream(events, task.get("suite_cmd", ""))}
    g["wall_s"] = run.get("wall_s", g["duration_s"])
    expected = [m.lower() for m in run.get("expected_models", [])] + ["haiku"]  # haiku: the goal evaluator
    g["unexpected_models"] = [m for m in g["models_seen"] if not any(x in m.lower() for x in expected)]
    reasons = []
    if run.get("infra_failure"):
        reasons.append(f"infrastructure: {run['infra_failure']}")
    if not g["has_result"]:
        reasons.append("no result event in the stream")
    if not g["goal_set"]:
        reasons.append("the goal was never set")
    elif not g["goal_evaluated"]:
        if g["errored"]:
            reasons.append("infrastructure: the run errored before its first turn ended")
            g["infra_suspect"] = True
        else:
            reasons.append("the goal was never evaluated")
    g["valid"], g["invalid_reason"] = not reasons, "; ".join(reasons) or None
    if run.get("infra_failure"):
        g.update(hidden_frac=None, solved=False, skipped="infrastructure failure, rerun")
        (run_dir / "grade.json").write_text(json.dumps(g, indent=1) + "\n")
        return g
    repo = Path(run["repo"])
    g.update(repo_metrics(repo, run["base_sha"], task["plan"], task, run["plugin"]))
    units = grade_tests(repo, task, task_dir, run, retries)
    if grader:
        sc = grade_scenarios(repo, task_dir, grader)
        g["scenarios"] = sc
        units.update({k: v["pass"] for k, v in sc.items()})
    g["units"] = units
    f2p = [v for k, v in units.items() if k.startswith("f2p:")]
    g["hidden_frac"] = sum(f2p) / len(f2p) if f2p else None
    g["hidden_basis"] = "fail_to_pass" if "fail_to_pass" in task else "all hidden files (task.json has no fail_to_pass list)"
    sc = [v["pass"] for v in g.get("scenarios", {}).values()]
    g["scenario_frac"] = sum(sc) / len(sc) if sc else None
    g["visible_pass"] = units.get("p2p:suite")
    g["regression"] = units.get("p2p:suite") is False or any(v is False for k, v in units.items() if k.startswith("p2p:hidden:"))
    g["solved"] = g["hidden_frac"] == 1 and not g["regression"]
    hf = g["hidden_frac"]
    g["visible_hidden_gap"] = (1.0 if g["visible_pass"] else 0.0) - hf if hf is not None and g["visible_pass"] is not None else None
    g["verifier_false_pass"] = g["verifier_verdict"] == "PASS" and hf is not None and hf < 1
    g["goal_met_not_solved"] = bool(g["goal_met"]) and hf is not None and hf < 1
    g["claimed_done_not_solved"] = g["end_state"] in ("SHIPPED", "HOLD") and hf is not None and hf < 1
    (run_dir / "grade.json").write_text(json.dumps(g, indent=1, default=str) + "\n")
    return g


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--grader", choices=["codex", "opus", "none"], default="codex")
    ap.add_argument("--grader-model")
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--task", help="task dir, when run.json does not name it")
    a = ap.parse_args(argv)
    model = a.grader_model or ("gpt-6.2-astra" if a.grader == "codex" else "opus")
    g = grade_run(a.run_dir, None if a.grader == "none" else make_grader(a.grader, model), a.retries, a.task)
    print(f"{g['run_id']}: valid={g['valid']} hidden_frac={g.get('hidden_frac')} solved={g.get('solved')} end={g['end_state']} cost=${g['cost_total']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
