"""capture.py: screens.json validation, the app start, reachability, stability and the baseline compare,
end to end on a tiny fixture app (two screens, two states each). The browser is faked at the driver
boundary (sdlc.json visual.driver); one live Playwright test runs only with SDLC_LIVE_PLAYWRIGHT=1."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "templates" / "scripts"
CAPTURE = SCRIPTS / "capture.py"
sys.path.insert(0, str(SCRIPTS))
import capture  # noqa: E402

ID = "2026-11-20-leads"
APP = '''
import os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
PAGES = {"/preview/leads": "Leads", "/preview/deals": "Deals"}
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/" : body = b"ok"
        elif u.path in PAGES:
            state = parse_qs(u.query).get("state", ["full"])[0]
            if os.environ.get("FLAKY") and state == "empty":
                import time; state += str(time.time())
            body = f"{PAGES[u.path]}:{state}:{os.environ.get('MARK', '')}".encode()
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass
HTTPServer(("127.0.0.1", int(os.environ["PORT"])), H).serve_forever()
'''
# the fake browser: GET the page, draw a 16x8 png whose pixels come from the page bytes
DRIVER = '''
import json, sys, hashlib, urllib.request
sys.path.insert(0, SCRIPTS_DIR)
import capture
job = json.load(open(sys.argv[1]))
for j in job["jobs"]:
    body = urllib.request.urlopen(job["base"] + j["route"]).read()
    h = hashlib.sha256(body).digest()
    rgb = bytes(h[(i // 3) % 32] for i in range(16 * 8 * 3))
    capture.write_png(__import__("pathlib").Path(j["out"]), 16, 8, rgb)
'''.replace("SCRIPTS_DIR", repr(str(SCRIPTS)))
ENTRIES = [
    {"id": f"{s}.list.{st}", "route": f"/preview/{s}?state={st}", "viewport": [1440, 900], "fixture": "seed-1"}
    for s in ("leads", "deals")
    for st in ("empty", "full")
]


def _repo(tmp_path: Path, entries=ENTRIES, **visual) -> Path:
    repo = tmp_path / "repo"
    change = repo / "changes" / ID
    change.mkdir(parents=True)
    (repo / "app.py").write_text(APP)
    (repo / "driver.py").write_text(DRIVER)
    cfg = {"start": f"{sys.executable} app.py", "driver": f"{sys.executable} driver.py", "startTimeout": 20, **visual}
    (repo / "sdlc.json").write_text(json.dumps({"visual": cfg}))
    (change / "screens.json").write_text(json.dumps(entries))
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


def _run(repo: Path, **env: str) -> subprocess.CompletedProcess[str]:
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    e.update(env)
    return subprocess.run([sys.executable, str(CAPTURE), "run", str(repo / "changes" / ID)], cwd=repo, capture_output=True, text=True, env=e)


def _last(r: subprocess.CompletedProcess[str]) -> str:
    return r.stdout.strip().splitlines()[-1]


def _approve_all(repo: Path) -> None:
    """What `evidence.py gallery --import` leaves behind: the shots as baselines, their sha256 in approved.json."""
    change = repo / "changes" / ID
    (change / "screens").mkdir(exist_ok=True)
    entries = {}
    for e in ENTRIES:
        shot = change / "verify" / "shots" / f"{e['id']}.png"
        (change / "screens" / f"{e['id']}.png").write_bytes(shot.read_bytes())
        entries[e["id"]] = {"sha256": hashlib.sha256(shot.read_bytes()).hexdigest(), "file": f"screens/{e['id']}.png",
                            "approvedBy": "owner", "date": "2026-11-20"}  # fmt: skip
    (change / "screens" / "approved.json").write_text(json.dumps({"format": 1, "entries": entries}))


# --- screens.json ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("entry", "needle"),
    [
        ({"route": "/a", "viewport": [1, 1], "fixture": "f"}, "id must be a plain name"),
        ({"id": "../x", "route": "/a", "viewport": [1, 1], "fixture": "f"}, "id must be a plain name"),
        ({"id": "a", "route": "a", "viewport": [1, 1], "fixture": "f"}, "route must start"),
        ({"id": "a", "route": "//evil", "viewport": [1, 1], "fixture": "f"}, "route must start"),
        ({"id": "a", "route": "/a", "viewport": [0, 5], "fixture": "f"}, "viewport"),
        ({"id": "a", "route": "/a", "viewport": [1], "fixture": "f"}, "viewport"),
        ({"id": "a", "route": "/a", "viewport": [1, 1]}, "fixture"),
    ],
)
def test_a_bad_entry_is_named(tmp_path: Path, entry: dict, needle: str) -> None:
    (tmp_path / "screens.json").write_text(json.dumps([entry]))
    _, problems = capture.load_screens(tmp_path)
    assert any(needle in p for p in problems), problems


def test_missing_empty_and_duplicate_screens_json(tmp_path: Path) -> None:
    assert "missing" in capture.load_screens(tmp_path)[1][0]
    (tmp_path / "screens.json").write_text("[]")
    assert capture.load_screens(tmp_path)[1]
    good = ENTRIES[0]
    (tmp_path / "screens.json").write_text(json.dumps({"screens": [good, good]}))
    assert "used twice" in capture.load_screens(tmp_path)[1][0]
    (tmp_path / "screens.json").write_text(json.dumps({"screens": ENTRIES}))
    assert capture.load_screens(tmp_path)[1] == []


# --- the capture, end to end on the fixture app ----------------------------------------------------


def test_unapproved_entries_block_with_needs_baseline_and_leave_the_shots(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    r = _run(repo)
    assert _last(r) == "VERIFY BLOCKED reason=needs-baseline" and r.returncode == 3
    assert "4 of 4 entries have no approved shot" in r.stdout
    shots = sorted(p.name for p in (repo / "changes" / ID / "verify/shots").glob("*.png"))
    assert shots == sorted(f"{e['id']}.png" for e in ENTRIES)  # the second pass is not kept


def test_approved_shots_pass_and_a_changed_page_fails_with_the_entry_and_a_diff(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _run(repo)
    _approve_all(repo)
    r = _run(repo)
    assert _last(r) == "CAPTURE PASS 4" and r.returncode == 0
    r = _run(repo, MARK="changed")
    assert _last(r) == "CAPTURE FAIL changed" and r.returncode == 1
    assert all(f"{e['id']}: differs from the approved shot" in r.stdout for e in ENTRIES)


def test_the_threshold_accepts_a_small_share_of_pixels_and_refuses_a_large_one(tmp_path: Path) -> None:
    repo = _repo(tmp_path, threshold=0.1)
    _run(repo)
    _approve_all(repo)
    change = repo / "changes" / ID
    # a baseline that differs from the capture in 2 of 128 pixels is inside 10 percent
    base = change / "screens" / "leads.list.empty.png"
    w, h, _, raw = capture.pixels(base)
    tweaked = bytearray(raw)
    tweaked[0:6] = bytes((tweaked[0] ^ 255, 0, 0, tweaked[3] ^ 255, 0, 0))
    capture.write_png(base, w, h, bytes(tweaked))
    approved = json.loads((change / "screens/approved.json").read_text())
    approved["entries"]["leads.list.empty"]["sha256"] = hashlib.sha256(base.read_bytes()).hexdigest()
    (change / "screens/approved.json").write_text(json.dumps(approved))
    assert _last(_run(repo)) == "CAPTURE PASS 4"
    (repo / "sdlc.json").write_text(json.dumps({"visual": {**json.loads((repo / "sdlc.json").read_text())["visual"], "threshold": 0}}))
    r = _run(repo)
    assert _last(r) == "CAPTURE FAIL changed" and "leads.list.empty: differs" in r.stdout


def test_two_differing_shots_of_one_entry_are_unstable(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    r = _run(repo, FLAKY="1")
    assert _last(r) == "CAPTURE FAIL unstable"
    assert "leads.list.empty" in r.stdout and "deals.list.full" not in r.stdout.split("unstable")[1]


def test_an_entry_with_no_preview_page_fails_before_any_capture(tmp_path: Path) -> None:
    gone = {"id": "deals.list.gone", "route": "/preview/nowhere", "viewport": [800, 600], "fixture": "seed-1"}
    repo = _repo(tmp_path, [*ENTRIES, gone])
    r = _run(repo)
    assert _last(r) == "CAPTURE FAIL preview-unreachable"
    assert "deals.list.gone: /preview/nowhere answers 404" in r.stdout
    assert not list((repo / "changes" / ID / "verify/shots").glob("*.png"))


def test_an_app_that_never_starts_is_an_env_block(tmp_path: Path) -> None:
    repo = _repo(tmp_path, start=f"{sys.executable} -c 'import sys; sys.exit(1)'")
    r = _run(repo)
    assert _last(r) == "VERIFY BLOCKED reason=env" and "did not answer" in r.stdout


def test_a_repo_without_playwright_or_a_driver_is_blocked_with_what_to_install(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    cfg = json.loads((repo / "sdlc.json").read_text())
    del cfg["visual"]["driver"]
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    r = _run(repo)
    assert _last(r) == "VERIFY BLOCKED reason=env"
    assert "@playwright/test" in r.stdout and "visual.driver" in r.stdout


def test_no_start_command_is_an_env_block(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "sdlc.json").write_text("{}")
    assert _last(_run(repo)) == "VERIFY BLOCKED reason=env"


def test_playwright_in_package_json_is_detected(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"@playwright/test": "1.0.0"}}))
    assert capture.has_playwright(tmp_path)
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"left-pad": "1.0.0"}}))
    assert not capture.has_playwright(tmp_path)


def test_png_round_trip_and_compare(tmp_path: Path) -> None:
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    capture.write_png(a, 4, 2, bytes(range(24)))
    capture.write_png(b, 4, 2, bytes(range(24)))
    assert capture.compare(a, b, tmp_path / "d.png") == 0 and not (tmp_path / "d.png").exists()
    capture.write_png(b, 4, 2, bytes(range(1, 25)))
    assert capture.compare(a, b, tmp_path / "d.png") == 1.0 and (tmp_path / "d.png").is_file()


@pytest.mark.skipif(not os.environ.get("SDLC_LIVE_PLAYWRIGHT"), reason="set SDLC_LIVE_PLAYWRIGHT=1 with Playwright installed in the repo")
def test_live_playwright_captures_the_fixture_app_twice_identically(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    cfg = json.loads((repo / "sdlc.json").read_text())
    del cfg["visual"]["driver"]
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    (repo / "package.json").write_text(json.dumps({"devDependencies": {"@playwright/test": "*"}}))
    assert _last(_run(repo)) == "VERIFY BLOCKED reason=needs-baseline"
