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

Changes approved from 3.25.0 (`"visual": "app"`, a screens.json in the change folder) approve shots of the
real app instead: `gallery CHANGE` writes one offline page (verify/gallery.html) with every latest shot and
an accept / send back choice; the owner downloads answers.json, and `gallery CHANGE --import answers.json
[--by NAME]` copies each accepted shot to screens/<entry>.png and records its sha256 in screens/approved.json
(a send back removes the entry and prints `reopened: <entry>`). `status` then prints
`screens: N of M approved · K changed since approval · L not captured`.

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
import os
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


def status_line(change: str | Path) -> str:
    if (Path(change) / "screens.json").is_file():
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


# --- the app flow (lock "visual": "app"): screens.json, shots of the real app, approved.json ---------

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


def approved_path(change: str | Path) -> Path:
    return screens_dir(change) / "approved.json"


def read_approved(change: str | Path) -> dict:
    try:
        data = json.loads(approved_path(change).read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return data.get("entries", {}) if isinstance(data, dict) and isinstance(data.get("entries"), dict) else {}


def write_approved(change: str | Path, entries: dict) -> None:
    path = approved_path(change)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"format": 1, "entries": entries}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def app_state(change: str | Path, entry: str, approved: dict) -> str:
    """approved | changed | new | not captured, for one entry."""
    shot, ok = sha_of(shot_of(change, entry)), approved.get(entry)
    if ok:
        return "changed" if shot and shot != ok.get("sha256") else "approved"
    return "new" if shot else "not captured"


def app_status_line(change: str | Path) -> str:
    approved = read_approved(change)
    states = [app_state(change, e["id"], approved) for e in app_entries(change)]
    if not states:
        return ""
    return (f"screens: {states.count('approved')} of {len(states)} approved · {states.count('changed')} changed since approval"
            f" · {states.count('not captured')} not captured")


PAGE = """<!doctype html><meta charset="utf-8"><title>Screens to approve</title>
<style>body{font:15px system-ui;margin:2rem auto;max-width:1100px;padding:0 1rem}h2{margin-top:2.5rem}
figure{border:1px solid #ccc;border-radius:8px;padding:1rem;margin:1rem 0}img{max-width:100%;border:1px solid #ddd}
code{background:#eee;padding:0 .3rem}.changed{color:#b00}label{margin-right:1rem}</style>
<h1>Screens to approve</h1><p>Change <code>__CHANGE__</code>. Pick accept or send back per screen, then download your answers.</p>
<p><label>Your name <input id="by"></label> <button onclick="dl()">Download answers</button></p>
__BODY__
<script>function dl(){var a={};document.querySelectorAll('figure[data-id]').forEach(function(f){var c=f.querySelector('input[type=radio]:checked');
if(c)a[f.dataset.id]={answer:c.value,sha256:f.dataset.sha}});var b=new Blob([JSON.stringify({format:1,approvedBy:document.getElementById('by').value,answers:a},null,2)],{type:'application/json'});
var l=document.createElement('a');l.href=URL.createObjectURL(b);l.download='answers.json';l.click()}</script>
"""


def gallery_cmd(args) -> int:
    change = Path(args.change)
    entries = app_entries(change)
    if not entries:
        print(f"evidence: {change}/screens.json has no entries", file=sys.stderr)
        return 1
    return gallery_import(args, change, entries) if args.do_import else gallery_write(change, entries)


def gallery_write(change: Path, entries: list[dict]) -> int:
    approved, body, seen = read_approved(change), [], []
    for e in entries:
        group = e["id"].rpartition(".")[0] or e["id"]
        if group not in seen:
            seen.append(group)
            body.append(f"<h2>{html.escape(group)}</h2>")
        state, shot = app_state(change, e["id"], approved), shot_of(change, e["id"])
        head = f"<b>{html.escape(e['id'])}</b> <code>{html.escape(str(e.get('route', '')))}</code> "
        if shot.is_file():
            data = base64.b64encode(shot.read_bytes()).decode()
            cls = ' class="changed"' if state == "changed" else ""
            body.append(
                f'<figure data-id="{html.escape(e["id"], quote=True)}" data-sha="{sha_of(shot)}">{head}<span{cls}>'
                f'{"changed since approval" if state == "changed" else state}</span><br>'
                f'<img alt="{html.escape(e["id"], quote=True)}" src="data:image/png;base64,{data}"><br>'
                f'<label><input type="radio" name="{html.escape(e["id"], quote=True)}" value="accept"> accept</label>'
                f'<label><input type="radio" name="{html.escape(e["id"], quote=True)}" value="send back"> send back</label></figure>')
        else:
            body.append(f"<figure>{head}<span>not captured</span></figure>")
    out = change / "verify" / "gallery.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(PAGE.replace("__CHANGE__", html.escape(change.name)).replace("__BODY__", "\n".join(body)), encoding="utf-8")
    print(f"wrote {out}")
    return 0


def gallery_import(args, change: Path, entries: list[dict]) -> int:
    try:
        data = json.loads(Path(args.do_import).read_text("utf-8"))
        answers = data["answers"]
        if not isinstance(answers, dict):
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        print(f"evidence: {args.do_import} is not an answers file", file=sys.stderr)
        return 1
    by = data.get("approvedBy") or args.by
    if not by:
        print("evidence: the answers name nobody; fill in the name on the page or pass --by", file=sys.stderr)
        return 1
    known, approved, bad, reopened = {e["id"] for e in entries}, read_approved(change), [], []
    before = dict(approved)
    for entry, a in answers.items():
        answer = ANSWERS.get(str((a or {}).get("answer", "")).lower()) if isinstance(a, dict) else None
        shot = shot_of(change, entry)
        if entry not in known or not answer:
            bad.append(f"{entry}: not an entry of screens.json or not an answer")
        elif answer == "send-back":
            if approved.pop(entry, None):
                (screens_dir(change) / f"{entry}.png").unlink(missing_ok=True)
            reopened.append(entry)
        elif not shot.is_file() or sha_of(shot) != a.get("sha256"):
            bad.append(f"{entry}: the shot changed since the gallery was made; regenerate it")
        else:
            screens_dir(change).mkdir(parents=True, exist_ok=True)
            (screens_dir(change) / f"{entry}.png").write_bytes(shot.read_bytes())
            approved[entry] = {"sha256": sha_of(shot), "file": f"screens/{entry}.png", "approvedBy": by,
                               "date": time.strftime("%Y-%m-%d")}  # fmt: skip
    if approved != before:
        write_approved(change, approved)
    for r in reopened:
        print(f"reopened: {r}")
    print(f"approved {len(approved)} of {len(entries)}")
    for b in bad:
        print(f"evidence: {b}", file=sys.stderr)
    return 1 if bad else 0


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
    g.add_argument("--import", dest="do_import", metavar="ANSWERS_JSON")
    g.add_argument("--by", default="")
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
