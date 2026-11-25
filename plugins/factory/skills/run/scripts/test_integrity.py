import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent / "test-integrity.sh"
BASE_FILES = {
    "src/a.ts": "export const a = 1\n",
    "src/a.test.ts": "it('a', () => {})\n",
    "package.json": "{}\n",
    ".cfactory/goal-brief.py": "x\n",
    ".github/workflows/ci.yml": "on: pull_request\n",
    ".github/actions/setup/action.yml": "name: setup\n",
    ".fitness/baseline.json": "{}\n",
    "tools/slop-baseline.json": "{}\n",
    "changes/2026-11-24-x/plan.md": "# plan\n",
}


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"})


def make(tmp_path, edits):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    for name, text in BASE_FILES.items():
        f = repo / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    git(repo, "switch", "-qc", "task")
    for name, text in edits.items():
        f = repo / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "task")
    p = subprocess.run(["bash", str(SCRIPT), str(repo), "main"], capture_output=True, text=True)
    return p.returncode, p.stdout


def test_clean_branch_ok(tmp_path):
    code, out = make(tmp_path, {"src/b.ts": "export const b = 2\n", "src/b.test.ts": "it('b', () => {})\n"})
    assert code == 0 and out.strip() == "INTEGRITY OK"


@pytest.mark.parametrize("path,reason", [
    (".cfactory/goal-brief.py", "harness changed"),
    (".cfactory/new.sh", "harness changed"),
    ("changes/2026-11-24-x/plan.md", "plan changed"),
    (".github/workflows/ci.yml", "CI config changed"),
    (".github/actions/setup/action.yml", "CI config changed"),
    (".fitness/baseline.json", "baseline changed"),
    ("tools/slop-baseline.json", "baseline changed"),
    ("specs/adr/0007-queue.md", "ADR changed"),
    ("specs/2026-12/2026-12-20__guest-links.md", "spec changed"),
])
def test_protected_file_changed(tmp_path, path, reason):
    code, out = make(tmp_path, {path: "changed\n"})
    assert code == 1 and f"INTEGRITY FAIL {reason}: {path}" in out


@pytest.mark.parametrize("line", [
    "// biome-ignore lint/suspicious/noExplicitAny: x", "// eslint-disable-next-line", "// oxlint-disable-next-line",
    "// @ts-ignore", "// @ts-expect-error", "x = 1  # noqa",
])
def test_lint_suppression_in_code(tmp_path, line):
    code, out = make(tmp_path, {"src/a.ts": f"export const a = 1\n{line}\n"})
    assert code == 1 and "INTEGRITY FAIL added lint suppression" in out


def test_suppression_in_test_file_or_docs_not_flagged_here(tmp_path):
    code, out = make(tmp_path, {"docs/x.md": "use biome-ignore sparingly\n"})
    assert code == 0 and out.strip() == "INTEGRITY OK"


def test_existing_test_changed(tmp_path):
    code, out = make(tmp_path, {"src/a.test.ts": "it('a', () => { /* weakened */ })\n"})
    assert code == 1 and "existing test changed or deleted: src/a.test.ts" in out


def test_unresolvable_base_fails(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    git(repo, "init", "-q")
    p = subprocess.run(["bash", str(SCRIPT), str(repo), "nope"], capture_output=True, text=True)
    assert p.returncode == 1 and "INTEGRITY FAIL cannot resolve" in p.stdout


# ---- plan-aware modes ----
import json  # noqa: E402

PLAN = {
    "change": "2026-11-24-x", "base": "main", "integration": "integ", "goalTurns": 5,
    "requirements": ["req-1", "req-2"],
    "milestones": [
        {"id": "M1", "layer": "backend", "covers": ["req-1"], "tasks": [
            {"id": "T1", "covers": ["req-1"], "check": "true", "files": ["src/a.ts", "lib/"], "allowTestEdits": ["src/a.test.ts"]},
            {"id": "T2", "check": "true", "files": ["src/b*.ts"], "allowTestEdits": ["src/b.test.ts"]}]},
        {"id": "M2", "layer": "screens", "covers": ["req-2"], "tasks": [{"id": "T3", "covers": ["req-2"], "check": "true", "files": ["src/c.ts"]}]},
    ],
}
PLAN_PATH = "changes/2026-11-24-x/plan.md"


def plan_text(plan, extra=""):
    return "# plan\n\n```json cfactory\n" + json.dumps(plan, indent=1) + "\n```\n" + extra


def run(repo, *args):
    p = subprocess.run(["bash", str(SCRIPT), str(repo), *args], capture_output=True, text=True)
    return p.returncode, p.stdout


def plan_repo(tmp_path, plan=PLAN, with_integ=True):
    """main holds the plan and existing tests; integ is a copy of main; branch `ms` is checked out."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    for name, text in {**BASE_FILES, "src/b.test.ts": "it('b', () => {})\n", PLAN_PATH: plan_text(plan),
                       "changes/2026-11-24-x/delta.md": "## ADDED\n- req-1: a [outcome-1]\n- req-2: b [outcome-1]\n",
                       "changes/2026-11-24-x/intent.md": "- outcome-1: x\n"}.items():
        f = repo / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    if with_integ:
        git(repo, "branch", "integ")
    git(repo, "switch", "-qc", "ms")
    return repo


def commit(repo, edits, msg="c"):
    for name, text in edits.items():
        f = repo / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", msg)


def appr(repo):
    """The approved revision in these tests: the base commit every branch descends from."""
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "main"], capture_output=True, text=True).stdout.strip()


def head(repo):
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def test_m1_regression_test_added_then_edited_is_new_on_integration(tmp_path):
    repo = plan_repo(tmp_path)
    git(repo, "switch", "-qc", "t1")
    commit(repo, {"src/new.test.ts": "it('n', () => {})\n"}, "pass 1")
    git(repo, "switch", "-q", "ms")
    commit(repo, {"src/a.ts": "export const a = 2\n"}, "ms work")  # diverge so the merge is real
    git(repo, "merge", "-q", "--no-ff", "-m", "merge t1", "t1")
    commit(repo, {"src/new.test.ts": "it('n', () => { expect(1) })\n"}, "pass 2")
    code, out = run(repo, "main", str(repo / PLAN_PATH))
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    # the same edit to a test that exists on integration is an existing-test change
    commit(repo, {"src/a.test.ts": "it('a', () => { /* weakened */ })\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH))
    assert code == 1 and "existing test changed or deleted: src/a.test.ts" in out


def test_new_test_judged_against_integration_not_base_ref(tmp_path):
    repo = plan_repo(tmp_path)
    git(repo, "switch", "-q", "integ")
    commit(repo, {"src/early.test.ts": "it('e', () => {})\n"}, "on integ")
    git(repo, "switch", "-q", "ms")
    git(repo, "merge", "-q", "integ")
    commit(repo, {"src/early.test.ts": "it('e', () => { /* edited */ })\n"})
    code, out = run(repo, "integ", str(repo / PLAN_PATH))
    assert code == 1 and "existing test changed or deleted: src/early.test.ts" in out


def test_old_top_level_allow_test_edits_still_honoured_without_mode(tmp_path):
    repo = plan_repo(tmp_path, dict(PLAN, allowTestEdits=["src/a.test.ts"]))
    commit(repo, {"src/a.test.ts": "it('a', () => { /* edited */ })\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH))
    assert code == 0 and out.strip() == "INTEGRITY OK", out


def test_unresolvable_integration_fails(tmp_path):
    repo = plan_repo(tmp_path, with_integ=False)
    commit(repo, {"src/a.ts": "export const a = 2\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH))
    assert code == 1 and "INTEGRITY FAIL cannot resolve integration ref integ" in out


def test_task_outside_files_fails(tmp_path):
    repo = plan_repo(tmp_path)
    commit(repo, {"src/a.ts": "export const a = 2\n", "lib/x.ts": "x\n", "src/other.ts": "y\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T1")
    assert code == 1
    assert "INTEGRITY FAIL outside task T1: src/other.ts" in out
    assert "outside task T1: src/a.ts" not in out and "outside task T1: lib/x.ts" not in out


def test_task_glob_and_new_test_ok(tmp_path):
    repo = plan_repo(tmp_path)
    commit(repo, {"src/bar.ts": "z\n", "src/zzz.test.ts": "it('z', () => {})\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T2")
    assert code == 0 and out.strip() == "INTEGRITY OK", out


def test_test_edit_allowed_only_for_another_task_fails(tmp_path):
    repo = plan_repo(tmp_path)
    commit(repo, {"src/a.test.ts": "it('a', () => { /* edited */ })\n"})  # T1 may, T2 may not
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T1")
    assert code == 0, out
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T2")
    assert code == 1 and "existing test changed or deleted: src/a.test.ts" in out
    assert "outside task T2: src/a.test.ts" not in out  # one line per path


def test_task_mode_still_fails_plan_change(tmp_path):
    repo = plan_repo(tmp_path)
    commit(repo, {PLAN_PATH: plan_text(PLAN, "progress\n")})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T1")
    assert code == 1 and f"plan changed: {PLAN_PATH}" in out


def test_unknown_task_fails(tmp_path):
    repo = plan_repo(tmp_path)
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T9")
    assert code == 1 and "no task or milestone T9" in out


def test_milestone_accepts_plan_progress_and_evidence_rejects_stray(tmp_path):
    repo = plan_repo(tmp_path)
    commit(repo, {"src/a.ts": "export const a = 2\n", "src/b.ts": "b\n",
                  PLAN_PATH: plan_text(PLAN, "progress: M1 done\n"),
                  "changes/2026-11-24-x/evidence/M1/gallery.md": "g\n",
                  "changes/2026-11-24-x/kickoff-M1.md": "k\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    commit(repo, {"src/stray.ts": "s\n", "specs/2026-12/guest.md": "spec\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 1 and "outside milestone M1: src/stray.ts" in out and "spec changed: specs/2026-12/guest.md" in out


def test_milestone_scope_excludes_other_milestones(tmp_path):
    repo = plan_repo(tmp_path)
    commit(repo, {"src/c.ts": "c\n"})  # belongs to M2's T3
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 1 and "outside milestone M1: src/c.ts" in out


def test_specs_allowed_only_on_last_milestone_and_never_adr(tmp_path):
    repo = plan_repo(tmp_path)
    commit(repo, {"src/c.ts": "c\n", "specs/2026-12/guest.md": "spec\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M2", "--approved", appr(repo))
    assert code == 0, out
    commit(repo, {"specs/adr/0001-x.md": "adr\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M2", "--approved", appr(repo))
    assert code == 1 and "ADR changed: specs/adr/0001-x.md" in out


def test_milestone_plan_change_checked_with_approved(tmp_path):
    if "--approved" not in (SCRIPT.parent / "check-plan.py").read_text():
        pytest.skip("check-plan.py has no --approved yet")
    repo = plan_repo(tmp_path)
    approved = head(repo)
    commit(repo, {PLAN_PATH: plan_text(dict(PLAN, goalTurns=9))})  # the block changed after approval
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", approved)
    assert code == 1 and "fails check-plan" in out


def test_approved_plan_values_win_over_working_copy(tmp_path):
    repo = plan_repo(tmp_path)
    approved = head(repo)
    commit(repo, {"src/other.ts": "o\n"})
    widened = json.loads(json.dumps(PLAN))
    widened["milestones"][0]["tasks"][0]["files"].append("src/other.ts")
    (repo / PLAN_PATH).write_text(plan_text(widened))  # uncommitted widening is ignored
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T1", "--approved", approved)
    assert code == 1 and "outside task T1: src/other.ts" in out
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T1")
    assert code == 0, out


def test_pin_unchanged_passes_changed_fails(tmp_path):
    repo = plan_repo(tmp_path)
    commit(repo, {"src/reg.test.ts": "it('reg', () => {})\n"}, "red")
    pin = head(repo)
    commit(repo, {"src/a.ts": "export const a = 2\n"}, "fix")
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T1", "--pin", pin)
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    commit(repo, {"src/reg.test.ts": "it('reg', () => { /* weakened */ })\n"}, "weaken")
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T1", "--pin", pin)
    assert code == 1 and "INTEGRITY FAIL pinned regression test changed: src/reg.test.ts" in out


def test_milestone_progress_only_plan_change_ok_with_approved(tmp_path):
    repo = plan_repo(tmp_path)
    approved = head(repo)
    commit(repo, {"src/a.ts": "export const a = 2\n", PLAN_PATH: plan_text(PLAN, "progress: M1 T1 done\n")})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", approved)
    assert code == 0 and out.strip() == "INTEGRITY OK", out


@pytest.mark.parametrize("where", ["sibling", "nested"])
def test_plan_path_resolves_across_worktrees_of_one_repo(tmp_path, where):
    """The coordinator runs the script from the milestone worktree against a task worktree of the same repo."""
    repo = plan_repo(tmp_path)
    approved = head(repo)
    wt = tmp_path / "task-wt" if where == "sibling" else repo / ".worktrees" / "task-wt"
    git(repo, "worktree", "add", "-q", "-b", "task", str(wt), "ms")
    commit(wt, {"src/a.ts": "export const a = 2\n"})
    for plan in (str(repo / PLAN_PATH), PLAN_PATH):  # the other worktree's absolute path, and the repo-relative one
        for extra in ([], ["--approved", approved]):
            code, out = run(wt, "ms", plan, "--task", "T1", *extra)
            assert code == 0 and out.strip() == "INTEGRITY OK", (plan, extra, out)
    commit(wt, {"src/other.ts": "o\n"})  # the task scope still bites
    code, out = run(wt, "ms", str(repo / PLAN_PATH), "--task", "T1", "--approved", approved)
    assert code == 1 and "outside task T1: src/other.ts" in out and "cannot read plan" not in out
    code, out = run(wt, "ms", "../elsewhere/plan.md", "--task", "T1")
    assert code == 1 and "cannot read plan" in out


def test_target_sha_decides_what_is_new_not_a_stale_local_integration(tmp_path):
    repo = plan_repo(tmp_path)  # local `integ` still sits at the original base
    git(repo, "switch", "-q", "-c", "fresh", "main")
    commit(repo, {"src/early.test.ts": "it('e', () => {})\n", "src/m1.ts": "m1\n"}, "M1 merged remotely")
    fresh = head(repo)
    git(repo, "switch", "-q", "ms")
    git(repo, "merge", "-q", "fresh")
    commit(repo, {"src/early.test.ts": "it('e', () => { /* edited */ })\n"})
    plan = str(repo / PLAN_PATH)
    code, out = run(repo, fresh, plan)  # the stale local ref calls the edited test new
    assert code == 0, out
    code, out = run(repo, fresh, plan, "--target", fresh)
    assert code == 1 and "existing test changed or deleted: src/early.test.ts" in out
    code, out = run(repo, fresh, plan, "--target", "0" * 40)
    assert code == 1 and "INTEGRITY FAIL cannot resolve target" in out


def test_milestone_diff_from_the_recorded_target_does_not_charge_earlier_milestones(tmp_path):
    repo = plan_repo(tmp_path)
    git(repo, "switch", "-q", "-c", "fresh", "main")
    commit(repo, {"src/m1.ts": "m1\n"}, "M1 merged remotely")
    fresh = head(repo)
    git(repo, "switch", "-q", "ms")
    git(repo, "merge", "-q", "fresh")
    commit(repo, {"src/c.ts": "c\n"})  # M2's own task file
    plan = str(repo / PLAN_PATH)
    code, out = run(repo, "main", plan, "--milestone", "M2", "--approved", appr(repo))
    assert code == 1 and "outside milestone M2: src/m1.ts" in out  # the stale base charges M1's file to M2
    code, out = run(repo, fresh, plan, "--milestone", "M2", "--target", fresh, "--approved", appr(repo))
    assert code == 0 and out.strip() == "INTEGRITY OK", out


def test_checked_commits_gate_who_built_the_milestone_files(tmp_path):
    repo = plan_repo(tmp_path)
    plan = str(repo / PLAN_PATH)
    shas = []
    for branch, edits in (("t1", {"src/a.ts": "export const a = 2\n"}), ("t2", {"src/b.ts": "b\n"})):  # both cut from the milestone head
        git(repo, "switch", "-qc", branch, "ms")
        commit(repo, edits, branch)
        shas.append(head(repo))
        git(repo, "switch", "-q", "ms")
    for branch in ("t1", "t2"):
        git(repo, "merge", "-q", "--no-ff", "-m", f"merge {branch}", branch)
    both = ",".join(shas)
    commit(repo, {PLAN_PATH: plan_text(PLAN, "progress\n"), "changes/2026-11-24-x/evidence/M1/gallery.md": "g\n"})  # coordinator paths
    code, out = run(repo, "main", plan, "--milestone", "M1", "--checked", both, "--approved", appr(repo))
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    code, out = run(repo, "main", plan, "--milestone", "M1", "--checked", shas[1], "--approved", appr(repo))  # T1's commit is not listed
    assert code == 1 and "INTEGRITY FAIL changed after the builder check: src/a.ts" in out
    assert "src/b.ts" not in out
    commit(repo, {"src/a.ts": "export const a = 3 // coordinator edit\n"})  # an in-scope file, changed outside a builder
    code, out = run(repo, "main", plan, "--milestone", "M1", "--checked", both, "--approved", appr(repo))
    assert code == 1 and "INTEGRITY FAIL changed after the builder check: src/a.ts" in out
    code, out = run(repo, "main", plan, "--milestone", "M1", "--approved", appr(repo))  # no --checked: scope is all it can say
    assert code == 0, out
    code, out = run(repo, "main", plan, "--milestone", "M1", "--checked", "nope", "--approved", appr(repo))
    assert code == 1 and "cannot resolve checked commit nope" in out
    commit(repo, {".github/workflows/ci.yml": "on: push\n"})  # protected paths keep their own message
    code, out = run(repo, "main", plan, "--milestone", "M1", "--checked", both, "--approved", appr(repo))
    assert "INTEGRITY FAIL CI config changed: .github/workflows/ci.yml" in out
    assert "changed after the builder check: .github" not in out


def test_a_plan_copy_outside_every_worktree_is_still_read_without_approved(tmp_path):
    """The M1 replay passes a plan copy from the scratchpad, never a path inside the repo."""
    repo = plan_repo(tmp_path)
    loose = tmp_path / "loose-plan.md"
    loose.write_text(plan_text(dict(PLAN, allowTestEdits=["src/a.test.ts"])))
    commit(repo, {"src/a.test.ts": "it('a', () => { /* edited */ })\n"})
    code, out = run(repo, "main", str(loose))
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    code, out = run(repo, "main", str(loose), "--approved", head(repo))  # an approved read needs a repo path
    assert code == 1 and "cannot read plan" in out


def test_milestone_accepts_approved_content_and_rejects_later_edits(tmp_path):
    # milestone 1 in a repo without a plan PR carries the approved delta and .cfactory/ on its own branch
    repo = plan_repo(tmp_path)
    commit(repo, {"changes/2026-11-24-x/delta.md": "## ADDED\n- req-1: a, revised [outcome-1]\n- req-2: b [outcome-1]\n", ".cfactory/check-plan.py": "# copy\n"})
    approved = head(repo)
    commit(repo, {"src/a.ts": "export const a = 2\n", PLAN_PATH: plan_text(PLAN, "progress: M1 T1 done\n")})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", approved)
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    commit(repo, {"changes/2026-11-24-x/delta.md": "## ADDED\n- req-1: a, weakened [outcome-1]\n- req-2: b [outcome-1]\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", approved)
    assert code == 1 and "delta changed: changes/2026-11-24-x/delta.md" in out, out


def test_milestone_without_approved_is_a_usage_error_not_a_skipped_plan_change(tmp_path):
    repo = plan_repo(tmp_path)
    commit(repo, {PLAN_PATH: plan_text(dict(PLAN, goalTurns=99))})  # a changed plan used to be skipped silently
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1")
    assert code == 2 and "INTEGRITY OK" not in out


def test_milestone_scope_comes_from_the_approved_plan(tmp_path):
    repo = plan_repo(tmp_path)
    approved = head(repo)
    commit(repo, {"src/other.ts": "o\n"})
    widened = json.loads(json.dumps(PLAN))
    widened["milestones"][0]["tasks"][0]["files"].append("src/other.ts")
    (repo / PLAN_PATH).write_text(plan_text(widened))  # uncommitted widening is ignored
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", approved)
    assert code == 1 and "outside milestone M1: src/other.ts" in out


def test_new_test_file_outside_task_scope_fails(tmp_path):
    repo = plan_repo(tmp_path)
    commit(repo, {"app/runtime/hidden.test.ts": "export const x = 1\n", "src/near.test.ts": "it('n', () => {})\n",
                  "lib/deep/n.spec.ts": "it('n', () => {})\n", "src/zzz/not_a_test.ts": "z\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T1")
    assert code == 1 and "outside task T1: app/runtime/hidden.test.ts" in out
    assert "outside task T1: src/near.test.ts" not in out and "outside task T1: lib/deep/n.spec.ts" not in out


def test_new_test_file_allowed_by_allow_test_edits_anywhere(tmp_path):
    plan = json.loads(json.dumps(PLAN))
    plan["milestones"][0]["tasks"][0]["allowTestEdits"].append("e2e/new.test.ts")
    repo = plan_repo(tmp_path, plan)
    commit(repo, {"e2e/new.test.ts": "it('n', () => {})\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T1")
    assert code == 0 and out.strip() == "INTEGRITY OK", out


@pytest.mark.parametrize("path,line,reason", [
    ("src/new.test.ts", "// eslint-disable-next-line", "added lint suppression eslint-disable"),
    ("src/new.test.ts", "it.skip('x', () => {})", "added line contains .skip("),
    ("src/runner.sh", "false || true", "added line contains || true"),
])
def test_new_files_get_both_scans(tmp_path, path, line, reason):
    repo = plan_repo(tmp_path)
    commit(repo, {path: f"{line}\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T1")
    assert code == 1 and f"INTEGRITY FAIL {reason}" in out, out


def test_approved_must_be_an_ancestor_of_head(tmp_path):
    repo = plan_repo(tmp_path)
    git(repo, "switch", "-qc", "other", "main")
    commit(repo, {"src/a.ts": "export const a = 9\n"}, "unrelated")
    foreign = head(repo)
    git(repo, "switch", "-q", "ms")
    commit(repo, {"src/a.ts": "export const a = 9\n"}, "same content, other history")
    for mode in ("--task", "--milestone"):
        code, out = run(repo, "main", str(repo / PLAN_PATH), mode, "T1" if mode == "--task" else "M1", "--approved", foreign)
        assert code == 1 and f"INTEGRITY FAIL approved {foreign} is not an ancestor of HEAD" in out, out
