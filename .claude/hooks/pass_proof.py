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

Three rules keep the gate (the writer, scripts/verify_gate.py), the hook and the status check
(the readers) from drifting apart; sdlc_status.py ships in the plugin and updates with it, the
other two are copies in each repo that change only when someone runs adopt.

1. ONE KEY. `key()` maps (scope, branch, explicit milestone) to the record key, the file stem
   <git-common-dir>/sdlc/receipts/<change>/<key>.json. The gate, the hook and the status check all
   call it; nothing else derives a milestone number or a record name.
2. ONE READER. `holds()` is the only reader of those files, and `write_record()` the only writer.
   A record must carry every binding field (change, scope, key, number, owner, sha, verdict): one
   that lacks any does not hold. The newest run of a key replaces the one before it.
3. THE READER'S MODE COMES FROM THE WRITER. `writer_format()` reads RECEIPT_FORMAT from the repo's
   own scripts/verify_gate.py (the sdlcVersion stamp in sdlc.json only when that file cannot be
   read). A writer without the constant is older: only the legacy path applies (report.json, and
   the old milestone-<n>.json receipt), exactly what that writer's own readers accepted.
"""

from __future__ import annotations

import datetime as dt
import functools
import json
import os
import re
import subprocess
from pathlib import Path

LOCKED = {"facts.md", "done.json", "lock.json"}
EVIDENCE_FILES = {"marks.json"}
EVIDENCE_DIRS = {"asks", "evidence", "shots"}
RECEIPT_FORMAT_RE = re.compile(r"^RECEIPT_FORMAT\s*=\s*(\d+)\s*$", re.M)
FIRST = ".first"  # written once, with the first record of a change; never read by the writer


@functools.cache
def _common(repo: str) -> str:
    """The git dir every worktree of the repo shares, resolved once per process."""
    out = subprocess.run(
        ["git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True
    )
    return out.stdout.decode("utf-8", "replace").strip() if out.returncode == 0 else ""


@functools.cache
def _top(repo: str) -> str:
    out = subprocess.run(["git", "-C", repo, "rev-parse", "--show-toplevel"], capture_output=True)
    return out.stdout.decode("utf-8", "replace").strip() or repo if out.returncode == 0 else repo


def slug_of(name: str) -> str:
    """A change folder's slug: the id without its date and ticket prefix."""
    return re.sub(r"^[A-Z][A-Z0-9]+-\d+-", "", re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name))


def key(
    scope: str, branch: str = "", milestone: int | None = None, prefix: str = "milestone/", slug: str = ""
) -> str | None:
    """The record key of a gate run, or None when nothing names one (a detached HEAD). A milestone
    is the explicit number, else the branch's `-<n>`; the unnumbered branch `<prefix><slug>` is
    milestone 1, as is a plan without a Milestones row. A run on some other branch writes
    `milestone-0`, a slot no reader counts. A feature is its branch's name (one slot per feature),
    a project has one."""
    if scope == "project":
        return "project-0"
    if scope == "feature":
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", branch).strip("-.")
        return f"feature-{name}" if name else None
    if scope != "milestone":
        return None
    if milestone is not None:
        return f"milestone-{int(milestone)}"
    name = branch[len(prefix) :] if prefix and branch.startswith(prefix) else ""
    if slug and name == slug:
        return "milestone-1"
    numbered = (slug and re.fullmatch(re.escape(slug) + r"-(\d+)", name)) or re.fullmatch(r".+-(\d+)", name)
    return f"milestone-{int(numbered[1])}" if numbered else "milestone-0" if branch else None


def _dir(repo: Path, change: str) -> Path:
    return Path(_common(str(repo)) or ".git") / "sdlc" / "receipts" / change


def write_record(repo: Path, change: str, record_key: str, data: dict) -> None:
    """The gate's one write: the record under its key, replaced whole (a reader sees the old record
    or the new one), after the change's FIRST marker exists (created once, never read here)."""
    folder = _dir(repo, change)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        with open(folder / FIRST, "x", encoding="utf-8") as marker:
            marker.write(str(data.get("time", "")))
    except FileExistsError:
        pass
    path = folder / f"{record_key}.json"
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def writer_format(repo: Path) -> int:
    """2 when the repo's installed gate writes bound records (RECEIPT_FORMAT in its
    scripts/verify_gate.py), else 1. The sdlcVersion stamp is the fallback only for a gate file
    that cannot be read: adopt restamps it on a plain --upgrade, which keeps the old gate."""
    top = Path(_top(str(repo)))
    try:
        found = RECEIPT_FORMAT_RE.search((top / "scripts" / "verify_gate.py").read_text(encoding="utf-8"))
        return int(found[1]) if found else 1
    except OSError:
        pass
    try:
        stamp = json.loads((top / "sdlc.json").read_text(encoding="utf-8")).get("sdlcVersion", "")
        return 2 if tuple(int(x) for x in re.findall(r"\d+", str(stamp))[:3]) >= (3, 20, 4) else 1
    except (OSError, ValueError, AttributeError):
        return 1


def _json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _normalize(data: dict, change: str, scope: str, record_key: str, n: int, strict: bool) -> dict:
    """The record with `verdict` and `valid`. Strict (a format-2 writer): every binding field must
    be present and right. Lenient (an older writer's receipt): scope, change and milestone must
    match, the verdict comes from `result`, and an owner counts only when the record names one."""
    if not data:
        return {}
    result = str(data.get("result", ""))
    if strict:
        verdict = data.get("verdict")
        bound = (
            verdict in ("pass", "fail", "blocked")
            and data.get("key") == record_key
            and "owner" in data
            and isinstance(data.get("sha"), str)
            and bool(data["sha"])
        )
    else:
        verdict = (
            "pass" if result.startswith("VERIFY PASS") else "blocked" if result.startswith("VERIFY BLOCKED") else "fail"
        )
        bound = True
    if scope == "milestone":
        bound = bound and "milestone" in data and str(data["milestone"]) == str(n)
    valid = (
        bound
        and data.get("scope") == scope
        and data.get("change") == change
        and (verdict != "pass" or result == f"VERIFY PASS {scope} {change} {data.get('sha')}")
    )
    return {**data, "verdict": verdict, "valid": bool(valid)}


class Hold(str):
    """The gated sha when a pass holds at the head asked about, "" when none does. What else the
    reader found is on the value, so the caller never reads a record itself:
    .verdict    the newest record's verdict (pass, fail, blocked) when it is bound to this change,
                key and owner, else ""
    .result     that record's last line
    .gated      the record's own sha when it is a bound PASS, whether or not it holds at the head
    .first      the time of the change's first record ("" when the new writer never ran for it)
    .record     the record itself ({} when none, or when it is not bound to this caller)
    .present    a record file exists for the key, bound or not
    .at(head)   the same record judged at another head (one read per key per poll)"""

    verdict: str
    result: str
    gated: str
    first: str
    record: dict
    present: bool
    at: object

    def __new__(cls, sha: str, verdict: str, found: dict, first: str, present: bool = False) -> Hold:
        self = super().__new__(cls, sha)
        self.verdict, self.record, self.first, self.present = verdict, found, first, present
        self.result = str(found.get("result", ""))
        self.gated = str(found.get("sha", "")) if verdict == "pass" else ""
        return self


def holds(
    repo: Path,
    changes_dir: str,
    change: str,
    record_key: str,
    head: str,
    owner: str | None = None,
    legacy: tuple[Path, ...] | list[Path] = (),
) -> Hold:
    """The gated sha of the pass that holds at `head` for this change and key (`key()`), or "". The
    record must have been issued for `owner`, the project branch the caller needs ("" for none);
    None does not ask. With no `head` the answer is "" and the record's verdict is still reported.

    A format-2 writer is decided by its record alone: the newest run of the key, a failed or
    blocked one too. LEGACY (an older writer): the old milestone-<n>.json receipt decides when
    there is a valid one; otherwise the report.json files in `legacy` (a pass whose result line
    names this scope and change, and its milestone when it records one)."""
    repo = Path(repo)
    scope = record_key.split("-", 1)[0]
    n = int(record_key.split("-", 1)[1]) if scope == "milestone" and record_key.split("-", 1)[1].isdigit() else 0
    strict = writer_format(repo) >= 2
    marker = _dir(repo, change) / FIRST
    first = marker.read_text(encoding="utf-8").strip() if marker.is_file() else ""
    found = _normalize(_json(_dir(repo, change) / f"{record_key}.json"), change, scope, record_key, n, strict)
    mine = bool(found.get("valid")) and (owner is None or found.get("owner", owner) == owner)

    def decide(at: str) -> Hold:
        if scope == "milestone" and n < 1:  # no number, no milestone pass
            return _with(Hold("", "", {}, first, False), decide)
        done = Hold("", found["verdict"], found, first, True) if mine else Hold("", "", {}, first, bool(found))
        done.at = decide
        if (found.get("valid") and not mine) or not at:
            return done  # another project's record decides nothing here, and no report may stand in
        if mine:
            if found["verdict"] != "pass":
                return done
            ok = proves(repo, changes_dir, done.gated, at)
            return _with(Hold(done.gated if ok else "", "pass", found, first, True), decide)
        if strict:
            return done
        for path in legacy:
            data = _json(path)
            gated = data.get("sha") or ""
            if not gated or data.get("scope", scope) != scope:
                continue
            if scope == "milestone" and "milestone" in data and str(data["milestone"]) != str(n or ""):
                continue
            if str(data.get("result", "")).startswith(f"VERIFY PASS {scope} {change} ") and proves(
                repo, changes_dir, gated, at
            ):
                return _with(Hold(gated, "pass", data, first, bool(found)), decide)
        return done

    return decide(head)


def _with(hold: Hold, decide) -> Hold:
    hold.at = decide
    return hold


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
