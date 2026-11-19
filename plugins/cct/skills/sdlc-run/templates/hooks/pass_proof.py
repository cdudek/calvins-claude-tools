"""What a gate pass proves about a later head: one definition, read by pr-gate.sh (hook) and by
sdlc_status.py (the goal check). stdlib only.

A pass proves the head the gate ran on. A later head counts as the same pass only when the gated
head is its ancestor and nothing but the change records moved: a file outside the changes folder,
a locked input (facts.md, done.json, lock.json; the checks live in sdlc.json, outside the folder)
or evidence (marks.json and anything under asks/, evidence/, shots/) moved. An archive
move (changes/<id> -> changes/archive/<id> or archive/<year>/<year-month>/<id>) is not a change
when every file keeps its content.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

LOCKED = {"facts.md", "done.json", "lock.json"}
EVIDENCE_FILES = {"marks.json"}
EVIDENCE_DIRS = {"asks", "evidence", "shots"}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True)


def _key(path: str, rel: str) -> str:
    """The path inside the change, with the archive folders taken off."""
    parts = Path(path).relative_to(rel).parts
    if parts and parts[0] == "archive":
        parts = parts[1:]
        if len(parts) > 2 and re.fullmatch(r"\d{4}", parts[0]) and re.fullmatch(r"\d{4}-\d{2}", parts[1]):
            parts = parts[2:]
    return "/".join(parts)


def _tree(repo: Path, rel: str, ref: str) -> dict[str, str]:
    out = _git(repo, "ls-tree", "-rz", ref, "--", rel + "/").stdout.decode("utf-8", "replace")
    files = {}
    for entry in filter(None, out.split("\0")):
        meta, _, path = entry.partition("\t")
        files[_key(path, rel)] = meta.split()[2]
    return files


def proves(repo: Path, changes_dir: str, gated: str, head: str) -> bool:
    """True when a pass gated at `gated` still holds at `head`."""
    if not gated or not head:
        return False
    if gated == head:
        return True
    if _git(repo, "merge-base", "--is-ancestor", gated, head).returncode:
        return False
    rel = changes_dir.rstrip("/")
    moved = _git(repo, "diff", "--name-only", "--no-renames", "-z", gated, head).stdout
    if any(not p.startswith(rel + "/") for p in moved.decode("utf-8", "replace").split("\0") if p):
        return False
    before, after = _tree(repo, rel, gated), _tree(repo, rel, head)
    for key in {k for k in before.keys() | after.keys() if before.get(k) != after.get(k)}:
        parts = key.split("/")
        if parts[-1] in LOCKED | EVIDENCE_FILES or EVIDENCE_DIRS & set(parts[:-1]):
            return False
    return True
