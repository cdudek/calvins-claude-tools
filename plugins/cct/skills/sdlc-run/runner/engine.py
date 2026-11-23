"""Scheduling, worktrees, integration, milestone merges, caps, stop and resume (design 3.2, 3.4).

The orchestrating session calls these through sdlc.py; builders are subagents that only edit their worktree and commit.
Branches: sdlc/<run> (project), sdlc-m/<run>/<m> (milestone), sdlc-t/<run>/<t> (task). Git cannot hold sdlc/x and sdlc/x/y.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import contract
import graph
import store
import verify
from contract import git, wt_path
from store import SdlcError

BUILDERS = 8
ATTEMPTS = 3  # one initial build and two fix attempts per feature


def tasks_doc(rid: str) -> dict:
    return store.read_json(store.run_dir(rid) / "tasks.json")


def lim(rid: str) -> dict:
    c = store.read_json(store.run_dir(rid) / "contract.json").get("limits", {})
    a = store.read_json(store.run_dir(rid) / "approval.json", {"deadline": None}) if (store.run_dir(rid) / "approval.json").exists() else {}
    return {"builders": min(c.get("builders", BUILDERS), contract.MAX_BUILDERS), "max_dispatches": c.get("max_dispatches"), "deadline": a.get("deadline")}


def block(rid: str, kind: str, msg: str) -> SdlcError:
    text = f"{kind} {msg}"
    store.update_cp(rid, lambda cp: cp.__setitem__("blocked", text))
    store.set_status(rid, "blocked", text)
    return SdlcError(text)


def _worktree(repo: str, path: Path, branch: str, start: str) -> Path:
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    if subprocess.run(["git", "rev-parse", "--verify", "-q", f"refs/heads/{branch}"], cwd=repo, capture_output=True).returncode == 0:
        git(repo, "worktree", "add", str(path), branch)
    else:
        git(repo, "worktree", "add", "-b", branch, str(path), start)
    return path


def _recut(repo: str, path: Path, branch: str, start: str) -> None:
    """Throw the task's worktree and branch away and cut both again from `start`."""
    subprocess.run(["git", "worktree", "remove", "--force", str(path)], cwd=repo, capture_output=True)
    if path.exists():
        import shutil
        shutil.rmtree(path, ignore_errors=True)
    subprocess.run(["git", "worktree", "prune"], cwd=repo, capture_output=True)
    git(repo, "branch", "-D", branch)
    _worktree(repo, path, branch, start)


def project_wt(rid: str, repo_name: str) -> Path:
    r = store.load_meta(rid)["repos"][repo_name]
    return _worktree(r["path"], wt_path(r["path"], rid, "project"), r["branch"], r["branch"])


def milestone_branch(rid: str, mid: str) -> str:
    return f"sdlc-m/{rid}/{mid}"


def open_milestone(rid: str, mid: str) -> Path:
    doc = tasks_doc(rid)
    m = next(m for m in doc["milestones"] if m["id"] == mid)
    r = store.load_meta(rid)["repos"][m["repo"]]
    project_wt(rid, m["repo"])
    path = wt_path(r["path"], rid, f"m-{mid}")
    fresh = not path.exists()
    wt = _worktree(r["path"], path, milestone_branch(rid, mid), r["branch"])
    if fresh:
        _approved_dependencies(rid, m["repo"], wt)
        _pinned_inputs(rid, m["repo"], wt)
    store.update_cp(rid, lambda cp: cp["milestones"].setdefault(mid, {}).update(status="open", base=git(wt, "rev-parse", "HEAD")))
    return wt


def _approved_dependencies(rid: str, repo: str, wt: Path) -> None:
    """The runner, not a builder, puts the approved manifest and lockfile in and runs the frozen install."""
    import deps
    if not deps.planned(rid, repo):
        return
    deps.apply(rid, repo, wt)
    argv = deps.frozen_install(wt)
    if argv:
        job = verify.run_job(rid, f"{repo}-install", argv, wt)
        if job.exit != 0:
            raise block(rid, "BLOCKED env", f"the frozen install for {repo} failed: {job.out.strip()[-160:]}")


def _pinned_inputs(rid: str, repo: str, wt: Path) -> None:
    """The runner writes the approved config files (exact bytes, hashed in the bundle) before any task of the milestone is dispatched."""
    pins = verify.pinned_inputs(rid, repo)
    if not pins:
        return
    verify.overlay(rid, repo, wt, pins)
    if git(wt, "status", "--porcelain"):
        git(wt, "add", "--", *pins)
        git(wt, "commit", "-qm", "sdlc: approved pinned inputs", "--", *pins)


def preflight(rid: str, tid: str | None = None) -> None:
    """Before every dispatch: stop, deadline, caps, then the graph. Each refusal is durable (BLOCKED)."""
    if store.is_stopped(rid):
        raise SdlcError("STOPPED the owner stopped this run")
    ok, why = contract.approved_digest_ok(rid)
    if not ok:
        raise block(rid, "BLOCKED integrity", why)
    if why := contract.base_problem(rid):
        raise block(rid, "BLOCKED integrity", why)
    L, cp, doc = lim(rid), store.load_cp(rid), tasks_doc(rid)
    if L["deadline"] and store.now() > L["deadline"]:
        raise block(rid, "BLOCKED cap", "the run deadline has passed")
    if L["max_dispatches"] is not None and cp["dispatches"] >= L["max_dispatches"]:
        raise block(rid, "BLOCKED cap", f"dispatch cap {L['max_dispatches']} reached")
    if tid and cp["tasks"].get(tid, {}).get("attempts", 0) >= ATTEMPTS:
        raise block(rid, "BLOCKED cap", f"task {tid} used its {ATTEMPTS} attempts (one build, two fixes)")
    if why := graph.deadlock(doc, cp):
        raise block(rid, "BLOCKED deadlock", why)


def validate_plan(rid: str) -> None:
    """At planning: a cycle is a planning error the planner must fix before approval."""
    doc = tasks_doc(rid)
    deps = graph.build(doc)
    if missing := graph.unknown_refs(deps):
        raise SdlcError(f"plan error: unknown dependency {', '.join(missing)}")
    if c := graph.find_cycle(deps):
        raise SdlcError(f"plan error: cycle {graph.describe(c)} (split a task or move the shared piece earlier)")
    seen: set[str] = set()
    for m in doc.get("milestones", []):
        for t in m.get("tasks", []):
            if t["id"] in seen:
                raise SdlcError(f"plan error: duplicate task id {t['id']}")
            seen.add(t["id"])
            for g in t.get("replaces_tests", []):
                if why := replaces_problem(g, t.get("paths", [])):
                    raise SdlcError(f"plan error: task {t['id']} replaces_tests {g!r} {why}")


def replaces_problem(g, owned: list[str]) -> str:
    """A replaces_tests entry is an explicit test path or glob inside a path the task owns; anything wider is refused."""
    if not isinstance(g, str):
        return "must be a string"
    plain = g.replace("*", "x").replace("?", "x")
    if not (contract.safe_relpath(plain) and verify.TEST_PATH.search(plain)):
        return "must be a relative test path or glob (no .. or absolute path)"
    static = g.split("*")[0].split("?")[0]  # the part before the first wildcard
    if not any(static.startswith(o.rstrip("/") + "/") or g == o for o in owned if contract.safe_relpath(o.rstrip("/"))):
        return "is not inside the paths this task owns"
    return ""


def task_info(rid: str, tid: str) -> dict:
    doc, cp = tasks_doc(rid), store.load_cp(rid)
    for m in doc["milestones"]:
        for t in m.get("tasks", []):
            if t["id"] == tid:
                return {**t, "milestone": m["id"], "repo": m["repo"]}
    if tid in cp.get("extra_tasks", {}):
        x = cp["extra_tasks"][tid]
        return {"id": tid, **x, "repo": next(m["repo"] for m in doc["milestones"] if m["id"] == x["milestone"])}
    raise SdlcError(f"unknown task {tid}")


def next_batch(rid: str) -> list[dict]:
    doc, cp, L = tasks_doc(rid), store.load_cp(rid), lim(rid)
    for mid in graph.openable(doc, cp):
        open_milestone(rid, mid)
        cp = store.load_cp(rid)
    running = [t for t in cp["tasks"].values() if t["status"] in ("running", "submitted")]
    paths = [t.get("paths", []) for t in running]
    return graph.pick_batch(graph.ready_tasks(doc, cp), paths, L["builders"], len(running))


def ready_for_dispatch(rid: str, t: dict, cp: dict) -> None:
    """Readiness is decided here, at the moment of dispatch, not trusted from an earlier `next`."""
    tid, doc = t["id"], tasks_doc(rid)
    st = cp["tasks"].get(tid, {}).get("status", "pending")
    if st != "pending":
        raise SdlcError(f"task {tid} is {st}, not ready for a dispatch")
    if cp["milestones"].get(t["milestone"], {}).get("status", "waiting") == "waiting" and t["milestone"] not in graph.openable(doc, cp):
        raise SdlcError(f"milestone {t['milestone']} cannot open yet: the milestones it needs are not merged")
    waiting = [n for n in t.get("needs", []) if cp["tasks"].get(n, {}).get("status") != "done"]
    if waiting:
        raise SdlcError(f"task {tid} waits on {', '.join(waiting)}")
    running = [x for x in cp["tasks"].values() if x["status"] in ("running", "submitted")]
    if len(running) >= lim(rid)["builders"]:
        raise SdlcError(f"builders are at their cap of {lim(rid)['builders']}")
    if graph.pick_batch([t], [x.get("paths", []) for x in running], 10**6, 0) == []:
        raise SdlcError(f"task {tid} owns paths a running task owns; it runs after that one")


def dispatch(rid: str, tid: str) -> dict:
    """Count the dispatch durably, then cut the worktree at the milestone's integration SHA and write the brief."""
    preflight(rid, tid)
    t = task_info(rid, tid)
    cp = store.load_cp(rid)
    ready_for_dispatch(rid, t, cp)
    if cp["milestones"].get(t["milestone"], {}).get("status") not in ("open", "failing"):
        open_milestone(rid, t["milestone"])
    r = store.load_meta(rid)["repos"][t["repo"]]
    mwt = wt_path(r["path"], rid, f"m-{t['milestone']}")
    base = git(mwt, "rev-parse", "HEAD")

    def count(cp):  # before launch: a crash right after still counts
        cp["dispatches"] += 1
        e = cp["tasks"].setdefault(tid, {"attempts": 0, "paths": t.get("paths", [])})
        e.update(status="running", attempts=e["attempts"] + 1, base=base, milestone=t["milestone"], repo=t["repo"], paths=t.get("paths", []))
    store.update_cp(rid, count)
    branch = f"sdlc-t/{rid}/{tid}"
    path = wt_path(r["path"], rid, f"t-{tid}")
    fresh = not path.exists()
    _worktree(r["path"], path, branch, base)
    if not fresh:  # a fix attempt continues the same work on top of the current milestone head
        if subprocess.run(["git", "merge", "--no-edit", base], cwd=path, capture_output=True).returncode:
            subprocess.run(["git", "merge", "--abort"], cwd=path, capture_output=True)
            _recut(r["path"], path, branch, base)  # the old work conflicts with the new head: redo it there, the attempt stays counted
            store.log(rid, f"recut {tid} from {base[:9]}: its old work conflicted with the milestone head")
            fresh = True
    if git(path, "rev-parse", "HEAD") != base and fresh:
        raise block(rid, "BLOCKED integrity", f"worktree of {tid} is not at the integration SHA")
    items = [c for c in store.read_json(store.run_dir(rid) / "contract.json")["checks"] if c.get("task") == tid]
    d = store.briefs_dir(rid) / tid
    d.mkdir(parents=True, exist_ok=True)
    brief = (f"# Task {tid}: {t.get('title', '')}\n\n{t.get('desc', '')}\n\n"
             f"- Worktree (work only here, absolute path): {path}\n- Base: {base}\n- Branch: {branch}\n"
             f"- Paths you own: {', '.join(t.get('paths', [])) or 'declared by the task'}\n"
             f"- Attempt: {store.load_cp(rid)['tasks'][tid]['attempts']} of {ATTEMPTS}\n\n"
             "Rules: commit your work in the worktree and report the commit SHA. Do not edit pinned tests or fixtures, test or CI "
             "configuration, or anything under ~/.sdlc. The result is graded by the runner's verifier, not by what you say.\n\n"
             "Checks that will run on your commit:\n" + "\n".join(f"- {c['id']}: {' '.join(c['runner'])}" for c in items) + "\n")
    store.atomic_write(d / "brief.md", brief)
    store.log(rid, f"dispatch {tid} attempt {store.load_cp(rid)['tasks'][tid]['attempts']} base {base[:9]}")
    return {"task": tid, "worktree": str(path), "branch": branch, "base": base, "brief": str(d / "brief.md")}


def submit(rid: str, tid: str) -> dict:
    """The builder returned a commit: check the tree, compare the diff against the base for tampering, record the candidate."""
    e = store.load_cp(rid)["tasks"].get(tid)
    if not e:
        raise SdlcError(f"task {tid} was never dispatched")
    r = store.load_meta(rid)["repos"][e["repo"]]
    path = wt_path(r["path"], rid, f"t-{tid}")
    if git(path, "status", "--porcelain"):
        raise SdlcError(f"task {tid}: uncommitted changes in the worktree; commit them")
    cand = git(path, "rev-parse", "HEAD")
    if cand == e["base"]:
        raise SdlcError(f"task {tid}: no commit was made")
    bad = verify.guard_diff(rid, e["repo"], e["base"], cand, tid)
    owned = e.get("paths") or []
    if owned:
        for rel in git(path, "diff", "--no-renames", "--name-only", f"{e['base']}..{cand}").splitlines():
            if not any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in owned):
                bad.append(f"changed {rel}, outside the paths this task owns")
    if bad:  # back to pending: the attempt stays counted and the next dispatch is a fix
        store.update_cp(rid, lambda cp: cp["tasks"][tid].update(status="pending", reason="; ".join(bad)))
        store.log(rid, f"reject {tid}: {'; '.join(bad)}")
        raise SdlcError(f"BLOCKED test-path {tid}: " + "; ".join(bad))
    store.update_cp(rid, lambda cp: cp["tasks"][tid].update(status="submitted", sha=cand))
    return {"task": tid, "candidate": cand}


def verify_task(rid: str, tid: str) -> list[dict]:
    """The independent verifier: the task's contract items run on a clean checkout of the candidate."""
    e = store.load_cp(rid)["tasks"][tid]
    cand = e["sha"]
    out = []
    for c in store.read_json(store.run_dir(rid) / "contract.json")["checks"]:
        if c.get("task") == tid:
            out.append(verify.verify_check(rid, c, ref=cand, base_sha=e["base"]))
    ok = all(b["verdict"] == "PASS" for b in out)
    store.update_cp(rid, lambda cp: cp["tasks"][tid].update(verified=cand if ok else None, **({} if ok else {"status": "pending"})))
    return out


def integrate(rid: str, tid: str) -> str:
    """Merge a verified candidate into its milestone branch; a conflict puts the task back for a rerun on the new head."""
    if store.is_stopped(rid):
        raise SdlcError("STOPPED the owner stopped this run")
    e = store.load_cp(rid)["tasks"][tid]
    if e.get("status") != "submitted" or e.get("verified") != e.get("sha"):
        raise SdlcError(f"task {tid} has no passing verifier result for {str(e.get('sha'))[:9]}")
    r = store.load_meta(rid)["repos"][e["repo"]]
    mwt = wt_path(r["path"], rid, f"m-{e['milestone']}")
    p = subprocess.run(["git", "merge", "--no-ff", "-m", f"sdlc: task {tid}", e["sha"]], cwd=mwt, capture_output=True, text=True)
    if p.returncode:
        subprocess.run(["git", "merge", "--abort"], cwd=mwt, capture_output=True)
        store.update_cp(rid, lambda cp: cp["tasks"][tid].update(status="pending", verified=None))
        raise SdlcError(f"overlap: task {tid} conflicts with the integrated head; it reruns on the new head")
    head = git(mwt, "rev-parse", "HEAD")
    store.update_cp(rid, lambda cp: cp["tasks"][tid].update(status="done", merged=head))
    store.log(rid, f"integrated {tid} into {e['milestone']} at {head[:9]}")
    return head


def add_fix_task(rid: str, tid: str, milestone: str, paths: list[str] | None = None) -> None:
    store.update_cp(rid, lambda cp: cp.setdefault("extra_tasks", {}).__setitem__(tid, {"milestone": milestone, "needs": [], "paths": paths or []}))


def close_milestone(rid: str, mid: str) -> dict:
    """Run the milestone's due contract items and the full gate on the integrated head; pass merges it into the project branch."""
    if store.is_stopped(rid):
        raise SdlcError("STOPPED the owner stopped this run")
    doc, cp = tasks_doc(rid), store.load_cp(rid)
    m = next(m for m in doc["milestones"] if m["id"] == mid)
    pending = [t for t in graph.milestone_tasks(doc, cp, mid) if cp["tasks"].get(t, {}).get("status") != "done"]
    if pending:
        raise SdlcError(f"milestone {mid} has unfinished tasks: {', '.join(pending)}")
    r = store.load_meta(rid)["repos"][m["repo"]]
    branch = milestone_branch(rid, mid)
    results = []
    for c in store.read_json(store.run_dir(rid) / "contract.json")["checks"]:
        if c["repo"] == m["repo"] and (c.get("milestone") == mid or c.get("due") == "each"):
            results.append(verify.verify_check(rid, c, ref=branch))
    bad = [b for b in results if b["verdict"] != "PASS"]
    if bad:
        st = "blocked" if any(b["verdict"] == "BLOCKED" for b in bad) else "failing"
        store.update_cp(rid, lambda cp: cp["milestones"][mid].update(status=st))
        return {"milestone": mid, "status": st, "failed": [f"{b['check']}: {b['reason']}" for b in bad]}
    pwt = project_wt(rid, m["repo"])
    p = subprocess.run(["git", "merge", "--no-ff", "-m", f"sdlc: milestone {mid}", branch], cwd=pwt, capture_output=True, text=True)
    if p.returncode:
        subprocess.run(["git", "merge", "--abort"], cwd=pwt, capture_output=True)
        raise block(rid, "BLOCKED integrity", f"milestone {mid} does not merge into the project branch: {p.stdout[-200:]}")
    head = git(pwt, "rev-parse", "HEAD")
    store.update_cp(rid, lambda cp: cp["milestones"][mid].update(status="merged", merge=head))
    store.log(rid, f"milestone {mid} merged into {r['branch']} at {head[:9]}")
    return {"milestone": mid, "status": "merged", "head": head}


def final_verify(rid: str) -> list[dict]:
    """The whole contract on the final heads: receipts for every item bound to the project branch."""
    doc, cp = tasks_doc(rid), store.load_cp(rid)
    open_ms = [m["id"] for m in doc["milestones"] if cp["milestones"].get(m["id"], {}).get("status") != "merged"]
    if open_ms:
        raise SdlcError(f"milestones not merged yet: {', '.join(open_ms)}")
    res = [verify.verify_check(rid, c) for c in store.read_json(store.run_dir(rid) / "contract.json")["checks"]]
    contract.seal_final(rid)  # the whole contract just ran on the frozen heads: READY needs exactly these receipts
    return res


# ---- stop and resume ------------------------------------------------------------------------------

def stop(rid: str) -> list[int]:
    """Durably mark the run stopped, then cancel every live job process group. Branches and records stay."""
    store.stop_marker(rid).write_text(store.iso())
    store.set_status(rid, "stopped", "owner stop")
    killed = []
    for pf in (store.run_dir(rid) / "jobs").glob("*.pid"):
        if (pid := verify.kill_recorded(pf)) is not None:
            killed.append(pid)
    return killed


def restart(rid: str) -> None:
    """Only an explicit owner restart clears a stop; the original caps and deadline stay."""
    if not contract.granted("restart", rid):
        raise SdlcError("only the owner restarts a stopped run (run `sdlc gate <id> restart`)")
    store.stop_marker(rid).unlink(missing_ok=True)
    store.update_cp(rid, lambda cp: cp.pop("blocked", None))
    store.set_status(rid, "approved", "restarted by the owner")


def external(rid: str, key: str, sha: str, do, done_check) -> str:
    """Run one remote write at most once: record intent, do it, record done. After a crash done_check decides."""
    cp = store.load_cp(rid)
    e = cp["external"].get(key)
    if e and e.get("state") == "done" and e.get("sha") == sha:
        return "already-done"
    if e and e.get("state") == "started" and e.get("sha") == sha and done_check():
        store.update_cp(rid, lambda c: c["external"][key].update(state="done"))
        return "reconciled"
    store.update_cp(rid, lambda c: c["external"].__setitem__(key, {"state": "started", "sha": sha}))
    do()
    store.update_cp(rid, lambda c: c["external"][key].update(state="done"))
    return "done"


def push(rid: str, repo: str) -> str:
    meta = store.load_meta(rid)
    r = meta["repos"][repo]
    if store.is_stopped(rid):
        raise SdlcError("STOPPED the owner stopped this run")
    sha = git(r["path"], "rev-parse", r["branch"])

    def do():
        git(r["path"], "push", "origin", f"{r['branch']}:{r['branch']}")

    def done():
        p = subprocess.run(["git", "ls-remote", "origin", f"refs/heads/{r['branch']}"], cwd=r["path"], capture_output=True, text=True)
        return p.stdout.split()[:1] == [sha]
    return external(rid, f"push:{repo}", sha, do, done)


def resume(rid: str) -> dict:
    """Continue on the same machine: keep counters, reconcile what ran, put interrupted work back, name the next step."""
    if store.is_stopped(rid):
        raise SdlcError("STOPPED the run was stopped; `sdlc gate <id> restart` clears it")
    ok, why = contract.approved_digest_ok(rid)
    if not ok:
        raise SdlcError(f"BLOCKED integrity {why}")
    meta, cp = store.load_meta(rid), store.load_cp(rid)
    for repo, r in meta["repos"].items():  # recorded heads must still exist
        try:
            git(r["path"], "rev-parse", "--verify", r["branch"])
        except SdlcError as e:
            raise SdlcError(f"BLOCKED integrity branch of {repo} is gone: {e}") from None
    for pf in (store.run_dir(rid) / "jobs").glob("*.pid"):  # a job that survived the crash is cancelled, then runs again
        verify.kill_recorded(pf)  # only if the PID still is the job we started
        pf.unlink(missing_ok=True)

    def requeue(cp):
        for e in cp["tasks"].values():
            if e["status"] == "running":
                e["status"] = "pending"  # the attempt stays counted: it was durable before launch
    store.update_cp(rid, requeue)
    store.set_status(rid, "approved" if meta["status"] != "done" else "done", "resumed")
    cp = store.load_cp(rid)
    return {"done": [t for t, e in cp["tasks"].items() if e["status"] == "done"],
            "requeued": [t for t, e in cp["tasks"].items() if e["status"] == "pending"],
            "merged": [m for m, e in cp["milestones"].items() if e["status"] == "merged"],
            "external": {k: v["state"] for k, v in cp["external"].items()},
            "dispatches": cp["dispatches"], "next": [t["id"] for t in next_batch(rid)]}


def finish(rid: str) -> str:
    """The run ends: every proof is current and (when PRs exist) their checks are green; the active link is removed."""
    code, first, _ = contract.evaluate(rid)
    if code != contract.READY:
        raise SdlcError(f"not finished: {first}")
    store.set_status(rid, "done", "all proof present")
    return "done"


def pr_guard(rid: str, repo: str, arming: bool = False) -> None:
    """A PR (and its auto-merge) only for a repo whose own proof is READY; a consumer waits for its producer's release.
    Arming auto-merge also needs the PR head to be the proven head and required CI (or approved local-only proof)."""
    code, first, _ = contract.evaluate(rid, skip_ci=True, repo=repo)
    if code != contract.READY:
        raise SdlcError(f"not ready for a PR of {repo}: {first}")
    if arming:
        import ci
        if why := ci.auto_merge_problem(rid, repo):
            raise SdlcError(f"not arming auto-merge: {why}")
