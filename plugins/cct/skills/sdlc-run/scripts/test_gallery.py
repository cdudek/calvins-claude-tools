"""evidence.py gallery / gallery --import: the owner's one-page approval of the app's own screenshots."""

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

from test_capture import owner_answers

EVIDENCE = Path(__file__).resolve().parents[1] / "templates/scripts/evidence.py"
STATUS = Path(__file__).resolve().parent / "sdlc_status.py"
ID = "2026-11-20-leads"
PNG = b"\x89PNG\r\n\x1a\n"
ENTRIES = ["leads.list.empty", "leads.list.full", "leads.detail.open", "leads.detail.error"]


def ev(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "HOME": str(repo.parent / "home")}  # where the owner's transcripts are read
    return subprocess.run([sys.executable, str(EVIDENCE), *args], cwd=repo, capture_output=True, text=True, env=env)


def imp(repo: Path, answers_file: str) -> subprocess.CompletedProcess[str]:
    """The import as the flow runs it: it asks for the owner's dialog, the owner answers it, the agent runs it again."""
    first = ev(repo, "gallery", str(ch(repo)), "--import", answers_file)
    if not (asked := re.search(r"finding (screens-\w+):", first.stderr)):
        return first
    owner_answers(repo, asked[1])
    return ev(repo, "gallery", str(ch(repo)), "--import", answers_file)


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
    out = imp(repo, str(answers(repo, **{"leads.list.empty": "accept"})))
    assert out.returncode == 0, out.stderr
    shot = (ch(repo) / "verify" / "shots" / "leads.list.empty.png").read_bytes()
    assert (ch(repo) / "screens" / "leads.list.empty.png").read_bytes() == shot
    entry = approved(repo)["leads.list.empty"]
    assert entry["sha256"] == sha(shot) and entry["file"] == "screens/leads.list.empty.png"
    assert entry["approvedBy"] == "Ana" and len(entry["date"]) == 10
    assert json.loads((ch(repo) / "screens" / "approved.json").read_text())["format"] == 1


def test_import_send_back_reopens_and_never_silent(repo: Path) -> None:
    imp(repo, str(answers(repo, **{"leads.list.empty": "accept", "leads.list.full": "accept"})))
    out = imp(repo, str(answers(repo, **{"leads.list.empty": "send back"})))
    assert out.returncode == 0, out.stderr
    assert "reopened: leads.list.empty" in out.stdout
    assert set(approved(repo)) == {"leads.list.full"}  # the other approval stays


def test_import_refuses_an_answer_for_a_shot_that_changed_since_the_gallery(repo: Path) -> None:
    path = answers(repo, **{"leads.list.empty": "accept"})
    (ch(repo) / "verify" / "shots" / "leads.list.empty.png").write_bytes(PNG + b"new")
    out = imp(repo, str(path))
    assert out.returncode == 1 and "leads.list.empty" in out.stderr
    assert not (ch(repo) / "screens" / "approved.json").exists()


def test_import_refuses_an_entry_not_in_screens_json(repo: Path) -> None:
    path = answers(repo, **{"leads.list.empty": "accept"})
    body = json.loads(path.read_text())
    body["answers"]["../evil"] = {"answer": "accept", "sha256": "0" * 64}
    path.write_text(json.dumps(body))
    out = imp(repo, str(path))
    assert out.returncode == 1 and "../evil" in out.stderr
    assert "leads.list.empty" in approved(repo)  # the good answer still lands


def test_regenerating_the_gallery_keeps_every_approval(repo: Path) -> None:
    imp(repo, str(answers(repo, **{"leads.list.empty": "accept"})))
    before = (ch(repo) / "screens" / "approved.json").read_text()
    (ch(repo) / "verify" / "shots" / "leads.list.empty.png").write_bytes(PNG + b"changed")
    html = gallery(repo).read_text()
    assert (ch(repo) / "screens" / "approved.json").read_text() == before
    assert "changed since approval" in html


def status(repo: Path) -> str:
    return ev(repo, "status", str(ch(repo))).stdout.strip()


def test_status_counts(repo: Path) -> None:
    assert status(repo) == "screens: 0 of 4 approved · 0 changed since approval · 0 not captured"
    imp(repo, str(answers(repo, **{"leads.list.empty": "accept", "leads.list.full": "accept"})))
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
    out = imp(repo, str(path))
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
    imp(repo, str(answers(repo, **{"leads.list.empty": "accept"})))
    out = imp(repo, str(old))
    assert out.returncode == 1 and "leads.list.empty" in out.stderr
    assert "leads.list.empty" in approved(repo)


def test_two_imports_at_once_both_land(repo: Path) -> None:
    a = answers(repo, **{"leads.list.empty": "accept"})
    b = repo / "b.json"
    b.write_text(json.dumps({"format": 1, "approvedBy": "Bo", "answers": {
        "leads.list.full": {"answer": "accept", "sha256": sha((ch(repo) / "verify/shots/leads.list.full.png").read_bytes())}}}))  # fmt: skip
    for e in ("leads.list.empty", "leads.list.full"):
        owner_answers(repo, capture.approval_id([[e, sha((ch(repo) / "verify/shots" / f"{e}.png").read_bytes())]]))
    env = {**os.environ, "HOME": str(repo.parent / "home")}
    procs = [subprocess.Popen([sys.executable, str(EVIDENCE), "gallery", str(ch(repo)), "--import", str(f)], cwd=repo, env=env) for f in (a, b)]
    assert [p.wait() for p in procs] == [0, 0]
    assert set(approved(repo)) == {"leads.list.empty", "leads.list.full"}


# ---------------------------------------------------------------- the owner approves, never the agent


def test_an_import_nobody_answered_writes_nothing_and_prints_the_dialog(repo: Path) -> None:
    out = ev(repo, "gallery", str(ch(repo)), "--import", str(answers(repo, **{"leads.list.empty": "accept", "leads.list.full": "accept"})))
    assert out.returncode == 1
    assert "AskUserQuestion" in out.stderr and "Approve screens" in out.stderr
    assert re.search(r"Change 2026-11-20-leads, finding screens-\w{16}: Approve these 2 screens\? ", out.stderr)
    assert not (ch(repo) / "screens").exists()


def test_a_hold_or_another_batch_does_not_approve_this_one(repo: Path) -> None:
    path = str(answers(repo, **{"leads.list.empty": "accept"}))
    asked = re.search(r"finding (screens-\w+):", ev(repo, "gallery", str(ch(repo)), "--import", path).stderr)[1]
    owner_answers(repo, asked, label="Hold")
    other = capture.approval_id([["leads.list.full", sha(PNG + b"\x01")]])
    owner_answers(repo, other, n=2)  # a yes to some other batch
    out = ev(repo, "gallery", str(ch(repo)), "--import", path)
    assert out.returncode == 1 and not (ch(repo) / "screens").exists()
    owner_answers(repo, asked, n=3)
    assert ev(repo, "gallery", str(ch(repo)), "--import", path).returncode == 0
    assert approved(repo)["leads.list.empty"]["decision"] == asked


def test_the_batch_is_recorded_so_the_gate_can_check_it(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(repo.parent / "home"))
    imp(repo, str(answers(repo, **{"leads.list.empty": "accept"})))
    data = json.loads((ch(repo) / "screens" / "approved.json").read_text())
    bid = approved(repo)["leads.list.empty"]["decision"]
    assert data["batches"] == {bid: [["leads.list.empty", approved(repo)["leads.list.empty"]["sha256"]]]}
    assert capture.uncovered(ch(repo), approved(repo)) == []  # the owner's answer covers it
    assert capture.uncovered(ch(repo), {**approved(repo), "leads.list.full": approved(repo)["leads.list.empty"]})  # an entry the batch lacks


def test_a_send_back_needs_the_owners_answer_too(repo: Path) -> None:
    imp(repo, str(answers(repo, **{"leads.list.empty": "accept"})))
    out = ev(repo, "gallery", str(ch(repo)), "--import", str(answers(repo, **{"leads.list.empty": "send back"})))
    assert out.returncode == 1 and "AskUserQuestion" in out.stderr
    assert "leads.list.empty" in approved(repo) and (ch(repo) / "screens/leads.list.empty.png").is_file()
    assert imp(repo, str(answers(repo, **{"leads.list.empty": "send back"}))).returncode == 0
    assert "leads.list.empty" not in approved(repo)


def test_an_old_batch_cannot_undo_a_later_send_back(repo: Path) -> None:
    (repo / "first.json").write_text(answers(repo, **{"leads.list.empty": "accept"}).read_text())  # kept: `answers` reuses its file
    first = str(repo / "first.json")
    imp(repo, first)
    imp(repo, str(answers(repo, **{"leads.list.empty": "send back"})))
    assert "leads.list.empty" not in approved(repo)
    out = ev(repo, "gallery", str(ch(repo)), "--import", first)  # the owner's old yes still stands in the transcript
    assert out.returncode == 1 and "send back" in out.stderr and "new batch" in out.stderr
    assert "leads.list.empty" not in approved(repo)
    shot = ch(repo) / "verify/shots/leads.list.empty.png"
    shot.write_bytes(shot.read_bytes() + b"x")  # a new shot is a new batch, and it takes a new answer
    assert imp(repo, str(answers(repo, **{"leads.list.empty": "accept"}))).returncode == 0
    assert "leads.list.empty" in approved(repo)


def test_every_decision_is_logged_in_order_with_its_batch(repo: Path) -> None:
    imp(repo, str(answers(repo, **{"leads.list.empty": "accept"})))
    imp(repo, str(answers(repo, **{"leads.list.empty": "send back"})))
    log = json.loads((ch(repo) / "screens/approved.json").read_text())["log"]
    assert [(r["entry"], r["answer"]) for r in log] == [("leads.list.empty", "accept"), ("leads.list.empty", "send-back")]
    assert all(r["batch"].startswith("screens-") and r["time"] for r in log) and log[0]["batch"] != log[1]["batch"]


# --- 3.26.0: the design is binding for what exists ---------------------------------------------------

BOARD = PNG + b"board"


def with_design(repo: Path, deviates: str = "") -> None:
    """3 boards: b1 (image) maps leads.list.empty, b2 (no image) maps leads.list.full, b3 is dropped; an optional deviation."""
    change = ch(repo)
    (change / "asks" / "design").mkdir(parents=True)
    (change / "asks" / "design" / "b1.png").write_bytes(BOARD)
    (change / "design.json").write_text(json.dumps({
        "source": "https://design.example/file/1",
        "boards": [{"id": "b1", "name": "Leads empty", "image": "asks/design/b1.png"}, {"id": "b2", "name": "Leads full"}, {"id": "b3", "name": "Old"}],
        "dropped": [{"board": "b3", "reason": "replaced by the detail panel"}]}))  # fmt: skip
    rows = json.loads((change / "screens.json").read_text())
    rows[0]["design"], rows[1]["design"] = ["b1"], ["b2"]
    if deviates:
        rows[0]["deviates"] = deviates
    (change / "screens.json").write_text(json.dumps(rows))


def test_the_gallery_shows_the_board_next_to_the_app_the_deviation_and_the_counts(repo: Path) -> None:
    with_design(repo, "no filter bar: the list has one column less")
    page = gallery(repo).read_text()
    assert "3 boards · 2 mapped · 1 dropped · 1 deviations" in page
    assert "Deviates from the design:</b> no filter bar: the list has one column less" in page
    assert base64.b64encode(BOARD).decode() in page  # the board image is embedded, the file stays single and offline
    assert 'Leads full</b> (b2), no image: <a href="https://design.example/file/1">source</a>' in page


def test_a_deviation_cannot_be_approved_in_bulk(repo: Path) -> None:
    with_design(repo, "no filter bar")
    plain = answers(repo, **{"leads.list.empty": "accept"})
    res = ev(repo, "gallery", str(ch(repo)), "--import", str(plain))
    assert res.returncode == 1 and "leads.list.empty: it deviates from the design" in res.stderr
    assert not (ch(repo) / "screens" / "approved.json").exists() or "leads.list.empty" not in approved(repo)
    tag = capture.deviation_tag("no filter bar")
    body = json.loads(plain.read_text())
    body["answers"]["leads.list.empty"]["deviation"] = capture.deviation_tag("another text")
    plain.write_text(json.dumps(body))
    assert "it deviates from the design" in ev(repo, "gallery", str(ch(repo)), "--import", str(plain)).stderr  # the text it names must be this one
    body["answers"]["leads.list.empty"]["deviation"] = tag
    plain.write_text(json.dumps(body))
    first = ev(repo, "gallery", str(ch(repo)), "--import", str(plain))
    assert first.returncode == 1 and "(1 with a deviation from the design, each accepted by name)" in first.stderr  # the dialog says how many
    assert imp(repo, str(plain)).returncode == 0 and set(approved(repo)) == {"leads.list.empty"}


def test_a_deviation_added_after_the_approval_needs_the_owner_again(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(repo.parent / "home"))
    with_design(repo)
    assert imp(repo, str(answers(repo, **{"leads.list.empty": "accept"}))).returncode == 0
    import marks

    marks._ANSWERS.clear()
    assert capture.uncovered(ch(repo), approved(repo)) == []
    rows = json.loads((ch(repo) / "screens.json").read_text())
    rows[0]["deviates"] = "added by the build"
    (ch(repo) / "screens.json").write_text(json.dumps(rows))
    left = capture.uncovered(ch(repo), approved(repo))
    assert any("leads.list.empty: no recorded batch of an owner approval holds it with its current board mapping and deviation" in p for p in left)


def test_the_status_line_counts_the_design(repo: Path) -> None:
    with_design(repo, "x")
    out = ev(repo, "status", str(ch(repo)))
    assert out.stdout.splitlines()[-1] == "design: 3 boards · 2 mapped · 1 dropped · 1 deviations", out.stdout


def test_the_decision_log_is_a_chain_and_a_spent_or_trimmed_log_is_refused(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(repo.parent / "home"))
    imp(repo, str(answers(repo, **{"leads.list.empty": "accept"})))
    old = json.loads((ch(repo) / "screens/approved.json").read_text())
    imp(repo, str(answers(repo, **{"leads.list.empty": "send back"})))
    log = json.loads((ch(repo) / "screens/approved.json").read_text())["log"]
    assert all(r["hash"] and "prev" in r and "lock" in r for r in log) and capture.chain_problems(log, log[-1]["hash"]) == []
    import marks

    marks._ANSWERS.clear()
    # the send back is removed and the old entry put back: a later send back spent that batch
    (ch(repo) / "screens/approved.json").write_text(json.dumps({**old, "log": log, "head": log[-1]["hash"]}))
    assert any("spent by a later send back" in p for p in capture.uncovered(ch(repo), approved(repo)))
    # a log trimmed to the accept: the file's head no longer matches, and a rewritten entry breaks the chain
    assert any("entries were removed" in p for p in capture.chain_problems(log[:1], log[-1]["hash"]))
    rewritten = [{**log[0], "answer": "send-back"}, log[1]]
    assert any("was changed" in p for p in capture.chain_problems(rewritten, log[-1]["hash"]))
    assert capture.chain_problems([{"entry": "x", "answer": "accept", "batch": "b"}], None) == []  # a 3.25 log has no hashes: read as it is


def test_a_remapped_screen_needs_a_new_owner_answer_and_shows_needs_review(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import marks

    monkeypatch.setenv("HOME", str(repo.parent / "home"))
    with_design(repo)
    assert imp(repo, str(answers(repo, **{"leads.list.empty": "accept"}))).returncode == 0
    marks._ANSWERS.clear()
    assert capture.uncovered(ch(repo), approved(repo)) == []
    rows = json.loads((ch(repo) / "screens.json").read_text())
    rows[0]["design"] = ["b2"]  # the same screen and pixels, another board
    (ch(repo) / "screens.json").write_text(json.dumps(rows))
    assert any("current board mapping" in p for p in capture.uncovered(ch(repo), approved(repo)))
    state = ev(repo, "status", str(ch(repo))).stdout
    assert "screens: 0 of 4 approved · 1 changed since approval" in state  # the status counts it as not approved
    assert "needs review" in gallery(repo).read_text()
    # a board image that changed after the owner saw it changes the binding too
    rows[0]["design"] = ["b1"]
    (ch(repo) / "screens.json").write_text(json.dumps(rows))
    assert capture.uncovered(ch(repo), approved(repo)) == []
    (ch(repo) / "asks" / "design" / "b1.png").write_bytes(BOARD + b"2")
    assert any("current board mapping" in p for p in capture.uncovered(ch(repo), approved(repo)))


def test_a_board_named_without_a_design_json_is_a_problem_and_hashes_bind_record_boundaries(repo: Path) -> None:
    rows = [{"id": "a", "route": "/a", "viewport": [1, 1], "fixture": "f", "design": ["b9"]}]
    assert capture.design_problems(ch(repo), rows) == ["screens.json entry a names board b9, but the change has no design.json"]
    one = {"boards": [{"id": "b1", "name": "x"}], "dropped": [{"board": "b1", "reason": "a\nb2 c"}]}
    two = {"boards": [{"id": "b1", "name": "x"}], "dropped": [{"board": "b1", "reason": "a"}, {"board": "b2", "reason": "c"}]}
    assert capture.inventory_id(one) != capture.inventory_id(two)
    assert capture.approval_id([["a", "b c"]]) != capture.approval_id([["a b", "c"]])


def test_a_kept_older_capture_py_is_refused_never_stubbed(repo: Path, tmp_path: Path) -> None:
    """A capture.py without a check (link, replayed, image_problems ...) cannot be stood in for: the command stops and
    names the missing function, with or without a design. Only the presentation helpers may be stubbed."""
    env = {**os.environ, "HOME": str(repo.parent / "home")}
    checks = ["binding_tag", "deviation_tag", "lock_sha", "image_problems", "link", "replayed", "board_file"]
    for gone in [*checks, "design_problems"]:
        old = tmp_path / f"old-{gone}"
        old.mkdir()
        src = (EVIDENCE.parent / "capture.py").read_text()
        assert f"def {gone}(" in src
        (old / "capture.py").write_text(src.replace(f"def {gone}(", f"def _gone_{gone}("))
        for name in ("evidence.py", "marks.py"):
            (old / name).write_bytes((EVIDENCE.parent / name).read_bytes())
        out = subprocess.run([sys.executable, str(old / "evidence.py"), "gallery", str(ch(repo))], cwd=repo, capture_output=True, text=True, env=env)
        assert out.returncode == 1 and f"`{gone}`" in out.stderr and "adopt --migrate" in out.stderr, (gone, out.stderr)
    gallery(repo)  # the current capture.py: no refusal


def _chained(n: int) -> list[dict]:
    log: list[dict] = []
    for i in range(n):
        log.append(capture.link(log, {"entry": f"e{i}", "answer": "accept", "batch": "b"}, "sha"))
    return log


def test_a_3_26_log_refuses_unhashed_entries_a_mixed_log_and_a_head_that_is_not_the_last_entry() -> None:
    plain = [{"entry": "x", "answer": "accept", "batch": "b"}]
    assert capture.chain_problems(plain, None, strict=True)  # nothing is hashed: the whole log is an agent's text
    assert capture.chain_problems(plain, None) == []  # a log before 3.26 keeps its path
    log = _chained(2)
    assert capture.chain_problems(log, log[-1]["hash"], strict=True) == []
    assert capture.chain_problems([], None, strict=True) == [] and capture.chain_problems([], "", strict=True) == []
    assert capture.chain_problems(log + plain, log[-1]["hash"], strict=True)  # hashed then unhashed
    assert capture.chain_problems(plain + log, log[-1]["hash"], strict=True)  # unhashed then hashed
    assert capture.chain_problems([], "forged", strict=True)  # a head with no entries
    assert any("removed" in p for p in capture.chain_problems(plain, "forged", strict=True))  # head vs last, nothing hashed


def test_the_gate_reads_the_log_strictly_when_the_lock_is_3_26_and_loosely_before(repo: Path) -> None:
    approved_json = ch(repo) / "screens" / "approved.json"
    approved_json.parent.mkdir(exist_ok=True)
    entry = {"sha256": "x", "decision": "b"}
    approved_json.write_text(json.dumps({"format": 1, "entries": {"leads.list.empty": entry}, "batches": {}, "log": [{"entry": "leads.list.empty", "answer": "accept", "batch": "b"}]}))
    old = capture.uncovered(ch(repo), {"leads.list.empty": entry})
    assert not any(p.startswith("decision log") for p in old)  # locked before 3.26: read as it is
    (ch(repo) / "lock.json").write_text(json.dumps({"visual": "app", "criteria": {}, "design": "none"}))
    assert any(p.startswith("decision log") for p in capture.uncovered(ch(repo), {"leads.list.empty": entry}))


@pytest.mark.parametrize("how", ["absolute", "parent", "symlink", "symlinked-folder"])
def test_a_board_image_outside_the_change_is_neither_hashed_nor_embedded(tmp_path: Path, how: str) -> None:
    change = tmp_path / "changes" / "c1"
    (change / "asks" / "design").mkdir(parents=True)
    secret = tmp_path / "secret.png"
    secret.write_bytes(PNG + b"secret")
    inside = change / "asks" / "design" / "ok.png"
    inside.write_bytes(PNG + b"ok")
    image = {"absolute": str(secret), "parent": "../../secret.png", "symlink": "asks/design/link.png", "symlinked-folder": "asks/out/secret.png"}[how]
    if how == "symlink":
        (change / "asks" / "design" / "link.png").symlink_to(secret)
    if how == "symlinked-folder":
        (change / "asks" / "out").symlink_to(tmp_path)
    design = {"source": "x", "boards": [{"id": "b1", "name": "B", "image": image}, {"id": "b2", "name": "C", "image": "asks/design/ok.png"}]}
    (change / "design.json").write_text(json.dumps(design))
    assert capture.board_digest(change, design, "b1") == ""
    assert capture.image_digests(change) == {"b1": "", "b2": sha(PNG + b"ok")}
    entries = [{"id": "s", "design": ["b1", "b2"]}]
    assert any("board b1" in p and "image" in p for p in capture.design_problems(change, entries))


def test_a_lock_of_3_26_0_without_a_design_reads_the_log_strictly_through_the_head_it_always_wrote(repo: Path) -> None:
    approved_json = ch(repo) / "screens" / "approved.json"
    approved_json.parent.mkdir(exist_ok=True)
    entry = {"sha256": "x", "decision": "b"}
    plain = [{"entry": "leads.list.empty", "answer": "accept", "batch": "b"}]
    body = {"format": 1, "entries": {"leads.list.empty": entry}, "batches": {}, "log": plain}
    approved_json.write_text(json.dumps({**body, "head": ""}))  # 3.26.0 wrote `head` for every app change, `design` or not
    assert any(p.startswith("decision log") for p in capture.uncovered(ch(repo), {"leads.list.empty": entry}))
    approved_json.write_text(json.dumps(body))  # a 3.25 file has no head: it keeps its path
    assert not any(p.startswith("decision log") for p in capture.uncovered(ch(repo), {"leads.list.empty": entry}))
