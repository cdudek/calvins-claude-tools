"""The records guard: agents neither read nor write the runs folder; one plain runner call is the only way in."""
import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "sdlc-records-guard.py"
RUNNER = str(Path(__file__).resolve().parent.parent / "skills" / "sdlc-run" / "runner" / "sdlc.py")


def run(tool, tool_input, home, cwd=None, env=None):
    ev = {"tool_name": tool, "tool_input": tool_input, **({"cwd": str(cwd)} if cwd else {})}
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev), capture_output=True, text=True,
                       env={**os.environ, "SDLC_HOME": str(home), **(env or {})})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else None


def bash(cmd, home, **kw):
    return run("Bash", {"command": cmd}, home, **kw)


def test_writes_and_reads_of_the_records_are_denied(tmp_path):
    f = tmp_path / "runs" / "r1" / "receipts" / "x.json"
    for tool in ("Write", "Edit", "MultiEdit", "Read"):
        assert run(tool, {"file_path": str(f)}, tmp_path) == "deny", tool
    assert run("Grep", {"pattern": "PASS", "path": str(tmp_path / "runs")}, tmp_path) == "deny"
    assert run("Grep", {"pattern": "PASS", "path": str(tmp_path)}, tmp_path) == "deny"  # a recursive search from above
    assert run("Glob", {"pattern": "**/*.json", "path": str(tmp_path / "runs" / "r1")}, tmp_path) == "deny"
    assert run("Read", {"file_path": str(tmp_path / "briefs" / "r1" / "t1" / "brief.md")}, tmp_path) is None  # a brief is readable
    assert run("Grep", {"pattern": "x", "path": str(tmp_path / "work")}, tmp_path) is None


def test_every_way_to_name_the_folder_is_denied(tmp_path):
    home = tmp_path / ".sdlc"
    for cmd in ("rm -rf ~/.sdlc/*", "rm -rf ~/.sdlc/r*", "X=.sdlc; rm -rf ~/$X/runs", "echo hi\nrm -rf ~/.sdlc/runs",
                "cat $HOME/.sdlc/runs/r1/run.json", "ls ~/.s*", "ls ~/.sdl?/runs", "cat ~/.[s]dlc/runs/x", "rm -rf ~/.'sd'lc",
                f"cd {home}/runs && echo x > f", f"cat {home}/runs/r1/run.json", "SDLC_HOME=/x python3 -c 'pass'"):
        assert bash(cmd, home, env={"SDLC_HOME": str(home)}) == "deny", cmd


def test_only_one_plain_runner_call_may_touch_the_records(tmp_path):
    home = tmp_path / ".sdlc"
    env = {"SDLC_HOME": str(home)}
    assert bash(f"python3 {RUNNER} check r1 --note ~/.sdlc/runs/r1", home, env=env) is None
    assert bash(f"{RUNNER} status", home, env=env) is None
    for cmd in (f"python3 {RUNNER} check r1; rm -rf ~/.sdlc/runs", f"python3 {RUNNER} check ~/.sdlc && rm -rf ~/.sdlc", f"python3 {RUNNER} status | tee ~/.sdlc/runs/x",
                f"python3 {RUNNER} status `rm -rf ~/.sdlc`", f"python3 {RUNNER} status $(rm -rf ~/.sdlc)", f"python3 {RUNNER} check x\nrm -rf ~/.sdlc",
                "./sdlc check ~/.sdlc/runs/r1", "sdlc check ~/.sdlc/runs/r1", f"python3 /tmp/fake/sdlc.py check ~/.sdlc/runs/r1",
                f"X=1 python3 {RUNNER} check ~/.sdlc"):
        assert bash(cmd, home, env=env) == "deny", cmd


def test_unrelated_commands_pass_including_unparsable_ones(tmp_path):
    home = tmp_path / ".sdlc"
    env = {"SDLC_HOME": str(home)}
    for cmd in ("git status", "ls *.py", "python3 -m pytest -q", "git commit -m \"it's fine\"", "cat <<EOF\nit's\nEOF", "echo 'unbalanced"):
        assert bash(cmd, home, env=env) is None, cmd
    assert bash("echo 'unbalanced ~/.sdlc", home, env=env) == "deny"
    assert bash("git status", home, cwd=home / "runs", env=env) == "deny"  # a shell inside the records is the records
    assert bash("git status", home, cwd=tmp_path, env=env) is None


def test_a_command_that_sets_the_gate_override_is_denied(tmp_path):
    assert bash("SDLC_GATE_CMD=true python3 -m pytest", tmp_path / "h") == "deny"
    assert bash("env SDLC_GATE_CMD=true sdlc gate x", tmp_path / "h") == "deny"


def test_n1_hook_bypasses_are_denied(tmp_path):
    home = tmp_path / ".sdlc"
    env = {"SDLC_HOME": str(home)}
    runner_dir = str(Path(RUNNER).parent)
    for cmd in (
        f"python3 -c \"import sys;sys.path.insert(0,'{runner_dir}');import contract,store;contract.approve('r','agent')\"",
        "python3 - <<'EOF'\nimport sys\nsys.path.insert(0, 'plugins/cct/skills/sdlc-run/runner')\nimport contract\nEOF",
        "python3 -c 'import store; store.write_json(1, 2)'",
        "python3 -c 'from engine import restart'",
        f"PATH=/tmp/fake:$PATH python3 {RUNNER} gate r1 --by x",
        f"HOME=/tmp/h python3 {RUNNER} gate r1 --by x",
        f"PYTHONPATH=/tmp/x python3 {RUNNER} gate r1 --by x",
        f"env PATH=/tmp/fake python3 {RUNNER} gate r1 --by x",
        f"env -i python3 {RUNNER} check r1",
        "./sdlc gate r1 --by x",
        "./sdlc.py gate r1 --by x",
        "python3 sdlc.py gate r1 --by x",
        "python3 ../runner/sdlc.py gate r1 --by x",
        "python3 /tmp/fake/runner/sdlc.py gate r1 --by x",
        f"python3 -I {RUNNER} gate r1 --by x",
    ):
        assert bash(cmd, home, env=env) == "deny", cmd
    assert bash(f"python3 {RUNNER} gate r1 --by owner", home, env=env) is None  # exactly one plain call of the plugin's runner
    assert bash(f"{RUNNER} check r1", home, env=env) is None
    assert bash("python3 -c 'print(1)'", home, env=env) is None
    assert bash("git commit -m 'import store'", home, env=env) is None  # prose is not an import
    assert bash("git diff plugins/cct/skills/sdlc-run/runner/engine.py", home, env=env) is None  # reading the code is not running it
    assert bash("git add sdlc.py", home, env=env) is None


def test_the_glob_is_tested_on_every_path_component(tmp_path):
    home = tmp_path / ".sdlc"
    for cmd in ("cat ~/.s?lc/runs/*/contract.json", "cat ~/.s*/runs/*/receipts/*.json", "ls ~/.sdlc/r*/*/contract.json",
                "cat ~/.[s]dlc/runs/r1/contract.json", "cat ~/.sd?c/*/run1/*.json"):
        assert bash(cmd, home, env={"SDLC_HOME": str(home)}) == "deny", cmd
    real_home = os.path.expanduser("~")
    for cmd in (f"cat {real_home}/.s?lc/runs/*/contract.json",):
        assert bash(cmd, Path(real_home) / ".sdlc") == "deny", cmd
    assert bash("ls ~/projects/*/src/*.py", home) is None
