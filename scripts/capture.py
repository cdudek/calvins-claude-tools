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
        if isinstance(route, str) and isinstance(vp, list):
            first = spots.setdefault((route, tuple(map(str, vp))), name)
            if first != name:
                problems.append(f"{tag}: same route and viewport as {first}: the fixture shows only through the route, so give each state its own")
    return [e for e in entries if isinstance(e, dict)], problems


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


def stop(proc: subprocess.Popen, group: bool = False) -> None:
    """Stop the app. With `group` it shares this process's group (so the gate's group kill reaps it): signal the
    whole group while ignoring our own SIGTERM; otherwise it has a group of its own."""
    old = signal.signal(signal.SIGTERM, signal.SIG_IGN) if group else None
    try:
        os.killpg(os.getpgrp() if group else proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        try:
            proc.kill() if group else os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
    finally:
        if old is not None:
            signal.signal(signal.SIGTERM, old)


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
        problems = load_screens(change)[1]
        print("\n".join(problems))
        return 1 if problems else 0
    repo = Path(subprocess.run(["git", "-C", str(change), "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")
    return run(change, repo, upto, group)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
