#!/usr/bin/env python3
"""PreToolUse: agents neither read nor write the run records (~/.sdlc/runs/ or $SDLC_HOME/runs/). Only the runner does.

This hook is the barrier: receipts and checkpoints carry no signature, so nothing but this guard keeps an agent from
writing a pass. It stops a careless or confused agent, not a hostile process of the same user (design 3.2).

Rule for Bash: a command that mentions the sdlc folder in any form is denied unless the WHOLE command is exactly one
invocation of this plugin's own runner. Deny on a match, stay silent otherwise.
"""
import fnmatch
import json
import os
import re
import shlex
import sys

RUNNER = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "sdlc-run", "runner", "sdlc.py"))
OPERATORS = set(";&|<>()")


def roots() -> tuple[str, str, str]:
    home = os.environ.get("SDLC_HOME") or os.path.expanduser("~/.sdlc")
    return home, os.path.join(home, "runs"), os.path.realpath(os.path.join(home, "runs"))


def deny(why: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": why}}))


def under(path: str, root: str) -> bool:
    p = os.path.realpath(os.path.expanduser(os.path.expandvars(path))) if path else ""
    return bool(p) and (p == root or p.startswith(root + os.sep))


def mentions(cmd: str, words: list[str], home: str, runs: str, real: str) -> bool:
    if ".sdlc" in cmd or "SDLC_HOME" in cmd or home in cmd or runs in cmd or real in cmd:
        return True
    for w in words:
        if ".sdlc" in w or home in w:
            return True
        if re.search(r"[*?\[]", w):  # a glob that could name the folder
            g = os.path.expanduser(os.path.expandvars(w))
            cands = [p for h in (home, os.path.realpath(home), os.path.expanduser("~/.sdlc"))
                     for p in (h, os.path.join(h, "runs"), os.path.join(h, "runs", "x"), os.path.join(h, "runs", "x", "y"))]
            if any(fnmatch.fnmatchcase(c, g) for c in cands):
                return True
            base = g.rsplit("/", 1)[-1]
            if base.startswith(".") and fnmatch.fnmatchcase(".sdlc", base):
                return True
    return False


def is_exact_runner(cmd: str, words: list[str]) -> bool:
    """One simple command, no chaining, no expansion, and argv resolves to this plugin's own runner."""
    if "\n" in cmd or "\r" in cmd or "`" in cmd or "$" in cmd:
        return False
    if any(set(w) <= OPERATORS for w in words) or not words:
        return False
    argv = words
    if os.path.basename(argv[0]).startswith("python") and len(argv) > 1:
        argv = argv[1:]
    return os.path.realpath(os.path.expanduser(argv[0])) == RUNNER


def main() -> None:
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return
    home, runs, real = roots()
    ti, tool = ev.get("tool_input") or {}, ev.get("tool_name")
    cwd = ev.get("cwd") or os.getcwd()
    msg = f"The run records under {runs} belong to the sdlc runner; use `sdlc.py` instead of reading or editing them."
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit", "Read"):
        if under(ti.get("file_path") or ti.get("notebook_path") or "", real):
            deny(msg)
    elif tool in ("Grep", "Glob"):
        p = ti.get("path") or ""
        pat = ti.get("pattern") or ""
        rp = os.path.realpath(os.path.expanduser(p)) if p else ""
        ancestor = bool(rp) and real.startswith(rp.rstrip(os.sep) + os.sep)  # a recursive search from above reaches the records
        if under(p, real) or ancestor or ".sdlc" in pat or under(pat, real):
            deny(msg)
    elif tool == "Bash":
        cmd = ti.get("command") or ""
        try:
            lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
            lex.whitespace_split = True
            words = list(lex)
            parsed = True
        except ValueError:
            words, parsed = [], False
        if "SDLC_GATE_CMD" in cmd:  # the owner's approval program is not an agent's to set
            return deny("SDLC_GATE_CMD may not be set: the approval gate is a fixed command.")
        inside = under(cwd, real)
        if not (mentions(cmd, words, home, runs, real) or inside):
            return
        if parsed and is_exact_runner(cmd, words):
            return
        deny(msg + (" (the command could not be parsed)" if not parsed else " (only one plain runner call may touch them)"))


main()
