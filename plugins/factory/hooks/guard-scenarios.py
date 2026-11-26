#!/usr/bin/env python3
"""PreToolUse hook: only the factory verifier may touch the holdout scenarios (~/.factory/scenarios).
Any other subagent (builders, the UX verifier) is denied a tool call whose input names that folder.
The main session (the coordinator) has no agent_type and is allowed: it drafts the scenarios, unless
FACTORY_EVAL=1 (the eval harness), which denies it too so a coordinator cannot read them.
It also denies an Agent/Task call with run_in_background in a factory run (FACTORY_EVAL=1, or a cwd inside a repo
with .factory/ whose branch is milestone/*): /goal skips its evaluation while background work runs.
Fails closed: a crash or a non-object input is denied when the text names the folder; only unreadable JSON passes.
shortcut: matches the path as text (with ~, $HOME, // and /./ expanded), so a command that assembles the path at
runtime gets through; upgrade to an OS-level read restriction if a builder is ever seen doing that.
"""
import json
import os
import re
import subprocess
import sys

# bare "verifier" too: the hook input's agent_type format for plugin agents is not documented
ALLOWED = {"factory:verifier", "verifier"}
MARKER = "factory/scenarios"
DENY = {"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "factory holdout scenarios are for the verifier only; build from the delta and plan.",
}}
BG_DENY = {"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "factory runs start every agent in the foreground: run it again without run_in_background",
}}


def factory_run(event):
    if os.environ.get("FACTORY_EVAL") == "1":
        return True
    # shortcut: a milestone/* branch in a repo with .factory/ also matches an owner working there by hand; upgrade to an explicit env var if that bites
    cwd = str(event.get("cwd") or ".")
    try:
        git = lambda *a: subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, timeout=5).stdout.strip()  # noqa: E731
        if not git("symbolic-ref", "--short", "HEAD").startswith("milestone/"):
            return False
        top = git("rev-parse", "--show-toplevel")
        return bool(top) and os.path.isdir(os.path.join(top, ".factory"))
    except (OSError, subprocess.SubprocessError):
        return False  # not a factory run as far as we can tell: an ordinary session must never lose background agents to a git error


def mentions(text):
    home = os.path.expanduser("~")
    t = text.replace("${HOME}", home).replace("$HOME", home).replace("~/", home + "/")
    t = re.sub(r"/(\./|/)+", "/", t)  # a//b and a/./b
    # the folder's two names in one command (cd ~/.factory && cat scenarios/x) count as naming it
    return any(MARKER in v for v in (text, t)) or ("factory" in t and "scenarios" in t)


def decide(event):
    ti = event.get("tool_input")
    if event.get("tool_name") in ("Agent", "Task") and isinstance(ti, dict) and ti.get("run_in_background") not in (None, False, 0, "", "false", "False") and factory_run(event):
        return BG_DENY
    agent = str(event.get("agent_type") or "")
    if not agent and os.environ.get("FACTORY_EVAL") != "1":
        return None
    if agent in ALLOWED:
        return None
    if not agent and event.get("tool_name") in ("Agent", "Task") and isinstance(ti, dict) and str(ti.get("subagent_type") or "") == "factory:verifier":
        # eval mode: the coordinator may dispatch the verifier with the scenarios path; dispatch names are always namespaced,
        # so the bare alias is not accepted here (it could be another plugin's agent)
        return None
    return DENY if mentions(json.dumps(event.get("tool_input", {}))) else None


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except ValueError:
        sys.exit(0)  # unreadable input: do not block unrelated work
    try:
        if not isinstance(event, dict):
            raise TypeError("event is not an object")
        out = decide(event)
    except Exception:
        out = DENY if mentions(raw) else None  # cannot tell who is asking: deny whatever names the folder
    if out:
        print(json.dumps(out))
