"""`sdlc_status.py sweep-merged`: the next change's first commit removes the folders of merged changes."""

from __future__ import annotations

import subprocess
from pathlib import Path

import sdlc_status
from test_sdlc_status import (  # noqa: F401  (ID is the current change: its branch is checked out)
    ID,
    _env,
)

OLD = "2026-10-01-old-thing"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=_env(),
    ).stdout


def _pr(head: str, base: str = "main", state: str = "MERGED", number: int = 3) -> dict:
    return {"number": number, "headRefName": head, "baseRefName": base, "state": state}


def _setup(repo: Path, old: str = OLD) -> Path:
    folder = repo / "changes" / old
    folder.mkdir(parents=True)
    (folder / "intent.md").write_text("# Intent\n\n## Success measure\n\nFewer questions.\n")
    (folder / "facts.md").write_text("facts\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "start")
    return folder


def _sweep(repo: Path, prs: list[dict], apply: bool = False) -> list[str]:
    return sdlc_status.sweep_merged(
        repo, apply=apply, gh=lambda root, *a: [p for p in prs if p["state"] == "MERGED"]
    )  # `--state merged`


def test_a_merged_change_is_listed_with_its_two_commands(repo: Path) -> None:
    _setup(repo)
    out = _sweep(repo, [_pr("milestone/old-thing-1")])
    assert out == [
        f"python3 scripts/spec.py outcome write changes/{OLD}",
        f"git rm -r changes/{OLD}",
    ]


def test_the_change_this_branch_builds_is_never_swept(repo: Path) -> None:
    _setup(repo)
    assert _sweep(repo, [_pr("milestone/redesign-r2-1")]) == []


def test_an_unmerged_change_stays(repo: Path) -> None:
    _setup(repo)
    assert _sweep(repo, [_pr("milestone/old-thing-1", state="OPEN")]) == []


def test_a_milestone_merged_into_a_project_branch_needs_the_project_pr(repo: Path) -> None:
    _setup(repo)
    into_project = _pr("milestone/old-thing-1", base="project/big")
    assert _sweep(repo, [into_project]) == []
    assert _sweep(repo, [into_project, _pr("project/big", number=4)]) != []


def test_a_reader_outside_the_folder_blocks_the_removal(repo: Path) -> None:
    _setup(repo)
    (repo / "docs.md").write_text(f"see changes/{OLD}/facts.md\n")
    _git(repo, "add", "-A")
    out = _sweep(repo, [_pr("milestone/old-thing-1")])
    assert len(out) == 1 and out[0].startswith(f"BLOCKED changes/{OLD}") and "docs.md" in out[0]


def test_apply_removes_the_folder_keeps_the_outcome_and_stages_both(repo: Path) -> None:
    folder = _setup(repo)
    (folder / "verify").mkdir()
    (folder / "verify" / "report.json").write_text("{}")  # ignored output the git rm leaves behind
    (repo / ".gitignore").write_text("verify/\n")
    _sweep(repo, [_pr("milestone/old-thing-1")], apply=True)
    assert not folder.exists()
    assert (repo / ".sdlc" / "outcomes" / f"{OLD}.json").exists()
    staged = _git(repo, "diff", "--cached", "--name-only")
    assert f".sdlc/outcomes/{OLD}.json" in staged and f"changes/{OLD}/facts.md" in staged
