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
                         "tool_input": {"file_path": "/home/x/.factory/scenarios/repo/s/a.md"}})
        assert code == 0 and denied(out), agent


def test_builder_bash_with_tilde_denied():
    code, out = run({"agent_type": "factory:builder", "tool_name": "Bash",
                     "tool_input": {"command": "cat ~/.factory/scenarios/repo/s/a.md"}})
    assert denied(out)


def test_verifier_and_coordinator_allowed():
    path = {"file_path": "/home/x/.factory/scenarios/repo/s/a.md"}
    assert run({"agent_type": "factory:verifier", "tool_name": "Read", "tool_input": path})[1] is None
    assert run({"agent_type": "verifier", "tool_name": "Read", "tool_input": path})[1] is None
    assert run({"tool_name": "Read", "tool_input": path})[1] is None


def test_unrelated_calls_and_bad_input_pass():
    assert run({"agent_type": "factory:builder", "tool_name": "Read", "tool_input": {"file_path": "src/a.ts"}})[1] is None
    p = subprocess.run([sys.executable, str(SCRIPT)], input="not json", capture_output=True, text=True)
    assert p.returncode == 0 and not p.stdout.strip()


def test_malformed_input_with_marker_denied_without_marker_allowed():
    for raw in ('["~/.factory/scenarios/a.md"]', '"factory/scenarios"'):
        p = subprocess.run([sys.executable, str(SCRIPT)], input=raw, capture_output=True, text=True)
        assert denied(json.loads(p.stdout)), raw
    for raw in ("[1]", "null", '{"agent_type": 5, "tool_input": []}'):
        p = subprocess.run([sys.executable, str(SCRIPT)], input=raw, capture_output=True, text=True)
        assert p.returncode == 0 and not p.stdout.strip(), raw


def test_crash_in_decide_denies_when_marker_named(monkeypatch=None):
    # tool_input as a list: .get fails inside decide for the old code path; the marker still denies
    code, out = run({"agent_type": "factory:builder", "tool_input": "cat ~/.factory/scenarios/x"})
    assert denied(out)


def test_aliases_and_split_names_denied():
    for cmd in ("cat $HOME/.factory/scenarios/x", "cat ${HOME}/.factory//scenarios/x", "cat ~/.factory/./scenarios/x",
                "cd ~/.factory && cat scenarios/x", "cat .factory/scenarios/x"):
        code, out = run({"agent_type": "factory:builder", "tool_name": "Bash", "tool_input": {"command": cmd}})
        assert denied(out), cmd
    code, out = run({"agent_type": "factory:builder", "tool_name": "Agent",
                     "tool_input": {"prompt": "read ~/.factory/scenarios and report"}})
    assert denied(out)


def test_eval_mode_denies_main_session_but_not_verifier():
    path = {"file_path": "/home/x/.factory/scenarios/repo/s/a.md"}
    env = {**os.environ, "FACTORY_EVAL": "1"}

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


def test_eval_mode_main_session_may_dispatch_the_verifier_only():
    env = {**os.environ, "FACTORY_EVAL": "1"}

    def go(event):
        p = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(event), capture_output=True, text=True, env=env)
        return json.loads(p.stdout) if p.stdout.strip() else None
    prompt = "read ~/.factory/scenarios/repo/s and verify"
    assert go({"tool_name": "Agent", "tool_input": {"subagent_type": "factory:verifier", "prompt": prompt}}) is None
    for sub in ("factory:builder", "verifier"):  # a bare alias could name another plugin's agent
        assert denied(go({"tool_name": "Agent", "tool_input": {"subagent_type": sub, "prompt": prompt}})), sub
    assert denied(go({"tool_name": "Bash", "tool_input": {"command": "cat ~/.factory/scenarios/x", "subagent_type": "verifier"}}))


def _bg(env_extra, cwd, bg):
    ti = {"subagent_type": "factory:builder", "prompt": "x"}
    if bg:
        ti["run_in_background"] = True
    env = {k: v for k, v in os.environ.items() if k != "FACTORY_EVAL"}
    p = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps({"tool_name": "Agent", "cwd": str(cwd), "tool_input": ti}),
                       capture_output=True, text=True, env={**env, **env_extra})
    return json.loads(p.stdout) if p.stdout.strip() else None


def test_background_agent_denied_in_a_factory_run(tmp_path):
    out = _bg({"FACTORY_EVAL": "1"}, tmp_path, True)
    assert denied(out) and "without run_in_background" in out["hookSpecificOutput"]["permissionDecisionReason"]
    repo = tmp_path / "r"
    (repo / ".factory").mkdir(parents=True)
    for cmd in (["init", "-q"], ["checkout", "-q", "-b", "milestone/x-M1"]):
        subprocess.run(["git", "-C", str(repo), *cmd], check=True)
    assert denied(_bg({}, repo, True))


def test_foreground_agent_allowed_in_a_factory_run(tmp_path):
    assert _bg({"FACTORY_EVAL": "1"}, tmp_path, False) is None


def test_background_agent_allowed_outside_a_factory_run(tmp_path):
    assert _bg({}, tmp_path, True) is None
    repo = tmp_path / "r"
    (repo / ".factory").mkdir(parents=True)
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    assert _bg({}, repo, True) is None  # .factory/ alone, no milestone branch
