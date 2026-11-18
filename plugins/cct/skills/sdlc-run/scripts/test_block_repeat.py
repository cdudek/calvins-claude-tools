"""A repeated block says stop: pr-gate.sh, chain-gate.sh and gate-bash.sh record each block in
the session's state file and rewrite an identical second block as `STOP: this block repeated.`
Every case runs the hook as Claude Code does: JSON payload (session_id, cwd) on stdin, exit
code, stderr."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "templates" / "hooks"
ID = "2026-11-01-trial"
PLAN = "---\nstatus: approved\n---\n\n## Goal handover\n\nDeliver feature 1 of change trial.\n"
BLOCKED = [{"match": r"(^|[[:space:];&|(])kubectl([[:space:]]+[^[:space:];&|]+)*[[:space:]]+(apply|delete)([[:space:]]|$)", "message": "the cluster changes through Argo CD from a merged PR."}]  # fmt: skip
RUNNING = {"type": "attachment", "attachment": {"type": "goal_status", "met": False}}
NO_GOAL = {"type": "user", "message": {"content": "hello"}}
STOP = "STOP: this block repeated."


def _env() -> dict[str, str]:
    return {
        k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "SDLC_GOAL_OFF"
    }


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo, check=True, env=_env(), capture_output=True, text=True,
    ).stdout.strip()  # fmt: skip


def _commit(repo: Path, path: str, text: str) -> None:
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", path)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """One repo for all three hooks: milestone branch `milestone/trial-1` of change `trial`,
    approved and locked, no gate pass, and a sdlc.json with one blocked[] rule."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "master", str(origin))
    repo = tmp_path / "repo"
    hooks = repo / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    for name in ("pr-gate.sh", "chain-gate.sh", "gate-bash.sh", "sdlc-config.sh"):
        shutil.copy(HOOKS / name, hooks / name)
    for name in ("goal_active.py", "block_state.py"):
        if (HOOKS / name).exists():  # today's tree has neither yet
            shutil.copy(HOOKS / name, hooks / name)
    (repo / "sdlc.json").write_text(
        json.dumps({"defaultBranch": "master", "changesDir": "changes", "blocked": BLOCKED})
    )
    (repo / ".gitignore").write_text("/changes/*/verify/\n")
    change = repo / "changes" / ID
    change.mkdir(parents=True)
    (change / "decisions.json").write_text(
        json.dumps(
            {"size": "M", "kind": "feature", "milestone": {"kind": "single", "slug": "trial"}}
        )
    )
    for name in ("intent.md", "facts.md"):
        (change / name).write_text("---\nstatus: approved\n---\n")
    (change / "plan.md").write_text(PLAN)
    (change / "lock.json").write_text("{}\n")
    _git(tmp_path, "init", "-q", "-b", "master", str(repo))
    _git(repo, "remote", "add", "origin", str(origin))
    _commit(repo, "src/app.ts", "1\n")
    _git(repo, "push", "-q", "origin", "master")
    _git(repo, "checkout", "-qb", "milestone/trial-1")
    _commit(repo, "src/app.ts", "2\n")
    return repo


@dataclass
class Variant:
    """One way a hook blocks. `sources` are groups of strings; the repeat's text must hold one
    of each group (TRANSCRIPT stands for the transcript's path)."""

    hook: str
    kind: str  # "bash" (tool_input.command) or "edit" (tool_input.file_path)
    block: str
    allow: str
    sources: list[list[str]]
    branch: str = "milestone/trial-1"
    transcript: list = field(default_factory=lambda: [NO_GOAL])
    action: str | None = None  # a string the owner action holds
    uses_cwd: bool = True


VARIANTS = {
    "pr-gate/milestone-gate": Variant(
        "pr-gate.sh", "bash", "git push -u origin milestone/trial-1", "git push origin --tags",
        [["verify/report.json"]],
    ),
    "pr-gate/goal": Variant(
        "pr-gate.sh", "bash", "git push -u origin fix/trial-thing", "git push origin --tags",
        [["the transcript's goal entry"], ["TRANSCRIPT"]],
        branch="fix/trial-thing", transcript=[NO_GOAL, RUNNING], action="/goal clear",
    ),
    "pr-gate/other": Variant(
        "pr-gate.sh", "bash", "git push origin HEAD:master", "git push origin --tags",
        [["sdlc.json"]],
    ),
    "chain-gate/goal": Variant(
        "chain-gate.sh", "edit", "src/app.ts", "docs/notes.md", [["transcript"]],
        uses_cwd=False,
    ),
    "chain-gate/other": Variant(
        "chain-gate.sh", "edit", f"changes/{ID}/facts.md", "docs/notes.md",
        [["lock.json", "decisions.json", "plan.md"]], uses_cwd=False,
    ),
    "gate-bash": Variant(
        "gate-bash.sh", "bash", "kubectl apply -f x.yaml", "git status", [["sdlc.json blocked[]"]],
        branch="milestone/trial-1", uses_cwd=False,
    ),
}  # fmt: skip
ALL = list(VARIANTS)
ONE_PER_HOOK = ["pr-gate/milestone-gate", "chain-gate/goal", "gate-bash"]


def _call(
    repo: Path, v: Variant, *, tool: str | None = None, session: str | None = "sess-1",
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:  # fmt: skip
    if (
        _git(repo, "rev-parse", "--abbrev-ref", "HEAD") != v.branch
    ):  # never write to a read-only .git
        try:
            _git(repo, "checkout", "-q", v.branch)
        except subprocess.CalledProcessError:
            _git(repo, "checkout", "-qb", v.branch)
    transcript = repo.parent / "t.jsonl"
    transcript.write_text("".join(json.dumps(e) + "\n" for e in v.transcript))
    tool = tool or v.block
    payload: dict = {
        "tool_input": {"command": tool} if v.kind == "bash" else {"file_path": tool},
        "transcript_path": str(transcript),
        "cwd": cwd or str(repo),
    }
    if session is not None:
        payload["session_id"] = session
    return subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / v.hook)],
        input=json.dumps(payload), capture_output=True, text=True,
        env={**_env(), "CLAUDE_PROJECT_DIR": str(repo)},
    )  # fmt: skip


def _state(repo: Path, session: str = "sess-1") -> list[dict]:
    path = repo / ".git" / "sdlc-blocks" / f"{session}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def _norm(text: str) -> str:
    return text.rstrip("\n")


def _header(
    first: subprocess.CompletedProcess[str], second: subprocess.CompletedProcess[str]
) -> str:
    """What the repeat adds before the original first-time message."""
    one, two = _norm(first.stderr), _norm(second.stderr)
    assert two.endswith("\n" + one), second.stderr
    return two[: -len(one)]


def _replay(repo: Path, v: Variant, **kw: object):
    first = _call(repo, v, **kw)  # type: ignore[arg-type]
    second = _call(repo, v, **kw)  # type: ignore[arg-type]
    assert first.returncode == 2 and first.stderr.startswith("BLOCKED"), first.stderr
    return first, second


# --- F9: every block is recorded ------------------------------------------------------------
@pytest.mark.parametrize("name", ALL)
def test_a_block_is_appended_to_the_session_file_F9(repo: Path, name: str) -> None:
    v = VARIANTS[name]
    before = time.time()
    r = _call(repo, v)
    assert r.returncode == 2 and not r.stderr.startswith(STOP)
    rows = _state(repo)
    assert len(rows) == 1, rows
    assert set(rows[0]) == {"hook", "message", "ts"}
    assert rows[0]["hook"] == v.hook
    assert _norm(rows[0]["message"]) == _norm(r.stderr)
    assert before - 2 <= rows[0]["ts"] <= time.time() + 2
    _call(repo, v)
    assert len(_state(repo)) == 2  # the repeat is a block too


@pytest.mark.parametrize("name", ONE_PER_HOOK)
def test_state_files_older_than_14_days_are_deleted_on_write_F9(repo: Path, name: str) -> None:
    blocks = repo / ".git" / "sdlc-blocks"
    blocks.mkdir()
    old, recent = blocks / "old-session.jsonl", blocks / "recent-session.jsonl"
    for p, days in ((old, 15), (recent, 1)):
        p.write_text("{}\n")
        stamp = time.time() - days * 86400
        os.utime(p, (stamp, stamp))
    assert _call(repo, VARIANTS[name]).returncode == 2
    assert not old.exists() and recent.exists()


# --- F10: a repeat says STOP ----------------------------------------------------------------
@pytest.mark.parametrize("name", ALL)
def test_a_repeated_block_starts_with_stop_F10(repo: Path, name: str) -> None:
    v = VARIANTS[name]
    assert not _call(repo, v).stderr.startswith(STOP)
    assert _call(repo, v, tool=v.allow).returncode == 0  # an allowed call in between: no reset
    for _ in range(2):  # the second and every later block
        r = _call(repo, v)
        assert r.returncode == 2 and r.stderr.startswith(STOP), r.stderr


@pytest.mark.parametrize("name", ALL)
def test_another_session_is_not_a_repeat_F10(repo: Path, name: str) -> None:
    v = VARIANTS[name]
    _call(repo, v, session="sess-1")
    r = _call(repo, v, session="sess-2")
    assert r.returncode == 2 and r.stderr.startswith("BLOCKED")


def test_a_block_with_a_new_message_is_not_a_repeat_F10(repo: Path) -> None:
    v = VARIANTS["pr-gate/milestone-gate"]  # the message names the head sha
    first = _call(repo, v)
    _commit(repo, "src/app.ts", "3\n")
    r = _call(repo, v)
    assert r.returncode == 2 and r.stderr.startswith("BLOCKED") and r.stderr != first.stderr


# --- F11: the repeat names the hook and what it read ----------------------------------------
@pytest.mark.parametrize("name", ALL)
def test_the_repeat_names_the_hook_and_its_source_F11(repo: Path, name: str) -> None:
    v = VARIANTS[name]
    header = _header(*_replay(repo, v))
    assert header.startswith(f"{STOP} {v.hook} refused the same call again; it read "), header
    transcript = str(repo.parent / "t.jsonl")
    for group in v.sources:
        wanted = [transcript if s == "TRANSCRIPT" else s for s in group]
        assert any(s in header for s in wanted), (wanted, header)


# --- F12: two identical blocks, the second message ------------------------------------------
@pytest.mark.parametrize("name", ONE_PER_HOOK)
def test_replaying_two_identical_blocks_gives_the_stop_message_F12(repo: Path, name: str) -> None:
    v = VARIANTS[name]
    first, second = _replay(repo, v)
    assert second.returncode == 2
    assert second.stderr.startswith(f"{STOP} {v.hook} refused the same call again; it read ")
    header = _header(first, second)
    assert "Do not retry" in header and "Owner action:" in header
    assert second.stderr.count(STOP) == 1  # one prefix, the original text unchanged after it


# --- F13: one owner action, no retry --------------------------------------------------------
@pytest.mark.parametrize("name", ALL)
def test_the_repeat_gives_one_owner_action_and_says_not_to_retry_F13(repo: Path, name: str) -> None:
    v = VARIANTS[name]
    header = _header(*_replay(repo, v))
    assert "Do not retry" in header
    assert header.count("Owner action:") == 1
    assert header.index("Do not retry") < header.index("Owner action:")
    action = header.split("Owner action:", 1)[1]
    assert action.strip(), "an empty owner action"
    if v.action:
        assert v.action in action, action


# --- N1: block state never breaks a hook ----------------------------------------------------
def _assert_first_time_twice(repo: Path, v: Variant, **kw: object) -> None:
    first = _call(repo, v, **kw)  # type: ignore[arg-type]
    second = _call(repo, v, **kw)  # type: ignore[arg-type]
    for r in (first, second):
        assert r.returncode == 2 and r.stderr.startswith("BLOCKED"), r.stderr
    assert STOP not in second.stderr and second.stderr == first.stderr


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
@pytest.mark.parametrize("name", ONE_PER_HOOK)
def test_unwritable_state_N1(repo: Path, name: str) -> None:
    common = repo / ".git"
    blocks = common / "sdlc-blocks"
    blocks.mkdir()
    blocks.chmod(0o555)  # read-only state dir
    try:
        _assert_first_time_twice(repo, VARIANTS[name])
    finally:
        blocks.chmod(0o755)
    shutil.rmtree(blocks)
    common.chmod(0o555)  # read-only common dir: sdlc-blocks cannot even be created
    try:
        _assert_first_time_twice(repo, VARIANTS[name])
    finally:
        common.chmod(0o755)


@pytest.mark.parametrize("name", ONE_PER_HOOK)
def test_a_state_path_that_is_a_file_N1(repo: Path, name: str) -> None:
    (repo / ".git" / "sdlc-blocks").write_text("not a directory")
    _assert_first_time_twice(repo, VARIANTS[name])


@pytest.mark.parametrize("name", ONE_PER_HOOK)
def test_a_missing_session_id_gives_the_first_time_message_N1(repo: Path, name: str) -> None:
    _assert_first_time_twice(repo, VARIANTS[name], session=None)


@pytest.mark.parametrize("name", [n for n in ONE_PER_HOOK if not VARIANTS[n].uses_cwd])
def test_an_unreadable_cwd_gives_the_first_time_message_N1(repo: Path, name: str) -> None:
    _assert_first_time_twice(repo, VARIANTS[name], cwd=str(repo.parent / "no-such-dir"))


def test_the_repeat_shape_is_one_line_then_the_original_F12(repo: Path) -> None:
    """The fixed shape: `STOP: this block repeated. <hook> refused the same call again; it read
    <source>. Do not retry. Owner action: <action>.` and a newline, then the first message."""
    v = VARIANTS["gate-bash"]
    first, second = _replay(repo, v)
    head = _header(first, second)
    assert re.fullmatch(
        r"STOP: this block repeated\. gate-bash\.sh refused the same call again; it read .+?\. "
        r"Do not retry\. Owner action: .+\n",
        head,
        re.S,
    ), head
