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

Which gate run counts at all is `holds()`: the one reader of the gate's receipts. Every gate run
writes one receipt, <git-common-dir>/sdlc/receipts/<change>/<scope>-<n>.json (verify_gate.py), so
every worktree sees it and the newest run of a (change, scope, n) is the one record. pr-gate.sh,
sdlc_status.py and verify_gate.py all ask `holds()`; report.json is a human-readable artifact.
"""

from __future__ import annotations

import datetime as dt
import functools
import json
import re
import subprocess
from pathlib import Path

LOCKED = {"facts.md", "done.json", "lock.json"}
EVIDENCE_FILES = {"marks.json"}
EVIDENCE_DIRS = {"asks", "evidence", "shots"}


@functools.cache
def _common(repo: str) -> str:
    """The git dir every worktree of the repo shares, resolved once per process."""
    out = subprocess.run(
        ["git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True
    )
    return out.stdout.decode("utf-8", "replace").strip() if out.returncode == 0 else ""


def receipt_dir(repo: Path, change: str) -> Path:
    return Path(_common(str(repo)) or ".git") / "sdlc" / "receipts" / change


def receipt_path(repo: Path, change: str, scope: str, n: int) -> Path:
    """verify_gate.py writes here; the layout is written down twice (the gate lives in scripts/,
    this file in the hooks) and test_verify_gate.py holds the two together."""
    return receipt_dir(repo, change) / f"{scope}-{n}.json"


def has_receipts(repo: Path, change: str) -> bool:
    return next(receipt_dir(repo, change).glob("*.json"), None) is not None


def normalize(data: object, change: str, scope: str, n: int) -> dict:
    """A receipt (or a report an older gate wrote as one) with `verdict` (pass, fail, blocked) and
    `valid` added; {} for nothing. Valid: it names this change, scope and number, and a pass line
    carries the record's own sha. Older records have no `verdict`: it comes from `result`."""
    if not isinstance(data, dict) or not data:
        return {}
    result = str(data.get("result", ""))
    verdict = data.get("verdict") or (
        "pass" if result.startswith("VERIFY PASS") else "blocked" if result.startswith("VERIFY BLOCKED") else "fail"
    )
    valid = (
        data.get("scope") == scope
        and data.get("change", change) == change
        and str(data.get("milestone", n)) == str(n)
        and (verdict != "pass" or result == f"VERIFY PASS {scope} {change} {data.get('sha')}")
    )
    return {**data, "verdict": verdict, "valid": bool(valid)}


def read_receipt(repo: Path, change: str, scope: str, n: int) -> dict:
    """The receipt of (change, scope, n), normalized; {} when the gate never ran it."""
    try:
        data = json.loads(receipt_path(repo, change, scope, n).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return normalize(data, change, scope, n)


def holds(
    repo: Path,
    changes_dir: str,
    change: str,
    scope: str,
    n: int,
    head: str,
    owner: str | None = None,
    legacy: tuple[Path, ...] | list[Path] = (),
) -> str:
    """The gated sha of the pass that holds at `head` for this change, scope and number (the
    milestone number; 0 for any other scope), or "". `owner` is the project branch the caller
    needs the pass to have been for ("" for none); None does not ask.

    A change with receipts is decided by its receipt alone: the newest run of (change, scope, n),
    a failed or blocked one too, and a milestone without a number has no receipt that counts.
    LEGACY RULE: a change with no receipt at all (gated before 3.20.3) still reads the old
    report.json files in `legacy`; the first receipt the change gets ends that for good."""
    if not head:
        return ""
    if has_receipts(repo, change):
        if scope == "milestone" and n < 1:
            return ""
        found = read_receipt(repo, change, scope, n)
        if found.get("verdict") != "pass" or not found["valid"]:
            return ""
        # a receipt from before 3.20.3 names no owner: only the caller's own record check speaks
        if owner is not None and found.get("owner", owner) != owner:
            return ""
        gated = str(found.get("sha", ""))
        return gated if proves(repo, changes_dir, gated, head) else ""
    for path in legacy:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        gated = data.get("sha") or ""
        if not gated or data.get("scope", scope) != scope:
            continue
        if scope == "milestone" and "milestone" in data and str(data["milestone"]) != str(n or ""):
            continue
        if str(data.get("result", "")).startswith(f"VERIFY PASS {scope} {change} ") and proves(
            repo, changes_dir, gated, head
        ):
            return gated
    return ""


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
