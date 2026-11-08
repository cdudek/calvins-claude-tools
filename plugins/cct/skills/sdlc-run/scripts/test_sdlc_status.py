"""sdlc_status.py map: milestones, features and stage, read from the files and nothing else."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "templates" / "scripts" / "sdlc_status.py"
ID = "2026-10-09-redesign-r2"
ROWS = "\n".join(
    f"| {n} | {ID} | feature {n} | url | {'merged' if n < 3 else 'building' if n == 3 else 'todo'} |"
    for n in range(1, 11)
)


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    change = repo / "changes" / ID
    change.mkdir(parents=True)
    (repo / "docs" / "designs").mkdir(parents=True)
    (repo / "sdlc.json").write_text("{}")
    (repo / "docs" / "designs" / "redesign.md").write_text(
        "# Design: Redesign\n\n## Milestones\n\n- R1 foundations: 2026-10-01-redesign-r1\n"
        f"- R2 editor: {ID}\n- R3 export\n- R4 polish\n"
    )
    (change / "decisions.json").write_text(
        json.dumps(
            {
                "design": "docs/designs/redesign.md",
                "milestone": {"kind": "new", "slug": "redesign-r2"},
            }
        )
    )
    (change / "milestone.md").write_text(
        "---\nmilestone: redesign-r2\n---\n\n## Features\n\n| # | Change | Feature | PR | State |\n"
        f"|---|---|---|---|---|\n{ROWS}\n\n## Done\n"
    )
    (change / "lock.json").write_text("{}")
    subprocess.run(
        ["git", "init", "-q", "-b", "feat/redesign-r2"], cwd=repo, check=True, env=_env()
    )
    return repo


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env=_env(),
    )


def test_map_shows_both_levels_and_the_stage(repo: Path) -> None:
    out = _run(repo, "map").stdout
    assert "Redesign  M2 of 4" in out and "2 of 10 merged  ✓✓◐○○○○○○○" in out
    assert "stage  5/7 Build" in out


def test_stage_comes_from_the_files(repo: Path) -> None:
    change = repo / "changes" / ID
    (change / "lock.json").unlink()
    stages = []
    for step in (
        lambda: None,
        lambda: (change / "intent.md").write_text("---\nstatus: approved\n---\n"),
        lambda: (change / "facts.md").write_text("# Facts\n"),
        lambda: (change / "plan.md").write_text("# Plan: Redesign\n"),
        lambda: (change / "lock.json").write_text("{}"),
    ):
        step()
        stages.append(_run(repo, "map").stdout.split("stage  ")[1][:3])
    assert stages == ["1/7", "2/7", "3/7", "4/7", "5/7"]


def test_map_finds_the_only_open_change_off_its_branch(repo: Path) -> None:
    subprocess.run(["git", "checkout", "-q", "-b", "other"], cwd=repo, check=True, env=_env())
    assert "Redesign  M2 of 4" in _run(repo, "map").stdout


def test_map_writes_nothing(repo: Path) -> None:
    before = sorted(p.name for p in (repo / "changes" / ID).iterdir())
    _run(repo, "map")
    assert sorted(p.name for p in (repo / "changes" / ID).iterdir()) == before


def test_the_removed_verbs_are_refused(repo: Path) -> None:
    for verb in ("set", "line", "name"):
        assert _run(repo, verb).returncode == 2
