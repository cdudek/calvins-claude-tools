"""One evidence file per screen, and "changed since capture" checked per text key.

    python3 scripts/evidence.py record DIR SCREEN --shot FILE --catalog FILE --keys a.b,c.d
    python3 scripts/evidence.py stale DIR --catalog FILE      # exit 1 and one line per stale screen

A capture is proof for the text it showed. `record` writes `DIR/<SCREEN>.json` with the shot's hash
and a hash of each catalogue value the screen displays (a JSON file, nested keys joined with dots).
`stale` names every screen whose keys now differ, so a copy change recaptures only the screens that
show that key, not every screen in a shared ledger. One file per screen also means parallel helpers
never write the same file. Written by `sdlc-run adopt` from the kit; edit the kit, not this copy.
stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

SCREEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def flatten(node: object, prefix: str = "") -> dict[str, str]:
    if isinstance(node, dict):
        out: dict[str, str] = {}
        for k, v in node.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
        return out
    return {prefix: json.dumps(node, sort_keys=True)}


def digest(text: str | bytes) -> str:
    return hashlib.sha256(text if isinstance(text, bytes) else text.encode()).hexdigest()[:16]


def load_catalog(path: str) -> dict[str, str]:
    return {k: digest(v) for k, v in flatten(json.loads(Path(path).read_text("utf-8"))).items()}


def record(args) -> int:
    if not SCREEN.match(args.screen):
        print(
            f"evidence: {args.screen!r} is not a screen name (letters, digits, . _ -)",
            file=sys.stderr,
        )
        return 2
    keys = [k for k in args.keys.split(",") if k]
    catalog = load_catalog(args.catalog) if args.catalog else {}
    missing = [k for k in keys if k not in catalog]
    if missing:
        print(f"evidence: not in the catalogue: {', '.join(missing)}", file=sys.stderr)
        return 2
    shot = Path(args.shot).read_bytes() if args.shot else b""
    out = Path(args.dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.screen}.json").write_text(
        json.dumps(
            {"screen": args.screen, "shot": args.shot, "shotSha": digest(shot),
             "keys": {k: catalog[k] for k in keys}, "at": time.strftime("%Y-%m-%dT%H:%M:%S")},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )  # fmt: skip
    return 0


def stale(args) -> int:
    catalog = load_catalog(args.catalog)
    found = []
    for path in sorted(Path(args.dir).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = [k for k, h in data.get("keys", {}).items() if catalog.get(k) != h]
        if changed:
            found.append(f"{data.get('screen', path.stem)}: {', '.join(changed)}")
    print("\n".join(found))
    return 1 if found else 0


def main(argv: list[str]) -> int:
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    ap = argparse.ArgumentParser(prog="evidence.py")
    sub = ap.add_subparsers(dest="verb", required=True)
    r = sub.add_parser("record")
    r.add_argument("dir")
    r.add_argument("screen")
    r.add_argument("--shot")
    r.add_argument("--catalog")
    r.add_argument("--keys", default="")
    s = sub.add_parser("stale")
    s.add_argument("dir")
    s.add_argument("--catalog", required=True)
    args = ap.parse_args(argv)
    return record(args) if args.verb == "record" else stale(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
