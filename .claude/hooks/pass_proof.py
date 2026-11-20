"""What a gate pass proves about a later head: one definition, read by pr-gate.sh (hook) and by
sdlc_status.py (the goal check). stdlib only.

A pass proves the head the gate ran on. A later head counts as the same pass only when the gated
head is its ancestor and nothing but the change records moved: a file outside the changes folder,
a locked input (LOCKED_FILES: facts.md, or spec.md, design.md and tasks.md rows, with done.json and
lock.json; the checks live in sdlc.json, outside the folder)
or evidence (marks.json and anything under asks/, evidence/, shots/, screens/) moved. A record under
.sdlc/outcomes/ is a change record too. An archive
move (changes/<id> -> changes/archive/<id> or archive/<year>/<year-month>/<id>) is not a change
when every file keeps its content, except that facts.md may gain one `archived_at:` frontmatter
line: Stage 7 requires it in that same commit, and its value must be a real date written the way
templates/tests/test_sdlc.py accepts (YYYY-MM-DD).
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

# The documents approval locks, by layout: the one list. chain-gate.sh protects them (minus the ones
# that take ticks) and verify_gate.py hashes them into lock.json; test_sdd_hooks pins that the three agree.
LOCKED_FILES = {
    3: ("facts.md", "done.json", "lock.json"),
    4: ("spec.md", "design.md", "tasks.md", "done.json", "lock.json"),
}
TICKED_FILES = ("tasks.md",)  # a tick or a handover edit is not an edit: only its task rows are locked
LOCKED = {name for names in LOCKED_FILES.values() for name in names}
APP_LOCKED_FILES = ("screens.json", "screens/approved.json")  # locked too once the lock says `"visual": "app"` or hashed it (3.25.0)
APP_LOCKED_GLOBS = ("screens/*.png",)  # the approved baselines: the owner approves them, an edit needs the owner too
EVIDENCE_FILES = {"marks.json"}
EVIDENCE_DIRS = {"asks", "evidence", "shots", "screens"}  # screens/: the per-screen records (3.23.0)
OUTCOMES = ".sdlc/outcomes/"  # a record of the success measure (spec.py outcome write): records only


# Where a change folder lives: live, flat archive, archive/<year>/<year-month>. One list for the PR
# hook, the goal check and the gate, so none of them looks shallower or deeper than the runbook writes.
LAYOUTS = ("{id}", "archive/{id}", "archive/*/{id}", "archive/*/*/{id}")


def change_paths(changes: Path, change_id: str) -> list[Path]:
    """The folders named `change_id` under `changes`, live first. An empty list means the folder was
    removed after merge (the owner's rule), not an error: nothing is left to read."""
    if Path(change_id).name != change_id or change_id in ("..", "archive", ""):
        return []
    return [d for layout in LAYOUTS for d in sorted(changes.glob(layout.format(id=change_id))) if d.is_dir()]


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


def bound(
    data: dict, scope: str, subject: str, number: int | None = None, owner: str | None = None
) -> bool:
    """A gate report is a pass for this subject: `VERIFY PASS <scope> <subject> <sha>` naming the
    sha it records, and for a milestone the change and the number it was gated as (an unnumbered
    branch is 1; a report with no number is a pass for no numbered milestone). `owner`, when given,
    is the project branch the caller needs: the report must name the same one. A report with no `format`
    and none of the binding keys (change, owner, milestone) was written by a gate from before they
    existed (a kept older gate): only its result line is compared. Any other report must carry every
    binding and match it. The mode comes from the report, never from the checkout's gate text."""
    result, sha = str(data.get("result", "")), data.get("sha")
    if not sha or data.get("scope", scope) != scope or result != f"VERIFY PASS {scope} {subject} {sha}":
        return False
    if "format" not in data and not {"change", "owner", "milestone"} & data.keys():
        return True
    if scope != "project" and data.get("change") != subject:
        return False
    if scope == "milestone" and (number is None or data.get("milestone") != number):
        return False
    return owner is None or scope == "project" or data.get("owner") == owner


def passes_dir(repo: Path) -> Path | None:
    """Where the gate keeps a copy of every report it writes: the common git dir, which outlives the
    worktree and the branch that ran the gate."""
    out = _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.decode("utf-8", "replace").strip()
    return Path(out) / "sdlc" / "passes" if out else None


def pass_key(scope: str, branch: str, number: int | None = None) -> str | None:
    """The key of a record inside its change: a milestone's number (`milestone_of` numbers a branch,
    the caller passes its answer), a feature's branch (percent-encoded: `feat/a-b` and `feat/a/b` stay
    two keys), `0` for the project. None when the branch is not one the scope can be gated on."""
    if scope == "milestone":
        return str(number) if number else None
    if scope == "feature":
        return quote(branch, safe="") or None
    return "0" if scope == "project" else None


def shared(repo: Path, change: str, scope: str, key: str | None) -> Path | None:
    """<common git dir>/sdlc/passes/<change>/<scope>-<key>.json, or None for a name that is not a
    plain change id or a key that does not exist. The only reader of that folder is this module."""
    base = passes_dir(repo)
    if base is None or key is None or Path(change).name != change or change in ("", ".", ".."):
        return None
    return base / change / f"{scope}-{key}.json"


def _read(path: Path | None) -> tuple[int, dict] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path else None
        return (path.stat().st_mtime_ns, data) if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def newest(files: list[Path | None], scope: str | None = None) -> dict:
    """The newest report among `files` (the checkout's and the shared copy), {} when none reads.
    With `scope`, a report of another scope is not a candidate (report.json holds the last scope run)."""
    found = [r for r in map(_read, files) if r and (scope is None or r[1].get("scope") == scope)]
    return max(found, key=lambda r: r[0])[1] if found else {}


def chain(
    files: list[Path | None], scope: str, subject: str, number: int | None = None, owner: str | None = None
) -> list[tuple[bool, dict]]:
    """The reports of `files` that speak for this subject, newest first, as (is a pass, report): the
    passes (`bound`) down to the first non-pass, which is included and ends the list: a newer
    failure or block blocks, whichever copy holds it. A non-pass speaks for the subject when it is
    of this scope and names it (`id`) without naming another milestone or owner; a report of
    another milestone, owner or change is not about this one."""
    out = []
    # on a tie in time a non-pass comes first: the walk fails closed
    ordered = sorted(
        filter(None, map(_read, files)),
        key=lambda r: (r[0], not str(r[1].get("result", "")).startswith("VERIFY PASS")),
        reverse=True,
    )
    for _, data in ordered:
        if bound(data, scope, subject, number, owner):
            out.append((True, data))
        elif (
            data.get("scope", scope) == scope
            and not str(data.get("result", "")).startswith("VERIFY PASS")
            and data.get("id", subject) == subject
            and data.get("milestone", number) == number
            and not (owner is not None and data.get("owner", owner) != owner)
        ):
            out.append((False, data))
            break
    return out


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


def _section(text: str, name: str) -> str:
    """spec.py `section`: the body of a `##`-`####` heading, up to the next heading of its level or above."""
    m = re.search(rf"^(#{{2,4}})\s+{re.escape(name)}\b.*$", text, re.M | re.I)
    if not m:
        return ""
    rest = text[m.end() :]
    stop = re.search(rf"^#{{2,{len(m.group(1))}}}\s", rest, re.M)
    return rest[: stop.start()] if stop else rest


def tasks_lock(text: str) -> str:
    """What approval hashes of a tasks.md: the rows of its `## Tasks` and `## Milestones` tables without
    the State column (spec.py `lock_inputs`, the one reader; test_sdd_hooks keeps the two equal). A tick or
    a handover edit never moves it; renaming or emptying a section does."""
    keep = []
    for name in ("Tasks", "Milestones"):
        rows = [
            [c.strip() for c in ln.strip().strip("|").split("|")]
            for ln in _section(text, name).splitlines()
            if ln.strip().startswith("|")
        ]
        rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
        head = [h.lower() for h in rows[0]] if rows else []
        keep += ["|".join(v for k, v in dict(zip(head, r)).items() if k != "state") for r in rows[1:]]
    return "\n".join(keep)


def _text(repo: Path, entry: tuple[str, str] | None) -> str:
    return _git(repo, "cat-file", "blob", entry[0]).stdout.decode("utf-8", "replace") if entry else ""


def _only_ticks(repo: Path, old: tuple[str, str], new: tuple[str, str]) -> bool:
    """`new` differs from `old` only outside the locked rows of the change's own tasks.md, or in their State column."""
    return tasks_lock(_text(repo, old)) == tasks_lock(_text(repo, new))


ROUTING = ("size", "visualSource")  # the decisions.json fields the lock hashes (verify_gate.ROUTING; test_sdd_hooks)


def _routing(repo: Path, tree: dict[str, tuple[str, str]]) -> object:
    """verify_gate.routing: the routing fields, `state/intake.json` first; a missing or unreadable file is itself."""
    entry = tree.get("state/intake.json") or tree.get("decisions.json")
    if not entry:
        return {"missing": True}
    try:
        data = json.loads(_text(repo, entry))
    except ValueError:
        return {"unreadable": True}
    return {k: data.get(k) for k in ROUTING} if isinstance(data, dict) else {"unreadable": True}


def _plan_milestones(repo: Path, tree: dict[str, tuple[str, str]]) -> str:
    """verify_gate `section(plan.md, "Milestones")`: the layout 3 allocation the lock hashes."""
    m = re.search(r"^#{2,3} Milestones\s*$(.*?)(?=^#{1,3} |\Z)", _text(repo, tree.get("plan.md")), re.M | re.S)
    return m.group(1) if m else ""


def _lock_keys(repo: Path, tree: dict[str, tuple[str, str]]) -> set[str]:
    """The `criteria` keys the gated lock hashed: an older lock lacks plan.milestones and decisions.routing,
    which then stay free to edit, as the gate treats them."""
    try:
        data = json.loads(_text(repo, tree.get("state/lock.json") or tree.get("lock.json")))
    except ValueError:
        return set()
    criteria = data.get("criteria") if isinstance(data, dict) else None
    return set(criteria) if isinstance(criteria, dict) else set()


def app_locked(lock: object) -> bool:
    """The lock protects screens.json: it says `"visual": "app"` or hashed the file (chain-gate.sh reads the same rule)."""
    if not isinstance(lock, dict):
        return False
    criteria = lock.get("criteria")
    return lock.get("visual") == "app" or "screens.json" in (criteria if isinstance(criteria, dict) else {})


def _app_locked(repo: Path, tree: dict[str, tuple[str, str]]) -> bool:
    try:
        return app_locked(json.loads(_text(repo, tree.get("state/lock.json") or tree.get("lock.json"))))
    except (ValueError, TypeError):
        return False


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
    if any(not p.startswith((rel + "/", OUTCOMES)) for p in moved.decode("utf-8", "replace").split("\0") if p):
        return False
    before, after = _tree(repo, rel, gated), _tree(repo, rel, head)
    if before is None or after is None:
        return False
    changed = {k for k in before.keys() | after.keys() if (before.get(k) or ("",))[0] != (after.get(k) or ("",))[0]}
    for key in changed:  # `<change id>/<path inside it>`
        parts = key.split("/")
        if parts[-1] in EVIDENCE_FILES or EVIDENCE_DIRS & set(parts[1:-1]):  # first: evidence is never a task list
            return False
        if parts[-1] == "facts.md" and key in before and key in after and _only_archived_at(repo, before[key], after[key]):
            continue
        if len(parts) == 2 and parts[1] in TICKED_FILES and key in before and key in after and _only_ticks(repo, before[key], after[key]):
            continue
        if parts[-1] in LOCKED:
            return False
    for cid in {k.split("/", 1)[0] for k in changed}:  # what the lock hashes beyond the locked files
        mine = [{k.split("/", 1)[1]: v for k, v in tree.items() if k.startswith(cid + "/")} for tree in (before, after)]
        keys = _lock_keys(repo, mine[0])
        if "decisions.routing" in keys and _routing(repo, mine[0]) != _routing(repo, mine[1]):
            return False
        if _app_locked(repo, mine[0]) and any((mine[0].get(f) or ("",))[0] != (mine[1].get(f) or ("",))[0] for f in APP_LOCKED_FILES):
            return False
        if "plan.milestones" in keys and _plan_milestones(repo, mine[0]) != _plan_milestones(repo, mine[1]):
            return False
    return True
