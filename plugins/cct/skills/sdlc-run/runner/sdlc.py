#!/usr/bin/env python3
"""sdlc: the runner CLI (sdlc-run 4.x). Plain stdlib. Records live in ~/.sdlc/runs/<run-id>/, never in a repo.

  plan <repo>... --slug S [--title T]   discover, probe, write plan/contract drafts and the approval screen
  approve <id> --by NAME                record the owner's one approval (after the approval gate returned approved)
  check [<id>]                          read-only completion test: exit 0 READY, 1 FAIL, 2 BLOCKED/STOPPED, 3 PENDING
  status [<id>] | list                  where a run stands; live runs
  resume <id>                           continue after a crash, on the same machine
  stop <id>                             durably stop a run and cancel its jobs
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
    return code


def cmd_approve(a) -> int:
    rec = contract.approve(a.run, a.by)
    print(f"APPROVED {a.run} digest={rec['digest'][:12]} by={a.by}")
    return 0


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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sdlc")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("run", nargs="?")
    c.add_argument("--due", help="only the items due at this milestone")
    c.set_defaults(fn=cmd_check)
    c = sub.add_parser("approve")
    c.add_argument("run")
    c.add_argument("--by", required=True)
    c.set_defaults(fn=cmd_approve)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    c = sub.add_parser("status")
    c.add_argument("run", nargs="?")
    c.set_defaults(fn=cmd_status)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    try:
        return a.fn(a)
    except SdlcError as e:
        print(f"BLOCKED {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
