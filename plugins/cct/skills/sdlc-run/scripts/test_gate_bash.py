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
    for name in ("gate-bash.sh", "plan-gate.sh", "sdlc-config.sh"):
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
