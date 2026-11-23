"""The records guard denies agent writes under the runs folder and nothing else."""
import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "sdlc-records-guard.py"


def run(tool, tool_input, home):
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"tool_name": tool, "tool_input": tool_input}), capture_output=True, text=True,
                       env={**os.environ, "SDLC_HOME": str(home)})
    assert r.returncode == 0
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else None


def test_writes_under_runs_are_denied(tmp_path):
    f = tmp_path / "runs" / "r1" / "receipts" / "x.json"
    assert run("Write", {"file_path": str(f)}, tmp_path) == "deny"
    assert run("Edit", {"file_path": str(f)}, tmp_path) == "deny"
    assert run("Bash", {"command": f"echo '{{}}' > {f}"}, tmp_path) == "deny"
    assert run("Bash", {"command": f"python3 -c 'open(\"{f}\",\"w\")'"}, tmp_path) == "deny"
    assert run("Bash", {"command": f"rm -rf {tmp_path}/runs/r1"}, tmp_path) == "deny"


def test_reads_the_runner_and_other_paths_pass(tmp_path):
    f = tmp_path / "runs" / "r1" / "run.json"
    assert run("Bash", {"command": f"cat {f}"}, tmp_path) is None
    assert run("Bash", {"command": f"ls {tmp_path}/runs"}, tmp_path) is None
    assert run("Bash", {"command": "python3 /x/sdlc-run/runner/sdlc.py check r1"}, tmp_path) is None
    assert run("Write", {"file_path": str(tmp_path / "work" / "a.txt")}, tmp_path) is None
    assert run("Bash", {"command": "git status"}, tmp_path) is None
