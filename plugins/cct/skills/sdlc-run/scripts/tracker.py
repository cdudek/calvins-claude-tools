"""Which tracker plans this repo's work, what is set up for it, and which one to recommend.

    python3 tracker.py detect [--linear-mcp yes|no]

Run from the repo root at `adopt` and at Stage 1.0. The agent passes --linear-mcp because only it
can see its own MCP tools. stdlib only. Output sections (key: value rows):

    -#-#- TRACKER -#-#-     configured, in_use, recommend, reason
    -#-#- LINEAR -#-#-      mcp
    -#-#- GITHUB -#-#-      gh, authed, project_scope, repo, open_milestones
    -#-#- BEADS -#-#-       bd, initialised
    -#-#- SETUP -#-#-       the missing steps for the recommended tracker, one per row

The rules (references/trackers.md explains each): a tracker set in sdlc.json wins; else the one
this repo already uses, because switching splits the history; else GitHub when gh works, because it needs no extra tool;
else Beads when bd is installed; else none, and the repo files are the plan. Linear is picked only when sdlc.json or the repo
already uses it.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

KINDS = ("linear", "github", "beads", "none")


def run(*cmd: str) -> tuple[int, str]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return out.returncode, (out.stdout + out.stderr).strip()


def configured(cfg: dict) -> str:
    kind = (cfg.get("tracker") or {}).get("kind", "")
    if kind in KINDS:
        return kind
    return "linear" if (cfg.get("linear") or {}).get("team") else ""


def github_repo() -> str:
    _, url = run("git", "remote", "get-url", "origin")
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?$", url)
    return m.group(1) if m else ""


def detect(linear_mcp: str) -> dict:
    cfg_path = Path("sdlc.json")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    repo = github_repo()
    gh = shutil.which("gh") is not None
    code, auth = run("gh", "auth", "status") if gh else (1, "")
    authed = gh and code == 0
    scope = authed and re.search(r"['\"]project['\"]", auth) is not None
    milestones = 0
    if authed and repo:
        code, out = run("gh", "api", f"repos/{repo}/milestones?state=open", "--jq", "length")
        milestones = int(out) if code == 0 and out.isdigit() else 0
    bd = shutil.which("bd") is not None
    beads = Path(".beads").is_dir()

    in_use = [
        kind
        for kind, evidence in (
            ("linear", bool((cfg.get("linear") or {}).get("team"))),
            ("github", milestones > 0),
            ("beads", beads),
        )
        if evidence
    ]
    chosen = configured(cfg)
    if chosen:
        kind, reason = chosen, "sdlc.json already names it"
    elif in_use:
        kind = in_use[0]
        reason = (
            f"this repo already uses it ({', '.join(in_use)} in use); switching splits the history"
        )
    elif authed:
        kind, reason = "github", "gh already works here, so it needs no extra tool"
    elif bd:
        kind, reason = "beads", "bd is installed and keeps the plan local, with epics"
    else:
        kind, reason = "none", "nothing is set up; the repo files are the plan until a tracker is"

    setup = {
        "linear": []
        if linear_mcp == "yes"
        else ["connect the Linear MCP: /mcp → claude.ai Linear"],
        "github": (
            ([] if gh else ["install gh: brew install gh"])
            + ([] if authed else ["gh auth login"])
            + ([] if scope else ["gh auth refresh -s project  (boards need the project scope)"])
        ),
        "beads": ([] if bd else ["install beads: brew install beads"])
        + ([] if beads else ["bd init  (creates .beads/ in this repo)"]),
        "none": [],
    }[kind]
    return {
        "TRACKER": {
            "configured": chosen or "none",
            "in_use": ",".join(in_use) or "none",
            "recommend": kind,
            "reason": reason,
        },
        "LINEAR": {"mcp": linear_mcp},
        "GITHUB": {
            "gh": "yes" if gh else "no",
            "authed": "yes" if authed else "no",
            "project_scope": "yes" if scope else "no",
            "repo": repo or "none",
            "open_milestones": str(milestones),
        },
        "BEADS": {"bd": "yes" if bd else "no", "initialised": "yes" if beads else "no"},
        "SETUP": {f"step{i}": s for i, s in enumerate(setup, 1)} or {"steps": "none"},
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] != "detect":
        print(__doc__)
        return 2
    mcp = argv[argv.index("--linear-mcp") + 1] if "--linear-mcp" in argv else "unknown"
    for name, rows in detect(mcp).items():
        print(f"-#-#- {name} -#-#-")
        for key, value in rows.items():
            print(f"- {key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
