#!/usr/bin/env python3
"""Usage: task-step.py target <plan.md> <M> [--resume]
       task-step.py start  <plan.md> <M> <T>
       task-step.py pin    <plan.md> <M> <sha>
       task-step.py finish <plan.md> <M> <T> --approved <sha>
       task-step.py gate   <plan.md> <M> --approved <sha>
       task-step.py status <plan.md> <M>
The coordinator's routine per-task mechanics, run from the milestone worktree (branch milestone/<slug>-<M>); <plan.md> is
repo-relative (changes/<slug>/plan.md). <T> is a plan task (T3) or the milestone's gap fix task (M2-gap).
  target   fetch origin and record the head of the integration (else base) branch as the target SHA; --resume records
           `git merge-base HEAD origin/<target>` instead
  start    create the task branch and worktree (`git worktree add <repo>/.worktrees/<slug>-<M>-<T>`)
           at the milestone head, run the plan's `setup` in it
  pin      record the bug flow's failing-test SHA
  finish   run test-integrity.sh for the task in its worktree, record the builder commit as a checked SHA and merge exactly that commit
  gate     the pre-PR calls: test-integrity.sh --milestone with every checked SHA, then check-plan.py --approved
  status   print the recorded state
State: <worktree>/.factory/state/<M>.json, git-ignored by a `*` .gitignore beside it (builder commit, merged head per task, checked SHAs,
target, pin). Prints one `<STEP> OK|FAIL <detail>` line per step, then the failing check's own lines; exit 1 on any FAIL.
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("check_plan", HERE / "check-plan.py")
check_plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_plan)


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def out(cwd, *args):
    p = git(cwd, *args)
    return p.stdout.strip() if p.returncode == 0 else None


def say(step, ok, detail=""):
    print(f"{step} {'OK' if ok else 'FAIL'}" + (f" {detail}" if detail else ""))
    return 0 if ok else 1


class Ctx:
    def __init__(self, plan_arg, ms):
        self.repo = Path(out(".", "rev-parse", "--show-toplevel") or ".")
        self.plan_arg, self.ms = plan_arg, ms
        self.plan_file = self.repo / plan_arg
        self.plan = json.loads(check_plan.block_text(self.plan_file.read_text(encoding="utf-8")))
        self.change = self.plan["change"]
        self.branch = f"milestone/{self.change}-{ms}"
        self.tgt = self.plan.get("integration") or self.plan["base"]
        common = out(self.repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
        self.root = Path(common).parent  # the main checkout, which holds .worktrees/
        self.state_file = self.repo / ".factory" / "state" / f"{ms}.json"

    def state(self):
        try:
            return json.loads(self.state_file.read_text())
        except (OSError, ValueError):
            return {"target": None, "pin": None, "checked": [], "tasks": {}}

    def save(self, st):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        (self.state_file.parent / ".gitignore").write_text("*\n")  # ignores itself and every state file
        self.state_file.write_text(json.dumps(st, indent=1) + "\n")

    def name(self, task):
        return f"{self.change}-{task}" if task.endswith("-gap") else f"{self.change}-{self.ms}-{task}"

    def worktree(self, task):
        return self.root / ".worktrees" / self.name(task)

    def flags(self, st, approved):
        f = ["--approved", approved, "--target", st["target"]]
        return (["--pin", st["pin"]] if st.get("pin") else []) + f


def cmd_target(c, resume):
    git(c.repo, "fetch", "-q", "origin")
    sha = out(c.repo, "merge-base", "HEAD", f"origin/{c.tgt}") if resume else out(c.repo, "rev-parse", f"origin/{c.tgt}")
    if not sha:
        return say("TARGET", False, f"cannot resolve origin/{c.tgt}")
    st = c.state()
    st["target"] = sha
    c.save(st)
    return say("TARGET", True, sha)


def cmd_start(c, task):
    if not re.fullmatch(r"T\d+|M\d+-gap", task):
        return say("START", False, f"{task} is not a task id")
    path, name = c.worktree(task), c.name(task)
    head = out(c.repo, "rev-parse", c.branch)
    if not head:
        return say("START", False, f"cannot resolve {c.branch}")
    if not path.exists():
        if out(c.repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}") is None:
            if git(c.repo, "branch", name, c.branch).returncode:
                return say("START", False, f"git branch {name} {c.branch} failed")
        made = git(c.repo, "worktree", "add", str(path), name)
        if made.returncode:
            return say("START", False, f"could not create the worktree {path}: {(made.stderr or made.stdout).strip()[:200]}")
        if out(path, "rev-parse", "HEAD") != head:
            return say("START", False, f"{path} HEAD is not the milestone head {head}")
        if c.plan.get("setup") and subprocess.run(c.plan["setup"], shell=True, cwd=path, capture_output=True).returncode:
            return say("START", False, f"setup `{c.plan['setup']}` failed in {path}")
        return say("START", True, f"{task} {path} {head}")
    return say("START", True, f"{task} {path} reused, its HEAD is {out(path, 'rev-parse', 'HEAD')}, the milestone head is {head}")


def cmd_pin(c, sha):
    if not out(c.repo, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"):
        return say("PIN", False, f"cannot resolve {sha}")
    st = c.state()
    st["pin"] = sha
    c.save(st)
    return say("PIN", True, sha)


def integrity(c, *args):
    return subprocess.run(["bash", str(HERE / "test-integrity.sh"), *args], capture_output=True, text=True)


def cmd_finish(c, task, approved):
    st = c.state()
    if not st.get("target"):
        return say("FINISH", False, "no target SHA recorded: run `target` first")
    if out(c.repo, "branch", "--show-current") != c.branch:
        return say("FINISH", False, f"run it from the milestone worktree on {c.branch}")
    wt = c.worktree(task)
    if not wt.exists():
        return say("FINISH", False, f"no worktree {wt}")
    p = integrity(c, str(wt), c.branch, c.plan_arg, "--task", task, *c.flags(st, approved))
    if p.returncode:
        say("FINISH", False, f"{task} integrity")
        print(p.stdout.strip())
        return 1
    built = out(wt, "rev-parse", "HEAD")
    m = git(c.repo, "merge", "--no-ff", "-q", "-m", f"merge {c.name(task)}", built)
    if m.returncode:
        git(c.repo, "merge", "--abort")
        return say("FINISH", False, f"{task} merge of {built} failed: {(m.stdout + m.stderr).strip()[:200]}")
    merged = out(c.repo, "rev-parse", "HEAD")
    st["checked"] = st["checked"] + [built] if built not in st["checked"] else st["checked"]
    st["tasks"][task] = {"builder": built, "merged": merged}
    c.save(st)
    return say("FINISH", True, f"{task} INTEGRITY OK builder={built} merged={merged}")


def cmd_gate(c, approved):
    st = c.state()
    if not st.get("target"):
        return say("GATE", False, "no target SHA recorded: run `target` first")
    if not st["checked"]:
        return say("GATE", False, "no task has passed `finish` yet: there is no checked SHA to gate on")
    p = integrity(c, str(c.repo), st["target"], c.plan_arg, "--milestone", c.ms, *c.flags(st, approved), "--checked", ",".join(st["checked"]))
    bad = say("GATE integrity", p.returncode == 0, "see the lines below" if p.returncode else "")
    if p.returncode:
        print(p.stdout.strip())
    q = subprocess.run([sys.executable, str(HERE / "check-plan.py"), str(c.plan_file), "--approved", approved], capture_output=True, text=True)
    bad += say("GATE check-plan", q.returncode == 0, "see the lines below" if q.returncode else "")
    if q.returncode:
        print(q.stdout.strip())
    return 1 if bad else 0


def cmd_status(c):
    st = c.state()
    merged = ",".join(f"{t}:{v['merged']}" for t, v in st["tasks"].items())
    return say("STATE", True, f"{c.ms} target={st['target']} pin={st.get('pin')} checked={','.join(st['checked'])} merged={merged}")


def main():
    a = sys.argv[1:]
    approved = None
    if "--approved" in a and a.index("--approved") == len(a) - 2:
        a, approved = a[:-2], a[-1]
    resume = "--resume" in a
    a = [x for x in a if x != "--resume"]
    n = {"target": 3, "start": 4, "pin": 4, "finish": 4, "gate": 3, "status": 3}
    if not a or a[0] not in n or len(a) != n[a[0]] or (a[0] in ("finish", "gate") and not approved):
        print("usage: task-step.py target|start|pin|finish|gate|status <plan.md> <M> [<T>|<sha>] [--approved <sha>] (see the header)", file=sys.stderr)
        return 2
    if not re.fullmatch(r"M\d+", a[2]):
        print(f"{a[2]} is not a milestone id", file=sys.stderr)
        return 2
    try:
        c = Ctx(a[1], a[2])
    except (OSError, ValueError, KeyError) as e:
        return say(a[0].upper(), False, f"cannot read the plan: {e}")
    return {"target": lambda: cmd_target(c, resume), "start": lambda: cmd_start(c, a[3]), "pin": lambda: cmd_pin(c, a[3]),
            "finish": lambda: cmd_finish(c, a[3], approved), "gate": lambda: cmd_gate(c, approved), "status": lambda: cmd_status(c)}[a[0]]()


if __name__ == "__main__":
    sys.exit(main())
