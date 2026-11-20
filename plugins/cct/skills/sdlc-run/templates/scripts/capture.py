"""The app capture of a change approved from 3.25.0 (lock `"visual": "app"`): one app start, every
`screens.json` entry at its viewport, twice, compared with the approved baseline.

    python3 scripts/capture.py check <change-dir>     # validate screens.json only (what `approve` runs)
    python3 scripts/capture.py run <change-dir>       # reachability, capture x2, stability, baseline compare

`screens.json` (in the change folder): a list, or {"screens": [...]}, of
    {"id": "leads.list.empty", "route": "/preview/leads?state=empty", "viewport": [1440, 900], "fixture": "empty-leads"}
Ids are plain names (letters, digits, `.` `_` `-`) and unique; a route starts with `/`; a viewport is two positive ints.

sdlc.json `visual` (all optional except `start` for `run`):
    start         shell command that starts the app on $PORT (a build step may precede it: `npm run build && npm start`)
    ready         path polled until the app answers (default "/")
    startTimeout  seconds to wait for it (default 120)
    threshold     fraction of differing pixels still accepted (default 0: bytes must be equal)
    driver        a capture command of your own: `<driver> <jobs.json>` writes the png of every job (see below);
                  default is the repo's Playwright (`@playwright/test` or `playwright` in package.json)

Driver contract: jobs.json is {"base": "http://127.0.0.1:PORT", "jobs": [{"id", "route", "viewport", "out"}]};
the driver writes a png to every `out` and exits 0.

Shots go to <change>/verify/shots/<id>.png (and <id>.b.png for the second pass; a differing pair is
unstable). The baseline is <change>/screens/approved.json: {"format": 1, "entries": {"<id>": {"sha256", "file", ...}}}
with the png at <change>/<file>. A difference writes verify/shots/<id>.diff.png and needs a new approval.

Last line: `CAPTURE PASS <n>` (exit 0), `CAPTURE FAIL ...` (exit 1) or `VERIFY BLOCKED reason=<code>` (exit 3:
needs-baseline when an entry has no approved shot, env when the app or Playwright is missing).
Written by `sdlc-run adopt` from the kit; edit the kit, not this copy. stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
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
    await page.goto(job.base + j.route, { waitUntil: 'networkidle' });
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
    entries = data.get("screens") if isinstance(data, dict) else data
    if not isinstance(entries, list) or not entries:
        return [], [f"{path.name} must be a non-empty list of entries (or {{\"screens\": [...]}})"]
    problems, seen = [], set()
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
        seen.add(name)
        route = e.get("route")
        if not isinstance(route, str) or not route.startswith("/") or "//" in route[:2] or re.search(r"\s", route):
            problems.append(f"{tag}: route must start with a single / and hold no space")
        vp = e.get("viewport")
        if not (isinstance(vp, list) and len(vp) == 2 and all(isinstance(n, int) and not isinstance(n, bool) and 0 < n <= 10000 for n in vp)):
            problems.append(f"{tag}: viewport must be [width, height], two positive integers")
        if not isinstance(e.get("fixture"), str) or not e["fixture"].strip():
            problems.append(f"{tag}: fixture must name the sample data the app seeds")
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


def fetch(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=10) as r:  # noqa: S310 -- our own local app
            return r.status
    except urllib.error.HTTPError as err:
        return err.code
    except (OSError, ValueError):
        return 0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def stop(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass


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


def run(change: Path, repo: Path) -> int:
    entries, problems = load_screens(change)
    if problems:
        print("\n".join(problems))
        return end("CAPTURE FAIL screens.json", 1)
    cfg = read_config(repo)
    if not cfg.get("start"):
        print('sdlc.json has no visual.start: the command that starts the app on $PORT (for example "npm run build && npm start").')
        return end("VERIFY BLOCKED reason=env", 3)
    port = int(os.environ.get("SDLC_APP_PORT") or free_port())
    base = f"http://127.0.0.1:{port}"
    shots = change / "verify" / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    log = tempfile.NamedTemporaryFile("w+", prefix="capture-app-", suffix=".log", delete=False)
    app = subprocess.Popen(
        str(cfg["start"]), shell=True, cwd=repo, env={**os.environ, "PORT": str(port)},
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )  # fmt: skip
    try:
        deadline = time.monotonic() + float(cfg.get("startTimeout", 120))
        ready = base + str(cfg.get("ready", "/"))
        while not fetch(ready):
            if app.poll() is not None or time.monotonic() > deadline:
                log.seek(0)
                print(f"the app did not answer at {ready}:\n" + "\n".join(log.read().splitlines()[-30:]))
                return end("VERIFY BLOCKED reason=env", 3)
            time.sleep(0.5)
        missing = [f"{e['id']}: {e['route']} answers {code or 'nothing'}" for e in entries if not 200 <= (code := fetch(base + e["route"])) < 300]
        if missing:
            print("no reachable preview page for these entries (the build gives every one a route):\n" + "\n".join(missing))
            return end("CAPTURE FAIL preview-unreachable", 1)
        jobs = [
            {"id": e["id"], "route": e["route"], "viewport": e["viewport"], "out": str(shots / f"{e['id']}{suffix}.png")}
            for suffix in ("", ".b")
            for e in entries
        ]
        jobs_file = shots / "jobs.json"
        jobs_file.write_text(json.dumps({"base": base, "jobs": jobs}), encoding="utf-8")
        code, out = drive(repo, cfg, jobs_file)
        if code:
            print(out)
            return end("VERIFY BLOCKED reason=env" if code == 3 else "CAPTURE FAIL capture", 3 if code == 3 else 1)
    finally:
        stop(app)
        log.close()
        Path(log.name).unlink(missing_ok=True)
    return judge(change, entries, shots, float(cfg.get("threshold", 0)))


def judge(change: Path, entries: list[dict], shots: Path, threshold: float) -> int:
    ids = [e["id"] for e in entries]
    absent = [i for i in ids if not (shots / f"{i}.png").is_file() or not (shots / f"{i}.b.png").is_file()]
    if absent:
        print("the capture wrote no shot for: " + ", ".join(absent))
        return end("CAPTURE FAIL capture", 1)
    unstable = [i for i in ids if sha(shots / f"{i}.png") != sha(shots / f"{i}.b.png")]
    for i in ids:
        (shots / f"{i}.b.png").unlink(missing_ok=True) if i not in unstable else None
    if unstable:
        print("unstable: two shots of one entry differ (animation, a clock, random data: fix the preview page):\n  " + "\n  ".join(unstable))
        return end("CAPTURE FAIL unstable", 1)
    try:
        approved = json.loads((change / "screens" / "approved.json").read_text(encoding="utf-8")).get("entries", {})
    except (OSError, ValueError, AttributeError):
        approved = {}
    fresh = [i for i in ids if i not in approved]
    if fresh:
        print(
            f"{len(fresh)} of {len(ids)} entries have no approved shot: " + ", ".join(fresh)
            + f"\nThe shots are in {shots}. Build the gallery (`python3 scripts/evidence.py gallery {change.name}`) and have the owner approve them."
        )
        return end("VERIFY BLOCKED reason=needs-baseline", 3)
    changed = []
    for i in ids:
        now, base = shots / f"{i}.png", change / str(approved[i].get("file", f"screens/{i}.png"))
        if sha(now) == approved[i].get("sha256"):
            continue
        try:
            share = compare(now, base, shots / f"{i}.diff.png") if base.is_file() and threshold else 1.0
        except (ValueError, zlib.error, struct.error) as err:
            print(f"{i}: cannot compare by pixels: {err}")
            share = 1.0
        if share > threshold:
            note = f" ({share:.4%} of pixels, diff {shots / f'{i}.diff.png'})" if (shots / f"{i}.diff.png").is_file() else ""
            changed.append(f"{i}: differs from the approved shot{note}")
    if changed:
        print("\n".join(changed) + "\nA changed screen needs a new approval: rebuild the gallery, or fix the page.")
        return end("CAPTURE FAIL changed", 1)
    return end(f"CAPTURE PASS {len(ids)}", 0)


def end(line: str, code: int) -> int:
    print(line)
    return code


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("check", "run"):
        print(__doc__)
        return 2
    change = Path(argv[2]).resolve()
    if argv[1] == "check":
        problems = load_screens(change)[1]
        print("\n".join(problems))
        return 1 if problems else 0
    repo = Path(subprocess.run(["git", "-C", str(change), "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")
    return run(change, repo)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
