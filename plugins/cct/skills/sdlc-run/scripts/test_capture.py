"""capture.py: screens.json validation, the app start, reachability, stability and the comparison verdicts,
end to end on a tiny fixture app (two screens, two states each). The browser is faked at the driver
boundary (sdlc.json visual.driver); one live Playwright test runs only with SDLC_LIVE_PLAYWRIGHT=1."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
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
    e.update(HOME=str(repo.parent / "home"), **env)  # the owner's transcripts are read from the home folder
    return subprocess.run([sys.executable, str(CAPTURE), "run", str(repo / "changes" / ID)], cwd=repo, capture_output=True, text=True, env=e)


def _last(r: subprocess.CompletedProcess[str]) -> str:
    return r.stdout.strip().splitlines()[-1]


def owner_answers(repo: Path, bid: str, label: str = "Approve screens", n: int = 1, change_id: str = ID, home: Path | None = None,
                  options: tuple[str, ...] = ("Approve screens", "Hold"), cwd: Path | None = None) -> None:
    """The owner's structured answer to the dialog that names approval `bid`, in the session transcript
    Claude Code keeps for this repo (the one place the gate believes an owner decision)."""
    folder = (home or repo.parent / "home") / ".claude/projects" / re.sub(r"[^A-Za-z0-9]", "-", str(repo.resolve()))
    folder.mkdir(parents=True, exist_ok=True)
    question = f"Change {change_id}, finding {bid}: Approve these screens?"
    stamp = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=60 + n)).isoformat()
    where = {"cwd": str(cwd)} if cwd else {}
    entries = [
        {"type": "assistant", "timestamp": stamp, **where, "message": {"content": [{
            "type": "tool_use", "id": f"s{n}", "name": "AskUserQuestion",
            "input": {"questions": [{"question": question, "options": [{"label": o} for o in options]}]},
        }]}},
        {"type": "user", "timestamp": stamp, "toolUseResult": {"answers": {question: label}},
         "message": {"content": [{"type": "tool_result", "tool_use_id": f"s{n}", "content": "ok"}]}},
    ]  # fmt: skip
    with (folder / "session.jsonl").open("a") as out:
        out.write("".join(json.dumps(e) + "\n" for e in entries))


def _compare(repo: Path, verdict: str = "match", only: tuple[str, ...] = ()) -> None:
    """What the agents' board-to-build comparison leaves behind: one verdict per captured shot, bound to its sha256."""
    change = repo / "changes" / ID
    entries = {}
    for shot in sorted((change / "verify" / "shots").glob("*.png")):
        if only and shot.stem not in only:
            continue
        entries[shot.stem] = {"sha256": hashlib.sha256(shot.read_bytes()).hexdigest(), "verdict": verdict,
                              "report": "verify/ux/qa.md", "differences": "the header is missing"}  # fmt: skip
    (change / "verify" / "comparison.json").write_text(json.dumps({"format": 1, "entries": entries}))


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
    (tmp_path / "screens.json").write_text(json.dumps({"entries": [good, good]}))
    assert "used twice" in capture.load_screens(tmp_path)[1][0]
    (tmp_path / "screens.json").write_text(json.dumps({"entries": ENTRIES}))
    assert capture.load_screens(tmp_path)[1] == []


# --- the capture, end to end on the fixture app ----------------------------------------------------


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
    assert _last(_run(repo)) == "VERIFY BLOCKED reason=needs-comparison"


@pytest.mark.parametrize("image", ["asks/../x.png", "./a.png", "a/./b.png", "../x.png", "a//b.png"])
def test_a_board_path_with_dot_parts_is_no_board_image(tmp_path: Path, image: str) -> None:
    for rel in ("x.png", "a.png", "a/b.png", "asks/keep"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(b"png")
    assert capture.board_file(tmp_path, image) is None
    assert capture.read_board(tmp_path, image) is None
    assert capture.read_board(tmp_path, "a/b.png") == b"png"


# --- the 3.25.0 fix round ----------------------------------------------------------------------------


def test_an_occupied_port_blocks_before_the_app_starts(tmp_path: Path) -> None:
    import socket

    repo = _repo(tmp_path)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        port = s.getsockname()[1]
        r = _run(repo, SDLC_APP_PORT=str(port))
    assert _last(r) == "VERIFY BLOCKED reason=env" and r.returncode == 3 and str(port) in r.stdout


@pytest.mark.parametrize(
    ("second", "needle"),
    [
        ({"id": "LEADS.list.empty", "route": "/preview/x", "viewport": [1, 1], "fixture": "f"}, "same name"),
        ({"id": "other", "route": ENTRIES[0]["route"], "viewport": [1440, 900], "fixture": "seed-2"}, "same route and viewport"),
        ({"id": "ms", "route": "/x", "viewport": [1, 1], "fixture": "f", "milestone": 0}, "milestone"),
        ({"id": "ms", "route": "/x", "viewport": [1, 1], "fixture": "f", "milestone": "2"}, "milestone"),
    ],
)
def test_entries_that_would_collide_or_hide_a_state_are_refused(tmp_path: Path, second: dict, needle: str) -> None:
    (tmp_path / "screens.json").write_text(json.dumps([ENTRIES[0], second]))
    problems = capture.load_screens(tmp_path)[1]
    assert any(needle in p for p in problems), problems


def test_an_id_that_looks_like_a_second_pass_does_not_collide(tmp_path: Path) -> None:
    ents = [
        {"id": "home", "route": "/preview/leads?state=full", "viewport": [800, 600], "fixture": "a"},
        {"id": "home.b", "route": "/preview/deals?state=full", "viewport": [800, 600], "fixture": "a"},
        {"id": "home.diff", "route": "/preview/deals?state=empty", "viewport": [800, 600], "fixture": "a"},
    ]
    repo = _repo(tmp_path, ents)
    r = _run(repo)
    assert _last(r) == "VERIFY BLOCKED reason=needs-comparison" and "3 of 3 screens have no board-to-build comparison" in r.stdout
    assert sorted(p.name for p in (repo / "changes" / ID / "verify/shots").glob("*.png")) == ["home.b.png", "home.diff.png", "home.png"]


def test_a_retry_never_accepts_shots_left_by_an_earlier_batch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _run(repo)  # leaves every primary shot on disk
    (repo / "noop.py").write_text("")
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["visual"]["driver"] = f"{sys.executable} noop.py"  # a driver that skips the work and exits 0
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    r = _run(repo)
    assert _last(r) == "CAPTURE FAIL capture" and "wrote no shot" in r.stdout


def test_a_preview_that_redirects_is_not_reachable(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "app.py").write_text((repo / "app.py").read_text().replace(
        'if u.path == "/" : body = b"ok"',
        'if u.path == "/login-wall":\n            self.send_response(302); self.send_header("Location", "/"); self.end_headers(); return\n        if u.path == "/" : body = b"ok"'))
    gone = {"id": "deals.list.wall", "route": "/login-wall", "viewport": [800, 600], "fixture": "seed-1"}
    (repo / "changes" / ID / "screens.json").write_text(json.dumps([*ENTRIES, gone]))
    r = _run(repo)
    assert _last(r) == "CAPTURE FAIL preview-unreachable"
    assert "deals.list.wall: /login-wall answers 302" in r.stdout


def test_the_driver_contract_and_the_playwright_driver_check_the_origin_and_the_status() -> None:
    assert "redirect" in capture.__doc__ and "2xx" in capture.__doc__
    assert "new URL(page.url()).origin" in capture.PLAYWRIGHT_JS and "res.status()" in capture.PLAYWRIGHT_JS


@pytest.mark.parametrize("bad", [5, -0.1, "NaN", "0.1", True, 1.5])
def test_a_threshold_outside_zero_to_one_is_an_env_block_naming_it(tmp_path: Path, bad: object) -> None:
    repo = _repo(tmp_path, threshold=bad)
    r = _run(repo)
    assert _last(r) == "VERIFY BLOCKED reason=env" and "visual.threshold" in r.stdout and repr(bad) in r.stdout
    assert not list((repo / "changes" / ID / "verify").glob("shots/*.png"))  # refused before the app started


def test_killing_the_capture_with_its_group_reaps_the_app(tmp_path: Path) -> None:
    import signal
    import time

    repo = _repo(tmp_path)
    (repo / "slow.py").write_text("import time; time.sleep(60)")
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["visual"]["start"] = f"echo $$ > app.pid; exec {sys.executable} app.py"
    cfg["visual"]["driver"] = f"{sys.executable} slow.py"
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    cap = subprocess.Popen([sys.executable, str(CAPTURE), "run", str(repo / "changes" / ID), "--group"], cwd=repo, env=env, start_new_session=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # fmt: skip
    pidfile = repo / "app.pid"
    for _ in range(100):
        if pidfile.is_file() and pidfile.read_text().strip():
            break
        time.sleep(0.1)
    time.sleep(1.5)  # the app answers and the slow driver is running
    pid = int(pidfile.read_text())
    os.killpg(cap.pid, signal.SIGKILL)  # what the gate does on a timeout or a cancel
    cap.wait()
    for _ in range(50):
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.1)
    os.kill(pid, signal.SIGKILL)
    raise AssertionError("the app outlived the killed capture")


def test_the_milestone_bound_captures_only_the_entries_due(tmp_path: Path) -> None:
    later = {"id": "deals.list.later", "route": "/preview/not-built-yet", "viewport": [800, 600], "fixture": "seed-1", "milestone": 2}
    repo = _repo(tmp_path, [*ENTRIES, later])
    change = repo / "changes" / ID
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    r = subprocess.run([sys.executable, str(CAPTURE), "run", str(change), "--upto", "1"], cwd=repo, capture_output=True, text=True, env=e)
    assert _last(r) == "VERIFY BLOCKED reason=needs-comparison" and "4 of 4 screens" in r.stdout
    assert _last(_run(repo)) == "CAPTURE FAIL preview-unreachable"  # the last milestone needs all of them


def test_group_cleanup_spares_the_shell_that_leads_the_group(tmp_path: Path) -> None:
    """The gate runs a check as `sh -c <cmd>` in a new session; a shell that does not exec (dash) leads the group.
    Stopping the app must not signal that shell, or a passing capture reads as a failure."""
    repo = _repo(tmp_path)
    _run(repo)
    _compare(repo)
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {"HOME": str(tmp_path / "home")}
    cmd = f"{sys.executable} {CAPTURE} run {repo / 'changes' / ID} --group; echo rc=$?"  # `; echo` keeps sh alive
    r = subprocess.run(["sh", "-c", cmd], cwd=repo, capture_output=True, text=True, env=e, start_new_session=True)
    assert r.returncode == 0 and "CAPTURE PASS 4" in r.stdout and "rc=0" in r.stdout, (r.returncode, r.stdout)


def _gate_dirs(repo: Path) -> list[str]:
    return sorted(p.name for p in (repo / "changes" / ID).iterdir())


def test_a_run_with_no_comparison_blocks_and_leaves_the_shots(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    r = _run(repo)
    assert _last(r) == "VERIFY BLOCKED reason=needs-comparison" and r.returncode == 3
    assert "4 of 4 screens have no board-to-build comparison" in r.stdout and "No owner answer is needed" in r.stdout
    shots = sorted(p.name for p in (repo / "changes" / ID / "verify/shots").glob("*.png"))
    assert shots == sorted(f"{e['id']}.png" for e in ENTRIES)  # the second pass is not kept


def test_a_matching_comparison_of_this_capture_passes_and_stores_nothing(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _run(repo)
    _compare(repo)
    r = _run(repo)  # recaptured: the same page gives the same bytes, so the verdicts still bind
    assert _last(r) == "CAPTURE PASS 4" and r.returncode == 0
    change = repo / "changes" / ID
    assert not (change / "screens").exists() and not list(change.rglob("approved.json")) and not list(change.rglob("baselines-pending.json"))
    assert _last(_run(repo, MARK="changed")) == "VERIFY BLOCKED reason=needs-comparison"  # a changed page is compared again


def test_a_differing_comparison_is_a_blocking_finding_never_an_owner_question(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _run(repo)
    _compare(repo, "differs", only=("leads.list.empty",))
    path = repo / "changes" / ID / "verify/comparison.json"
    data = json.loads(path.read_text())
    for shot in (repo / "changes" / ID / "verify/shots").glob("*.png"):
        if shot.stem != "leads.list.empty":
            data["entries"][shot.stem] = {"sha256": hashlib.sha256(shot.read_bytes()).hexdigest(), "verdict": "match", "report": "r"}
    path.write_text(json.dumps(data))
    r = _run(repo)
    assert _last(r) == "CAPTURE FAIL comparison" and r.returncode == 1
    assert "leads.list.empty: the header is missing" in r.stdout and "not an owner question" in r.stdout
    _compare(repo)  # fixed in the fix round: the new capture matches
    assert _last(_run(repo)) == "CAPTURE PASS 4"


def test_a_forged_comparison_without_the_capture_sha_is_refused(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    change = repo / "changes" / ID
    (change / "verify").mkdir()
    forged = {e["id"]: {"verdict": "match", "report": "made up"} for e in ENTRIES}  # no sha256, never captured
    (change / "verify/comparison.json").write_text(json.dumps({"format": 1, "entries": forged}))
    r = _run(repo)
    assert _last(r) == "VERIFY BLOCKED reason=needs-comparison" and "4 of 4 screens" in r.stdout


def test_a_comparison_of_an_earlier_capture_or_a_wrong_sha_is_refused(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _run(repo)
    _compare(repo)
    r = _run(repo, MARK="changed")  # the page changed since the comparison: its shots hash differently
    assert _last(r) == "VERIFY BLOCKED reason=needs-comparison" and "4 of 4 screens" in r.stdout
    _compare(repo)
    path = repo / "changes" / ID / "verify/comparison.json"
    data = json.loads(path.read_text())
    data["entries"]["leads.list.empty"]["sha256"] = "0" * 64
    path.write_text(json.dumps(data))
    r = _run(repo, MARK="changed")
    assert _last(r) == "VERIFY BLOCKED reason=needs-comparison" and "leads.list.empty" in r.stdout
    assert "1 of 4 screens" in r.stdout


def test_the_comparison_is_judged_only_for_the_entries_due(tmp_path: Path) -> None:
    ents = [{**e, "milestone": 2 if e["id"].startswith("deals") else 1} for e in ENTRIES]
    repo = _repo(tmp_path, ents)
    _run(repo)
    _compare(repo, only=("leads.list.empty", "leads.list.full"))
    change = repo / "changes" / ID
    env = {**os.environ, "HOME": str(tmp_path / "home")}
    run = lambda *extra: subprocess.run([sys.executable, str(CAPTURE), "run", str(change), *extra], cwd=repo, capture_output=True, text=True, env=env)  # noqa: E731
    assert _last(run("--upto", "1")) == "CAPTURE PASS 2"
    final = run()
    assert _last(final) == "VERIFY BLOCKED reason=needs-comparison" and "deals.list.empty" in final.stdout
