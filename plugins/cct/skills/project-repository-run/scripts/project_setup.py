#!/usr/bin/env python3
"""Brings a repo to the blueprint baseline: declares plugins, adds the Decision4 contract and a starter
boundary map, and checks the result. Stdlib only. Nothing is written without --yes.

    project_setup.py [--root DIR] [--plugins cct@cct[,x@y]] [--marketplace-ref REF]
                     [--marketplace-source NAME=OWNER/REPO] [--decision4|--no-decision4]
                     [--anti-slop|--no-anti-slop] [--sdlc|--no-sdlc] [--check] [--yes] [--dry-run]

Exit codes: 0 ok, 1 --check found drift or a problem, 2 unreadable settings.json.
"""
from __future__ import annotations

import argparse
import copy
import json
import importlib.util
import re
import sys
from pathlib import Path

CCT_MARKETPLACE, CCT_REPO = "cct", "cdudek/calvins-claude-tools"
CLASSES = ("Undo", "Repair", "Migrate", "Answer")
VERSION_RE = re.compile(r"Decision4 handoff contract \(v(\d+)\)")
HEADING = "## Decision4 handoff contract (v1)"
SOURCE = ("Source: Decision4 v1.0.1 (https://github.com/Habitat-Thinking/decision4/blob/v1.0.1/DECISION4.md), "
          "Habitat Thinking, CC BY 4.0.")
# Handoff rules adapted from AGENTS-snippet.md at tag v1.0.1
CONTRACT = f"""{HEADING}

For every decision you make, ask: "If this turns out to be wrong,
what does it take to put right?" Take the class from the boundary map.
Classes run from lowest to highest: Undo, Repair, Migrate, Answer.

- Undo (a revert): hand back the result.
- Repair (real work, contained to this team): hand back the result and a
  choice story: Chose / Over / Because / Commits us to.
- Migrate (coordinated change involving other people): hand back at least
  two real options, or one stated as forced with the constraint that forces it.
- Answer (an explanation to someone outside the team with standing to ask,
  because the wrong outcome has reached them and nothing unmakes it): hand back
  evidence labelled observed, inferred, asked or unknown, and your challenges.
  Do not recommend.

Rules:
- Propose a class at or above the map's floor, never below it.
- Unmapped or unsure: take the higher class and log a map gap.
- A change takes the class of its highest decision.
- Escalate freely and say who it pulls in. Never lower a class silently.
- Unattended runs close only Undo. Above Undo, hand back and stop.

{SOURCE}

The boundary map is `boundary-map.yaml` at the repo root; read it before classifying.
For PRs, fill the repository's readable Decision4 section and follow its writing-rules
HTML comment. Choose the highest applicable class from the whole diff and the map.
Validate the proposed body with `.github/scripts/decision4.py` before pushing; keep the
repository's own local gate and check invocation. PyYAML is required by the checker.
Run `bash tests/decision4/run.sh` for the synthetic regression fixtures; validate actual
changed paths separately with the repository's `boundary-map.yaml`.
"""
# Load the same offline assets used by sdlc-run adopt.
_spec = importlib.util.spec_from_file_location(
    "decision4_assets", Path(__file__).resolve().parents[2] / "sdlc-run/scripts/decision4_assets.py"
)
_assets = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_assets)
STARTER_MAP = _assets.STARTER_MAP
ANTI_SLOP_CMD = "npx skills add dmmulroy/anti-slop --skill install-anti-slop"


def read(p: Path) -> str:
    return p.read_text() if p.exists() else ""


def imported(root: Path, f: Path, text: str) -> list[Path]:
    """Files a markdown agent file pulls in with a leading `@path` line (one level)."""
    return [q for m in re.finditer(r"^@(\S+)", text, re.M) if (q := (f.parent / m.group(1))).is_file()]


def settings_changes(root, plugins, ref, sources, problems):
    path = root / ".claude/settings.json"
    try:
        orig = json.loads(read(path) or "{}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path}: not valid JSON ({e}); fix it first, nothing was changed") from None
    s = copy.deepcopy(orig)
    mk, ep = s.setdefault("extraKnownMarketplaces", {}), s.setdefault("enabledPlugins", {})
    for name in sorted({p.split("@")[1] for p in plugins}):
        repo = CCT_REPO if name == CCT_MARKETPLACE else sources.get(name)
        entry = mk.get(name)
        if entry is None and repo is None:
            problems.append(f"marketplace '{name}' is not declared: pass --marketplace-source {name}=OWNER/REPO")
        elif entry is None:
            src = {"source": "github", "repo": repo}
            if ref and name == CCT_MARKETPLACE:
                src["ref"] = ref
            mk[name] = {"source": src}
        else:
            src = entry.setdefault("source", {})
            if repo and src.get("repo") != repo:
                problems.append(f"marketplace '{name}' points at {src.get('repo') or src}, expected {repo}; not overwritten")
            elif ref and name == CCT_MARKETPLACE and src.get("ref") != ref:
                src["ref"] = ref
    for p in plugins:
        ep[p] = True
    return [("update", path, json.dumps(s, indent=2) + "\n", "declare marketplaces and enable plugins", True)] if s != orig else []


def decision4_changes(root, problems):
    target = next((root / n for n in ("CLAUDE.md", "AGENTS.md") if (root / n).exists()), root / "CLAUDE.md")
    text = read(target)
    versions = {int(v) for v in VERSION_RE.findall(text)}
    if versions:
        if 1 not in versions:
            problems.append(f"{target.name} carries Decision4 contract v{min(versions)}, expected v1")
        return []
    carriers = [q for q in imported(root, target, text) if HEADING in read(q)]
    sep = "\n" if text and not text.endswith("\n") else ""
    if carriers:
        line = f"\nDecision4 handoff contract (v1): the section in `{carriers[0].name}` applies here. {SOURCE}\n"
        return [("update", target, text + sep + line, f"pointer to the contract in {carriers[0].name}", False)]
    body = (text + sep + "\n" if text else "") + CONTRACT
    return [("update" if text else "create", target, body, "add the Decision4 handoff contract v1", True)]


def map_problems(t: str) -> list[str]:
    # Shape only; the repo's Decision4 gate validates the schema. shortcut: line-based, no YAML parser in the stdlib.
    out = [m for ok, m in ((re.search(r"^version:\s*1\s*$", t, re.M), "version: 1 missing"),
                           (re.search(r"^entries:\s*$", t, re.M), "entries: missing")) if not ok]
    floors = [f.strip("'\"") for f in re.findall(r"^\s*floor:\s*(\S+)\s*$", t, re.M)]
    selects = len(re.findall(r"^\s*-\s*select:", t, re.M))
    if not floors:
        out.append("no entry has a floor")
    if len(floors) != selects:
        out.append(f"{selects} select blocks but {len(floors)} floors")
    out += [f"unknown floor '{f}'" for f in floors if f not in CLASSES]
    return out


def map_changes(root, problems):
    path = root / "boundary-map.yaml"
    if not path.exists():
        return [("create", path, STARTER_MAP, "starter boundary map (covers its own trust ground at Migrate)", True)]
    problems += [f"boundary-map.yaml: {p}" for p in map_problems(read(path))]
    return []


def is_typescript(root: Path) -> bool:
    pkg = read(root / "package.json")
    return (root / "tsconfig.json").exists() or '"typescript"' in pkg


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    B = argparse.BooleanOptionalAction
    ap.add_argument("--root", default=".")
    ap.add_argument("--plugins", action="append", help="name@marketplace, comma-separated or repeated (default cct@cct)")
    ap.add_argument("--marketplace-ref", help="git ref (tag, branch) to pin the cct marketplace to")
    ap.add_argument("--marketplace-source", action="append", default=[], metavar="NAME=OWNER/REPO",
                    help="GitHub repo of a non-cct marketplace named in --plugins")
    ap.add_argument("--decision4", action=B, default=True)
    ap.add_argument("--anti-slop", action=B, default=None, help="default: on for TypeScript repos")
    ap.add_argument("--sdlc", action=B, default=True)
    ap.add_argument("--check", action="store_true", help="read-only drift check; exit 1 when something is missing")
    ap.add_argument("--yes", action="store_true", help="apply; without it the plan is printed and nothing is written")
    ap.add_argument("--dry-run", action="store_true", help="print the plan even with --yes")
    a = ap.parse_args(argv)

    root = Path(a.root).resolve()
    plugins = [p.strip() for v in (a.plugins or [f"cct@{CCT_MARKETPLACE}"]) for p in v.split(",") if p.strip()]
    bad = [p for p in plugins if not re.fullmatch(r"[\w.-]+@[\w.-]+", p)]
    if bad:
        ap.error(f"plugins must look like name@marketplace: {bad}")
    sources = dict(s.split("=", 1) for s in a.marketplace_source if "=" in s)

    problems: list[str] = []
    changes = settings_changes(root, plugins, a.marketplace_ref, sources, problems)
    if a.decision4:
        changes += decision4_changes(root, problems) + map_changes(root, problems)
        changes += [("update" if path.exists() else "create", path, text,
                     "install readable Decision4 template, checker and fixtures", True)
                    for path, text in _assets.asset_changes(root) if path != root / "boundary-map.yaml"]

    if a.check:
        missing = [f"{p.relative_to(root)}: {why}" for _, p, _, why, required in changes if required] + problems
        print("project-repository-run check: " + ("ok" if not missing else f"{len(missing)} missing"))
        for m in missing:
            print(f"  - {m}")
        return 1 if missing else 0

    apply = a.yes and not a.dry_run
    print(("APPLY" if apply else "PLAN (nothing written; add --yes)") + f" in {root}")
    for kind, path, text, why, _ in changes:
        print(f"  {kind} {path.relative_to(root)}: {why}")
        if apply:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    if not changes:
        print("  nothing to change")
    for p in problems:
        print(f"  PROBLEM {p}")
    print("Next:")
    if a.sdlc:
        print("  /cct:sdlc-run adopt")
    if (a.anti_slop if a.anti_slop is not None else is_typescript(root)):
        print(f"  {ANTI_SLOP_CMD}   (then ask the agent to install anti-slop)")
    print("  python3 project_setup.py --check")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
