"""Track owner notes and reference images against the build. stdlib only.

Usage: python3 scripts/marks.py init|check|table <change-id>
Run from the repo root. Output: init additions/orphans; check problems and a summary;
table a Markdown report. Written by `sdlc-run adopt`; edit the kit, not this copy.

marks.json holds {"rows": [...]}. Source paths and shots are change-relative; decision
paths are repo-relative. IDs use the session folder relative to asks, or ref:<image path>.
A fixed note names its proof in `test` (a tag such as @F1) found in a testGlobs file.
Init preserves existing rows and fields. Check inventories sources again, so missing,
duplicate, changed and orphaned rows cannot silently pass. This checks coverage, not pixels:
the reviewer must inspect each pair using the existing UX visual pass and ledger.
"""

from __future__ import annotations

import argparse
import glob
import html
import json
import re
import sys
from pathlib import Path

SECTION = re.compile(r"^## (\d{3}) · \d{2}:\d{2}[ \t]*$", re.M)
NOTE = re.compile(r"^(\d+)\. ([^\n]*(?:\n(?!\d+\. ).*)*)", re.M)
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif", ".bmp", ".tif", ".tiff"}
NOTE_STATUSES = {"fixed", "partly", "not-fixed", "contradicted", "ruled-out", "cant-see"}
REFERENCE_STATUSES = {"match", "differs"}
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
    for folder in (change / "asks", change / "spec" / "prototype"):
        for path in sorted(folder.rglob("*")):
            if (
                path.is_file()
                and path.suffix.lower() in IMAGES
                and path.resolve() not in mark_images
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


def init(change: Path, sources: list[dict]) -> int:
    path = change / "marks.json"
    rows = read_rows(path) if path.exists() else []
    by_id = {row["id"]: row for row in rows}
    added = 0
    for source in sources:
        if source["id"] not in by_id:
            rows.append(source | FILLED)
            added += 1
        else:
            for key, value in (source | FILLED).items():
                by_id[source["id"]].setdefault(key, value)
    source_ids = {row["id"] for row in sources}
    orphans = [row["id"] for row in rows if row["id"] not in source_ids]
    for orphan in orphans:
        print(f"{orphan}: orphan retained; source is missing")
    content = json.dumps({"rows": rows}, ensure_ascii=False, indent=2) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")
    print(f"MARKS INIT {change.name} added={added} rows={len(rows)} orphans={len(orphans)}")
    return 0


def check(change: Path, sources: list[dict], repo: Path, designs: Path, globs: list[str]) -> int:
    rows = read_rows(change / "marks.json")
    problems = []
    wanted = {row["id"]: row for row in sources}
    seen = set()
    specs = spec_text(repo, globs) if any(row.get("status") == "fixed" for row in rows) else ""
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
        if status not in ("fixed", "match", "ruled-out") and not filled(row.get("accepted")):
            problem("unresolved status; needs the engineer's accepted words")
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
        if filled(row.get("accepted")):
            status += f" (accepted: {row['accepted']})"
        values = [
            row["id"],
            row.get("words", row.get("image")),
            row.get("decision"),
            row.get("shot"),
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
