"""Per-screen records (evidence.py screen/review/round/status/sheet), enforced by marks.py check."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TPL = Path(__file__).resolve().parents[1] / "templates/scripts"
EVIDENCE, MARKS = TPL / "evidence.py", TPL / "marks.py"
STATUS = Path(__file__).resolve().parent / "sdlc_status.py"
ID = "2026-11-01-match"


def ev(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EVIDENCE), *args], cwd=repo, capture_output=True, text=True
    )


def marks_check(repo: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "HOME": str(repo.parent / "home")}
    return subprocess.run(
        [sys.executable, str(MARKS), "check", ID], cwd=repo, capture_output=True, text=True, env=env
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "sdlc.json").write_text("{}")
    (tmp_path / "changes" / ID).mkdir(parents=True)
    return tmp_path


def change(repo: Path) -> Path:
    return repo / "changes" / ID


def lock(repo: Path, **kv: str) -> None:
    (change(repo) / "lock.json").write_text(json.dumps(kv))


def rec(repo: Path, screen: str) -> dict:
    return json.loads((change(repo) / "verify/screens" / f"{screen}.json").read_text())


def screen(repo: Path, name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return ev(repo, "screen", str(change(repo)), name, *args)


def test_a_screen_record_holds_status_release_and_capture_hashes(repo: Path) -> None:
    shot = change(repo) / "verify/shots/home.png"
    shot.parent.mkdir(parents=True)
    shot.write_bytes(b"png")
    r = screen(repo, "home", "--status", "open", "--design-system", "r1", "--build", "a" * 40,
               "--capture", "verify/shots/home.png", "--group", "auth")  # fmt: skip
    assert r.returncode == 0, r.stderr
    data = rec(repo, "home")
    assert data["status"] == "open" and data["designSystem"] == "r1" and data["group"] == "auth"
    assert data["build"] == "a" * 40
    assert data["captures"] == [
        {"file": "verify/shots/home.png", "sha256": hashlib.sha256(b"png").hexdigest()}
    ]


def test_a_new_design_system_release_resets_the_rounds(repo: Path) -> None:
    screen(repo, "home", "--status", "open", "--design-system", "r1")
    ev(repo, "round", str(change(repo)), "home")
    assert rec(repo, "home")["rounds"] == 1
    screen(repo, "home", "--design-system", "r2")
    assert rec(repo, "home")["rounds"] == 0


def test_the_first_review_writes_the_list_and_a_later_one_only_ticks_or_adds_high(repo: Path) -> None:
    c = str(change(repo))
    r = ev(repo, "review", c, "home", "--defect", "Medium:tokens:wrong grey",
           "--defect", "Low:geometry:2px gap", "--build", "b" * 40)  # fmt: skip
    assert r.returncode == 0, r.stderr
    d = rec(repo, "home")["defects"]
    assert [x["id"] for x in d] == ["D1", "D2"] and d[0]["build"] == "b" * 40
    late = ev(repo, "review", c, "home", "--defect", "Medium:copy:new typo")
    assert late.returncode != 0 and "frozen" in late.stderr
    assert ev(repo, "review", c, "home", "--defect", "High:structure:lost heading").returncode == 0
    assert ev(repo, "review", c, "home", "--defect", "Low:tokens:x", "--regression").returncode == 0
    assert ev(repo, "review", c, "home", "--tick", "D1").returncode == 0
    by = {x["id"]: x for x in rec(repo, "home")["defects"]}
    assert by["D1"]["open"] is False and by["D2"]["open"] is True
    assert by["D3"]["added"] == "later" and by["D4"]["regression"] is True


def test_check_fails_a_late_medium_a_third_round_and_a_changed_capture(repo: Path) -> None:
    lock(repo, screens="required")
    shot = change(repo) / "verify/shots/home.png"
    shot.parent.mkdir(parents=True)
    shot.write_bytes(b"one")
    screen(repo, "home", "--status", "open", "--design-system", "r1",
           "--capture", "verify/shots/home.png")  # fmt: skip
    assert marks_check(repo).returncode == 0, marks_check(repo).stdout
    path = change(repo) / "verify/screens/home.json"
    data = json.loads(path.read_text())
    data["defects"] = [{"id": "D1", "severity": "Medium", "layer": "copy", "text": "t",
                        "build": "x", "open": True, "added": "later"}]  # fmt: skip
    data["rounds"] = 3
    path.write_text(json.dumps(data))
    out = marks_check(repo)
    assert out.returncode == 1
    assert "home: defect D1 added after the first review" in out.stdout
    assert "send the side-by-side list to the owner" in out.stdout
    data.update(defects=[], rounds=0)
    path.write_text(json.dumps(data))
    shot.write_bytes(b"two")
    assert "capture verify/shots/home.png does not match its recorded sha256" in marks_check(repo).stdout


def test_two_captures_must_agree(repo: Path) -> None:
    lock(repo, screens="required")
    shots = change(repo) / "verify/shots"
    shots.mkdir(parents=True)
    (shots / "a.png").write_bytes(b"1")
    (shots / "b.png").write_bytes(b"1")
    screen(repo, "home", "--status", "open", "--capture", "verify/shots/a.png",
           "--capture", "verify/shots/b.png")  # fmt: skip
    assert marks_check(repo).returncode == 0
    (shots / "b.png").write_bytes(b"2")
    screen(repo, "home", "--capture", "verify/shots/a.png", "--capture", "verify/shots/b.png")
    assert "home: unstable: its two captures differ" in marks_check(repo).stdout


def test_a_lenient_change_ignores_screen_rules(repo: Path) -> None:
    (change(repo) / "marks.json").write_text('{"rows": []}')
    screen(repo, "home", "--status", "open")
    path = change(repo) / "verify/screens/home.json"
    data = json.loads(path.read_text())
    data["rounds"] = 9
    path.write_text(json.dumps(data))
    assert marks_check(repo).returncode == 0


def fill(repo: Path) -> None:
    rows = [("a", "match", 0, "auth"), ("b", "fixed", 1, "auth"), ("c", "ruled-out", 0, ""),
            ("d", "accepted-by-owner", 0, ""), ("e", "open", 2, "auth"), ("f", "open", 2, "pay"),
            ("g", "waits-on-design-system", 0, ""), ("h", "open", 1, ""), ("i", "open", 0, "")]  # fmt: skip
    for name, status, rounds, group in rows:
        screen(repo, name, "--status", status, *(["--group", group] if group else []))
        for _ in range(rounds):
            ev(repo, "round", str(change(repo)), name)


def test_status_counts_are_mutually_exclusive(repo: Path) -> None:
    fill(repo)
    out = ev(repo, "status", str(change(repo))).stdout.strip()
    assert out == "screens: 4 of 9 done · 2 wait on you · 1 wait on the design system · 2 open"


def test_sdlc_status_prints_the_screens_line_and_nothing_without_records(repo: Path) -> None:
    assert ev(repo, "status", str(change(repo))).stdout == ""
    fill(repo)
    sys.path.insert(0, str(STATUS.parent))
    import sdlc_status

    assert sdlc_status.screens_line(change(repo)).startswith("screens: 4 of 9 done")


def test_the_owner_sheet_lists_screens_left_after_two_rounds_by_group(repo: Path) -> None:
    fill(repo)
    c = str(change(repo))
    ev(repo, "review", c, "e", "--defect", "High:tokens:wrong blue")
    (change(repo) / "asks").mkdir()
    (change(repo) / "asks/e.png").write_bytes(b"x")
    screen(repo, "e", "--reference", "asks/e.png", "--capture", "asks/e.png")
    assert ev(repo, "sheet", c).returncode == 0
    text = (change(repo) / "verify/owner-sheet.md").read_text()
    assert "## auth" in text and "## pay" in text
    assert "| e | asks/e.png | asks/e.png | D1 High wrong blue |" in text and "accept / send back" in text
    assert "| a |" not in text and "| h |" not in text
