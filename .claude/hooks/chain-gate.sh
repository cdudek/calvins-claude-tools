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
# v3 = decisions.json has `size`; v2 folders keep the v2 rules, v3 folders without `milestone`
# keep the v3 rules, so in-flight changes finish on the process they started. Rules 5-7 fire
# only when the checked-out branch has a change folder: no folder, no opinion. Bash wrapper,
# Python engine.
set -uo pipefail
. "$(dirname "$0")/sdlc-config.sh"

payload=$(cat)
file=$(sdlc_field "$payload" file_path)
[ -n "$file" ] || exit 0
[ -f "$SDLC_JSON" ] || exit 0
transcript=$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("transcript_path") or "")' 2>/dev/null || true)

python3 - "$SDLC_ROOT" "$SDLC_JSON" "$file" "$transcript" <<'PY'
from __future__ import annotations

import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
cfg_path = Path(sys.argv[2])
file_arg = sys.argv[3]
transcript = sys.argv[4] if len(sys.argv) > 4 else ""
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


def deny(message: str) -> None:
    print(f"BLOCKED: {message}\n({docs})", file=sys.stderr)
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


def load_decisions(change_dir: Path) -> dict:
    path = change_dir / "decisions.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def is_v3(decisions: dict) -> bool:
    return "size" in decisions


def is_milestone(decisions: dict) -> bool:
    return "milestone" in decisions


PROTECTED_FILES = ("facts.md", "done.json", "lock.json")
PROTECTED_GLOBS = ["sdlc.json", "**/*-snapshots/**", "**/__screenshots__/**", "**/*allowlist*"]


def goal_active(path: str) -> bool | None:
    """True/False from the last goal_status entry of the transcript; None when unreadable.

    The entry is undocumented: {"type":"attachment","attachment":{"type":"goal_status",
    "met":false,...}}. Unreadable fails open with a warning rather than blocking every edit.
    """
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
        return None
    parsed, last = 0, None
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        parsed += 1
        att = entry.get("attachment") if isinstance(entry, dict) else None
        if isinstance(att, dict) and att.get("type") == "goal_status":
            last = att
    if not parsed:
        return None
    return last is not None and last.get("met") is False


def skipped(decisions: dict, activity: str) -> bool:
    value = decisions.get("skips", {}).get(activity, "")
    return isinstance(value, str) and value.startswith("skip")


def activity_done(change_dir: Path, decisions: dict, activity: str) -> bool:
    files = {
        "brief": change_dir / "spec" / "brief.md",
        "ia": change_dir / "spec" / "ia.md",
        "interaction": change_dir / "spec" / "interaction.md",
        "screens": change_dir / "spec" / "screens.md",
        "prototype": change_dir / "spec" / "prototype" / "index.md",
        "conformance": change_dir / "spec" / "conformance.md",
        "validation": change_dir / "spec" / "validation.md",
    }
    return skipped(decisions, activity) or files[activity].exists()


def validation_ready(change_dir: Path, decisions: dict) -> bool:
    if skipped(decisions, "validation"):
        return True
    validation = change_dir / "spec" / "validation.md"
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


def branch_change() -> tuple[str, Path, dict] | None:
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
        fnmatch.fnmatchcase(path, pat) or fnmatch.fnmatchcase(path, pat.removeprefix("**/"))
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

    if base == "decisions.json":
        sys.exit(0)
    if not (change_dir / "decisions.json").exists():
        deny(
            f"the Stage 1.1 dialog has not run for {change_id}. AskUserQuestion must ask ticket "
            f"(search Linear first), intent, design file, size and kind; then write "
            f"{changes}/{change_id}/decisions.json."
        )

    decisions = load_decisions(change_dir)
    v3 = is_v3(decisions)

    if is_milestone(decisions):
        if inside in PROTECTED_FILES and (change_dir / "lock.json").exists():
            if decisions.get("protectedEdit"):
                sys.exit(0)
            deny(
                f"{changes}/{change_id}/{inside} is locked since the engineer approved the plan. "
                "Stop and ask; record their words as `protectedEdit` in decisions.json first."
            )
        if (inside.startswith("spec/") or base == "facts.md") and fm(
            change_dir / "intent.md", "status"
        ) != "approved":
            deny(
                f"{changes}/{change_id}/intent.md is not approved. Draft it (asks, job stories, "
                "success measure) and have the engineer confirm it first."
            )
        if base == "facts.md" and decisions.get("size") != "none" and cfg.get("ux", "on") != "off":
            needed = ["conformance"] + (["validation"] if decisions.get("size") in ("M", "L") else [])
            missing = [a for a in needed if not activity_done(change_dir, decisions, a)]
            if missing:
                deny(
                    f"{changes}/{change_id}/facts.md comes after the UX plan: {', '.join(missing)} "
                    f"missing. Run cct:ux-rules-validate spec {change_id}"
                    + (f" and one pass of cct:ux-spec-validate spec {change_id}." if "validation" in missing else ".")
                )
        if base == "plan.md" and not (change_dir / "facts.md").exists():
            deny(f"{changes}/{change_id}/facts.md does not exist yet. Facts come before a plan.")
        sys.exit(0)

    if v3 and inside.startswith("spec/") and not has_asks(change_dir):
        deny(
            f"{changes}/{change_id}/intent.md needs a non-empty ## Asks table before spec files. "
            f"Run Stage 1.3 and write the A<n> table, then continue with cct:ux-design-run {change_id}."
        )

    if base == "facts.md":
        # The intent decision comes first, v2 and v3 alike: a skip with its reason, or the interview.
        intent = str(decisions.get("intent", ""))
        if not intent:
            deny(
                f"decisions.json for {change_id} records no intent decision. Record a skip with "
                "its reason, or run the interview."
            )
        if not intent.startswith("skip") and not (change_dir / "interview-result.json").exists():
            deny(
                f"the intent interview has not run for {change_id}. Run: plannotator "
                f"setup-goal interview {changes}/{change_id}/interview.json --json | "
                f"tee {changes}/{change_id}/interview-result.json"
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
                    f"{', '.join(missing)}. Run {'; '.join(commands)}."
                )

    if base == "plan.md":
        if not (change_dir / "facts.md").exists():
            deny(f"{changes}/{change_id}/facts.md does not exist yet. Facts come before a plan.")
        if fm(change_dir / "facts.md", "status") != "approved":
            deny(
                f"{changes}/{change_id}/facts.md is not approved. Run the facts/spec gate before "
                "writing the plan."
            )
        if v3 and not validation_ready(change_dir, decisions):
            deny(
                f"{changes}/{change_id}/spec/validation.md must have verdict: ready and "
                f"status: approved, or validation must be skipped. Run cct:ux-spec-validate spec "
                f"{change_id}, then get the owner gate."
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
            "`testEdit` with their words."
        )

if v3 and not skipped(decisions, "prototype"):
    for proto in cfg.get("prototypeDirs", []):
        p = proto.rstrip("/")
        if rel == p or rel.startswith(p + "/"):
            sys.exit(0)

if is_milestone(decisions):
    locked = (change_dir / "lock.json").exists()
    if locked and match_any(rel, cfg.get("protected", PROTECTED_GLOBS)) and not decisions.get("protectedEdit"):
        deny(
            f"{rel} is a protected path since the plan was approved. Stop and ask; record the "
            f"engineer's words as `protectedEdit` in {changes}/{change_id}/decisions.json first."
        )
    if fm(change_dir / "plan.md", "status") != "approved" or not locked:
        deny(
            f"{changes}/{change_id} is not approved yet. One gate approves UX plan, facts and plan: "
            f"plannotator annotate {changes}/{change_id}/plan.md --gate, then "
            f"python3 scripts/verify_gate.py approve {change_id}."
        )
    if not section(change_dir / "plan.md", "Goal handover"):
        deny(f"{changes}/{change_id}/plan.md has an empty ## Goal handover. Write the /goal there first.")
    active = goal_active(transcript)
    if active is None:
        print("chain-gate: transcript unreadable, cannot check for an active /goal; allowing.", file=sys.stderr)
    elif not active:
        deny(
            "building happens inside /goal. Start it with the condition in "
            f"{changes}/{change_id}/plan.md ## Goal handover, then edit again."
        )
    sys.exit(0)

if not (change_dir / "plan.md").exists():
    deny(
        f"{changes}/{change_id} has no plan.md, and this branch is its branch. Write the plan "
        f"and gate it: plannotator annotate {changes}/{change_id}/plan.md --gate"
    )
if fm(change_dir / "plan.md", "status") != "approved":
    deny(
        f"{changes}/{change_id}/plan.md is not approved. Gate it before writing source: "
        f"plannotator annotate {changes}/{change_id}/plan.md --gate"
    )
if not section(change_dir / "plan.md", "Goal handover"):
    deny(
        f"{changes}/{change_id}/plan.md has an empty ## Goal handover. Write the /goal there "
        "before building, or `none -- <why>` when the artifact is the diff itself."
    )
PY
