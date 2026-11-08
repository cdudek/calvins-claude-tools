"""Classify a set of changed paths into one merge tier: ask, show or ship.

    python3 scripts/ship_show_ask.py classify k8s/base/x.yaml docs/a.md   -> ask
    git diff --name-only origin/<default> | xargs python3 scripts/ship_show_ask.py classify

The globs live in .github/tiers.json so the workflow, this script and the sdlc guardrail
test read one file. Precedence is the `order` list there: a PR is as risky as its riskiest
file. stdlib only -- this runs on a bare GitHub runner before any install step.
"""

from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TIERS_FILE = REPO_ROOT / ".github" / "tiers.json"


def load_tiers(path: Path = TIERS_FILE) -> dict[str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {tier: data[tier] for tier in data["order"]}


def tier_of(file: str, tiers: dict[str, list[str]]) -> str:
    """First tier (in order) with a glob matching the path.

    fnmatch's `*` crosses `/`, so `k8s/**` and `k8s/*` both match `k8s/base/x.yaml` --
    that is the intent: a glob names a subtree. A bare filename like `CLAUDE.md` matches
    the root file only.
    """
    for tier, globs in tiers.items():
        if any(fnmatch.fnmatchcase(file, glob) for glob in globs):
            return tier
    return next(reversed(tiers))


def classify(files: list[str], tiers: dict[str, list[str]] | None = None) -> str:
    tiers = tiers or load_tiers()
    order = list(tiers)
    if not files:
        return order[-1]
    return min((tier_of(f, tiers) for f in files), key=order.index)


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] != "classify":
        print(__doc__, file=sys.stderr)
        return 2
    print(classify([f for f in argv[2:] if f]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
