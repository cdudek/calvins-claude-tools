"""One evidence file per screen, and "changed since capture" checked per text key.

    python3 scripts/evidence.py record DIR SCREEN --shot FILE --catalog FILE --keys a.b,c.d
    python3 scripts/evidence.py stale DIR --catalog FILE      # exit 1 and one line per stale screen

A capture is proof for the text it showed. `record` writes `DIR/<SCREEN>.json` with the shot's hash
and a hash of each catalogue value the screen displays (a JSON file, nested keys joined with dots).
`stale` names every screen whose keys now differ, so a copy change recaptures only the screens that
show that key, not every screen in a shared ledger. One file per screen also means parallel helpers
never write the same file. Per-screen records (verify/screens/<screen>.json, one writer per file):

    python3 scripts/evidence.py screen CHANGE SCREEN [--status S] [--group G] [--design-system REL]
        [--build SHA] [--reference FILE] [--capture FILE ...]   # one call's captures are one set
    python3 scripts/evidence.py review CHANGE SCREEN --defect SEV:LAYER:TEXT ... | --tick ID [--regression]
    python3 scripts/evidence.py round CHANGE SCREEN             # one fix round used in this release
    python3 scripts/evidence.py status CHANGE                   # the "screens: 62 of 271 done" line
    python3 scripts/evidence.py sheet CHANGE                    # verify/owner-sheet.md for the owner

The first review writes the defect list; it is frozen after that: a later review ticks items or adds
a High or a flagged regression. A new design-system release resets the rounds. Written by `sdlc-run adopt` from the kit; edit the kit, not this copy.
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


STATUSES = ("match", "fixed", "open", "waits-on-design-system", "ruled-out", "accepted-by-owner")
DONE = ("match", "fixed", "ruled-out", "accepted-by-owner")
SEVERITIES = ("High", "Medium", "Low")
MAX_ROUNDS = 2  # fix rounds per screen per design-system release


def screens_dir(change: str | Path) -> Path:
    return Path(change) / "verify" / "screens"


def load_screens(change: str | Path) -> list[dict]:
    return [json.loads(p.read_text("utf-8")) for p in sorted(screens_dir(change).glob("*.json"))]


def screen_file(args) -> Path | None:
    if not SCREEN.match(args.screen):
        print(f"evidence: {args.screen!r} is not a screen name (letters, digits, . _ -)", file=sys.stderr)
        return None
    return screens_dir(args.change) / f"{args.screen}.json"


def load_one(path: Path, screen: str) -> dict:
    if path.exists():
        return json.loads(path.read_text("utf-8"))
    return {"screen": screen, "status": "open", "defects": [], "rounds": 0, "designSystem": ""}


def save_one(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def screen_cmd(args) -> int:
    path = screen_file(args)
    if path is None:
        return 2
    data = load_one(path, args.screen)
    if args.status:
        data["status"] = args.status
    if args.group:
        data["group"] = args.group
    if args.reference:
        data["reference"] = args.reference
    if args.build:
        data["build"] = args.build
    if args.design_system is not None and args.design_system != data["designSystem"]:
        data["designSystem"], data["rounds"] = args.design_system, 0  # a new release: a new budget
    if args.capture:
        base = Path(args.change)
        missing = [f for f in args.capture if not (base / f).is_file()]
        if missing:
            print(f"evidence: no such capture: {', '.join(missing)}", file=sys.stderr)
            return 2
        data["captures"] = [
            {"file": f, "sha256": hashlib.sha256((base / f).read_bytes()).hexdigest()}
            for f in args.capture
        ]
    save_one(path, data)
    return 0


def review_cmd(args) -> int:
    path = screen_file(args)
    if path is None:
        return 2
    data = load_one(path, args.screen)
    defects = data["defects"]
    first = not data.get("reviewed")
    for spec in args.defect:
        sev, _, rest = spec.partition(":")
        layer, _, text = rest.partition(":")
        if sev not in SEVERITIES or not layer or not text:
            print(f"evidence: --defect wants SEVERITY:LAYER:TEXT, got {spec!r}", file=sys.stderr)
            return 2
        if not first and sev != "High" and not args.regression:
            print(f"evidence: the defect list is frozen; only a High or a --regression may be added: {spec!r}", file=sys.stderr)
            return 2
        defects.append({"id": f"D{len(defects) + 1}", "severity": sev, "layer": layer, "text": text,
                        "build": data.get("build", args.build or ""), "open": True,
                        "added": "first" if first else "later",
                        **({"regression": True} if args.regression and not first else {})})  # fmt: skip
    for tick in args.tick:
        hit = [d for d in defects if d["id"] == tick]
        if not hit:
            print(f"evidence: no defect {tick}", file=sys.stderr)
            return 2
        hit[0]["open"] = False
    data["reviewed"] = True
    save_one(path, data)
    return 0


def round_cmd(args) -> int:
    path = screen_file(args)
    if path is None:
        return 2
    data = load_one(path, args.screen)
    data["rounds"] += 1
    save_one(path, data)
    return 0


def screens_problems(change: str | Path) -> list[str]:
    """What marks.py check reports for a change that requires per-screen records."""
    found = []
    for d in load_screens(change):
        name = d.get("screen", "?")
        for x in d.get("defects", []):
            if x.get("added") == "later" and x.get("severity") != "High" and not x.get("regression"):
                found.append(f"{name}: defect {x.get('id')} added after the first review is neither High nor a regression")
        if d.get("rounds", 0) > MAX_ROUNDS:
            found.append(f"{name}: {d['rounds']} fix rounds in one design-system release; send the side-by-side list to the owner")
        caps = d.get("captures", [])
        for c in caps:
            f = Path(change) / c.get("file", "")
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != c.get("sha256"):
                found.append(f"{name}: capture {c.get('file')} does not match its recorded sha256")
        if len({c.get("sha256") for c in caps}) > 1:
            found.append(f"{name}: unstable: its two captures differ")
    return found


def counts(records: list[dict]) -> tuple[int, int, int, int]:
    """done, waiting on the owner, waiting on the design system, open: each screen in one."""
    done = sum(r["status"] in DONE for r in records)
    kit = sum(r["status"] == "waits-on-design-system" for r in records)
    you = sum(r["status"] == "open" and r.get("rounds", 0) >= MAX_ROUNDS for r in records)
    return done, you, kit, len(records) - done - you - kit


def status_line(change: str | Path) -> str:
    records = load_screens(change)
    if not records:
        return ""
    done, you, kit, rest = counts(records)
    return f"screens: {done} of {len(records)} done · {you} wait on you · {kit} wait on the design system · {rest} open"


def sheet_cmd(args) -> int:
    left = [r for r in load_screens(args.change)
            if r["status"] == "open" and r.get("rounds", 0) >= MAX_ROUNDS]  # fmt: skip
    out = ["# Owner sheet", "", "Answer once per group: write `accept` or `send back` in the last column.", ""]
    for group in sorted({r.get("group", "") for r in left}):
        out += [f"## {group or 'ungrouped'}", "",
                "| screen | reference | build capture | open defects | accept / send back |",
                "|---|---|---|---|---|"]  # fmt: skip
        for r in (r for r in left if r.get("group", "") == group):
            cap = (r.get("captures") or [{}])[0].get("file", "")
            todo = "; ".join(f"{d['id']} {d['severity']} {d['text']}" for d in r["defects"] if d["open"])
            out.append(f"| {r['screen']} | {r.get('reference', '')} | {cap} | {todo} |  |")
        out.append("")
    path = Path(args.change) / "verify" / "owner-sheet.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {path} ({len(left)} screens)")
    return 0


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
    for verb in ("screen", "review", "round"):
        p = sub.add_parser(verb)
        p.add_argument("change")
        p.add_argument("screen")
    for verb in ("status", "sheet"):
        sub.add_parser(verb).add_argument("change")
    sc = sub.choices["screen"]
    sc.add_argument("--status", choices=STATUSES)
    sc.add_argument("--group")
    sc.add_argument("--design-system")
    sc.add_argument("--build")
    sc.add_argument("--reference")
    sc.add_argument("--capture", action="append", default=[])
    rv = sub.choices["review"]
    rv.add_argument("--defect", action="append", default=[])
    rv.add_argument("--tick", action="append", default=[])
    rv.add_argument("--regression", action="store_true")
    rv.add_argument("--build")
    args = ap.parse_args(argv)
    if args.verb == "status":
        if line := status_line(args.change):
            print(line)
        return 0
    verbs = {"record": record, "stale": stale, "screen": screen_cmd, "review": review_cmd,
             "round": round_cmd, "sheet": sheet_cmd}  # fmt: skip
    return verbs[args.verb](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
