"""goal_active.py: the one reading of "is a /goal running" for pr-gate.sh, chain-gate.sh and
verify-on-stop.sh. The transcript fixtures pin the undocumented shapes; if Claude Code changes
them, these tests are where it shows. Then each hook is run the way Claude Code runs it (JSON
payload on stdin, exit code, stderr) to prove it reads goal state only through the helper,
keeps today's handling of an unreadable transcript, and blocks when the helper is missing.

The module is loaded inside each test, so a missing goal_active.py fails those tests and
nothing else."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "templates" / "hooks"
HELPER = HOOKS / "goal_active.py"
ID = "2026-11-01-trial"
PLAN = "---\nstatus: approved\n---\n\n## Goal handover\n\nDeliver feature 1 of change trial.\n"

# --- transcript shapes (undocumented; pinned here) -----------------------------------------
RUNNING = {"type": "attachment", "attachment": {"type": "goal_status", "met": False}}
RUNNING_SENTINEL = {
    "type": "attachment",
    "attachment": {"type": "goal_status", "met": False, "sentinel": True},
}
MET = {"attachment": {"type": "goal_status", "met": True}}
FAILED = {"attachment": {"type": "goal_status", "met": False, "failed": True}}
SET = {
    "type": "user",
    "message": {"content": "A session-scoped Stop hook is now active with condition: ship it"},
}
CLEAR_CMD = {
    "type": "system",
    "subtype": "local_command",
    "content": "<command-name>/goal</command-name>\n<command-args>clear</command-args>",
}
CLEAR_OUT = {
    "type": "system",
    "subtype": "local_command",
    "content": "<local-command-stdout>No goal set</local-command-stdout>",
}
CHATTER = [{"type": "user", "message": {"content": "hello"}}, {"type": "assistant"}]


def _env() -> dict[str, str]:
    return {
        k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "SDLC_GOAL_OFF"
    }


def _transcript(tmp: Path, *entries: object, name: str = "t.jsonl") -> str:
    path = tmp / name
    path.write_text("".join(json.dumps(e) + "\n" for e in entries))
    return str(path)


@pytest.fixture
def goal_active(monkeypatch: pytest.MonkeyPatch):
    """goal_active(transcript), importing the helper on the first call inside the test, so a
    missing goal_active.py fails that test instead of erroring in setup."""
    monkeypatch.delenv("SDLC_GOAL_OFF", raising=False)

    def call(transcript: str) -> bool | None:
        spec = importlib.util.spec_from_file_location("goal_active_under_test", HELPER)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # FileNotFoundError while the helper does not exist yet
        return mod.goal_active(transcript)

    return call


# --- the helper: one transcript per fact ---------------------------------------------------
def test_a_failed_goal_is_not_active_F1(goal_active, tmp_path: Path) -> None:
    assert goal_active(_transcript(tmp_path, SET, RUNNING, FAILED)) is False
    assert goal_active(_transcript(tmp_path, RUNNING, RUNNING_SENTINEL, FAILED)) is False


def test_a_met_goal_is_not_active_F1(goal_active, tmp_path: Path) -> None:
    assert goal_active(_transcript(tmp_path, RUNNING_SENTINEL, MET)) is False


def test_a_transcript_without_goal_entries_reports_no_goal_F1(goal_active, tmp_path: Path) -> None:
    # False, not None: the file is readable and says there is no goal.
    assert goal_active(_transcript(tmp_path, *CHATTER)) is False


def test_goal_clear_ends_a_running_goal_F2(goal_active, tmp_path: Path) -> None:
    assert goal_active(_transcript(tmp_path, SET, RUNNING, CLEAR_CMD, CLEAR_OUT)) is False
    assert goal_active(_transcript(tmp_path, RUNNING, CLEAR_CMD, CLEAR_OUT)) is False


def test_text_quoted_in_other_entries_does_not_clear_a_goal_F2(goal_active, tmp_path: Path) -> None:
    # An api request blob quotes old transcript text; only system and user entries count.
    blob = {"type": "api-request-blob", "content": CLEAR_CMD["content"] + " No goal set"}
    assert goal_active(_transcript(tmp_path, SET, RUNNING, blob)) is True


def test_the_off_switch_env_turns_a_running_goal_off_F3(
    goal_active, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    t = _transcript(tmp_path, SET, RUNNING_SENTINEL)
    assert goal_active(t) is True
    monkeypatch.setenv("SDLC_GOAL_OFF", "1")
    assert goal_active(t) is False
    cli = subprocess.run([sys.executable, str(HELPER), t], env=os.environ.copy())
    assert cli.returncode == 1
    monkeypatch.setenv("SDLC_GOAL_OFF", "0")
    assert goal_active(t) is True  # only "1" switches it off


def test_off_switch_file_does_not_turn_a_goal_off_F3(
    goal_active, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """There is no off-switch file: an agent could write one. A `sdlc-goal-off` file in the git
    common dir or the repo root changes nothing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "master"], cwd=repo, check=True, env=_env())
    (repo / ".git" / "sdlc-goal-off").write_text("")
    (repo / "sdlc-goal-off").write_text("")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))
    assert goal_active(_transcript(tmp_path, SET, RUNNING)) is True


def test_a_goal_set_and_not_ended_is_active_F5(goal_active, tmp_path: Path) -> None:
    assert goal_active(_transcript(tmp_path, RUNNING)) is True
    assert goal_active(_transcript(tmp_path, *CHATTER, SET)) is True
    assert (
        goal_active(_transcript(tmp_path, SET, RUNNING_SENTINEL, {"type": "assistant"}, RUNNING))
        is True
    )


@pytest.mark.parametrize(
    "ended", [[FAILED], [MET], [CLEAR_CMD, CLEAR_OUT]], ids=["failed", "met", "clear"]
)
def test_a_goal_set_after_an_ended_one_is_active_F5(
    goal_active, tmp_path: Path, ended: list
) -> None:
    assert goal_active(_transcript(tmp_path, SET, RUNNING, *ended, SET)) is True


def test_cli_exit_code_follows_the_reading_F5(tmp_path: Path) -> None:
    """`python3 goal_active.py <transcript>`: exit 0 when a goal is active, 1 otherwise."""

    def run(*entries: object) -> int:
        t = _transcript(tmp_path, *entries)
        return subprocess.run([sys.executable, str(HELPER), t], env=_env()).returncode

    assert run(SET, RUNNING) == 0
    assert run(SET, RUNNING, FAILED) == 1
    assert run(*CHATTER) == 1


@pytest.mark.parametrize(
    "content", [None, "", "not json at all\n{broken\n"], ids=["missing", "empty", "garbage"]
)
def test_an_unreadable_transcript_is_none_F14(
    goal_active, tmp_path: Path, content: str | None
) -> None:
    path = tmp_path / "t.jsonl"
    if content is not None:
        path.write_text(content)
    assert goal_active(str(path)) is None


# --- F4: the hooks read goal state only through the helper ---------------------------------
def test_hooks_share_helper_F4() -> None:
    assert HELPER.is_file(), "templates/hooks/goal_active.py is the one reading"
    holders = sorted(
        p.name
        for p in HOOKS.iterdir()
        if p.is_file() and p != HELPER and "goal_status" in p.read_text()
    )
    assert holders == [], f"read goal_status outside goal_active.py: {holders}"
    for hook in ("pr-gate.sh", "chain-gate.sh", "verify-on-stop.sh"):
        assert "goal_active" in (HOOKS / hook).read_text(), f"{hook} does not use the helper"


# --- the hooks, run as Claude Code runs them ------------------------------------------------
def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo, check=True, env=_env(), capture_output=True, text=True,
    ).stdout.strip()  # fmt: skip


def _project(tmp_path: Path, helper: bool = True) -> Path:
    """One repo all three hooks work in: branch fix/trial-thing carries the change `trial`, so
    chain-gate treats source edits as milestone building, pr-gate sees a plain branch push and
    verify-on-stop sees a verify command that fails."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "master", str(origin))
    repo = tmp_path / "repo"
    hooks = repo / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    names = ["pr-gate.sh", "chain-gate.sh", "verify-on-stop.sh", "sdlc-config.sh", "block_state.py", "pass_proof.py"]
    if helper:
        names.append("goal_active.py")
    for name in names:
        if (HOOKS / name).exists():  # today's tree has neither .py yet
            shutil.copy(HOOKS / name, hooks / name)
    (repo / "sdlc.json").write_text(
        json.dumps(
            {
                "defaultBranch": "master",
                "changesDir": "changes",
                "verify": "sh -c 'echo verify-ran; exit 1'",
                "verifyDirty": ["*.py"],
            }
        )
    )
    change = repo / "changes" / ID
    change.mkdir(parents=True)
    (change / "decisions.json").write_text(
        json.dumps(
            {"size": "M", "kind": "feature", "milestone": {"kind": "single", "slug": "trial"}}
        )
    )
    (change / "intent.md").write_text("---\nstatus: approved\n---\n")
    (change / "facts.md").write_text("---\nstatus: approved\n---\n")
    (change / "plan.md").write_text(PLAN)
    (change / "lock.json").write_text("{}\n")
    _git(tmp_path, "init", "-q", "-b", "master", str(repo))
    _git(repo, "remote", "add", "origin", str(origin))
    (repo / "src").mkdir()
    (repo / "src" / "app.ts").write_text("1\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "init")
    _git(repo, "push", "-q", "origin", "master")
    _git(repo, "checkout", "-qb", "fix/trial-thing")
    return repo


def _hook(repo: Path, name: str, **payload: object) -> subprocess.CompletedProcess[str]:
    payload = {"cwd": str(repo), "session_id": "sess-1", **payload}
    return subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / name)],
        input=json.dumps(payload), capture_output=True, text=True,
        env={**_env(), "CLAUDE_PROJECT_DIR": str(repo)},
    )  # fmt: skip


def _push(repo: Path, transcript: str, command: str = "git push -u origin fix/trial-thing"):
    return _hook(repo, "pr-gate.sh", tool_input={"command": command}, transcript_path=transcript)


def _edit(repo: Path, transcript: str, file: str = "src/app.ts"):
    return _hook(repo, "chain-gate.sh", tool_input={"file_path": file}, transcript_path=transcript)


def _stop(repo: Path, transcript: str):
    (repo / "x.py").write_text("x = 1\n")  # dirty source reaches the goal check
    return _hook(repo, "verify-on-stop.sh", stop_hook_active=False, transcript_path=transcript)


UNREADABLE = ["missing", "garbage"]


def _unreadable(tmp_path: Path, kind: str) -> str:
    path = tmp_path / "unreadable.jsonl"
    if kind == "garbage":
        path.write_text("not json\n{broken\n")
    return str(path)


@pytest.mark.parametrize("kind", UNREADABLE)
def test_pr_gate_reads_no_goal_from_an_unreadable_transcript_F14(tmp_path: Path, kind: str) -> None:
    repo = _project(tmp_path)
    assert _push(repo, _unreadable(tmp_path, kind)).returncode == 0  # no goal block
    # and it is the transcript, not the rule, that went quiet: a readable goal still blocks
    r = _push(repo, _transcript(tmp_path, SET, RUNNING))
    assert r.returncode == 2 and "inside a /goal run" in r.stderr


@pytest.mark.parametrize("kind", UNREADABLE)
def test_chain_gate_allows_with_a_warning_on_an_unreadable_transcript_F14(
    tmp_path: Path, kind: str
) -> None:
    r = _edit(_project(tmp_path), _unreadable(tmp_path, kind))
    assert r.returncode == 0
    assert (
        "chain-gate: transcript unreadable, cannot check for an active /goal; allowing." in r.stderr
    )


@pytest.mark.parametrize("kind", UNREADABLE)
def test_verify_on_stop_runs_verify_on_an_unreadable_transcript_F14(
    tmp_path: Path, kind: str
) -> None:
    r = _stop(_project(tmp_path), _unreadable(tmp_path, kind))
    assert r.returncode == 2 and "verify-ran" in r.stderr


@pytest.mark.parametrize(
    "command", ["git push -u origin fix/trial-thing", "gh pr create --title t --body b"]
)
def test_pr_gate_blocks_when_the_helper_is_missing_F15(tmp_path: Path, command: str) -> None:
    repo = _project(tmp_path, helper=False)
    t = _transcript(tmp_path, SET, RUNNING)
    r = _push(repo, t, command)
    assert r.returncode == 2 and "sdlc-run adopt" in r.stderr
    # an unrelated call does not need the helper
    assert _push(repo, t, "git push origin --tags").returncode == 0
    assert _push(repo, t, "git status").returncode == 0


def test_chain_gate_blocks_when_the_helper_is_missing_F15(tmp_path: Path) -> None:
    repo = _project(tmp_path, helper=False)
    t = _transcript(tmp_path, SET, RUNNING)
    r = _edit(repo, t)
    assert r.returncode == 2 and "sdlc-run adopt" in r.stderr
    assert _edit(repo, t, "docs/notes.md").returncode == 0  # never reaches the /goal check


def test_verify_on_stop_blocks_when_the_helper_is_missing_F15(tmp_path: Path) -> None:
    repo = _project(tmp_path, helper=False)
    r = _stop(repo, _transcript(tmp_path, SET, RUNNING))
    assert r.returncode == 2 and "sdlc-run adopt" in r.stderr and "verify-ran" not in r.stderr
    # clean tree: nothing reaches the goal check
    (tmp_path / "clean").mkdir()
    clean = _project(tmp_path / "clean", helper=False)
    r = _hook(clean, "verify-on-stop.sh", stop_hook_active=False, transcript_path="")
    assert r.returncode == 0
