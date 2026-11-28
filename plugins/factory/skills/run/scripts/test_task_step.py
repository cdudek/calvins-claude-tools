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


def milestone_repo(tmp_path, plan=PLAN):
    """A repo with an origin holding main (with the approved plan), on branch milestone/<slug>-M1; returns (repo, approved sha)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    files = {P: "# Plan\n\n```json factory\n" + json.dumps(plan, indent=1) + "\n```\n\n## Progress log\n",
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


def ok(repo, sha, cmd, *args):
    return step(repo, cmd, P, "M1", *args, "--approved", sha)


def test_full_flow_target_start_finish_gate_status(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    code, out = ok(repo, sha, "target")
    assert code == 0 and out.strip() == f"TARGET OK {sha}"
    code, out = ok(repo, sha, "start", "T1")
    wt = repo / ".worktrees" / f"{SLUG}-M1-T1"
    assert code == 0 and out.strip() == f"START OK T1 {wt} {git(repo, 'rev-parse', 'HEAD')}" and (wt / ".setup-ran").exists()
    assert "reused" in ok(repo, sha, "start", "T1")[1]
    build(wt, "src/a.ts")
    built = git(wt, "rev-parse", "HEAD")
    code, out = ok(repo, sha, "finish", "T1")
    assert code == 0 and f"FINISH OK T1 INTEGRITY OK builder={built} merged={git(repo, 'rev-parse', 'HEAD')} worktree removed" in out
    assert not wt.exists() and git(repo, "rev-parse", f"{SLUG}-M1-T1") == built  # the checkout goes, the branch keeps the work
    assert "FINISH OK T1 already merged" in ok(repo, sha, "finish", "T1")[1]
    assert git(repo, "rev-parse", "HEAD^2") == built and git(repo, "log", "-1", "--format=%s").startswith("factory-merge: ")
    st = json.loads((repo / ".factory/state/M1.json").read_text())
    assert st["checked"] == [built] and st["tasks"]["T1"]["builder"] == built and st["target"] == sha
    assert git(repo, "status", "--porcelain") == ""  # state is git-ignored
    ok(repo, sha, "start", "T2")
    build(repo / ".worktrees" / f"{SLUG}-M1-T2", "src/b.ts")
    assert ok(repo, sha, "finish", "T2")[0] == 0
    code, out = ok(repo, sha, "gate")
    assert code == 0 and "GATE integrity OK" in out and "GATE check-plan OK" in out, out
    code, out = ok(repo, sha, "status")
    assert code == 0 and f"target={sha}" in out and "T1:" in out and "T2:" in out and out.count(",") >= 2


def test_finish_keeps_a_worktree_with_an_uncommitted_tracked_edit(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    ok(repo, sha, "target")
    ok(repo, sha, "start", "T1")
    wt = repo / ".worktrees" / f"{SLUG}-M1-T1"
    build(wt, "src/a.ts")
    (wt / "src/a.ts").write_text("edited after the commit\n")
    code, out = ok(repo, sha, "finish", "T1")
    assert code == 0 and "worktree removed" not in out and (wt / "src/a.ts").read_text() == "edited after the commit\n"


def test_finish_fails_on_a_path_outside_the_task_and_merges_nothing(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    ok(repo, sha, "target")
    ok(repo, sha, "start", "T1")
    wt = repo / ".worktrees" / f"{SLUG}-M1-T1"
    build(wt, "src/a.ts")
    build(wt, "src/stray.ts")
    before = git(repo, "rev-parse", "HEAD")
    code, out = ok(repo, sha, "finish", "T1")
    assert code == 1 and "FINISH FAIL T1 integrity" in out and "INTEGRITY FAIL outside task T1: src/stray.ts" in out
    assert git(repo, "rev-parse", "HEAD") == before and json.loads((repo / ".factory/state/M1.json").read_text())["checked"] == []


def test_gate_fails_for_a_change_made_after_the_builder_check(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    ok(repo, sha, "target")
    code, out = ok(repo, sha, "gate")
    assert code == 1 and "GATE FAIL no task has passed `finish` yet" in out
    ok(repo, sha, "start", "T1")
    build(repo / ".worktrees" / f"{SLUG}-M1-T1", "src/a.ts")
    assert ok(repo, sha, "finish", "T1")[0] == 0
    (repo / "src/a.ts").write_text("edited after the check\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "direct")
    code, out = ok(repo, sha, "gate")
    assert code == 1 and "GATE integrity FAIL" in out and "changed after the builder check: src/a.ts" in out


def test_a_sha_added_to_the_state_file_never_reaches_checked(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    ok(repo, sha, "target")
    (repo / "src").mkdir()
    (repo / "src/a.ts").write_text("sneaked in\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "direct")
    sneaked = git(repo, "rev-parse", "HEAD")
    f = repo / ".factory/state/M1.json"
    st = json.loads(f.read_text())
    st["checked"] = [sneaked]
    st["tasks"]["T1"] = {"builder": sneaked, "merged": sneaked}
    f.write_text(json.dumps(st))
    code, out = ok(repo, sha, "gate")
    assert code == 1 and "no task has passed `finish` yet" in out
    assert f"checked={sneaked}" not in ok(repo, sha, "status")[1]


def test_setup_comes_from_the_approved_commit_not_the_working_file(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    ok(repo, sha, "target")
    plan = repo / P
    plan.write_text(plan.read_text().replace('"setup": "touch .setup-ran"', '"setup": "touch .pwned"'))  # uncommitted edit
    assert ok(repo, sha, "start", "T1")[0] == 0
    wt = repo / ".worktrees" / f"{SLUG}-M1-T1"
    assert (wt / ".setup-ran").exists() and not (wt / ".pwned").exists()


def test_bad_arguments_are_refused(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    assert step(repo, "finish", P, "M1", "T1") [0] == 2  # --approved is required
    assert step(repo, "start", P, "M1", "T1")[0] == 2
    for bad in ("../evil", "T1;x", "M1-gap9", "M1-gap0", "M1-gapx", "-rf"):
        assert ok(repo, sha, "start", bad)[0] == 2, bad
    assert ok(repo, sha, "bogus")[0] == 2
    code, out = step(repo, "target", P, "x;rm", "--approved", sha)
    assert code == 1 and "not a milestone id" in out
    code, out = step(repo, "target", str(repo / P), "M1", "--approved", sha)
    assert code == 1 and "repo-relative" in out
    code, out = step(repo, "target", "../plan.md", "M1", "--approved", sha)
    assert code == 1 and "repo-relative" in out
    code, out = step(repo, "target", P, "M1", "--approved", "deadbeef")
    assert code == 1 and "not a commit" in out
    code, out = step(repo, "target", "changes/nope.md", "M1", "--approved", sha)
    assert code == 1 and "does not exist at approved" in out


def test_finish_and_gate_need_a_valid_target(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    assert ok(repo, sha, "finish", "T1")[0] == 1 and "no valid target SHA" in ok(repo, sha, "finish", "T1")[1]
    f = repo / ".factory/state/M1.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"target": "0" * 40, "pin": None, "checked": [], "tasks": {}}))
    assert "no valid target SHA" in ok(repo, sha, "gate")[1]


def test_pin_is_recorded_and_passed_to_integrity(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    assert ok(repo, sha, "pin", sha) == (0, f"PIN OK {sha}\n")
    assert json.loads((repo / ".factory/state/M1.json").read_text())["pin"] == sha
    assert ok(repo, sha, "pin", "deadbeef")[0] == 1


def test_milestone_id_with_a_letter_suffix_and_its_gap_task_are_accepted(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    code, out = step(repo, "status", P, "M2a", "--approved", sha)
    assert code == 0 and "not a milestone id" not in out  # parsed; its state is just empty here
    for bad in ("M2A", "M2ab", "M"):
        code, out = step(repo, "status", P, bad, "--approved", sha)
        assert code == 1 and "not a milestone id" in out, bad
    assert ok(repo, sha, "start", "M2a-gap")[0] != 2 and ok(repo, sha, "start", "M2A-gap")[0] == 2


def test_gap_round_tasks_get_their_own_worktree_and_merge(tmp_path):
    repo, sha = milestone_repo(tmp_path)
    ok(repo, sha, "target")
    for t in ("M1-gap", "M1-gap2"):
        code, out = ok(repo, sha, "start", t)
        wt = repo / ".worktrees" / f"{SLUG}-{t}"  # the task id already carries the milestone
        assert code == 0 and f" {wt} " in out and wt.is_dir(), out
    assert git(repo, "rev-parse", "--verify", f"{SLUG}-M1-gap2")


def with_ms(**kw):
    plan = json.loads(json.dumps(PLAN))
    plan["milestones"][0].update(kw)
    return plan


def test_rule_test_task_is_built_first(tmp_path):
    plan = with_ms()
    plan["milestones"][0]["tasks"][1]["ruleTest"] = True
    repo, sha = milestone_repo(tmp_path, plan)
    ok(repo, sha, "target")
    code, out = ok(repo, sha, "start", "T1")
    assert code == 1 and "build and finish the rule test T2 first" in out
    assert ok(repo, sha, "start", "T2")[0] == 0
    assert "rule test T2 first" in ok(repo, sha, "finish", "T1")[1]
    build(repo / ".worktrees" / f"{SLUG}-M1-T2", "src/b.ts")
    assert ok(repo, sha, "finish", "T2")[0] == 0
    assert ok(repo, sha, "start", "T1")[0] == 0


def test_security_review_rounds_are_capped_and_gated(tmp_path):
    repo, sha = milestone_repo(tmp_path, with_ms(risky=True))
    ok(repo, sha, "target")
    code, out = ok(repo, sha, "review", "FAIL", "guest-reads-moved-comment")
    assert code == 0 and "round=1 FAIL, fix round 1 of 1" in out
    git(repo, "commit", "-qam", "log review 1")
    code, out = ok(repo, sha, "review", "FAIL", "guest-reads-moved-comment")
    assert code == 1 and "past securityRounds 1" in out and "BLOCKED: owner decides on guest-reads-moved-comment" in out
    git(repo, "commit", "-qam", "log review 2")
    assert ok(repo, sha, "review", "FAIL", "two words")[0] == 1  # a rule is hyphenated words


def test_gate_security_passes_after_one_fix_round(tmp_path):
    repo, sha = milestone_repo(tmp_path, with_ms(risky=True))
    ok(repo, sha, "target")
    ok(repo, sha, "start", "T1")
    build(repo / ".worktrees" / f"{SLUG}-M1-T1", "src/a.ts")
    ok(repo, sha, "finish", "T1")
    assert "GATE security FAIL" in ok(repo, sha, "gate")[1]  # no review yet
    ok(repo, sha, "review", "FAIL", "guest-reads-moved-comment")
    assert "commit the previous log line first" in ok(repo, sha, "review", "PASS", "-")[1]
    git(repo, "commit", "-qam", "log review 1")
    ok(repo, sha, "review", "PASS", "-")
    git(repo, "commit", "-qam", "log review 2")
    assert "GATE security OK" in ok(repo, sha, "gate")[1]
    ok(repo, sha, "start", "T2")  # a task merged after the PASS needs a new review
    build(repo / ".worktrees" / f"{SLUG}-M1-T2", "src/b.ts")
    ok(repo, sha, "finish", "T2")
    assert "GATE security FAIL" in ok(repo, sha, "gate")[1]


def plan_with_tests(**tests):
    plan = json.loads(json.dumps(PLAN))
    plan["tests"] = tests
    return plan


def test_finish_runs_related_and_matching_triggers_before_the_merge(tmp_path):
    plan = plan_with_tests(related="test \"{files}\" = src/a.ts && touch ../related-saw-a",
                      triggers=[{"paths": ["src/**"], "run": "echo trigger-a", "why": "w"},
                                {"paths": ["docs/*.md"], "run": "echo trigger-b", "why": "w"}])
    repo, sha = milestone_repo(tmp_path, plan)
    ok(repo, sha, "target")
    ok(repo, sha, "start", "T1")
    wt = repo / ".worktrees" / f"{SLUG}-M1-T1"
    build(wt, "src/a.ts")
    code, out = ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests OK 2 commands" in out and "worktree removed" in out, out  # related + trigger-a, not trigger-b
    assert (repo / ".worktrees" / "related-saw-a").exists()


def test_finish_blocks_the_merge_when_a_hand_back_test_fails(tmp_path):
    plan = plan_with_tests(triggers=[{"paths": ["src/*.ts"], "run": "test ! -e src/a.ts || { echo boom-line; exit 3; }", "why": "w"}])
    repo, sha = milestone_repo(tmp_path, plan)
    ok(repo, sha, "target")
    ok(repo, sha, "start", "T1")
    wt = repo / ".worktrees" / f"{SLUG}-M1-T1"
    build(wt, "src/a.ts")
    before = git(repo, "rev-parse", "HEAD")
    code, out = ok(repo, sha, "finish", "T1")
    assert code == 1 and "FINISH FAIL T1 tests: test ! -e src/a.ts" in out and "boom-line" in out, out
    assert git(repo, "rev-parse", "HEAD") == before and wt.exists()
    assert json.loads((repo / ".factory/state/M1.json").read_text())["checked"] == []


def test_finish_skips_triggers_that_match_no_changed_file(tmp_path):
    plan = plan_with_tests(triggers=[{"paths": ["db/**"], "run": "exit 1", "why": "w"}])
    repo, sha = milestone_repo(tmp_path, plan)
    ok(repo, sha, "target")
    ok(repo, sha, "start", "T1")
    build(repo / ".worktrees" / f"{SLUG}-M1-T1", "src/a.ts")
    code, out = ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests" not in out


def test_gate_runs_each_suite_once_and_fails_on_a_red_one(tmp_path):
    plan = plan_with_tests(suites=[{"name": "unit", "cmd": "echo u >> ../suite-count"}, {"name": "arch", "cmd": "test ! -e src/a.ts || { echo arch-broke; exit 1; }", "lock": True}])
    repo, sha = milestone_repo(tmp_path, plan)
    ok(repo, sha, "target")
    ok(repo, sha, "start", "T1")
    build(repo / ".worktrees" / f"{SLUG}-M1-T1", "src/a.ts")
    assert ok(repo, sha, "finish", "T1")[0] == 0
    code, out = ok(repo, sha, "gate")
    assert code == 1 and "GATE tests OK unit" in out and "GATE tests FAIL arch" in out and "arch-broke" in out, out
    assert (tmp_path / "suite-count").read_text() == "u\n"  # zero at target, once at gate


def test_finish_does_not_block_on_a_command_already_red_on_the_milestone(tmp_path):
    plan = plan_with_tests(triggers=[{"paths": ["src/*.ts"], "run": "echo old-red; exit 3", "why": "w"}])
    repo, sha = milestone_repo(tmp_path, plan)
    ok(repo, sha, "target")
    ok(repo, sha, "start", "T1")
    build(repo / ".worktrees" / f"{SLUG}-M1-T1", "src/a.ts")
    code, out = ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests PRE-EXISTING echo old-red; exit 3" in out and "old-red" in out and "FINISH FAIL" not in out, out
    st = json.loads((repo / ".factory/state/M1.json").read_text())
    assert st["preexisting"] == ["echo old-red; exit 3"] and "T1" in st["tasks"]


def test_gate_reports_a_suite_red_at_target_as_pre_existing(tmp_path):
    plan = plan_with_tests(suites=[{"name": "old", "cmd": f"echo o >> {tmp_path}/old-count; exit 1"}, {"name": "unit", "cmd": "true"}])
    repo, sha = milestone_repo(tmp_path, plan)
    ok(repo, sha, "target")
    assert not (tmp_path / "old-count").exists()  # target runs no suite
    ok(repo, sha, "start", "T1")
    build(repo / ".worktrees" / f"{SLUG}-M1-T1", "src/a.ts")
    assert ok(repo, sha, "finish", "T1")[0] == 0
    code, out = ok(repo, sha, "gate")
    assert "GATE tests PRE-EXISTING old" in out and "GATE tests OK unit" in out and "GATE tests FAIL" not in out, out
    assert (tmp_path / "old-count").read_text() == "o\no\n"  # milestone worktree, then the baseline worktree
    assert not (repo / ".worktrees" / f"{SLUG}-M1-baseline").exists()


def test_gate_fails_a_suite_that_is_green_at_target(tmp_path):
    plan = plan_with_tests(suites=[{"name": "arch", "cmd": "test ! -e src/a.ts || { echo arch-broke; exit 1; }"}])
    repo, sha = milestone_repo(tmp_path, plan)
    ok(repo, sha, "target")
    ok(repo, sha, "start", "T1")
    build(repo / ".worktrees" / f"{SLUG}-M1-T1", "src/a.ts")
    assert ok(repo, sha, "finish", "T1")[0] == 0
    code, out = ok(repo, sha, "gate")
    assert code == 1 and "GATE tests FAIL arch" in out and "PRE-EXISTING" not in out, out
    assert not (repo / ".worktrees" / f"{SLUG}-M1-baseline").exists()
