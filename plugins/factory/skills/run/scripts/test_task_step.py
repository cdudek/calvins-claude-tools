import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "task-step.py"
SLUG = "2026-11-24-x"
PLAN = {"change": SLUG, "base": "main", "goalTurns": 12, "requirements": ["req-1"], "setup": "touch .setup-ran",
        "milestones": [{"id": "M1", "layer": "backend", "covers": ["req-1"], "tasks": [
            {"id": "T1", "covers": ["req-1"], "files": ["src/a.ts"], "check": "true"},
            {"id": "T2", "covers": ["req-1"], "files": ["src/b.ts"], "check": "true"}]}]}
P = f"changes/{SLUG}/plan.md"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def step(repo, *args):
    p = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=repo, capture_output=True, text=True)
    return p.returncode, p.stdout


def milestone_repo(tmp_path):
    """A repo with an origin holding main (with the approved plan), on branch milestone/<slug>-M1; returns (repo, approved sha)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    files = {P: "# Plan\n\n```json factory\n" + json.dumps(PLAN, indent=1) + "\n```\n\n## Progress log\n",
             f"changes/{SLUG}/delta.md": "### ADDED Requirements\n- req-1: When a, the system shall b [outcome-1]\n",
             f"changes/{SLUG}/intent.md": "- outcome-1: people do x\n", "README.md": "x\n"}
    for name, text in files.items():
        f = repo / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "plan")
    (repo / ".git/info/exclude").write_text(".worktrees/\n")
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "origin", "main")
    sha = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-qc", f"milestone/{SLUG}-M1")
    return repo, sha


def build(wt, name, text="x\n"):
    f = wt / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    git(wt, "add", name)
    git(wt, "commit", "-qm", f"build {name}")


def test_full_flow_target_start_finish_gate_status(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    code, out = step(repo, "target", P, "M1")
    assert code == 0 and out.strip() == f"TARGET OK {sha}"
    code, out = step(repo, "start", P, "M1", "T1")
    wt = repo / ".worktrees" / f"{SLUG}-M1-T1"
    assert code == 0 and out.strip() == f"START OK T1 {wt} {git(repo, 'rev-parse', 'HEAD')}" and (wt / ".setup-ran").exists()
    assert step(repo, "start", P, "M1", "T1")[1].startswith("START OK T1") and "reused" in step(repo, "start", P, "M1", "T1")[1]
    build(wt, "src/a.ts")
    code, out = step(repo, "finish", P, "M1", "T1", "--approved", sha)
    built = git(wt, "rev-parse", "HEAD")
    assert code == 0 and f"FINISH OK T1 INTEGRITY OK builder={built} merged={git(repo, 'rev-parse', 'HEAD')}" in out
    assert git(repo, "rev-parse", "HEAD^2") == built  # the checked commit itself was merged
    st = json.loads((repo / ".factory/state/M1.json").read_text())
    assert st["checked"] == [built] and st["tasks"]["T1"]["builder"] == built and st["target"] == sha
    assert git(repo, "status", "--porcelain") == ""  # state is git-ignored
    step(repo, "start", P, "M1", "T2")
    build(repo / ".worktrees" / f"{SLUG}-M1-T2", "src/b.ts")
    assert step(repo, "finish", P, "M1", "T2", "--approved", sha)[0] == 0
    code, out = step(repo, "gate", P, "M1", "--approved", sha)
    assert code == 0 and "GATE integrity OK" in out and "GATE check-plan OK" in out, out
    code, out = step(repo, "status", P, "M1")
    assert code == 0 and f"target={sha}" in out and "T1:" in out and "T2:" in out


def test_finish_fails_on_a_path_outside_the_task_and_merges_nothing(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    step(repo, "target", P, "M1")
    step(repo, "start", P, "M1", "T1")
    wt = repo / ".worktrees" / f"{SLUG}-M1-T1"
    build(wt, "src/a.ts")
    build(wt, "src/stray.ts")
    before = git(repo, "rev-parse", "HEAD")
    code, out = step(repo, "finish", P, "M1", "T1", "--approved", sha)
    assert code == 1 and "FINISH FAIL T1 integrity" in out and "INTEGRITY FAIL outside task T1: src/stray.ts" in out
    assert git(repo, "rev-parse", "HEAD") == before and json.loads((repo / ".factory/state/M1.json").read_text())["checked"] == []


def test_gate_fails_for_a_change_made_after_the_builder_check(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    step(repo, "target", P, "M1")
    code, out = step(repo, "gate", P, "M1", "--approved", sha)
    assert code == 1 and "GATE FAIL no task has passed `finish` yet" in out
    step(repo, "start", P, "M1", "T1")
    build(repo / ".worktrees" / f"{SLUG}-M1-T1", "src/a.ts")
    assert step(repo, "finish", P, "M1", "T1", "--approved", sha)[0] == 0
    (repo / "src/a.ts").write_text("edited after the check\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "direct")
    code, out = step(repo, "gate", P, "M1", "--approved", sha)
    assert code == 1 and "GATE integrity FAIL" in out and "changed after the builder check: src/a.ts" in out


def test_finish_gate_need_a_target_and_bad_ids_are_refused(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    assert step(repo, "finish", P, "M1", "T1", "--approved", sha) == (1, "FINISH FAIL no target SHA recorded: run `target` first\n")
    assert step(repo, "start", P, "M1", "../evil")[0] == 1
    assert step(repo, "start", P, "x;rm", "T1")[0] == 2
    assert step(repo, "bogus", P, "M1")[0] == 2


def test_pin_is_recorded_and_passed_to_integrity(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    assert step(repo, "pin", P, "M1", sha) == (0, f"PIN OK {sha}\n")
    assert json.loads((repo / ".factory/state/M1.json").read_text())["pin"] == sha
    assert step(repo, "pin", P, "M1", "deadbeef")[0] == 1
