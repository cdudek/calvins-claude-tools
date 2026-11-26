import copy
import importlib.util
import json
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "goal-brief.py"
TEMPLATE = HERE.parent / "references" / "plan-template.md"
INTENT = "# intent\n- outcome-1: people save a search\n- constraint-1: guests keep today's search\n"
R1, R2, R3 = ("req-1", "req-2", "req-3")

# The tests own their plan fixture, so the reference template can change without breaking them.
M1 = {"id": "M1", "layer": "components", "covers": [R1, R2], "tasks": [
    {"id": "T1", "covers": [R2], "files": ["src/ui/SavedSearchChip.tsx", "src/ui/SavedSearchChip.test.tsx"], "check": "npm test -- SavedSearchChip", "needs": []},
    {"id": "T2", "covers": [R1], "files": ["src/ui/SaveButton.tsx", "src/ui/SaveButton.test.tsx"], "check": "npm test -- SaveButton", "needs": []},
    {"id": "T3", "covers": [R1, R2], "files": ["src/app/preview/saved-search/page.tsx"], "check": "npm run typecheck", "needs": []}]}
M2_OPEN = {"id": "M2", "layer": "backend", "covers": [R1, R3], "risky": True}  # not detailed yet
M3_OPEN = {"id": "M3", "layer": "screens", "covers": [R2, R3]}
M2 = {"id": "M2", "layer": "backend", "covers": [R1, R3], "tasks": [
    {"id": "T4", "covers": [R1, R3], "files": ["src/api/s.ts"], "check": "npm test -- api", "needs": ["T1"]}]}
M2_RISKY = {**M2, "risky": True, "surface": [{"exposure": "list endpoint", "requirement": R1, "scenario": "guest-reads-list"}]}
M3 = {**M3_OPEN, "tasks": [{"id": "T5", "covers": [R2, R3], "files": ["src/app/search/page.tsx"], "check": "npm run typecheck", "needs": ["T4"]}]}
BASE = {"change": "2026-11-24-saved-searches", "base": "main", "goalTurns": 12, "requirements": [R1, R2, R3]}


def plan_text(milestones=None, **top):
    plan = {**copy.deepcopy(BASE), "milestones": copy.deepcopy(milestones or [M1, M2_OPEN, M3_OPEN]), **top}
    return "# Plan\n\n```json factory\n" + json.dumps(plan, indent=1) + "\n```\n\n## Progress log\n"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def repo(tmp_path, text=None, reqs=(R1, R2, R3), intent=True, sub=""):
    """A git repo with plan.md, delta.md and intent.md (in the folder sub) committed; returns (plan file, approved sha)."""
    tmp_path.mkdir(exist_ok=True)
    git(tmp_path, "init", "-q")
    d = tmp_path / sub
    d.mkdir(parents=True, exist_ok=True)
    plan = d / "plan.md"
    plan.write_text(text or plan_text())
    (d / "delta.md").write_text("# delta\n### ADDED Requirements\n" + "".join(f"- {r}: When ..., the system shall ... [outcome-1]\n" for r in reqs))
    if intent:
        (d / "intent.md").write_text(INTENT)
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "plan")
    return plan, git(tmp_path, "rev-parse", "HEAD")


def brief(plan, mid, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), str(plan), mid, *extra], capture_output=True, text=True)


def run(tmp_path, mid, text=None, **kw):
    plan, sha = repo(tmp_path, text, **kw)
    p = brief(plan, mid, "--approved", sha)
    return p.returncode, p.stdout, tmp_path / f"kickoff-{mid.lstrip('-')}.md"


def goal_of(out):
    g = out.split("-#-#- GOAL -#-#-\n")[1].split("\n")[0]
    assert len(g) < 4000 and g.startswith("/goal Met when any one of these is true. 1) ")
    return g


def turns_of(out):
    return out.split("--max-turns ")[2].split(" ")[0]


def test_template_passes_check_plan(tmp_path):
    plan, sha = repo(tmp_path, TEMPLATE.read_text())
    p = subprocess.run([sys.executable, str(HERE / "check-plan.py"), str(plan), "--approved", sha], capture_output=True, text=True)
    assert p.returncode == 0 and p.stdout.startswith("PLAN OK")


def test_ui_milestone_brief(tmp_path):
    code, out, kick = run(tmp_path, "M1")
    assert code == 0
    goal = goal_of(out)
    assert goal.startswith("/goal Met when any one of these is true. 1) SHIPPED: milestone M1 of 2026-11-24-saved-searches is merged into main")
    assert "req-1, req-2" in goal and "the UX verdict" in goal
    assert "gallery approval" not in goal and "by the owner" not in goal
    assert len(goal) < 1500
    k = kick.read_text()
    assert "`python3 .factory/task-step.py start plan.md M1 <task id>`" in k and "never by the Agent tool's worktree isolation" in k
    assert "git branch" not in k and "wt switch" not in k and "ff-only" not in k
    assert f"~/.factory/scenarios/{tmp_path.name}/2026-11-24-saved-searches/" in k
    assert "Arm auto-merge." in k and "ux-verifier" in k
    assert "never from the log" in k
    assert "after 12 turns" in goal
    assert "Builder effort: medium." in k and "gpt-6.2-astra" not in k  # M1 is not risky
    assert "--model sonnet --effort medium" in out
    run_line = out.split("-#-#- RUN -#-#-\n")[1].split("\n")[1]
    assert "--max-budget-usd" not in run_line
    # M1: components layer (UI), not risky, 3 tasks -> 2 x 10 x (3*3 + 3 + 0 + 1) = 260
    assert "--max-turns 260 " in run_line


def test_gallery_is_evidence_not_a_stop(tmp_path):
    code, out, kick = run(tmp_path, "M1")
    k = kick.read_text()
    assert code == 0 and "Do not merge yet" not in k and "owner approves the gallery" not in k
    assert "`design/`" in k and "approved at the single approval" in k
    assert "evidence/M1/gallery.md" in k and "evidence, not a stop" in k
    assert "Arm auto-merge." in k  # merges like any other milestone
    assert "BLOCKED: owner approves the gallery" not in out


def test_missing_approved_refused(tmp_path):
    plan, _ = repo(tmp_path)
    p = brief(plan, "M1")
    assert p.returncode == 1 and "BRIEF FAIL pass --approved <sha>, the commit the owner approved" in p.stdout
    assert not (tmp_path / "kickoff-M1.md").exists()


def test_plan_changed_after_approval_refused(tmp_path):
    plan, sha = repo(tmp_path)
    plan.write_text(plan.read_text().replace('"goalTurns": 12', '"goalTurns": 99'))
    p = brief(plan, "M1", "--approved", sha)
    assert p.returncode == 1 and f"BRIEF FAIL plan.md changed since approved {sha}" in p.stdout
    assert not (tmp_path / "kickoff-M1.md").exists()


def test_missing_intent_refused(tmp_path):
    code, out, kick = run(tmp_path, "M1", intent=False)
    assert code == 1 and "BRIEF FAIL missing intent.md next to the plan" in out and not kick.exists()


def test_integrity_and_plan_calls_carry_the_approved_sha(tmp_path):
    code, out, kick = run(tmp_path, "M1")
    sha = git(tmp_path, "rev-parse", "HEAD")
    k = kick.read_text()
    assert code == 0
    assert f"`python3 .factory/task-step.py finish plan.md M1 <task id> --approved {sha}`" in k
    assert f"`python3 .factory/task-step.py gate plan.md M1 --approved {sha}`" in k
    assert k.index("task-step.py finish") < k.index("task-step.py gate")  # per task first, then before the PR
    assert "--pin" not in k  # only the bug flow pins


def test_every_task_in_a_builder_and_work_moves_by_worktree(tmp_path):
    code, out, kick = run(tmp_path, "M1")
    k = kick.read_text()
    assert code == 0 and "Every task runs in a factory:builder subagent" in k and "even a one-line fix" in k
    assert "you only start worktrees, run checks, merge and log" in k
    assert "the next pass gets the same path" in k and "Never patch files" in k and "rtk proxy git diff" in k


def test_owner_merge_ends_shipped_with_the_merge_ready_url(tmp_path):
    code, out, kick = run(tmp_path, "M1", plan_text(merge="owner"))
    k = kick.read_text()
    goal = goal_of(out)
    assert code == 0 and "Never arm auto-merge" in k and "end with SHIPPED, the merge-ready PR URL" in k
    assert "BLOCKED: owner merges" not in k and "BLOCKED: owner merges" not in goal
    assert "is ready for the owner" in goal and "starts with SHIPPED and gives the merge-ready PR URL" in goal and "is merged into" not in goal


def test_integration_branch(tmp_path):
    code, out, kick = run(tmp_path, "M1", plan_text(integration="integration/v1-beta"))
    k = kick.read_text()
    goal = goal_of(out)
    assert code == 0 and "one PR into `integration/v1-beta`" in k and "plan and delta are on `integration/v1-beta`" in k
    assert "batch fixes into one push" in k
    assert "gh pr merge <n> --squash" in k and "release PR from `integration/v1-beta` into `main`" in k and "gh pr checks" not in k
    assert "merged into integration/v1-beta" in goal and "required CI" not in goal
    assert "Release:" not in k  # M1 is not the last milestone


FULL = [M1, M2, M3]


def test_release_pr_auto_merges_on_the_last_milestone(tmp_path):
    code, out, kick = run(tmp_path, "M3", plan_text(FULL, integration="integration/v1-beta"))
    k, goal = kick.read_text(), goal_of(out)
    assert code == 0 and "Release: once the milestone PR is merged" in k
    assert "gh pr create --base main --head integration/v1-beta" in k and "evidence/<M>/gallery.md" in k
    assert "Arm auto-merge (`gh pr merge <n> --merge --auto`)" in k and "Do not arm auto-merge" not in k
    assert "apply " in k and "delta.md to the spec files" in k  # the last milestone applies the delta, so the release PR carries it
    assert "the release PR from integration/v1-beta into main is merged into main" in goal and "its merge SHA" in goal
    assert "ready for the owner" not in goal


def test_release_pr_waits_for_the_owner_when_risky_or_deploying(tmp_path):
    for top, milestones, why in (({}, [M1, M2_RISKY, M3], "a milestone is risky"), ({"deployOnMerge": True}, FULL, "deployOnMerge is true")):
        code, out, kick = run(tmp_path / why.split()[0], "M3", plan_text(milestones, integration="integration/v1-beta", **top))
        k, goal = kick.read_text(), goal_of(out)
        assert code == 0 and f"Do not arm auto-merge ({why})" in k and "end with SHIPPED, the merge-ready release PR URL and its CI conclusion" in k
        assert "gh pr merge <n> --merge --auto" not in k and "BLOCKED: owner merges" not in k
        assert "the release PR from integration/v1-beta into main is ready for the owner" in goal
        assert "starts with SHIPPED and gives the merge-ready PR URL" in goal and "merge SHA" not in goal


def test_risky_milestone_pr_into_integration_still_merges_on_its_own(tmp_path):
    code, out, kick = run(tmp_path, "M2", plan_text([M1, M2_RISKY, M3], integration="integration/v1-beta"))
    k, goal = kick.read_text(), goal_of(out)
    assert code == 0 and "gh pr merge <n> --squash" in k and "Release:" not in k
    assert "milestone M2 of 2026-11-24-saved-searches is merged into integration/v1-beta" in goal


def test_hold_beats_integration_and_release(tmp_path):
    code, out, kick = run(tmp_path, "M3", plan_text(FULL, integration="integration/v1-beta", hold="owner restores billing"))
    k = kick.read_text()
    assert code == 0 and "gh pr create" not in k and "Release:" not in k and "Open no PR" in k


def risky_text():
    return plan_text([M1, M2_RISKY, M3_OPEN])


def test_risky_milestone_gets_security_review(tmp_path):
    code, out, kick = run(tmp_path, "M2", risky_text())
    k = kick.read_text()
    assert code == 0 and "security review" in k and "auth, money, consent or data exposure" in k
    assert "Opus 5.5 high" in k and "gpt-6.2-astra" in k and "ux-verifier" not in k  # backend: no gallery
    assert "fix every High" not in k
    assert "only inside the task's own files and its allowTestEdits" in k
    assert "is a `gap`: see the gap lane under Verify" in k


def test_goal_lists_end_states_in_order(tmp_path):
    code, out, _ = run(tmp_path, "M2", risky_text())
    goal = goal_of(out)
    assert code == 0
    order = [goal.index(s) for s in ("1) SHIPPED:", "2) BLOCKED:", "3) INCOMPLETE: after 12 turns")]
    assert order == sorted(order) and "HOLD" not in goal
    assert "whatever the build state" in goal


def test_setup_and_preflight_only_when_the_plan_has_them(tmp_path):
    code, out, kick = run(tmp_path / "a", "M1")
    k = kick.read_text()
    assert code == 0 and "preflight command" not in k and "tool or credential" not in k
    pf = ["command -v squawk", "gcloud auth print-access-token >/dev/null"]
    code, out, kick = run(tmp_path / "b", "M1", plan_text(setup="npm ci", preflight=pf))
    k = kick.read_text()
    assert code == 0 and "runs the plan's `setup` in it" in k
    assert "`command -v squawk`" in k and "`gcloud auth print-access-token >/dev/null`" in k
    assert "BLOCKED: <tool or credential> missing: <exact fix>" in k
    assert k.index("preflight command") < k.index("One worktree per task")  # first Build step


def test_hold_pushes_and_opens_no_pr(tmp_path):
    hold = "owner restores GitHub billing on the account"
    code, out, kick = run(tmp_path, "M2", plan_text([M1, M2_RISKY, M3_OPEN], hold=hold))
    k, goal = kick.read_text(), goal_of(out)
    assert code == 0
    for word in ("gh pr create", "gh pr merge", "auto-merge", "gh pr checks"):
        assert word not in k
    assert "Open no PR" in k and "push `milestone/2026-11-24-saved-searches-M2` once" in k and f"HOLD: {hold}" in k
    assert "1) HOLD: the last message starts with HOLD: and the transcript shows the pushed SHA" in goal and "verifier PASS for that same SHA" in goal
    assert f"In this run, {hold} is not such an action" in goal and "SHIPPED" not in goal
    assert "task-step.py gate plan.md M2 --approved" in k  # the integrity check still runs before the push


def test_bug_is_a_plan_with_a_pinned_failing_test(tmp_path):
    task = {"id": "T1", "covers": [R1], "files": ["src/login.ts"], "check": "npm test -- login", "needs": []}
    ms = [{"id": "M1", "layer": "rest", "covers": [R1], "tasks": [task]}]
    code, out, kick = run(tmp_path, "M1", plan_text(ms, kind="bug", requirements=[R1]), reqs=(R1,))
    k = kick.read_text()
    assert code == 0, out
    assert "first commit holds only the failing regression test" in k and "run the task's check with the worktree at that commit" in k
    assert "`python3 .factory/task-step.py pin plan.md M1 <failing-test SHA>`" in k and "later `finish` passes `--pin`" in k
    code, out, kick = run(tmp_path / "f", "M1", plan_text(ms, kind="feature", requirements=[R1]), reqs=(R1,))
    assert code == 0 and "task-step.py pin" not in kick.read_text() and "failing regression test" not in kick.read_text()


def test_small_flag_is_gone(tmp_path):
    p = subprocess.run([sys.executable, str(SCRIPT), "--small", "2026-11-24-fix-login", "Fix it.", "--check", "npm test"],
                       capture_output=True, text=True, cwd=tmp_path)
    assert p.returncode != 0 and not (tmp_path / "changes").exists() and "--small" not in SCRIPT.read_text()


def test_all_milestones_one_kickoff_and_one_goal(tmp_path):
    code, out, kick = run(tmp_path, "--all", plan_text(FULL, integration="integration/v1-beta"))
    k, goal = kick.read_text(), goal_of(out)
    assert code == 0 and kick.name == "kickoff-all.md" and not (tmp_path / "kickoff-M1.md").exists()
    order = [k.index(f"## Milestone {m} (") for m in ("M1", "M2", "M3")]
    assert order == sorted(order)
    assert f"git show {git(tmp_path, 'rev-parse', 'HEAD')}:plan.md" in k and "re-read the pinned plan" in k and "progress log" in k
    assert k.count("Release:") == 1 and k.index("Release:") > order[2]  # the release PR once, at the end
    assert k.count("## Stop") == 1 and k.count("apply ") == 1
    assert "all 3 milestones of 2026-11-24-saved-searches are built and the release PR from integration/v1-beta into main is merged into main" in goal
    assert "after 36 turns" in goal  # goalTurns 12 x 3 milestones
    assert "req-1, req-2, req-3" in goal and "the UX verdict" in goal
    # M1 260 + M2 (1 task: 3+3 = 6 dispatches) 120 + M3 (1 task, UI: 3+3+1 = 7) 140
    assert "--max-turns 520 " in out and turns_of(out) == "520"


def test_all_without_integration_ends_on_the_last_milestone_pr(tmp_path):
    code, out, kick = run(tmp_path, "--all", plan_text(FULL))
    goal = goal_of(out)
    assert code == 0 and "all 3 milestones of 2026-11-24-saved-searches are merged into main" in goal and "Release:" not in kick.read_text()


def test_all_needs_every_milestone_detailed_and_no_hold(tmp_path):
    code, out, kick = run(tmp_path / "a", "--all")
    assert code == 1 and "BRIEF FAIL M2 has no tasks" in out and "BRIEF FAIL M3 has no tasks" in out and not kick.exists()
    assert out.count("M2 has no tasks") == 1  # one source: check_plan.validate(..., every=True)
    code, out, kick = run(tmp_path / "b", "--all", plan_text(FULL, hold="owner restores billing"))
    assert code == 1 and "BRIEF FAIL --all cannot run with a hold" in out and not kick.exists()
    plan, _ = repo(tmp_path / "c", plan_text(FULL))
    p = brief(plan, "--all")
    assert p.returncode == 1 and "BRIEF FAIL pass --approved" in p.stdout


def test_plan_path_is_the_repo_relative_one(tmp_path):
    sub = "changes/2026-11-24-saved-searches"
    plan, sha = repo(tmp_path, plan_text(FULL), sub=sub)
    p = brief(plan, "--all", "--approved", sha)  # the owner may well pass an absolute path
    k = (plan.parent / "kickoff-all.md").read_text()
    assert p.returncode == 0, p.stdout
    assert f"task-step.py finish {sub}/plan.md M1 <task id> --approved {sha}" in k and f"task-step.py gate {sub}/plan.md M1 --approved {sha}" in k
    assert f"git show {sha}:{sub}/plan.md" in k
    assert f"{sub}/evidence/M1/gallery.md" in k and f"`{sub}/design/`" in k
    assert str(tmp_path) not in k.replace(f"{tmp_path.resolve()}/.worktrees", "")  # no absolute plan path anywhere


def test_target_sha_is_fetched_recorded_and_passed_not_a_branch_name(tmp_path):
    code, out, kick = run(tmp_path / "a", "M1", plan_text(integration="integ"))
    k = kick.read_text()
    assert code == 0 and "`python3 .factory/task-step.py target plan.md M1`" in k and "records the head of `integ` as the <target SHA>" in k
    assert k.index("task-step.py target") < k.index("task-step.py start")  # recorded before the first worktree and integrity call
    assert "<this worktree>" not in k and "--target <target SHA>" not in k
    code, out, kick = run(tmp_path / "b", "--all", plan_text(FULL, integration="integ"))
    k = kick.read_text()
    assert code == 0
    assert "`git fetch origin`, record `git rev-parse origin/integ` as that milestone's <target SHA>" in k
    assert "`git branch milestone/2026-11-24-saved-searches-<M> <target SHA>`" in k and "<M> origin/integ" not in k
    assert "then run `python3 .factory/task-step.py target plan.md <M>` inside it" in k and k.count("task-step.py target plan.md M1") == 1


def test_checked_task_commits_are_recorded_and_passed(tmp_path):
    code, out, kick = run(tmp_path, "M1")
    k = kick.read_text()
    assert code == 0 and "records its HEAD as a <checked SHA> (every INTEGRITY OK commit" in k
    assert "merges exactly that commit" in k
    assert k.index("<checked SHA>") < k.index("task-step.py gate") and "every <checked SHA>" in k


def ship_of(kick_text):
    return kick_text.split("Ship, in this order")[1]


def test_ship_commits_first_then_verifies_that_sha_then_pushes_it(tmp_path):
    hold = "owner restores billing"
    for name, text, mid in (("pr", plan_text(FULL, integration="integ"), "M3"), ("hold", plan_text(FULL, hold=hold), "M3"), ("ui", plan_text(), "M1")):
        code, out, kick = run(tmp_path / name, mid, text)
        k = kick.read_text()
        s = ship_of(k)
        assert code == 0 and "factory:verifier" not in k.split("Ship, in this order")[0].replace("ux-verifier", "")  # not in Verify
        order = [s.index(x) for x in ("1. Commit on", "the progress entry", "2. Run `python3 .factory/task-step.py gate",
                                       "3. factory:verifier on the final commit", "4. ")]
        assert order == sorted(order), (name, order)
        assert "Nothing is committed after the verifier" in s and s.count("<final SHA>") >= 2 and "verifier PASS for that SHA" in s
        after = s.split("3. factory:verifier on the final commit")[1]
        assert "progress entry" not in after and "commit it" not in after and "append" not in after  # nothing is committed after it
        assert "no PR number or merge SHA" in s
        assert "goes through Verify step 2 (per-task integrity, a new <checked SHA>, merge that commit), then repeat Ship from step 1" in s
        assert "task-step.py status" in k and "target plan.md <M> --resume" in k and "<checked SHA>s" in k  # a resumed run re-records both
        if mid == "M3":
            assert s.index("apply ") < s.index("the progress entry")  # the spec commit comes first too
        if mid == "M1":
            assert s.index("the gallery and the progress entry") > s.index("1. Commit on")
    assert "on the pushed SHA of branch milestone/2026-11-24-saved-searches-M1" in goal_of(out)
    code, out, _ = run(tmp_path / "all", "--all", plan_text(FULL, integration="integ"))
    assert code == 0 and "on each milestone branch's pushed SHA" in goal_of(out)  # never the release PR's head


def test_run_command_quotes_goal_and_kickoff_path(tmp_path):
    hold = "owner renews the owner's \"billing\" $HOME"
    code, out, kick = run(tmp_path / "a b", "M2", plan_text([M1, M2_RISKY, M3_OPEN], hold=hold))
    assert code == 0, out
    cmd = out.split("-#-#- RUN -#-#-\n")[1].split("\n")[1]
    script = tmp_path / "cmd.sh"
    script.write_text(cmd + "\n")
    assert subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode == 0
    words = shlex.split(cmd)
    assert words[-1] == goal_of(out) and "owner's \"billing\" $HOME" in words[-1]
    assert words[words.index("--append-system-prompt") + 1] == f"$(cat {shlex.quote(str(kick))})"
    assert kick.exists() and " " in str(kick)


def test_undetailed_milestone_refused(tmp_path):
    code, out, kick = run(tmp_path, "M2")
    assert code == 1 and "BRIEF FAIL M2 has no tasks" in out and not kick.exists()


def test_bad_plan_refused(tmp_path):
    text = plan_text().replace('"change": "2026-11-24-saved-searches"', '"change": "saved-searches"')
    code, out, kick = run(tmp_path, "M1", text)
    assert code == 1 and "BRIEF FAIL change must be the dated slug" in out and not kick.exists()


def test_every_agent_runs_in_the_foreground(tmp_path):
    # an unattended run exits under a background agent (a beta milestone, 2026-11-25)
    code, out, kick = run(tmp_path, "M1")
    assert code == 0 and "never with run_in_background" in kick.read_text()


def test_sized_plan_names_model_effort_and_verifier(tmp_path):
    m = copy.deepcopy(M1)
    m["tasks"][0].update(model="haiku", effort="high")
    m["verifier"] = {"model": "sonnet", "effort": "high"}
    _, out, kick = run(tmp_path, "M1", plan_text([m, M2_OPEN, M3_OPEN]))
    k = kick.read_text()
    assert "Builder effort: high. Builder model: haiku." in k and "Builder effort: medium." in k
    assert "Pass each task's builder model and effort to its Agent call" in k
    assert "factory:verifier (pass model sonnet and effort high to the Agent call) on the final commit" in k


KICKOFF_STANCE = "Do reversible steps yourself and keep going: create a missing branch, rerun a check, recreate a worktree. Stop only for a decision the plan does not cover or an irreversible step."


def with_origin(tmp_path, integ="integration/v1-beta", push_base=True, **top):
    """A repo whose origin is a local bare repo holding main; returns (plan, approved sha, bare path)."""
    work = tmp_path / "work"
    plan, sha = repo(work, plan_text(integration=integ, **top))
    git(work, "branch", "-M", "main")
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    git(work, "remote", "add", "origin", str(bare))
    if push_base:
        git(work, "push", "-q", "origin", "main")
    return plan, sha, bare


def heads(bare):
    return git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads")


def test_integration_exists_on_origin_nothing_changes(tmp_path):
    plan, sha, bare = with_origin(tmp_path)
    git(bare, "branch", "integration/v1-beta", "main")
    before = heads(bare)
    p = brief(plan, "M1", "--approved", sha)
    assert p.returncode == 0 and "-#-#- PREFLIGHT -#-#-\nintegration/v1-beta exists on origin" in p.stdout
    assert heads(bare) == before


def test_missing_integration_is_created_from_the_approved_sha(tmp_path):
    plan, sha, bare = with_origin(tmp_path)
    p = brief(plan, "M1", "--approved", sha)
    assert p.returncode == 0 and f"created integration/v1-beta on origin from {sha}" in p.stdout
    assert git(bare, "rev-parse", "integration/v1-beta") == sha


def test_missing_integration_with_sha_off_base_fails_with_the_command(tmp_path):
    plan, sha, bare = with_origin(tmp_path, push_base=False)
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init", "-q")
    (other / "f.txt").write_text("x")
    git(other, "add", "-A")
    git(other, "commit", "-q", "-m", "unrelated base")
    git(other, "push", "-q", str(bare), "HEAD:refs/heads/main")
    p = brief(plan, "M1", "--approved", sha)
    assert p.returncode == 1 and "BRIEF FAIL" in p.stdout
    assert f"run `git push origin {sha}:refs/heads/integration/v1-beta`" in p.stdout
    assert "integration/v1-beta" not in heads(bare)


def test_plan_without_integration_has_no_preflight_and_the_stance_line(tmp_path):
    code, out, kick = run(tmp_path, "M1")
    assert code == 0 and out.startswith("-#-#- KICKOFF FILE -#-#-") and "PREFLIGHT" not in out
    assert KICKOFF_STANCE in kick.read_text()


def load_brief():
    spec = importlib.util.spec_from_file_location("goal_brief", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bad_integration_or_base_names_are_rejected_before_any_git_call(tmp_path):
    for i, (integ, top) in enumerate((("-evil", {}), ("a..b", {}), ("x.lock", {}), ("integration/ok", {"base": "-b"}))):
        (tmp_path / str(i)).mkdir()
        plan, sha, bare = with_origin(tmp_path / str(i), integ=integ, **top)
        p = brief(plan, "M1", "--approved", sha)
        assert p.returncode == 1 and "BRIEF FAIL plan" in p.stdout and "not a valid branch name" in p.stdout, (integ, p.stdout)
        assert heads(bare) == "main"


def test_refs_come_after_a_double_dash(tmp_path):
    gb, calls = load_brief(), []

    def fake(cwd, *args):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "" if args[0] == "ls-remote" else "x", "")
    gb.git_out = fake
    ok, _ = gb.preflight_integration(tmp_path / "plan.md", {"integration": "integration/v1", "base": "main"}, "abc1234")
    assert ok
    by = {c[0]: c for c in calls}
    assert by["ls-remote"][by["ls-remote"].index("--") + 1:] == ("origin", "integration/v1")
    assert by["fetch"][by["fetch"].index("--") + 1:] == ("origin", "main")
    assert by["merge-base"][by["merge-base"].index("--") + 1:] == ("abc1234", "FETCH_HEAD")


def test_credentials_are_stripped_from_git_errors(tmp_path):
    scrub = load_brief().scrub
    assert scrub("fatal: unable to access 'https://user:s3cret@host.example/x.git/': nope") == "fatal: unable to access 'https://host.example/x.git/': nope"
    assert "s3cret" not in scrub("ssh://deploy:s3cret@host/x and https://tok@h/y")
    plan, sha, bare = with_origin(tmp_path)
    git(tmp_path / "work", "remote", "set-url", "origin", "https://user:s3cret@127.0.0.1:1/x.git")
    p = brief(plan, "M1", "--approved", sha)
    assert p.returncode == 1 and "could not read origin" in p.stdout and "s3cret" not in p.stdout + p.stderr


def test_only_integration_branches_are_pushed(tmp_path):
    plan, sha, bare = with_origin(tmp_path, integ="release/v1")
    p = brief(plan, "M1", "--approved", sha)
    assert p.returncode == 1 and "BRIEF FAIL" in p.stdout
    assert f"run `git push origin {sha}:refs/heads/release/v1` yourself" in p.stdout
    assert heads(bare) == "main"


def test_gap_lane_names_the_may_touch_globs_and_the_log_line(tmp_path):
    ms = [{**M1, "mayTouch": ["src/api/*", "tests/api/"]}, M2_OPEN, M3_OPEN]
    code, out, kick = run(tmp_path, "M1", plan_text(ms))
    k = kick.read_text()
    assert code == 0 and "labels every FAIL `bug` or `gap`" in k
    assert "matches M1's mayTouch (`src/api/*`, `tests/api/`)" in k and "`GAP-FIX M1 files=<a,b> tests=<c,d>`" in k
    assert "one fix task `M1-gap`" in k and "`--task M1-gap` integrity" in k and "A second gap" in k
    assert "a `gap` FAIL to the gap lane" in k


def test_gap_lane_without_may_touch_ends_blocked(tmp_path):
    code, out, kick = run(tmp_path, "M1")
    k = kick.read_text()
    assert code == 0 and "M1 has no `mayTouch`, so every `gap` ends `BLOCKED" in k and "GAP-FIX" not in k


def test_kickoff_comes_from_the_template_with_no_placeholder_left(tmp_path):
    for name, mid, text in (("one", "M1", plan_text()), ("all", "--all", plan_text(FULL, integration="integ")), ("hold", "M2", plan_text([M1, M2_RISKY, M3_OPEN], hold="x y"))):
        code, out, kick = run(tmp_path / name, mid, text)
        assert code == 0 and "{{" not in kick.read_text() and "}}" not in kick.read_text() and "@@" not in kick.read_text(), name
    assert (HERE.parent / "templates" / "kickoff.md").read_text().startswith("@@ top")
