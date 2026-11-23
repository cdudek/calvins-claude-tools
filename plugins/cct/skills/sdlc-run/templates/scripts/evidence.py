"""One evidence file per screen, and "changed since capture" checked per text key.

    python3 scripts/evidence.py record DIR SCREEN --shot FILE --catalog FILE --keys a.b,c.d
    python3 scripts/evidence.py stale DIR --catalog FILE      # exit 1 and one line per stale screen

A capture is proof for the text it showed. `record` writes `DIR/<SCREEN>.json` with the shot's hash
and a hash of each catalogue value the screen displays (a JSON file, nested keys joined with dots).
`stale` names every screen whose keys now differ, so a copy change recaptures only the screens that
show that key, not every screen in a shared ledger. One file per screen also means parallel helpers
never write the same file. Per-screen records, tracked in git (changes/<id>/screens/<file>.json;
SCREEN is the screen id marks.py derives from the approved inputs, e.g. ref:asks/home.png or
bundle:asks/export/home; the file name is made from it by one shared rule):

    python3 scripts/evidence.py screen CHANGE SCREEN [--status S] [--group G] [--build SHA]
        [--reference FILE] [--capture FILE ... [--state S] [--viewport V] [--zoom Z]]
    python3 scripts/evidence.py review CHANGE SCREEN --defect SEV:LAYER:TEXT ... | --tick ID [--regression]
    python3 scripts/evidence.py round CHANGE SCREEN             # one fix round used in this release
    python3 scripts/evidence.py status CHANGE                   # the "screens: 62 of 271 done" line
    python3 scripts/evidence.py sheet CHANGE [--import]         # changes/<id>/owner-sheet.md; --import records its answers

Changes approved from 3.25.0 (`"visual": "app"`, a screens.json in the change folder) capture the real app;
no owner approves a screen. The gate passes a screen only on the agents' board-to-build
comparison of this run's capture (verify/comparison.json, capture.py); nothing is stored as a baseline. `gallery CHANGE` writes verify/gallery.html, an optional read-only report of every
latest shot beside its design boards; it decides nothing. `status` prints
`screens: N of M compared · K differ · L not compared · P not captured`.

The first review writes the defect list and a snapshot of it; it is frozen after that: a later
review ticks items or adds a High or a flagged regression. A screen is done when it was reviewed
against the approved design-system release (lock.json), has a full build sha and a capture of that
build, and no open High or Medium. The fix-round budget belongs to that release: a new approved
release starts a new budget and needs a fresh review. Each record is written under a lock and
published by an atomic rename, so parallel helpers never lose an update. Written by `sdlc-run adopt`
from the kit; edit the kit, not this copy. stdlib only.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import fcntl
import hashlib
import html
import json
import mimetypes
import os
import re
import subprocess
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
REVIEWED = ("match", "fixed")  # claimed done by the build: needs a review, a build and a capture
SEVERITIES = ("High", "Medium", "Low")
MAX_ROUNDS = 2  # fix rounds per screen per approved design-system release
RECORD_FORMAT = 1  # a record without `format` is a pre-3.23 `record DIR` file: not a screen record
FULL_SHA = re.compile(r"[0-9a-f]{40}")
ANSWERS = {"accept": "accept", "send back": "send-back", "send-back": "send-back"}


def file_name(screen: str) -> str:
    """The one id-to-file-name rule, used by this writer and by marks.py's checker. A plain id is its
    own name; ref:asks/home.png becomes ref--asks--home-png-<hash> (the hash keeps two ids apart)."""
    if SCREEN.match(screen):
        return screen
    slug = re.sub(r"[^A-Za-z0-9-]+", "-", screen.replace(":", "--").replace("/", "--")).strip("-")
    return f"{slug or 'screen'}-{digest(screen)[:6]}"


def screens_dir(change: str | Path) -> Path:
    return Path(change) / "screens"


def record_path(change: str | Path, screen: str) -> Path:
    return screens_dir(change) / f"{file_name(screen)}.json"


def sheet_path(change: str | Path) -> Path:
    return Path(change) / "owner-sheet.md"


def lock(change: str | Path) -> dict | None:
    """lock.json of the change: {} when absent, None when it exists but cannot be read."""
    for path in (Path(change) / "state" / "lock.json", Path(change) / "lock.json"):
        if path.exists():
            try:
                data = json.loads(path.read_text("utf-8"))
            except (OSError, ValueError):
                return None
            return data if isinstance(data, dict) else None
    return {}


def strict(change: str | Path) -> bool:
    """A change approved from 3.23.0 has `"screens": "required"`; an unreadable lock counts as strict."""
    data = lock(change)
    return data is None or data.get("screens") == "required"


def release(change: str | Path) -> str:
    """The design-system release the approval locked: a short hash of the package and the resolved
    and declared version in every consumer. "" when the lock names none."""
    ds = (lock(change) or {}).get("designSystem")
    if not ds:
        return ""
    consumers = sorted((c.get("path"), c.get("pin"), c.get("resolved")) for c in ds.get("consumers") or [] if isinstance(c, dict))
    return digest(json.dumps([ds.get("name"), ds.get("version"), consumers], default=str))[:12]


def expected(change: str | Path) -> list[str]:
    """The approved screen inventory (marks.py's), [] when it cannot be read."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))  # marks.py sits beside this file
    try:
        import marks

        return marks.screen_ids(Path(change))
    except (ImportError, AttributeError, OSError, ValueError):
        return []


def read_record(path: Path) -> dict | None:
    """A screen record, or None for a file that is not one (a pre-3.23 record has no `format`)."""
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("format") == RECORD_FORMAT and "status" in data else None


def load_screens(change: str | Path) -> list[dict]:
    return [r for p in sorted(screens_dir(change).glob("*.json")) if (r := read_record(p))]


def screen_file(args) -> Path | None:
    if not args.screen or "\0" in args.screen or "\n" in args.screen:
        print(f"evidence: {args.screen!r} is not a screen id", file=sys.stderr)
        return None
    return record_path(args.change, args.screen)


def new_record(screen: str) -> dict:
    return {"format": RECORD_FORMAT, "screen": screen, "status": "open", "defects": [], "rounds": 0, "designSystem": ""}


@contextlib.contextmanager
def writing(change: str | Path, path: Path):
    """The whole read-modify-write of one record under an exclusive lock (kept in verify/, which is
    never committed), so two helpers cannot both read the old record and lose one update."""
    locks = Path(change) / "verify" / ".locks"
    locks.mkdir(parents=True, exist_ok=True)
    with open(locks / f"{path.stem}.lock", "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def load_one(path: Path, screen: str) -> dict:
    if path.exists():
        data = read_record(path)
        if data is None:
            raise ValueError(f"{path} is not a screen record")
        return data
    return new_record(screen)


def save_one(path: Path, data: dict) -> None:
    """Publish by atomic rename: a reader sees the old record or the new one, never half of one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sync_release(data: dict, now: str) -> None:
    """The round budget belongs to the approved release: a new one starts a new budget."""
    if data.get("designSystem") != now:
        data["designSystem"], data["rounds"] = now, 0


def rounds_used(data: dict, now: str) -> int:
    return data.get("rounds", 0) if data.get("designSystem") == now else 0


def not_done_why(data: dict, now: str) -> str | None:
    """Why a record that claims done is not: a match or fix needs a first review against the approved
    release, a full build sha, a capture of that build and no open High or Medium; an owner's accept
    needs the owner's recorded answer."""
    status = data["status"]
    if status in REVIEWED:
        if not data.get("reviewed"):
            return "it has no review"
        if data.get("reviewedRelease", "") != now:
            return "it was reviewed against another design-system release; review it again"
        if not FULL_SHA.fullmatch(str(data.get("build", ""))):
            return "it has no full build sha"
        if not any(c.get("build") == data["build"] and c.get("sha256") for c in data.get("captures", [])):
            return "it has no capture of its build"
        if bad := [d["id"] for d in data["defects"] if d.get("open") and d.get("severity") in ("High", "Medium")]:
            return f"it has open High or Medium defects ({', '.join(bad)})"
    if status == "accepted-by-owner" and data.get("ownerDecision") != "accept":
        return "the owner's accept is not recorded (evidence.py sheet --import)"
    return None


def screen_cmd(args) -> int:
    path = screen_file(args)
    if path is None:
        return 2
    now = release(args.change)
    base = Path(args.change)
    with writing(args.change, path):
        data = load_one(path, args.screen)
        sync_release(data, now)
        if args.group:
            data["group"] = args.group
        if args.reference:
            data["reference"] = args.reference
        if args.build:
            data["build"] = args.build
        if args.capture:
            missing = [f for f in args.capture if not (base / f).is_file()]
            if missing:
                print(f"evidence: no such capture: {', '.join(missing)}", file=sys.stderr)
                return 2
            for f in args.capture:
                entry = {"file": f, "sha256": hashlib.sha256((base / f).read_bytes()).hexdigest(),
                         "build": data.get("build", ""), "state": args.state, "viewport": args.viewport,
                         "zoom": args.zoom}  # fmt: skip
                # a recapture of the same file at a newer build replaces the older entry; the same build keeps both
                data["captures"] = [c for c in data.get("captures", []) if not (c["file"] == f and c.get("build") != entry["build"])]
                if entry not in data["captures"]:
                    data["captures"].append(entry)
        if args.status:
            data["status"] = args.status
            why = not_done_why(data, now) if args.status in REVIEWED + ("accepted-by-owner",) else None
            if why:
                print(f"evidence: {args.screen} cannot be {args.status}: {why}", file=sys.stderr)
                return 2
        save_one(path, data)
    return 0


def review_cmd(args) -> int:
    path = screen_file(args)
    if path is None:
        return 2
    now = release(args.change)
    with writing(args.change, path):
        data = load_one(path, args.screen)
        sync_release(data, now)
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
        if first:  # the baseline the checker holds the list to
            data["firstReview"] = [{k: d[k] for k in ("id", "severity", "layer", "text")} for d in defects]
        data["reviewed"], data["reviewedRelease"] = True, now
        save_one(path, data)
    return 0


def round_cmd(args) -> int:
    path = screen_file(args)
    if path is None:
        return 2
    with writing(args.change, path):
        data = load_one(path, args.screen)
        sync_release(data, release(args.change))
        data["rounds"] += 1
        save_one(path, data)
    return 0


def record_problems(data: dict, now: str, change: Path) -> list[str]:
    name = data.get("screen", "?")
    found = []
    first = {d["id"]: d for d in data.get("firstReview", [])}
    by_id = {d.get("id"): d for d in data.get("defects", [])}
    for fid, d in first.items():
        got = by_id.get(fid)
        if not got or any(got.get(k) != d[k] for k in ("severity", "layer", "text")):
            found.append(f"{name}: first-review defect {fid} was removed or changed")
    for x in data.get("defects", []):
        if x.get("added") == "first" and x.get("id") not in first:
            found.append(f"{name}: defect {x.get('id')} says it came from the first review but is not in its snapshot")
        if x.get("added") == "later" and x.get("severity") != "High" and not x.get("regression"):
            found.append(f"{name}: defect {x.get('id')} added after the first review is neither High nor a regression")
    if rounds_used(data, now) > MAX_ROUNDS:
        found.append(f"{name}: {data['rounds']} fix rounds in one design-system release; send the side-by-side list to the owner")
    cells: dict[tuple, set] = {}
    for c in data.get("captures", []):
        f = change / c.get("file", "")
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != c.get("sha256"):
            found.append(f"{name}: capture {c.get('file')} does not match its recorded sha256")
        cells.setdefault(tuple(c.get(k, "") for k in ("build", "state", "viewport", "zoom")), set()).add(c.get("sha256"))
    if any(len(v) > 1 for v in cells.values()):
        found.append(f"{name}: unstable: captures of the same build, state, viewport and zoom differ")
    if data["status"] in REVIEWED + ("accepted-by-owner",) and (why := not_done_why(data, now)):
        found.append(f"{name}: status {data['status']} but {why}")
    return found


def screens_problems(change: str | Path, wanted: list[str] | None = None) -> list[str]:
    """What marks.py check reports for a change that requires per-screen records: every approved
    screen has one, and each record is reviewed, current and consistent."""
    change, now = Path(change), release(change)
    found = []
    for sid in wanted or []:
        if read_record(record_path(change, sid)) is None:
            found.append(f"{sid}: missing screen record; run evidence.py screen {change.name} {sid}")
    for path in sorted(screens_dir(change).glob("*.json")):
        if (data := read_record(path)) is not None:
            found += record_problems(data, now, change)
    return found


def counts(records: list[dict], total: int, now: str) -> tuple[int, int, int, int]:
    """done, waiting on the owner, waiting on the design system, open: each approved screen in one;
    a screen with no record yet is open."""
    done = sum(r["status"] in DONE and not_done_why(r, now) is None for r in records)
    kit = sum(r["status"] == "waits-on-design-system" for r in records)
    you = sum(r["status"] == "open" and rounds_used(r, now) >= MAX_ROUNDS for r in records)
    return done, you, kit, total - done - you - kit


def universe(change: str | Path, records: list[dict]) -> int:
    ids = {r["screen"] for r in records}
    return len(ids | (set(expected(change)) if strict(change) else set()))


def app_locked(change: str | Path) -> bool:
    """The approval lock says `"visual": "app"` (3.25.0): a draft screens.json in an older change changes nothing."""
    for rel in ("state/lock.json", "lock.json"):
        try:
            return json.loads((Path(change) / rel).read_text("utf-8")).get("visual") == "app"
        except (OSError, ValueError, AttributeError):
            continue
    return False


def status_line(change: str | Path) -> str:
    if app_locked(change) and (Path(change) / "screens.json").is_file():
        return app_status_line(change)
    records = load_screens(change)
    total = universe(change, records)
    if not total:
        return ""
    done, you, kit, rest = counts(records, total, release(change))
    return f"screens: {done} of {total} done · {you} wait on you · {kit} wait on the design system · {rest} open"


def read_sheet(path: Path) -> dict[str, str]:
    """screen -> the owner's answer ('accept', 'send-back') for each answered row of an owner sheet."""
    out = {}
    if path.is_file():
        for line in path.read_text("utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else []
            if len(cells) >= 2 and (answer := ANSWERS.get(cells[-1].lower())):
                out[cells[0]] = answer
    return out


def sheet_cmd(args) -> int:
    path, now = sheet_path(args.change), release(args.change)
    answers = read_sheet(path)
    if args.do_import:
        for sid, answer in answers.items():
            rp = record_path(args.change, sid)
            if not rp.is_file():
                print(f"evidence: the sheet answers {sid}, which has no record", file=sys.stderr)
                return 2
            with writing(args.change, rp):
                data = load_one(rp, sid)
                data["ownerDecision"] = answer
                if answer == "accept":
                    data["status"] = "accepted-by-owner"
                else:  # sent back: the screen gets a new budget
                    data["status"], data["rounds"] = "open", 0
                save_one(rp, data)
        print(f"imported {len(answers)} answers from {path}")
        return 0
    left = [r for r in load_screens(args.change) if r["status"] == "open" and rounds_used(r, now) >= MAX_ROUNDS]
    listed = {r["screen"] for r in left}
    lost = [s for s, a in answers.items() if s not in listed and (read_record(record_path(args.change, s)) or {}).get("ownerDecision") != a]
    if lost:
        print(f"evidence: {path} has answers not imported yet ({', '.join(lost)}); run `sheet --import` first", file=sys.stderr)
        return 1
    out = ["# Owner sheet", "", "Answer once per group: write `accept` or `send back` in the last column.", ""]
    for group in sorted({r.get("group", "") for r in left}):
        out += [f"## {group or 'ungrouped'}", "",
                "| screen | reference | build capture | open defects | accept / send back |",
                "|---|---|---|---|---|"]  # fmt: skip
        for r in (r for r in left if r.get("group", "") == group):
            cap = (r.get("captures") or [{}])[-1].get("file", "")
            todo = "; ".join(f"{d['id']} {d['severity']} {d['text']}" for d in r["defects"] if d["open"]).replace("|", "/")
            out.append(f"| {r['screen']} | {r.get('reference', '')} | {cap} | {todo} | {'' if answers.get(r['screen']) == r.get('ownerDecision') else answers.get(r['screen'], '').replace('-', ' ')} |")
        out.append("")
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text("\n".join(out), encoding="utf-8")
    os.replace(tmp, path)
    print(f"wrote {path} ({len(left)} screens)")
    return 0


# --- the app flow (lock "visual": "app"): screens.json, shots of the real app, verify/comparison.json ---------

def app_entries(change: str | Path) -> list[dict]:
    """The entries of screens.json (a list, or {"entries": [...]}); [] when absent or unreadable."""
    try:
        data = json.loads((Path(change) / "screens.json").read_text("utf-8"))
    except (OSError, ValueError):
        return []
    rows = data.get("entries") if isinstance(data, dict) else data
    return [r for r in rows or [] if isinstance(r, dict) and isinstance(r.get("id"), str)]


def shot_of(change: str | Path, entry: str) -> Path:
    return Path(change) / "verify" / "shots" / f"{entry}.png"


def read_verdicts(change: str | Path) -> dict:
    try:
        data = json.loads((Path(change) / "verify" / "comparison.json").read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return data.get("entries", {}) if isinstance(data, dict) and isinstance(data.get("entries"), dict) else {}


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def app_state(change: str | Path, entry: str, verdicts: dict, digest: str | None = None) -> str:
    """compared | differs | not compared | not captured, for one entry: the agents' verdict in verify/comparison.json
    counts only when it carries the sha256 of the shot as it is now. Nothing is stored as a baseline."""
    shot, v = sha_of(shot_of(change, entry)) if digest is None else digest, verdicts.get(entry)
    if not shot:
        return "not captured"
    if not isinstance(v, dict) or v.get("sha256") != shot:
        return "not compared"
    return "compared" if v.get("verdict") == "match" else "differs"


def app_status_line(change: str | Path) -> str:
    verdicts = read_verdicts(change)
    import capture

    if missing := shim_old_capture(capture):
        return f"screens: unavailable, {stale_capture(missing)}"
    states = [app_state(change, e["id"], verdicts) for e in app_entries(change)]
    if not states:
        return ""
    line = (f"screens: {states.count('compared')} of {len(states)} compared · {states.count('differs')} differ"
            f" · {states.count('not compared')} not compared · {states.count('not captured')} not captured")
    counts = capture.design_counts(Path(change), app_entries(change))
    return line + (f"\ndesign: {counts[0]} boards · {counts[1]} mapped · {counts[2]} dropped · {counts[3]} deviations" if counts else "")


PAGE = """<!doctype html><meta charset="utf-8"><title>Screens (read-only report)</title>
<style>body{font:15px system-ui;margin:2rem auto;max-width:1100px;padding:0 1rem}h2{margin-top:2.5rem}
figure{border:1px solid #ccc;border-radius:8px;padding:1rem;margin:1rem 0}img{max-width:100%;border:1px solid #ddd}
code{background:#eee;padding:0 .3rem}.changed{color:#b00}
.pair{display:flex;gap:1rem;align-items:flex-start}.pair>div{flex:1;min-width:0}.dev{background:#fff3cd;border:1px solid #d6a300;padding:.5rem;margin:.5rem 0}
.board{border:1px dashed #999;padding:.5rem}</style>
<h1>Screens</h1><p>Change <code>__CHANGE__</code>. A read-only report: it decides nothing. The gate passes a screen only on a board-to-build comparison of its own capture.</p>
<p>__COUNTS__</p>
__BODY__
"""


def resolve_change(arg: str) -> Path:
    """The change folder: the path given, else a bare id under sdlc.json `changesDir` (default changes)."""
    if Path(arg).is_dir():
        return Path(arg)
    try:
        folder = json.loads(Path("sdlc.json").read_text("utf-8")).get("changesDir") or "changes"
    except (OSError, ValueError, AttributeError):
        folder = "changes"
    return Path(folder) / arg if (Path(folder) / arg).is_dir() else Path(arg)


def inside(change: Path, path: Path) -> bool:
    return path.resolve().is_relative_to(change.resolve())


CHECKS = ("image_problems", "board_file", "read_board", "design_problems", "read_comparison")


def shim_old_capture(capture) -> list[str]:
    """Stands in for the presentation helpers a kept older scripts/capture.py (3.25) lacks and returns the CHECKS it
    lacks: a check is never stubbed, because a stub that says "fine" is the approval an agent could not give itself."""
    none = {"load_design": lambda change: {}, "boards_of": lambda design: [], "dropped_of": lambda design: [], "mapped": lambda entry: [],
            "design_counts": lambda change, entries: None}  # fmt: skip
    for name, fn in none.items():
        if not hasattr(capture, name):
            setattr(capture, name, fn)
    return [n for n in CHECKS if not hasattr(capture, n)]


def stale_capture(missing: list[str]) -> str:
    return f"scripts/capture.py is older than this script and lacks `{missing[0]}`: run `adopt --migrate`"


def gallery_cmd(args) -> int:
    sys.dont_write_bytecode = True  # a checkout stays clean: no __pycache__ from importing the kit's scripts
    import capture  # the one id rule; both scripts sit in the same folder

    if missing := shim_old_capture(capture):
        print(f"evidence: {stale_capture(missing)}", file=sys.stderr)
        return 1
    change = resolve_change(args.change)
    if bad := capture.image_problems(change):
        print("\n".join(f"evidence: {p}" for p in bad), file=sys.stderr)
        return 1
    entries, problems = capture.load_screens(change)
    if problems:
        print("\n".join(f"evidence: {p}" for p in problems), file=sys.stderr)
        return 1
    return gallery_write(change, entries)


def boards_html(change: Path, design: dict, entry: dict) -> str:
    """The design boards an entry maps, as one column: the board image embedded, else its name and the source link."""
    import capture

    known, out = {b["id"]: b for b in capture.boards_of(design)}, []
    for bid in capture.mapped(entry):
        board = known.get(bid, {"id": bid, "name": bid})
        raw = capture.read_board(change, board.get("image"))  # one handle: the bytes embedded are the bytes of a plain file inside the change
        mime = mimetypes.guess_type(str(board.get("image")))[0] if raw is not None else None
        if raw is not None and mime:
            data = base64.b64encode(raw).decode()
            out.append(f'<img alt="design {html.escape(bid, quote=True)}" src="data:{mime};base64,{data}">')
        else:
            src = str(design.get("source", ""))
            link = f'<a href="{html.escape(src, quote=True)}">source</a>' if src.startswith(("http://", "https://")) else html.escape(src)
            out.append(f'<div class="board"><b>{html.escape(str(board.get("name", bid)))}</b> ({html.escape(bid)}), no image: {link}</div>')
    return f"<div><small>design</small><br>{''.join(out)}</div>" if out else ""


def gallery_write(change: Path, entries: list[dict]) -> int:
    import capture

    approved, body, seen, design = read_verdicts(change), [], [], capture.load_design(change)
    for e in entries:
        group = e["id"].rpartition(".")[0] or e["id"]
        if group not in seen:
            seen.append(group)
            body.append(f"<h2>{html.escape(group)}</h2>")
        shot = shot_of(change, e["id"])
        raw = shot.read_bytes() if shot.is_file() and inside(change, shot) else None  # read once: shown, hashed and approved alike
        digest = hashlib.sha256(raw).hexdigest() if raw is not None else ""
        state = app_state(change, e["id"], approved, digest)
        head = f"<b>{html.escape(e['id'])}</b> <code>{html.escape(str(e.get('route', '')))}</code> "
        deviates = str(e.get("deviates") or "").strip()
        note = f'<p class="dev"><b>Deviates from the design:</b> {html.escape(deviates)}</p>' if deviates else ""
        if raw is not None:
            data = base64.b64encode(raw).decode()
            cls = ' class="changed"' if state in ("differs", "not compared") else ""
            name = html.escape(e["id"], quote=True)
            body.append(
                f'<figure data-id="{name}" data-sha="{digest}">{head}<span{cls}>'
                f'{state}</span><br>{note}'
                f'<div class="pair">{boards_html(change, design, e)}<div><small>app</small><br>'
                f'<img alt="{name}" src="data:image/png;base64,{data}"></div></div></figure>')
        else:
            body.append(f"<figure>{head}<span>not captured</span>{note}</figure>")
    counts = capture.design_counts(change, entries)
    summary = "<b>design:</b> {} boards · {} mapped · {} dropped · {} deviations".format(*counts) if counts else ""
    out = change / "verify" / "gallery.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(PAGE.replace("__CHANGE__", html.escape(change.name)).replace("__COUNTS__", summary).replace("__BODY__", "\n".join(body)), encoding="utf-8")
    print(f"wrote {out}")
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
    sub.choices["sheet"].add_argument("--import", dest="do_import", action="store_true")
    g = sub.add_parser("gallery")
    g.add_argument("change")
    sc = sub.choices["screen"]
    sc.add_argument("--status", choices=STATUSES)
    sc.add_argument("--group")
    sc.add_argument("--build")
    sc.add_argument("--reference")
    sc.add_argument("--capture", action="append", default=[])
    for cell in ("state", "viewport", "zoom"):
        sc.add_argument(f"--{cell}", default="")
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
             "round": round_cmd, "sheet": sheet_cmd, "gallery": gallery_cmd}  # fmt: skip
    return verbs[args.verb](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
