"""What a gate pass proves about a later head: one definition, read by pr-gate.sh (hook) and by
sdlc_status.py (the goal check). stdlib only.

A pass proves the head the gate ran on. A later head counts as the same pass only when the gated
head is its ancestor and nothing but the change records moved: a file outside the changes folder,
a locked input (facts.md, done.json, lock.json; the checks live in sdlc.json, outside the folder)
or evidence (marks.json and anything under asks/, evidence/, shots/) moved. An archive
move (changes/<id> -> changes/archive/<id> or archive/<year>/<year-month>/<id>) is not a change
when every file keeps its content, except that facts.md may gain one `archived_at:` frontmatter
line: Stage 7 requires it in that same commit, and its value must be a real date written the way
templates/tests/test_sdlc.py accepts (YYYY-MM-DD).
"""

from __future__ import annotations

import datetime as dt
import re
import subprocess
from pathlib import Path

LOCKED = {"facts.md", "done.json", "lock.json"}
EVIDENCE_FILES = {"marks.json"}
EVIDENCE_DIRS = {"asks", "evidence", "shots"}


def milestone_of(branch: str, prefix: str, slug: str) -> int | None:
    """The milestone a branch is: `<prefix><slug>-<n>` is n, the unnumbered `<prefix><slug>` is 1,
    any other branch none. `prefix` is sdlc.json `milestones.branchPrefix`. verify_gate.py writes the
    number into its report with the same rule (test_contract keeps the two equal)."""
    name = branch[len(prefix) :] if branch.startswith(prefix) else ""
    if not slug or not name:
        return None
    if name == slug:
        return 1
    found = re.fullmatch(re.escape(slug) + r"-(\d+)", name)
    return int(found[1]) if found else None


def bound(data: dict, scope: str, subject: str, number: int | None = None, owner: str | None = None) -> bool:
    """A gate report is a pass for this subject: `VERIFY PASS <scope> <subject> <sha>` naming the
    sha it records, and for a milestone the change and the number it was gated as (an unnumbered
    branch is 1; a report with no number is a pass for no numbered milestone). `owner`, when given,
    is the project branch the caller needs: the report must name the same one."""
    result, sha = str(data.get("result", "")), data.get("sha")
    if not sha or data.get("scope", scope) != scope or result != f"VERIFY PASS {scope} {subject} {sha}":
        return False
    if scope == "milestone" and (data.get("change") != subject or number is None or data.get("milestone") != number):
        return False
    return owner is None or scope == "project" or data.get("owner") == owner


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


def _tree(repo: Path, rel: str, ref: str) -> dict[str, tuple[str, str]] | None:
    """(blob, path) per change path; None when two paths fold onto one key (a live file and an
    archive copy of it), because then one of them could hide an edit to the other."""
    out = _git(repo, "ls-tree", "-rz", ref, "--", rel + "/").stdout.decode("utf-8", "replace")
    files: dict[str, tuple[str, str]] = {}
    for entry in filter(None, out.split("\0")):
        meta, _, path = entry.partition("\t")
        key = _key(path, rel)
        if key in files:
            return None
        files[key] = (meta.split()[2], path)
    return files


def _only_archived_at(repo: Path, old: tuple[str, str], new: tuple[str, str]) -> bool:
    """`new` is `old` plus exactly one `archived_at:` line inside the frontmatter, and it moved
    into the archive: the one content change the Stage 7 archive commit makes."""
    if "archive" in Path(old[1]).parts or "archive" not in Path(new[1]).parts:
        return False
    before, after = (
        _git(repo, "cat-file", "blob", blob).stdout.decode("utf-8", "replace") for blob in (old[0], new[0])
    )
    lines = after.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---" or "archived_at:" in before:
        return False
    try:
        close = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return False
    added = [i for i, line in enumerate(lines) if line.startswith("archived_at:")]
    if not (len(added) == 1 and added[0] < close and "".join(lines[: added[0]] + lines[added[0] + 1 :]) == before):
        return False
    value = lines[added[0]].split(":", 1)[1].strip()
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None


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
    if before is None or after is None:
        return False
    for key in {k for k in before.keys() | after.keys() if (before.get(k) or ("",))[0] != (after.get(k) or ("",))[0]}:
        parts = key.split("/")
        if parts[-1] == "facts.md" and key in before and key in after and _only_archived_at(repo, before[key], after[key]):
            continue
        if parts[-1] in LOCKED | EVIDENCE_FILES or EVIDENCE_DIRS & set(parts[:-1]):
            return False
    return True
