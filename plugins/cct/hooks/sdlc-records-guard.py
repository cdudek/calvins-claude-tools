#!/usr/bin/env python3
"""PreToolUse: no agent writes under ~/.sdlc/runs/ (or $SDLC_HOME/runs/). Only the runner's own scripts do.

Deny on a match, stay silent otherwise. It stops a careless agent, not a hostile process (design 3.2).
"""
import json
import os
import re
import sys

READ_ONLY = {"cat", "ls", "head", "tail", "grep", "wc", "stat", "file", "diff", "find", "less", "rg", "jq", "tree"}
WRITES = re.compile(r"(>|\btee\b|\bsed\b[^|;&]*\s-i|\bmv\b|\bcp\b|\brm\b|\bln\b|\bchmod\b|\btouch\b|\btruncate\b|\bdd\b|-delete\b|-exec\b|\bpython3?\b|\bnode\b|\bperl\b|\bsh\b|\bbash\b)")
RUNNER = re.compile(r"sdlc-run/runner/sdlc\.py|\bsdlc\b\s+(plan|draft|screen|approve|check|list|status|resume|stop|restart|next|dispatch|submit|verify|integrate|milestone|final|push|pr|pack|publish|clean)\b")


def runs_root() -> str:
    return os.path.realpath(os.path.join(os.environ.get("SDLC_HOME") or os.path.expanduser("~/.sdlc"), "runs"))


def deny(why: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": why}}))


def main() -> None:
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return
    root, ti = runs_root(), ev.get("tool_input") or {}
    msg = f"Run records under {root} are written only by the sdlc runner; use `sdlc.py` instead of editing them."
    if ev.get("tool_name") in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        p = os.path.realpath(os.path.expanduser(ti.get("file_path") or ti.get("notebook_path") or ""))
        if p == root or p.startswith(root + os.sep):
            deny(msg)
    elif ev.get("tool_name") == "Bash":
        cmd = ti.get("command") or ""
        home = os.path.expanduser("~")
        mentions = ".sdlc/runs" in cmd or root in cmd or (os.environ.get("SDLC_HOME") and os.environ["SDLC_HOME"] + "/runs" in cmd)
        if mentions and not RUNNER.search(cmd) and (WRITES.search(cmd) or cmd.split()[:1] and cmd.split()[0] not in READ_ONLY):
            deny(msg)


main()
