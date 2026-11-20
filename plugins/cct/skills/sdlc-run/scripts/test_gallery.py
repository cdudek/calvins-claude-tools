"""evidence.py gallery / gallery --import: the owner's one-page approval of the app's own screenshots."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

EVIDENCE = Path(__file__).resolve().parents[1] / "templates/scripts/evidence.py"
STATUS = Path(__file__).resolve().parent / "sdlc_status.py"
ID = "2026-11-20-leads"
PNG = b"\x89PNG\r\n\x1a\n"
ENTRIES = ["leads.list.empty", "leads.list.full", "leads.detail.open", "leads.detail.error"]


def ev(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(EVIDENCE), *args], cwd=repo, capture_output=True, text=True)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "sdlc.json").write_text("{}")
    ch = tmp_path / "changes" / ID
    (ch / "verify" / "shots").mkdir(parents=True)
    rows = [{"id": e, "route": f"/preview/{e}", "viewport": [1440, 900], "fixture": "leads-basic"} for e in ENTRIES]
    (ch / "screens.json").write_text(json.dumps(rows))
    for i, e in enumerate(ENTRIES):
        (ch / "verify" / "shots" / f"{e}.png").write_bytes(PNG + bytes([i]))
    return tmp_path


def ch(repo: Path) -> Path:
    return repo / "changes" / ID


def gallery(repo: Path) -> Path:
    out = ev(repo, "gallery", str(ch(repo)))
    assert out.returncode == 0, out.stderr
    return Path(out.stdout.strip().split()[-1])


def answers(repo: Path, **by_entry: str) -> Path:
    body = {"format": 1, "approvedBy": "Ana", "answers": {
        e: {"answer": a, "sha256": sha((ch(repo) / "verify" / "shots" / f"{e}.png").read_bytes())} for e, a in by_entry.items()}}  # fmt: skip
    path = repo / "answers.json"
    path.write_text(json.dumps(body))
    return path


def approved(repo: Path) -> dict:
    return json.loads((ch(repo) / "screens" / "approved.json").read_text())["entries"]


def test_gallery_is_one_offline_page_with_every_entry(repo: Path) -> None:
    html = gallery(repo).read_text()
    for e in ENTRIES:
        assert e in html and f"/preview/{e}" in html
    assert html.count("data:image/png;base64,") == len(ENTRIES)
    assert "http://" not in html and "https://" not in html
    assert "download answers" in html.lower()


def test_gallery_groups_by_screen(repo: Path) -> None:
    html = gallery(repo).read_text()
    assert "leads.list" in html and "leads.detail" in html
    assert html.index("leads.list.empty") < html.index("leads.detail.open")  # list screen first, as in screens.json


def test_gallery_marks_an_entry_with_no_shot(repo: Path) -> None:
    (ch(repo) / "verify" / "shots" / "leads.detail.error.png").unlink()
    assert "not captured" in gallery(repo).read_text()


def test_import_accept_copies_the_shot_and_records_the_hash(repo: Path) -> None:
    out = ev(repo, "gallery", str(ch(repo)), "--import", str(answers(repo, **{"leads.list.empty": "accept"})))
    assert out.returncode == 0, out.stderr
    shot = (ch(repo) / "verify" / "shots" / "leads.list.empty.png").read_bytes()
    assert (ch(repo) / "screens" / "leads.list.empty.png").read_bytes() == shot
    entry = approved(repo)["leads.list.empty"]
    assert entry["sha256"] == sha(shot) and entry["file"] == "screens/leads.list.empty.png"
    assert entry["approvedBy"] == "Ana" and len(entry["date"]) == 10
    assert json.loads((ch(repo) / "screens" / "approved.json").read_text())["format"] == 1


def test_import_send_back_reopens_and_never_silent(repo: Path) -> None:
    ev(repo, "gallery", str(ch(repo)), "--import", str(answers(repo, **{"leads.list.empty": "accept", "leads.list.full": "accept"})))
    out = ev(repo, "gallery", str(ch(repo)), "--import", str(answers(repo, **{"leads.list.empty": "send back"})))
    assert out.returncode == 0, out.stderr
    assert "reopened: leads.list.empty" in out.stdout
    assert set(approved(repo)) == {"leads.list.full"}  # the other approval stays


def test_import_refuses_an_answer_for_a_shot_that_changed_since_the_gallery(repo: Path) -> None:
    path = answers(repo, **{"leads.list.empty": "accept"})
    (ch(repo) / "verify" / "shots" / "leads.list.empty.png").write_bytes(PNG + b"new")
    out = ev(repo, "gallery", str(ch(repo)), "--import", str(path))
    assert out.returncode == 1 and "leads.list.empty" in out.stderr
    assert not (ch(repo) / "screens" / "approved.json").exists()


def test_import_refuses_an_entry_not_in_screens_json(repo: Path) -> None:
    path = answers(repo, **{"leads.list.empty": "accept"})
    body = json.loads(path.read_text())
    body["answers"]["../evil"] = {"answer": "accept", "sha256": "0" * 64}
    path.write_text(json.dumps(body))
    out = ev(repo, "gallery", str(ch(repo)), "--import", str(path))
    assert out.returncode == 1 and "../evil" in out.stderr
    assert "leads.list.empty" in approved(repo)  # the good answer still lands


def test_regenerating_the_gallery_keeps_every_approval(repo: Path) -> None:
    ev(repo, "gallery", str(ch(repo)), "--import", str(answers(repo, **{"leads.list.empty": "accept"})))
    before = (ch(repo) / "screens" / "approved.json").read_text()
    (ch(repo) / "verify" / "shots" / "leads.list.empty.png").write_bytes(PNG + b"changed")
    html = gallery(repo).read_text()
    assert (ch(repo) / "screens" / "approved.json").read_text() == before
    assert "changed since approval" in html


def status(repo: Path) -> str:
    return ev(repo, "status", str(ch(repo))).stdout.strip()


def test_status_counts(repo: Path) -> None:
    assert status(repo) == "screens: 0 of 4 approved · 0 changed since approval · 0 not captured"
    ev(repo, "gallery", str(ch(repo)), "--import", str(answers(repo, **{"leads.list.empty": "accept", "leads.list.full": "accept"})))
    (ch(repo) / "verify" / "shots" / "leads.list.full.png").write_bytes(PNG + b"changed")
    (ch(repo) / "verify" / "shots" / "leads.detail.open.png").unlink()
    assert status(repo) == "screens: 1 of 4 approved · 1 changed since approval · 1 not captured"


def test_sdlc_status_prints_the_line(repo: Path) -> None:
    sys.path.insert(0, str(STATUS.parent))
    sys.path.insert(0, str(EVIDENCE.parent))
    import sdlc_status

    assert sdlc_status.screens_line(ch(repo)).startswith("screens: 0 of 4 approved")
