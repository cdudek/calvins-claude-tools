#!/usr/bin/env python3
"""A repeated gate block says stop. pr-gate.sh, chain-gate.sh and gate-bash.sh pass every block
through here: it records the block in `<git-common-dir>/sdlc-blocks/<session_id>.jsonl` and, when
the same hook already refused byte-identical text in this session, returns the message behind a
STOP line that names the hook, what it read and the one thing the owner does.

Imported (`rewrite`) by the Python hooks, run by the bash one:
    block_state.py <hook> <source> <action> <message>      payload JSON on stdin, prints the text

It never raises and never blocks: no session_id, an unreadable cwd or an unwritable state dir
returns the first-time message unchanged.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

KEEP_SECONDS = 14 * 86400


def _state_file(payload: dict) -> Path:
    session, cwd = payload["session_id"], payload["cwd"]
    if not (isinstance(session, str) and re.fullmatch(r"[\w-][\w.-]*", session) and isinstance(cwd, str) and cwd):
        raise ValueError("no usable session_id or cwd")
    out = subprocess.run(
        ["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, timeout=3,
    )  # fmt: skip
    if out.returncode or not out.stdout.strip():
        raise ValueError("cwd is not in a git repo")
    return Path(out.stdout.strip()) / "sdlc-blocks" / f"{session}.jsonl"


def rewrite(hook: str, message: str, source: str, action: str, payload: dict) -> str:
    """The text to print for this block: `message` the first time, the STOP form on a repeat."""
    message = message.rstrip("\n")
    try:
        path = _state_file(payload)
        path.parent.mkdir(exist_ok=True)
        for old in path.parent.iterdir():  # 14-day cleanup on every write
            try:
                if old.is_file() and old.stat().st_mtime < time.time() - KEEP_SECONDS:
                    old.unlink()
            except OSError:
                pass
        repeat = False
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                    repeat = repeat or (row["hook"] == hook and row["message"].rstrip("\n") == message)
                except (ValueError, KeyError, TypeError, AttributeError):
                    continue
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"hook": hook, "message": message, "ts": int(time.time())}) + "\n")
        if repeat:
            return (
                f"STOP: this block repeated. {hook} refused the same call again; it read {source}. "
                f"Do not retry. Owner action: {action.strip().rstrip('.')}.\n{message}"
            )
    except Exception:  # block state never changes the verdict
        pass
    return message


if __name__ == "__main__":
    hook, source, action, message = sys.argv[1:5]
    try:
        payload = json.loads(sys.stdin.read())
    except ValueError:
        payload = {}
    print(rewrite(hook, message, source, action, payload if isinstance(payload, dict) else {}))
