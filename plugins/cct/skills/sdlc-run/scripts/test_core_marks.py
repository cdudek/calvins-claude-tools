"""Speed A close, the owner-answer reader and the capture checks (3.21.0, round 3)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_verify_gate import (
    GATE,
    ID,
    OPEN_ITEM,
    _dialog,
    _dispose,
    _env,
    _git,
    _last,
    _later,
    _milestone_repo,
    _owner_gate,
)

TEMPLATES = GATE.parent


def _marks():
    sys.path.insert(0, str(TEMPLATES))
    spec = importlib.util.spec_from_file_location("marks_under_test", TEMPLATES / "marks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_recommended_option_is_read_without_its_suffix(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    _dispose(repo)
    options = ["Accept as is (Recommended)", "Fix it now", "Block the close"]
    entries = _dialog(label="Accept as is (Recommended)", options=options)
    assert _last(_owner_gate(repo, entries)).startswith(f"VERIFY PASS milestone {ID}")


def test_a_reused_finding_id_needs_a_fresh_answer(tmp_path: Path) -> None:
    """The earlier B2 was answered; the finding was removed and a new B2 appeared later: the old
    answer is older than this incarnation and settles nothing."""
    repo = _milestone_repo(tmp_path)
    _dispose(repo)  # first B2
    _dispose(repo, "## Blocking\n\n- [x] **B1** other\n")  # B2 gone
    findings = repo / "changes" / ID / "findings.md"
    findings.write_text(OPEN_ITEM)
    _git(repo, "add", "-A")
    late = _later(600).replace("Z", "+00:00")
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "B2 again", "--date", late],
        cwd=repo, check=True, capture_output=True, env={**_env(), "GIT_COMMITTER_DATE": late},
    )  # fmt: skip
    r = _owner_gate(repo, _dialog(n=1))  # answered before the second B2 existed
    assert _last(r) == "VERIFY BLOCKED reason=findings-open", r.stdout
    assert _last(_owner_gate(repo, _dialog(n=700))).startswith(f"VERIFY PASS milestone {ID}")


def test_the_transcript_is_parsed_once_per_process_and_skips_sessions_older_than_the_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _milestone_repo(tmp_path)
    _dispose(repo)
    marks = _marks()
    home = tmp_path / "home"
    folder = home / ".claude/projects" / "".join(c if c.isalnum() else "-" for c in str(repo.resolve()))
    folder.mkdir(parents=True)
    old, new = folder / "old.jsonl", folder / "new.jsonl"
    old.write_text("\n".join(json.dumps(e) for e in _dialog(n=1)) + "\n")
    new.write_text("\n".join(json.dumps(e) for e in _dialog(n=2)) + "\n")
    os.utime(old, (946684800, 946684800))  # the year 2000: older than the change folder
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    opened: list[str] = []
    real = Path.read_text

    def spy(self, *a, **k):
        if self.suffix == ".jsonl":
            opened.append(self.name)
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", spy)
    first = marks.owner_decisions(repo, ID, repo / "changes" / ID / "findings.md", "**{}**")
    marks.owner_decisions(repo, ID, repo / "changes" / ID / "findings.md", "**{}**")
    assert first.get("B2", ("",))[0] == "accepted"
    assert opened == ["new.jsonl"], opened


def test_a_changed_file_with_a_space_in_its_name_makes_the_capture_stale(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    (repo / "src").mkdir(parents=True)
    (repo / "changes").mkdir()
    (repo / "src" / "Account Page.tsx").write_text("a")
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "build")
    build = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    (repo / "src" / "Account Page.tsx").write_text("b")
    _git(repo, "commit", "-qam", "edit")
    why = _marks().stale_build(repo.resolve(), (repo / "changes" / "c").resolve(), build, ["src/Account Page.tsx"])
    assert "Account Page.tsx" in why


@pytest.mark.parametrize(
    "qa",
    [
        "# QA\n\n| Screen | Build commit | Verdict |\n|---|---|---|\n| home | {sha} | pass |\n",
        "# QA\n\nBuild: {sha}\n",
    ],
)
def test_qa_md_records_its_build_as_a_line_or_a_build_commit_column(tmp_path: Path, qa: str) -> None:
    repo = tmp_path / "r"
    change = repo / "changes" / "c"
    (change / "spec").mkdir(parents=True)
    (repo / "a").write_text("a")
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "x")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    (change / "spec" / "qa.md").write_text(qa.format(sha=sha))
    assert _marks().qa_problems(change.resolve(), repo.resolve(), True) == []


def _manifest_repo(tmp_path: Path, entries: list[dict]) -> tuple[Path, Path, list[dict]]:
    repo = tmp_path / "r"
    change = repo / "changes" / "c"
    (change / "verify/shots").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "src" / "a.tsx").write_text("a")
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "x")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    full = [{"build": sha, "reference": "0" * 64, "sources": ["src/a.tsx"], "shot": f"s{i}.png", **e} for i, e in enumerate(entries)]
    (change / "verify/shots/manifest.json").write_text(json.dumps({"entries": full, "shared": []}))
    (change / "lock.json").write_text(json.dumps({"manifest": "required"}))
    return repo.resolve(), change.resolve(), [{"id": "r", "kind": "reference", "image": "a.png"}]


CELL = {"screen": "home", "state": "default", "width": 1280}


def test_an_entry_with_no_screen_state_width_or_zoom_is_a_cell_error(tmp_path: Path) -> None:
    repo, change, rows = _manifest_repo(tmp_path, [{}])
    text = " ".join(_marks().manifest_problems(change, rows, repo))
    for field in ("screen", "state", "width", "zoom"):
        assert field in text, text


def test_each_screen_state_width_needs_both_zooms_100_and_150(tmp_path: Path) -> None:
    repo, change, rows = _manifest_repo(tmp_path, [{**CELL, "zoom": 100}])
    assert any("150" in p for p in _marks().manifest_problems(change, rows, repo))
    repo2, change2, rows2 = _manifest_repo(tmp_path / "b", [{**CELL, "zoom": 100}, {**CELL, "zoom": 150}])
    assert not any("zoom" in p for p in _marks().manifest_problems(change2, rows2, repo2))
