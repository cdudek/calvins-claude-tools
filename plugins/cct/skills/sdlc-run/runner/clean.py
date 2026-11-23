#!/usr/bin/env python3
"""sdlc clean: remove the copies that sdlc-run 3.x `adopt` installed into a product repo.

    sdlc clean <repo> [--apply] [--json]

4.0 installs nothing in product repos. Dry run by default. `--apply` prepares the removals on a
cleanup branch (never pushed). Evidence is only a shipped hash (scripts/kit-hashes.json), the
shipped template text (placeholders as wildcards) or an exact marker or fragment; never a name.
A file at a kit path that matches no shipped version is the repo's own edit and stays.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import subprocess
import sys
from functools import cache
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
TPL = SKILL / "templates"
SUBJECT = "chore: remove sdlc 3.x copies (sdlc clean)"

# Every top-level sdlc.json key 3.x adopt or its presets wrote.
KIT_KEYS = {
    "_comment",
    "askGatesMerge",
    "blocked",
    "builderEffort",
    "builderModel",
    "builders",
    "changesDir",
    "checks",
    "ciCommands",
    "ciPaths",
    "claudeAllow",
    "codeowners",
    "db",
    "defaultBranch",
    "delivery",
    "designsDir",
    "docs",
    "goal",
    "heavy",
    "hotfix",
    "keep",
    "kitTemplates",
    "languages",
    "layout",
    "lintOnEdit",
    "linear",
    "milestones",
    "product",
    "projects",
    "responsiveTier",
    "rules",
    "sdlcVersion",
    "showChannel",
    "specsDir",
    "testFile",
    "tests",
    "tiers",
    "toolsCommand",
    "tracker",
    "ux",
    "verify",
    "verifyDirty",
    "verifyStop",
}
LEGACY_HOOKS = {"ruff-on-edit.sh"}
HOOK_CMD = re.compile(r'^"?\$CLAUDE_PROJECT_DIR"?/\.claude/hooks/([\w.-]+)$')
GI_VERIFY_NOTE = "# verify_gate.py output; lock.json is committed"
GI_VERIFY = re.compile(r"/[^\s]+/\*/verify/")
GI_HOOKS_NOTE = "# the SDLC hooks are the repo's, not the laptop's"
GI_HOOKS = {
    "!.claude/",
    "!.claude/settings.json",
    "!.claude/hooks/",
    "!.claude/hooks/*.sh",
    "!.claude/hooks/*.py",
}
TIER_JSON_MARKER = '"_comment": "Ship/Show/Ask by blast radius.'
HEADING_CLAUDE = "## How work moves: the SDLC"
HEADING_AGENTS = "## Decision4: how hard is this change to undo?"
# The Decision4 workflow 3.x wrote before 3.12.0 (owner and sha vary).
DECISION4_WF = re.compile(
    r"name: Decision4\non:\n  pull_request:\n    types: \[opened, edited, synchronize, reopened\]\n"
    r"concurrency:\n  group: decision4-\$\{\{ github\.event\.pull_request\.number \}\}\n"
    r"  cancel-in-progress: true\npermissions:\n  contents: read\n  pull-requests: read\n"
    r"jobs:\n  decision4:\n    uses: [\w.-]+/[\w.-]+/\.github/workflows/decision4-check\.yml"
    r"@[0-9a-f]{7,40} # shared Decision4 v1\n*"
)
LEGACY_UNKNOWN = {
    ".github/workflows/claude-review.yml": "legacy Claude workflow, no shipped hash to compare",
    ".github/workflows/claude.yml": "legacy Claude workflow, no shipped hash to compare",
    ".github/workflows/ci-triage.yml": "legacy Claude workflow, no shipped hash to compare",
    ".decision4.lock": "pinned the removed Decision4 workflow; no content evidence",
    ".claude/hooks/ruff-on-edit.sh": "hook from the earlier repo-local layout; no shipped hash",
}


class CleanError(Exception):
    pass


def _h16(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _git(repo: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if check and r.returncode:
        raise CleanError(f"git {' '.join(args)} failed: {(r.stderr or r.stdout).strip()}")
    return r


def kit_hashes() -> dict[str, set[str]]:
    data = json.loads((SKILL / "scripts" / "kit-hashes.json").read_text(encoding="utf-8"))
    return {rel: set(hs) for rel, hs in data.items()}


# --- template text as evidence ------------------------------------------------------------------


def _blocks(text: str, vals: dict[str, bool]) -> str:
    n = 1
    while n:
        text, n = re.subn(
            r"\{\{#(\w+)\}\}\n?(.*?)\{\{/\1\}\}\n?",
            lambda m: m.group(2) if vals.get(m.group(1)) else "",
            text,
            flags=re.DOTALL,
        )
    return text


@cache
def _patterns(tpl_rel: str) -> tuple[re.Pattern[str], ...]:
    """One regex per way adopt could have rendered the template: `{{BLOCK}}` conditionals both
    ways, `{{VALUE}}` placeholders matching any text on one line."""
    path = TPL / tpl_rel
    if not path.is_file():
        return ()
    text = path.read_text(encoding="utf-8")
    names = sorted(set(re.findall(r"\{\{#(\w+)\}\}", text)))
    out = {}
    for combo in itertools.product((False, True), repeat=len(names)):
        body = _blocks(text, dict(zip(names, combo))).strip("\n")
        out[body] = re.compile(
            "[^\n]*".join(re.escape(p) for p in re.split(r"\{\{[A-Z_]+\}\}", body))
        )
    return tuple(out.values())


def _template_state(text: str, tpl_rel: str) -> str | None:
    """'exact' when the text is a rendering of the template, 'mixed' with other text after it."""
    for pat in _patterns(tpl_rel):
        if m := pat.match(text):
            return "exact" if not text[m.end() :].strip() else "mixed"
    return None


def _config(repo: Path) -> dict:
    try:
        cfg = json.loads(_read(repo / "sdlc.json"))
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def _pr_template_paths(repo: Path) -> list[str]:
    names = ("pull_request_template.md", "pull_request_template.txt")
    found = [
        p
        for d in (repo, repo / ".github", repo / "docs")
        if d.is_dir()
        for p in d.iterdir()
        if p.is_file() and p.name.lower() in names
    ]
    return sorted(p.relative_to(repo).as_posix() for p in found)


# --- files --------------------------------------------------------------------------------------


def _files(repo: Path, cfg: dict) -> tuple[list[dict], list[dict]]:
    exact: list[dict] = []
    edited: list[dict] = []

    def add(
        rel: str, kind: str, state: str | None, h: str, why: str = "matches no shipped version"
    ) -> None:
        if state == "exact":
            exact.append({"path": rel, "kind": kind, "hash": h})
        elif state is not None:
            edited.append({"path": rel, "kind": kind, "reason": why})

    for rel, hashes in sorted(kit_hashes().items()):
        p = repo / rel
        if p.is_file():
            h = _h16(p.read_bytes())
            add(
                rel,
                "hook" if rel.startswith(".claude/") else "script",
                "exact" if h in hashes else "edited",
                h,
            )

    docs = cfg.get("docs") if isinstance(cfg.get("docs"), str) else "docs/sdlc.md"
    tpl_files = [
        (docs, "docs", "docs-sdlc.md"),
        ("REVIEW.md", "review-instructions", "REVIEW.md"),
        ("tests/test_sdlc.py", "guardrail-test", "tests/test_sdlc.py"),
        ("tests/sdlc.test.ts", "guardrail-test", "tests/sdlc.test.ts"),
        (".github/workflows/ship-show-ask.yml", "workflow", "workflows/ship-show-ask.yml"),
        ("boundary-map.yaml", "boundary-map", "decision4/boundary-map.yaml"),
    ]
    tpl_files += [
        (rel, "pr-template", "github/PULL_REQUEST_TEMPLATE.md") for rel in _pr_template_paths(repo)
    ]
    tpl_files += [
        (f".github/ISSUE_TEMPLATE/{t.name}", "issue-template", f"github/ISSUE_TEMPLATE/{t.name}")
        for t in sorted((TPL / "github" / "ISSUE_TEMPLATE").glob("*"))
        if t.is_file()
    ]
    for rel, kind, tpl in tpl_files:
        p = repo / rel
        if not p.is_file():
            continue
        state = _template_state(_read(p), tpl)
        if state is None and kind == "pr-template":
            continue  # a native PR template may still hold an exact fragment (handled below)
        add(
            rel,
            kind,
            "exact" if state == "exact" else "edited",
            _h16(p.read_bytes()),
            "kit text plus the repo's own text"
            if state == "mixed"
            else "matches no shipped version",
        )

    d4 = repo / ".github" / "workflows" / "decision4.yml"
    if d4.is_file():
        add(
            ".github/workflows/decision4.yml",
            "workflow",
            "exact" if DECISION4_WF.fullmatch(_read(d4)) else "edited",
            _h16(d4.read_bytes()),
        )
    tiers = repo / ".github" / "tiers.json"
    if tiers.is_file() and TIER_JSON_MARKER in _read(tiers)[:600]:
        edited.append(
            {
                "path": ".github/tiers.json",
                "kind": "tiers",
                "reason": "generated but repo-tunable: only a marker, no hash",
            }
        )
    return exact, edited


# --- fragments of shared files ------------------------------------------------------------------


def _cut(text: str, start: int, end: int) -> str | None:
    """text without [start:end); None when only whitespace is left."""
    parts = [p for p in (text[:start].rstrip(), text[end:].lstrip()) if p]
    return "\n\n".join(parts) + "\n" if parts else None


def _frag(path: str, kind: str, lines: list[str], new: str | None) -> dict:
    return {
        "path": path,
        "kind": kind,
        "lines": lines,
        "action": "rewrite" if new is not None else "delete",
        "new": new,
    }


def _settings(repo: Path, hook_names: set[str], keep: set[str]) -> tuple[list[dict], list[dict]]:
    p = repo / ".claude" / "settings.json"
    if not p.is_file():
        return [], []
    try:
        data = json.loads(_read(p))
        hooks = data.get("hooks") if isinstance(data, dict) else None
    except ValueError:
        return [], [{"path": ".claude/settings.json", "reason": "not valid JSON, left as is"}]
    if not isinstance(hooks, dict):
        return [], []
    removed: list[str] = []

    def is_kit(h: object) -> bool:
        m = HOOK_CMD.match(str(h.get("command", "")).strip()) if isinstance(h, dict) else None
        return bool(m and m.group(1) in hook_names and m.group(1) not in keep)

    for event in list(hooks):
        groups = hooks[event] if isinstance(hooks[event], list) else []
        for g in groups:
            hs = g.get("hooks") if isinstance(g, dict) else None
            if isinstance(hs, list) and any(is_kit(h) for h in hs):
                removed += [f"{event}: {h['command']}" for h in hs if is_kit(h)]
                g["hooks"] = [h for h in hs if not is_kit(h)]
        if groups:
            hooks[event] = [g for g in groups if not (isinstance(g, dict) and g.get("hooks") == [])]
            if not hooks[event]:
                del hooks[event]
    if not removed:
        return [], []
    if not hooks:
        del data["hooks"]
    new = json.dumps(data, indent=2) + "\n" if data else None
    return [_frag(".claude/settings.json", "settings-hooks", removed, new)], []


def _block(repo: Path, rel: str, kind: str, heading: str, find) -> tuple[list[dict], list[dict]]:
    p = repo / rel
    if not p.is_file():
        return [], []
    text = _read(p)
    span = find(text)
    if span:
        return [_frag(rel, kind, text[span[0] : span[1]].splitlines(), _cut(text, *span))], []
    if heading in text:
        return [], [
            {
                "path": rel,
                "reason": f"has `{heading}` but its text differs from the shipped one, left as is",
            }
        ]
    return [], []


def _claude_md(repo: Path) -> tuple[list[dict], list[dict]]:
    def find(text: str) -> tuple[int, int] | None:
        for pat in _patterns("CLAUDE-section.md"):
            if m := pat.search(text):
                return m.span()
        return None

    return _block(repo, "CLAUDE.md", "claude-md-section", HEADING_CLAUDE, find)


def _agents_md(repo: Path) -> tuple[list[dict], list[dict]]:
    sec = TPL / "decision4" / "AGENTS-section.md"
    body = sec.read_text(encoding="utf-8").strip() if sec.is_file() else None

    def find(text: str) -> tuple[int, int] | None:
        i = text.find(body) if body else -1
        return (i, i + len(body)) if i >= 0 else None

    return _block(repo, "AGENTS.md", "agents-md-section", HEADING_AGENTS, find)


def _pr_sections(repo: Path) -> list[dict]:
    src = TPL / "github" / "PULL_REQUEST_TEMPLATE.md"
    if not src.is_file() or "<!-- Decision4 is advisory" not in (
        full := src.read_text(encoding="utf-8")
    ):
        return []
    sec = full[full.index("<!-- Decision4 is advisory") :].strip()
    out = []
    for rel in _pr_template_paths(repo):
        text = _read(repo / rel)
        i = text.find(sec)
        if i >= 0 and _template_state(text, "github/PULL_REQUEST_TEMPLATE.md") is None:
            out.append(
                _frag(rel, "pr-template-section", sec.splitlines(), _cut(text, i, i + len(sec)))
            )
    return out


def _gitignore(repo: Path) -> list[dict]:
    p = repo / ".gitignore"
    if not p.is_file():
        return []
    lines = _read(p).splitlines()
    out: list[str] = []
    removed: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i] == GI_VERIFY_NOTE and i + 1 < len(lines) and GI_VERIFY.fullmatch(lines[i + 1]):
            removed += lines[i : i + 2]
            i += 2
        elif lines[i] == GI_HOOKS_NOTE:
            j = i + 1
            while j < len(lines) and lines[j] in GI_HOOKS:
                j += 1
            removed += lines[i:j]
            if out and not out[-1].strip():
                out.pop()
            i = j
        else:
            out.append(lines[i])
            i += 1
    if not removed:
        return []
    return [
        _frag(
            ".gitignore",
            "gitignore-lines",
            removed,
            "\n".join(out) + "\n" if any(x.strip() for x in out) else None,
        )
    ]


def _sdlc_json(repo: Path) -> tuple[list[dict], list[dict]]:
    p = repo / "sdlc.json"
    if not p.is_file():
        return [], []
    try:
        data = json.loads(_read(p))
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return [], [{"path": "sdlc.json", "reason": "not a JSON object, left as is"}]
    extra = sorted(set(data) - KIT_KEYS)
    if extra:
        return [], [
            {
                "path": "sdlc.json",
                "reason": f"also holds keys the kit does not own ({', '.join(extra)}); left as is",
            }
        ]
    return [_frag("sdlc.json", "sdlc-json-keys", sorted(data), None)], []


def _fragments(
    repo: Path, hook_names: set[str], keep_hooks: set[str]
) -> tuple[list[dict], list[dict]]:
    frags: list[dict] = []
    unknown: list[dict] = []
    for f, u in (
        _settings(repo, hook_names, keep_hooks),
        _claude_md(repo),
        _agents_md(repo),
        _sdlc_json(repo),
    ):
        frags += f
        unknown += u
    return frags + _pr_sections(repo) + _gitignore(repo), unknown


# --- inventory, plan, apply ---------------------------------------------------------------------


def inventory(repo_path: str | Path) -> dict:
    repo = Path(repo_path)
    cfg = _config(repo)
    exact, edited = _files(repo, cfg)
    hooks = {
        rel.rsplit("/", 1)[1] for rel in kit_hashes() if rel.startswith(".claude/hooks/")
    } | LEGACY_HOOKS
    keep = {e["path"].rsplit("/", 1)[1] for e in edited if e["path"].startswith(".claude/hooks/")}
    frags, unknown = _fragments(repo, hooks, keep)
    unknown += [
        {"path": rel, "reason": why}
        for rel, why in LEGACY_UNKNOWN.items()
        if (repo / rel).is_file()
    ]
    if (repo / ".github" / "tiers.json").is_file() and not any(
        e["path"] == ".github/tiers.json" for e in edited
    ):
        unknown.append({"path": ".github/tiers.json", "reason": "no generated-by-adopt marker"})
    if (
        any(f["path"] == "AGENTS.md" for f in frags)
        and (repo / "CLAUDE.md").is_file()
        and "@AGENTS.md" in _read(repo / "CLAUDE.md")
    ):
        unknown.append(
            {"path": "CLAUDE.md", "reason": "`@AGENTS.md` line kept: it may be the repo's own"}
        )
    gone = {e["path"] for e in exact}
    preserved = []
    for d, why in (
        (cfg.get("changesDir") or "changes", "change folders"),
        (".changes", "change folders"),
        ("specs", "living specs"),
        (cfg.get("specsDir") or "docs/specs", "living specs"),
        (cfg.get("designsDir") or "docs/designs", "design records"),
    ):
        if (
            isinstance(d, str)
            and (repo / d).is_dir()
            and not any(x["path"] == d + "/" for x in preserved)
        ):
            preserved.append({"path": d + "/", "why": why})
    wf = repo / ".github" / "workflows"
    for f in sorted(wf.glob("*.y*ml")) if wf.is_dir() else []:
        rel = f.relative_to(repo).as_posix()
        if (
            rel not in gone
            and rel not in LEGACY_UNKNOWN
            and rel != ".github/workflows/decision4.yml"
        ):
            preserved.append({"path": rel, "why": "native or non-kit workflow"})
    for f in frags:
        f.pop("new")
    return {
        "repo": str(repo),
        "exact": exact,
        "edited": edited,
        "fragments": frags,
        "unknown": sorted(unknown, key=lambda u: u["path"]),
        "preserved": preserved,
    }


def plan_removals(inv: dict) -> dict:
    """What a clean would do: files to delete, shared files to rewrite, what stays."""
    delete = [e["path"] for e in inv["exact"]] + [
        f["path"] for f in inv["fragments"] if f["action"] == "delete"
    ]
    rewrite = [f["path"] for f in inv["fragments"] if f["action"] == "rewrite"]
    kept = [e["path"] for e in inv["edited"]] + [u["path"] for u in inv["unknown"]]
    return {
        "delete": sorted(delete),
        "rewrite": sorted(rewrite),
        "kept": sorted(set(kept)),
        "nothing": not (delete or rewrite),
    }


def _default_branch(repo: Path) -> tuple[str, str]:
    """(name, start point): origin/HEAD, else main, else master."""
    ref = _git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    names = (
        [ref.stdout.strip().removeprefix("origin/")]
        if ref.returncode == 0 and ref.stdout.strip()
        else []
    )
    for name in names + ["main", "master"]:
        for start in (name, f"origin/{name}"):
            if _git(repo, "rev-parse", "--verify", "-q", f"{start}^{{commit}}").returncode == 0:
                return name, start
    raise CleanError("no default branch found (origin/HEAD, main or master)")


def _message(inv: dict) -> str:
    lines = [SUBJECT, "", "Removed:"]
    lines += [f"- {e['path']} ({e['kind']}, hash {e['hash']})" for e in inv["exact"]]
    lines += [
        f"- {f['path']}: {f['kind']}"
        + (" (file now empty, deleted)" if f["action"] == "delete" else "")
        for f in inv["fragments"]
    ]
    lines += ["", "Kept:"]
    lines += [f"- {e['path']}: {e['reason']}" for e in inv["edited"]]
    lines += [f"- {u['path']}: {u['reason']}" for u in inv["unknown"]]
    lines += [f"- {p['path']}: {p['why']}, untouched" for p in inv["preserved"]]
    return "\n".join(lines) + "\n"


def _write_removals(repo: Path, inv: dict) -> list[str]:
    hooks = {
        rel.rsplit("/", 1)[1] for rel in kit_hashes() if rel.startswith(".claude/hooks/")
    } | LEGACY_HOOKS
    keep = {
        e["path"].rsplit("/", 1)[1] for e in inv["edited"] if e["path"].startswith(".claude/hooks/")
    }
    frags, _ = _fragments(repo, hooks, keep)
    touched = [e["path"] for e in inv["exact"]]
    for f in frags:
        if f["new"] is None:
            touched.append(f["path"])
        else:
            (repo / f["path"]).write_text(f["new"], encoding="utf-8")
            touched.append(f["path"])
    for rel in [e["path"] for e in inv["exact"]] + [f["path"] for f in frags if f["new"] is None]:
        (repo / rel).unlink(missing_ok=True)
        parent = (repo / rel).parent
        while parent != repo and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    return touched


def apply(repo_path: str | Path, branch: str = "sdlc-clean") -> dict:
    repo = Path(repo_path)
    if _git(repo, "status", "--porcelain").stdout.strip():
        raise CleanError("working tree is not clean: commit or stash first")
    if plan_removals(inventory(repo))["nothing"]:
        return {"changed": False, "message": "nothing to do"}
    current = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if current != branch:
        _, start = _default_branch(repo)
        if _git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{branch}").returncode == 0:
            raise CleanError(f"branch {branch} already exists: review or delete it first")
        _git(repo, "switch", "-q", "-c", branch, start, check=True)
    inv = inventory(repo)
    if plan_removals(inv)["nothing"]:  # the copies lived only on the branch we left
        if current != branch:
            _git(repo, "switch", "-q", current, check=True)
            _git(repo, "branch", "-q", "-D", branch, check=True)
        return {"changed": False, "message": "nothing to do on the default branch"}
    touched = _write_removals(repo, inv)
    for rel in touched:
        _git(repo, "add", "-A", "--", rel)
    ident = (
        []
        if _git(repo, "config", "user.email").stdout.strip()
        else ["-c", "user.name=sdlc", "-c", "user.email=sdlc@localhost"]
    )
    _git(repo, *ident, "commit", "-q", "-m", _message(inv), check=True)
    return {
        "changed": True,
        "branch": branch,
        "plan": plan_removals(inv),
        "message": f"committed on {branch}",
    }


# --- CLI ----------------------------------------------------------------------------------------


def _render(inv: dict) -> str:
    out = [f"sdlc clean: {inv['repo']}"]

    def section(title: str, rows: list[str]) -> None:
        out.append(f"\n{title} ({len(rows)})")
        out.extend(rows or ["  none"])

    rows = []
    for e in inv["exact"]:
        n = len(_read(Path(inv["repo"]) / e["path"]).splitlines())
        rows.append(
            f"  {e['path']}  [{e['kind']}, hash {e['hash']}]  would remove the file ({n} lines)"
        )
    section("EXACT: shipped copies, removed", rows)
    section(
        "EDITED: at a kit path, matches no shipped version, kept",
        [f"  {e['path']}  [{e['kind']}] {e['reason']}" for e in inv["edited"]],
    )
    rows = []
    for f in inv["fragments"]:
        rows.append(
            f"  {f['path']}  [{f['kind']}]"
            + ("  (file would be deleted)" if f["action"] == "delete" else "")
        )
        rows += [f"    - {ln}" for ln in f["lines"]]
    section("FRAGMENTS: exact owned text in shared files, removed", rows)
    section(
        "UNKNOWN: kit-looking, no evidence, kept",
        [f"  {u['path']}  {u['reason']}" for u in inv["unknown"]],
    )
    section("PRESERVED: untouched", [f"  {p['path']}  {p['why']}" for p in inv["preserved"]])
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="sdlc clean", description="Remove sdlc 3.x copies from a product repo."
    )
    ap.add_argument("repo")
    ap.add_argument("--apply", action="store_true", help="commit the removals on a cleanup branch")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    if not (repo / ".git").exists():
        ap.error(f"{repo} is not a git repository")
    inv = inventory(repo)
    plan = plan_removals(inv)
    result: dict = {}
    if args.apply:
        try:
            result = apply(repo)
        except CleanError as e:
            result = {"changed": False, "refused": str(e)}
    if args.json:
        print(json.dumps({"inventory": inv, "plan": plan, "result": result}, indent=2))
        return 0
    print(_render(inv))
    if not args.apply:
        print("\nDRY RUN: nothing changed (use --apply)")
    elif "refused" in result:
        print(f"\nREFUSED: {result['refused']}", file=sys.stderr)
    else:
        print(f"\n{result['message']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
