"""Where a change stands: every milestone, the features of this one, and the stage.

    python3 scripts/sdlc_status.py map [<id>]

Written by `sdlc-run adopt` from the kit; edit the kit, not this copy. stdlib only.

Everything is read from the files, nothing is written. The stage (1-7): an archived change → 7,
lock.json → 5 (6 once every feature is merged), plan.md → 4, facts.md → 3, an approved intent → 2,
otherwise 1. Milestone position comes from the design doc's `## Milestones` list (decisions.json
`design`), features from the milestone's `milestone.md` Features table.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

STAGES = ("Intent", "UX plan", "Facts", "Tech plan", "Build", "Milestone", "Outcome")


def git(root: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def repo_root(start: Path) -> Path | None:
    top = git(start, "rev-parse", "--show-toplevel")
    return Path(top) if top and (Path(top) / "sdlc.json").exists() else None


def config(root: Path) -> dict:
    return json.loads((root / "sdlc.json").read_text(encoding="utf-8"))


def slug_of(name: str) -> str:
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)
    return re.sub(r"^[A-Z][A-Z0-9]+-\d+-", "", name)


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def find_change(root: Path, cfg: dict, change_id: str | None) -> Path | None:
    base = root / cfg.get("changesDir", "changes")
    if change_id:
        return base / change_id if (base / change_id).is_dir() else None
    if not base.is_dir():
        return None
    folders = [d for d in base.iterdir() if d.is_dir() and d.name != "archive"]
    branch = git(root, "symbolic-ref", "--short", "-q", "HEAD")
    for d in sorted(folders):
        if branch and slug_of(d.name) in branch:
            return d
    return folders[0] if len(folders) == 1 else None


def frontmatter(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    m = re.search(rf"^{key}:\s*(.+)$", path.read_text(encoding="utf-8"), re.M)
    return m.group(1).strip() if m else ""


def section(text: str, heading: str) -> list[str]:
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return [line for line in m.group(1).splitlines() if line.strip()] if m else []


def initiative(change: Path, root: Path, decisions: dict) -> tuple[str, int, int]:
    """(name, milestone position, milestone total); 0/0 without a design doc listing it."""
    named = decisions.get("milestone", {}).get("initiative", "")
    design = root / str(decisions.get("design", ""))
    pos = total = 0
    if decisions.get("design") not in (None, "", "none") and design.is_file():
        text = design.read_text(encoding="utf-8")
        title = re.search(r"^# (?:Design:\s*)?(.+)$", text, re.M)
        named = named or (title.group(1).strip() if title else "")
        items = [li for li in section(text, "Milestones") if re.match(r"\s*(?:[-*]|\d+\.)\s", li)]
        total = len(items)
        pos = next((i for i, li in enumerate(items, 1) if slug_of(change.name) in li), 0)
    if not named:
        plan = change / "plan.md"
        title = (
            re.search(r"^# Plan:\s*(.+)$", plan.read_text(encoding="utf-8"), re.M)
            if plan.exists()
            else None
        )
        named = title.group(1).strip() if title else slug_of(change.name).replace("-", " ")
    return named, pos, total


def features(change: Path, root: Path, cfg: dict, decisions: dict) -> list[dict]:
    """Rows of the milestone's Features table: [{id, feature, state}]."""
    milestone = change / "milestone.md"
    slug = decisions.get("milestone", {}).get("slug", "")
    if not milestone.exists() and slug:
        base = root / cfg.get("changesDir", "changes")
        milestone = next(
            (m for m in base.glob("*/milestone.md") if frontmatter(m, "milestone") == slug),
            milestone,
        )
    if not milestone.exists():
        return []
    rows = []
    for line in section(milestone.read_text(encoding="utf-8"), "Features"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[0] not in ("#", "") and not set(cells[0]) <= {"-", ":"}:
            rows.append({"id": f"F{cells[0]}", "feature": cells[2], "state": cells[4]})
    return rows


def stage_of(change: Path, rows: list[dict]) -> int:
    if "archive" in change.parts:
        return 7
    if (change / "lock.json").exists():
        return 6 if rows and all(r["state"].startswith(("merged", "done")) for r in rows) else 5
    if (change / "plan.md").exists():
        return 4
    if (change / "facts.md").exists():
        return 3
    return 2 if frontmatter(change / "intent.md", "status") == "approved" else 1


def state(change: Path, root: Path, cfg: dict) -> dict:
    decisions = read_json(change / "decisions.json")
    name, pos, total = initiative(change, root, decisions)
    rows = features(change, root, cfg, decisions)
    return {
        "initiative": name,
        "pos": pos,
        "total": total,
        "stage": stage_of(change, rows),
        "features": rows,
        "merged": sum(1 for r in rows if r["state"].startswith(("merged", "done"))),
    }


def milestone_map(s: dict) -> str:
    head = s["initiative"] + (f"  M{s['pos']} of {s['total']}" if s["pos"] else "")
    marks = {"merged": "✓", "done": "✓", "building": "◐", "blocked": "✗"}
    bar = "".join(
        next((v for k, v in marks.items() if r["state"].startswith(k)), "○") for r in s["features"]
    )
    lines = [head, f"  this milestone  {s['merged']} of {len(s['features'])} merged  {bar}"]
    lines += [f"    {r['id']:<4} {r['feature']:<32} {r['state']}" for r in s["features"]]
    lines.append(f"  stage  {s['stage']}/7 {STAGES[s['stage'] - 1]}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] != "map":
        print(__doc__)
        return 2
    root = repo_root(Path.cwd())
    if not root:
        print("no sdlc.json in this repo: run `sdlc-run adopt`")
        return 2
    cfg = config(root)
    change = find_change(root, cfg, argv[2] if len(argv) > 2 else None)
    if not change:
        print("no change folder for this branch: pass its id")
        return 2
    print(milestone_map(state(change, root, cfg)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
