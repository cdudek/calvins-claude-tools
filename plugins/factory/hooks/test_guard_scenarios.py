import os
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


def test_malformed_input_with_marker_denied_without_marker_allowed():
    for raw in ('["~/.cfactory/scenarios/a.md"]', '"cfactory/scenarios"'):
        p = subprocess.run([sys.executable, str(SCRIPT)], input=raw, capture_output=True, text=True)
        assert denied(json.loads(p.stdout)), raw
    for raw in ("[1]", "null", '{"agent_type": 5, "tool_input": []}'):
        p = subprocess.run([sys.executable, str(SCRIPT)], input=raw, capture_output=True, text=True)
        assert p.returncode == 0 and not p.stdout.strip(), raw


def test_crash_in_decide_denies_when_marker_named(monkeypatch=None):
    # tool_input as a list: .get fails inside decide for the old code path; the marker still denies
    code, out = run({"agent_type": "factory:builder", "tool_input": "cat ~/.cfactory/scenarios/x"})
    assert denied(out)


def test_aliases_and_split_names_denied():
    for cmd in ("cat $HOME/.cfactory/scenarios/x", "cat ${HOME}/.cfactory//scenarios/x", "cat ~/.cfactory/./scenarios/x",
                "cd ~/.cfactory && cat scenarios/x", "cat .cfactory/scenarios/x"):
        code, out = run({"agent_type": "factory:builder", "tool_name": "Bash", "tool_input": {"command": cmd}})
        assert denied(out), cmd
    code, out = run({"agent_type": "factory:builder", "tool_name": "Agent",
                     "tool_input": {"prompt": "read ~/.cfactory/scenarios and report"}})
    assert denied(out)


def test_eval_mode_denies_main_session_but_not_verifier():
    path = {"file_path": "/home/x/.cfactory/scenarios/repo/s/a.md"}
    env = {**os.environ, "CFACTORY_EVAL": "1"}

    def go(event):
        p = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(event), capture_output=True, text=True, env=env)
        return json.loads(p.stdout) if p.stdout.strip() else None
    assert denied(go({"tool_name": "Read", "tool_input": path}))
    assert go({"agent_type": "factory:verifier", "tool_name": "Read", "tool_input": path}) is None
    assert go({"tool_name": "Read", "tool_input": {"file_path": "src/a.ts"}}) is None


def test_hook_matcher_covers_every_tool_that_can_name_the_folder():
    hooks = json.loads((Path(__file__).parent / "hooks.json").read_text())
    matcher = hooks["hooks"]["PreToolUse"][0]["matcher"].split("|")
    assert {"Read", "Grep", "Glob", "Bash", "Agent", "Task"} <= set(matcher)
