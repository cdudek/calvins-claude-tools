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
"""

from __future__ import annotations

import argparse
import glob
import hashlib
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
        if status not in ("fixed", "match", "ruled-out", "waits-on-design-system") and not filled(
            row.get("accepted")
        ):
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
