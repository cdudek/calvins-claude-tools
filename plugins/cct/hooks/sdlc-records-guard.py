#!/usr/bin/env python3
"""PreToolUse: no agent writes under ~/.sdlc/runs/ (or $SDLC_HOME/runs/). Only the runner's own scripts do.

Deny on a match, stay silent otherwise. It stops a careless agent, not a hostile process (design 3.2).
"""
import json
import os
import re
import shlex
import sys

READ_ONLY = {"cat", "ls", "head", "tail", "grep", "wc", "stat", "file", "diff", "less", "rg", "jq", "tree", "pwd", "echo", "true"}
OPERATORS = set(";&|<>()")


def runs_root() -> str:
    return os.path.realpath(os.path.join(os.environ.get("SDLC_HOME") or os.path.expanduser("~/.sdlc"), "runs"))


def deny(why: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": why}}))


def touches(tok: str, root: str, cwd: str) -> bool:
    """True when a word is the runs folder, inside it, an ancestor of it, or carries its path in a larger string."""
    t = os.path.expanduser(os.path.expandvars(tok))
    if ".sdlc/runs" in t or root in t:
        return True
    if not t or t.startswith("-") and "/" not in t:
        return False
    p = os.path.realpath(t if os.path.isabs(t) else os.path.join(cwd, t))
    return p == root or p.startswith(root + os.sep) or root.startswith(p.rstrip(os.sep) + os.sep)


def is_runner(argv: list[str]) -> bool:
    if not argv:
        return False
    if os.path.basename(argv[0]) == "sdlc":
        return True
    return os.path.basename(argv[0]).startswith("python") and len(argv) > 1 and argv[1].endswith("sdlc-run/runner/sdlc.py")


def main() -> None:
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return
    root, ti = runs_root(), ev.get("tool_input") or {}
    cwd = ev.get("cwd") or os.getcwd()
    msg = f"Run records under {root} are written only by the sdlc runner; use `sdlc.py` instead of editing them."
    if ev.get("tool_name") in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        p = os.path.realpath(os.path.expanduser(ti.get("file_path") or ti.get("notebook_path") or ""))
        if p == root or p.startswith(root + os.sep):
            deny(msg)
        return
    if ev.get("tool_name") != "Bash":
        return
    cmd = ti.get("command") or ""
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        # shortcut: an unparsable command is denied only when it could concern the records; upgrade if cheap to do better
        if re.search(r"sdlc|runs|SDLC_HOME", cmd):
            deny(msg + " (the command could not be parsed)")
        return
    composite = any(set(t) <= OPERATORS for t in toks) or "`" in cmd or "$(" in cmd
    words = [t for t in toks if not set(t) <= OPERATORS]
    inside = os.path.realpath(cwd) == root or os.path.realpath(cwd).startswith(root + os.sep)
    if not any(touches(w, root, cwd) for w in words) and not inside:
        return
    if composite:
        deny(msg + " (a command that touches them may not be chained or redirected)")
    elif is_runner(words):
        return
    elif words[0] in READ_ONLY:
        return
    else:
        deny(msg)


main()
