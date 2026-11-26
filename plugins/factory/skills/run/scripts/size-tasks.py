#!/usr/bin/env python3
"""Usage: size-tasks.py <plan.md> [--write]
Sizes every task and milestone of a plan from its own data, by the rules in SKILL.md "Models and effort".
Per task: small (<=3 files, milestone not risky, no `migrat` in a path) -> haiku high; large or risky
(>8 files, a risky milestone, or a `migrat` path) -> sonnet high; else sonnet medium. Per milestone verifier:
sonnet high when every task is small, else opus high. The only risk signal in the plan is the milestone's `risky`.
With --write the fields are set in the plan's json block in place; a field the plan already sets stays as it is.
Prints `T? files=N risky=yes|no -> model effort` per task and `M? verifier -> model effort` per milestone.
"""
import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
import importlib

cp = importlib.import_module("check-plan")


def is_small(t, risky):
    return len(t.get("files", [])) <= 3 and not risky and not migrates(t)


def migrates(t):
    return any("migrat" in f.lower() for f in t.get("files", []))


def size(t, risky):
    if is_small(t, risky):
        return "haiku", "high"
    if len(t.get("files", [])) > 8 or risky or migrates(t):
        return "sonnet", "high"
    return "sonnet", "medium"


def apply(plan, write):
    out = []
    for m in plan["milestones"]:
        risky = bool(m.get("risky"))
        for t in m.get("tasks", []):
            model, effort = size(t, risky)
            out.append(f"{t['id']} files={len(t.get('files', []))} risky={'yes' if risky or migrates(t) else 'no'} -> {model} {effort}")
            if write:
                t.setdefault("model", model)
                t.setdefault("effort", effort)
        if m.get("tasks"):
            vm = "sonnet" if all(is_small(t, risky) for t in m["tasks"]) else "opus"
            out.append(f"{m['id']} verifier -> {vm} high")
            if write:
                m.setdefault("verifier", {"model": vm, "effort": "high"})
    return out


def main():
    args = sys.argv[1:]
    write = "--write" in args
    args = [a for a in args if a != "--write"]
    if len(args) != 1:
        print("usage: size-tasks.py <plan.md> [--write]", file=sys.stderr)
        return 2
    text = open(args[0], encoding="utf-8").read()
    plan = json.loads(cp.block_text(text))
    lines = apply(plan, write)
    print("\n".join(lines))
    if write:
        m = cp.block_match(text)
        text = text[:m.start(1)] + json.dumps(plan, indent=2) + "\n" + text[m.end(1):]
        open(args[0], "w", encoding="utf-8").write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
