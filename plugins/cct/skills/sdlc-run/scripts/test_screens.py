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
SHA = "a" * 40


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


def lock(repo: Path, **kv: object) -> None:
    (change(repo) / "lock.json").write_text(json.dumps(kv))


def rec(repo: Path, screen: str) -> dict:
    return json.loads((change(repo) / "screens" / f"{screen}.json").read_text())


def screen(repo: Path, name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return ev(repo, "screen", str(change(repo)), name, *args)


def review(repo: Path, name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return ev(repo, "review", str(change(repo)), name, *args)


def shot(repo: Path, name: str = "home.png", data: bytes = b"png") -> str:
    path = change(repo) / "verify/shots" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"verify/shots/{name}"


def make_done(repo: Path, name: str, status: str = "match", group: str = "") -> None:
    """A screen that earned `status`: reviewed with no defect, a full build sha and a capture of it."""
    assert review(repo, name).returncode == 0
    r = screen(repo, name, "--build", SHA, "--capture", shot(repo, f"{name}.png"), "--status", status,
               *(["--group", group] if group else []))  # fmt: skip
    assert r.returncode == 0, r.stderr


def asks(repo: Path, *names: str) -> None:
    for n in names:
        path = change(repo) / "asks" / n
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")


# one screen id, one file name


def test_the_writer_accepts_the_canonical_id_the_checker_demands(repo: Path) -> None:
    lock(repo, screens="required")
    asks(repo, "home.png")
    out = marks_check(repo)
    assert "ref:asks/home.png: missing screen record" in out.stdout
    sid = "ref:asks/home.png"
    assert screen(repo, sid, "--status", "open").returncode == 0
    files = [p.name for p in (change(repo) / "screens").glob("*.json")]
    assert len(files) == 1 and files[0].startswith("ref--asks--home-png-")
    assert marks_check(repo).returncode == 0, marks_check(repo).stdout


def test_a_bundle_yields_one_id_per_screen_not_one_per_bundle(repo: Path) -> None:
    lock(repo, screens="required")
    asks(repo, "export/index.html", "export/settings/index.html", "export/gallery.html")
    sys.path.insert(0, str(TPL))
    import marks

    ids = marks.screen_ids(change(repo))
    assert ids == ["bundle:asks/export/index", "bundle:asks/export/settings/index"]
    out = marks_check(repo).stdout
    assert "bundle:asks/export/index: missing screen record" in out
    assert "bundle:asks/export/settings/index: missing screen record" in out


# records are tracked, not ignored


def test_records_and_the_owner_sheet_live_outside_the_ignored_verify_folder(repo: Path) -> None:
    screen(repo, "home", "--status", "open")
    assert (change(repo) / "screens/home.json").is_file()
    assert not (change(repo) / "verify/screens").exists()
    ev(repo, "round", str(change(repo)), "home")
    ev(repo, "round", str(change(repo)), "home")
    ev(repo, "sheet", str(change(repo)))
    assert (change(repo) / "owner-sheet.md").is_file() and not (change(repo) / "verify/owner-sheet.md").exists()


def test_a_screen_record_holds_status_release_and_capture_hashes(repo: Path) -> None:
    lock(repo, designSystem={"name": "ds", "version": "1.0.0", "consumers": [{"path": "p", "pin": "^1", "resolved": "1.0.0"}]})
    path = shot(repo)
    assert review(repo, "home").returncode == 0
    r = screen(repo, "home", "--build", SHA, "--capture", path, "--state", "default", "--viewport", "1280",
               "--zoom", "100", "--group", "auth", "--status", "match")  # fmt: skip
    assert r.returncode == 0, r.stderr
    data = rec(repo, "home")
    assert data["format"] == 1 and data["status"] == "match" and data["group"] == "auth" and data["build"] == SHA
    assert data["designSystem"] and data["designSystem"] == data["reviewedRelease"]
    assert data["captures"] == [{"file": path, "sha256": hashlib.sha256(b"png").hexdigest(), "build": SHA,
                                 "state": "default", "viewport": "1280", "zoom": "100"}]  # fmt: skip


# done means reviewed and current


def test_match_needs_a_review_a_full_build_and_a_capture(repo: Path) -> None:
    assert "no review" in screen(repo, "home", "--status", "match").stderr
    review(repo, "home")
    assert "full build sha" in screen(repo, "home", "--status", "match", "--build", "abc").stderr
    assert "no capture of its build" in screen(repo, "home", "--status", "fixed", "--build", SHA).stderr
    assert rec(repo, "home")["status"] == "open"
    make_done(repo, "home", "fixed")


def test_an_open_high_or_medium_blocks_match_but_a_low_does_not(repo: Path) -> None:
    review(repo, "a", "--defect", "Medium:tokens:grey", "--defect", "Low:geometry:gap")
    screen(repo, "a", "--build", SHA, "--capture", shot(repo))
    r = screen(repo, "a", "--status", "match")
    assert r.returncode == 2 and "open High or Medium" in r.stderr
    review(repo, "a", "--tick", "D1")
    assert screen(repo, "a", "--status", "match").returncode == 0


def test_check_fails_a_hand_written_match_without_evidence(repo: Path) -> None:
    lock(repo, screens="required")
    screen(repo, "home", "--status", "open")
    path = change(repo) / "screens/home.json"
    data = json.loads(path.read_text())
    data["status"] = "match"
    path.write_text(json.dumps(data))
    assert "home: status match but it has no review" in marks_check(repo).stdout


def test_accepted_by_owner_needs_the_recorded_answer(repo: Path) -> None:
    r = screen(repo, "home", "--status", "accepted-by-owner")
    assert r.returncode == 2 and "owner's accept is not recorded" in r.stderr


def test_a_re_approved_design_system_release_makes_old_matches_not_done(repo: Path) -> None:
    ds = {"name": "ds", "version": "1.0.0", "consumers": [{"path": "p", "pin": "^1", "resolved": "1.0.0"}]}
    lock(repo, screens="required", designSystem=ds)
    make_done(repo, "home")
    assert ev(repo, "status", str(change(repo))).stdout.startswith("screens: 1 of 1 done")
    assert marks_check(repo).returncode == 0
    ds["consumers"][0]["resolved"] = "1.1.0"
    lock(repo, screens="required", designSystem=ds)
    assert ev(repo, "status", str(change(repo))).stdout.startswith("screens: 0 of 1 done")
    assert "another design-system release" in marks_check(repo).stdout
    review(repo, "home")
    screen(repo, "home", "--build", "b" * 40, "--capture", shot(repo, "n.png", b"n"))
    assert marks_check(repo).returncode == 0, marks_check(repo).stdout


def test_the_round_budget_follows_the_approved_release_not_a_flag(repo: Path) -> None:
    lock(repo, designSystem={"name": "ds", "version": "1", "consumers": []})
    ev(repo, "round", str(change(repo)), "home")
    ev(repo, "round", str(change(repo)), "home")
    assert rec(repo, "home")["rounds"] == 2
    assert screen(repo, "home", "--design-system", "r9").returncode != 0  # no free-text reset
    assert rec(repo, "home")["rounds"] == 2
    lock(repo, designSystem={"name": "ds", "version": "2", "consumers": []})
    ev(repo, "round", str(change(repo)), "home")
    assert rec(repo, "home")["rounds"] == 1


# the frozen list has a baseline


def test_the_first_review_snapshot_catches_a_removed_or_added_first_defect(repo: Path) -> None:
    lock(repo, screens="required")
    review(repo, "home", "--defect", "Medium:tokens:grey", "--defect", "Low:geometry:gap")
    assert rec(repo, "home")["firstReview"][0]["text"] == "grey"
    assert marks_check(repo).returncode == 0
    path = change(repo) / "screens/home.json"
    data = json.loads(path.read_text())
    kept = data["defects"]
    data["defects"] = kept[1:]
    path.write_text(json.dumps(data))
    assert "home: first-review defect D1 was removed or changed" in marks_check(repo).stdout
    data["defects"] = kept + [{"id": "D3", "severity": "Low", "layer": "x", "text": "t", "build": "", "open": True, "added": "first"}]
    path.write_text(json.dumps(data))
    assert "D3 says it came from the first review" in marks_check(repo).stdout


# strict means strict


def test_check_fails_a_third_round_a_late_medium_and_a_changed_capture(repo: Path) -> None:
    lock(repo, screens="required")
    path = shot(repo, "home.png", b"one")
    screen(repo, "home", "--status", "open", "--capture", path)
    assert marks_check(repo).returncode == 0, marks_check(repo).stdout
    rp = change(repo) / "screens/home.json"
    data = json.loads(rp.read_text())
    data["defects"] = [{"id": "D1", "severity": "Medium", "layer": "copy", "text": "t",
                        "build": "x", "open": True, "added": "later"}]  # fmt: skip
    data["rounds"] = 3
    rp.write_text(json.dumps(data))
    out = marks_check(repo)
    assert out.returncode == 1
    assert "home: defect D1 added after the first review" in out.stdout
    assert "send the side-by-side list to the owner" in out.stdout
    data.update(defects=[], rounds=0)
    rp.write_text(json.dumps(data))
    (change(repo) / path).write_bytes(b"two")
    assert f"capture {path} does not match its recorded sha256" in marks_check(repo).stdout


def test_strict_checks_the_expected_set_even_when_a_ledger_exists(repo: Path) -> None:
    lock(repo, screens="required")
    asks(repo, "home.png")
    (change(repo) / "marks.json").write_text('{"rows": []}')
    out = marks_check(repo).stdout
    assert "ref:asks/home.png: missing screen record" in out


def test_an_unreadable_lock_fails_the_check(repo: Path) -> None:
    (change(repo) / "marks.json").write_text('{"rows": []}')
    (change(repo) / "lock.json").write_text("{not json")
    out = marks_check(repo)
    assert out.returncode == 1 and "lock.json cannot be read" in out.stdout


def test_a_lenient_change_ignores_screen_rules(repo: Path) -> None:
    (change(repo) / "marks.json").write_text('{"rows": []}')
    screen(repo, "home", "--status", "open")
    path = change(repo) / "screens/home.json"
    data = json.loads(path.read_text())
    data["rounds"] = 9
    path.write_text(json.dumps(data))
    assert marks_check(repo).returncode == 0


# captures, per cell


def test_two_captures_of_one_cell_must_agree_even_across_calls(repo: Path) -> None:
    lock(repo, screens="required")
    a, b = shot(repo, "a.png", b"1"), shot(repo, "b.png", b"1")
    screen(repo, "home", "--status", "open", "--build", SHA, "--capture", a)
    screen(repo, "home", "--capture", b)
    assert marks_check(repo).returncode == 0
    (change(repo) / b).write_bytes(b"2")
    screen(repo, "home", "--capture", b)  # a separate recapture keeps the first one to compare
    assert "home: unstable: captures of the same build, state, viewport and zoom differ" in marks_check(repo).stdout


def test_different_cells_may_differ(repo: Path) -> None:
    lock(repo, screens="required")
    a, b = shot(repo, "a.png", b"1"), shot(repo, "b.png", b"2")
    screen(repo, "home", "--status", "open", "--capture", a, "--viewport", "1280")
    screen(repo, "home", "--capture", b, "--viewport", "390")
    assert marks_check(repo).returncode == 0, marks_check(repo).stdout


# status


def fill(repo: Path) -> None:
    rows = [("a", "match", 0, "auth"), ("b", "fixed", 1, "auth"), ("c", "ruled-out", 0, ""),
            ("e", "open", 2, "auth"), ("f", "open", 2, "pay"),
            ("g", "waits-on-design-system", 0, ""), ("h", "open", 1, ""), ("i", "open", 0, "")]  # fmt: skip
    for name, status, rounds, group in rows:
        if status in ("match", "fixed"):
            make_done(repo, name, status, group)
        else:
            screen(repo, name, "--status", status, *(["--group", group] if group else []))
        for _ in range(rounds):
            ev(repo, "round", str(change(repo)), name)


def test_status_counts_are_mutually_exclusive(repo: Path) -> None:
    fill(repo)
    out = ev(repo, "status", str(change(repo))).stdout.strip()
    assert out == "screens: 3 of 8 done · 2 wait on you · 1 wait on the design system · 2 open"


def test_status_counts_unstarted_screens_as_open_and_ignores_legacy_records(repo: Path) -> None:
    lock(repo, screens="required")
    asks(repo, "a.png", "b.png", "c.png")
    make_done(repo, "ref:asks/a.png")
    legacy = change(repo) / "screens/old.json"
    legacy.write_text(json.dumps({"screen": "old", "shot": "x", "keys": {}}))  # a pre-3.23 `record DIR` file
    out = ev(repo, "status", str(change(repo)))
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "screens: 1 of 3 done · 0 wait on you · 0 wait on the design system · 2 open"


def test_sdlc_status_prints_the_screens_line_and_nothing_without_records(repo: Path) -> None:
    assert ev(repo, "status", str(change(repo))).stdout == ""
    fill(repo)
    sys.path.insert(0, str(STATUS.parent))
    import sdlc_status

    assert sdlc_status.screens_line(change(repo)).startswith("screens: 3 of 8 done")


# owner sheet


def test_the_owner_sheet_lists_screens_left_after_two_rounds_by_group(repo: Path) -> None:
    fill(repo)
    c = str(change(repo))
    ev(repo, "review", c, "e", "--defect", "High:tokens:wrong blue")
    asks(repo, "e.png")
    screen(repo, "e", "--reference", "asks/e.png", "--capture", "asks/e.png")
    assert ev(repo, "sheet", c).returncode == 0
    text = (change(repo) / "owner-sheet.md").read_text()
    assert "## auth" in text and "## pay" in text
    assert "| e | asks/e.png | asks/e.png | D1 High wrong blue |" in text and "accept / send back" in text
    assert "| a |" not in text and "| h |" not in text


def test_regenerating_the_sheet_keeps_answers_and_import_records_them(repo: Path) -> None:
    fill(repo)
    c = str(change(repo))
    ev(repo, "sheet", c)
    path = change(repo) / "owner-sheet.md"
    path.write_text(path.read_text().replace("| e |  |  |  |  |", "| e |  |  |  | accept |").replace("| f |  |  |  |  |", "| f |  |  |  | send back |"))
    assert "| accept |" in path.read_text()
    ev(repo, "sheet", c)  # regenerate before importing
    assert "| accept |" in path.read_text() and "| send back |" in path.read_text()
    assert ev(repo, "sheet", c, "--import").returncode == 0
    assert rec(repo, "e")["status"] == "accepted-by-owner" and rec(repo, "e")["ownerDecision"] == "accept"
    assert rec(repo, "f")["status"] == "open" and rec(repo, "f")["rounds"] == 0
    r = ev(repo, "sheet", c)  # e left the list but its answer was imported: no refusal
    assert r.returncode == 0, r.stderr
    assert "| e |" not in path.read_text()


def test_the_sheet_refuses_to_drop_an_answer_that_was_not_imported(repo: Path) -> None:
    fill(repo)
    c = str(change(repo))
    ev(repo, "sheet", c)
    path = change(repo) / "owner-sheet.md"
    path.write_text(path.read_text().replace("| e |  |  |  |  |", "| e |  |  |  | accept |"))
    screen(repo, "e", "--status", "waits-on-design-system")  # e leaves the list before the import
    r = ev(repo, "sheet", c)
    assert r.returncode == 1 and "not imported yet" in r.stderr


# parallel writers


def test_two_parallel_rounds_both_count(repo: Path) -> None:
    c = str(change(repo))
    procs = [subprocess.Popen([sys.executable, str(EVIDENCE), "round", c, "home"]) for _ in range(8)]
    assert all(p.wait() == 0 for p in procs)
    assert rec(repo, "home")["rounds"] == 8
    assert not list((change(repo) / "screens").glob(".*.tmp"))
