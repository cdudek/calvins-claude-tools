#!/usr/bin/env python3
"""Is a /goal running in this session? One reading for pr-gate.sh, chain-gate.sh and
verify-on-stop.sh. Imported (goal_active) or run: `goal_active.py <transcript>` exits 0 when active.

The transcript shapes are undocumented; test_goal_active.py pins them:
  - {"attachment": {"type": "goal_status", "met": false}}                   goal running
  - {"attachment": {"type": "goal_status", "met": true}}                    goal met
  - {"attachment": {"type": "goal_status", "met": false, "failed": true}}   goal ended failed
  - {"type": "system", "subtype": "local_command", "content": "...<command-args>clear</command-args>"}
    and "<local-command-stdout>No goal set</local-command-stdout>"          /goal clear
  - {"type": "user", "message": {"content": "A session-scoped Stop hook is now active ..."}}  goal set

Active = the last of those says running. The only off switch is `SDLC_GOAL_OFF=1` in the
environment Claude starts with (an agent's Bash export never reaches a hook). There is no
file switch: an agent could write one.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SET = "A session-scoped Stop hook is now active"
# Only a whole command entry or the exact stdout ends a goal: the same words quoted inside a
# longer message (a subagent report, a pasted log) must not switch the gate off.
TAGS = re.compile(r"\s*<command-(name|message|args)>([^<]*)</command-\1>\s*")
NO_GOAL = "<local-command-stdout>No goal set</local-command-stdout>"


def _cleared(text: str) -> bool:
    if text.strip() == NO_GOAL:
        return True
    tags, pos = {}, 0
    while pos < len(text):
        m = TAGS.match(text, pos)
        if not m:
            return False
        tags[m.group(1)], pos = m.group(2).strip(), m.end()
    return tags.get("name") == "/goal" and tags.get("args") == "clear"


def _text(entry: dict) -> str:
    c = entry.get("content")
    if c is None:
        c = (entry.get("message") or {}).get("content")
    return c if isinstance(c, str) else ""


def goal_active(transcript: str) -> bool | None:
    """True while a goal runs, False when none does, None when the transcript is unreadable."""
    try:
        lines = Path(transcript).read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
        return None
    parsed, live = 0, False
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        parsed += 1
        att = entry.get("attachment")
        if isinstance(att, dict) and att.get("type") == "goal_status":
            live = att.get("met") is False and not att.get("failed")
        elif entry.get("type") in ("system", "user"):  # never api-request blobs: they quote old text
            text = _text(entry)
            if _cleared(text):
                live = False
            elif text.startswith(SET):
                live = True
    if not parsed:
        return None
    return live and os.environ.get("SDLC_GOAL_OFF") != "1"


if __name__ == "__main__":
    sys.exit(0 if len(sys.argv) > 1 and goal_active(sys.argv[1]) else 1)
