#!/usr/bin/env python3
"""sdlc: the runner CLI (sdlc-run 4.x). Plain stdlib. Records live in ~/.sdlc/runs/<run-id>/, never in a repo.

  plan <repo>... --slug S [--title T]   discover, probe, write plan/contract drafts and the approval screen
  gate <id> [approve|restart] --by NAME   the owner's gate: Plannotator, and only on "approved" the approval (or restart), in one process
  check [<id>]                          read-only completion test: exit 0 READY, 1 FAIL, 2 BLOCKED/STOPPED, 3 PENDING
  status [<id>] | list                  where a run stands; live runs
  resume <id>                           continue after a crash, on the same machine
  stop <id>                             durably stop a run and cancel its jobs
  boards index <export-dir> | boards rows <mapping> --index F   design-canvas boards: list nodes with measured style, make check rows
  dispatch|submit|integrate|verify|milestone|final|pr|clean ...   see sdlc.py <cmd> -h
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract  # noqa: E402
import store  # noqa: E402
from store import SdlcError  # noqa: E402


def cmd_check(a) -> int:
    rid = store.resolve_run(a.run)
    code, first, _ = contract.evaluate(rid, a.due)
    print(contract.status_line(rid, code, first))
    if store.read_json(store.run_dir(rid) / "contract.json").get("spec"):
        print("\n".join(contract.spec_report(rid, not contract.final_problem(rid, store.load_meta(rid)) if a.due is None else False)))
    return code


def cmd_list(a) -> int:
    act = store.home() / "active"
    for p in sorted(act.iterdir()) if act.exists() else []:
        m = store.load_meta(p.name)
        print(f"{p.name}  {m['status']}")
    return 0


def cmd_status(a) -> int:
    rid = store.resolve_run(a.run, Path.cwd())
    m, cp = store.load_meta(rid), store.load_cp(rid)
    print(json.dumps({"run": rid, "status": m["status"], "repos": list(m["repos"]), "prs": m.get("prs", {}),
                      "dispatches": cp["dispatches"], "tasks": {k: v["status"] for k, v in cp["tasks"].items()},
                      "milestones": {k: v["status"] for k, v in cp["milestones"].items()}}, indent=1))
    return 0


def _j(o) -> None:
    print(json.dumps(o, indent=1, sort_keys=True))


def cmd_plan(a) -> int:
    import discover
    rid = discover.plan(a.repos, a.slug, a.title)
    print(rid)
    return 0


def cmd_draft(a) -> int:
    import discover
    blockers = discover.draft(a.run, a.plan, a.contract, a.tasks, a.input, a.dep)
    for b in blockers:
        print(f"OPEN BLOCKER {b}")
    return 2 if blockers and a.strict else 0


def cmd_screen(a) -> int:
    import discover
    p = discover.screen(a.run)
    print(p)
    print(f"plannotator annotate {p} --gate")
    return 0


def cmd_gate(a) -> int:
    import discover
    ok = discover.gate(a.run, a.purpose, a.by or "")
    print(f"GATE approved: {'RESTARTED' if a.purpose == 'restart' else 'APPROVED'} {a.run}" if ok else "GATE not approved")
    return 0 if ok else 2


def cmd_done(a) -> int:
    import engine
    print(engine.finish(a.run))
    return 0


def cmd_resume(a) -> int:
    import engine
    _j(engine.resume(a.run))
    return 0


def cmd_stop(a) -> int:
    import engine
    print(f"STOPPED {a.run} jobs_cancelled={engine.stop(a.run)}")
    return 0


def cmd_next(a) -> int:
    import engine
    _j([t["id"] for t in engine.next_batch(a.run)])
    return 0


def cmd_dispatch(a) -> int:
    import engine
    _j([engine.dispatch(a.run, t) for t in a.tasks])
    return 0


def cmd_submit(a) -> int:
    import engine
    _j(engine.submit(a.run, a.task))
    return 0


def cmd_verify(a) -> int:
    import engine
    import verify
    if a.task:
        res = engine.verify_task(a.run, a.task)
    else:
        c = store.read_json(store.run_dir(a.run) / "contract.json")
        res = [verify.verify_check(a.run, k) for k in c["checks"]
               if (not a.check or k["id"] == a.check) and (not a.repo or k["repo"] == a.repo)]  # --repo: a producer mid-run, before its consumers exist
    for b in res:
        print(f"{b['verdict']} {b['repo']}:{b['check']} {b['reason']}".strip())
    return 0 if all(b["verdict"] == "PASS" for b in res) else (1 if any(b["verdict"] == "FAIL" for b in res) else 2)


def cmd_integrate(a) -> int:
    import engine
    print(f"INTEGRATED {a.task} {engine.integrate(a.run, a.task)[:9]}")
    return 0


def cmd_milestone(a) -> int:
    import engine
    out = engine.close_milestone(a.run, a.milestone)
    _j(out)
    return 0 if out["status"] == "merged" else 1


def cmd_final(a) -> int:
    import engine
    res = engine.final_verify(a.run)
    bad = [b for b in res if b["verdict"] != "PASS"]
    for b in bad:
        print(f"{b['verdict']} {b['repo']}:{b['check']} {b['reason']}")
    if store.read_json(store.run_dir(a.run) / "contract.json").get("spec"):
        print("\n".join(contract.spec_report(a.run, not bad)))
    return 0 if not bad else 1


def cmd_push(a) -> int:
    import engine
    print(engine.push(a.run, a.repo))
    return 0


def cmd_pr(a) -> int:
    import ci
    import engine
    engine.pr_guard(a.run, a.repo)  # local proof of this repo is READY, and a consumer waits for its producer's release
    print(ci.open_pr(a.run, a.repo))
    if a.auto_merge:
        engine.pr_guard(a.run, a.repo, arming=True)
        print("auto-merge armed" if ci.arm_auto_merge(a.run, a.repo) else "owner merges")
    return 0


def cmd_pack(a) -> int:
    import release
    _j(release.pack(a.run, a.producer))
    return 0


def cmd_publish(a) -> int:
    import release
    _j(release.publish(a.run, a.producer))
    return 0


def cmd_clean(a) -> int:
    import clean
    return clean.main(a.rest)


def cmd_boards(a) -> int:
    import board
    return board.main(a.rest)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sdlc")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, *args, **kw):
        c = sub.add_parser(name, **kw)
        for arg, opts in args:
            c.add_argument(arg, **opts)
        c.set_defaults(fn=fn)
        return c

    RUN = ("run", {})
    add("plan", cmd_plan, ("repos", {"nargs": "+"}), ("--slug", {"required": True}), ("--title", {}))
    add("draft", cmd_draft, RUN, ("--plan", {}), ("--contract", {}), ("--tasks", {}), ("--input", {"action": "append", "default": []}),
            ("--dep", {"action": "append", "default": []}), ("--strict", {"action": "store_true"}))
    add("screen", cmd_screen, RUN)
    add("gate", cmd_gate, RUN, ("purpose", {"nargs": "?", "default": "approve", "choices": ["approve", "restart"]}), ("--by", {}))
    add("done", cmd_done, RUN)
    add("check", cmd_check, ("run", {"nargs": "?"}), ("--due", {}))
    add("list", cmd_list)
    add("status", cmd_status, ("run", {"nargs": "?"}))
    add("resume", cmd_resume, RUN)
    add("stop", cmd_stop, RUN)
    add("next", cmd_next, RUN)
    add("dispatch", cmd_dispatch, RUN, ("tasks", {"nargs": "+"}))
    add("submit", cmd_submit, RUN, ("task", {}))
    add("verify", cmd_verify, RUN, ("--task", {}), ("--check", {}), ("--repo", {}))
    add("integrate", cmd_integrate, RUN, ("task", {}))
    add("milestone", cmd_milestone, RUN, ("milestone", {}))
    add("final", cmd_final, RUN)
    add("push", cmd_push, RUN, ("repo", {}))
    add("pr", cmd_pr, RUN, ("repo", {}), ("--auto-merge", {"action": "store_true"}))
    add("pack", cmd_pack, RUN, ("producer", {}))
    add("publish", cmd_publish, RUN, ("producer", {}))
    add("boards", cmd_boards, ("rest", {"nargs": argparse.REMAINDER}))
    add("clean", cmd_clean, ("rest", {"nargs": argparse.REMAINDER}))
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        return a.fn(a)
    except SdlcError as e:
        print(f"BLOCKED {e}" if not str(e).startswith(("BLOCKED", "STOPPED")) else str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
