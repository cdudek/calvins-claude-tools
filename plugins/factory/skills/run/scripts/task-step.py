#!/usr/bin/env python3
"""Usage: task-step.py target <plan.md> <M> --approved <sha> [--resume]
       task-step.py start  <plan.md> <M> <T> --approved <sha>
       task-step.py pin    <plan.md> <M> <sha> --approved <sha>
       task-step.py finish <plan.md> <M> <T> --approved <sha>
       task-step.py gate   <plan.md> <M> --approved <sha>
       task-step.py status <plan.md> <M> --approved <sha>
The coordinator's routine per-task mechanics, run from the milestone worktree (branch milestone/<slug>-<M>); <plan.md> is
repo-relative (changes/<slug>/plan.md), never absolute and never outside the repo. <T> is a plan task (T3) or the milestone's
gap fix task (M2-gap). The plan, and so `change`, the target branch and `setup`, is read from the approved commit, never from the working file.
  target   fetch origin and record the head of the integration (else base) branch as the target SHA; --resume records
           `git merge-base HEAD origin/<target>` instead
  start    create the task branch and worktree (`git worktree add <repo>/.worktrees/<slug>-<M>-<T>`) at the milestone head, run the
           approved plan's `setup` in it
  pin      record the bug flow's failing-test SHA
  finish   run test-integrity.sh for the task in its worktree and merge exactly the checked commit (message `factory-merge: <name>`)
  gate     the pre-PR calls: test-integrity.sh --milestone with the checked commits, then check-plan.py --approved
  status   print the recorded state
The checked commits are never taken from the state file: `gate` derives them from git, as the second parents of the `factory-merge:` merges on the
milestone branch's first-parent chain since the target. The state file (<worktree>/.factory/state/<M>.json, git-ignored by a `*` .gitignore beside it)
is a convenience log. Prints one `<STEP> OK|FAIL <detail>` line per step, then the failing check's own lines; exit 1 on any FAIL.
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

MERGE_PREFIX = "factory-merge: "
TASK_ID = r"T\d+|M\d+[a-z]?-gap"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def out(cwd, *args):
    p = git(cwd, *args)
    return p.stdout.strip() if p.returncode == 0 else None


def say(step, ok, detail=""):
    print(f"{step} {'OK' if ok else 'FAIL'}" + (f" {detail}" if detail else ""))
    return 0 if ok else 1


class Abort(Exception):
    pass


def valid_ref(repo, name):
    return isinstance(name, str) and name != "" and not name.startswith("-") and git(repo, "check-ref-format", "--branch", name).returncode == 0


class Ctx:
    def __init__(self, plan_arg, ms, approved):
        top = out(".", "rev-parse", "--show-toplevel")
        if not top:
            raise Abort("not inside a git repo")
        self.repo = Path(top)
        if not re.fullmatch(check_plan.MS_ID, ms):
            raise Abort(f"{ms!r} is not a milestone id")
        real = os.path.realpath(self.repo)
        if os.path.isabs(plan_arg) or ".." in Path(plan_arg).parts or not os.path.realpath(self.repo / plan_arg).startswith(real + os.sep):
            raise Abort("the plan path must be repo-relative and inside the repo")
        if not out(self.repo, "rev-parse", "--verify", "--quiet", f"{approved}^{{commit}}") or git(self.repo, "merge-base", "--is-ancestor", approved, "HEAD").returncode:
            raise Abort(f"approved {approved} is not a commit that is an ancestor of HEAD")
        text = git(self.repo, "show", f"{approved}:{plan_arg}")
        if text.returncode:
            raise Abort(f"{plan_arg} does not exist at approved {approved}")
        self.plan_arg, self.ms, self.approved = plan_arg, ms, approved
        self.plan_file = self.repo / plan_arg
        self.plan = json.loads(check_plan.block_text(text.stdout))  # the owner-approved plan, not the working file
        self.change = self.plan.get("change", "")
        if not re.fullmatch(check_plan.SLUG, str(self.change)):
            raise Abort("the approved plan's change is not a dated slug")
        self.branch = f"milestone/{self.change}-{ms}"
        self.tgt = self.plan.get("integration") or self.plan.get("base")
        if not valid_ref(self.repo, self.tgt) or not valid_ref(self.repo, self.branch):
            raise Abort("the approved plan's base or integration is not a valid branch name")
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
        path = self.root / ".worktrees" / self.name(task)
        base = os.path.realpath(self.root / ".worktrees")
        if not os.path.realpath(path).startswith(base + os.sep):
            raise Abort(f"{path} is not under {base}")
        return path

    def target_ok(self, sha):
        """The recorded target must be a commit of origin's target branch that the milestone branch descends from."""
        if not sha or not re.fullmatch(r"[0-9a-f]{40}", sha):
            return False
        git(self.repo, "fetch", "-q", "--", "origin")
        return (git(self.repo, "merge-base", "--is-ancestor", sha, f"refs/remotes/origin/{self.tgt}").returncode == 0
                and git(self.repo, "merge-base", "--is-ancestor", sha, "HEAD").returncode == 0)

    def checked(self, target):
        """The commits `finish` merged: second parents of `factory-merge:` merges on the first-parent chain from HEAD down to the target."""
        log = out(self.repo, "rev-list", "--first-parent", "--parents", "--format=%s", "HEAD", f"^{target}")
        found, lines = [], (log or "").split("\n")
        for i in range(0, len(lines) - 1, 2):
            shas, subject = lines[i].replace("commit ", "").split(), lines[i + 1]
            if len(shas) == 3 and subject.startswith(MERGE_PREFIX):
                found.append(shas[2])
        return list(reversed(found))

    def flags(self, st):
        f = ["--approved", self.approved, "--target", st["target"]]
        return (["--pin", st["pin"]] if st.get("pin") else []) + f


def cmd_target(c, resume):
    git(c.repo, "fetch", "-q", "--", "origin")
    ref = f"refs/remotes/origin/{c.tgt}"
    sha = out(c.repo, "merge-base", "HEAD", ref) if resume else out(c.repo, "rev-parse", "--verify", ref)
    if not sha:
        return say("TARGET", False, f"cannot resolve origin/{c.tgt}")
    st = c.state()
    st["target"] = sha
    c.save(st)
    return say("TARGET", True, sha)


def cmd_start(c, task):
    path, name = c.worktree(task), c.name(task)
    head = out(c.repo, "rev-parse", "--verify", f"refs/heads/{c.branch}")
    if not head:
        return say("START", False, f"cannot resolve {c.branch}")
    if not path.exists():
        if out(c.repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}") is None:
            if git(c.repo, "branch", "--", name, head).returncode:
                return say("START", False, f"git branch {name} failed")
        made = git(c.repo, "worktree", "add", "--", str(path), name)
        if made.returncode:
            return say("START", False, f"could not create the worktree {path}: {(made.stderr or made.stdout).strip()[:200]}")
        if out(path, "rev-parse", "HEAD") != head:
            return say("START", False, f"{path} HEAD is not the milestone head {head}")
        # `setup` comes from the owner-approved plan commit (read in Ctx), so running it through the shell, which its env and pipes need, adds no new trust.
        if c.plan.get("setup") and subprocess.run(str(c.plan["setup"]), shell=True, cwd=path, capture_output=True).returncode:
            return say("START", False, f"setup `{c.plan['setup']}` failed in {path}")
        return say("START", True, f"{task} {path} {head}")
    return say("START", True, f"{task} {path} reused, its HEAD is {out(path, 'rev-parse', 'HEAD')}, the milestone head is {head}")


def cmd_pin(c, sha):
    if not re.fullmatch(r"[0-9a-f]{7,40}", sha) or not out(c.repo, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"):
        return say("PIN", False, f"cannot resolve {sha}")
    st = c.state()
    st["pin"] = sha
    c.save(st)
    return say("PIN", True, sha)


def integrity(*args):
    return subprocess.run(["bash", str(HERE / "test-integrity.sh"), *args], capture_output=True, text=True)


def cmd_finish(c, task):
    st = c.state()
    if not c.target_ok(st.get("target")):
        return say("FINISH", False, "no valid target SHA recorded (it must be on origin's target branch and under HEAD): run `target` first")
    if out(c.repo, "branch", "--show-current") != c.branch:
        return say("FINISH", False, f"run it from the milestone worktree on {c.branch}")
    wt = c.worktree(task)
    if not wt.exists():
        return say("FINISH", False, f"no worktree {wt}")
    p = integrity(str(wt), c.branch, c.plan_arg, "--task", task, *c.flags(st))
    if p.returncode:
        say("FINISH", False, f"{task} integrity")
        print(p.stdout.strip())
        return 1
    built = out(wt, "rev-parse", "HEAD")
    m = git(c.repo, "merge", "--no-ff", "-q", "-m", f"{MERGE_PREFIX}{c.name(task)}", built)
    if m.returncode:
        git(c.repo, "merge", "--abort")
        return say("FINISH", False, f"{task} merge of {built} failed: {(m.stdout + m.stderr).strip()[:200]}")
    merged = out(c.repo, "rev-parse", "HEAD")
    st["checked"] = st["checked"] + [built] if built not in st["checked"] else st["checked"]
    st["tasks"][task] = {"builder": built, "merged": merged}
    c.save(st)
    return say("FINISH", True, f"{task} INTEGRITY OK builder={built} merged={merged}")


def cmd_gate(c):
    st = c.state()
    if not c.target_ok(st.get("target")):
        return say("GATE", False, "no valid target SHA recorded (it must be on origin's target branch and under HEAD): run `target` first")
    checked = c.checked(st["target"])
    if not checked:
        return say("GATE", False, "no task has passed `finish` yet: git shows no factory-merge commit on the milestone branch")
    p = integrity(str(c.repo), st["target"], c.plan_arg, "--milestone", c.ms, *c.flags(st), "--checked", ",".join(checked))
    bad = say("GATE integrity", p.returncode == 0, "see the lines below" if p.returncode else "")
    if p.returncode:
        print(p.stdout.strip())
    q = subprocess.run([sys.executable, str(HERE / "check-plan.py"), str(c.plan_file), "--approved", c.approved], capture_output=True, text=True)
    bad += say("GATE check-plan", q.returncode == 0, "see the lines below" if q.returncode else "")
    if q.returncode:
        print(q.stdout.strip())
    return 1 if bad else 0


def cmd_status(c):
    st = c.state()
    merged = ",".join(f"{t}:{v['merged']}" for t, v in st["tasks"].items())
    derived = ",".join(c.checked(st["target"])) if c.target_ok(st.get("target")) else ""
    return say("STATE", True, f"{c.ms} target={st['target']} pin={st.get('pin')} checked={derived} merged={merged}")


def main():
    a = sys.argv[1:]
    approved = None
    if "--approved" in a and a.index("--approved") == len(a) - 2:
        a, approved = a[:-2], a[-1]
    resume = "--resume" in a
    a = [x for x in a if x != "--resume"]
    n = {"target": 3, "start": 4, "pin": 4, "finish": 4, "gate": 3, "status": 3}
    if not a or a[0] not in n or len(a) != n[a[0]] or not approved or not re.fullmatch(r"[0-9a-f]{7,40}", approved):
        print("usage: task-step.py target|start|pin|finish|gate|status <plan.md> <M> [<T>|<sha>] --approved <sha> (see the header)", file=sys.stderr)
        return 2
    if a[0] in ("start", "finish") and not re.fullmatch(TASK_ID, a[3]):
        print(f"{a[3]!r} is not a task id (T<n> or M<n>-gap)", file=sys.stderr)
        return 2
    try:
        c = Ctx(a[1], a[2], approved)
        return {"target": lambda: cmd_target(c, resume), "start": lambda: cmd_start(c, a[3]), "pin": lambda: cmd_pin(c, a[3]),
                "finish": lambda: cmd_finish(c, a[3]), "gate": lambda: cmd_gate(c), "status": lambda: cmd_status(c)}[a[0]]()
    except Abort as e:
        return say(a[0].upper(), False, str(e))
    except (OSError, ValueError, KeyError) as e:
        return say(a[0].upper(), False, f"cannot read the approved plan: {e}")


if __name__ == "__main__":
    sys.exit(main())
