"""Which sdlc-run version a repo runs, and whether the kit has moved on.

    python3 scripts/sdlc_version.py [repo]      # prints one line when the repo is not current, else nothing

`adopt` stamps sdlc.json `sdlcVersion` with the kit's version (SKILL.md `metadata.version`).
Every use of the skill compares the two and says so; it never blocks. Written by
`sdlc-run adopt` from the kit; edit the kit, not this copy. stdlib only, runs on python3.9.

The kit's version comes from, in order: env SDLC_KIT_VERSION; the SKILL.md two levels above this
file (when run from the kit); the newest installed cct plugin under ~/.claude/plugins/cache.
In a CI runner none of these exists, so there is nothing to compare and nothing is printed,
except that a repo with no stamp at all is always named.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

VERSION = re.compile(r"^\s*version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", re.M)


def parse(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split("."))


def _skill_md() -> Path | None:
    parents = Path(__file__).resolve().parents
    own = (
        parents[2] / "SKILL.md" if len(parents) > 2 else None
    )  # the kit: <skill>/templates/scripts/
    if own and own.is_file() and "name: sdlc-run" in own.read_text(encoding="utf-8"):
        return own
    cache = Path.home() / ".claude" / "plugins" / "cache"
    found = sorted(cache.glob("*/cct/*/skills/sdlc-run/SKILL.md"), key=lambda p: p.parts[-5:])
    return found[-1] if found else None


def kit_version() -> tuple[str | None, Path | None]:
    """(version, the kit's references/changelog.md when it can be found)."""
    skill = _skill_md()
    changelog = skill.parent / "references" / "changelog.md" if skill else None
    env = os.environ.get("SDLC_KIT_VERSION")
    if env:
        return env, changelog
    if skill:
        m = VERSION.search(skill.read_text(encoding="utf-8"))
        return (m.group(1) if m else None), changelog
    return None, None


def entries(changelog: Path | None) -> list[tuple[str, str, list[str], list[str]]]:
    """(version, headline, mechanical migrations, manual migrations), newest first."""
    if not changelog or not changelog.is_file():
        return []
    out = []
    for block in re.split(r"^## ", changelog.read_text(encoding="utf-8"), flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        m = re.match(r"([0-9]+\.[0-9]+\.[0-9]+)\s*(?:—|-|:)\s*(.+)", head.strip())
        if not m:
            continue
        lines = body.splitlines()
        mech = [
            ln[len("- Mechanical:") :].strip() for ln in lines if ln.startswith("- Mechanical:")
        ]
        manual = [ln[len("- Manual:") :].strip() for ln in lines if ln.startswith("- Manual:")]
        out.append((m.group(1), m.group(2).strip(), mech, manual))
    return out


def between(
    changelog: Path | None, stamp: str | None, kit: str
) -> list[tuple[str, str, list[str], list[str]]]:
    low = parse(stamp) if stamp else (0, 0, 0)
    return [e for e in entries(changelog) if low < parse(e[0]) <= parse(kit)]


def message(stamp: str | None, kit: str | None, changelog: Path | None = None) -> str | None:
    """The one line to print, or None when the repo is current (or the kit's version is unknown
    and the repo is stamped)."""
    if not kit:
        if stamp:
            return None
        return "This repo has no sdlcVersion stamp. Run `adopt --upgrade` from the cct plugin."
    if stamp and parse(stamp) == parse(kit):
        return None
    if stamp and parse(stamp) > parse(kit):
        return (
            f"This repo runs sdlc-run {stamp}, newer than the installed kit {kit}. "
            "Update the cct plugin."
        )
    heads = "; ".join(f"{v}: {h}" for v, h, _, _ in between(changelog, stamp, kit))
    tail = f" (changes: {heads})" if heads else ""
    return (
        f"This repo runs sdlc-run {stamp or 'none'}; the kit is {kit}. Run `adopt --upgrade`{tail}."
    )


def main(argv: list[str]) -> int:
    repo = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    cfg = repo / "sdlc.json"
    if not cfg.is_file():
        return 0
    stamp = json.loads(cfg.read_text(encoding="utf-8")).get("sdlcVersion")
    kit, changelog = kit_version()
    line = message(stamp, kit, changelog)
    if line:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
