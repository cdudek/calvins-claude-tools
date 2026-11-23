"""The records guard denies agent writes under the runs folder and nothing else."""
import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "sdlc-records-guard.py"


def run(tool, tool_input, home, cwd=None):
    ev = {"tool_name": tool, "tool_input": tool_input, **({"cwd": str(cwd)} if cwd else {})}
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev), capture_output=True, text=True,
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


def test_runner_token_does_not_whitelist_a_composite(tmp_path):
    f = tmp_path / "runs" / "r1" / "run.json"
    assert run("Bash", {"command": f"python3 /x/sdlc-run/runner/sdlc.py check r1; echo x > {f}"}, tmp_path) == "deny"
    assert run("Bash", {"command": f"sdlc check r1 && rm -rf {tmp_path}/runs"}, tmp_path) == "deny"
    assert run("Bash", {"command": f"sdlc status | tee {f}"}, tmp_path) == "deny"
    assert run("Bash", {"command": f"sdlc status `rm {f}`"}, tmp_path) == "deny"
    assert run("Bash", {"command": f"sdlc status $(rm {f})"}, tmp_path) == "deny"
    assert run("Bash", {"command": "python3 /x/sdlc-run/runner/sdlc.py check r1"}, tmp_path) is None
    assert run("Bash", {"command": f"sdlc check r1 > {tmp_path}/out.txt"}, tmp_path) is None  # no record is touched


def test_cd_into_the_records_then_write_is_denied(tmp_path):
    (tmp_path / "runs").mkdir()
    assert run("Bash", {"command": f"cd {tmp_path}/runs && echo x > f"}, tmp_path) == "deny"
    assert run("Bash", {"command": f"cd {tmp_path} && cd runs && echo x > f"}, tmp_path) == "deny"
    assert run("Bash", {"command": "echo x > f"}, tmp_path, cwd=tmp_path / "runs") == "deny"
    assert run("Bash", {"command": "git status"}, tmp_path, cwd=tmp_path) is None  # a parent of the records is not the records
    assert run("Bash", {"command": f"ln -s {tmp_path}/runs/r1 /tmp/l1 && rm /tmp/l1/run.json"}, tmp_path) == "deny"


def test_obfuscated_and_unparsable_commands(tmp_path):
    assert run("Bash", {"command": f"rm -rf {tmp_path}/ru''ns"}, tmp_path) == "deny"
    assert run("Bash", {"command": f"echo 'unbalanced > {tmp_path}/runs/x"}, tmp_path) == "deny"
    assert run("Bash", {"command": "python3 -c 'import os; os.remove(\"" + str(tmp_path) + "/runs/x\")'"}, tmp_path) == "deny"
    assert run("Bash", {"command": "echo 'unbalanced"}, tmp_path) is None
