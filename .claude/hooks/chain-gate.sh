#!/usr/bin/env bash
# PreToolUse hook on Edit|Write: the chain's gates, enforced where they can still change
# the outcome -- before the write, never as a test after the work is done.
#
# Until 2026-09-20 exactly one gate was wired to something the harness fires (plan-gate on
# ExitPlanMode); the ticket, intent, facts and /goal steps were sentences, and a skipped one
# left no trace. Refusals, in the order a change meets them:
#
#   1. anything under <changesDir>/<id>/  -- needs decisions.json (the Stage 1.1 dialog)
#   2. spec/** (v3)                      -- needs intent.md with a non-empty ## Asks
#   3. facts.md                          -- needs the interview or a recorded skip; v3 also needs
#                                           brief..conformance done or skipped
#   4. plan.md                           -- needs facts.md approved; v3 also an approved, ready
#                                           validation (or its skip)
#   5. source outside changes/ + docs/   -- needs an approved plan with a filled handover;
#                                           v3 prototypeDirs are open during Design
#   6. tests while testLocked (v3 bug)   -- refused unless testEdit records the user's OK
#
# The milestone process (approved 2026-10-09; decisions.json has `milestone`) replaces 2-5:
#   2. spec/** and facts.md              -- need intent.md `status: approved` (touchpoint one);
#                                           facts also need the UX plan done or skipped
#   4. plan.md                           -- needs facts.md (one gate approves all three)
#   5. source                            -- needs an approved plan, lock.json, a filled ## Goal,
#                                           and an active /goal in the transcript
#   7. protected paths after approval    -- facts.md, done.json, lock.json, sdlc.json and the
#                                           `protected` globs, unless protectedEdit quotes the engineer
#
# Layout 4 (spec.py `applies`) has no rules 2-4: its plan gate is `status: approved` on spec.md,
# design.md and tasks.md plus lock.json; after the lock spec.md, design.md, specs/*/rules/R*.md and
# .sdlc/last-rule-id need `protectedEdit` (a rule's `status:` line and task ticks stay open).
#
# v3 = decisions.json has `size`; v2 folders keep the v2 rules, v3 folders without `milestone`
# keep the v3 rules, so in-flight changes finish on the process they started. Rules 5-7 fire
# only when the checked-out branch has a change folder: no folder, no opinion. Bash wrapper,
# Python engine.
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1 # a hook must not leave __pycache__ in a clean checkout
. "$(dirname "$0")/sdlc-config.sh"
: "${SDLC_PY:=python3}" # an older sdlc-config.sh (one-file upgrade) does not set it

payload=$(cat)

# The session transcripts are the evidence for an owner quote (verify_gate.py reads them): no
# Write or Edit may touch ~/.claude/projects, in any repo, with or without sdlc.json or a goal.
if ! printf '%s' "$payload" | "$SDLC_PY" -c '
import json, os, sys
try:
    f = json.load(sys.stdin)["tool_input"]["file_path"]
except (ValueError, KeyError, TypeError):
    sys.exit(0)
if not f:
    sys.exit(0)
t = os.path.realpath(os.path.expanduser(os.path.expandvars(f)))
e = os.path.realpath(os.path.expanduser("~/.claude/projects"))
sys.exit(1 if t == e or t.startswith(e + os.sep) else 0)
'; then
  echo 'BLOCKED: ~/.claude/projects holds the session transcripts, the evidence of what the engineer said. They are never written or edited; ask the engineer to say it in the session.' >&2
  exit 2
fi
[ -f "$SDLC_JSON" ] || exit 0

# One interpreter start per call: the payload (fd 3) and sdlc.json are read in the same process.
SDLC_HOOK_DIR="$(cd "$(dirname "$0")" && pwd)" "$SDLC_PY" - "$SDLC_ROOT" "$SDLC_JSON" 3<<<"$payload" <<'PY'
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
cfg_path = Path(sys.argv[2])
try:
    payload = json.load(os.fdopen(3, encoding="utf-8"))
    file_arg = payload["tool_input"]["file_path"]
except (OSError, ValueError, KeyError, TypeError):
    sys.exit(0)
if not file_arg:
    sys.exit(0)
transcript = payload.get("transcript_path") or ""
# the two fields block_state.py keys on
block_ctx = {k: payload.get(k) for k in ("session_id", "cwd")}
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
changes = cfg.get("changesDir", "changes")
designs = cfg.get("designsDir", "docs/designs")
docs = cfg.get("docs", "docs/sdlc.md")

path = Path(file_arg)
try:
    rel = str(path.resolve().relative_to(root)) if path.is_absolute() else file_arg
except ValueError:
    sys.exit(0)
while rel.startswith("./"):
    rel = rel[2:]
if rel.startswith("../") or rel.startswith("/"):
    sys.exit(0)


def helper(name: str):
    """A sibling helper by its exact path: never found on sys.path, where the working directory
    could shadow it. Raises when it is missing or broken."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, os.path.join(os.environ["SDLC_HOOK_DIR"], f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def deny(message: str, source: str = "", action: str = "") -> None:
    """Block. `source` is what the check read, `action` what the owner does; a repeat of the
    same block says both (block_state.py). Without block_state.py it is the plain message."""
    text = f"BLOCKED: {message}\n({docs})"
    try:
        text = helper("block_state").rewrite(
            "chain-gate.sh", text, source or "its change files",
            action or "follow the route in the message below", block_ctx,
        )
    except Exception:  # block state never changes the verdict
        pass
    print(text, file=sys.stderr)
    sys.exit(2)


def fm(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return ""


def section(path: Path, heading: str) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    inside = False
    body: list[str] = []
    for line in lines:
        if line == f"## {heading}":
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside:
            body.append(line)
    return "\n".join(line for line in body if line.strip())


def state_file(change_dir: Path, name: str) -> Path:
    """A machine file of a change: <change>/state/ first (decisions.json is intake.json there), then
    the old place. The same reader as spec.py `state_path`, which a hook cannot import."""
    new = change_dir / "state" / {"decisions.json": "intake.json"}.get(name, name)
    return new if new.exists() else change_dir / name


def load_decisions(change_dir: Path) -> dict:
    path = state_file(change_dir, "decisions.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def is_v3(decisions: dict) -> bool:
    return "size" in decisions


def is_milestone(decisions: dict) -> bool:
    return "milestone" in decisions


def lock_layout(change_dir: Path) -> int | None:
    """The layout `approve` recorded in lock.json: None for a lock without one (an older lock) or
    an unreadable one. Once a lock exists it, not an editable file, says which layout applies."""
    try:
        value = json.loads((state_file(change_dir, "lock.json")).read_text(encoding="utf-8")).get("layout")
    except (OSError, ValueError, AttributeError):
        return None
    return value if isinstance(value, int) else None


def is_v4(change_dir: Path, decisions: dict) -> bool:
    """Layout 4 (spec.py `applies`, which a hook cannot import): pinned in decisions.json, or a
    spec.md with no facts.md. It has three documents and a living spec, not intent/facts/plan.
    After approval the lock decides, and a lock with no layout is an older, three-file one."""
    if (state_file(change_dir, "lock.json")).exists():
        return lock_layout(change_dir) == 4
    return decisions.get("layout") == 4 or (
        (change_dir / "spec.md").exists() and not (change_dir / "facts.md").exists()
    )


def protected_files(change_dir: Path, decisions: dict) -> tuple[str, ...]:
    """What a locked change protects: its layout's files, or both layouts' when the lock names none."""
    if lock_layout(change_dir) is None and (state_file(change_dir, "lock.json")).exists():
        return tuple(dict.fromkeys(PROTECTED_FILES + V4_PROTECTED_FILES))
    return V4_PROTECTED_FILES if is_v4(change_dir, decisions) else PROTECTED_FILES


PROTECTED_FILES = ("facts.md", "done.json", "lock.json")
V4_PROTECTED_FILES = ("spec.md", "design.md", "done.json", "lock.json")  # tasks.md takes ticks
PROTECTED_GLOBS = ["sdlc.json", "**/*-snapshots/**", "**/__screenshots__/**", "**/*allowlist*"]


def goal_active(path: str) -> bool | None:
    """goal_active.py's reading (None = unreadable, which fails open with a warning)."""
    try:
        read = helper("goal_active").goal_active
    except Exception:  # missing, or any error while importing it: a gate that cannot read the goal blocks
        deny(
            "goal_active.py is missing or broken beside chain-gate.sh; run `sdlc-run adopt` to restore it.",
            source="goal_active.py beside chain-gate.sh", action="run `sdlc-run adopt`",
        )
    return read(path)


def skipped(decisions: dict, activity: str) -> bool:
    value = decisions.get("skips", {}).get(activity, "")
    return isinstance(value, str) and value.startswith("skip")


def verdict_file(change_dir: Path) -> Path:
    """spec/readiness.md; spec/validation.md only for a folder written before the rename."""
    spec = change_dir / "spec"
    old = spec / "validation.md"
    return old if old.exists() and not (spec / "readiness.md").exists() else spec / "readiness.md"


def activity_done(change_dir: Path, decisions: dict, activity: str) -> bool:
    files = {
        "brief": change_dir / "spec" / "brief.md",
        "ia": change_dir / "spec" / "ia.md",
        "interaction": change_dir / "spec" / "interaction.md",
        "screens": change_dir / "spec" / "screens.md",
        "prototype": change_dir / "spec" / "prototype" / "index.md",
        "conformance": change_dir / "spec" / "conformance.md",
        "validation": verdict_file(change_dir),
    }
    return skipped(decisions, activity) or files[activity].exists()


def validation_ready(change_dir: Path, decisions: dict) -> bool:
    if skipped(decisions, "validation"):
        return True
    validation = verdict_file(change_dir)
    return fm(validation, "verdict") == "ready" and fm(validation, "status") == "approved"


def has_asks(change_dir: Path) -> bool:
    body = section(change_dir / "intent.md", "Asks")
    return bool(re.search(r"\|\s*A\d+\s*\|", body))


def branch_name() -> str:
    for cmd in (
        ["git", "-C", str(root), "symbolic-ref", "--short", "-q", "HEAD"],
        ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
    ):
        out = subprocess.run(cmd, capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    return ""


def git_dir() -> Path | None:
    out = subprocess.run(["git", "-C", str(root), "rev-parse", "--absolute-git-dir"], capture_output=True, text=True)
    return Path(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else None


def dispatched_change() -> tuple[str, Path, dict] | None:
    """The change a dispatch named: `<git dir>/sdlc-change` (the supervisor writes it into the
    builder's worktree) or SDLC_CHANGE. Never guessed from a branch name; an id with no folder is ignored."""
    ids = []
    gd = git_dir()
    if gd and (gd / "sdlc-change").is_file():
        ids.append((gd / "sdlc-change").read_text(encoding="utf-8").strip())
    ids.append(os.environ.get("SDLC_CHANGE", "").strip())
    for change_id in ids:
        if re.fullmatch(r"[\w.-]+", change_id) and (root / changes / change_id).is_dir():
            return change_id, root / changes / change_id, load_decisions(root / changes / change_id)
    return None


def authorized(target: str, change_id: str, change_dir: Path, decisions: dict) -> bool:
    """Does `protectedEdit` allow this edit of `target`? An entry is a quote (a string) or
    `{"path", "words", "sha"}`: `path` limits it to one file, `sha` to the lock it was given for. It
    is spent by the edit it allows (the key is kept in the git dir), so each edit needs its own
    quote. A quote with no words authorizes nothing."""
    import hashlib

    raw = decisions.get("protectedEdit")
    entries = raw if isinstance(raw, list) else [raw] if raw else []
    try:
        lock_sha = str(json.loads(state_file(change_dir, "lock.json").read_text(encoding="utf-8")).get("sha", ""))
    except (OSError, ValueError, AttributeError):
        lock_sha = ""
    gd = git_dir()
    used_path = gd / "sdlc-protected-used.json" if gd else None
    spent = False
    for entry in entries:
        path, words, sha = (entry.get("path"), str(entry.get("words", "")), entry.get("sha")) if isinstance(entry, dict) else (None, str(entry), None)
        if not words.strip() or (path and path.lstrip("./") != target) or (sha and sha != lock_sha):
            continue
        # a matching quote needs the ledger: one that cannot be found, read or written denies (fails closed)
        try:
            if used_path is None:
                raise OSError("no git dir")
            used = json.loads(used_path.read_text(encoding="utf-8")) if used_path.exists() else []
            if not isinstance(used, list):
                raise ValueError("not a list")
        except (OSError, ValueError):
            print(f"chain-gate: the protectedEdit ledger ({used_path or 'no git dir'}) is missing, unreadable or not a list; refusing the edit.", file=sys.stderr)
            return False
        key = hashlib.sha256(f"{change_id}\0{path or '*'}\0{words}\0{lock_sha}".encode()).hexdigest()
        if key in used:
            spent = True
            continue
        try:
            used_path.write_text(json.dumps([*used, key]), encoding="utf-8")
        except OSError:
            print(f"chain-gate: the protectedEdit ledger ({used_path}) is not writable; refusing the edit.", file=sys.stderr)
            return False
        return True
    if spent:
        print(f"chain-gate: the protectedEdit quote for {target} is already used; ask the engineer again and record new words.", file=sys.stderr)
    return False


def branch_change() -> tuple[str, Path, dict] | None:
    """The change of the checked-out branch; the dispatch pointer only fills in when the branch names
    none. When both name a change and they differ, the edit is refused: a pointer never overrides."""
    named, pointed = change_of_branch(), dispatched_change()
    if named and pointed and named[0] != pointed[0]:
        deny(
            f"the branch names change {named[0]} but the dispatch pointer (<git dir>/sdlc-change or SDLC_CHANGE) "
            f"names {pointed[0]}: they disagree. Fix the pointer or the branch; a pointer never overrides the branch.",
            source="the branch name and the dispatch pointer",
            action="remove the wrong pointer, or work on the branch of the change",
        )
    return named or pointed


def change_of_branch() -> tuple[str, Path, dict] | None:
    branch = branch_name()
    if not branch:
        return None
    base = root / changes
    if not base.is_dir():
        return None
    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name == "archive":
            continue
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", d.name)
        slug = re.sub(r"^[A-Z][A-Z0-9]+-\d+-", "", slug)
        if slug and slug in branch:
            return d.name, d, load_decisions(d)
    return None


def match_any(path: str, patterns: list[str]) -> bool:
    return any(
        fnmatch.fnmatchcase(path, pat) or fnmatch.fnmatchcase(path, (pat[3:] if pat.startswith("**/") else pat))
        for pat in patterns
    )


parts = rel.split("/")
if len(parts) >= 3 and parts[0] == changes:
    if len(parts) >= 2 and parts[1] == "archive":
        sys.exit(0)
    change_id = parts[1]
    change_dir = root / changes / change_id
    base = parts[-1]
    inside = "/".join(parts[2:])
    if inside.startswith("state/"):  # state/lock.json is lock.json, state/intake.json is decisions.json
        inside = {"intake.json": "decisions.json"}.get(inside[6:], inside[6:])
        base = inside.rsplit("/", 1)[-1]

    if base == "decisions.json":
        lock = state_file(change_dir, "lock.json")
        if lock.exists() and (state_file(change_dir, "decisions.json")).exists():
            # `layout` decides which files the lock protects: changing it after approval is a protected edit
            tool = payload.get("tool_input") or {}
            now = (state_file(change_dir, "decisions.json")).read_text(encoding="utf-8")
            new = tool["content"] if "content" in tool else now.replace(
                str(tool.get("old_string", "")), str(tool.get("new_string", "")), 1 if tool.get("old_string") else 0
            )
            def layout_of(text: str) -> object:
                try:
                    return json.loads(text).get("layout", "none")
                except (ValueError, AttributeError):
                    return "unreadable"
            if layout_of(new) != layout_of(now) and not authorized(rel, change_id, change_dir, load_decisions(change_dir)):
                deny(
                    f"{changes}/{change_id}/decisions.json `layout` is locked since the engineer approved the "
                    "change. Stop and ask; record their words as `protectedEdit` first.",
                    source=f"{changes}/{change_id}/lock.json and decisions.json",
                    action="stop and ask the engineer; their words go in decisions.json as protectedEdit",
                )
        sys.exit(0)
    if not (state_file(change_dir, "decisions.json")).exists():
        deny(
            f"the Stage 1.1 dialog has not run for {change_id}. AskUserQuestion must ask ticket "
            f"(search Linear first), intent, design file, size and kind; then write "
            f"{changes}/{change_id}/decisions.json.",
            source=f"{changes}/{change_id}/decisions.json"
        )

    decisions = load_decisions(change_dir)
    v3 = is_v3(decisions)
    v4 = is_v4(change_dir, decisions)

    if is_milestone(decisions) or v4:
        if inside in protected_files(change_dir, decisions) and (state_file(change_dir, "lock.json")).exists():
            if authorized(rel, change_id, change_dir, decisions):
                sys.exit(0)
            deny(
                f"{changes}/{change_id}/{inside} is locked since the engineer approved the plan. "
                "Stop and ask; record their words as `protectedEdit` in decisions.json first.",
                source=f"{changes}/{change_id}/lock.json and decisions.json", action="stop and ask the engineer; their words go in decisions.json as protectedEdit"
            )
        if v4:  # no intent/facts/plan ordering: the three documents have one gate, at the lock
            sys.exit(0)
        if (inside.startswith("spec/") or base == "facts.md") and fm(
            change_dir / "intent.md", "status"
        ) != "approved":
            deny(
                f"{changes}/{change_id}/intent.md is not approved. Draft it (asks, job stories, "
                "success measure) and have the engineer confirm it first.",
                source=f"{changes}/{change_id}/intent.md"
            )
        if base == "facts.md" and decisions.get("size") != "none" and cfg.get("ux", "on") != "off":
            needed = ["conformance"] + (["validation"] if decisions.get("size") in ("M", "L") else [])
            missing = [a for a in needed if not activity_done(change_dir, decisions, a)]
            if missing:
                deny(
                    f"{changes}/{change_id}/facts.md comes after the UX plan: {', '.join(missing)} "
                    f"missing. Run cct:ux-rules-validate spec {change_id}"
                    + (f" and one pass of cct:ux-spec-validate spec {change_id}." if "validation" in missing else "."),
                    source=f"{changes}/{change_id}/decisions.json and spec/"
                )
        if base == "plan.md" and not (change_dir / "facts.md").exists():
            deny(f"{changes}/{change_id}/facts.md does not exist yet. Facts come before a plan.", source=f"{changes}/{change_id}/facts.md")
        sys.exit(0)

    if v3 and inside.startswith("spec/") and not has_asks(change_dir):
        deny(
            f"{changes}/{change_id}/intent.md needs a non-empty ## Asks table before spec files. "
            f"Run Stage 1.3 and write the A<n> table, then continue with cct:ux-design-run {change_id}.",
            source=f"{changes}/{change_id}/intent.md"
        )

    if base == "facts.md":
        # The intent decision comes first, v2 and v3 alike: a skip with its reason, or the interview.
        intent = str(decisions.get("intent", ""))
        if not intent:
            deny(
                f"decisions.json for {change_id} records no intent decision. Record a skip with "
                "its reason, or run the interview.",
                source=f"{changes}/{change_id}/decisions.json"
            )
        if not intent.startswith("skip") and not (change_dir / "interview-result.json").exists():
            deny(
                f"the intent interview has not run for {change_id}. Run: plannotator "
                f"setup-goal interview {changes}/{change_id}/interview.json --json | "
                f"tee {changes}/{change_id}/interview-result.json",
                source=f"{changes}/{change_id}/interview-result.json"
            )
        if v3:
            missing = [
                a
                for a in ("brief", "ia", "interaction", "screens", "prototype", "conformance")
                if not activity_done(change_dir, decisions, a)
            ]
            if missing:
                commands = []
                if any(a != "conformance" for a in missing):
                    commands.append(f"cct:ux-design-run {change_id}")
                if "conformance" in missing:
                    commands.append(f"cct:ux-rules-validate spec {change_id}")
                deny(
                    f"{changes}/{change_id}/facts.md needs design activities done or skipped first: "
                    f"{', '.join(missing)}. Run {'; '.join(commands)}.",
                    source=f"{changes}/{change_id}/decisions.json and spec/"
                )

    if base == "plan.md":
        if not (change_dir / "facts.md").exists():
            deny(f"{changes}/{change_id}/facts.md does not exist yet. Facts come before a plan.", source=f"{changes}/{change_id}/facts.md")
        if fm(change_dir / "facts.md", "status") != "approved":
            deny(
                f"{changes}/{change_id}/facts.md is not approved. Run the facts/spec gate before "
                "writing the plan.",
                source=f"{changes}/{change_id}/facts.md"
            )
        if v3 and not validation_ready(change_dir, decisions):
            deny(
                f"{changes}/{change_id}/spec/readiness.md must have verdict: ready and "
                f"status: approved, or validation must be skipped. Run cct:ux-spec-validate spec "
                f"{change_id}, then get the owner gate.",
                source=f"{changes}/{change_id}/spec/readiness.md"
            )
    sys.exit(0)

if re.fullmatch(rf"{re.escape(str(cfg.get('livingSpecs') or 'specs'))}/[^/]+/rules/R\d+\.md", rel) or rel == ".sdlc/last-rule-id":
    # the living spec: rule files and the id floor change by script or git, not by a direct edit,
    # once a layout-4 change is approved. Flipping a rule's `status:` line is the one open edit.
    found = branch_change()
    if found and is_v4(found[1], found[2]) and (state_file(found[1], "lock.json")).exists():
        tool = payload.get("tool_input") or {}
        flip = all(re.fullmatch(r"\s*status:\s*\w+\s*", str(tool.get(k, "\n"))) for k in ("old_string", "new_string"))
        if not flip and not authorized(rel, found[0], found[1], found[2]):
            deny(
                f"{rel} is protected since the engineer approved the change. Rule files and the id floor "
                "change by script (`spec.py new`, `spec.py last-id --write`) or by git; to edit one "
                f"directly stop and ask, then record the words as `protectedEdit` in {changes}/{found[0]}/decisions.json.",
                source=f"{changes}/{found[0]}/lock.json and decisions.json",
                action="stop and ask the engineer; their words go in decisions.json as protectedEdit",
            )
    sys.exit(0)

if rel.startswith("docs/") or rel.startswith(f"{designs}/") or rel.startswith(".claude/") or rel.endswith(".md"):
    sys.exit(0)

current = branch_change()
if not current:
    sys.exit(0)
change_id, change_dir, decisions = current
v3 = is_v3(decisions)

if v3 and decisions.get("kind") == "bug" and decisions.get("testLocked") is True and not decisions.get("testEdit"):
    test_globs = cfg.get(
        "testGlobs",
        ["**/*.test.*", "**/*.spec.*", "**/test_*.py", "**/tests/**", "**/e2e/**"],
    )
    if match_any(rel, test_globs):
        deny(
            "fix the code, not the test; if the test is wrong, ask the user and record "
            "`testEdit` with their words.",
            source=f"{changes}/{change_id}/decisions.json"
        )

def lock_state() -> dict | None:
    """lock.json as a dict, {} without one, None when it exists but cannot be read (fails closed)."""
    path = state_file(change_dir, "lock.json")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def strings(value: object) -> list[str]:
    return [v for v in value if isinstance(v, str) and v] if isinstance(value, list) else []


# a visual change restyles what exists: no data, no auth, no new pages (those start a linked change)
SCOPE_GUARD = [  # at any depth: a monorepo keeps its migrations under packages/<x>/
    "**/migrations/**", "**/drizzle/**", "**/prisma/**", "**/db/migrate/**", "**/alembic/**",
]
# auth names count as whole words (split on punctuation and camelCase), so `author.tsx` is not auth; a restyle exemption is scopeGuard.allow
AUTH_WORDS = {"auth", "oauth", "authn", "authz", "authentication", "authorization", "login", "session", "sessions",
              "permission", "permissions", "rbac", "acl"}
ROUTE_EXT = ("tsx", "jsx", "ts", "js", "mjs", "mts", "cjs")
ROUTE_FILES = [f"**/{n}.{e}" for n in ("page", "route", "layout") for e in ROUTE_EXT] + ["**/pages/**", "**/routes/**"]


def auth_path(path: str) -> bool:
    for part in path.split("/"):
        words = re.split(r"[^A-Za-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", part))
        if any(w.lower() in AUTH_WORDS for w in words):
            return True
    return False


def at_approval(path: str, lock: dict | None) -> bool:
    """The file exists at the commit the plan was approved at (the lock's `sha`; HEAD for a lock from
    before it was kept). A literal path, so a route staged or written since approval is still new."""
    sha = (lock or {}).get("sha")
    ref = sha if isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{7,40}", sha) else "HEAD"
    return subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{ref}:{path}"], capture_output=True).returncode == 0


def has_visual_source(value: object) -> bool:
    """decisions.json `visualSource` names a design: not absent, empty or `none` (verify_gate.py holds the same rule)."""
    if isinstance(value, dict):
        return bool(value) and str(value.get("kind", "")).strip().lower() != "none"
    return isinstance(value, str) and value.strip().lower() not in ("", "none")


def scope_guard() -> None:
    lock = lock_state()
    if lock is not None and not (has_visual_source(decisions.get("visualSource")) or lock.get("screens") == "required"):
        return
    sg = cfg.get("scopeGuard")
    sg = sg if isinstance(sg, dict) else {}
    if match_any(rel, strings(sg.get("allow"))):
        return
    # the plan's folders are the snapshot approval locked, never the plan.md an edit can change
    folders = [f.strip("/") for f in strings((lock or {}).get("scopeFolders")) if ".." not in f.split("/") and f.strip("/")]
    new_route = match_any(rel, strings(sg.get("routes")) or ROUTE_FILES) and not at_approval(rel, lock) and not any(rel == f or rel.startswith(f + "/") for f in folders)
    if lock is None or match_any(rel, SCOPE_GUARD) or auth_path(rel) or new_route:
        deny(
            f"{rel}: a visual change does not add data, auth or new pages: start a linked change "
            "(`sdlc-run` new change) for it. A repo allows a path with sdlc.json `scopeGuard.allow`."
            + (" lock.json cannot be read, so the guard refuses." if lock is None else ""),
            source=f"{changes}/{change_id}/lock.json and decisions.json",
            action="start a linked change for the data, auth or page work",
        )


try:
    scope_guard()
except Exception as err:  # a guard that cannot decide refuses (SystemExit from deny passes through)
    deny(f"the visual scope guard failed ({type(err).__name__}); refusing {rel}. Fix sdlc.json scopeGuard.", source="sdlc.json scopeGuard")

if v3 and not skipped(decisions, "prototype") and not (state_file(change_dir, "lock.json")).exists():  # design only
    for proto in cfg.get("prototypeDirs", []):
        p = proto.rstrip("/")
        if rel == p or rel.startswith(p + "/"):
            sys.exit(0)

if is_milestone(decisions) or is_v4(change_dir, decisions):
    locked = (state_file(change_dir, "lock.json")).exists()
    v4 = is_v4(change_dir, decisions)
    if locked and match_any(rel, cfg.get("protected", PROTECTED_GLOBS)) and not authorized(rel, change_id, change_dir, decisions):
        deny(
            f"{rel} is a protected path since the plan was approved. Stop and ask; record the "
            f"engineer's words as `protectedEdit` in {changes}/{change_id}/decisions.json first.",
            source=f"{changes}/{change_id}/lock.json and decisions.json", action="stop and ask the engineer; their words go in decisions.json as protectedEdit"
        )
    if v4:  # the plan gate is `status: approved` on each of the three documents, and the lock
        unapproved = [
            f for f in ("spec.md", "design.md", "tasks.md")
            if (change_dir / f).exists() and fm(change_dir / f, "status") != "approved"
        ] + ([] if (change_dir / "spec.md").exists() else ["spec.md"])
        # scope S is spec.md alone (no tasks.md, so no handover to require); M and L keep it in tasks.md
        no_tasks = fm(change_dir / "spec.md", "scope") not in ("M", "L") and not (change_dir / "tasks.md").exists()
        handover = None if no_tasks else ("tasks.md", "Handover")
    else:
        unapproved = [] if fm(change_dir / "plan.md", "status") == "approved" else ["plan.md"]
        handover = ("plan.md", "Goal handover")
    if unapproved or not locked:
        deny(
            f"{changes}/{change_id} is not approved yet ({', '.join(unapproved) or 'lock.json'}). One gate approves the change: "
            f"plannotator annotate {changes}/{change_id}/{'spec.md' if v4 else 'plan.md'} --gate, then "
            f"python3 scripts/verify_gate.py approve {change_id}.",
            source=f"{changes}/{change_id}/{unapproved[0] if unapproved else 'lock.json'} and lock.json"
        )
    if handover and not section(change_dir / handover[0], handover[1]):
        deny(f"{changes}/{change_id}/{handover[0]} has an empty ## {handover[1]}. Write the /goal there first.", source=f"{changes}/{change_id}/{handover[0]}")
    active = goal_active(transcript)
    if active is None:
        print("chain-gate: transcript unreadable, cannot check for an active /goal; allowing.", file=sys.stderr)
    elif not active and os.environ.get("SDLC_GOAL_OFF") != "1":  # the off switch lets build edits through
        deny(
            "building happens inside /goal. Start it "
            + (f"with the condition in {changes}/{change_id}/{handover[0]} ## {handover[1]}" if handover else f"for {changes}/{change_id}/spec.md")
            + ", then edit again.",
            source=f"the transcript {transcript}",
            action=(f"start the /goal from the ## {handover[1]} in {changes}/{change_id}/{handover[0]}" if handover else f"start the /goal for {changes}/{change_id}/spec.md")
            + " (a person types it)",
        )
    sys.exit(0)

if not (change_dir / "plan.md").exists():
    deny(
        f"{changes}/{change_id} has no plan.md, and this branch is its branch. Write the plan "
        f"and gate it: plannotator annotate {changes}/{change_id}/plan.md --gate",
        source=f"{changes}/{change_id}/plan.md"
    )
if fm(change_dir / "plan.md", "status") != "approved":
    deny(
        f"{changes}/{change_id}/plan.md is not approved. Gate it before writing source: "
        f"plannotator annotate {changes}/{change_id}/plan.md --gate",
        source=f"{changes}/{change_id}/plan.md"
    )
if not section(change_dir / "plan.md", "Goal handover"):
    deny(
        f"{changes}/{change_id}/plan.md has an empty ## Goal handover. Write the /goal there "
        "before building, or `none -- <why>` when the artifact is the diff itself.",
        source=f"{changes}/{change_id}/plan.md"
    )
PY
