"""evidence.py gallery: an optional read-only report of the app's screenshots (nobody approves a screen) and the status line."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import capture
import pytest

EVIDENCE = Path(__file__).resolve().parents[1] / "templates/scripts/evidence.py"
STATUS = Path(__file__).resolve().parent / "sdlc_status.py"
ID = "2026-11-20-leads"
PNG = b"\x89PNG\r\n\x1a\n"
ENTRIES = ["leads.list.empty", "leads.list.full", "leads.detail.open", "leads.detail.error"]


def ev(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "HOME": str(repo.parent / "home")}  # where the owner's transcripts are read
    return subprocess.run([sys.executable, str(EVIDENCE), *args], cwd=repo, capture_output=True, text=True, env=env)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "sdlc.json").write_text("{}")
    ch = tmp_path / "changes" / ID
    (ch / "verify" / "shots").mkdir(parents=True)
    rows = [{"id": e, "route": f"/preview/{e}", "viewport": [1440, 900], "fixture": "leads-basic"} for e in ENTRIES]
    (ch / "screens.json").write_text(json.dumps(rows))
    (ch / "lock.json").write_text(json.dumps({"visual": "app", "criteria": {}}))
    for i, e in enumerate(ENTRIES):
        (ch / "verify" / "shots" / f"{e}.png").write_bytes(PNG + bytes([i]))
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)  # the change has a first commit: an answer after it counts
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "change"], cwd=tmp_path, check=True)
    return tmp_path


def ch(repo: Path) -> Path:
    return repo / "changes" / ID


def gallery(repo: Path) -> Path:
    out = ev(repo, "gallery", str(ch(repo)))
    assert out.returncode == 0, out.stderr
    return Path(out.stdout.strip().split()[-1])


def status(repo: Path) -> str:
    return ev(repo, "status", str(ch(repo))).stdout.strip()


def baseline(repo: Path, *entries: str) -> None:
    """What the gate records after a passing comparison: the shot as the baseline and its sha256."""
    folder = ch(repo) / "screens"
    folder.mkdir(exist_ok=True)
    data = {}
    for e in entries:
        shot = (ch(repo) / "verify" / "shots" / f"{e}.png").read_bytes()
        (folder / f"{e}.png").write_bytes(shot)
        data[e] = {"sha256": sha(shot), "approvedBy": "comparison", "report": "r", "at": "2026-11-23"}
    (folder / "approved.json").write_text(json.dumps({"format": 2, "entries": data}))


def test_gallery_is_one_offline_read_only_page_with_every_entry(repo: Path) -> None:
    html = gallery(repo).read_text()
    for e in ENTRIES:
        assert e in html and f"/preview/{e}" in html
    assert html.count("data:image/png;base64,") == len(ENTRIES)
    assert "http://" not in html and "https://" not in html
    assert "<input" not in html and "download" not in html.lower() and "decides nothing" in html


def test_gallery_groups_by_screen(repo: Path) -> None:
    html = gallery(repo).read_text()
    assert "leads.list" in html and "leads.detail" in html
    assert html.index("leads.list.empty") < html.index("leads.detail.open")  # list screen first, as in screens.json


def test_gallery_marks_an_entry_with_no_shot(repo: Path) -> None:
    (ch(repo) / "verify" / "shots" / "leads.detail.error.png").unlink()
    assert "not captured" in gallery(repo).read_text()


def test_the_import_flag_is_gone(repo: Path) -> None:
    out = ev(repo, "gallery", str(ch(repo)), "--import", "answers.json")
    assert out.returncode != 0 and not (ch(repo) / "screens" / "approved.json").exists()


def test_status_counts(repo: Path) -> None:
    assert status(repo) == "screens: 0 of 4 with a baseline · 0 changed since baseline · 0 not captured"
    baseline(repo, "leads.list.empty", "leads.list.full")
    (ch(repo) / "verify" / "shots" / "leads.list.full.png").write_bytes(PNG + b"changed")
    (ch(repo) / "verify" / "shots" / "leads.detail.open.png").unlink()
    assert status(repo) == "screens: 1 of 4 with a baseline · 1 changed since baseline · 1 not captured"


def test_sdlc_status_prints_the_line(repo: Path) -> None:
    sys.path.insert(0, str(STATUS.parent))
    sys.path.insert(0, str(EVIDENCE.parent))
    import sdlc_status

    assert sdlc_status.screens_line(ch(repo)).startswith("screens: 0 of 4 with a baseline")


def test_status_uses_the_app_flow_only_when_the_lock_says_visual_app(repo: Path) -> None:
    (ch(repo) / "lock.json").write_text(json.dumps({"screens": "required", "criteria": {}}))  # a 3.24 lock
    assert "with a baseline" not in status(repo)
    (ch(repo) / "lock.json").write_text(json.dumps({"visual": "app", "criteria": {}}))
    assert status(repo).startswith("screens: 0 of 4 with a baseline")


@pytest.mark.parametrize("bad", ["../evil", "a/b", "/etc/passwd"])
def test_gallery_refuses_an_id_capture_would_reject_before_touching_a_file(repo: Path, bad: str) -> None:
    rows = json.loads((ch(repo) / "screens.json").read_text())
    rows.append({"id": bad, "route": "/preview/x", "viewport": [800, 600], "fixture": "f"})
    (ch(repo) / "screens.json").write_text(json.dumps(rows))
    out = ev(repo, "gallery", str(ch(repo)))
    assert out.returncode == 1 and bad.split("/")[0] in (out.stdout + out.stderr)
    assert not (ch(repo) / "verify" / "gallery.html").exists()
