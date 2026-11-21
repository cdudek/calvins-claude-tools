"""The app capture of a change approved from 3.25.0 (lock `"visual": "app"`): one app start, every
`screens.json` entry at its viewport, twice, compared with the approved baseline.

    python3 scripts/capture.py check <change-dir>     # validate screens.json only (what `approve` runs)
    python3 scripts/capture.py run <change-dir> [--upto N] [--group]
        # reachability, capture x2, stability, baseline compare. --upto N: only entries due by milestone N.
        # --group: the caller (the gate) leads this process group, so the app starts inside it and dies with it.

`screens.json` (in the change folder): a list, or {"entries": [...]}, of
    {"id": "leads.list.empty", "route": "/preview/leads?state=empty", "viewport": [1440, 900], "fixture": "empty-leads"}
Ids are plain names (letters, digits, `.` `_` `-`), unique even when case is ignored; a route starts with `/`; a viewport
is two positive ints; no two entries share a route and viewport (the fixture shows only through the route). An entry may
carry "milestone": N (default 1): a milestone close captures the entries with milestone <= N, the last one requires all.

sdlc.json `visual` (all optional except `start` for `run`):
    start         shell command that starts the app on $PORT (a build step may precede it: `npm run build && npm start`)
    ready         path polled until the app answers (default "/")
    startTimeout  seconds to wait for it (default 120)
    threshold     fraction of differing pixels still accepted, a number from 0 to 1 (default 0: bytes must be equal)
    driver        a capture command of your own: `<driver> <jobs.json>` writes the png of every job (see below);
                  default is the repo's Playwright (`@playwright/test` or `playwright` in package.json)

Driver contract: jobs.json is {"base": "http://127.0.0.1:PORT", "jobs": [{"id", "route", "viewport", "out"}]};
the driver writes a png to every `out` and exits 0. It must not follow a redirect off the app: before each shot it
checks that the response is 2xx and that the final URL is on the origin of `base`, and fails (non-zero) otherwise.
(The reachability probe does not follow redirects either: a 3xx is "not reachable".) The shot folders are emptied
before the driver runs, and every expected file must be newer than the start of the batch.

Shots go to <change>/verify/shots/<id>.png (the second pass to verify/shots/second/<id>.png; a differing pair is
unstable). The baseline is <change>/screens/approved.json: {"format": 1, "entries": {"<id>": {"sha256", ...}}}
with the png at <change>/screens/<id>.png, which must hash to that sha256 before any pixel is compared. A difference
writes verify/shots/diff/<id>.png and needs a new approval.

Last line: `CAPTURE PASS <n>` (exit 0), `CAPTURE FAIL ...` (exit 1) or `VERIFY BLOCKED reason=<code>` (exit 3:
needs-baseline when an entry has no approved shot, env when the app or Playwright is missing).
Written by `sdlc-run adopt` from the kit; edit the kit, not this copy. stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shlex
import shutil
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
import zlib
from pathlib import Path

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
PLAYWRIGHT_JS = r"""
const path = require('path'), fs = require('fs');
const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const find = (n) => { try { return require(require.resolve(n, {paths: [process.cwd()]})); } catch (e) { return null; } };
const pw = find('@playwright/test') || find('playwright');
if (!pw) { console.error('playwright is not installed'); process.exit(2); }
(async () => {
  const browser = await pw.chromium.launch();
  for (const j of job.jobs) {
    const page = await browser.newPage({ viewport: { width: j.viewport[0], height: j.viewport[1] } });
    const res = await page.goto(job.base + j.route, { waitUntil: 'networkidle' });
    if (!res || res.status() < 200 || res.status() >= 300 || new URL(page.url()).origin !== new URL(job.base).origin) {
      throw new Error(j.id + ': ' + page.url() + ' answered ' + (res ? res.status() : 'nothing') + ', not a 2xx page of the launched app');
    }
    await page.screenshot({ path: j.out, animations: 'disabled', caret: 'hide' });
    await page.close();
  }
  await browser.close();
})().catch((e) => { console.error(String(e)); process.exit(1); });
"""


def load_screens(change: Path) -> tuple[list[dict], list[str]]:
    """The entries of screens.json and the problems with them."""
    path = Path(change) / "screens.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return [], [f"{path.name} is missing: the UX plan writes one entry per screen and state"]
    except ValueError as err:
        return [], [f"{path.name} is not JSON: {err}"]
    entries = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(entries, list) or not entries:
        return [], [f"{path.name} must be a non-empty list of entries (or {{\"entries\": [...]}})"]
    problems, seen, spots = [], set(), {}
    for i, e in enumerate(entries, 1):
        name = e.get("id") if isinstance(e, dict) else None
        tag = f"{path.name} entry {i}" + (f" ({name})" if isinstance(name, str) else "")
        if not isinstance(e, dict):
            problems.append(f"{tag}: not an object")
            continue
        if not isinstance(name, str) or not ID.match(name):
            problems.append(f"{tag}: id must be a plain name (letters, digits, . _ -)")
        elif name in seen:
            problems.append(f"{tag}: id is used twice")
        elif name.lower() in {s.lower() for s in seen}:
            problems.append(f"{tag}: id has the same name as another entry once case is ignored (they would share one file)")
        if isinstance(name, str):
            seen.add(name)
        route = e.get("route")
        if not isinstance(route, str) or not route.startswith("/") or "//" in route[:2] or re.search(r"\s", route):
            problems.append(f"{tag}: route must start with a single / and hold no space")
        vp = e.get("viewport")
        if not (isinstance(vp, list) and len(vp) == 2 and all(isinstance(n, int) and not isinstance(n, bool) and 0 < n <= 10000 for n in vp)):
            problems.append(f"{tag}: viewport must be [width, height], two positive integers")
        if not isinstance(e.get("fixture"), str) or not e["fixture"].strip():
            problems.append(f"{tag}: fixture must name the sample data the app seeds")
        ms = e.get("milestone", 1)
        if not isinstance(ms, int) or isinstance(ms, bool) or ms < 1:
            problems.append(f"{tag}: milestone must be a positive integer")
        boards = e.get("design", [])
        if not isinstance(boards, list) or not all(isinstance(b, str) and ID.match(b) for b in boards):
            problems.append(f"{tag}: design must be a list of board ids from design.json")
        if "deviates" in e and not (isinstance(e["deviates"], str) and e["deviates"].strip()):
            problems.append(f"{tag}: deviates must say what differs from the board and why")
        if isinstance(route, str) and isinstance(vp, list):
            first = spots.setdefault((route, tuple(map(str, vp))), name)
            if first != name:
                problems.append(f"{tag}: same route and viewport as {first}: the fixture shows only through the route, so give each state its own")
    return [e for e in entries if isinstance(e, dict)], problems


# --- 3.26.0: the design is binding for what exists (design.json maps the boards of the design source to screens.json) ---

def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_design(change: Path) -> dict:
    """design.json: {"source", "boards": [{"id", "name", "image"?}], "dropped": [{"board", "reason"}]}; {} when absent or unreadable."""
    data = read_json(Path(change) / "design.json")
    return data if isinstance(data, dict) else {}


def boards_of(design: dict) -> list[dict]:
    return [b for b in design.get("boards") or [] if isinstance(b, dict) and isinstance(b.get("id"), str)]


def mapped(entry: dict) -> list[str]:
    """The board ids an entry's `design` list names."""
    return [b for b in entry.get("design") or [] if isinstance(b, str)] if isinstance(entry.get("design"), list) else []


def dropped_of(design: dict) -> list[dict]:
    return [d for d in design.get("dropped") or [] if isinstance(d, dict)]


def canon(value: object) -> str:
    """The one text every approval hash is made of: sorted canonical JSON, so record boundaries bind."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def inventory_id(design: dict) -> str:
    """The id of the owner's confirmation of the inventory: `inventory-` and 16 hex of the canonical board list (ids,
    names, count) and dropped list. The dialog is `Change <id>, finding <this id>: these N boards are the whole design`,
    so the answer covers exactly this list and no other."""
    boards = sorted([b["id"], str(b.get("name", ""))] for b in boards_of(design))
    dropped = sorted([str(d.get("board")), str(d.get("reason"))] for d in dropped_of(design))
    return "inventory-" + hashlib.sha256(canon({"boards": boards, "count": len(boards), "dropped": dropped}).encode()).hexdigest()[:16]


def board_file(change: Path, image: object) -> Path | None:
    """The board image as a file of the change, or None: a relative path that stays inside the change folder, passes no
    symlink and is a file. An absolute path, a `..` that leaves, a symlink or a symlinked folder is no board image."""
    if not isinstance(image, str) or not image or Path(image).is_absolute():
        return None
    if os.path.normpath(image) != image or {".", ".."} & set(image.split("/")):  # 3.26.4: no `.`/`..` part, so the folder walk never follows one
        return None
    base = Path(change).resolve()
    path = base / image
    real = path.resolve()
    return real if real.is_relative_to(base) and os.path.normpath(path) == str(real) and real.is_file() else None


def read_board(change: Path, image: object) -> bytes | None:
    """The bytes of a board image, read once from one handle. `board_file` has the path checked; the file is then opened
    folder by folder from the change with O_NOFOLLOW, so a path swapped for a symlink after the check is refused, and
    what is read is the regular file that handle names. None when it is no board image or cannot be opened so."""
    if board_file(change, image) is None:
        return None
    *folders, leaf = Path(str(image)).parts
    if {".", ".."} & {*folders, leaf}:
        return None
    fd = -1
    try:
        fd = os.open(Path(change).resolve(), os.O_RDONLY | os.O_DIRECTORY)
        for name in folders:
            nxt = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        nxt = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)  # a fifo swapped in must not block the read
        os.close(fd)
        fd = nxt
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            return handle.read()
    except OSError:
        return None
    finally:
        if fd >= 0:
            os.close(fd)


def board_digest(change: Path, design: dict, board_id: str) -> str:
    """sha256 of a board's image file, "" when it has none (or the file is missing or leaves the change: design_problems says so)."""
    board = next((b for b in boards_of(design) if b["id"] == board_id), {})
    data = read_board(change, board.get("image"))
    return hashlib.sha256(data).hexdigest() if data is not None else ""


def image_digests(change: Path) -> dict[str, str]:
    """{board id: sha256} of every board image: what approval records in the lock."""
    design = load_design(change)
    return {b["id"]: board_digest(change, design, b["id"]) for b in boards_of(design) if isinstance(b.get("image"), str)}


def image_problems(change: Path) -> list[str]:
    """A board image that changed (or went missing) since approval, by board. Nothing when the lock recorded none."""
    locked = {}
    for rel in ("state/lock.json", "lock.json"):
        data = read_json(Path(change) / rel)
        if isinstance(data, dict):
            locked = data.get("designImages") if isinstance(data.get("designImages"), dict) else {}
            break
    now = image_digests(change)
    return [f"board {b}: its image changed or is missing since approval (approval locked it)" for b, d in locked.items() if now.get(b) != d]


def binding_tag(change: Path, design: dict, entry: dict) -> str:
    """What the owner's answer for a screen is bound to beyond its pixels: the boards it maps (with their image digests)
    and its deviation text. "" for a screen with neither, so a change with no design input hashes as before."""
    boards = mapped(entry)
    text = str(entry.get("deviates") or "").strip()
    if not boards and not text:
        return ""
    return "bind-" + hashlib.sha256(canon({"boards": [[b, board_digest(change, design, b)] for b in boards], "deviates": text}).encode()).hexdigest()[:8]


def deviation_tag(text: str) -> str:
    """What an approval pair carries for an entry with a `deviates` text: the owner accepted exactly this text."""
    return "dev-" + hashlib.sha256(text.strip().encode()).hexdigest()[:8]


def design_problems(change: Path, entries: list[dict], required: bool = False) -> list[str]:
    """Every board of design.json is mapped by an entry's `design` list or dropped with a reason, and every entry
    names only boards design.json lists. `required`: the change has a design input, so design.json must exist."""
    change = Path(change)
    if not (change / "design.json").is_file():
        if required:
            return ["design.json is missing: the change has a design input, so the UX plan lists every board of it"]
        return [f"screens.json entry {e.get('id')} names board {b}, but the change has no design.json" for e in entries for b in mapped(e)]
    design = load_design(change)
    boards = design.get("boards")
    if not (isinstance(design.get("source"), str) and design["source"].strip() and isinstance(boards, list) and boards):
        return ['design.json must be {"source": "<link or path>", "boards": [{"id", "name", "image"?}, ...]} with at least one board']
    problems, ids = [], []
    for b in boards:
        name = b.get("id") if isinstance(b, dict) else None
        if not (isinstance(name, str) and ID.match(name)) or not isinstance(b.get("name"), str) or not b["name"].strip():
            problems.append(f"design.json board {name or b!r}: needs a plain id and a name")
        elif name in ids:
            problems.append(f"design.json board {name}: id is used twice")
        else:
            ids.append(name)
        image = b.get("image") if isinstance(b, dict) else None
        if image is not None and board_file(change, image) is None:
            problems.append(f"design.json board {name}: image {image!r} is not a file of the change")
    dropped = design.get("dropped", [])
    ok = isinstance(dropped, list) and all(isinstance(d, dict) and d.get("board") in ids and isinstance(d.get("reason"), str) and d["reason"].strip() for d in dropped)
    if not ok:
        problems.append('design.json dropped must be [{"board": <a board id>, "reason": "..."}, ...]')
        dropped = []
    used = {b for e in entries for b in mapped(e)}
    for e in entries:
        problems += [f"screens.json entry {e.get('id')} maps board {b}, which design.json does not list" for b in mapped(e) if b not in ids]
    gone = {d["board"] for d in dropped}
    problems += [f"board {b} is mapped by no screens.json entry and is not dropped: map it (\"design\": [\"{b}\"]) or drop it with a reason" for b in ids if b not in used and b not in gone]
    problems += [f"board {b} is both mapped and dropped: choose one" for b in ids if b in used and b in gone]
    return problems


def design_counts(change: Path, entries: list[dict]) -> tuple[int, int, int, int] | None:
    """(boards, mapped, dropped, deviations) of a change that has design.json, else None."""
    design = load_design(change)
    boards = [b["id"] for b in boards_of(design)]
    if not boards:
        return None
    used = {b for e in entries for b in mapped(e)}
    return len(boards), len([b for b in boards if b in used]), len(dropped_of(design)), len([e for e in entries if str(e.get("deviates", "")).strip()])


def lock_sha(change: Path) -> str:
    for rel in ("state/lock.json", "lock.json"):
        data = read_json(Path(change) / rel)
        if isinstance(data, dict):
            return str(data.get("sha", ""))
    return ""


def link(log: list, record: dict, lock: str) -> dict:
    """`record` chained to the log: the hash of the entry before it and the lock it was decided under go into its own hash."""
    prev = log[-1].get("hash", "") if log else ""
    body = {k: v for k, v in record.items() if k not in ("hash", "prev", "lock")}
    body.update({"prev": prev, "lock": lock})
    body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return body


def chain_problems(log: list, head: object = None, strict: bool = False) -> list[str]:
    """A log written before 3.26.0 has no hashes and is read as it is; once an entry is hashed, every later one is,
    each names the hash of the one before it, and the file's `head` is the last. A trimmed or rewritten log fails.
    `strict` (a 3.26+ lock): every entry is hashed, none is missing from the chain, and `head` is the last entry's
    hash even when no entry is hashed."""
    out, prev, hashed = [], "", False
    for i, rec in enumerate(log):
        if "hash" not in rec:
            if hashed or strict:
                out.append(f"log entry {i + 1} has no hash" + (" after a hashed one" if hashed else ""))
            continue
        body = {k: v for k, v in rec.items() if k != "hash"}
        want = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        if rec.get("prev") != prev or rec["hash"] != want:
            out.append(f"log entry {i + 1} ({rec.get('entry')}) does not follow the one before it: the log was changed")
        prev, hashed = rec["hash"], True
    last = log[-1].get("hash", "") if log else ""
    if (hashed or strict) and (head or "") != (prev if hashed else last):
        out.append("the log does not end where approved.json says it does: entries were removed")
    return out


def replayed(log: list, entry: str, bid: str) -> bool:
    """`bid` already approved `entry`, and a send back of the entry came after it: that batch is spent."""
    at = [i for i, r in enumerate(log) if r.get("entry") == entry and r.get("answer") == "accept" and r.get("batch") == bid]
    return bool(at) and any(r.get("entry") == entry and r.get("answer") == "send-back" for r in log[at[0] + 1 :])


def read_config(repo: Path) -> dict:
    try:
        cfg = json.loads((repo / "sdlc.json").read_text(encoding="utf-8")).get("visual")
    except (OSError, ValueError, AttributeError):
        return {}
    return cfg if isinstance(cfg, dict) else {}


def has_playwright(repo: Path) -> bool:
    try:
        pkg = json.loads((repo / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    return "@playwright/test" in deps or "playwright" in deps


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # a 3xx stays a 3xx: it is never "reachable"
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def fetch(url: str) -> int:
    try:
        with OPENER.open(url, timeout=10) as r:  # our own local app
            return r.status
    except urllib.error.HTTPError as err:
        return err.code
    except (OSError, ValueError):
        return 0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def pixels(path: Path) -> tuple[int, int, int, bytes]:
    """(width, height, bytes per pixel, raw rows) of an 8-bit non-interlaced png: what Playwright writes."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path.name} is not a png")
    pos, idat, head = 8, b"", None
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos : pos + 8])
        body = data[pos + 8 : pos + 8 + n]
        pos += 12 + n
        if kind == b"IHDR":
            head = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
    w, h, depth, color, _, _, interlace = head
    bpp = {2: 3, 6: 4, 0: 1}.get(color)
    if depth != 8 or interlace or not bpp:
        raise ValueError(f"{path.name}: only 8-bit non-interlaced png can be compared by pixels")
    raw, stride, rows, prev = zlib.decompress(idat), w * bpp, [], bytearray(w * bpp)
    for y in range(h):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line))
        prev = line
    return w, h, bpp, b"".join(rows)


def write_png(path: Path, w: int, h: int, rgb: bytes) -> None:
    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    raw = b"".join(b"\0" + rgb[y * w * 3 : (y + 1) * w * 3] for y in range(h))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def compare(a: Path, b: Path, diff: Path) -> float:
    """Fraction of differing pixels (1.0 for another size); writes `diff` (red = changed) when any differ."""
    wa, ha, ba, da = pixels(a)
    wb, hb, bb, db = pixels(b)
    if (wa, ha, ba) != (wb, hb, bb):
        return 1.0
    out, bad = bytearray(), 0
    for i in range(0, len(da), ba):
        same = da[i : i + ba] == db[i : i + ba]
        bad += not same
        out += b"\x80\x80\x80" if same else b"\xff\x00\x00"
    if bad:
        write_png(diff, wa, ha, bytes(out))
    return bad / (wa * ha)


def group_others() -> list[int]:
    """The other members of this process group, minus this process and its ancestors: the gate runs a check
    as `sh -c`, and a shell that does not exec (dash) leads the group, so signalling the whole group kills it."""
    out = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,pgid="], capture_output=True, text=True).stdout
    rows = {int(f[0]): (int(f[1]), int(f[2])) for f in (line.split() for line in out.splitlines()) if len(f) == 3}
    mine, pid = set(), os.getpid()
    while pid in rows and pid not in mine:
        mine.add(pid)
        pid = rows[pid][0]
    return [p for p, (_, g) in rows.items() if g == os.getpgrp() and p not in mine]


def stop(proc: subprocess.Popen, group: bool = False) -> None:
    """Stop the app. With `group` it shares this process's group (so the gate's group kill reaps it): signal the
    group's other members, never this process or the shell above it; otherwise it has a group of its own."""

    def signal_app(sig: int) -> None:
        if not group:
            os.killpg(proc.pid, sig)
            return
        for pid in group_others():
            try:
                os.kill(pid, sig)
            except OSError:  # already gone, such as the ps that listed it
                pass

    try:
        signal_app(signal.SIGTERM)
        proc.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        try:
            signal_app(signal.SIGKILL)
        except OSError:
            pass


def valid_threshold(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def drive(repo: Path, cfg: dict, jobs_file: Path) -> tuple[int, str]:
    if cfg.get("driver"):
        cmd = [*shlex.split(str(cfg["driver"])), str(jobs_file)]
    elif has_playwright(repo):
        js = jobs_file.with_suffix(".mjs.cjs")
        js.write_text(PLAYWRIGHT_JS, encoding="utf-8")
        cmd = ["node", str(js), str(jobs_file)]
    else:
        return 3, (
            "this repo has no Playwright: add it (`npm i -D @playwright/test && npx playwright install chromium`, or the "
            "pnpm/yarn/bun equivalent), or set sdlc.json visual.driver to a capture command of your own"
        )
    res = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    return res.returncode, (res.stdout + res.stderr)[-2000:]


def run(change: Path, repo: Path, upto: int | None = None, group: bool = False) -> int:
    entries, problems = load_screens(change)
    if problems:
        print("\n".join(problems))
        return end("CAPTURE FAIL screens.json", 1)
    entries = [e for e in entries if upto is None or e.get("milestone", 1) <= upto]  # a milestone close: the entries due so far
    cfg = read_config(repo)
    if not cfg.get("start"):
        print('sdlc.json has no visual.start: the command that starts the app on $PORT (for example "npm run build && npm start").')
        return end("VERIFY BLOCKED reason=env", 3)
    threshold = cfg.get("threshold", 0)
    if not valid_threshold(threshold):
        print(f"sdlc.json visual.threshold must be a number from 0 to 1 (the share of pixels that may differ), not {threshold!r}.")
        return end("VERIFY BLOCKED reason=env", 3)
    port = int(os.environ.get("SDLC_APP_PORT") or free_port())
    if port_in_use(port):
        print(f"port {port} already answers: an old server could pass for this build. Stop it or set another SDLC_APP_PORT.")
        return end("VERIFY BLOCKED reason=env", 3)
    base = f"http://127.0.0.1:{port}"
    shots = change / "verify" / "shots"
    for folder in (shots / "second", shots / "diff"):
        shutil.rmtree(folder, ignore_errors=True)
    for old in shots.glob("*.png"):  # nothing left from an earlier batch can pass for this one
        old.unlink()
    shots.mkdir(parents=True, exist_ok=True)
    (shots / "second").mkdir(exist_ok=True)
    started = time.time()
    log = tempfile.NamedTemporaryFile("w+", prefix="capture-app-", suffix=".log", delete=False)
    app = subprocess.Popen(
        str(cfg["start"]), shell=True, cwd=repo, env={**os.environ, "PORT": str(port)},
        stdout=log, stderr=subprocess.STDOUT, start_new_session=not group,
    )  # fmt: skip

    def cancelled(signum, _frame) -> None:  # a caught signal also stops the app; SIGKILL is covered by the shared group
        stop(app, group)
        sys.exit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, cancelled)
    try:
        deadline = time.monotonic() + float(cfg.get("startTimeout", 120))
        ready = base + str(cfg.get("ready", "/"))
        while not fetch(ready):
            if app.poll() is not None or time.monotonic() > deadline:
                log.seek(0)
                print(f"the app did not answer at {ready}:\n" + "\n".join(log.read().splitlines()[-30:]))
                return end("VERIFY BLOCKED reason=env", 3)
            time.sleep(0.5)
        missing = []
        for e in entries:
            code = fetch(base + e["route"])
            if not 200 <= code < 300:
                why = f"answers {code or 'nothing'}" + (" (a redirect: a preview page answers 200 itself)" if 300 <= code < 400 else "")
                missing.append(f"{e['id']}: {e['route']} {why}")
        if missing:
            print("no reachable preview page for these entries (the build gives every one a route):\n" + "\n".join(missing))
            return end("CAPTURE FAIL preview-unreachable", 1)
        jobs = [
            {"id": e["id"], "route": e["route"], "viewport": e["viewport"], "out": str(shots / sub / f"{e['id']}.png")}
            for sub in ("", "second")
            for e in entries
        ]
        jobs_file = shots / "jobs.json"
        jobs_file.write_text(json.dumps({"base": base, "jobs": jobs}), encoding="utf-8")
        code, out = drive(repo, cfg, jobs_file)
        if code:
            print(out)
            return end("VERIFY BLOCKED reason=env" if code == 3 else "CAPTURE FAIL capture", 3 if code == 3 else 1)
    finally:
        stop(app, group)
        log.close()
        Path(log.name).unlink(missing_ok=True)
    return judge(change, entries, shots, float(threshold), started, repo)


def approval_id(pairs: list) -> str:
    """The id of one owner approval: `screens-` and 16 hex of the sorted canonical pairs `[entry, sha256]` (a send back or a
    screen's board and deviation binding adds a third word). The owner's dialog is `Change <id>, finding <this id>: ...`,
    so the answer covers exactly these shots and no others."""
    return "screens-" + hashlib.sha256(canon(sorted(pairs)).encode()).hexdigest()[:16]


def legacy_approval_id(pairs: list) -> str | None:
    """The id 3.25.1 to 3.25.2 made of a batch: the sorted `<entry> <sha256>` lines (a send back's third word included)
    joined by newlines. A baseline written then keeps this id, and `uncovered` reads it only for a lock that is not
    strict (pre-3.26) while the decision log is empty (3.26 logs every decision). The join is ambiguous, so it is made only of pairs of the old shape: 2 or 3 fields without
    whitespace, the digest 64 lowercase hex. None for any other batch."""
    if not all(isinstance(p, list) and len(p) in (2, 3) and all(isinstance(w, str) and w and not re.search(r"\s", w) for w in p)
               and re.fullmatch(r"[0-9a-f]{64}", p[1]) for p in pairs):
        return None
    return "screens-" + hashlib.sha256("\n".join(sorted(" ".join(p) for p in pairs)).encode()).hexdigest()[:16]


def uncovered(change: Path, approved: dict) -> list[str]:
    """The approved entries no owner decision covers. approved.json is the owner's approval, so each entry
    names the batch (`decision`) its import was confirmed in: `batches[<id>]` lists that batch's
    `[entry, sha256]` pairs (a send back adds `"send-back"`, an entry with boards or a `deviates` text its `bind-` tag), the id is their
    `approval_id`, and the owner answered `Approve screens` to the dialog of that id (`marks.owner_decisions`, the
    transcript). A file an agent wrote covers nothing, a batch a later send back spent covers nothing (the decision
    log says so), and a log that was trimmed or rewritten fails the check."""
    data = read_json(change / "screens" / "approved.json")
    data = data if isinstance(data, dict) else {}
    batches = data["batches"] if isinstance(data.get("batches"), dict) else {}
    log = [r for r in data["log"] if isinstance(r, dict)] if isinstance(data.get("log"), list) else []
    lock = next((d for rel in ("state/lock.json", "lock.json") if isinstance(d := read_json(change / rel), dict)), {})
    strict = "design" in lock or "head" in data  # 3.26.1: a 3.26 lock, or the `head` 3.26.0 wrote into every approved.json
    out = [f"decision log: {p}" for p in chain_problems(log, data.get("head"), strict=strict)]
    if strict and approved and not log:  # 3.26 logs every decision: approvals beside an empty or absent log mean it was removed
        out.append("decision log: the log is empty beside approvals: entries were removed")
    repo = Path(subprocess.run(["git", "-C", str(change), "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")
    sys.dont_write_bytecode = True  # the gate checks that the tree is clean afterwards: no __pycache__ from here
    try:
        from marks import owner_decisions

        decided = owner_decisions(repo, change.name)
    except ImportError:  # no reader of owner answers: nothing is covered
        decided = {}
    design = load_design(change)
    tags = {e["id"]: binding_tag(change, design, e) for e in load_screens(change)[0]}
    for entry, a in approved.items():
        bid = a.get("decision")
        pairs = batches.get(bid) if isinstance(bid, str) else None
        ok = isinstance(pairs, list) and all(isinstance(p, list) and len(p) in (2, 3) for p in pairs)
        # a deviation the owner did not see (added after the approval) is not covered: it needs the gallery again
        held = ok and any(p[:2] == [entry, a.get("sha256")] and p[2:] != ["send-back"] and p[2:] == ([tags[entry]] if tags.get(entry) else []) for p in pairs)
        if not ok or bid not in (approval_id(pairs), *([] if strict or log else [legacy_approval_id(pairs)])) or not held:
            out.append(f"{entry}: no recorded batch of an owner approval holds it" + (" with its current board mapping and deviation" if tags.get(entry) else ""))
        elif decided.get(bid, ("",))[0] != "screens":
            out.append(f"{entry}: the owner has not answered the dialog of {bid}")
        elif replayed(log, entry, bid):
            out.append(f"{entry}: the owner's answer of {bid} was spent by a later send back: approve the screen again")
    return out


def judge(change: Path, entries: list[dict], shots: Path, threshold: float, started: float = 0.0, repo: Path | None = None) -> int:
    ids = [e["id"] for e in entries]
    second = shots / "second"

    def fresh(path: Path) -> bool:  # written by this batch (a little slack for coarse file times)
        return path.is_file() and path.stat().st_mtime >= started - 2

    absent = [i for i in ids if not fresh(shots / f"{i}.png") or not fresh(second / f"{i}.png")]
    if absent:
        print("the capture wrote no shot for: " + ", ".join(absent))
        return end("CAPTURE FAIL capture", 1)
    unstable = [i for i in ids if sha(shots / f"{i}.png") != sha(second / f"{i}.png")]
    shutil.rmtree(second, ignore_errors=True)
    if unstable:
        print("unstable: two shots of one entry differ (animation, a clock, random data: fix the preview page):\n  " + "\n  ".join(unstable))
        return end("CAPTURE FAIL unstable", 1)
    if bad := image_problems(change):
        print("\n".join(bad) + "\nRestore the image from git, or have the plan approved again with the new one.")
        return end("CAPTURE FAIL design", 1)
    try:
        approved = json.loads((change / "screens" / "approved.json").read_text(encoding="utf-8")).get("entries", {})
    except (OSError, ValueError, AttributeError):
        approved = {}
    approved = {i: a for i, a in approved.items() if isinstance(a, dict)} if isinstance(approved, dict) else {}
    fresh_ids = [i for i in ids if i not in approved]
    if fresh_ids:
        where = os.path.relpath(change, repo) if repo else str(change)
        print(
            f"{len(fresh_ids)} of {len(ids)} entries have no approved shot: " + ", ".join(fresh_ids)
            + f"\nThe shots are in {shots}. Build the gallery (`python3 scripts/evidence.py gallery {where}`) and have the owner approve them."
        )
        return end("VERIFY BLOCKED reason=needs-baseline", 3)
    full = {e["id"] for e in load_screens(change)[0]}  # an early close checks the entries due, the last one every approval
    if no_owner := uncovered(change, approved if set(ids) >= full else {i: a for i, a in approved.items() if i in ids}):
        print("approved.json holds approvals no owner decision covers (an agent cannot approve a screen):\n  " + "\n  ".join(no_owner)
              + "\nImport the gallery answers with `evidence.py gallery <change> --import`: it asks the owner, and records the answer.")
        return end("CAPTURE FAIL approval", 1)
    # the baseline is screens/<id>.png (the id is validated: no path comes from the file field) and must be the approved bytes
    torn = [i for i in ids if sha(change / "screens" / f"{i}.png") != approved[i].get("sha256")]
    if torn:
        print("the approved baseline does not match its recorded sha256 (edited or missing): " + ", ".join(torn)
              + "\nRestore screens/<id>.png from git, or approve the shots again.")
        return end("CAPTURE FAIL baseline", 1)
    changed = []
    (shots / "diff").mkdir(exist_ok=True)
    for i in ids:
        now, base, diff = shots / f"{i}.png", change / "screens" / f"{i}.png", shots / "diff" / f"{i}.png"
        if sha(now) == approved[i].get("sha256"):
            continue
        try:
            share = compare(now, base, diff) if threshold else 1.0
        except (ValueError, zlib.error, struct.error) as err:
            print(f"{i}: cannot compare by pixels: {err}")
            share = 1.0
        if share > threshold:
            note = f" ({share:.4%} of pixels, diff {diff})" if diff.is_file() else ""
            changed.append(f"{i}: differs from the approved shot{note}")
    if changed:
        print("\n".join(changed) + "\nA changed screen needs a new approval: rebuild the gallery, or fix the page.")
        return end("CAPTURE FAIL changed", 1)
    return end(f"CAPTURE PASS {len(ids)}", 0)


def end(line: str, code: int) -> int:
    print(line)
    return code


def main(argv: list[str]) -> int:
    args, upto, group = argv[1:], None, False
    if "--group" in args:
        group = True
        args.remove("--group")
    if "--upto" in args:
        k = args.index("--upto")
        try:
            upto = int(args[k + 1])
        except (IndexError, ValueError):
            print(__doc__)
            return 2
        del args[k : k + 2]
    if len(args) != 2 or args[0] not in ("check", "run"):
        print(__doc__)
        return 2
    change = Path(args[1]).resolve()
    if args[0] == "check":
        entries, problems = load_screens(change)
        problems += design_problems(change, entries) if not problems else []
        print("\n".join(problems))
        return 1 if problems else 0
    repo = Path(subprocess.run(["git", "-C", str(change), "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")
    return run(change, repo, upto, group)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
