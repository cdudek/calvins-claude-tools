"""Install the SDLC chain into the current repo from sdlc.json.

    python3 adopt.py [--dry-run] [--upgrade] [--apply --replace FILE] [--preset node|python] [--ticket KEY-123] [--tiers yes|no]
    python3 adopt.py --templates-hash        # what sdlc.json `kitTemplates` should say

`--upgrade` is for a repo that already runs the chain, and it never overwrites or moves anything:
it adds the missing sdlc.json keys with the stack's defaults (never changing a value), stamps
`sdlcVersion`, and lists every file that differs from the kit's copy as `review diff` in MANUAL.
`--upgrade --replace FILE` shows the diff of one kit-owned file; add `--apply` to replace it.
`--dry-run` writes nothing at all. A plain `adopt` stamps too and still refreshes the copies.

`--tiers` writes the engineer's answer to "Use Ship/Show/Ask?" into sdlc.json `tiers`; the
skill asks it on every adopt. Without the flag, a set `tiers` stays and a missing one means
TIERS_DEFAULT.

Idempotent: generated files (hooks, workflows, tiers classifier, CODEOWNERS, docs, test)
are rewritten from the templates every run; files the repo owns (sdlc.json, tiers.json,
REVIEW.md, settings.json content outside the SDLC hooks, CLAUDE.md, the "Repo-specific"
tail of docs/sdlc.md, anything listed in sdlc.json `keep`) are created once and then
kept. Migrates a `goals/` tree and `.claude/plans/` when it finds them. Adds a missing
`verifyStop` from the preset and rewrites a whole-suite E2E `--repeat-each` in
`checks.milestone` to the preset's form, listing the open changes that must be re-approved.
stdlib only.

Output ends with three sections: WROTE, KEPT, MANUAL -- the skill relays MANUAL to the user.

v3 keys are pass-through repo policy. `verifyStop`, `planGate`, `testGlobs`, `prototypeDirs`,
`feedback`, `milestones`, `hotfix`, `checks`, `goal`, `languages`, `responsiveTier`, `ux` and
`protected` are read when present. Existing repos keep their values, and adopt does not add
missing optional keys unless the selected preset already contains them.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
TPL = SKILL / "templates"
ROOT = Path.cwd()
if "--help" in sys.argv or "-h" in sys.argv:
    print(__doc__)
    sys.exit(0)


def templates_hash() -> str:
    """Fingerprint of everything `adopt` copies into a repo. `sdlc.json` records it, so
    `status.sh` can tell a repo whose copies predate the installed kit -- the copies run in
    CI, where no plugin is installed, so they cannot read the skill at runtime."""
    h = hashlib.sha256()
    # Bytecode is not a template: adopt imports design_index.py from TPL, and the
    # __pycache__ it may leave would otherwise mark every repo stale on that laptop.
    for f in sorted(p for p in TPL.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(str(f.relative_to(TPL)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:12]


if "--templates-hash" in sys.argv:
    print(templates_hash())
    sys.exit(0)
DRY_RUN = "--dry-run" in sys.argv
# `--upgrade` never overwrites or moves anything. It runs the whole flow as a dry run to learn which
# files differ from the kit's copies, writes only sdlc.json (missing keys, the version stamp) and
# lists the rest for review. `--apply --replace <file>` replaces one kit-owned file, diff shown.
UPGRADE = "--upgrade" in sys.argv
APPLY = "--apply" in sys.argv
REPLACE = [a for a in (sys.argv[i + 1 : i + 2] for i, v in enumerate(sys.argv) if v == "--replace")]
REPLACE = [r[0] for r in REPLACE if r]
DRY = DRY_RUN or UPGRADE
pending: dict[str, tuple[str, bool]] = {}  # file -> (the kit's text, executable) where it differs
# Ship/Show/Ask when sdlc.json has no `tiers` and adopt got no --tiers. The skill's question
# recommends the same value.
TIERS_DEFAULT = False
wrote: list[str] = []
written: list[Path] = []
kept: list[str] = []
manual: list[str] = []

# --- sdlc.json ---------------------------------------------------------------------------


def detect_preset() -> str:
    if "--preset" in sys.argv:
        return sys.argv[sys.argv.index("--preset") + 1]
    if (ROOT / "package.json").exists():
        return "node"
    if (ROOT / "pyproject.toml").exists():
        return "python"
    sys.exit(
        "cannot detect a preset (no package.json, no pyproject.toml); pass --preset node|python"
    )


def default_branch() -> str:
    # origin/HEAD exists only after `git clone`; a repo pushed with `gh repo create --push` or
    # `git remote add` lacks it, so ask the remote before falling back.
    for cmd in (
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        ["git", "ls-remote", "--symref", "origin", "HEAD"],
    ):
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
        m = re.search(r"refs/(?:remotes/origin|heads)/(\S+)", out)
        if m:
            return m.group(1)
    return "master"


def git_email() -> str:
    try:
        return subprocess.run(
            ["git", "config", "user.email"], capture_output=True, text=True
        ).stdout.strip()
    except OSError:
        return ""


# --- change folder ids --------------------------------------------------------------------

# `<created>-<KEY>-<slug>`, and `<created>-<slug>` when the change has no Linear issue.
CHANGE_DIR = re.compile(r"^(\d{4}-\d{2}-\d{2})-(?:([A-Z][A-Z0-9]+-\d+)-)?([a-z0-9][a-z0-9-]*)$")
# Everything the chain named before the date prefix existed, `PENDING-` included.
LEGACY_DIR = re.compile(r"^(?:(\d{4}-\d{2}-\d{2})-)?(?:([A-Z][A-Z0-9]+-\d+|PENDING)-)?(.+)$")


def change_id(date: str, key: str, slug: str) -> str:
    return f"{date}-{key}-{slug}" if key else f"{date}-{slug}"


def first_commit_date(path: Path) -> str:
    out = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%ad", "--date=short", "--", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.split()
    return out[-1] if out else ""


def migrate_change_ids(changes: Path, today: str) -> None:
    """Rename folders from before the date prefix, and drop `PENDING` -- it never meant
    "a key is coming", it meant "this change has no Linear issue"."""
    folders = [p for p in sorted(changes.glob("*")) if p.is_dir() and p.name != "archive"]
    folders += archived_changes(changes / "archive")
    for old in folders:
        if CHANGE_DIR.match(old.name):
            continue
        m = LEGACY_DIR.match(old.name)
        if not m:
            continue
        date, key, slug = m.group(1) or "", m.group(2) or "", m.group(3)
        key = "" if key == "PENDING" else key
        arts = [old / n for n in ("plan.md", "facts.md", "intent.md") if (old / n).exists()]
        if not date:
            for a in arts:
                fm = re.search(
                    r"^created:\s*(\d{4}-\d{2}-\d{2})", a.read_text(encoding="utf-8"), re.M
                )
                if fm:
                    date = fm.group(1)
                    break
        date = date or first_commit_date(old) or today
        new = old.with_name(change_id(date, key, slug))
        if new == old:
            continue
        wrote.append(
            f"{old.relative_to(ROOT)} -> {new.relative_to(ROOT)} (renamed: ids carry their creation date)"
        )
        if DRY:
            continue
        subprocess.run(["git", "mv", str(old), str(new)], cwd=ROOT, check=True)
        for md in sorted(new.glob("*.md")):
            text = md.read_text(encoding="utf-8")
            head, sep, body = (
                text[4:].partition("\n---\n") if text.startswith("---\n") else ("", "", "")
            )
            if not sep:
                continue
            head = re.sub(r"^change:.*$", f"change: {new.name}", head, count=1, flags=re.M)
            head = re.sub(r"^linear:.*$", f"linear: {key or 'none'}", head, count=1, flags=re.M)
            if re.search(r"^created:", head, re.M):
                head = re.sub(r"^created:.*$", f"created: {date}", head, count=1, flags=re.M)
            else:
                head += f"\ncreated: {date}"
            md.write_text("---\n" + head + sep + body, encoding="utf-8")


# `2026` and `2026-09`, the two bucket levels -- and NOT `2026-09-04-slug`, which is a
# change. Detecting the bucket rather than the change is what lets this run beside
# migrate_change_ids, whose whole job is folders that do NOT match CHANGE_DIR yet: with the
# other rule it renamed the fresh `2026` bucket to `2026-09-20-2026` on the second adopt.
ARCHIVE_BUCKET = re.compile(r"^\d{4}(-\d{2})?$")


def archived_changes(archive: Path, depth: int = 2) -> list[Path]:
    """Every change folder under the archive, flat or nested, legacy names included."""
    if not archive.is_dir():
        return []
    out: list[Path] = []
    for child in sorted(archive.iterdir()):
        if not child.is_dir():
            continue
        if depth > 0 and ARCHIVE_BUCKET.match(child.name):
            out.extend(archived_changes(child, depth - 1))
        else:
            out.append(child)
    return out


def migrate_archive_layout(changes: Path) -> None:
    """Nest the archive by <year>/<year-month>/, the way docsDesigns already nests, and make
    every archived folder's name-date its `created` date.

    Two problems, one pass, because both are answered by the same frontmatter. Measured in
    a real repo: 52 archived changes in 15 days -- ~1,200 a year in one flat
    directory -- and 2 of them named by their archive date rather than their creation date,
    so a folder name could not be read without opening it.

    Only the archive moves. Open changes stay flat: they are the working set, and hiding
    them behind two directory levels to match a convention costs more than it buys."""
    archive = changes / "archive"
    for old in archived_changes(archive):
        name = old.name
        date = name[:10]
        created = ""
        for art in ("plan.md", "facts.md", "intent.md"):
            f = old / art
            if not f.exists():
                continue
            m = re.search(r"^created:\s*(\d{4}-\d{2}-\d{2})", f.read_text(encoding="utf-8"), re.M)
            if m:
                created = m.group(1)
                break
        # No `created` to trust: leave the name alone and bucket it where it already says.
        if created and created != date:
            name = created + name[10:]
            date = created
        bucket = archive / date[:4] / date[:7]
        new = bucket / name
        if new == old:
            continue
        if new.exists():
            wrote.append(
                f"{old.relative_to(ROOT)} (SKIPPED: {new.relative_to(ROOT)} already exists)"
            )
            continue
        why = "nested by year-month" if name == old.name else "renamed to its creation date, nested"
        wrote.append(f"{old.relative_to(ROOT)} -> {new.relative_to(ROOT)} ({why})")
        if DRY:
            continue
        bucket.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "mv", str(old), str(new)], cwd=ROOT, check=True)
        if name != old.name:
            for md in sorted(new.glob("*.md")):
                text = md.read_text(encoding="utf-8")
                md.write_text(
                    re.sub(r"^change:.*$", f"change: {name}", text, count=1, flags=re.M),
                    encoding="utf-8",
                )
    # git leaves the emptied year/month and flat parents behind; they are not ours to keep.
    for d in sorted(archive.rglob("*"), key=lambda p: -len(p.parts)) if not DRY else ():
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()


DECISION_LOG = Path("docs/ux/decisions.md")
LOG_FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
LOG_DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(.+)$")
LOG_ROW = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|(.+)\|\s*$")
LOG_REPLACED = re.compile(
    r"(?:Replaced|Superseded)(?P<p1> in part)?(?: on \d{4}-\d{2}-\d{2})?(?P<p2> in part| for \w+)?"
    r" by (?P<refs>[^\n]+?)(?::|\*\*|$)",
    re.MULTILINE,
)
LOG_REF = re.compile(r"(\d{4}-\d{2}-\d{2}) (.+?)(?= and \d{4}-\d{2}-\d{2} |$)")


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def split_decision_log(text: str, today: str) -> list[dict[str, object]]:
    """The decisions in an appended log, in order. A `## <date> <title>` section is one
    decision, or one per `### ` child when it has children (a round of answers). Rows of a
    dated table before the first `##` are one decision each; prose after that table is kept
    as notes on every row. An undated `##` takes the date of the section before it."""
    body = LOG_FRONTMATTER.sub("", text, count=1)
    blocks = re.split(r"^## ", body, flags=re.MULTILINE)
    units: list[dict[str, object]] = []
    lines = blocks[0].splitlines()
    rows = [(i, m) for i, line in enumerate(lines) if (m := LOG_ROW.match(line))]
    if rows:
        first = rows[0][0]
        header = [line for line in lines[max(0, first - 2) : first] if line.startswith("|")]
        notes = "\n".join(lines[rows[-1][0] + 1 :]).strip()
        for i, m in rows:
            title = re.split(r"[:;(]", m.group(2).split("|")[0])[0].strip()[:90]
            units.append(
                {
                    "date": m.group(1),
                    "title": title,
                    "body": "\n".join([*header, lines[i]]),
                    "notes": notes,
                }
            )
    last = str(units[0]["date"]) if units else today
    for block in blocks[1:]:
        head, _, rest = block.partition("\n")
        dated = LOG_DATED.match(head.strip())
        date, title = (dated.group(1), dated.group(2).strip()) if dated else (last, head.strip())
        last = date
        parts = re.split(r"^### ", rest, flags=re.MULTILINE)
        if len(parts) == 1:
            units.append({"date": date, "title": title, "body": rest.strip()})
            continue
        for child in parts[1:]:
            child_title, _, child_body = child.partition("\n")
            units.append(
                {
                    "date": date,
                    "title": child_title.strip(),
                    "body": child_body.strip(),
                    "round": title,
                    "lead": parts[0].strip(),
                }
            )
    for u in units:
        said = f"{u['title']} {u.get('round', '')}".lower()
        status = re.search(r"\*\*Status:\*\*\s*([A-Za-z-]+)", str(u["body"]))
        u["status"] = (
            "open"
            if re.search(r"\bopen\b", said)
            else status.group(1).lower()
            if status
            else "accepted"
        )
        u["by"] = "claude" if "settled by claude" in said else "owner" if "owner" in said else ""
        for key in ("supersedes", "superseded_by", "amended_by"):
            u[key] = []
    return units


def link_decisions(units: list[dict[str, object]]) -> list[str]:
    """Turn "Replaced on <date> by <date> <title>" into `superseded_by` on the old decision and
    `supersedes` on the new one; "in part" or "for <who>" is `amended_by` and keeps the old one
    current. Returns every reference that names no decision in the log, for a person to link."""
    unresolved = []
    for old in units:
        body = str(old["body"])
        # Only a note that opens the decision replaces all of it. The same words inside a
        # bullet of a long round replace that bullet, and the rest of the round still holds.
        opening = len(body.lstrip().partition("\n")[0]) + len(body) - len(body.lstrip())
        for m in LOG_REPLACED.finditer(body):
            partial = bool(m.group("p1") or m.group("p2")) or m.start() > opening
            refs = LOG_REF.findall(m.group("refs").strip())
            if not refs:
                unresolved.append(f"{old['id']}: {m.group(0).strip()[:120]}")
            for date, ref in refs:
                want = " ".join(_words(ref))
                new = next(
                    (
                        u
                        for u in units
                        if u["date"] == date
                        and u is not old
                        and (
                            want.startswith(" ".join(_words(str(u["title"]))))
                            or " ".join(_words(str(u["title"]))).startswith(want)
                        )
                    ),
                    None,
                )
                if new is None:
                    unresolved.append(f"{old['id']}: {date} {ref[:100]}")
                    continue
                old["amended_by" if partial else "superseded_by"].append(new["id"])  # type: ignore[union-attr]
                new["supersedes"].append(old["id"])  # type: ignore[union-attr]
                if not partial:
                    old["status"] = "superseded"
        if re.search(r"Replaced|Superseded", str(old.get("notes", ""))):
            unresolved.append(f"{old['id']}: its shared notes say something was replaced")
    return unresolved


def migrate_decision_log(designs: Path, today: str) -> None:
    """Split an appended decision log into one ADR file per decision under `designsDir`.

    `cct:ux-decision-log` used to append every answer to `docs/ux/decisions.md`. Measured in
    a real repo: 2,910 lines, 87 sections, 35 commits in 19 days, read whole by
    every agent that needed one answer. One decision per file plus `INDEX.md` lets it read
    the index and open one file. Idempotent: the log is replaced by a pointer with no
    sections, so a second run finds nothing to split."""
    log = ROOT / DECISION_LOG
    if not log.exists():
        return
    text = log.read_text(encoding="utf-8")
    units = split_decision_log(text, today)
    if not units:
        return
    nested = designs.is_dir() and any(
        p.is_dir() and re.fullmatch(r"\d{4}", p.name) for p in designs.iterdir()
    )
    taken = {p.stem for p in designs.rglob("*.md")} if designs.is_dir() else set()
    for u in units:
        date = str(u["date"])
        base = f"{date}-adr-{'-'.join(_words(str(u['title']))[:6]) or 'decision'}"
        uid, n = base, 2
        while uid in taken:
            uid, n = f"{base}-{n}", n + 1
        taken.add(uid)
        u["id"] = uid
        u["path"] = designs / (f"{date[:4]}/{date[:7]}" if nested else "") / f"{uid}.md"
    unresolved = link_decisions(units)
    source = DECISION_LOG.as_posix()
    for u in units:

        def ids(key: str, u: dict[str, object] = u) -> str:
            return "[" + ", ".join(u[key]) + "]"  # type: ignore[arg-type]

        head = [
            "---",
            f"id: {u['id']}",
            f"title: {json.dumps(str(u['title']), ensure_ascii=False)}",
            "type: adr",
            f"status: {u['status']}",
            f"created: {u['date']}",
            *([f"decided_by: {u['by']}"] if u["by"] else []),
            *(
                [f"round: {json.dumps(str(u['round']), ensure_ascii=False)}"]
                if "round" in u
                else []
            ),
            f"supersedes: {ids('supersedes')}",
            f"superseded_by: {ids('superseded_by')}",
            f"amended_by: {ids('amended_by')}",
            "tags: [ux]",
            f"migrated_from: {source}",
            "---",
            "",
            f"# {u['title']}",
            "",
        ]
        parts = [str(u["body"])]
        if u.get("lead"):
            parts.insert(0, f"## The round: {u['round']}\n\n{u['lead']}\n\n## This decision")
        if u.get("notes"):
            parts.append(f"## Notes on the whole table\n\n{u['notes']}")
        write(Path(str(u["path"])), "\n".join(head) + "\n" + "\n\n".join(parts).rstrip() + "\n")
    title = re.search(r"^# (.+)$", text, re.MULTILINE)
    rel = designs.relative_to(ROOT).as_posix()
    write(
        log,
        f"# {title.group(1).strip() if title else 'Decision log'} (moved)\n\n"
        f"Moved on {today}: every decision is its own file under `{rel}/` (type `adr`), "
        f"listed in `{rel}/INDEX.md`. Write a new decision as a new file, never here.\n"
        f"`git log --follow {source}` holds the old log.\n",
    )
    wrote.append(f"{source}: split into {len(units)} decision files under {rel}/")
    manual.extend(f"link by hand: {line}" for line in unresolved)


def write_design_index(designs: Path) -> None:
    """`INDEX.md` from the kit's own copy of the script, so adopt and CI render the same text."""
    if not designs.is_dir():
        return
    spec = importlib.util.spec_from_file_location(
        "design_index", TPL / "scripts" / "design_index.py"
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    write(designs / "INDEX.md", mod.render(designs))


TIER_DEFAULTS = {
    "node": {
        "ask": [
            "drizzle/**",
            "prisma/**",
            "src/lib/db/schema/**",
            "k8s/**",
            ".github/**",
            "package.json",
            "pnpm-lock.yaml",
            "REVIEW.md",
            "sdlc.json",
            ".claude/settings.json",
            ".claude/hooks/**",
        ],
        "show": ["src/**", "e2e/**", "tests/**", "scripts/**"],
    },
    "python": {
        "ask": [
            "src/integrations/**",
            "k8s/**",
            ".github/**",
            "pyproject.toml",
            "uv.lock",
            "REVIEW.md",
            "sdlc.json",
            ".claude/settings.json",
            ".claude/hooks/**",
        ],
        "show": ["src/**", "tests/**", "scripts/**"],
    },
}


def write(path: Path, text: str, *, keep: bool = False, executable: bool = False) -> None:
    rel = str(path.relative_to(ROOT))
    if keep and path.exists():
        kept.append(rel)
        return
    if path.exists() and path.read_text(encoding="utf-8") == text:
        kept.append(rel)
        return
    wrote.append(rel)
    pending[rel] = (text, executable)
    if DRY:
        return
    written.append(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def remove(path: Path, why: str) -> None:
    """Take a generated file out of the repo: `git rm`, then unlink whatever git did not track."""
    if not path.exists():
        return
    wrote.append(f"{path.relative_to(ROOT)} (removed: {why})")
    if DRY:
        return
    subprocess.run(["git", "rm", "-qf", "--ignore-unmatch", str(path)], cwd=ROOT, check=True)
    if path.exists():
        path.unlink()


PRETTIER_SUFFIXES = {".ts", ".js", ".mjs", ".json", ".yml", ".yaml", ".md"}


def format_written() -> None:
    """Run the repo's own prettier over what we just wrote.

    The templates cannot be formatted to suit every repo -- printWidth, quotes and plugins
    all differ -- so a repo with a `prettier --check` gate rejects a freshly adopted file.
    The repo's formatter is the authority; we just call it. No prettier, nothing to do."""
    if DRY:
        return
    targets = [p for p in written if p.suffix in PRETTIER_SUFFIXES]
    written.clear()
    binary = ROOT / "node_modules" / ".bin" / "prettier"
    if not targets or not binary.exists():
        return
    out = subprocess.run(
        [str(binary), "--write", "--log-level", "warn", *(str(p) for p in targets)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if out.returncode == 0:
        wrote.append(f"prettier --write on {len(targets)} written file(s)")
    else:
        detail = (out.stderr or out.stdout).strip().splitlines()
        manual.append(
            "prettier failed on the files adopt wrote -- run `prettier --write` before committing"
            + (f": {detail[-1]}" if detail else "")
        )


# CLAUDE-section.md's tier sentence as rendered with tiers on, and what replaces it when
# they go off. Both are ONE line in the template on purpose: this constant has to match the
# rendered text byte for byte, and a wrapped sentence silently stops matching the moment the
# template is rewrapped — the swap then no-ops and CLAUDE.md keeps promising a tier that is
# gone. Keep them single-line and keep them whole sentences.
TIERED_SENTENCE = (
    "That PR is labelled by blast radius: `ask` needs a human, `show` and `ship` "
    "auto-merge on green."
)
UNTIERED_SENTENCE = "There are no Ship/Show/Ask tiers here, so that PR auto-merges on green too."
# The headers adopt's tier templates open with; a tier file without its header is the repo's own.
GENERATED_CODEOWNERS = (
    "# GENERATED by `run-sdlc adopt` from sdlc.json (codeowners) x .github/tiers.json (ask)."
)
TIER_WORKFLOW_MARKER = "# Ship / Show / Ask by blast radius"
TIER_SCRIPT_MARKER = '"""Classify a set of changed paths into one merge tier'
TIER_JSON_MARKER = '"_comment": "Ship/Show/Ask by blast radius.'


def render(text: str, values: dict[str, str]) -> str:
    """`{{NAME}}` tokens only (uppercase, underscores) -- `${{ secrets.X }}` is untouched.
    `{{#block}}...{{/block}}` is kept when values[block] is truthy, dropped otherwise.
    Blocks nest: the outer one is resolved first, then the pass repeats on what it kept."""

    def block(m: re.Match[str]) -> str:
        return m.group(2) if values.get(m.group(1)) else ""

    n = 1
    while n:
        text, n = re.subn(r"\{\{#(\w+)\}\}\n?(.*?)\{\{/\1\}\}\n?", block, text, flags=re.DOTALL)
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: values.get(m.group(1), m.group(0)), text)


E2E_CMD = re.compile(r"playwright|test:e2e")
# `--repeat-each` is a Playwright flag, so it marks an E2E check even behind a wrapper script
# (samplewerk: `sh scripts/e2e.sh --repeat-each 3`). The match covers its own value.
WHOLE_SUITE_REPEAT = re.compile(r"\s*--repeat-each(?:=|\s+)\S+")
MAX_FAILURES = re.compile(r"--max-failures(?:=|\s+)\S+")


CI_STACK = {"node": "typescript", "python": "python"}


KIT_CI_MARKER = "# CI for any stack: one workflow, one required status"


def kit_version() -> str:
    m = re.search(r"^  version:\s*(\S+)", (SKILL / "SKILL.md").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "0.0.0"


def add_ci_paths(cfg: dict, preset: str) -> None:
    """`ciPaths` is the repo's own list of which changed files switch which CI step on; the CI
    `changes` job and the agents' "touched tests" read it. Added from the stack's default when
    missing; a block that exists keeps every value and only gains the keys it lacks (`code`,
    `config`, `specs` arrived in 3.3.0)."""
    defaults = json.loads((TPL / "ci-paths.json").read_text(encoding="utf-8"))[CI_STACK[preset]]
    if "ciPaths" not in cfg:
        cfg["ciPaths"] = defaults
        wrote.append(
            f"sdlc.json: ciPaths added ({CI_STACK[preset]} defaults; edit to the repo's folders)"
        )
        return
    added = [k for k in defaults if k not in cfg["ciPaths"]]
    for k in added:
        cfg["ciPaths"][k] = defaults[k]
    if added:
        wrote.append(
            f"sdlc.json: ciPaths gained {', '.join(added)} ({CI_STACK[preset]} defaults; check them against the repo's folders)"
        )


def add_ci_commands(cfg: dict, preset: str) -> None:
    """`ciCommands` is what each job of templates/ci/github-actions.yml runs. Missing keys come
    from the stack's defaults; values the repo set are never touched."""
    defaults = json.loads((TPL / "ci-commands.json").read_text(encoding="utf-8"))[CI_STACK[preset]]
    have = cfg.setdefault("ciCommands", {})
    added = [k for k in defaults if k not in have]
    for k in added:
        have[k] = defaults[k]
    if added:
        wrote.append(
            f"sdlc.json: ciCommands added {', '.join(added)} ({CI_STACK[preset]} defaults)"
        )


BUILDERS = ("claude", "codex")
EFFORTS = ("low", "medium", "high", "xhigh")
DEFAULT_MODEL = {"claude": "sonnet", "codex": "gpt-5.5"}


def add_builders(cfg: dict) -> None:
    """`builders` says who builds feature rows and fix parts: `claude` (`cct:sdlc-feature-builder`
    agents, the default) or `codex` (`scripts/codex-build.sh`, 3.5.0). `builderModel` and
    `builderEffort` (3.6.0) say which model and how hard: the agent's `model`/`effort` override
    for claude, `-c model`/`model_reasoning_effort` for codex. Missing keys get the defaults
    (sonnet or gpt-5.5, high) and are written; a value the repo set is kept; a value outside
    the lists stops adopt."""
    v = cfg.get("builders")
    if v is None:
        v = cfg["builders"] = "claude"
        wrote.append("sdlc.json: builders added (claude; set codex to build with the Codex CLI)")
    elif v not in BUILDERS:
        sys.exit(f'sdlc.json builders must be "claude" or "codex", not {v!r}')
    m = cfg.get("builderModel")
    if m is None:
        cfg["builderModel"] = DEFAULT_MODEL[v]
        wrote.append(f"sdlc.json: builderModel added ({DEFAULT_MODEL[v]})")
    elif not isinstance(m, str) or not m.strip():
        sys.exit(f"sdlc.json builderModel must be a model name, not {m!r}")
    e = cfg.get("builderEffort")
    if e is None:
        cfg["builderEffort"] = "high"
        wrote.append("sdlc.json: builderEffort added (high)")
    elif e not in EFFORTS:
        sys.exit(f"sdlc.json builderEffort must be one of {', '.join(EFFORTS)}, not {e!r}")


def check_rules(cfg: dict) -> None:
    """`rules` (3.8.0) is optional: the repo files that hold standing rules, which Stages 1 and 4
    read. A missing key means the defaults in references/quality-passes.md; a list is kept as it
    is and never written by adopt, so a re-adopt cannot lose it. Anything but a list of paths
    stops adopt."""
    r = cfg.get("rules")
    if r is not None and not (isinstance(r, list) and all(isinstance(p, str) and p for p in r)):
        sys.exit(f"sdlc.json rules must be a list of repo paths, not {r!r}")


def stamp_version(cfg: dict, *, fresh: bool) -> None:
    """`sdlcVersion` says which kit version the repo was last adopted or upgraded with, so the
    skill can tell a repo it is behind. On a move from an older stamp, the changelog's manual
    migrations in between go to MANUAL."""
    new = kit_version()
    old = cfg.get("sdlcVersion")
    spec = importlib.util.spec_from_file_location(
        "sdlc_version", TPL / "scripts" / "sdlc_version.py"
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    if old and old != new and mod.parse(old) > mod.parse(new):
        manual.append(
            f"sdlc.json says sdlcVersion {old}, newer than this kit ({new}): update the cct plugin"
        )
        return
    if old != new:
        cfg["sdlcVersion"] = new
        wrote.append(f"sdlc.json: sdlcVersion {old or 'none'} -> {new}")
    if fresh or old == new:
        return
    for version, headline, _mech, todo in reversed(
        mod.between(SKILL / "references" / "changelog.md", old, new)
    ):
        for line in todo:
            manual.append(f"upgrade {version} ({headline}): {line}")


def ci_gaps(text: str) -> list[str]:
    gaps = []
    if not re.search(r"^  check:\s*$", text, re.M):
        gaps.append("no job named `check` as the one required status")
    if "ciPaths" not in text:
        gaps.append("steps are not gated on changed files from sdlc.json ciPaths")
    if "paths-ignore" in text:
        gaps.append("workflow-level paths-ignore leaves a required status pending forever")
    if "fromJSON" not in text and "shard" not in text:
        gaps.append("E2E is not sharded")
    return gaps


def adopt_ci(cfg: dict, preset: str) -> None:
    """A repo with no CI gets templates/ci/github-actions.yml with its STACK and default branch
    set. A repo with its own CI keeps it; adopt prints what it lacks and which jobs to copy."""
    wf = ROOT / ".github" / "workflows"
    kit_names = {p.name for p in (TPL / "workflows").glob("*.yml")}
    own = sorted(p for p in (*wf.glob("*.yml"), *wf.glob("*.yaml")) if p.name not in kit_names)
    ci = wf / "ci.yml"
    if ci.exists() and ci.read_text(encoding="utf-8").startswith(KIT_CI_MARKER):
        kept.append(".github/workflows/ci.yml (the kit's template, the repo's now)")
        return
    template = TPL / "ci" / "github-actions.yml"
    if not own and UPGRADE:
        manual.append(
            f"CI: the repo has no CI workflow; copy {template} to .github/workflows/ci.yml "
            f"(set STACK {preset}) or run `adopt`"
        )
        return
    if not own:
        text = template.read_text(encoding="utf-8")
        text = text.replace("  STACK: node #", f"  STACK: {preset} #", 1)
        text = text.replace(
            "branches: [main] # the default branch",
            f"branches: [{cfg.get('defaultBranch', 'main')}] # the default branch",
            1,
        )
        write(ci, text)
        manual.append(
            "CI: .github/workflows/ci.yml was written from the kit's template (STACK "
            f"{preset}); check sdlc.json ciCommands and ciPaths, then make `check` the only required status (ci-blueprint.md, A6)"
        )
        return
    gaps = ci_gaps("\n".join(p.read_text(encoding="utf-8") for p in own))
    manual.append(
        "CI: the repo has its own workflow(s) ("
        + ", ".join(p.name for p in own)
        + "), left alone. "
        + (f"Gaps: {'; '.join(gaps)}. " if gaps else "No gaps found by grep. ")
        + f"Copy the `changes` and `check` jobs from {template} and gate each job on its flag (references/ci-blueprint.md)"
    )


def migrate_test_cost(cfg: dict, preset: str) -> None:
    """Bring an adopted repo's test cost in line with the preset (measured in leadhub: a
    `--repeat-each 3` over the whole suite took 59-71 min per gate, and the Stop hook fell back
    to the full `verify` 760 times). Adds `verifyStop`, and turns a whole-suite repeat into a
    single run in place: the repeat goes, the preset's `--max-failures` comes, and the repo's own
    command and flags stay. `lock.json` hashes `checks`, so every open change then needs the
    engineer's OK again -- adopt lists them and never re-locks."""
    base = json.loads((TPL / "presets" / f"{preset}.json").read_text(encoding="utf-8"))
    if not cfg.get("verifyStop") and base.get("verifyStop"):
        cfg["verifyStop"] = base["verifyStop"]
        wrote.append(f"sdlc.json: verifyStop added: {base['verifyStop']}")
    # The node preset speaks pnpm. In an npm repo a pnpm verifyStop fails every Stop
    # in practice), so translate it to the package manager the lockfile names.
    stop = cfg.get("verifyStop") or ""
    if (
        stop.startswith("pnpm ")
        and (ROOT / "package-lock.json").exists()
        and not (ROOT / "pnpm-lock.yaml").exists()
    ):
        npm = re.sub(r"\bpnpm exec\b", "npx", stop)
        npm = re.sub(r"\bpnpm (?:run )?(?=[\w:-])", "npm run ", npm)
        cfg["verifyStop"] = npm
        wrote.append(f"sdlc.json: verifyStop `{stop}` -> `{npm}` (this repo uses npm)")
    preset_e2e = " ".join(
        c for c in base.get("checks", {}).get("milestone", []) if E2E_CMD.search(c)
    )
    found = MAX_FAILURES.search(preset_e2e)
    fail_fast = found.group(0) if found else "--max-failures=10"
    milestone = cfg.get("checks", {}).get("milestone", [])
    moved = False
    for i, check in enumerate(milestone):
        cmd = check["run"] if isinstance(check, dict) else check
        if not WHOLE_SUITE_REPEAT.search(cmd) or "--only-changed" in cmd or "--grep" in cmd:
            continue
        new = WHOLE_SUITE_REPEAT.sub("", cmd)
        if not MAX_FAILURES.search(new):
            new = f"{new} {fail_fast}"
        if isinstance(check, dict):
            check["run"] = new
        else:
            milestone[i] = new
        wrote.append(f"sdlc.json: checks.milestone `{cmd}` -> `{new}`")
        moved = True
    if not moved:
        return
    changes = ROOT / cfg.get("changesDir", "changes")
    for folder in sorted(changes.glob("*")) if changes.is_dir() else ():
        if folder.is_dir() and folder.name != "archive" and (folder / "lock.json").exists():
            manual.append(
                f"{folder.name}: its lock.json hashed the old checks, so the gate blocks with "
                f"protected-path. Record your OK: run `python3 scripts/verify_gate.py approve "
                f"{folder.name}` yourself (the agent never re-locks) and commit lock.json"
            )


def apply_tiers_answer(cfg: dict) -> None:
    """The engineer's answer to "Use Ship/Show/Ask?" (`--tiers yes|no`) becomes sdlc.json `tiers`.
    Without an answer a missing key is written as TIERS_DEFAULT, because the guardrail test copied
    into the repo reads a missing key as true."""
    if "--tiers" not in sys.argv:
        if "tiers" not in cfg:
            cfg["tiers"] = TIERS_DEFAULT
            wrote.append(f"sdlc.json: tiers {str(TIERS_DEFAULT).lower()} (the kit default)")
        return
    answer = sys.argv[sys.argv.index("--tiers") + 1]
    if answer not in ("yes", "no"):
        sys.exit(f"--tiers takes yes or no, not {answer!r}")
    if cfg.get("tiers") != (answer == "yes"):
        cfg["tiers"] = answer == "yes"
        wrote.append(f"sdlc.json: tiers {str(cfg['tiers']).lower()} (Ship/Show/Ask: {answer})")


def finish_upgrade() -> str:
    """After the dry-run flow: everything it would have written or moved becomes a review line,
    and `--replace <file>` shows (or, with --apply, writes) the kit's copy of one file."""
    import difflib

    review = [w for w in wrote if not w.startswith("sdlc.json")]
    wrote[:] = [w for w in wrote if w.startswith("sdlc.json")]
    for w in review:
        rel = w.split(" ")[0]
        if rel in pending:
            manual.append(
                f"review diff: {rel} differs from the kit's copy (the kit changed it or the repo "
                f"edited it); left alone. See the diff: `adopt --upgrade --replace {rel}`; "
                f"replace it: add `--apply`"
            )
        else:
            manual.append(
                f"review: `{w}` is a layout migration or removal that --upgrade does not apply; run `adopt` to apply it"
            )
    out = []
    for rel in REPLACE:
        if rel not in pending:
            manual.append(
                f"--replace {rel}: nothing to replace (it is the kit's copy already, or not a file adopt owns)"
            )
            continue
        text, executable = pending[rel]
        path = ROOT / rel
        old = path.read_text(encoding="utf-8").splitlines(True) if path.exists() else []
        out.append(
            "".join(difflib.unified_diff(old, text.splitlines(True), f"a/{rel}", f"b/{rel} (kit)"))
        )
        if APPLY and not DRY_RUN:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            if executable:
                path.chmod(0o755)
            wrote.append(f"{rel} (replaced by the kit's copy)")
            manual[:] = [m for m in manual if not m.startswith(f"review diff: {rel} ")]
        else:
            manual.append(
                f"--replace {rel}: diff shown, nothing written; add --apply to replace it"
            )
    return "\n".join(out)


def main() -> int:
    preset = detect_preset()
    cfg_path = ROOT / "sdlc.json"
    if UPGRADE and not cfg_path.exists():
        sys.exit(
            "sdlc.json is missing: this repo is not adopted. Run `adopt`, not `adopt --upgrade`."
        )
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg_before = json.dumps(cfg, sort_keys=True)
        kept.append("sdlc.json")
        if not UPGRADE:
            cfg["kitTemplates"] = templates_hash()
            apply_tiers_answer(cfg)
    else:
        cfg = json.loads((TPL / "presets" / f"{preset}.json").read_text(encoding="utf-8"))
        cfg["defaultBranch"] = default_branch()
        cfg["kitTemplates"] = templates_hash()
        apply_tiers_answer(cfg)
        add_ci_paths(cfg, preset)
        add_ci_commands(cfg, preset)
        add_builders(cfg)
        stamp_version(cfg, fresh=True)
        write(cfg_path, json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
        manual.append(
            f"sdlc.json was created from the {preset} preset -- check linear.team/project, verify, blocked, codeowners"
        )

    # --- migration: the 2026-09-07 layout decision. `.changes/` -> `changes/` (visible: it is
    # the audit trail, not scratch), `specs/` -> `docs/designs/` (a design is documentation),
    # `specsDir` -> `designsDir`, and `spec:` -> `design:` in every change artifact. Idempotent.
    if UPGRADE and ("specsDir" in cfg or cfg.get("changesDir") == ".changes"):
        manual.append(
            "sdlc.json uses the old layout keys (specsDir, .changes): run `adopt`, not --upgrade, to migrate"
        )
    elif "specsDir" in cfg:
        cfg["designsDir"] = (
            "docs/designs" if cfg["specsDir"] in ("specs", "docs") else cfg.pop("specsDir")
        )
        cfg.pop("specsDir", None)
        wrote.append("sdlc.json: specsDir -> designsDir")
    if not UPGRADE and cfg.get("changesDir") == ".changes":
        cfg["changesDir"] = "changes"
        wrote.append("sdlc.json: changesDir .changes -> changes")
    if "sdlc.json" in kept:
        add_ci_paths(cfg, preset)
        add_ci_commands(cfg, preset)
        add_builders(cfg)
        check_rules(cfg)
        if "claude" in cfg:
            cfg.pop("claude")
            wrote.append("sdlc.json: claude removed (no Claude in CI since sdlc-run 3.7.0)")
        if not UPGRADE:
            migrate_test_cost(cfg, preset)
        elif "--repeat-each" in json.dumps(cfg.get("checks", {})):
            manual.append(
                "sdlc.json: checks.milestone repeats the whole suite (--repeat-each); `adopt` rewrites it, --upgrade leaves it"
            )
        stamp_version(cfg, fresh=False)
    changed = UPGRADE and json.dumps(cfg, sort_keys=True) != cfg_before
    if (changed and not DRY_RUN) or (
        not UPGRADE and not DRY and cfg_path.exists() and "sdlc.json" in kept
    ):
        cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        # Not via write(): sdlc.json is the repo's own file and only gets fields merged in.
        # It still has to reach format_written(), or a prettier repo rejects the commit.
        written.append(cfg_path)
    changes_dir = cfg.get("changesDir", "changes")
    designs_dir = cfg.get("designsDir", "docs/designs")
    for old, new in ((ROOT / ".changes", ROOT / changes_dir), (ROOT / "specs", ROOT / designs_dir)):
        if old.is_dir() and old != new and not new.exists():
            wrote.append(f"{old.relative_to(ROOT)}/ -> {new.relative_to(ROOT)}/ (migrated)")
            if not DRY:
                new.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["git", "mv", "-k", str(old), str(new)], cwd=ROOT, check=True)
                if old.exists():
                    old.rename(new)
    for md in (ROOT / changes_dir).rglob("*.md") if (ROOT / changes_dir).is_dir() else ():
        text = md.read_text(encoding="utf-8")
        if text.startswith("---\n") and re.search(r"^spec:", text, re.M):
            head, sep, body = text[4:].partition("\n---\n")
            head = re.sub(
                r"^spec:(.*)$",
                lambda mm: "design:" + mm.group(1).replace("specs/", designs_dir + "/"),
                head,
                count=1,
                flags=re.M,
            )
            body = body.replace("## Spec changes", "## Design changes").replace(
                "`spec:`", "`design:`"
            )
            wrote.append(f"{md.relative_to(ROOT)}: spec: -> design:")
            if not DRY:
                md.write_text("---\n" + head + sep + body, encoding="utf-8")
    review_md = ROOT / "REVIEW.md"  # repo-owned and kept, so its paths are patched, not regenerated
    if review_md.exists() and ".changes/" in review_md.read_text(encoding="utf-8"):
        wrote.append(f"REVIEW.md: .changes/ -> {changes_dir}/")
        if not DRY:
            review_md.write_text(
                review_md.read_text(encoding="utf-8").replace(".changes/", changes_dir + "/"),
                encoding="utf-8",
            )
    docs = cfg.get("docs", "docs/sdlc.md")
    today = dt.date.today().isoformat()
    keep_paths = set(cfg.get("keep", []))

    def _write(path: Path, text: str, **kw: object) -> None:
        if str(path.relative_to(ROOT)) in keep_paths:
            kept.append(str(path.relative_to(ROOT)) + " (sdlc.json keep)")
            return
        write(path, text, **kw)  # type: ignore[arg-type]

    # --- hooks + settings.json
    hooks_dir = ROOT / ".claude" / "hooks"
    for src in sorted((TPL / "hooks").glob("*.sh")):
        _write(hooks_dir / src.name, src.read_text(encoding="utf-8"), executable=True)

    settings_path = ROOT / ".claude" / "settings.json"
    settings = (
        json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    )
    deny = settings.setdefault("permissions", {}).setdefault("deny", [])
    for rule in ("Read(.env*)", "Read(**/secrets/**)", "Read(**/.secrets/**)"):
        if rule not in deny:
            deny.append(rule)
    hooks = settings.setdefault("hooks", {})
    # Hooks the earlier, repo-local layout shipped under other names: unregister and remove.
    for legacy in ("ruff-on-edit.sh",):
        for event, groups in list(hooks.items()):
            for g in groups:
                g["hooks"] = [h for h in g.get("hooks", []) if legacy not in h.get("command", "")]
            hooks[event] = [g for g in groups if g.get("hooks")]
        old = hooks_dir / legacy
        if old.exists():
            wrote.append(f".claude/hooks/{legacy} (removed: replaced by lint-on-edit.sh)")
            if not DRY:
                subprocess.run(
                    ["git", "rm", "-qf", "--ignore-unmatch", str(old)], cwd=ROOT, check=True
                )
                if old.exists():
                    old.unlink()
    # A LIST, not a dict keyed by event: PreToolUse carries two entries -- gate-bash.sh for
    # what sdlc.json blocks, chain-gate.sh for the chain's own gates -- and a dict silently
    # kept only the last one.
    spec = [
        ("SessionStart", None, "session-check.sh", 5),
        ("PermissionRequest", "ExitPlanMode", "plan-gate.sh", 345600),
        ("PreToolUse", "Bash", "gate-bash.sh", 5),
        ("PreToolUse", "Bash", "pr-gate.sh", 20),
        ("PreToolUse", "Edit|Write", "chain-gate.sh", 5),
        ("PostToolUse", "Edit|Write", "lint-on-edit.sh", 30),
        ("Stop", None, "verify-on-stop.sh", 300),
    ]
    for event, matcher, script, timeout in spec:
        groups = hooks.setdefault(event, [])
        entry = {
            "type": "command",
            "command": f'"$CLAUDE_PROJECT_DIR"/.claude/hooks/{script}',
            "timeout": timeout,
        }
        if any(script in h.get("command", "") for g in groups for h in g.get("hooks", [])):
            continue
        group = {"hooks": [entry]}
        if matcher:
            group = {"matcher": matcher, **group}
        groups.append(group)
    write(settings_path, json.dumps(settings, indent=2) + "\n")

    # A global gitignore that hides `.claude/*` would leave the hooks working on one laptop.
    ignored = (
        subprocess.run(
            ["git", "check-ignore", "-q", ".claude/hooks/gate-bash.sh"], cwd=ROOT
        ).returncode
        == 0
    )
    if ignored:
        gi = ROOT / ".gitignore"
        lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
        add = [
            line
            for line in (
                "!.claude/",
                "!.claude/settings.json",
                "!.claude/hooks/",
                "!.claude/hooks/*.sh",
            )
            if line not in lines
        ]
        if add:
            write(
                gi,
                "\n".join(lines + ["", "# the SDLC hooks are the repo's, not the laptop's"] + add)
                + "\n",
            )

    # --- tiers, classifier, CODEOWNERS
    # sdlc.json `tiers` (default TIERS_DEFAULT): Ship/Show/Ask. False is for a repo with one owner --
    # there is nobody to ask and nobody to show, so every PR auto-merges on green. adopt
    # writes none of the four tier files and removes any that exist.
    tiers_on = cfg.get("tiers", TIERS_DEFAULT)
    tiers_path = ROOT / ".github" / "tiers.json"
    co_path = ROOT / ".github" / "CODEOWNERS"
    tiers = {"ask": [], "show": []}  # what ASK_PATHS / SHOW_PATHS read when tiers is off
    if not tiers_on:
        # Only what adopt generated goes, recognised by the header its template opens with: a
        # path in `keep` or a hand-written file stays (KEPT).
        removed = False
        for p in (
            ROOT / ".github" / "workflows" / "ship-show-ask.yml",
            ROOT / "scripts" / "ship_show_ask.py",
            tiers_path,
            co_path,
        ):
            if not p.exists():
                continue
            rel = str(p.relative_to(ROOT))
            head = p.read_text(encoding="utf-8", errors="replace")
            generated = {
                ".github/workflows/ship-show-ask.yml": head.startswith(TIER_WORKFLOW_MARKER),
                "scripts/ship_show_ask.py": head.startswith(TIER_SCRIPT_MARKER),
                ".github/tiers.json": TIER_JSON_MARKER in head,
                ".github/CODEOWNERS": head.startswith(GENERATED_CODEOWNERS),
            }[rel]
            if rel in keep_paths:
                kept.append(f"{rel} (sdlc.json keep)")
            elif not generated:
                kept.append(f"{rel} (hand-written, not adopt's)")
            else:
                remove(p, "sdlc.json tiers=false")
                removed = True
        if any(w.startswith(".github/CODEOWNERS (removed") for w in wrote):
            manual.append(
                f"ruleset on {cfg.get('defaultBranch', 'master')}: CODEOWNERS removed; turn off "
                "require_code_owner_review or commit your own CODEOWNERS"
            )
        if removed:
            manual.append(
                f"ruleset on {cfg.get('defaultBranch', 'master')}: remove the GitHub App from the "
                "pull_request bypass actors; delete the secrets CODE_MANAGER_APP_CLIENT_ID, "
                "CODE_MANAGER_APP_PRIVATE_KEY, SDLC_SLACK_BOT_TOKEN and the variable SDLC_COOWNER "
                "(Ship/Show/Ask is off, so the tier workflow that used them is gone)"
            )
    elif tiers_path.exists():
        tiers = json.loads(tiers_path.read_text(encoding="utf-8"))
        kept.append(".github/tiers.json")
    else:
        d = TIER_DEFAULTS[preset]
        tiers = {
            "_comment": f"Ship/Show/Ask by blast radius. First tier whose glob matches a changed file wins, in this order. Read by scripts/ship_show_ask.py, .github/workflows/ship-show-ask.yml and the sdlc guardrail test; CODEOWNERS is generated from the ask globs and sdlc.json codeowners. {docs} explains the tiers.",
            "order": ["ask", "show", "ship"],
            "ask": d["ask"],
            "show": d["show"],
            "ship": ["**"],
        }
        write(tiers_path, json.dumps(tiers, indent=2) + "\n")
        manual.append(
            f".github/tiers.json was created with {preset} defaults -- check the ask globs against what really hurts here"
        )
    # The verify contract runs in CI and in /goal, where no plugin is installed: a copy.
    for script in (
        "verify_gate.py",
        "sdlc_status.py",
        "design_index.py",
        "marks.py",
        "sdlc_version.py",
    ):
        _write(ROOT / "scripts" / script, (TPL / "scripts" / script).read_text(encoding="utf-8"))
    gi = ROOT / ".gitignore"
    gi_lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    verify_out = f"/{changes_dir}/*/verify/"
    if verify_out not in gi_lines:
        write(
            gi,
            "\n".join(gi_lines + ["# verify_gate.py output; lock.json is committed", verify_out])
            + "\n",
        )
    if not (cfg.get("tracker") or (cfg.get("linear") or {}).get("team")):
        manual.append(
            "tracker: none set -- run `sdlc-run tracker` to choose Linear, GitHub or Beads and set it up"
        )
    if tiers_on:
        _write(
            ROOT / "scripts" / "ship_show_ask.py",
            (TPL / "scripts" / "ship_show_ask.py").read_text(encoding="utf-8"),
        )

    owners = cfg.get("codeowners", []) if tiers_on else []
    if owners:
        rules = "\n".join(
            f"/{g[:-3] + '/' if g.endswith('/**') else g}  {' '.join(owners)}" for g in tiers["ask"]
        )
        _write(co_path, render((TPL / "CODEOWNERS").read_text(encoding="utf-8"), {"RULES": rules}))
        manual.append("ruleset: set require_code_owner_review=true (codeowners are named)")
    elif tiers_on and co_path.exists():
        wrote.append(".github/CODEOWNERS (removed: no codeowners in sdlc.json)")
        if not DRY:
            co_path.unlink()
        manual.append("ruleset: set require_code_owner_review=false (no codeowners named)")

    # --- workflows
    adopt_ci(cfg, preset)
    ci_name = "CI"
    ci = ROOT / ".github" / "workflows" / "ci.yml"
    if ci.exists():
        m = re.search(r"^name:\s*(.+)$", ci.read_text(encoding="utf-8"), re.M)
        if m:
            ci_name = m.group(1).strip().strip("\"'")
    setup = {
        "node": "      - uses: pnpm/action-setup@ea17c68df8912ef543352723c149a84f56e3d413 # v6.1.0\n        if: steps.key.outputs.present == 'true'\n      - uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0\n        if: steps.key.outputs.present == 'true'\n        with:\n          node-version-file: package.json\n          cache: pnpm\n      - run: pnpm install --frozen-lockfile\n        if: steps.key.outputs.present == 'true'\n",
        "python": "      - uses: astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9 # v9.0.0\n        if: steps.key.outputs.present == 'true'\n        with:\n          enable-cache: true\n",
    }[preset]
    values = {
        "CHANGES_DIR": changes_dir,
        "DOCS": docs,
        "DESIGNS_DIR": cfg.get("designsDir", "docs/designs"),
        "DEFAULT_BRANCH": cfg.get("defaultBranch", "master"),
        "VERIFY": cfg["verify"],
        "VERIFY_STOP": cfg.get("verifyStop", cfg["verify"]),
        "TOOLS_COMMAND": cfg["toolsCommand"],
        "CI_WORKFLOW": ci_name,
        "SETUP_STEP": setup.rstrip("\n"),
        "CLAUDE_ALLOW": ",".join(
            ["Edit", "MultiEdit", "Write", "Read", "Glob", "Grep"] + cfg.get("claudeAllow", [])
        ),
        # sdlc.json `askGatesMerge` (default true): whether the ask tier WITHHOLDS
        # auto-merge. False means the tier only says who should read, and every human
        # PR merges itself on green. one repo turned it off and had
        # the one-line edit silently reverted by the next adopt — hence a setting.
        "TIERS": tiers_on,
        "NO_TIERS": not tiers_on,
        "ASK_GATES_MERGE": cfg.get("askGatesMerge", True),
        "ASK_MERGES_ON_GREEN": not cfg.get("askGatesMerge", True),
        "SHOW_CHANNEL": cfg.get("showChannel", ""),
        "notify": cfg.get("showChannel", ""),
        "ASK_PATHS": " · ".join(f"`{g}`" for g in tiers["ask"]),
        "SHOW_PATHS": " · ".join(f"`{g}`" for g in tiers["show"]),
        "SHOW_CHANNEL_NOTE": f"; Slack `{cfg['showChannel']}` gets the link"
        if cfg.get("showChannel")
        else "",
    }
    # No Claude in CI since 3.7.0: the milestone close reviews locally with Claude and Codex, so
    # claude-review.yml (+ its merge-gate), claude.yml (@claude) and ci-triage.yml are taken out
    # of every repo that still has them, and no repo needs ANTHROPIC_API_KEY.
    for name in ("claude-review.yml", "claude.yml", "ci-triage.yml"):
        remove(ROOT / ".github" / "workflows" / name, "no Claude in CI since sdlc-run 3.7.0")
    for src in sorted((TPL / "workflows").glob("*.yml")):
        dest = ROOT / ".github" / "workflows" / src.name
        if src.name == "ship-show-ask.yml" and not tiers_on:
            continue  # removed above, with the other tier files
        _write(dest, render(src.read_text(encoding="utf-8"), values))

    # --- GitHub issue and PR templates
    # Written once, then the repo owns them: a team that adds a field to its bug form should
    # not have it reverted by the next `adopt`. The shapes mirror the Linear templates in
    # cct:linear-manage, so an issue reads the same whichever tracker it started in.
    for src in sorted((TPL / "github" / "ISSUE_TEMPLATE").iterdir()):
        write(
            ROOT / ".github" / "ISSUE_TEMPLATE" / src.name,
            src.read_text(encoding="utf-8"),
            keep=True,
        )
    write(
        ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
        (TPL / "github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8"),
        keep=True,
    )

    # --- REVIEW.md (kept once written), docs, CLAUDE.md
    write(
        ROOT / "REVIEW.md",
        render((TPL / "REVIEW.md").read_text(encoding="utf-8"), values),
        keep=True,
    )

    tests = cfg.get("tests", "vitest")
    test_rel = cfg.get("testFile") or (
        "tests/test_sdlc.py" if tests == "pytest" else "tests/sdlc.test.ts"
    )
    values["TEST_PATH"] = test_rel
    docs_path = ROOT / docs
    tail = ""
    # The skill was also published as `run-sdlc`; a repo adopted under that name carries its
    # marker, and missing it silently dropped the repo's own section on the next adopt.
    markers = (
        "<!-- sdlc-run adopt keeps everything below this line -->",
        "<!-- run-sdlc adopt keeps everything below this line -->",
    )
    current = docs_path.read_text(encoding="utf-8") if docs_path.exists() else ""
    for marker in markers:
        if marker in current:
            tail = current.split(marker, 1)[1].strip("\n")
            break
    body = render((TPL / "docs-sdlc.md").read_text(encoding="utf-8"), values).rstrip("\n") + "\n"
    _write(docs_path, body + (tail + "\n" if tail else ""))

    claude_md = ROOT / "CLAUDE.md"
    text = claude_md.read_text(encoding="utf-8") if claude_md.exists() else f"# {ROOT.name}\n"
    section = render((TPL / "CLAUDE-section.md").read_text(encoding="utf-8"), values)
    if docs not in text:
        write(claude_md, text.rstrip("\n") + "\n" + section)
    elif re.search(r"`\.changes/|specs in `", text):
        # The section from before the 2026-09-07 layout decision: replace it in place, keep
        # everything around it (it is the one generated block inside a repo-owned file).
        start = text.find("## How work moves: the SDLC")
        end_marker = "dirty source files.\n"
        end = text.find(end_marker, start)
        if end < 0:
            end_marker = "when source files are dirty.\n"
            end = text.find(end_marker, start)
        if start >= 0 and end >= 0:
            write(claude_md, text[:start] + section.lstrip("\n") + text[end + len(end_marker) :])
        else:
            manual.append(
                "CLAUDE.md: the SDLC section still says .changes/ or specs/ -- update it by hand"
            )
            kept.append("CLAUDE.md")
    elif not tiers_on and TIERED_SENTENCE in text:
        # The one tier sentence in the generated section of a repo-owned file: swapped in
        # place when tiers go off, so CLAUDE.md does not promise an `ask` tier that is gone.
        write(claude_md, text.replace(TIERED_SENTENCE, UNTIERED_SENTENCE))
    else:
        kept.append("CLAUDE.md")

    # --- guardrail test
    test_path = ROOT / test_rel
    depth = len(Path(test_rel).parents) - 1
    tvals = {"ROOT_REL": "/".join([".."] * depth) or ".", "ROOT_DEPTH": str(depth)}
    src = TPL / "tests" / ("test_sdlc.py" if tests == "pytest" else "sdlc.test.ts")
    _write(test_path, render(src.read_text(encoding="utf-8"), tvals))
    if tests == "pytest" and tiers_on:
        manual.append(
            "pytest: the test imports scripts/ship_show_ask.py -- scripts/ needs no __init__.py, sys.path is set in the test"
        )
    elif tests != "pytest":
        manual.append(
            f"vitest: make sure the config's `include` covers {test_rel} (the file sets its own 120s testTimeout)"
        )

    # --- migrations: goals/ (the earlier layout) and .claude/plans/ (the tool's scratch)
    goals = ROOT / "goals"
    archive = ROOT / changes_dir / "archive"
    if goals.is_dir():
        for g in sorted(p for p in goals.iterdir() if p.is_dir()):
            if not any(g.iterdir()):
                # `git mv` refuses an empty directory ("fatal: source directory is empty") and
                # used to abort the whole adopt. There is nothing in it to migrate either.
                wrote.append(f"{g.relative_to(ROOT)}/ (empty -- removed, nothing to migrate)")
                if not DRY:
                    g.rmdir()
                continue
            m = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", g.name)
            date, slug = (m.group(1), m.group(2)) if m else (today, g.name)
            key = ""
            for name in ("intent.md", "plan.md", "facts.md"):
                fm = (
                    re.search(
                        r"^linear:\s*([A-Z][A-Z0-9]+-\d+)",
                        (g / name).read_text(encoding="utf-8"),
                        re.M,
                    )
                    if (g / name).exists()
                    else None
                )
                if fm:
                    key = fm.group(1)
                    break
            dest = archive / change_id(date, key, slug)
            wrote.append(
                f"{g.relative_to(ROOT)} -> {dest.relative_to(ROOT)} (migrated; goal.md folded into plan.md '## Done')"
            )
            manual.append(
                f"{dest.relative_to(ROOT)}: read plan.md -- `## Order of work` and `## Revisions` may be missing (the test wants them); set `design:` and `linear:` if known"
            )
            if not DRY:
                dest.parent.mkdir(parents=True, exist_ok=True)
                mv = subprocess.run(
                    ["git", "mv", str(g), str(dest)], cwd=ROOT, capture_output=True, text=True
                )
                if mv.returncode != 0:
                    # Never fatal: a folder git does not track ("fatal: not under version
                    # control") still has to move, and aborting here would also skip
                    # format_written(). A plain rename does the same job without the index.
                    shutil.move(str(g), str(dest))
                goal_md = dest / "goal.md"
                plan_md = dest / "plan.md"
                if goal_md.exists():
                    done = goal_md.read_text(encoding="utf-8").split("## Done condition", 1)
                    if plan_md.exists() and "## Done" not in plan_md.read_text(encoding="utf-8"):
                        plan_md.write_text(
                            plan_md.read_text(encoding="utf-8").rstrip("\n")
                            + "\n\n## Done\n"
                            + (done[1] if len(done) > 1 else "\n"),
                            encoding="utf-8",
                        )
                    subprocess.run(["git", "rm", "-qf", str(goal_md)], cwd=ROOT, check=True)
                for md in dest.glob("*.md"):
                    text = md.read_text(encoding="utf-8")
                    if not text.startswith("---\n"):
                        # A plannotator run before the chain had a frontmatter: give it the minimum.
                        text = (
                            f"---\nlinear: {key or 'none'}\ntype: {md.stem}\nchange: {dest.name}\ndesign: null\nauthor: {git_email()}\nstatus: approved\ncreated: {date}\n---\n\n"
                            + text
                        )
                    text = re.sub(
                        r"^goal:\s*(.+)$",
                        # Grund fuer das noqa unten: das Lambda wird von re.sub() in derselben
                        # Iteration verbraucht, dest kann nicht weiterlaufen.
                        lambda mm: f"change: {dest.name}",  # noqa: B023
                        text,
                        count=1,
                        flags=re.M,
                    )
                    head, sep, body = text[4:].partition("\n---\n")  # inside the frontmatter block
                    fields = {
                        "change": dest.name,
                        "design": "null",
                        "archived_at": today,
                        "created": date,
                    }
                    for k, v in fields.items():
                        if not re.search(rf"^{k}:", head, re.M):
                            head += f"\n{k}: {v}"
                    if md.name == "plan.md" and "## Revisions" not in body:
                        body = (
                            body.rstrip("\n") + "\n\n## Revisions\n\nNone — archived as approved.\n"
                        )
                    md.write_text("---\n" + head + sep + body, encoding="utf-8")
        if not DRY and not any(goals.iterdir()):
            goals.rmdir()
    plans = ROOT / ".claude" / "plans"
    if plans.is_dir() and any(plans.iterdir()):
        hist = ROOT / "docs" / "history" / "plans"
        wrote.append(
            f".claude/plans/ -> {hist.relative_to(ROOT)}/ (migrated: {sum(1 for _ in plans.iterdir())} files)"
        )
        if not DRY:
            hist.mkdir(parents=True, exist_ok=True)
            for f in sorted(plans.iterdir()):
                subprocess.run(
                    ["git", "mv", "-k", str(f), str(hist / f.name)], cwd=ROOT, check=True
                )
                if f.exists():
                    f.rename(hist / f.name)
            plans.rmdir()

    # --- the first change: adopting the chain is itself a change
    changes = ROOT / changes_dir
    migrate_change_ids(changes, today)
    migrate_archive_layout(changes)
    migrate_decision_log(ROOT / designs_dir, today)
    write_design_index(ROOT / designs_dir)
    ticket = sys.argv[sys.argv.index("--ticket") + 1] if "--ticket" in sys.argv else ""
    first = changes / change_id(today, ticket, "adopt-sdlc")
    has_open = changes.exists() and any(
        p.is_dir() and p.name != "archive" for p in changes.iterdir()
    )
    has_archived = archive.exists() and any(p.is_dir() for p in archive.iterdir())
    # A repo that already ran the chain (migrated or not) adopted it back then; no new first change.
    if not has_open and not has_archived:
        cvals = {
            "LINEAR": ticket or "none",
            "CHANGE": first.name,
            "DESIGN": "null",
            "AUTHOR": git_email(),
            "DATE": today,
            "TITLE": f"Adopt the AI-native SDLC in {ROOT.name}",
            "VERIFY": cfg["verify"],
        }
        for name in ("intent.md", "facts.md", "plan.md"):
            write(first / name, render((TPL / "change" / name).read_text(encoding="utf-8"), cvals))
        manual.append(
            f"{first.relative_to(ROOT)}/ is the first change: fill intent/facts/plan from this adoption, gate the plan, archive it when the PR is green"
        )
    (archive).mkdir(parents=True, exist_ok=True) if not DRY else None
    gitkeep = archive / ".gitkeep"
    if not DRY and not any(archive.iterdir()):
        gitkeep.write_text("")

    secrets = (
        [
            "CODE_MANAGER_APP_CLIENT_ID + CODE_MANAGER_APP_PRIVATE_KEY (secrets), SDLC_COOWNER (variable)"
            + (", SDLC_SLACK_BOT_TOKEN (secret)" if cfg.get("showChannel") else "")
        ]
        if tiers_on
        else []
    )
    manual.extend(
        [
            "add the tools target: `{}` -> plannotator install (see {}, 'Install once per machine')".format(
                cfg["toolsCommand"], docs
            ),
            *(["GitHub: " + ", ".join(secrets)] if secrets else []),
            "ruleset on {}: required checks = CI (no merge-gate: remove it from the ruleset AND classic "
            "branch protection if it is there); strict=false; thread resolution=false; allow merge "
            "commits (milestone PRs merge with one){}".format(
                cfg.get("defaultBranch", "master"),
                "; App as pull_request bypass actor" if tiers_on else "",
            ),
            "run `{}` and the guardrail test; commit as `feat(sdlc): adopt the chain`".format(
                cfg["verify"]
            ),
        ]
    )

    manual.append(
        "audit: run `python3 scripts/verify_gate.py audit` once the gate has run (it reports "
        "which declared gates are installed, configured, executed and required); add the "
        "monthly job from references/ci-blueprint.md if you want it scheduled"
    )
    diffs = finish_upgrade() if UPGRADE else ""
    format_written()

    print("-#-#- WROTE -#-#-")
    print("\n".join(wrote) or "(nothing)")
    print("-#-#- KEPT -#-#-")
    print("\n".join(kept) or "(nothing)")
    print("-#-#- MANUAL -#-#-")
    print("\n".join(f"- {m}" for m in manual))
    if diffs:
        print("-#-#- DIFF -#-#-")
        print(diffs)
    if UPGRADE:
        print("(upgrade: only sdlc.json keys and --apply --replace files are written)")
    elif DRY:
        print("(dry run: nothing written)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        # A crash mid-adopt must not leave files in the templates' own formatting: whatever
        # already reached disk still gets the repo's formatter. `written` is cleared by the
        # call inside main(), so this is a no-op after a clean run.
        format_written()
