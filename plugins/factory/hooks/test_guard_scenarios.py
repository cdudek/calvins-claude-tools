import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "guard-scenarios.py"


def run(event):
    p = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(event), capture_output=True, text=True)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip() else None)


def denied(out):
    return out and out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_builder_read_denied():
    for agent in ("factory:builder", "builder", "factory:ux-verifier", "old-prefix:verifier", "other-plugin:verifier", "general-purpose"):
        code, out = run({"agent_type": agent, "tool_name": "Read",
                         "tool_input": {"file_path": "/home/x/.cfactory/scenarios/repo/s/a.md"}})
        assert code == 0 and denied(out), agent


def test_builder_bash_with_tilde_denied():
    code, out = run({"agent_type": "factory:builder", "tool_name": "Bash",
                     "tool_input": {"command": "cat ~/.cfactory/scenarios/repo/s/a.md"}})
    assert denied(out)


def test_verifier_and_coordinator_allowed():
    path = {"file_path": "/home/x/.cfactory/scenarios/repo/s/a.md"}
    assert run({"agent_type": "factory:verifier", "tool_name": "Read", "tool_input": path})[1] is None
    assert run({"agent_type": "verifier", "tool_name": "Read", "tool_input": path})[1] is None
    assert run({"tool_name": "Read", "tool_input": path})[1] is None


def test_unrelated_calls_and_bad_input_pass():
    assert run({"agent_type": "factory:builder", "tool_name": "Read", "tool_input": {"file_path": "src/a.ts"}})[1] is None
    p = subprocess.run([sys.executable, str(SCRIPT)], input="not json", capture_output=True, text=True)
    assert p.returncode == 0 and not p.stdout.strip()
