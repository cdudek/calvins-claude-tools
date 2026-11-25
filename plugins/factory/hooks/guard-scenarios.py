#!/usr/bin/env python3
"""PreToolUse hook: only the factory verifier may touch the holdout scenarios (~/.cfactory/scenarios).
Any other subagent (builders, the UX verifier) is denied a tool call whose input names that folder.
The main session (the coordinator) has no agent_type and is allowed: it drafts the scenarios, unless
CFACTORY_EVAL=1 (the eval harness), which denies it too so a coordinator cannot read them.
Fails closed: a crash or a non-object input is denied when the text names the folder; only unreadable JSON passes.
shortcut: matches the path as text (with ~, $HOME, // and /./ expanded), so a command that assembles the path at
runtime gets through; upgrade to an OS-level read restriction if a builder is ever seen doing that.
"""
import json
import os
import re
import sys

# bare "verifier" too: the hook input's agent_type format for plugin agents is not documented
ALLOWED = {"factory:verifier", "verifier"}
MARKER = "cfactory/scenarios"
DENY = {"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "factory holdout scenarios are for the verifier only; build from the delta and plan.",
}}


def mentions(text):
    home = os.path.expanduser("~")
    t = text.replace("${HOME}", home).replace("$HOME", home).replace("~/", home + "/")
    t = re.sub(r"/(\./|/)+", "/", t)  # a//b and a/./b
    # the folder's two names in one command (cd ~/.cfactory && cat scenarios/x) count as naming it
    return any(MARKER in v for v in (text, t)) or ("cfactory" in t and "scenarios" in t)


def decide(event):
    agent = str(event.get("agent_type") or "")
    if not agent and os.environ.get("CFACTORY_EVAL") != "1":
        return None
    if agent in ALLOWED:
        return None
    ti = event.get("tool_input")
    if not agent and event.get("tool_name") in ("Agent", "Task") and isinstance(ti, dict) and str(ti.get("subagent_type") or "") in ALLOWED:
        return None  # eval mode: the coordinator may dispatch the verifier with the scenarios path
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
