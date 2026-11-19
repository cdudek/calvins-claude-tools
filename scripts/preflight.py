"""One preflight of what this change will need: tools, auth, Docker and two config conflicts.

    python3 scripts/preflight.py            # prints one `FAIL <what>: <fix>` line per failure, exit 1
    python3 scripts/preflight.py --config   # only the config conflicts (CI: no tool or auth to find yet)

Run it once at plan approval and once at the start of CI, so a missing capability fails in seconds, not
after an hour of building. It checks only what the repo declares, so it never fails on a tool nobody
uses:

- tools: `git`, the first word of `verify`, and `sdlc.json` `preflight.tools` (a list of commands)
- auth: `preflight.auth`, a list of `{"name", "check", "fix"}`; `check` runs once (15 s limit),
  exit 0 means signed in; `fix` is the one line printed on failure
- disk: free space on the repo's volume (`preflight.minFreeGB`, default 15): FAIL below it, WARN below twice it
- Docker or Podman (db.test.engine, as db.py picks it), only when `db.test` is configured or `preflight.docker` is true
- config: feature-PR delivery with local milestones (the milestone branch it needs is the one a local
  milestone never pushes; `adopt` refuses the same pair), and a `blocked[]` rule with no message (a refusal with no route)

Written by `sdlc-run adopt` from the kit; edit the kit, not this copy. stdlib only.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

TIMEOUT = 15


def ok(argv: list[str]) -> bool:
    try:
        return subprocess.run(argv, capture_output=True, timeout=TIMEOUT).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def config_conflicts(cfg: dict) -> list[str]:
    out: list[str] = []
    merge = (
        (cfg.get("milestones") or {}).get("merge")
        if isinstance(cfg.get("milestones"), dict)
        else None
    )
    if cfg.get("delivery") == "feature-prs" and merge == "local":
        out.append(
            "FAIL config delivery: feature PRs need a published milestone branch and local milestones "
            'forbid it; choose remote feature PRs (milestones.merge "pr") or local feature commits '
            '(delivery "one-go") in sdlc.json'
        )
    for i, rule in enumerate(cfg.get("blocked") or []):
        if isinstance(rule, dict) and not str(rule.get("message", "")).strip():
            out.append(
                f"FAIL config blocked[{i}]: add a `message` saying who does what instead; "
                "a refusal without a route leaves the agent stuck"
            )
    return out


def disk_lines(pre: dict) -> list[str]:
    """FAIL below `preflight.minFreeGB` (default 15), WARN below twice that: a full disk fails a build
    in a way that reads like a code bug."""
    try:
        need = float(pre.get("minFreeGB", 15))
        free = shutil.disk_usage(".").free / 2**30
    except (OSError, ValueError, TypeError):
        return []
    if free < need:
        return [
            f"FAIL disk: {free:.1f} GB free, need {need:g} (preflight.minFreeGB); remove old "
            "worktrees, caches or containers"
        ]
    if free < 2 * need:
        return [f"WARN disk: {free:.1f} GB free, under twice preflight.minFreeGB ({need:g})"]
    return []


def pick_engine(test: dict) -> str:
    """The engine db.py would use (db.test.engine, SDLC_DB_ENGINE, docker unless only podman is installed);
    db.py's own function when it sits beside this file."""
    path = Path(__file__).with_name("db.py")
    if path.is_file():
        spec = importlib.util.spec_from_file_location("sdlc_db_engine", path)
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod.pick_engine(test)
    return test.get("engine") or os.environ.get("SDLC_DB_ENGINE") or "docker"


def failures(cfg: dict, config_only: bool = False) -> list[str]:
    out = config_conflicts(cfg)
    if config_only:
        return out
    pre = cfg.get("preflight") if isinstance(cfg.get("preflight"), dict) else {}
    tools = ["git"] + list(pre.get("tools", []))
    words = shlex.split(cfg["verify"]) if isinstance(cfg.get("verify"), str) else []
    tools += words[:1]
    for tool in dict.fromkeys(tools):
        if not shutil.which(tool):
            out.append(f"FAIL tool {tool}: install `{tool}` and put it on PATH")
    for a in pre.get("auth", []):
        if isinstance(a, dict) and a.get("check") and not ok(shlex.split(a["check"])):
            out.append(
                f"FAIL auth {a.get('name', a['check'])}: {a.get('fix') or 'sign in, then rerun preflight'}"
            )
    out += disk_lines(pre)
    if (isinstance(cfg.get("db"), dict) and "test" in cfg["db"]) or pre.get("docker"):
        test = cfg["db"]["test"] if isinstance(cfg.get("db"), dict) and isinstance(cfg["db"].get("test"), dict) else {}
        engine = pick_engine(test)
        if not (shutil.which(engine) and ok([engine, "info"])):
            out.append(
                f"FAIL {engine}: start {engine} ("
                + ("Docker Desktop or `colima start`" if engine == "docker" else "`podman machine start`")
                + "), then rerun preflight"
            )
    return out


def main(argv: list[str]) -> int:
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    try:
        cfg = json.loads(Path("sdlc.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("FAIL config sdlc.json: run from the repo root; the file must be valid JSON")
        print("PREFLIGHT FAIL 1")
        return 1
    found = failures(cfg if isinstance(cfg, dict) else {}, "--config" in argv)
    bad = [x for x in found if x.startswith("FAIL")]  # a WARN line informs and never fails
    print("\n".join(found + [f"PREFLIGHT FAIL {len(bad)}" if bad else "PREFLIGHT OK"]))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
