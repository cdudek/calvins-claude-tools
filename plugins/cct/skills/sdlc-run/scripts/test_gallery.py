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
    (ch / "lock.json").write_text(json.dumps({"visual": "app", "criteria": {}}))
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


def test_status_uses_the_app_flow_only_when_the_lock_says_visual_app(repo: Path) -> None:
    (ch(repo) / "lock.json").write_text(json.dumps({"screens": "required", "criteria": {}}))  # a 3.24 lock
    assert "approved" not in status(repo)
    (ch(repo) / "lock.json").write_text(json.dumps({"visual": "app", "criteria": {}}))
    assert status(repo).startswith("screens: 0 of 4 approved")


def test_a_bare_change_id_resolves_through_changes_dir(repo: Path) -> None:
    out = ev(repo, "gallery", ID)
    assert out.returncode == 0, out.stderr
    assert (ch(repo) / "verify" / "gallery.html").is_file()


@pytest.mark.parametrize("bad", ["../evil", "a/b", "/etc/passwd"])
def test_gallery_and_import_refuse_an_id_capture_would_reject_before_touching_a_file(repo: Path, bad: str) -> None:
    rows = json.loads((ch(repo) / "screens.json").read_text())
    rows.append({"id": bad, "route": "/preview/x", "viewport": [800, 600], "fixture": "f"})
    (ch(repo) / "screens.json").write_text(json.dumps(rows))
    (ch(repo) / "verify" / "evil.png").write_bytes(PNG + b"outside")
    out = ev(repo, "gallery", str(ch(repo)))
    assert out.returncode == 1 and bad.split("/")[0] in (out.stdout + out.stderr)
    assert not (ch(repo) / "verify" / "gallery.html").exists()
    path = answers(repo, **{"leads.list.empty": "accept"})
    body = json.loads(path.read_text())
    body["answers"][bad] = {"answer": "accept", "sha256": sha(PNG + b"outside")}
    path.write_text(json.dumps(body))
    out = ev(repo, "gallery", str(ch(repo)), "--import", str(path))
    assert out.returncode == 1
    assert not (ch(repo) / "screens" / "approved.json").exists() and not (ch(repo) / "evil.png").exists()


def test_each_shot_is_read_once_so_the_page_shows_the_bytes_that_are_approved(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sys.path.insert(0, str(EVIDENCE.parent))
    import evidence

    reads: list[str] = []
    real = Path.read_bytes
    file = str(answers(repo, **{"leads.list.empty": "accept"}))  # the helper reads the shot too: before counting

    def counting(self: Path) -> bytes:
        if self.suffix == ".png":
            reads.append(self.name)
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", counting)
    shot = ch(repo) / "verify" / "shots" / "leads.list.empty.png"
    evidence.gallery_write(ch(repo), evidence.app_entries(ch(repo)))
    assert reads.count("leads.list.empty.png") == 1
    reads.clear()
    args = type("A", (), {"do_import": file, "by": ""})()
    evidence.gallery_import(args, ch(repo), evidence.app_entries(ch(repo)))
    assert reads.count("leads.list.empty.png") == 1 and shot.is_file()


def test_a_send_back_for_an_old_shot_does_not_revoke_a_newer_approval(repo: Path) -> None:
    old = repo / "old.json"
    old.write_text(answers(repo, **{"leads.list.empty": "send back"}).read_text())  # made from the shot as it was
    shot = ch(repo) / "verify" / "shots" / "leads.list.empty.png"
    shot.write_bytes(PNG + b"newer")
    ev(repo, "gallery", str(ch(repo)), "--import", str(answers(repo, **{"leads.list.empty": "accept"})))
    out = ev(repo, "gallery", str(ch(repo)), "--import", str(old))
    assert out.returncode == 1 and "leads.list.empty" in out.stderr
    assert "leads.list.empty" in approved(repo)


def test_two_imports_at_once_both_land(repo: Path) -> None:
    a = answers(repo, **{"leads.list.empty": "accept"})
    b = repo / "b.json"
    b.write_text(json.dumps({"format": 1, "approvedBy": "Bo", "answers": {
        "leads.list.full": {"answer": "accept", "sha256": sha((ch(repo) / "verify/shots/leads.list.full.png").read_bytes())}}}))  # fmt: skip
    procs = [subprocess.Popen([sys.executable, str(EVIDENCE), "gallery", str(ch(repo)), "--import", str(f)], cwd=repo) for f in (a, b)]
    assert [p.wait() for p in procs] == [0, 0]
    assert set(approved(repo)) == {"leads.list.empty", "leads.list.full"}
