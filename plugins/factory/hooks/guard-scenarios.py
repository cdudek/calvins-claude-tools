#!/usr/bin/env python3
"""PreToolUse hook: only the factory verifier may touch the holdout scenarios (~/.cfactory/scenarios).
Any other subagent (builders, the UX verifier) is denied a tool call whose input names that folder.
The main session (the coordinator) has no agent_type and is allowed: it drafts the scenarios.
shortcut: matches the path as text, so a command that assembles the path at runtime gets through; upgrade to an OS-level
read restriction if a builder is ever seen doing that.
"""
import json
import sys

# bare "verifier" too: the hook input's agent_type format for plugin agents is not documented
ALLOWED = {"factory:verifier", "verifier"}
MARKER = "cfactory/scenarios"


def decide(event):
    agent = str(event.get("agent_type") or "")
    if not agent:
        return None
    if agent in ALLOWED:
        return None
    if MARKER not in json.dumps(event.get("tool_input", {})):
        return None
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "factory holdout scenarios are for the verifier only; build from the delta and plan.",
    }}


if __name__ == "__main__":
    try:
        out = decide(json.load(sys.stdin))
    except ValueError:
        sys.exit(0)  # unreadable input: do not block unrelated work
    if out:
        print(json.dumps(out))
