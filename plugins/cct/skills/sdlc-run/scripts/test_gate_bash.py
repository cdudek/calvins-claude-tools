"""gate-bash.sh and plan-gate.sh: the Bash blocklist from sdlc.json, and the plan hook that must
never block. Negative fixtures first: each blocked command is one a real run reached for."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "templates" / "hooks"
BLOCKED = [
    {
        "match": r"(^|[[:space:];&|(])kubectl([[:space:]]+[^[:space:];&|]+)*[[:space:]]+(apply|delete)([[:space:]]|$)",
        "message": "the cluster changes through Argo CD from a merged PR.",
    },
    {"match": r"(^|[[:space:];&|(])uv[[:space:]]+add([[:space:]]|$)", "message": "ask first."},
]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    for name in ("gate-bash.sh", "plan-gate.sh", "sdlc-config.sh", "block_state.py"):
        if (HOOKS / name).exists():  # the helper sits beside the hook; absent in older trees
            shutil.copy(HOOKS / name, tmp_path / ".claude" / "hooks" / name)
    (tmp_path / "sdlc.json").write_text(json.dumps({"blocked": BLOCKED}))
    return tmp_path


def _bash(repo: Path, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / "gate-bash.sh")],
        input=json.dumps({"tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(repo)},
    )


@pytest.mark.parametrize(
    "command",
    [
        "kubectl apply -f x.yaml",
        "cd x && kubectl -n prod delete job migrate",
        "uv add httpx",
        "echo ok; uv add httpx",
    ],
)
def test_a_blocked_command_is_refused_with_its_route(repo: Path, command: str) -> None:
    r = _bash(repo, command)
    assert r.returncode == 2 and r.stderr.startswith("BLOCKED: ")


@pytest.mark.parametrize("command", ["kubectl get pods", "uv run pytest", "git status"])
def test_permitted_commands_pass(repo: Path, command: str) -> None:
    assert _bash(repo, command).returncode == 0


def test_a_repo_without_sdlc_json_gets_no_opinion(repo: Path) -> None:
    (repo / "sdlc.json").unlink()
    assert _bash(repo, "kubectl apply -f x.yaml").returncode == 0


def test_plan_gate_never_blocks_and_stays_quiet_without_plannotator(
    repo: Path, tmp_path: Path
) -> None:
    config = tmp_path / "claude-config"
    config.mkdir()
    (config / "plugins").mkdir()
    (config / "plugins" / "installed_plugins.json").write_text('{"plannotator@plannotator": {}}')
    r = subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / "plan-gate.sh")],
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_CONFIG_DIR": str(config), "PATH": "/usr/bin:/bin"},
    )
    assert r.returncode == 0 and r.stdout == "" and r.stderr == ""


OLD_CONFIG = """SDLC_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SDLC_JSON="$SDLC_ROOT/sdlc.json"
sdlc_get() { :; }
"""  # sdlc-config.sh before the fast hooks: no $SDLC_PY, no python-free helpers


def test_a_new_hook_under_an_old_config_still_blocks_F4(repo: Path) -> None:
    """`adopt --replace` swaps one file at a time: the hook must not need the new config."""
    (repo / ".claude" / "hooks" / "sdlc-config.sh").write_text(OLD_CONFIG)
    r = _bash(repo, "uv add httpx")
    assert r.returncode == 2 and r.stderr.startswith("BLOCKED: ")


def test_a_new_config_still_offers_sdlc_field_to_old_hooks_F4(repo: Path) -> None:
    script = (
        f'. "{repo}/.claude/hooks/sdlc-config.sh"; '
        "sdlc_field '{\"tool_input\": {\"command\": \"uv add x\"}}' command"
    )
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert r.stdout.strip() == "uv add x"


def test_a_malformed_rule_is_skipped_and_the_valid_ones_still_apply_F14(repo: Path) -> None:
    good = BLOCKED[1]
    for rules in ([good, {"message": "no match"}], [{"message": "no match"}, good], [good, 7]):
        (repo / "sdlc.json").write_text(json.dumps({"blocked": rules}))
        r = _bash(repo, "uv add httpx")
        assert r.returncode == 2 and "BLOCKED: ask first." in r.stderr, rules
        assert "blocked[" in r.stderr and "skipped" in r.stderr, rules


@pytest.mark.parametrize(
    "command",
    [
        "echo x > ~/.claude/projects/p/s.jsonl",
        "echo x >> $HOME/.claude/projects/p/s.jsonl",
        "cat a | tee ~/.claude/projects/p/s.jsonl",
        "cp forged.jsonl ~/.claude/projects/p/s.jsonl",
        "mv forged.jsonl ~/.claude/projects/p/",
        "sed -i 's/a/b/' ~/.claude/projects/p/s.jsonl",
        "cd ~/.claude/projects/p && printf x > s.jsonl",
        "python3 -c \"open('/Users/x/.claude/projects/p/s.jsonl','w')\"",
    ],
)
def test_bash_writes_into_the_session_transcripts_are_refused(repo: Path, command: str) -> None:
    r = _bash(repo, command)
    assert r.returncode == 2 and "session transcripts" in r.stderr


@pytest.mark.parametrize(
    "command",
    ["cat ~/.claude/projects/p/s.jsonl", "grep -c user ~/.claude/projects/p/s.jsonl > /tmp/n"],
)
def test_reading_the_session_transcripts_is_not_refused(repo: Path, command: str) -> None:
    assert _bash(repo, command).returncode == 0


def test_the_transcript_guard_holds_without_any_blocked_rules(repo: Path) -> None:
    (repo / "sdlc.json").write_text("{}")
    assert _bash(repo, "echo x > ~/.claude/projects/p/s.jsonl").returncode == 2
