"""Install the SDLC chain into the current repo from sdlc.json.

    python3 adopt.py [--dry-run] [--upgrade] [--apply --replace FILE] [--migrate] [--preset node|python] [--ticket KEY-123] [--tiers yes|no]
    python3 adopt.py --templates-hash        # what sdlc.json `kitTemplates` should say

`--upgrade` is for a repo that already runs the chain, and it never overwrites or moves anything:
it adds the missing sdlc.json keys with the stack's defaults (never changing a value), stamps
`sdlcVersion`, and lists every file that differs from the kit's copy as `review diff` in MANUAL.
`--upgrade --replace FILE` shows the diff of one kit-owned file; add `--apply` to replace it.
`--migrate` is the one way across kit versions: every kit-owned file replaced as one set (`keep` paths
stay, with a MANUAL line), a file the repo owns at a kit path never overwritten (MANUAL line), archive
folders removed only for a merged PR from the change's own branch, Claude workflows removed only when
they match a kit version, `sdlcVersion` stamped, and the in-flight changes listed with the milestone
gate run each needs. `--dry-run` writes nothing at all. A plain `adopt` stamps too and still refreshes the copies.

`--tiers` writes the engineer's answer to "Use Ship/Show/Ask?" into sdlc.json `tiers`; the
skill asks it on every adopt. Without the flag, a set `tiers` stays and a missing one means
TIERS_DEFAULT.

Idempotent: generated files (hooks, workflows, tiers classifier, docs, test)
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
# `--migrate` brings a repo to this kit in one run: every kit-owned file as one set, the merged
# archive folders removed, the in-flight changes listed with the gate run each needs. A gate or
# hook file is never replaced alone: a gate beside another version's hook or helper reads a pass
# another way, so `--upgrade --replace` of one of them says "use --migrate" and stops.
MIGRATE = "--migrate" in sys.argv
FORCE_KIT = {sys.argv[i + 1] for i, v in enumerate(sys.argv[:-1]) if v == "--force-kit"}
if FORCE_KIT and not MIGRATE:
    sys.exit("--force-kit belongs to --migrate")
if MIGRATE and (UPGRADE or APPLY or REPLACE):
    sys.exit("--migrate takes no --upgrade, --apply or --replace: it replaces the whole kit set")
if UPGRADE and any(r.startswith(("scripts/", ".claude/hooks/")) for r in REPLACE):
    sys.exit(
        "the gate, its hooks and helpers are one version: replacing one alone leaves the repo "
        "with two. Use `python3 adopt.py --migrate`, then re-run the milestone gate on the "
        "changes it lists."
    )
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
    cfg_path = ROOT / "sdlc.json"
    if cfg_path.exists():  # an adopted repo says what it runs; only a fresh adopt needs a preset
        return "python" if json.loads(cfg_path.read_text(encoding="utf-8")).get("tests") == "pytest" else "node"
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
        if old.name in PINNED_ARCHIVES:
            manual.append(f"{old.relative_to(ROOT)}: not moved to {new.relative_to(ROOT)}, because a file links to it; move it and fix the link by hand")
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


# The workflow adopt wrote before 3.12.0 (templates/decision4/decision4.yml): owner and sha vary.
GENERATED_DECISION4 = re.compile(
    r"name: Decision4\non:\n  pull_request:\n    types: \[opened, edited, synchronize, reopened\]\n"
    r"concurrency:\n  group: decision4-\$\{\{ github\.event\.pull_request\.number \}\}\n"
    r"  cancel-in-progress: true\npermissions:\n  contents: read\n  pull-requests: read\n"
    r"jobs:\n  decision4:\n    uses: [\w.-]+/[\w.-]+/\.github/workflows/decision4-check\.yml"
    r"@[0-9a-f]{7,40} # shared Decision4 v1\n*"
)


# The Claude workflows older kits wrote, by the hash of their shape: the repo-specific parts (the
# setup steps, the allowed tools, the CI workflow's name) are masked, everything else must match.
# A workflow of the repo's own, even one named claude.yml, matches no entry and stays.
KIT_WORKFLOWS = {
    "claude-review.yml": {
        "2bec20cb4b2d2f99",
        "441961f74ecdd754",
        "6897e56dc566fe24",
        "912abc195da2c7ca",
        "a7c18f9925d59e49",
    },
    "claude.yml": {
        "08fd464d30e21602",
        "e276c4ad576f9493",
    },
    "ci-triage.yml": {
        "6ef421d7bb6c5dca",
    },
}


def workflow_shape(text: str) -> str:
    text = re.sub(r'--allowedTools ".*"', '--allowedTools "X"', text)
    text = re.sub(r"workflows: \[.*\]", "workflows: [X]", text)
    return re.sub(r"(fetch-depth: 1\n\n).*?(      - name: Run Claude Code)", r"\1S\n\2", text, flags=re.S)


def kit_workflow(path: Path) -> bool:
    shape = workflow_shape(path.read_text(encoding="utf-8"))
    return hashlib.sha256(shape.encode("utf-8")).hexdigest()[:16] in KIT_WORKFLOWS.get(path.name, set())


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
BIOME_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".jsonc"}


def uses_biome() -> bool:
    """Biome is the repo's formatter: it is configured (a biome config, or @biomejs/biome in package.json)
    and its formatter is not switched off in that config."""
    for name in ("biome.json", "biome.jsonc"):
        if (ROOT / name).exists():
            try:
                text = re.sub(r"^\s*//.*$", "", (ROOT / name).read_text(encoding="utf-8"), flags=re.M)
                formatter = (json.loads(text) or {}).get("formatter") or {}
            except (OSError, ValueError, AttributeError):
                return True  # a config we cannot read: assume the default, formatter on
            return formatter.get("enabled", True) is not False
    try:
        pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(pkg, dict) and any("@biomejs/biome" in (pkg.get(k) or {}) for k in ("dependencies", "devDependencies"))


LOCKFILES = ("pnpm-lock.yaml", "package-lock.json", "yarn.lock")  # the order that wins when none is named
MANAGER_LOCKS = {"pnpm": ("pnpm-lock.yaml",), "npm": ("package-lock.json",), "yarn": ("yarn.lock",), "bun": ("bun.lock", "bun.lockb")}


def main_checkout() -> Path | None:
    """The main checkout when ROOT is another worktree of the repo (`git worktree list`: its first entry), else None."""
    out = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    first = next((Path(line[9:]) for line in out if line.startswith("worktree ")), None)
    return first if first is not None and first.resolve() != ROOT.resolve() else None


def active_lockfiles(main: Path) -> list[str]:
    """The lockfiles of the package manager in use: the `packageManager` field of package.json, else every lockfile present."""
    try:
        manager = str(json.loads((ROOT / "package.json").read_text(encoding="utf-8")).get("packageManager", "")).split("@")[0]
    except (OSError, ValueError, AttributeError):
        manager = ""
    if manager in MANAGER_LOCKS:
        return list(MANAGER_LOCKS[manager])
    return [lock for lock in LOCKFILES if (ROOT / lock).exists() or (main / lock).exists()]


def main_checkout_formatter(name: str) -> tuple[Path | None, bool]:
    """(the main checkout's `node_modules/.bin/<name>` when this worktree has no node_modules at all and the active package
    manager's lockfile is byte for byte the same in both, whether the main checkout has the formatter at all)."""
    main = main_checkout()
    binary = main / "node_modules" / ".bin" / name if main else None
    if binary is None or not binary.exists():
        return None, False
    locks = active_lockfiles(main)
    same = bool(locks) and all((ROOT / lock).is_file() and (main / lock).is_file() and (ROOT / lock).read_bytes() == (main / lock).read_bytes() for lock in locks)
    return (binary if same and not (ROOT / "node_modules").exists() else None), True


def format_written() -> None:
    """Run the repo's own formatter over what we just wrote, per file type: biome for the types it handles
    when it is the repo's formatter, prettier for everything else.

    The templates cannot be formatted to suit every repo -- printWidth, quotes and plugins
    all differ -- so a repo with a format check rejects a freshly adopted file.
    The repo's formatter is the authority; we just call it. Not installed, nothing to do."""
    if DRY:
        return
    biome = uses_biome()
    todo, written[:] = list(written), []
    groups = [
        ("biome", "biome format --write", ["format", "--write", "--no-errors-on-unmatched"], [p for p in todo if p.suffix in BIOME_SUFFIXES] if biome else []),
        ("prettier", "prettier --write", ["--write", "--log-level", "warn"], [p for p in todo if p.suffix in PRETTIER_SUFFIXES and not (biome and p.suffix in BIOME_SUFFIXES)]),
    ]
    for name, label, flags, targets in groups:
        binary = ROOT / "node_modules" / ".bin" / name
        if targets and not binary.exists():
            binary, installed = main_checkout_formatter(name)
            if binary is None and installed:
                files = " ".join(str(p.relative_to(ROOT)) for p in targets)
                manual.append(f"{name} is not installed in this worktree and the main checkout's lockfile differs, so adopt did not format what it wrote -- run `{label} {files}` before committing")
        if not targets or binary is None or not binary.exists():
            continue
        out = subprocess.run([str(binary), *flags, *(str(p) for p in targets)], cwd=ROOT, capture_output=True, text=True)
        if out.returncode == 0:
            wrote.append(f"{label} on {len(targets)} written file(s)")
        else:
            detail = (out.stderr or out.stdout).strip().splitlines()
            manual.append(f"{name} failed on the files adopt wrote -- run `{label}` before committing" + (f": {detail[-1]}" if detail else ""))


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


def delivery_values(cfg: dict) -> dict[str, str]:
    """What plan.md's turn caps render by, from `goal` (defaults 150 for a whole run, 30 for a
    milestone close, which is also the default for a project close)."""
    goal = cfg.get("goal") if isinstance(cfg.get("goal"), dict) else {}
    return {
        "RUN_TURNS": str(goal.get("runTurns", 150)),
        "PROJECT_TURNS": str(goal.get("projectTurns", goal.get("milestoneTurns", 30))),  # a project close is a milestone-sized run
    }


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


CHEAP = re.compile(r"format|fmt|lint|ruff|eslint|prettier|biome|oxlint|stylelint|typecheck|tsc|mypy|secret|gitleaks|actionlint|shellcheck|docs")
HEAVY_CI_KEYS = ("unit", "build", "e2e", "e2eTouched")  # the ciCommands that are suites, not installs or lint


def add_heavy_patterns(cfg: dict) -> None:
    """`heavy.patterns` (3.22.0) is the repo's own list of commands that take a heavy slot. The
    classifier knows builds, servers, browsers and `npm test`; a full suite under another name
    (`uv run pytest`, `sh scripts/run-suite.sh`) it cannot know. Seeded once, from the milestone checks
    and the suite jobs of `ciCommands`, for every command that is not a lint/format/type check and
    that the classifier calls light; `{placeholders}` match anything. A repo that has the key keeps it."""
    if "patterns" in (cfg.get("heavy") if isinstance(cfg.get("heavy"), dict) else {}):
        return
    spec = importlib.util.spec_from_file_location("heavy_kit", TPL / "scripts" / "heavy.py")
    heavy = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(heavy)  # type: ignore[union-attr]
    commands = [c if isinstance(c, str) else c.get("run") for c in (cfg.get("checks") or {}).get("milestone", [])]
    commands += [(cfg.get("ciCommands") or {}).get(k) for k in HEAVY_CI_KEYS]
    seeds: list[str] = []
    for cmd in commands:
        if not isinstance(cmd, str) or not cmd.strip() or len(cmd) > 160 or CHEAP.search(cmd):
            continue  # a long shell fragment is the repo's to list
        if heavy.is_heavy(["sh", "-c", cmd], {}):
            continue
        pattern = ".*".join(re.escape(part) for part in re.split(r"\{\w+\}", cmd.strip()))
        if pattern not in seeds:
            seeds.append(pattern)
    if seeds:
        cfg.setdefault("heavy", {})["patterns"] = seeds
        wrote.append(f"sdlc.json: heavy.patterns added ({len(seeds)} suite command(s) from checks.milestone and ciCommands; edit to the repo's own)")


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
    """Preserve remote CI; report that GitHub's required checks are the merge gate."""
    wf = ROOT / ".github" / "workflows"
    kit_names = {p.name for p in (TPL / "workflows").glob("*.yml")}
    own = sorted(p for p in (*wf.glob("*.yml"), *wf.glob("*.yaml")) if p.name not in kit_names)
    if own:
        kept.extend(str(p.relative_to(ROOT)) + " (existing CI, left alone)" for p in own)
    manual.append(
        "CI: GitHub Actions required checks are the merge gate; require them in the rulesets "
        "of the default and protected interior branches. Nothing local gates a push. Keep "
        "existing required checks (references/ci-blueprint.md; references/local-first.md)."
    )


E2E_SCOPED = re.compile(
    r"--grep|--only-changed|--last-failed|--repeat-each|\bseq\b|\bfor\b|\brelated\b"
    r"|\.(?:spec|test)\.\w+|test_\w+\.py|\$specs"
)  # keep equal to verify_gate.E2E_SCOPED


def has_e2e_config() -> bool:
    return (ROOT / "e2e").is_dir() or any(ROOT.glob("playwright.config.*"))


def e2e_gap_note(milestone: list) -> None:
    """MANUAL line when the repo has an E2E suite and `checks.milestone` lacks the full E2E entry or the
    x3 repeat of the changed and flaky specs. adopt never re-locks: the engineer approves again."""
    cmds = [c["run"] if isinstance(c, dict) else c for c in milestone]
    full = any(E2E_CMD.search(run) and not E2E_SCOPED.search(run) for run in cmds)
    repeat = any(E2E_CMD.search(run) and re.search(r"--repeat-each|\bseq\s+3\b|\bin\s+1\s+2\s+3\b", run) for run in cmds)
    if has_e2e_config() and not (full and repeat):
        what = "no full E2E entry" if not full else "no repeat (x3) of the changed and flaky specs"
        manual.append(
            f"sdlc.json checks.milestone has {what} although the repo has an E2E suite: "
            "add the full E2E command and a repeat (x3) of the changed and flaky specs "
            "(the preset's `e2e` and `e2e-repeat` entries); the engineer approves the change "
            "again, adopt never re-locks (an older lock only reports an upgrade gap)"
        )


MIGRATIONS_PATH = re.compile(r"(?:^|/)(?:migrations|migrate)/|^(?:drizzle|alembic)/")


def db_gap_note(cfg: dict) -> None:
    """MANUAL line when tracked files look like database migrations and sdlc.json has no `db.test`:
    without it every database test pays for a full migration run instead of a template copy."""
    if (cfg.get("db") or {}).get("test"):
        return
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout
    found = [
        f
        for f in tracked.splitlines()
        if MIGRATIONS_PATH.search(f) and "node_modules/" not in f and "vendor/" not in f
    ]
    if found:
        folder = re.match(r"(.*?(?:migrations|migrate)|drizzle|alembic)/", found[0]).group(1)
        manual.append(
            f"sdlc.json has no db.test although the repo has migrations ({folder}/): add "
            '`"db": {"test": {"container", "port", "template", "migrate", "migrations"}}` '
            f'with `migrations` set to a glob such as "{folder}/**" (a change rebuilds the '
            "template, one copy per job) and `python3 scripts/db.py test run -- <tests>` "
            "(references/heavy-work.md, Databases)"
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
        run
        for c in base.get("checks", {}).get("milestone", [])
        if E2E_CMD.search(run := c["run"] if isinstance(c, dict) else c)
    )
    found = MAX_FAILURES.search(preset_e2e)
    fail_fast = found.group(0) if found else "--max-failures=10"
    milestone = cfg.get("checks", {}).get("milestone", [])
    moved = False
    for i, check in enumerate(milestone):
        cmd = check["run"] if isinstance(check, dict) else check
        if (
            not WHOLE_SUITE_REPEAT.search(cmd)
            or "--only-changed" in cmd
            or "--grep" in cmd
            or "flaky-specs" in cmd  # the preset's repeat of changed and flaky specs: leave it
        ):
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
    e2e_gap_note(milestone)
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


# The same lists for the files the kit added after 3.18 and the gate imports or a repo may own a
# file of that name: adopt writes one of them over an existing file only when the file is one of
# these (unedited kit copy). test_adopt.py walks the history and fails on a missing hash.
KIT_SPEC = {
    "10c861037f2649ee",
    "b5c5f0e0f76c6562",
    "132e4bf85fcacc3e",
    "2371a851cf373336",
    "52f000090cb648ad",
    "6e76ac5977b05a94",
    "6f3bdf69aec3a169",
    "8958f5cfd24341dc",
    "b317d0a123e1827a",
    "c6542ee0d5796633",
    "d493b854eb70d6ec",
    "be0765bdcddad6b6",
}
KIT_HEAVY = {
    "5deaa2eb45d65844",
    "7dfd1429b4f9cd2d",
    "8b4f8c3dfa44073f",
    "af2eb2673c676348",
    "cc25027d60793b2b",
    "f411b8feb66c33ed",
    "1bb86e7356aa80e0",
    "aa80c7f1cdab2e74",
    "a09c60909df8931b",
    "a13b3e0ac5548a40",
    "133511d3c4625790",
    "d5f94641e353c11a",
}
KIT_DB = {
    "b34ea79ae0841fc5",
    "132fb5df36b3a3ca",
    "392a3cb2e1676489",
    "473a8a34cad7f3e3",
}
KIT_EVIDENCE = {
    "6a317db378861d28",
    "c90008dbca3b8a29",
    "d1ca5373b45d3068",
    "1ee414d2b612b638",
    "a2ad7046f8557477",
    "74b85435656e6566",
    "6c666865c4228267",
    "ac196d166bdc401d",
    "9cb41cc57637e80a",
    "06688e12102ccf68",
}
KIT_PREFLIGHT = {
    "848114ac6dd4a375",
    "d5c15466ff9464be",
    "9e40826faba1db82",
    "020f538fc743c5b0",
    "800076649e5cd346",
}
KIT_CAPTURE = {
    "55464dcaa9fb571a",
    "b83541819543ec15",
    "df45ac2d5c99d0bb",
    "76f341df1ef81a00",
    "b66771e69e06e46f",
    "e43a7d24e86cfe1f",
    "9cd5bdc59852d1a6",
    "2b0aa4a315b83122",
    "ebdfb586c6d92fc8",
}
KIT_HELPER_GUARD = {
    "ca26ffb8ad16e8b3",
}
KIT_PARTS = {
    "scripts/spec.py": KIT_SPEC,
    "scripts/heavy.py": KIT_HEAVY,
    "scripts/db.py": KIT_DB,
    "scripts/evidence.py": KIT_EVIDENCE,
    "scripts/preflight.py": KIT_PREFLIGHT,
    "scripts/capture.py": KIT_CAPTURE,
    ".claude/hooks/helper-guard.sh": KIT_HELPER_GUARD,
}
# Files a 3.18 kit did not ship: a repo may have its own file at the path.
NEW_KIT_FILES = {
    "scripts/spec.py",
    "scripts/heavy.py",
    "scripts/db.py",
    "scripts/evidence.py",
    "scripts/preflight.py",
    "scripts/capture.py",
    ".claude/hooks/helper-guard.sh",
}


def kit_hashes() -> dict[str, set[str]]:
    """Every hook and script version the kit shipped, by installed path (kit-hashes.json)."""
    data = json.loads((Path(__file__).with_name("kit-hashes.json")).read_text(encoding="utf-8"))
    return {rel: set(hs) for rel, hs in data.items()}


def edited_kit_file(path: Path, text: str) -> bool:
    """`--migrate` only: a kit-owned hook or script that matches no shipped kit version is the repo's
    own edit, and stays unless `--force-kit <path>` names it."""
    rel = path.relative_to(ROOT).as_posix()
    if not MIGRATE or rel in FORCE_KIT or not path.is_file() or rel not in (known := kit_hashes()):
        return False
    mine = path.read_bytes()
    return mine != text.encode("utf-8") and hashlib.sha256(mine).hexdigest()[:16] not in known[rel]


def own_file(path: Path, text: str) -> bool:
    """True for a file adopt must not overwrite: one at a path the kit added later that is neither
    the kit's text nor a version the kit shipped."""
    rel = path.relative_to(ROOT).as_posix()
    if rel not in NEW_KIT_FILES or not path.is_file():
        return False
    mine = path.read_bytes()
    return mine != text.encode("utf-8") and hashlib.sha256(mine).hexdigest()[:16] not in KIT_PARTS[rel]


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
    wanted = list(dict.fromkeys(REPLACE))
    for rel in wanted:
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


def merged_pr(root: Path, branch: str) -> bool | None:
    """True when a merged PR came from exactly `branch` (gh is asked for that head), None when gh cannot say."""
    try:
        out = subprocess.run(
            ["gh", "pr", "list", "--head", branch, "--state", "merged", "--limit", "1", "--json", "headRefName"],
            cwd=root, capture_output=True, text=True, timeout=60,
        )  # fmt: skip
        return bool(json.loads(out.stdout or "[]")) if out.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def _slug(value: object, prefix: str) -> str | None:
    """A slug from a decisions.json field: a string (`slug` or the whole branch name) or a dict with
    `slug`. "" for a missing field, None for a shape adopt cannot read."""
    if value is None:
        return ""
    if isinstance(value, dict):
        value = value.get("slug", "")
    if not isinstance(value, str):
        return None
    return value.removeprefix(prefix)


def own_branch(folder: Path, cfg: dict, head: str) -> bool:
    """`head` is a branch of this change: milestone/<slug>[-n], project/<slug>, or a branch the
    change's own plan.md names (the folder name gives the slug when decisions.json names none).
    Nothing a PR body says counts, and a decisions.json adopt cannot read means the branch is unknown."""
    decisions = read_decisions_of(folder)
    if not isinstance(decisions, dict):
        return False
    prefix = (cfg.get("milestones") or {}).get("branchPrefix", "milestone/")
    pprefix = (cfg.get("projects") or {}).get("branchPrefix", "project/")
    slug = _slug(decisions.get("milestone"), prefix)
    project = _slug(decisions.get("project"), pprefix)
    if slug is None or project is None:
        return False
    slug = slug or re.sub(r"^([A-Z][A-Z0-9]+-\d+-)?", "", re.sub(r"^\d{4}-\d{2}-\d{2}-", "", folder.name))
    if re.fullmatch(re.escape(f"{prefix}{slug}") + r"(-\d+)?", head) or (project and head == f"{pprefix}{project}"):
        return True
    try:
        plan = (folder / "plan.md").read_text(encoding="utf-8")
    except OSError:
        return False
    return "/" in head and re.search(rf"(?<![\w/.-]){re.escape(head)}(?![\w/-])", plan) is not None


def read_decisions_of(folder: Path) -> object:
    """The change's decisions: `state/intake.json` (layout 4's name for it), `state/decisions.json`, else `decisions.json`."""
    for path in (folder / "state" / "intake.json", folder / "state" / "decisions.json", folder / "decisions.json"):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
    return {}


def own_branches(folder: Path, cfg: dict) -> list[str]:
    """The branches the change declares, as names to ask gh about: milestone/<slug>, milestone/<slug>-1 to -<last M of
    plan.md>, project/<slug>, and a `branch:` field (decisions or a line of plan.md). Nothing is guessed from paths in the
    plan. [] when the decisions cannot be read."""
    decisions = read_decisions_of(folder)
    prefix = (cfg.get("milestones") or {}).get("branchPrefix", "milestone/")
    pprefix = (cfg.get("projects") or {}).get("branchPrefix", "project/")
    slug = _slug(decisions.get("milestone"), prefix) if isinstance(decisions, dict) else None
    project = _slug(decisions.get("project"), pprefix) if isinstance(decisions, dict) else None
    if slug is None or project is None:
        return []
    slug = slug or re.sub(r"^([A-Z][A-Z0-9]+-\d+-)?", "", re.sub(r"^\d{4}-\d{2}-\d{2}-", "", folder.name))
    try:
        plan = (folder / "plan.md").read_text(encoding="utf-8")
    except OSError:
        plan = ""
    last = max([1, *(int(n) for n in re.findall(r"\bM(\d+)\b", plan))])
    declared = [str(decisions.get("branch", ""))] if isinstance(decisions, dict) else []
    declared += re.findall(r"^\s*branch:\s*([\w.-]+/[\w./-]+?)\s*$", plan, re.M)
    found = [f"{prefix}{slug}", *(f"{prefix}{slug}-{n}" for n in range(1, last + 1)), *([f"{pprefix}{project}"] if project else []), *(b for b in declared if b)]
    return list(dict.fromkeys(found))


TALLY = "IMPORTANT: <n>  NITS: <m>  SHA: <head sha>"
SHORT_TALLY = re.compile(r"IMPORTANT: <n>  NITS: <m>(?!  SHA: <head sha>)")


def add_review_tally(review_md: Path) -> None:
    """The guardrail test wants the full tally line (with the commit it binds to) in the repo's own REVIEW.md.
    A shorter form is completed in place; a missing line is appended to the end of the `## Cap the nits`
    section; with no such section, say so."""
    if not review_md.is_file() or TALLY in (text := review_md.read_text(encoding="utf-8")):
        return
    if SHORT_TALLY.search(text):
        wrote.append("REVIEW.md: the review tally line now carries `SHA: <head sha>`")
        if not DRY:
            review_md.write_text(SHORT_TALLY.sub("IMPORTANT: <n>  NITS: <m>  SHA: <head sha>", text), encoding="utf-8")
        return
    m = re.search(r"^## Cap the nits[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        manual.append(f"REVIEW.md has no `## Cap the nits` section to hold the tally line the guardrail test needs: add `{TALLY}` to it by hand")
        return
    wrote.append("REVIEW.md: added the review tally line under `## Cap the nits`")
    if not DRY:
        body = m[1].rstrip("\n") + "\n\nOpen the review with the tally in this exact shape on its own line, so the merge gate can read it:\n\n    " + TALLY + "\n\n"
        review_md.write_text(text[: m.start(1)] + body + text[m.end(1) :], encoding="utf-8")


def migrate_plan(cfg: dict) -> dict:
    """The reads of `--migrate` (gh, branches, every decisions.json), made before anything is
    written, so a half-migrated tree cannot happen. Returns what to remove and what to list."""
    changes = ROOT / cfg.get("changesDir", "changes")
    if not changes.is_dir():
        changes = ROOT / ".changes"
    folders = archived_changes(changes / "archive")
    remove_list, kept_lines = [], []
    for folder in folders:
        branches, answers = own_branches(folder, cfg), []
        for branch in branches:  # the change's own branches, one question each; the first merged PR settles it
            answers.append(merged_pr(ROOT, branch))
            if answers[-1]:
                break
        rel = folder.relative_to(ROOT)
        if any(answers):
            remove_list.append(folder)
        else:
            looked = f" (looked for {', '.join(branches)}{'; gh could not answer' if None in answers else ''})" if branches else " (no branch name could be read from decisions.json)"
            kept_lines.append(f"{rel}: kept, gh could not confirm a merged PR from {folder.name}'s own branch{looked}")
    moved = True
    while moved:  # a kept folder's own files count as referrers for the others, so repeat until nothing moves
        moved = False
        for folder in list(remove_list):
            if ref := referrer(folder.name, remove_list):
                remove_list.remove(folder)
                PINNED_ARCHIVES.add(folder.name)
                kept_lines.append(f"{folder.relative_to(ROOT)}: kept, referenced by {ref} (a link would break)")
                moved = True
    return {
        "remove": remove_list,
        "kept": kept_lines,
        "open": unmerged_branches(ROOT, cfg.get("defaultBranch") or "main"),
        "had": {rel for rel in kit_script_paths() if (ROOT / rel).exists()},  # before this run writes any
    }


def referrer(name: str, doomed: list[Path], skip: set[str] = frozenset()) -> str | None:
    """A tracked file that names the folder `name` (in its text, or as a symlink's target) and is not inside a
    folder about to be removed. A search that fails counts as a hit: an incomplete scan keeps the folder."""
    out = subprocess.run(["git", "grep", "-lIF", "--", name], cwd=ROOT, capture_output=True, text=True)
    if out.returncode not in (0, 1):
        return "(the reference search failed: the scan is incomplete)"
    root = ROOT.resolve()
    inside = lambda path: any(path.is_relative_to(d.resolve()) for d in doomed)  # noqa: E731
    for hit in out.stdout.splitlines():  # the file itself, not what a link points at
        if hit not in skip and not inside(root / hit):
            return hit
    for link in tracked_symlinks():  # git grep reads a link's own text, never what it points at
        if link not in skip and not inside(root / link) and inside((root / link).parent.joinpath((root / link).readlink()).resolve()):
            return link
    return None


def tracked_symlinks() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-s"], cwd=ROOT, capture_output=True, text=True).stdout
    return [line.partition("\t")[2] for line in out.splitlines() if line.startswith("120000")]


PINNED_ARCHIVES: set[str] = set()  # archives kept because something links to them: the layout step leaves them where they are

def kit_script_paths() -> list[str]:
    return [f"scripts/{p.name}" for p in sorted((TPL / "scripts").glob("*")) if p.is_file()]


def migrate_script_lists(plan: dict, cfg: dict) -> None:
    """A repo that lists kit scripts for its own tooling (a lint exclude, a Makefile list, a test's tuple)
    breaks when a release adds a script. For each tracked text file outside changes/ that lists the new
    script's neighbours one per line (`  "scripts/db.py",`) and lacks the new one, the first such line is
    copied with the new path right after it, same quoting and indentation. A line that holds several
    scripts (an inline tuple) cannot be copied: it becomes a MANUAL line."""
    kit = kit_script_paths()
    new = [rel for rel in kit if rel not in plan["had"] and (rel in pending or (ROOT / rel).exists())]
    old = [rel for rel in kit if rel in plan["had"]]
    if not new or not old:
        return
    changes = cfg.get("changesDir", "changes")
    entry = re.compile(r"^(\s*(?:[-*]\s+)?[\"']?)(" + "|".join(map(re.escape, old)) + r")([\"']?\s*[,\\]?\s*)$")
    inline = re.compile("|".join(r"[\"']" + re.escape(rel) + r"[\"']" for rel in old))
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True).stdout.split("\0")
    skip = {"sdlc.json", *cfg.get("keep", []), *kit, *(f".claude/hooks/{p.name}" for p in (TPL / "hooks").glob("*"))}
    for rel in filter(None, tracked):
        path = ROOT / rel
        if rel in skip or path.is_symlink() or rel.startswith(changes + "/") or rel.endswith((".lock", "-lock.json", ".lockb")):
            continue
        try:
            text = path.read_text(encoding="utf-8") if path.is_file() and path.stat().st_size < 1_000_000 else ""
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.split("\n")
        for script in new:
            if script in "\n".join(lines):
                continue
            at = next((i for i, line in enumerate(lines) if entry.match(line) and list_line_ok(rel, lines, i)), None)
            if at is not None:
                m = entry.match(lines[at])
                edited = insert_list_line(lines, at, f"{m[1]}{script}", m[3])
                if not list_still_valid(rel, text, "\n".join(edited), script, m[2]):
                    manual.append(f"{rel}: adding {script} next to {m[2]} would not leave a valid list; left untouched, add it by hand if it must list every kit script")
                    continue
                lines = edited
                wrote.append(f"{rel}: added {script} next to {m[2]} (the repo lists kit scripts)")
            elif any(len({x for x in inline.findall(line)}) > 1 for line in lines):
                manual.append(f"{rel}: lists kit scripts on one line, a shape adopt cannot copy; add {script} to it by hand if it must list them all")
        if not DRY and "\n".join(lines) != text:
            path.write_text("\n".join(lines), encoding="utf-8")


def list_line_ok(rel: str, lines: list[str], i: int) -> bool:
    """A Makefile takes an element only in a variable assignment (the head line or its `\\` continuations),
    never in a tab-indented recipe, where a new line would be a new command."""
    if Path(rel).name not in ("Makefile", "GNUmakefile", "makefile") and not rel.endswith((".mk", ".mak")):
        return True
    j = i
    while j > 0 and lines[j - 1].rstrip().endswith("\\"):
        j -= 1
    return j < i and not lines[j].startswith("\t") and bool(re.match(r"\s*(export\s+)?[A-Za-z_][\w.-]*\s*[:+?!]*=", lines[j]))


def insert_list_line(lines: list[str], at: int, head: str, tail: str) -> list[str]:
    """The new element goes after the matched one when that has a separator, else before it (it may be the
    last), above any comment that sits on it, taking the separator from the list's previous element."""
    if tail.rstrip().endswith((",", "\\")):
        return [*lines[: at + 1], head + tail, *lines[at + 1 :]]
    j = at
    while j > 0 and lines[j - 1].strip().startswith(("#", "//")):
        j -= 1
    k = j
    while k > 0 and not lines[k - 1].strip():
        k -= 1
    before = lines[k - 1].rstrip() if k else ""
    sep = "," if not before or before.endswith(("[", "(", "{", ",")) else (" \\" if before.endswith("\\") else "")
    return [*lines[:j], f"{head}{tail.rstrip()}{sep}", *lines[j:]]


def list_still_valid(rel: str, before: str, after: str, script: str, old: str) -> bool:
    """For .py, .toml and .json: the edited file still parses, and both paths are separate string elements."""
    suffix = Path(rel).suffix

    def strings(text: str) -> set[str] | None:
        try:
            if suffix == ".py":
                import ast

                return {n.value for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
            if suffix == ".toml":
                import tomllib

                data = tomllib.loads(text)
            elif suffix == ".json":
                data = json.loads(text)
            else:
                return set()
        except (ImportError, SyntaxError, ValueError):
            return None
        found: set[str] = set()

        def walk(node: object, in_list: bool) -> None:
            if isinstance(node, dict):
                for v in node.values():
                    walk(v, False)
            elif isinstance(node, list):
                for v in node:
                    walk(v, True)
            elif isinstance(node, str) and in_list:
                found.add(node)

        walk(data, False)
        return found

    if suffix == ".toml":
        try:
            import tomllib  # noqa: F401 -- Python 3.11+; without it a TOML edit cannot be checked, so none is made
        except ImportError:
            return False
    if suffix not in (".py", ".toml", ".json") or strings(before) is None:
        return True  # nothing to check with (or the file did not parse before the edit)
    got = strings(after)
    return got is not None and script in got and old in got


def migrate_archives(plan: dict) -> None:
    """An archive folder is removed (the owner's rule is no archive) only when a merged PR came from
    the change's own branch, and only its tracked files; the others are listed. Runs before the
    layout migration, whose staged renames would stop `git rm`. A dry run prints the same lines."""
    manual.extend(plan["kept"])
    for folder in plan["remove"]:
        rel = folder.relative_to(ROOT)
        if DRY:
            wrote.append(f"{rel} (would be removed: its PR merged, no archive)")
            continue
        tracked = subprocess.run(["git", "ls-files", "--", str(folder)], cwd=ROOT, capture_output=True, text=True)
        gone = tracked.stdout.strip() and subprocess.run(
            ["git", "rm", "-rq", "--", str(folder)], cwd=ROOT, capture_output=True
        ).returncode == 0  # fmt: skip
        if folder.exists() or not gone:
            manual.append(f"{rel}: kept, untracked files remain (or git could not remove it): check it by hand")
        else:
            wrote.append(f"{rel} (removed: its PR merged, no archive)")


def migrate_report(cfg: dict, plan: dict) -> None:
    """Every change still in flight gets the one gate run that writes the new report."""
    changes = ROOT / cfg.get("changesDir", "changes")
    for folder in sorted(changes.glob("*")) if changes.is_dir() else ():
        if not (folder.is_dir() and folder.name != "archive" and (
            (folder / "lock.json").exists() or (folder / "state" / "lock.json").exists()
        )):
            continue
        for branch in (b for b in plan["open"] if own_branch(folder, cfg, b)):
            manual.append(
                f"{folder.name} is in flight on {branch}: `git switch {branch}`, then run "
                f"`python3 scripts/verify_gate.py milestone {folder.name}` once (it writes the report the new gate reads)"
            )


def unmerged_branches(root: Path, default: str) -> list[str]:
    """Branches not merged into the default branch (local and origin) and without a merged PR
    (a squash merge leaves the branch looking unmerged), plus the heads of open PRs."""
    base = f"origin/{default}" if subprocess.run(
        ["git", "rev-parse", "--verify", "-q", f"origin/{default}"], cwd=root, capture_output=True
    ).returncode == 0 else default  # fmt: skip
    out = subprocess.run(
        ["git", "for-each-ref", "--no-merged", base, "--format=%(refname:short)", "refs/heads", "refs/remotes/origin"],
        cwd=root, capture_output=True, text=True,
    )  # fmt: skip
    names = [n.removeprefix("origin/") for n in out.stdout.split()] if out.returncode == 0 else []
    names = [n for n in names if not merged_pr(root, n)]  # a squash merge leaves the branch looking unmerged
    try:
        pr = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json", "headRefName"],
            cwd=root, capture_output=True, text=True, timeout=60,
        )  # fmt: skip
        names += [str(p.get("headRefName", "")) for p in json.loads(pr.stdout or "[]")] if pr.returncode == 0 else []
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return list(dict.fromkeys(n for n in names if n and n not in (default, "origin", "HEAD")))


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
        if cfg.get("delivery") == "feature-prs":
            open_changes = ROOT / cfg.get("changesDir", "changes")
            approved = [  # a lock is the approval; a merged change's folder is already gone
                d.name for d in sorted(open_changes.iterdir())
                if d.is_dir() and d.name != "archive" and any((d / n).exists() for n in ("lock.json", "state/lock.json"))
            ] if open_changes.is_dir() else []  # fmt: skip
            if approved:
                sys.exit(
                    f"{', '.join(approved)} was approved with per-feature PR delivery and is not merged: "
                    "sdlc-run 3.24.0 removed that mode: finish or re-approve it as one milestone PR first, then run adopt again."
                )
            manual.append(
                'sdlc.json: delivery "feature-prs" is gone (sdlc-run 3.24.0): every change now delivers one '
                'milestone PR, features are commits on its branch. Set "delivery": "one-go" to silence this'
            )
        kept.append("sdlc.json")
        if UPGRADE and "layout" not in cfg:  # never a silent switch: new changes of this repo stay on layout 3
            manual.append(
                'layout: new changes use the three-document layout (spec.md, design.md, tasks.md) when '
                'sdlc.json has `"layout": 4`; this repo has no `layout`, so new changes keep intent, facts and plan. '
                "Add it to switch (a change already in flight finishes on the layout it started with)"
            )
        plan = migrate_plan(cfg) if MIGRATE else {}
        if not UPGRADE:
            cfg["kitTemplates"] = templates_hash()
            apply_tiers_answer(cfg)
    else:
        cfg = json.loads((TPL / "presets" / f"{preset}.json").read_text(encoding="utf-8"))
        cfg["defaultBranch"] = default_branch()
        cfg["layout"] = 4  # a new adoption starts on the three-document layout
        cfg["kitTemplates"] = templates_hash()
        apply_tiers_answer(cfg)
        add_ci_paths(cfg, preset)
        add_ci_commands(cfg, preset)
        add_builders(cfg)
        add_heavy_patterns(cfg)
        stamp_version(cfg, fresh=True)
        plan = migrate_plan(cfg) if MIGRATE else {}
        write(cfg_path, json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
        manual.append(
            f"sdlc.json was created from the {preset} preset -- check linear.team/project, verify, blocked"
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
        if not MIGRATE:  # --migrate works with the repo's own settings, never the preset's defaults
            add_ci_paths(cfg, preset)
            add_ci_commands(cfg, preset)
        add_builders(cfg)
        add_heavy_patterns(cfg)
        check_rules(cfg)
        if "claude" in cfg:
            cfg.pop("claude")
            wrote.append("sdlc.json: claude removed (no Claude in CI since sdlc-run 3.7.0)")
        if not UPGRADE and not MIGRATE:
            migrate_test_cost(cfg, preset)
        else:
            if "--repeat-each" in json.dumps(cfg.get("checks", {})):
                manual.append(
                    "sdlc.json: checks.milestone repeats the whole suite (--repeat-each); `adopt` rewrites it, --upgrade leaves it"
                )
            e2e_gap_note(cfg.get("checks", {}).get("milestone", []))
        stamp_version(cfg, fresh=False)
    changed = UPGRADE and json.dumps(cfg, sort_keys=True) != cfg_before
    if (changed and not DRY_RUN) or (
        not UPGRADE and not DRY and cfg_path.exists() and "sdlc.json" in kept
    ):
        cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        # Not via write(): sdlc.json is the repo's own file and only gets fields merged in.
        # It still has to reach format_written(), or a prettier repo rejects the commit.
        written.append(cfg_path)
    if MIGRATE:
        migrate_archives(plan)  # before the layout moves: their staged renames would stop git rm
    changes_dir = cfg.get("changesDir", "changes")
    designs_dir = cfg.get("designsDir", "docs/designs")
    living = any((ROOT / "specs").glob("*/rules")) or any((ROOT / "specs").glob("*/manifest.yaml"))
    for old, new in ((ROOT / ".changes", ROOT / changes_dir), (ROOT / "specs", ROOT / designs_dir)):
        if old.name == "specs" and living:  # living specs (rules/, manifest.yaml) are not old design docs
            continue
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
    # The one known template sentence that sent the closer to `review-fix-run` (a second review):
    # replaced in place; every custom rule of the repo's REVIEW.md stays.
    old_review = re.compile(
        r"The review \(`cct:review-code-run` with one `review-fix-run` round\) runs once per milestone,"
    )
    if UPGRADE and review_md.exists() and old_review.search(review_md.read_text(encoding="utf-8")):
        manual.append(
            "REVIEW.md: the template sentence `The review (`cct:review-code-run` with one `review-fix-run` round) "
            "runs once per milestone,` starts a second review; --upgrade never edits REVIEW.md (it is yours), so "
            "replace it by hand with `The review (`cct:review-code-run changes <parent> --codex`, then one fix "
            "round on its findings) runs once per milestone,`, or run `adopt` (without --upgrade), which does it"
        )
    if not UPGRADE and review_md.exists() and old_review.search(review_md.read_text(encoding="utf-8")):
        wrote.append("REVIEW.md: review-fix-run sentence -> review-code-run changes, then one fix round")
        if not DRY:
            review_md.write_text(
                old_review.sub(
                    "The review (`cct:review-code-run changes <parent> --codex`, then one fix round "
                    "on its findings) runs once per milestone,",
                    review_md.read_text(encoding="utf-8"),
                ),
                encoding="utf-8",
            )
    if MIGRATE:
        add_review_tally(review_md)
    docs = cfg.get("docs", "docs/sdlc.md")
    today = dt.date.today().isoformat()
    keep_paths = set(cfg.get("keep", []))

    def _write(path: Path, text: str, **kw: object) -> None:
        if str(path.relative_to(ROOT)) in keep_paths:
            kept.append(str(path.relative_to(ROOT)) + " (sdlc.json keep)")
            if MIGRATE:
                manual.append(
                    f"{path.relative_to(ROOT)} is in sdlc.json `keep`, so it was not replaced: it may "
                    f"belong to an older kit version; compare it with the kit's copy by hand"
                )
            return
        if own_file(path, text):  # a path the kit added after 3.18: the repo's own file stays
            manual.append(
                f"{path.relative_to(ROOT)}: a file of your own (it matches no kit version), not "
                f"overwritten. The kit ships a {path.name} too and its scripts import it: merge the "
                f"two, or move yours and run `adopt` again"
            )
            return
        if edited_kit_file(path, text):
            rel = path.relative_to(ROOT).as_posix()
            sub = "hooks" if rel.startswith(".claude/hooks/") else "scripts"
            manual.append(
                f"{rel} matches no shipped kit version, so it stays (compare: `diff {rel} "
                f"{TPL / sub / path.name}`); `--migrate --force-kit {rel}` replaces it with the kit's copy"
            )
            return
        write(path, text, **kw)  # type: ignore[arg-type]

    # --- hooks + settings.json
    hooks_dir = ROOT / ".claude" / "hooks"
    for src in sorted((TPL / "hooks").glob("*.sh")):
        _write(hooks_dir / src.name, src.read_text(encoding="utf-8"), executable=True)
    for src in sorted((TPL / "hooks").glob("*.py")):  # helpers the hooks import (F15)
        _write(hooks_dir / src.name, src.read_text(encoding="utf-8"))

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
    # A LIST, not a dict keyed by event: PreToolUse carries several entries -- gate-bash.sh for
    # what sdlc.json blocks, chain-gate.sh for the chain's own gates -- and a dict silently
    # kept only the last one.
    spec = [
        ("SessionStart", None, "session-check.sh", 5),
        ("UserPromptSubmit", None, "turn-start.sh", 5),
        ("PermissionRequest", "ExitPlanMode", "plan-gate.sh", 345600),
        ("PreToolUse", "Bash", "gate-bash.sh", 5),
        ("PreToolUse", "Bash", "pr-gate.sh", 20),
        ("PreToolUse", "Bash", "helper-guard.sh", 5),
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
    ignored = any(  # a `*.py` rule leaves the helpers untracked while the `.sh` hooks stay
        subprocess.run(["git", "check-ignore", "-q", f".claude/hooks/{name}"], cwd=ROOT).returncode == 0
        for name in ("gate-bash.sh", "goal_active.py")
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
                "!.claude/hooks/*.py",
            )
            if line not in lines
        ]
        if add:
            write(
                gi,
                "\n".join(lines + ["", "# the SDLC hooks are the repo's, not the laptop's"] + add)
                + "\n",
            )

    # --- tiers and classifier (CODEOWNERS is repository-owned)
    # sdlc.json `tiers` (default TIERS_DEFAULT): Ship/Show/Ask. False is for a repo with one owner --
    # there is nobody to ask and nobody to show, so every PR auto-merges on green. adopt
    # writes none of the three tier files and removes any that exist.
    tiers_on = cfg.get("tiers", TIERS_DEFAULT)
    tiers_path = ROOT / ".github" / "tiers.json"
    tiers = {"ask": [], "show": []}  # what ASK_PATHS / SHOW_PATHS read when tiers is off
    if not tiers_on:
        # Only what adopt generated goes, recognised by the header its template opens with: a
        # path in `keep` or a hand-written file stays (KEPT).
        removed = False
        for p in (
            ROOT / ".github" / "workflows" / "ship-show-ask.yml",
            ROOT / "scripts" / "ship_show_ask.py",
            tiers_path,
        ):
            if not p.exists():
                continue
            rel = str(p.relative_to(ROOT))
            head = p.read_text(encoding="utf-8", errors="replace")
            generated = {
                ".github/workflows/ship-show-ask.yml": head.startswith(TIER_WORKFLOW_MARKER),
                "scripts/ship_show_ask.py": head.startswith(TIER_SCRIPT_MARKER),
                ".github/tiers.json": TIER_JSON_MARKER in head,
            }[rel]
            if rel in keep_paths:
                kept.append(f"{rel} (sdlc.json keep)")
            elif not generated:
                kept.append(f"{rel} (hand-written, not adopt's)")
            else:
                remove(p, "sdlc.json tiers=false")
                removed = True
        if removed:
            manual.append(
                f"ruleset on {cfg.get('defaultBranch', 'master')}: remove the GitHub App from the "
                "pull_request bypass actors; delete the secrets CODE_MANAGER_APP_CLIENT_ID, "
                "CODE_MANAGER_APP_PRIVATE_KEY and SDLC_SLACK_BOT_TOKEN "
                "(Ship/Show/Ask is off, so the tier workflow that used them is gone)"
            )
    elif tiers_path.exists():
        tiers = json.loads(tiers_path.read_text(encoding="utf-8"))
        kept.append(".github/tiers.json")
    else:
        d = TIER_DEFAULTS[preset]
        tiers = {
            "_comment": f"Ship/Show/Ask by blast radius. First tier whose glob matches a changed file wins, in this order. Read by scripts/ship_show_ask.py, .github/workflows/ship-show-ask.yml and the sdlc guardrail test; CODEOWNERS is maintained by the repository team, never by adopt. {docs} explains the tiers.",
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
        "design_index.py",
        "marks.py",
        "sdlc_version.py",
        "spec.py",
        "heavy.py",
        "db.py",
        "evidence.py",
        "preflight.py",
        "capture.py",
    ):
        _write(ROOT / "scripts" / script, (TPL / "scripts" / script).read_text(encoding="utf-8"))
    # sdlc_status.py runs from the plugin now and is never copied into a repo.
    remove(ROOT / "scripts" / "sdlc_status.py", "now runs from the plugin")
    for name in ("Makefile", "package.json"):  # named, never edited: they are the repo's own
        named = ROOT / name
        for no, line in enumerate(named.read_text(encoding="utf-8").splitlines(), 1) if named.is_file() else ():
            if "scripts/sdlc_status.py" in line:
                manual.append(
                    f"{name}:{no} names scripts/sdlc_status.py, which no longer exists (it runs from the plugin): edit that line"
                )
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

    # CODEOWNERS is a team-repo choice. Never create, edit or delete it, even
    # when an older adopt generated it or tiers/codeowners settings change.

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
        old_wf = ROOT / ".github" / "workflows" / name
        if not old_wf.exists():
            continue
        if kit_workflow(old_wf):
            remove(old_wf, "no Claude in CI since sdlc-run 3.7.0")
        else:
            manual.append(
                f".github/workflows/{name} matches no kit version, so it stays; remove it by hand if "
                f"you no longer want Claude in CI. Until you do, the guardrail test fails "
                f"(`test_docs_and_workflows_exist_and_are_linked` in tests/test_sdlc.py, or "
                f"`docs and workflows exist and are linked from CLAUDE.md` in tests/sdlc.test.ts)"
            )
    # Decision4 is advisory (no workflow) since 3.12.0. A repo adopted before keeps the workflow
    # adopt wrote then, which calls the shared checker and fails on every PR event. Only a file
    # that matches the generated one exactly goes, and not when sdlc.json `keep` lists it; a
    # workflow of the repo's own, even one named decision4.yml, stays.
    d4 = ROOT / ".github" / "workflows" / "decision4.yml"
    d4_lock = ROOT / ".decision4.lock"
    if (
        d4.exists()
        and ".github/workflows/decision4.yml" not in keep_paths
        and GENERATED_DECISION4.fullmatch(d4.read_text(encoding="utf-8"))
    ):
        remove(d4, "Decision4 is advisory since sdlc-run 3.12.0: no workflow")
        if ".decision4.lock" not in keep_paths:
            remove(d4_lock, "pinned the removed Decision4 checker")
    old_tier = ROOT / ".github" / "workflows" / "ship-show-ask.yml"
    if (
        tiers_on
        and old_tier.exists()
        and ".github/workflows/ship-show-ask.yml" not in keep_paths
        and "SDLC_COOWNER" in old_tier.read_text(encoding="utf-8")
    ):
        manual.append(
            "ship-show-ask.yml no longer requests the Show reviewer (vars.SDLC_COOWNER, removed in "
            "sdlc-run 3.18.0): add the reviewer to CODEOWNERS, or a `gh pr edit --add-reviewer` step by hand."
        )
    for src in sorted((TPL / "workflows").glob("*.yml")):
        dest = ROOT / ".github" / "workflows" / src.name
        if src.name == "ship-show-ask.yml" and not tiers_on:
            continue  # removed above, with the other tier files
        _write(dest, render(src.read_text(encoding="utf-8"), values))

    # --- GitHub issue and PR templates
    # Issue forms and the PR template are written once, then repo-owned. The shapes mirror the
    # Linear templates in cct:linear-manage, so an issue reads the same whichever tracker it
    # started in.
    for src in sorted((TPL / "github" / "ISSUE_TEMPLATE").iterdir()):
        write(
            ROOT / ".github" / "ISSUE_TEMPLATE" / src.name,
            src.read_text(encoding="utf-8"),
            keep=True,
        )
    # Decision4 is advisory: the boundary map, the AGENTS.md section and the PR-template
    # section, never a workflow. Anything already there stays the repo's.
    from decision4_assets import asset_changes

    for path, text in asset_changes(ROOT):
        _write(path, text)
    manual.append(
        "Decision4 (advisory, nothing checks it): review the starter boundary-map.yaml so each "
        "path has the right lowest level. The AGENTS.md section and PR-template section are "
        "installed once; edit them in the repo."
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
    if not has_open and not has_archived and not MIGRATE:
        cvals = {
            "LINEAR": ticket or "none",
            "CHANGE": first.name,
            "DESIGN": "null",
            "AUTHOR": git_email(),
            "DATE": today,
            "TITLE": f"Adopt the AI-native SDLC in {ROOT.name}",
            "VERIFY": cfg["verify"],
            **delivery_values(cfg),
        }
        if cfg.get("layout") == 4:  # the configured layout: one spec.md (scope S, no UX), pinned in decisions.json
            text = render((TPL / "change" / "spec.md").read_text(encoding="utf-8"), cvals)
            text = re.sub(r"^scope: .*$", "scope: S", text, count=1, flags=re.M)
            text = re.sub(r"^ux: .*$", "ux: none", text, count=1, flags=re.M)
            text = re.sub(r"^prototype: .*\n", "", text, count=1, flags=re.M)
            write(first / "spec.md", text)
            write(first / "decisions.json", json.dumps({"layout": 4}) + "\n")
            manual.append(
                f"{first.relative_to(ROOT)}/ is the first change: fill spec.md from this adoption, gate it; "
                "the next change removes its folder once the PR merged (`sdlc_status.py sweep-merged`)"
            )
        else:
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
            "CODE_MANAGER_APP_CLIENT_ID + CODE_MANAGER_APP_PRIVATE_KEY (secrets, normally already set; no action)"
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

    db_gap_note(cfg)
    manual.append(
        "audit: run `python3 scripts/verify_gate.py audit` once the gate has run (it reports "
        "which declared gates are installed, configured, executed and required); add the "
        "monthly job from references/ci-blueprint.md if you want it scheduled"
    )
    diffs = finish_upgrade() if UPGRADE else ""
    if MIGRATE:
        migrate_script_lists(plan, cfg)
        migrate_report(cfg, plan)
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
