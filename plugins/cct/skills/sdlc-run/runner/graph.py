"""The milestone and task graph across repos: cycles at planning, deadlocks at run time (design 3.4).

Nodes: O:<m> open a milestone (needs the C: of every milestone it needs), T:<t> a task (needs O: of its milestone and
its task needs), C:<m> close a milestone (needs every one of its tasks). A cycle can never be satisfied.
"""
from __future__ import annotations


def build(tasks_doc: dict, extra: dict | None = None) -> dict[str, list[str]]:
    deps: dict[str, list[str]] = {}
    for m in tasks_doc.get("milestones", []):
        mid = m["id"]
        deps[f"O:{mid}"] = [f"C:{n}" for n in m.get("needs", [])]
        deps[f"C:{mid}"] = [f"O:{mid}"] + [f"T:{t['id']}" for t in m.get("tasks", [])]
        for t in m.get("tasks", []):
            deps[f"T:{t['id']}"] = [f"O:{mid}"] + [f"T:{n}" for n in t.get("needs", [])]
    for tid, t in (extra or {}).items():  # fix tasks added at run time
        deps[f"T:{tid}"] = [f"O:{t['milestone']}"] + [f"T:{n}" for n in t.get("needs", [])]
        deps[f"C:{t['milestone']}"] = deps.get(f"C:{t['milestone']}", []) + [f"T:{tid}"]
    return deps


def find_cycle(deps: dict[str, list[str]]) -> list[str] | None:
    """A cycle as a node list that starts and ends on the same node, or None."""
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(n: str):
        state[n] = 1
        stack.append(n)
        for d in deps.get(n, []):
            if state.get(d) == 1:
                return stack[stack.index(d):] + [d]
            if state.get(d) is None and d in deps and (c := visit(d)):
                return c
        stack.pop()
        state[n] = 2
        return None

    for n in list(deps):
        if state.get(n) is None and (c := visit(n)):
            return c
    return None


def unknown_refs(deps: dict[str, list[str]]) -> list[str]:
    return sorted({d for v in deps.values() for d in v if d not in deps})


def describe(cycle: list[str]) -> str:
    return "->".join(n.replace("O:", "open ").replace("C:", "close ").replace("T:", "") for n in cycle)


def ready_tasks(tasks_doc: dict, cp: dict) -> list[dict]:
    """Tasks that can start now: milestone open, task needs done, not started."""
    out = []
    ms = {m["id"]: m for m in tasks_doc.get("milestones", [])}
    allt = [(m["id"], t) for m in ms.values() for t in m.get("tasks", [])]
    allt += [(t["milestone"], {"id": k, **t}) for k, t in cp.get("extra_tasks", {}).items()]
    for mid, t in allt:
        st = cp["tasks"].get(t["id"], {}).get("status", "pending")
        mst = cp["milestones"].get(mid, {}).get("status", "waiting")
        if st != "pending" or mst != "open":
            continue
        if all(cp["tasks"].get(n, {}).get("status") == "done" for n in t.get("needs", [])):
            out.append({**t, "milestone": mid, "repo": ms[mid]["repo"]})
    return out


def pick_batch(ready: list[dict], running_paths: list[list[str]], cap: int, running: int) -> list[dict]:
    """Up to `cap` ready tasks with disjoint owned paths; a task with no declared paths owns everything."""
    def clash(a: list[str], b: list[str]) -> bool:
        if not a or not b:
            return True
        return any(x == y or x.startswith(y.rstrip("/") + "/") or y.startswith(x.rstrip("/") + "/") for x in a for y in b)

    chosen: list[dict] = []
    taken = [p for p in running_paths]
    for t in ready:
        if running + len(chosen) >= cap:
            break
        if any(clash(t.get("paths", []), p) for p in taken):
            continue
        chosen.append(t)
        taken.append(t.get("paths", []))
    return chosen


def milestone_tasks(tasks_doc: dict, cp: dict, mid: str) -> list[str]:
    m = next(m for m in tasks_doc["milestones"] if m["id"] == mid)
    return [t["id"] for t in m.get("tasks", [])] + [k for k, t in cp.get("extra_tasks", {}).items() if t["milestone"] == mid]


def openable(tasks_doc: dict, cp: dict) -> list[str]:
    return [m["id"] for m in tasks_doc.get("milestones", [])
            if cp["milestones"].get(m["id"], {}).get("status", "waiting") == "waiting"
            and all(cp["milestones"].get(n, {}).get("status") == "merged" for n in m.get("needs", []))]


def deadlock(tasks_doc: dict, cp: dict) -> str:
    """Empty string when work can progress; else why it cannot: the cycle, or what every stuck node waits on."""
    if c := find_cycle(build(tasks_doc, cp.get("extra_tasks"))):
        return "cycle " + describe(c)
    if any(t["status"] in ("running", "submitted") for t in cp["tasks"].values()):
        return ""
    stuck = [m for m in tasks_doc.get("milestones", []) if cp["milestones"].get(m["id"], {}).get("status") != "merged"]
    if not stuck:
        return ""
    if ready_tasks(tasks_doc, cp) or openable(tasks_doc, cp):
        return ""
    for m in stuck:
        st = cp["milestones"].get(m["id"], {}).get("status", "waiting")
        ts = milestone_tasks(tasks_doc, cp, m["id"])
        if st == "failing" or (st == "open" and all(cp["tasks"].get(t, {}).get("status") == "done" for t in ts)):
            return ""  # a close or a fix dispatch is the next step
    return "; ".join(f"{m['id']} waits on " + (", ".join(n for n in m.get("needs", [])
                     if cp["milestones"].get(n, {}).get("status") != "merged") or "tasks that cannot start") for m in stuck)
