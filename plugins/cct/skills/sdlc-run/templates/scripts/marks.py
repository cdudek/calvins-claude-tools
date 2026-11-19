"""Track owner notes and reference images against the build. stdlib only.

Usage: python3 scripts/marks.py init|check|table <change-id>
Run from the repo root. Output: init additions/orphans; check problems and a summary;
table a Markdown report. Written by `sdlc-run adopt`; edit the kit, not this copy.

A design export bundle (a folder under asks/ with an index.html, or the folder decisions.json
names as visualSource.path) is one row, kind bundle, with the hash of every file in it. It is
never edited: a changed hash fails the check. Its row says "needs rendering" until `rendered`
names a separate folder under asks/ holding at least one image per screen, matched by name
(`<screen>.png`, `<screen>--desktop@2x.png`); those images are then inventoried as reference rows
like any other. Generated mockups (spec/prototype) are advisory and never rows.

`init` migrates a ledger written before these rules: a `ref:spec/prototype/...` row moves to
`retired` (advisory now; the whole row is kept), and a `ref:` row for an image inside a bundle is
folded into the bundle row's `folded` list with its owner decisions. Neither is an orphan.

marks.json holds {"rows": [...]}. Source paths and shots are change-relative; decision
paths are repo-relative. IDs use the session folder relative to asks, or ref:<image path>.
A fixed note names its proof in `test` (a tag such as @F1) found in a testGlobs file.
Init preserves existing rows and fields. Check inventories sources again, so missing,
duplicate, changed and orphaned rows cannot silently pass. This checks coverage, not pixels:
the reviewer must inspect each pair using the existing UX visual pass and ledger.

Captures have one owner: verify/shots/manifest.json, {"entries": [{shot, build, reference,
screen, state, width, zoom}], "qa": {"build": <sha>}}. `build` is the commit captured, `reference`
the sha256 of the reference image. When the file exists, check refuses a shot that is not in it,
one cell (screen, state, width, zoom) captured twice, a capture or `qa.md` whose build differs
from HEAD in any file outside the changes folder, and a reference whose bytes changed since
capture, so a stale capture is invalidated by its inputs, never reused because it exists.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SECTION = re.compile(r"^## (\d{3}) · \d{2}:\d{2}[ \t]*$", re.M)
NOTE = re.compile(r"^(\d+)\. ([^\n]*(?:\n(?!\d+\. ).*)*)", re.M)
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif", ".bmp", ".tif", ".tiff"}
NOTE_STATUSES = {"fixed", "partly", "not-fixed", "contradicted", "ruled-out", "cant-see"}
# waits-on-design-system: done in the app, only a design-system part is missing; not a failure.
REFERENCE_STATUSES = {"match", "differs", "waits-on-design-system"}
FILLED = {
    "decision": None,
    "expected": "",
    "shot": "",
    "status": None,
    "differs": "",
    "accepted": "",
    "test": "",
}
TEST_GLOBS = ["**/*.test.*", "**/*.spec.*", "**/test_*.py", "**/tests/**", "**/e2e/**"]
SKIP = ("node_modules", ".git", ".worktrees")
BUNDLE_FILLED = {"rendered": ""}

# One grammar for a finding id, shared by the producer (findings.md items, marks rows) and the parser.
FINDING_ID = r"[A-Z]\d+"
ASKED = re.compile(r"\AChange (\S+), finding (\S+): ")  # "Change <id>, finding B2: ..."
# The fixed options of an owner dialog; the selected label is the decision.
OWNER_LABELS = {
    "fix it now": "fix",
    "accept as is": "accepted",
    "block the close": "blocked",
    "accept milestone": "accepted",
    "hold": "hold",
    "skip visual evidence": "skip",
    "run visual evidence": "run",
}
DEFER = re.compile(r"defer to milestone (\d+)", re.I)


def when(text: object) -> dt.datetime | None:
    try:
        stamp = dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=dt.timezone.utc)  # noqa: UP017 -- macOS python3 3.9


def transcript_dirs(repo: Path) -> list[Path]:
    """Claude Code's project folders for this repo: its working tree and the main checkout it
    belongs to (a worktree has its own folder, and the owner may have spoken in either). A folder
    is read only if neither it nor a parent is a link (a link could point at a folder the agent
    wrote) and it is ours."""
    roots = {repo.resolve()}
    common = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if common.endswith("/.git"):
        roots.add(Path(common).parent.resolve())
    found = []
    for root in sorted(roots):
        base = Path.home() / ".claude/projects" / re.sub(r"[^A-Za-z0-9]", "-", str(root))
        if base.is_dir() and not any(p.is_symlink() for p in (base, base.parent, base.parent.parent)):
            found.append(base)
    return found


def first_seen(repo: Path, record: Path, needle: str) -> dt.datetime | None:
    """When the current incarnation of `needle` began in `record`: the newest commit that took it
    from absent to present, else the file's mtime (an uncommitted or untracked finding). An id that
    was removed and reused later is a new finding: an answer to the old one is older than this."""
    rel = record.resolve().relative_to(repo.resolve()).as_posix() if record.exists() else str(record)

    def has(rev: str) -> bool:
        out = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{rel}"], capture_output=True, text=True)
        return out.returncode == 0 and needle in out.stdout

    worktree = record.exists() and needle in record.read_text(encoding="utf-8", errors="ignore")
    if worktree and not has("HEAD"):
        return dt.datetime.fromtimestamp(record.stat().st_mtime, dt.timezone.utc)  # noqa: UP017
    log = subprocess.run(
        ["git", "-C", str(repo), "log", f"-S{needle}", "--format=%H %cI", "--", rel],
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    for line in log:  # newest first
        sha, _, stamp = line.partition(" ")
        if has(sha) and not has(f"{sha}^"):
            return when(stamp)
    if record.exists():
        return dt.datetime.fromtimestamp(record.stat().st_mtime, dt.timezone.utc)  # noqa: UP017
    return None


_ANSWERS: dict[tuple[str, str], list[tuple[str, tuple[str, str], dt.datetime]]] = {}


def change_born(repo: Path, change_id: str) -> dt.datetime | None:
    """When the change folder came to exist: its first commit, else the folder's mtime. No session
    file last written before then can hold an answer about it."""
    try:
        changes = json.loads((repo / "sdlc.json").read_text(encoding="utf-8")).get("changesDir", "changes")
    except (OSError, ValueError, AttributeError):
        changes = "changes"
    folder = repo / changes / change_id
    first = subprocess.run(
        ["git", "-C", str(repo), "log", "--reverse", "--format=%cI", "--", f"{changes}/{change_id}"],
        capture_output=True,
        text=True,
    ).stdout.split()
    if first:
        return when(first[0])
    if folder.exists():
        return dt.datetime.fromtimestamp(folder.stat().st_mtime, dt.timezone.utc)  # noqa: UP017
    return None


def answers(repo: Path, change_id: str) -> list[tuple[str, tuple[str, str], dt.datetime]]:
    """Every owner answer about `change_id` in the transcripts, as (finding id, kind, time), parsed
    once per process and only from sessions written since the change folder was born."""
    key = (str(repo.resolve()), change_id)
    if key in _ANSWERS:
        return _ANSWERS[key]
    out: list[tuple[str, tuple[str, str], dt.datetime]] = []
    born = change_born(repo, change_id)
    for base in transcript_dirs(repo):
        for path in sorted(base.glob("*.jsonl")):
            try:
                info = path.stat()
                if path.is_symlink() or info.st_uid != os.getuid():
                    continue
                if born and dt.datetime.fromtimestamp(info.st_mtime, dt.timezone.utc) < born:  # noqa: UP017
                    continue
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, ValueError):
                continue
            out += _answers_in(lines, change_id)
    _ANSWERS[key] = out
    return out


def _label(label: object) -> str:
    """The option's meaning: lowercase, without a trailing `(Recommended)` the skill adds."""
    return re.sub(r"\s*\(recommended\)\s*$", "", str(label).strip(), flags=re.I).lower()


def _answers_in(lines: list[str], change_id: str) -> list[tuple[str, tuple[str, str], dt.datetime]]:
    out = []
    asked: dict[str, dict[str, list]] = {}
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("message") if isinstance(entry, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list) or entry.get("isSidechain"):
            continue
        blocks = [b for b in content if isinstance(b, dict)]
        if entry.get("type") == "assistant":
            for b in blocks:
                if b.get("type") == "tool_use" and b.get("name") == "AskUserQuestion":
                    qs = (b.get("input") or {}).get("questions")
                    asked[str(b.get("id"))] = {
                        q["question"]: [o.get("label") for o in q.get("options") or [] if isinstance(o, dict)]
                        for q in qs or []
                        if isinstance(q, dict) and isinstance(q.get("question"), str)
                    }
            continue
        result = entry.get("toolUseResult")
        given = result.get("answers") if isinstance(result, dict) else None
        stamp = when(entry.get("timestamp"))
        if entry.get("type") != "user" or not isinstance(given, dict) or not stamp:
            continue
        for b in blocks:
            options = asked.get(str(b.get("tool_use_id")))
            if b.get("type") != "tool_result" or b.get("is_error") or options is None:
                continue
            for question, label in given.items():
                m = ASKED.match(question) if isinstance(question, str) else None
                if not m or m[1] != change_id or label not in options.get(question, []):
                    continue
                name = _label(label)
                defer = DEFER.fullmatch(name)
                kind = ("deferred", defer[1]) if defer else (OWNER_LABELS.get(name), "")
                if kind[0]:
                    out.append((m[2], kind, stamp))
    return out


def owner_decisions(
    repo: Path, change_id: str, record: Path | None = None, needle: str = "{}", with_time: bool = False
) -> dict[str, tuple]:
    """finding id -> (kind, detail) from the owner's answers to AskUserQuestion dialogs whose
    question starts `Change <change id>, finding <id>: ` and whose options include the selected
    label (a trailing `(Recommended)` is ignored). kind is fix | accepted | deferred (detail: the milestone) | blocked | hold. Only the
    structured tool result counts: typed text, an agent message or a subagent never does. The
    latest answer wins; an answer older than the finding's first appearance in `record` is ignored
    (`needle` formats the id into the text searched for). No readable transcript gives {}.
    Threat model: protects against a careless agent settling its own finding, not against someone
    with a shell; the transcript folder is read from the calling process's home."""
    found: dict[str, tuple[tuple[dt.datetime, int], tuple[str, str]]] = {}
    seen: dict[str, dt.datetime | None] = {}
    for order, (fid, kind, stamp) in enumerate(answers(repo, change_id)):
        if record is not None and fid not in seen:
            seen[fid] = first_seen(repo, record, needle.format(fid))
        if record is not None and (seen[fid] is None or stamp < seen[fid]):
            continue  # said before this incarnation of the finding existed
        if fid not in found or (stamp, order) > found[fid][0]:
            found[fid] = ((stamp, order), kind)
    if with_time:  # (kind, detail, when it was answered)
        return {fid: (*kind, stamp) for fid, ((stamp, _), kind) in found.items()}
    return {fid: kind for fid, (_, kind) in found.items()}


def bundles(change: Path) -> dict[Path, str]:
    """Export bundle folders under asks/, with their hash: any folder holding index.html, plus
    the folder decisions.json names as visualSource.path (a React export has no index.html)."""
    folders = {index.parent for index in (change / "asks").rglob("index.html")}
    try:
        declared = json.loads((change / "decisions.json").read_text(encoding="utf-8"))
        path = (change / declared["visualSource"]["path"]).resolve()
        if path.is_dir() and path.is_relative_to((change / "asks").resolve()):
            folders.add(path)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass  # no decisions.json, no visualSource, or a URL: nothing declared
    found = {}
    for folder in sorted(folders):
        if any(parent in found for parent in folder.parents):
            continue
        digest = hashlib.sha256()
        for path in sorted(p for p in folder.rglob("*") if p.is_file()):
            parts = path.relative_to(folder).parts  # the repo itself may sit under .worktrees
            if path.name == ".DS_Store" or any(part in SKIP for part in parts):
                continue
            digest.update(path.relative_to(folder).as_posix().encode() + b"\0")
            digest.update(path.read_bytes() + b"\0")
        found[folder] = digest.hexdigest()
    return found


def sessions(change: Path) -> list[tuple[Path, str]]:
    """Only Snapmark-shaped session.md files, not unrelated session notes."""
    found = []
    for path in sorted((change / "asks").rglob("session.md")):
        text = path.read_text(encoding="utf-8")
        if re.match(r"\A# [^\n]+\n", text) and SECTION.search(text):
            found.append((path, text))
    return found


def inventory(change: Path) -> list[dict]:
    rows = []
    mark_images = set()
    for path, text in sessions(change):
        folder = path.parent.relative_to(change).as_posix()
        session_id = path.parent.relative_to(change / "asks").as_posix()
        sections = list(SECTION.finditer(text))
        for i, section in enumerate(sections):
            body = text[
                section.end() : sections[i + 1].start() if i + 1 < len(sections) else len(text)
            ]
            mark = section.group(1)
            image = IMAGE.search(body)
            source = path.parent / (image.group(1) if image else f"img/{mark}.png")
            mark_images.add(source.resolve())
            for note in NOTE.finditer(body):
                rows.append(
                    {
                        "id": f"{session_id}/{mark}.{note.group(1)}",
                        "kind": "note",
                        "session": folder,
                        "mark": mark,
                        "note": int(note.group(1)),
                        "words": note.group(2).rstrip("\n"),
                        "image": source.relative_to(change).as_posix(),
                    }
                )
    found = bundles(change)
    for folder, digest in found.items():
        rel = folder.relative_to(change).as_posix()
        rows.append({"id": f"bundle:{rel}", "kind": "bundle", "path": rel, "hash": digest})
    # Generated mockups (spec/prototype) are advisory: only what the owner supplied is a reference.
    for path in sorted((change / "asks").rglob("*")):
        if (
            path.is_file()
            and path.suffix.lower() in IMAGES
            and path.resolve() not in mark_images
            and not any(b in path.parents for b in found)
        ):
            image = path.relative_to(change).as_posix()
            rows.append({"id": f"ref:{image}", "kind": "reference", "image": image})
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate source IDs: check session mark and note numbers")
    return rows


def read_rows(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise ValueError("marks.json must contain a rows array")
    rows = data["rows"]
    if any(not isinstance(row, dict) or not filled(row.get("id")) for row in rows):
        raise ValueError("every row needs a non-empty string id")
    return rows


def filled(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def inside_file(base: Path, value: object, boundary: Path) -> bool:
    if not filled(value) or Path(value).is_absolute():
        return False
    path = (base / value).resolve()
    return path.is_relative_to(boundary.resolve()) and path.is_file()


def inside_dir(boundary: Path, path: Path) -> bool:
    return path.resolve().is_relative_to(boundary.resolve())


def spec_text(repo: Path, globs: list[str]) -> str:
    """All spec and test file text. shortcut: reads every match once, fine below ~10k files."""
    root = str(repo)
    names = set()
    for pattern in globs:
        for p in (pattern, pattern + "/*" if pattern.endswith("/**") else pattern):
            names.update(glob.glob(p, root_dir=root, recursive=True))
    parts = []
    for name in sorted(names):
        path = repo / name
        if path.is_file() and not any(part in SKIP for part in path.relative_to(repo).parts):
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def shot_screen(image: Path) -> str:
    """The screen a rendered image shows: render.sh puts <screen>--<viewport>@2x.png in a shots/
    folder beside the screen, so the folder (minus shots/) plus the name before that suffix. Only the renderer's own
    `--<viewport>@2x` comes off: home--compact.html is home--compact--desktop@2x.png, not `home`."""
    name = re.sub(r"--(?:desktop|mobile|zoom150)@2x$", "", image.stem)
    return "/".join([*(part for part in image.parent.parts if part != "shots"), name])


def extra(source: dict) -> dict:
    return BUNDLE_FILLED if source["kind"] == "bundle" else FILLED


def migrate(
    rows: list[dict], retired: list[dict], bundles_: dict[str, dict], change: Path
) -> list[dict]:
    """Rows of the two categories earlier versions inventoried and this one does not: generated
    mockups retire as advisory, images inside a bundle fold into its row. Evidence stays. A row
    folds only for an image that is still on disk: a deleted one stays a (failing) orphan row."""
    kept = []
    for row in rows:
        image = row["id"][4:] if row["id"].startswith("ref:") else None
        owner = next(
            (
                b
                for p, b in bundles_.items()
                if image and image.startswith(p + "/") and (change / image).is_file()
            ),
            None,
        )
        if image is not None and image.startswith("spec/prototype/"):
            retired.append(row)
            print(f"{row['id']}: retired as advisory; the row is kept under retired")
        elif owner is not None:
            owner.setdefault("folded", []).append(row)
            print(f"{row['id']}: folded into {owner['id']}")
        else:
            kept.append(row)
    return kept


def init(change: Path, sources: list[dict]) -> int:
    path = change / "marks.json"
    rows = read_rows(path) if path.exists() else []
    retired = json.loads(path.read_text(encoding="utf-8")).get("retired", []) if path.exists() else []
    by_id = {row["id"]: row for row in rows}
    wanted = {row["id"] for row in sources}
    added = 0
    for source in sources:
        if source["id"] not in by_id:
            rows.append(source | extra(source))
            by_id[source["id"]] = rows[-1]
            added += 1
        else:
            for key, value in (source | extra(source)).items():
                by_id[source["id"]].setdefault(key, value)
    stale = [r for r in rows if r["id"] not in wanted]
    folds = {s["path"]: by_id[s["id"]] for s in sources if s["kind"] == "bundle"}
    orphaned = migrate(stale, retired, folds, change)
    rows = [row for row in rows if row["id"] in wanted or row in orphaned]
    orphans = [row["id"] for row in rows if row["id"] not in wanted]
    for orphan in orphans:
        print(f"{orphan}: orphan retained; source is missing")
    data = {"rows": rows, **({"retired": retired} if retired else {})}
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")
    print(f"MARKS INIT {change.name} added={added} rows={len(rows)} orphans={len(orphans)}")
    return 0


def stale_build(
    repo: Path, change: Path, build: object, paths: list[str] | None = None, strict: bool = False
) -> str:
    """Why a capture of commit `build` no longer describes HEAD, or "" when it still does: only
    records under the changes folder may differ. With `paths` (the cell's own sources plus the
    shared dependencies) only a change to one of those files, or under one of those folders,
    makes it stale. `strict` also demands a full commit sha, never a moving ref."""
    if not filled(build):
        return "no build commit recorded"
    if strict and not re.fullmatch(r"[0-9a-f]{40}", str(build)):
        return f"build must be a full commit sha, not {build!r}"
    known = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-t", f"{build}^{{commit}}"], capture_output=True, text=True
    )
    if known.returncode or known.stdout.strip() != "commit":
        return f"build {str(build)[:12]} is not a commit here"
    records = change.parent.relative_to(repo.resolve()).as_posix()
    done = subprocess.run(
        ["git", "-C", str(repo), "diff", "-z", "--name-only", build, "HEAD", "--", ".", f":!{records}"],
        capture_output=True,
        text=True,
    )
    if done.returncode:
        return f"build {str(build)[:12]} is not a commit here"
    files = [f for f in done.stdout.split("\0") if f]  # -z: a name may hold spaces
    if paths is not None:
        roots = [p.rstrip("/") for p in paths]
        files = [f for f in files if any(f == r or f.startswith(r + "/") for r in roots)]
    return f"{files[0]} changed since build {str(build)[:12]}" if files else ""


def manifest_required(change: Path) -> bool:
    """A change approved from 3.21.0 has `"manifest": "required"` in its lock; older changes keep
    the behaviour in which an absent manifest is fine. Fails closed: a lock.json that exists but
    cannot be read as an object is treated as strict, never as legacy. (Editing a lock after
    approval is refused by chain-gate.sh, and the gate compares its hashes.)"""
    path = change / "lock.json"
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True
    return not isinstance(data, dict) or data.get("manifest") == "required"


def qa_problems(change: Path, repo: Path, visual: bool) -> list[str]:
    """`<spec>/qa.md` verified by its own recorded `Build: <sha>`, never by manifest metadata. It is
    required when the change has visual rows or a spec folder (marks.json is editable, the spec
    folder is not derived from it); and whenever it exists its build must be fresh."""
    qa = change / "spec" / "qa.md"
    if not qa.is_file():
        if visual or (change / "spec").is_dir():
            return ["qa.md is missing: build QA has not been recorded for this change"]
        return []
    text = qa.read_text(encoding="utf-8")
    builds = [m[1] for m in re.finditer(r"^Build:\s*`?(\S+?)`?\s*$", text, re.M | re.I)]
    rows: list[list[str]] = []
    for line in text.splitlines():  # the first table only (the header table), never the coverage matrix
        if line.lstrip().startswith("|"):
            rows.append([c.strip(" `") for c in line.strip().strip("|").split("|")])
        elif rows:
            break
    head = [c.lower() for c in rows[0]] if rows else []
    if "build commit" in head:  # the build QA template's table: one commit column
        at = head.index("build commit")
        builds += [r[at] for r in rows[1:] if len(r) > at and re.fullmatch(r"[0-9A-Za-z]{7,40}", r[at])]
    if not builds:
        return ["qa.md records no `Build: <sha>` line or `Build commit` column, so its inputs cannot be checked"]
    for build in dict.fromkeys(builds):
        if why := stale_build(repo, change, build, strict=True):
            return [f"qa.md is stale: {why}"]
    return []


def canonical_source(repo: Path, source: object) -> str | None:
    """The canonical repo path of a declared source, or None. Plain only: relative, no `.`, `..` or
    empty component, no glob or pathspec syntax (`* ? [ ] \\`, a leading `:`), no edge whitespace.
    It must name a file or folder tracked at HEAD, matched literally, so a narrowed staleness
    check can never watch nothing or something else."""
    if not isinstance(source, str) or not source or source != source.strip():
        return None
    if Path(source).is_absolute() or source[0] == ":" or any(c in source for c in "*?[]\\"):
        return None
    parts = source.rstrip("/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        return None
    path = "/".join(parts)
    listed = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", "HEAD", "--", f":(literal){path}"],
        capture_output=True,
        text=True,
    )
    return path if listed.returncode == 0 and listed.stdout.strip() else None


ZOOMS = (100, 150)  # the build QA looks at every state at 100 and 150 percent


def matrix_problems(entries: list[dict]) -> list[str]:
    """The required capture matrix: every entry names its screen, state, width and zoom, and each
    screen-state-width it shows has a capture at every zoom of ZOOMS."""
    problems = []
    for e in entries:
        missing = [k for k in ("screen", "state", "width", "zoom") if e.get(k) in (None, "")]
        if missing:
            problems.append(f"capture {e.get('shot')}: cell lacks {', '.join(missing)}")
    seen: dict[tuple, set] = {}
    for e in entries:
        if all(e.get(k) not in (None, "") for k in ("screen", "state", "width", "zoom")):
            seen.setdefault((e["screen"], e["state"], e["width"]), set()).add(str(e["zoom"]).rstrip("%"))
    for cell, zooms in sorted(seen.items(), key=str):
        gone = [z for z in ZOOMS if str(z) not in zooms]
        if gone:
            problems.append(f"capture matrix: {cell} lacks zoom {', '.join(map(str, gone))}")
    return problems


def manifest_problems(change: Path, rows: list[dict], repo: Path) -> list[str]:
    """Problems with verify/shots/manifest.json against the rows. An absent file is a problem only
    when the lock requires one (3.21.0) and rows hold visual work; the strict rules (commit sha,
    reference digest, per-cell sources, a real qa.md) apply to those changes only."""
    path = change / "verify/shots/manifest.json"
    strict = manifest_required(change)
    visual = any(filled(r.get("shot")) for r in rows) or any(
        r.get("kind") in ("reference", "bundle") for r in rows
    )
    problems = qa_problems(change, repo, visual) if strict else []  # whether or not a manifest exists
    if not path.exists():
        if strict and visual:
            problems.append("capture manifest is required (verify/shots/manifest.json): no capture is recorded")
        return problems
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = [e for e in data["entries"] if isinstance(e, dict)]
    except (OSError, ValueError, KeyError, TypeError):
        return problems + ["capture manifest: unreadable; it needs an entries list"]
    cells = [(e.get("screen"), e.get("state"), e.get("width"), e.get("zoom")) for e in entries]
    problems += [f"capture manifest: cell {c} captured twice" for c in sorted(set(
        c for c in cells if cells.count(c) > 1), key=str)]  # fmt: skip
    shared = data.get("shared") if isinstance(data.get("shared"), list) else []
    if strict:
        problems += matrix_problems(entries)
        problems += [
            f"capture manifest: shared dependency {x!r} is not a plain repo path tracked at HEAD"
            for x in shared
            if canonical_source(repo, x) is None
        ]
    for entry in entries:
        mine = entry.get("sources")
        paths = None
        if strict:
            if not (isinstance(mine, list) and mine and all(filled(x) for x in mine)):
                problems.append(f"capture {entry.get('shot')}: must list the source files of its screen")
            else:
                canon = [canonical_source(repo, x) for x in mine]
                problems += [
                    f"capture {entry.get('shot')}: source {x!r} is not a plain repo path tracked at HEAD"
                    for x, c in zip(mine, canon)
                    if c is None
                ]
                # only canonical, tracked paths narrow the check; a bad one fails the cell above
                paths = [c for c in canon if c] + [
                    c for x in shared if (c := canonical_source(repo, x))
                ]
            ref = entry.get("reference")
            if not (isinstance(ref, str) and re.fullmatch(r"[0-9a-f]{64}", ref)):
                problems.append(f"capture {entry.get('shot')}: reference digest is required (sha256)")
        if why := stale_build(repo, change, entry.get("build"), paths, strict):
            problems.append(f"capture {entry.get('shot')}: stale: {why}")
    if not strict:
        qa = data.get("qa")
        if isinstance(qa, dict) and (why := stale_build(repo, change, qa.get("build"))):
            problems.append(f"qa.md is stale: {why}")
    for row in rows:
        shot = row.get("shot")
        if not filled(shot):
            continue
        mine = [e for e in entries if e.get("shot") == shot]
        if not mine:
            problems.append(f"{row['id']}: shot {shot} is not in the capture manifest")
            continue
        image = row.get("image")
        if filled(image) and (change / image).is_file():
            digest = hashlib.sha256((change / image).read_bytes()).hexdigest()
            known = [e["reference"] for e in mine if filled(e.get("reference"))]
            if known and digest not in known:
                problems.append(f"{row['id']}: reference changed since capture; capture again")
    return problems


def check(change: Path, sources: list[dict], repo: Path, designs: Path, globs: list[str]) -> int:
    rows = read_rows(change / "marks.json")
    problems = []
    wanted = {row["id"]: row for row in sources}
    seen = set()
    specs = spec_text(repo, globs) if any(row.get("status") == "fixed" for row in rows) else ""
    owners: dict[str, tuple[str, str]] | None = None
    for row in rows:
        rid = row["id"]

        def problem(message: str, rid: str = rid) -> None:
            problems.append(f"{rid}: {message}")

        if rid in seen:
            problem("duplicate row")
        seen.add(rid)
        source = wanted.get(rid)
        if source is None:
            problem("orphan row: source is missing")
        elif any(row.get(key) != value for key, value in source.items()):
            problem("source fields differ; restore the original words and source paths")
        kind = source["kind"] if source else row.get("kind")
        if kind == "bundle":
            rendered = row.get("rendered")
            if not filled(rendered) or not (change / rendered).is_dir():
                problem(
                    "needs rendering: render the bundle to images in a folder under asks/ "
                    "and set rendered to it"
                )
            elif not inside_dir(change / "asks", change / rendered):
                problem("rendered must be a folder under asks/")
            elif source and (
                inside_dir(change / source["path"], change / rendered)
                or inside_dir(change / rendered, change / source["path"])
            ):
                problem("rendered must be separate from the bundle (render a copy, not the bundle)")
            elif source:
                # a screen is its path in the bundle without the extension: settings/index is not index
                screens = sorted(
                    {
                        h.relative_to(change / source["path"]).with_suffix("").as_posix()
                        for h in (change / source["path"]).rglob("*.html")
                        if h.name != "gallery.html"
                    }
                )
                images = {
                    shot_screen(p.relative_to(change / rendered))
                    for p in (change / rendered).rglob("*")
                    if p.is_file() and p.suffix.lower() in IMAGES
                }
                lacking = [name for name in screens if name not in images]
                if lacking or not images:
                    problem(f"rendered has no image for screen: {', '.join(lacking) or 'any'}")
            continue
        statuses = NOTE_STATUSES if kind == "note" else REFERENCE_STATUSES
        if kind not in ("note", "reference"):
            problem("invalid kind")
        status = row.get("status")
        if (
            status is not None
            and status != ""
            and (not isinstance(status, str) or status not in statuses)
        ):
            problem("invalid status")
        if status == "waits-on-design-system" and not filled(row.get("differs")):
            problem("waits-on-design-system must name the missing design-system parts in differs")
        if status not in ("fixed", "match", "ruled-out", "waits-on-design-system"):
            if owners is None:
                owners = owner_decisions(repo, change.name, change / "marks.json")
            if owners.get(rid, ("",))[0] not in ("accepted", "deferred"):
                problem(
                    "unresolved status; needs the owner's Accept as is or Defer to milestone <n> "
                    f"answer to a dialog starting 'Change {change.name}, finding {rid}: '"
                )
        if status != "ruled-out":
            if not filled(row.get("expected")):
                problem("expected is required")
            if not inside_file(change, row.get("shot"), change):
                problem("shot must be an existing file inside the change folder")
        decision = row.get("decision")
        if status == "ruled-out" or decision is not None:
            if not inside_file(repo, decision, designs):
                problem("decision must be an existing file under designsDir")
        if status == "fixed":
            tag = row.get("test")
            if not filled(tag) or not tag.startswith("@"):
                problem("fixed needs a test tag (@F<n>) that proves it; none named")
            elif not re.search(re.escape(tag.strip()) + r"(?!\w)", specs):
                problem(f"test tag {tag} appears in no spec or test file")
        if status in ("fixed", "match") and row.get("differs") not in (None, ""):
            problem("fixed/match must have no differs")
    problems += manifest_problems(change, rows, repo)
    for rid in wanted.keys() - seen:
        problems.append(f"{rid}: missing row; run marks.py init {change.name}")
    for problem in sorted(problems):
        print(problem)
    print(
        f"MARKS {'FAIL' if problems else 'PASS'} {change.name} "
        f"rows={len(rows)} problems={len(problems)}"
    )
    return int(bool(problems))


def table(rows: list[dict]) -> int:
    def cell(value: object) -> str:
        # Render owner text literally, including backticks, quotes, pipes and newlines.
        text = html.escape(str(value) if value is not None else "", quote=False)
        text = re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", text)
        return text.replace("\n", "<br>")

    print("| mark | words | decision | shot | status | test | still differs |")
    print("|---|---|---|---|---|---|---|")
    for row in rows:
        status = row.get("status") or "unset"
        if row.get("kind") == "bundle":
            status = "rendered" if filled(row.get("rendered")) else "needs rendering"
        if filled(row.get("accepted")):
            status += f" (accepted: {row['accepted']})"
        values = [
            row["id"],
            row.get("words", row.get("image", row.get("path"))),
            row.get("decision"),
            row.get("shot", row.get("rendered")),
            status,
            row.get("test"),
            row.get("differs"),
        ]
        print("| " + " | ".join(cell(value) for value in values) + " |")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("init", "check", "table"))
    parser.add_argument("id")
    args = parser.parse_args(argv[1:])
    try:
        repo = Path.cwd()
        cfg = json.loads((repo / "sdlc.json").read_text(encoding="utf-8"))
        changes = (repo / cfg.get("changesDir", "changes")).resolve()
        change = (changes / args.id).resolve()
        if not change.is_relative_to(changes) or change == changes or not change.is_dir():
            raise ValueError("no change folder inside changesDir")
        if args.mode == "table":
            return table(read_rows(change / "marks.json"))
        sources = inventory(change)
        if args.mode == "init":
            return init(change, sources)
        designs = repo / cfg.get("designsDir", "docs/designs")
        return check(change, sources, repo, designs, cfg.get("testGlobs", TEST_GLOBS))
    except (OSError, ValueError) as exc:
        print(f"marks: {str(exc).replace(chr(10), ' ')}")
        print(f"MARKS FAIL {args.id} problems=1")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
