"""pass_proof.py: the one key, the one reader, and the reader's mode (the installed writer's version)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "templates" / "hooks"))
import pass_proof  # noqa: E402

ID = "2026-11-01-widget"
SHA = "a" * 40


def _git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    return subprocess.run(["git", *ident, *args], cwd=repo, check=True, env=env, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "verify_gate.py").write_text("RECEIPT_FORMAT = 2\n")
    (tmp_path / "f").write_text("x")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def _record(repo: Path, **over: object) -> dict:
    sha = _git(repo, "rev-parse", "HEAD")
    data = {
        "scope": "milestone", "change": ID, "key": "milestone-1", "milestone": 1, "owner": "project/p",
        "sha": sha, "verdict": "pass", "result": f"VERIFY PASS milestone {ID} {sha}", "time": "2026-11-19T10:00:00+00:00",
    }  # fmt: skip
    data = {k: v for k, v in {**data, **over}.items() if v is not None}
    pass_proof.write_record(repo, ID, "milestone-1", data)
    return data


def test_the_key_names_one_record_per_run() -> None:
    k = pass_proof.key
    assert k("milestone", "milestone/widget-2", None, "milestone/", "widget") == "milestone-2"
    assert k("milestone", "milestone/widget", None, "milestone/", "widget") == "milestone-1"  # unnumbered
    assert k("milestone", "", 3, "milestone/", "widget") == "milestone-3"  # detached, explicit
    assert k("milestone", "milestone/widget-2", 2, "milestone/", "widget") == "milestone-2"
    assert k("milestone", "", None) is None  # nothing names it
    assert k("milestone", "feat/other") == "milestone-0"  # a slot no reader counts
    assert k("feature", "feat/cart") == k("feature", "feat/cart") == "feature-feat-cart"
    assert k("feature", "feat/cart") != k("feature", "feat/pay")  # one slot per feature
    assert k("feature", "") is None and k("project") == "project-0"


@pytest.mark.parametrize("missing", ["scope", "change", "key", "milestone", "owner", "sha", "verdict"])
def test_a_record_missing_a_binding_field_does_not_hold(repo: Path, missing: str) -> None:
    data = _record(repo)
    got = pass_proof.holds(repo, "changes", ID, "milestone-1", data["sha"], "project/p")
    assert got == data["sha"] and got.verdict == "pass"
    _record(repo, **{missing: None})
    assert pass_proof.holds(repo, "changes", ID, "milestone-1", data["sha"], "project/p") == ""


@pytest.mark.parametrize(
    "wrong",
    [{"scope": "feature"}, {"change": "2026-01-01-other"}, {"key": "milestone-2"}, {"milestone": 2}, {"owner": "project/q"}],
)
def test_a_record_bound_to_something_else_does_not_hold(repo: Path, wrong: dict) -> None:
    data = _record(repo, **wrong)
    assert pass_proof.holds(repo, "changes", ID, "milestone-1", data["sha"], "project/p") == ""


def test_another_owners_record_is_no_pass_and_no_block(repo: Path) -> None:
    data = _record(repo, owner="project/q", verdict="blocked", result="VERIFY BLOCKED reason=env")
    got = pass_proof.holds(repo, "changes", ID, "milestone-1", data["sha"], "project/p")
    assert got == "" and got.verdict == ""  # it decides nothing for project/p


def test_the_newest_run_replaces_the_pass_and_reports_its_verdict(repo: Path) -> None:
    sha = _record(repo)["sha"]
    _record(repo, verdict="blocked", result="VERIFY BLOCKED reason=protected-path")
    got = pass_proof.holds(repo, "changes", ID, "milestone-1", sha, "project/p")
    assert got == "" and got.verdict == "blocked" and got.result == "VERIFY BLOCKED reason=protected-path"
    assert pass_proof.holds(repo, "changes", ID, "milestone-1", "", "project/p").verdict == "blocked"  # no head asked


def test_a_milestone_without_a_number_never_holds(repo: Path) -> None:
    pass_proof.write_record(repo, ID, "milestone-0", {**_record(repo), "key": "milestone-0", "milestone": 0})
    assert pass_proof.holds(repo, "changes", ID, "milestone-0", _git(repo, "rev-parse", "HEAD"), None) == ""


def test_the_writer_version_not_the_records_choose_the_mode(repo: Path) -> None:
    gate = repo / "scripts" / "verify_gate.py"
    sdlc = repo / "sdlc.json"
    assert pass_proof.writer_format(repo) == 2
    gate.write_text("# kit 3.20.3, no constant\n")
    sdlc.write_text(json.dumps({"sdlcVersion": "3.20.4"}))  # adopt restamps on a plain --upgrade
    assert pass_proof.writer_format(repo) == 1  # a readable gate without the constant is older, full stop
    gate.unlink()
    assert pass_proof.writer_format(repo) == 2  # unreadable: the stamp
    sdlc.write_text(json.dumps({"sdlcVersion": "3.20.3"}))
    assert pass_proof.writer_format(repo) == 1
    sdlc.write_text("{}")
    assert pass_proof.writer_format(repo) == 1


def test_an_older_writer_is_read_by_its_own_receipt_and_report(repo: Path) -> None:
    (repo / "scripts" / "verify_gate.py").write_text("# 3.20.2\n")
    sha = _git(repo, "rev-parse", "HEAD")
    old = {"scope": "milestone", "milestone": 1, "change": ID, "sha": sha, "result": f"VERIFY PASS milestone {ID} {sha}"}
    pass_proof.write_record(repo, ID, "milestone-1", old)  # what 3.20.2 left: no verdict, no owner, no key
    assert pass_proof.holds(repo, "changes", ID, "milestone-1", sha, "project/p") == sha
    # ...and the new writer's reader refuses the same file
    (repo / "scripts" / "verify_gate.py").write_text("RECEIPT_FORMAT = 2\n")
    assert pass_proof.holds(repo, "changes", ID, "milestone-1", sha, "project/p") == ""
    # an old record that names another owner is not another project's pass either
    (repo / "scripts" / "verify_gate.py").write_text("# 3.20.3\n")
    pass_proof.write_record(repo, ID, "milestone-1", {**old, "owner": "project/q", "verdict": "pass"})
    assert pass_proof.holds(repo, "changes", ID, "milestone-1", sha, "project/p") == ""


def test_the_first_record_is_marked_once_and_a_hold_carries_it(repo: Path) -> None:
    data = _record(repo)
    _record(repo, time="2026-12-01T00:00:00+00:00")
    got = pass_proof.holds(repo, "changes", ID, "milestone-1", data["sha"], "project/p")
    assert got.first == data["time"]  # the first run's time, not the newest record's


def test_one_hold_judges_other_heads_without_reading_again(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = _record(repo)
    got = pass_proof.holds(repo, "changes", ID, "milestone-1", "", "project/p")
    reads = []
    real = Path.read_text
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: (reads.append(self.name), real(self, *a, **k))[1])
    assert got.at(data["sha"]) == data["sha"] and got.at("b" * 40) == ""
    assert "milestone-1.json" not in reads


def test_only_pass_proof_opens_the_records() -> None:
    """The one reader: no other shipped script, hook or template names the records folder or the
    helpers that read it, so a second reader cannot grow beside holds()."""
    shipped = [
        *(p for p in (SKILL / "scripts").glob("*.py") if not p.name.startswith("test_")),
        *(SKILL / "templates" / "hooks").glob("*"),
        *(SKILL / "templates" / "scripts").glob("*"),
    ]
    banned = re.compile(r"[\"']receipts[\"']|sdlc/receipts|read_receipt|has_receipts|receipt_dir|receipt_path|[\"']\.first[\"']")
    hits = [
        f"{p.name}:{n}: {line.strip()}"
        for p in shipped
        if p.is_file() and p.name != "pass_proof.py"
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if banned.search(line)
    ]
    assert not hits, hits
