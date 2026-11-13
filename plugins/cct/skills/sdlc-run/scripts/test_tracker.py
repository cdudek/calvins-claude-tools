"""tracker.py detect: what is set up, and which tracker it recommends, with fake gh and bd."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

TRACKER = Path(__file__).resolve().parent / "tracker.py"


def _bin(tmp_path: Path, gh: str | None, bd: bool) -> Path:
    b = tmp_path / "bin"
    b.mkdir()
    if gh is not None:
        (b / "gh").write_text(f"#!/bin/sh\n{gh}\n")
        (b / "gh").chmod(0o755)
    if bd:
        (b / "bd").write_text("#!/bin/sh\nexit 0\n")
        (b / "bd").chmod(0o755)
    return b


GH_OK = """case "$1" in auth) echo "Token scopes: 'repo', 'project'";; api) echo "${MILESTONES:-0}";; esac"""
GH_NO_SCOPE = """case "$1" in auth) echo "Token scopes: 'repo'";; api) echo 0;; esac"""


def _detect(
    tmp_path: Path,
    *,
    owner: str,
    gh: str | None,
    bd: bool,
    cfg: dict | None = None,
    beads: bool = False,
    milestones: int = 0,
    mcp: str = "no",
) -> dict[str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "remote", "add", "origin", f"git@github.com:{owner}/app.git"],
        cwd=repo,
        check=True,
        env=env,
    )
    if cfg is not None:
        (repo / "sdlc.json").write_text(json.dumps(cfg))
    if beads:
        (repo / ".beads").mkdir()
    env["PATH"] = f"{_bin(tmp_path, gh, bd)}:/usr/bin:/bin"
    env["MILESTONES"] = str(milestones)
    out = subprocess.run(
        [sys.executable, str(TRACKER), "detect", "--linear-mcp", mcp],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout
    return dict(re.findall(r"^- (\w+): (.*)$", out, re.M))


def test_sdlc_json_wins(tmp_path: Path) -> None:
    rows = _detect(tmp_path, owner="acme", gh=GH_OK, bd=True, cfg={"tracker": {"kind": "beads"}})
    assert rows["recommend"] == "beads" and rows["reason"] == "sdlc.json already names it"


def test_the_old_linear_key_means_linear(tmp_path: Path) -> None:
    rows = _detect(
        tmp_path, owner="x", gh=None, bd=False, cfg={"linear": {"team": "ABC"}}, mcp="yes"
    )
    assert rows["configured"] == "linear" and rows["steps"] == "none"


def test_beads_already_in_use_is_kept(tmp_path: Path) -> None:
    rows = _detect(tmp_path, owner="acme", gh=GH_OK, bd=True, beads=True)
    assert rows["recommend"] == "beads" and "switching splits the history" in rows["reason"]


def test_github_milestones_already_in_use_are_kept(tmp_path: Path) -> None:
    rows = _detect(tmp_path, owner="acme", gh=GH_OK, bd=False, milestones=3)
    assert rows["recommend"] == "github" and rows["open_milestones"] == "3"


@pytest.mark.parametrize(
    "gh,bd,expected,step",
    [
        (GH_NO_SCOPE, False, "github", "gh auth refresh -s project"),
        (None, True, "beads", "bd init"),
        (None, False, "none", None),
    ],
)
def test_elsewhere_the_cheapest_working_tool(tmp_path: Path, gh, bd, expected, step) -> None:
    rows = _detect(tmp_path, owner="someone", gh=gh, bd=bd)
    assert rows["recommend"] == expected
    if step:
        assert any(v.startswith(step) for k, v in rows.items() if k.startswith("step"))
    else:
        assert rows["steps"] == "none"
