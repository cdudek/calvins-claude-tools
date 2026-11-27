import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent / "test-integrity.sh"
BASE_FILES = {
    "src/a.ts": "export const a = 1\n",
    "src/a.test.ts": "it('a', () => {})\n",
    "package.json": "{}\n",
    ".factory/goal-brief.py": "x\n",
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
    (".factory/goal-brief.py", "harness changed"),
    (".factory/new.sh", "harness changed"),
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
    return "# plan\n\n```json factory\n" + json.dumps(plan, indent=1) + "\n```\n" + extra


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
    # milestone 1 in a repo without a plan PR carries the approved delta and .factory/ on its own branch
    repo = plan_repo(tmp_path)
    commit(repo, {"changes/2026-11-24-x/delta.md": "## ADDED\n- req-1: a, revised [outcome-1]\n- req-2: b [outcome-1]\n", ".factory/check-plan.py": "# copy\n"})
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


MAY_PLAN = {**PLAN, "milestones": [{**PLAN["milestones"][0], "mayTouch": ["src/api/*", "src/b.test.ts"]}, PLAN["milestones"][1]]}


def gap_repo(tmp_path, *log, edits=None, plan=MAY_PLAN):
    """MAY_PLAN is approved; the fix round's files are committed with the log lines under the plan's json block."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    repo = plan_repo(tmp_path, plan)
    commit(repo, {**(edits or {}), PLAN_PATH: plan_text(plan, "".join(f"{l}\n" for l in log))})
    return repo


def test_gap_fix_files_are_in_scope_only_when_logged_and_inside_may_touch(tmp_path):
    repo = gap_repo(tmp_path, "GAP-FIX M1 files=src/api/list.ts", edits={"src/api/list.ts": "x\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    repo = gap_repo(tmp_path / "n", edits={"src/api/list.ts": "x\n"})  # not logged
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 1 and "outside milestone M1: src/api/list.ts" in out
    repo = gap_repo(tmp_path / "o", "GAP-FIX M1 files=src/api/list.ts,src/secret.ts", edits={"src/api/list.ts": "x\n", "src/secret.ts": "x\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 1 and "outside milestone M1: src/secret.ts" in out and "outside milestone M1: src/api/list.ts" not in out


def test_gap_fix_task_scope_and_test_edit(tmp_path):
    """The fix task is cut from the milestone head, which already holds the log line, so its base is that head."""
    repo = gap_repo(tmp_path, "GAP-FIX M1 files=src/api/list.ts tests=src/b.test.ts")
    ms = head(repo)
    commit(repo, {"src/api/list.ts": "x\n", "src/b.test.ts": "it('b', () => { /* new rule */ })\n"})
    code, out = run(repo, ms, str(repo / PLAN_PATH), "--task", "M1-gap", "--approved", appr(repo))
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    commit(repo, {"src/a.ts": "export const a = 3\n"})  # a plan task's file, but not the fix task's
    code, out = run(repo, ms, str(repo / PLAN_PATH), "--task", "M1-gap", "--approved", appr(repo))
    assert code == 1 and "outside task M1-gap: src/a.ts" in out
    repo = gap_repo(tmp_path / "t", "GAP-FIX M1 files=src/api/list.ts")
    ms = head(repo)
    commit(repo, {"src/b.test.ts": "it('b', () => { /* x */ })\n"})
    code, out = run(repo, ms, str(repo / PLAN_PATH), "--task", "M1-gap", "--approved", appr(repo))
    assert code == 1 and "existing test changed or deleted: src/b.test.ts" in out  # not named in tests=


def test_unlogged_fix_task_fails(tmp_path):
    repo = gap_repo(tmp_path, edits={"src/api/a.ts": "x\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "M1-gap", "--approved", appr(repo))
    assert code == 1 and "no task or milestone M1-gap" in out


def ms_run(repo, *args):
    return run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo), *args)


def test_milestone_unions_every_logged_round(tmp_path):
    log = ("GAP-FIX M1 round=1 files=src/api/a.ts", "GAP-FIX M1 round=2 files=src/api/b.ts tests=src/b.test.ts")
    repo = gap_repo(tmp_path, *log, edits={"src/api/a.ts": "x\n", "src/api/b.ts": "x\n", "src/b.test.ts": "it('b', () => { /* r2 */ })\n"})
    code, out = ms_run(repo)
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    repo = gap_repo(tmp_path / "n", *log[:1], edits={"src/api/a.ts": "x\n", "src/api/b.ts": "x\n"})  # round 2 not logged
    code, out = ms_run(repo)
    assert code == 1 and "outside milestone M1: src/api/b.ts" in out and "outside milestone M1: src/api/a.ts" not in out


def test_legacy_line_without_round_counts_as_round_one(tmp_path):
    repo = gap_repo(tmp_path, "GAP-FIX M1 files=src/api/a.ts", "GAP-FIX M1 round=2 files=src/api/b.ts", edits={"src/api/a.ts": "x\n", "src/api/b.ts": "x\n"})
    assert ms_run(repo)[0] == 0
    repo = gap_repo(tmp_path / "d", "GAP-FIX M1 files=src/api/a.ts", "GAP-FIX M1 round=1 files=src/api/b.ts", edits={"src/api/a.ts": "x\n"})
    code, out = ms_run(repo)
    assert code == 1 and "gap rounds for M1 must be numbered 1..n, each round once" in out
    repo = gap_repo(tmp_path / "t", "GAP-FIX M1 files=src/api/a.ts", "GAP-FIX M1 files=src/api/b.ts", edits={"src/api/a.ts": "x\n"})
    assert "each round once" in ms_run(repo)[1]  # two legacy lines are a duplicate round 1


def test_rounds_must_be_consecutive_and_unique(tmp_path):
    for i, log in enumerate((("GAP-FIX M1 round=2 files=src/api/a.ts",), ("GAP-FIX M1 round=1 files=src/api/a.ts", "GAP-FIX M1 round=3 files=src/api/b.ts"),
                             ("GAP-FIX M1 round=1 files=src/api/a.ts", "GAP-FIX M1 round=1 files=src/api/b.ts"), ("GAP-FIX M1 round=0 files=src/api/a.ts",))):
        code, out = ms_run(gap_repo(tmp_path / str(i), *log, edits={"src/api/a.ts": "x\n"}))
        assert code == 1 and "each round once" in out, log
    # the same check guards the fix task, so a bad log cannot be run round by round
    repo = gap_repo(tmp_path / "t", "GAP-FIX M1 round=2 files=src/api/a.ts")
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "M1-gap2", "--approved", appr(repo))
    assert code == 1 and "each round once" in out


def test_more_rounds_than_the_cap_fail(tmp_path):
    four = tuple(f"GAP-FIX M1 round={n} files=src/api/a.ts" for n in (1, 2, 3, 4))  # the default cap is 3
    code, out = ms_run(gap_repo(tmp_path / "d", *four, edits={"src/api/a.ts": "x\n"}))
    assert code == 1 and "more than 3 gap rounds for M1" in out
    one = {**MAY_PLAN, "milestones": [{**MAY_PLAN["milestones"][0], "gapRounds": 1}, PLAN["milestones"][1]]}
    code, out = ms_run(gap_repo(tmp_path / "o", *four[:2], edits={"src/api/a.ts": "x\n"}, plan=one))
    assert code == 1 and "more than 1 gap rounds for M1" in out
    five = {**MAY_PLAN, "milestones": [{**MAY_PLAN["milestones"][0], "gapRounds": 5}, PLAN["milestones"][1]]}
    code, out = ms_run(gap_repo(tmp_path / "f", *four, edits={"src/api/a.ts": "x\n"}, plan=five))
    assert code == 0 and out.strip() == "INTEGRITY OK", out


def test_fix_task_is_scoped_to_exactly_its_round(tmp_path):
    repo = gap_repo(tmp_path, "GAP-FIX M1 round=1 files=src/api/a.ts", "GAP-FIX M1 round=2 files=src/api/b.ts tests=src/b.test.ts")
    ms = head(repo)
    commit(repo, {"src/api/b.ts": "x\n", "src/b.test.ts": "it('b', () => { /* r2 */ })\n"})
    task = lambda t: run(repo, ms, str(repo / PLAN_PATH), "--task", t, "--approved", appr(repo))
    code, out = task("M1-gap2")
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    code, out = task("M1-gap")  # alias of round 1, which owns only src/api/a.ts
    assert code == 1 and "outside task M1-gap: src/api/b.ts" in out and "existing test changed or deleted: src/b.test.ts" in out
    code, out = task("M1-gap1")
    assert code == 1 and "outside task M1-gap1: src/api/b.ts" in out
    code, out = task("M1-gap3")
    assert code == 1 and "no task or milestone M1-gap3" in out
    commit(repo, {"src/api/a.ts": "x\n"})  # round 1's file is not round 2's
    assert "outside task M1-gap2: src/api/a.ts" in task("M1-gap2")[1]


def test_every_round_stays_inside_the_approved_may_touch(tmp_path):
    log = ("GAP-FIX M1 round=1 files=src/api/a.ts", "GAP-FIX M1 round=2 files=src/secret.ts,src/api/deep/x.ts")
    code, out = ms_run(gap_repo(tmp_path, *log, edits={"src/api/a.ts": "x\n", "src/secret.ts": "x\n", "src/api/deep/x.ts": "x\n"}))
    assert code == 1 and "outside milestone M1: src/secret.ts" in out and "outside milestone M1: src/api/deep/x.ts" in out
    assert "outside milestone M1: src/api/a.ts" not in out


def test_gap_rounds_work_for_a_milestone_with_a_letter_suffix(tmp_path):
    first = {**MAY_PLAN["milestones"][0], "id": "M1a"}
    plan = {**MAY_PLAN, "milestones": [first, PLAN["milestones"][1]]}
    repo = gap_repo(tmp_path, "GAP-FIX M1a round=1 files=src/api/a.ts", "GAP-FIX M1a round=2 files=src/api/b.ts", edits={"src/api/a.ts": "x\n", "src/api/b.ts": "x\n"}, plan=plan)
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1a", "--approved", appr(repo))
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    ms = head(repo)
    commit(repo, {"src/api/a.ts": "y\n"})
    code, out = run(repo, ms, str(repo / PLAN_PATH), "--task", "M1a-gap1", "--approved", appr(repo))
    assert code == 0, out
    code, out = run(repo, ms, str(repo / PLAN_PATH), "--task", "M1a-gap2", "--approved", appr(repo))
    assert code == 1 and "outside task M1a-gap2: src/api/a.ts" in out
    # a line for M1 must not be read as one for M1a, nor the reverse
    repo = gap_repo(tmp_path / "x", "GAP-FIX M1 round=1 files=src/api/a.ts", edits={"src/api/a.ts": "x\n"}, plan=plan)
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1a", "--approved", appr(repo))
    assert code == 1 and "outside milestone M1a: src/api/a.ts" in out


def test_gap_log_line_without_may_touch_widens_nothing(tmp_path):
    repo = plan_repo(tmp_path)  # the approved plan has no mayTouch
    commit(repo, {"src/api/list.ts": "x\n", PLAN_PATH: plan_text(PLAN, "GAP-FIX M1 files=src/api/list.ts\n")})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 1 and "outside milestone M1: src/api/list.ts" in out


def test_star_never_crosses_a_slash_in_may_touch(tmp_path):
    repo = gap_repo(tmp_path, "GAP-FIX M1 files=src/api/deep/x.ts,src/api/ok.ts", edits={"src/api/deep/x.ts": "x\n", "src/api/ok.ts": "x\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 1 and "outside milestone M1: src/api/deep/x.ts" in out and "outside milestone M1: src/api/ok.ts" not in out


def test_wildcard_first_segment_and_double_star_match_nothing(tmp_path):
    plan = {**PLAN, "milestones": [{**PLAN["milestones"][0], "mayTouch": ["*", "**", "*/x.ts", "src/**"]}, PLAN["milestones"][1]]}
    repo = plan_repo(tmp_path, plan)
    commit(repo, {"src/x.ts": "x\n", "a/x.ts": "x\n", PLAN_PATH: plan_text(plan, "GAP-FIX M1 files=src/x.ts,a/x.ts\n")})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 1 and "outside milestone M1: src/x.ts" in out and "outside milestone M1: a/x.ts" in out


def test_uncommitted_gap_log_line_grants_no_scope(tmp_path):
    repo = gap_repo(tmp_path, edits={"src/api/list.ts": "x\n"})
    (repo / PLAN_PATH).write_text(plan_text(MAY_PLAN, "GAP-FIX M1 files=src/api/list.ts\n"))  # in the working file only
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 1 and "outside milestone M1: src/api/list.ts" in out


# ---- add-only gate for the existing tests a task may edit ----
AO_PLAN = {**PLAN, "milestones": [{**PLAN["milestones"][0], "tasks": [
    {**PLAN["milestones"][0]["tasks"][0], "allowTestEdits": ["src/a.test.ts", "tests/test_a.py", "src/b.test.ts", "e2e/flow.spec.rb"]}, PLAN["milestones"][0]["tasks"][1]]}, PLAN["milestones"][1]]}
JS_OLD = """describe('x', () => {
  it('adds', () => {
    expect(add(1, 2)).toBe(3)
    expect(add(2, 2)).toEqual(4)
  })
  it('lists', () => {
    expect(list()).toHaveLength(2)
  }, 5000)
})
"""
PY_OLD = """import pytest


def test_add():
    assert add(1, 2) == 3
    assert add(2, 2) == 4


def test_flag():
    assert flag()
"""


def addonly(tmp_path, path, old, new):
    """`old` is the existing test at the branch the task is cut from; `new` is what the task commits."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    repo = plan_repo(tmp_path, AO_PLAN)
    commit(repo, {path: old}, "existing test")
    ms = head(repo)
    git(repo, "switch", "-qc", "t1")
    if new is None:
        (repo / path).unlink()
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "delete")
    else:
        commit(repo, {path: new} if new != old else {"src/a.ts": "export const a = 2\n"})  # same text: the allowed file is not touched
    return run(repo, ms, str(repo / PLAN_PATH), "--task", "T1", "--approved", appr(repo))


def ao_fail(tmp_path, path, old, new, *reasons):
    code, out = addonly(tmp_path, path, old, new)
    assert code == 1 and all(f"INTEGRITY FAIL add-only gate: {path}: " in out and r in out for r in reasons), (reasons, out)


def test_add_only_accepts_more_tests_more_assertions_and_a_renamed_symbol(tmp_path):
    grown = JS_OLD.replace("add(", "sum(") + "it('new', () => { expect(1).toBe(1) })\n"  # every `add` renamed, one test added
    grown = grown.replace("expect(list()).toHaveLength(2)", "expect(list()).toHaveLength(2)\n    expect(list()).toBeTruthy()")
    code, out = addonly(tmp_path / "js", "src/a.test.ts", JS_OLD, grown)
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    code, out = addonly(tmp_path / "py", "tests/test_a.py", PY_OLD, PY_OLD.replace("add(1", "plus(1").replace("add(2", "plus(2") + "\n\ndef test_more():\n    assert 1 == 1\n")
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    code, out = addonly(tmp_path / "same", "src/a.test.ts", JS_OLD, JS_OLD)  # the allowed file is not touched
    assert code == 0, out


def test_add_only_refuses_a_removed_or_renamed_block(tmp_path):
    ao_fail(tmp_path / "a", "src/a.test.ts", JS_OLD, JS_OLD.replace("it('lists'", "it('lists the rows'"), "block lists: test block removed or renamed")
    ao_fail(tmp_path / "b", "src/a.test.ts", JS_OLD, JS_OLD.split("  it('lists'")[0] + "})\n", "block lists: test block removed or renamed")
    ao_fail(tmp_path / "c", "tests/test_a.py", PY_OLD, PY_OLD.split("def test_flag")[0], "block test_flag: test block removed or renamed")
    ao_fail(tmp_path / "d", "src/a.test.ts", JS_OLD, "", "block adds: test block removed or renamed", "block x: test block removed or renamed")
    ao_fail(tmp_path / "e", "src/a.test.ts", JS_OLD, None, "the file is deleted")


def test_add_only_refuses_fewer_assertions_in_a_surviving_block(tmp_path):
    ao_fail(tmp_path / "a", "src/a.test.ts", JS_OLD, JS_OLD.replace("    expect(add(2, 2)).toEqual(4)\n", ""), "block adds: assertions dropped from 2 to 1")
    ao_fail(tmp_path / "b", "tests/test_a.py", PY_OLD, PY_OLD.replace("    assert add(2, 2) == 4\n", ""), "block test_add: assertions dropped from 2 to 1")
    ao_fail(tmp_path / "c", "tests/test_a.py", PY_OLD, PY_OLD.replace("    assert flag()\n", "    flag()\n"), "block test_flag: assertions dropped from 1 to 0")
    # another test's assertions do not pay for it
    ao_fail(tmp_path / "d", "src/a.test.ts", JS_OLD, JS_OLD.replace("    expect(add(2, 2)).toEqual(4)\n", "").replace("it('lists', () => {\n", "it('lists', () => {\n    expect(1).toBe(1)\n"), "block adds: assertions dropped")


def test_add_only_refuses_a_skip_or_focus_marker(tmp_path):
    for i, (old, new) in enumerate((("it('adds'", "it.skip('adds'"), ("it('adds'", "it.only('adds'"), ("it('adds'", "it.todo('adds'"), ("it('adds'", "it.fixme('adds'"),
                                    ("it('adds'", "xit('adds'"), ("describe('x'", "xdescribe('x'"))):
        ao_fail(tmp_path / f"js{i}", "src/a.test.ts", JS_OLD, JS_OLD.replace(old, new), "skip or focus marker added")
    ao_fail(tmp_path / "new", "src/a.test.ts", JS_OLD, JS_OLD + "xtest('later', () => {})\n", "block later: skip or focus marker added")
    for i, (old, new) in enumerate((("def test_add", "@pytest.mark.skip(reason='x')\ndef test_add"), ("def test_add", "@pytest.mark.xfail\ndef test_add"),
                                    ("    assert flag()", "    pytest.skip('x')\n    assert flag()"))):
        ao_fail(tmp_path / f"py{i}", "tests/test_a.py", PY_OLD, PY_OLD.replace(old, new), "skip or focus marker added")
    ao_fail(tmp_path / "pytop", "tests/test_a.py", PY_OLD, PY_OLD.replace("import pytest\n", "import pytest\npytest.skip('all', allow_module_level=True)\n"), "block <top of file>: skip or focus marker added")


def test_add_only_refuses_strict_matchers_traded_for_loose_ones(tmp_path):
    loose = JS_OLD.replace("expect(add(1, 2)).toBe(3)", "expect(add(1, 2)).toBeTruthy()")
    ao_fail(tmp_path / "a", "src/a.test.ts", JS_OLD, loose, "block adds: strict matchers replaced by loose ones")
    ao_fail(tmp_path / "b", "src/a.test.ts", JS_OLD, JS_OLD.replace(".toEqual(4)", ".toContain(4)").replace(".toBe(3)", ".toMatch(3)"), "strict matchers replaced by loose ones")
    ao_fail(tmp_path / "c", "tests/test_a.py", PY_OLD, PY_OLD.replace("assert add(1, 2) == 3", "assert add(1, 2)"), "block test_add: strict matchers replaced by loose ones")
    # a strict matcher that goes without a loose one coming in is not this rule (the assertion count still guards it)
    ok_ = JS_OLD.replace("expect(add(1, 2)).toBe(3)", "expect(add(1, 2)).toBe(3)\n    expect(add(1, 2)).toBeDefined()").replace(".toEqual(4)", ".toEqual(4)")
    assert addonly(tmp_path / "ok", "src/a.test.ts", JS_OLD, ok_)[0] == 0


def test_add_only_refuses_a_raised_timeout(tmp_path):
    ao_fail(tmp_path / "a", "src/a.test.ts", JS_OLD, JS_OLD.replace("}, 5000)", "}, 30000)"), "block lists: timeout raised from 5000 to 30000")
    ao_fail(tmp_path / "b", "src/a.test.ts", JS_OLD, JS_OLD.replace("it('adds', () => {", "it('adds', () => {\n    jest.setTimeout(9000)"), "block adds: timeout raised from 0 to 9000")
    ao_fail(tmp_path / "c", "src/a.test.ts", JS_OLD.replace("}, 5000)", "}, { timeout: 1000 })"), JS_OLD.replace("}, 5000)", "}, { timeout: 8000 })"), "timeout raised from 1000 to 8000")
    ao_fail(tmp_path / "d", "src/a.test.ts", JS_OLD, JS_OLD.replace("it('adds', () => {", "it('adds', async () => {", 1).replace("  })\n  it('lists'", "  }, 60_000)\n  it('lists'"), "block adds: timeout raised from 0 to 60000")
    assert addonly(tmp_path / "ok", "src/a.test.ts", JS_OLD, JS_OLD.replace("}, 5000)", "}, 3000)"))[0] == 0  # a lower timeout is fine


def test_add_only_also_guards_the_tests_of_a_gap_round(tmp_path):
    repo = gap_repo(tmp_path, "GAP-FIX M1 round=1 files=src/api/list.ts tests=src/b.test.ts")
    ms = head(repo)
    commit(repo, {"src/api/list.ts": "x\n", "src/b.test.ts": "it('b2', () => {})\n"})  # block b is gone
    code, out = run(repo, ms, str(repo / PLAN_PATH), "--task", "M1-gap", "--approved", appr(repo))
    assert code == 1 and "INTEGRITY FAIL add-only gate: src/b.test.ts: block b: test block removed or renamed" in out, out
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 1 and "add-only gate: src/b.test.ts: block b:" in out


# ---- the gap lane fails closed ----
def test_invalid_gap_rounds_in_the_approved_plan_is_an_error_not_the_default(tmp_path):
    for i, bad in enumerate((0, 6, -1, "3", 2.5, True, None)):
        plan = {**MAY_PLAN, "milestones": [{**MAY_PLAN["milestones"][0], "gapRounds": bad}, PLAN["milestones"][1]]}
        repo = gap_repo(tmp_path / str(i), "GAP-FIX M1 round=1 files=src/api/a.ts", edits={"src/api/a.ts": "x\n"}, plan=plan)
        for mode, arg in (("--milestone", "M1"), ("--task", "M1-gap")):
            base = "main" if mode == "--milestone" else head(repo)
            code, out = run(repo, base, str(repo / PLAN_PATH), mode, arg, "--approved", appr(repo))
            assert code == 1 and "gapRounds for M1 must be a whole number from 1 to 5" in out, (bad, mode, out)


def test_a_gap_task_requires_approved(tmp_path):
    repo = gap_repo(tmp_path, "GAP-FIX M1 round=1 files=src/api/a.ts", edits={"src/api/a.ts": "x\n"})
    for t in ("M1-gap", "M1-gap2", "M1a-gap3"):
        code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", t)
        assert code == 2 and out == "", t
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "T1")  # a plan task still runs without it
    assert code in (0, 1) and "requires" not in out


def test_may_touch_and_gap_rounds_come_from_the_approved_plan_not_head(tmp_path):
    repo = gap_repo(tmp_path, "GAP-FIX M1 round=1 files=src/secret.ts", "GAP-FIX M1 round=2 files=src/api/a.ts", edits={"src/secret.ts": "x\n", "src/api/a.ts": "x\n"})
    wide = {**MAY_PLAN, "milestones": [{**MAY_PLAN["milestones"][0], "mayTouch": ["src/*"], "gapRounds": 1}, PLAN["milestones"][1]]}
    commit(repo, {PLAN_PATH: plan_text(wide, "GAP-FIX M1 round=1 files=src/secret.ts\nGAP-FIX M1 round=2 files=src/api/a.ts\n")})  # HEAD widens both
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--task", "M1-gap", "--approved", appr(repo))
    assert code == 1 and "outside task M1-gap: src/secret.ts" in out and "more than 1" not in out, out  # the approved cap is 3, not HEAD's 1
    assert "outside task M1-gap2: src/api/a.ts" not in run(repo, "main", str(repo / PLAN_PATH), "--task", "M1-gap2", "--approved", appr(repo))[1]  # round 2 exists under the approved cap of 3


def test_handover_markdown_in_the_change_folder_is_not_flagged(tmp_path):
    repo = plan_repo(tmp_path)
    commit(repo, {"src/a.ts": "export const a = 2\n", "changes/2026-11-24-x/handover-2026-11-26.md": "# handover\n", "changes/2026-11-24-x/handover-M1.md": "x\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    for name in ("changes/2026-11-24-x/handover-x.txt", "changes/2026-11-24-x/handover.md", "changes/2026-11-24-x/notes/handover-a.md", "changes/other/handover-a.md"):
        (tmp_path / name.replace("/", "_")).mkdir()
        repo = plan_repo(tmp_path / name.replace("/", "_"))
        commit(repo, {"src/a.ts": "export const a = 2\n", name: "x\n"})
        code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
        assert code == 1 and f"outside milestone M1: {name}" in out, name


DUP_OLD = """it('dup', () => {
  expect(a()).toBe(1)
  expect(b()).toBe(2)
})
it('dup', () => {
  expect(c()).toBe(3)
  expect(d()).toBe(4)
}, 5000)
"""


def test_add_only_sums_blocks_that_share_a_name(tmp_path):
    ao_fail(tmp_path / "a", "src/a.test.ts", DUP_OLD, DUP_OLD.split("it('dup', () => {\n  expect(c")[0], "block dup: assertions dropped from 4 to 2")  # one copy deleted
    ao_fail(tmp_path / "b", "src/a.test.ts", DUP_OLD, DUP_OLD.replace("  expect(b()).toBe(2)\n", "").replace("}, 5000)", "}, 9000)"), "block dup: assertions dropped", "block dup: timeout raised from 5000 to 9000")
    ao_fail(tmp_path / "c", "src/a.test.ts", DUP_OLD, DUP_OLD.replace("}, 5000)", "}, 4000)").replace("it('dup', () => {\n  expect(a", "it.skip('dup', () => {\n  expect(a", 1), "block dup: skip or focus marker added")
    ao_fail(tmp_path / "d", "src/a.test.ts", DUP_OLD, DUP_OLD.replace("it('dup'", "it('dup2'"), "block dup: test block removed or renamed")
    # the same assertions spread over the two copies in another way stay equal in total
    spread = DUP_OLD.replace("  expect(b()).toBe(2)\n", "").replace("  expect(c()).toBe(3)\n", "  expect(c()).toBe(3)\n  expect(b()).toBe(2)\n")
    assert addonly(tmp_path / "ok", "src/a.test.ts", DUP_OLD, spread)[0] == 0


def test_add_only_does_not_count_comments_or_strings_as_assertions(tmp_path):
    base = "it('x', () => {\n  expect(a()).toBe(1)\n})\n"
    for i, new in enumerate(("it('x', () => {\n  // expect(a()).toBe(1)\n})\n", "it('x', () => {\n  const s = 'expect(a()).toBe(1)'\n})\n",
                             "it('x', () => {\n  /* expect(a()).toBe(1) */\n})\n", "it('x', () => {\n  log(`expect(a())`) // expect(b())\n})\n")):
        ao_fail(tmp_path / f"js{i}", "src/a.test.ts", base, new, "block x: assertions dropped from 1 to 0")
    pbase = "def test_x():\n    assert a() == 1\n    self.assertEqual(a(), 1)\n"
    for i, new in enumerate(("def test_x():\n    # assert a() == 1\n    # self.assertEqual(a(), 1)\n", "def test_x():\n    s = 'assert a() == 1'\n    t = \"self.assertEqual(a(), 1)\"\n",
                             "def test_x():\n    r = assert_ok(1)\n    q = x.assert_called(1)\n")):
        ao_fail(tmp_path / f"py{i}", "tests/test_a.py", pbase, new, "block test_x: assertions dropped from 2 to 0")
    # `expect (` with a space and a `self.assert*(` call still count
    assert addonly(tmp_path / "ok", "src/a.test.ts", base, "it('x', () => {\n  expect (a()).toBe(1)\n  // expect(b())\n})\n")[0] == 0
    assert addonly(tmp_path / "okp", "tests/test_a.py", pbase, pbase.replace("assert a() == 1", "assert a() == 1  # fine") + "    self.assertTrue(a())\n")[0] == 0


def test_add_only_parses_timeout_literals_and_fails_closed_on_the_rest(tmp_path):
    base = "it('t', async () => {\n  expect(a()).toBe(1)\n}, 5000)\n"
    for i, big in enumerate(("0x7530", "30_000", "3e4", "2.5e4", "0X9C40")):
        ao_fail(tmp_path / f"lit{i}", "src/a.test.ts", base, base.replace("5000", big), "block t: timeout raised from 5000 to ")
    assert addonly(tmp_path / "low", "src/a.test.ts", base, base.replace("5000", "0x1388"))[0] == 0  # 0x1388 is 5000
    assert addonly(tmp_path / "same", "src/a.test.ts", base, base.replace("5000", "5_000"))[0] == 0
    ao_fail(tmp_path / "var", "src/a.test.ts", base, base.replace("5000", "LIMIT"), "block t: timeout LIMIT is not a literal and changed")
    ao_fail(tmp_path / "expr", "src/a.test.ts", "it('t', () => {\n  expect(1).toBe(1)\n  page.go(u, { timeout: 100 })\n})\n",
            "it('t', () => {\n  expect(1).toBe(1)\n  page.go(u, { timeout: BASE * 2 })\n})\n", "is not a literal and changed")
    ao_fail(tmp_path / "set", "src/a.test.ts", base, base.replace("  expect", "  jest.setTimeout(LIMIT + 1)\n  expect"), "is not a literal and changed")
    unchanged = "it('t', () => {\n  expect(1).toBe(1)\n  page.go(u, { timeout: LIMIT })\n})\n"
    assert addonly(tmp_path / "ok", "src/a.test.ts", unchanged, unchanged.replace("expect(1)", "expect(2)") + "it('n', () => { expect(1).toBe(1) })\n")[0] == 0


def test_add_only_never_skips_an_unsupported_file_type(tmp_path):
    ao_fail(tmp_path / "a", "e2e/flow.spec.rb", "it 'a' do\nend\n", "it 'a' do\n  skip\nend\n", "unsupported file type, cannot verify")
    ao_fail(tmp_path / "b", "e2e/flow.spec.rb", "it 'a' do\nend\n", None, "unsupported file type, cannot verify")
    assert addonly(tmp_path / "c", "e2e/flow.spec.rb", "it 'a' do\nend\n", "it 'a' do\nend\n")[0] == 0  # not edited: nothing to verify


def test_add_only_knows_more_skip_markers_and_early_exits(tmp_path):
    base = "it('x', () => {\n  expect(a()).toBe(1)\n})\n"
    for i, line in enumerate(("  test.fixme(true)", "  this.skip()", "  it.skipIf(ci)('y', () => {})", "  it.runIf(ci)('y', () => {})", "  test.fixme()")):
        ao_fail(tmp_path / f"js{i}", "src/a.test.ts", base, base.replace("  expect", line + "\n  expect"), "skip or focus marker added")
    pbase = "def test_x():\n    assert a() == 1\n"
    for i, (old, new) in enumerate((("def test_x", "@unittest.skip('x')\ndef test_x"), ("def test_x", "@unittest.skipIf(ci, 'x')\ndef test_x"), ("def test_x", "@unittest.skipUnless(ci, 'x')\ndef test_x"),
                                    ("    assert", "    pytest.importorskip('numpy')\n    assert"))):
        ao_fail(tmp_path / f"py{i}", "tests/test_a.py", pbase, pbase.replace(old, new), "skip or focus marker added")
    for i, line in enumerate(("  return", "  return;", "  if (false) { expect(1) }")):
        ao_fail(tmp_path / f"early{i}", "src/a.test.ts", base, base.replace("  expect", line + "\n  expect"), "block x: early exit added before the first assertion")
    for i, line in enumerate(("    return", "    if 0:\n        pass", "    if False:\n        pass")):
        ao_fail(tmp_path / f"pyearly{i}", "tests/test_a.py", pbase, pbase.replace("    assert", line + "\n    assert"), "block test_x: early exit added before the first assertion")
    # a return after the first assertion, or one that was already there, is fine
    assert addonly(tmp_path / "ok", "src/a.test.ts", base, base.replace("})", "  return\n})"))[0] == 0
    early = "it('x', () => {\n  return\n  expect(a()).toBe(1)\n})\n"
    assert addonly(tmp_path / "okold", "src/a.test.ts", early, early.replace("toBe(1)", "toBe(2)"))[0] == 0


def test_kickoff_and_handover_exemptions_cover_one_path_segment_only(tmp_path):
    for i, (name, reason) in enumerate((("changes/2026-11-24-x/handover-x/y.md", "outside milestone M1: changes/2026-11-24-x/handover-x/y.md"),
                                        ("changes/2026-11-24-x/handover-x/delta.md", "delta changed: changes/2026-11-24-x/handover-x/delta.md"),
                                        ("changes/2026-11-24-x/kickoff-a/plan.md", "plan changed: changes/2026-11-24-x/kickoff-a/plan.md"),
                                        ("changes/2026-11-24-x/kickoff-a/b.md", "outside milestone M1: changes/2026-11-24-x/kickoff-a/b.md"))):
        (tmp_path / str(i)).mkdir()
        repo = plan_repo(tmp_path / str(i))
        commit(repo, {"src/a.ts": "export const a = 2\n", name: "x\n"})
        code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
        assert code == 1 and reason in out, (name, out)
    (tmp_path / "ok").mkdir()
    repo = plan_repo(tmp_path / "ok")
    commit(repo, {"src/a.ts": "export const a = 2\n", "changes/2026-11-24-x/kickoff-M1.md": "k\n", "changes/2026-11-24-x/handover-a.md": "h\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 0 and out.strip() == "INTEGRITY OK", out


def test_add_only_counts_node_assert_calls(tmp_path):
    base = "it('x', () => {\n  assert.strictEqual(a(), 1)\n  assert (b)\n  assert.deepStrictEqual(c(), [1])\n})\n"
    ao_fail(tmp_path / "a", "src/a.test.ts", base, base.replace("  assert (b)\n", ""), "block x: assertions dropped from 3 to 2")
    ao_fail(tmp_path / "b", "src/a.test.ts", base, base.replace("  assert.strictEqual(a(), 1)\n", "  expect(a()).toBeTruthy()\n"), "block x: strict matchers replaced by loose ones")
    ao_fail(tmp_path / "c", "src/a.test.ts", base, base.replace("assert.deepStrictEqual(c(), [1])", "expect(c()).toBeDefined()"), "block x: strict matchers replaced by loose ones")
    assert addonly(tmp_path / "ok", "src/a.test.ts", base, base.replace("a(), 1", "a(), 2") + "it('y', () => { assert.equal(1, 1) })\n")[0] == 0


def test_add_only_fails_closed_on_a_third_argument_that_is_not_a_literal(tmp_path):
    base = "it('t', async () => {\n  expect(a()).toBe(1)\n}, 5000)\n"
    ao_fail(tmp_path / "expr", "src/a.test.ts", base, base.replace("5000", "BASE * 2"), "is not a literal and changed")
    ao_fail(tmp_path / "name", "src/a.test.ts", base, base.replace("5000", "LIMIT"), "block t: timeout LIMIT is not a literal and changed")
    ao_fail(tmp_path / "gone", "src/a.test.ts", base, base.replace("}, 5000)", "})"), "block t: timeout removed, cannot verify")
    ao_fail(tmp_path / "opts", "src/a.test.ts", "it('t', () => {\n  expect(a()).toBe(1)\n}, { timeout: 100 })\n", "it('t', () => {\n  expect(a()).toBe(1)\n}, { timeout: LIMIT })\n", "is not a literal and changed")
    one = "it('t', () => { expect(a()).toBe(1) }, 5000)\n"  # on the test line itself
    ao_fail(tmp_path / "line", "src/a.test.ts", one, one.replace("5000", "SLOW"), "is not a literal and changed")
    assert addonly(tmp_path / "ok", "src/a.test.ts", base, base.replace("toBe(1)", "toBe(2)"))[0] == 0  # unchanged argument


def test_add_only_fails_when_the_block_count_of_a_name_drops(tmp_path):
    two = "it('dup', () => {\n  expect(a()).toBe(1)\n})\nit('dup', () => {\n  expect(b()).toBe(2)\n})\n"
    merged = "it('dup', () => {\n  expect(a()).toBe(1)\n  expect(b()).toBe(2)\n})\n"  # same total, one block fewer
    ao_fail(tmp_path / "a", "src/a.test.ts", two, merged, "block dup: block count dropped from 2 to 1")
    ao_fail(tmp_path / "b", "tests/test_a.py", "def test_d():\n    assert a() == 1\n\n\ndef test_d():\n    assert b() == 2\n", "def test_d():\n    assert a() == 1\n    assert b() == 2\n", "block test_d: block count dropped from 2 to 1")
    assert addonly(tmp_path / "ok", "src/a.test.ts", two, two + "it('dup', () => { expect(1).toBe(1) })\n")[0] == 0


def test_add_only_counts_nothing_inside_multi_line_comments_and_literals(tmp_path):
    base = "it('x', () => {\n  expect(a()).toBe(1)\n})\n"
    for i, new in enumerate(("it('x', () => {\n  /*\n  expect(a()).toBe(1)\n  */\n})\n", "it('x', () => {\n  /* start\n  expect(a()).toBe(1) */\n})\n",
                             "it('x', () => {\n  const s = `\n  expect(a()).toBe(1)\n  `\n})\n")):
        ao_fail(tmp_path / f"js{i}", "src/a.test.ts", base, new, "block x: assertions dropped from 1 to 0")
    pbase = "def test_x():\n    assert a() == 1\n"
    ao_fail(tmp_path / "py", "tests/test_a.py", pbase, 'def test_x():\n    """\n    assert a() == 1\n    """\n', "block test_x: assertions dropped from 1 to 0")
    ghost = "/*\nit('ghost', () => {\n  expect(1).toBe(1)\n})\n*/\n" + base
    assert addonly(tmp_path / "ok", "src/a.test.ts", ghost, base)[0] == 0  # a test inside a comment is not a block
    live = "const t = `\nit('ghost', () => {})\n`\n" + base
    assert addonly(tmp_path / "ok2", "src/a.test.ts", live, base)[0] == 0
    assert addonly(tmp_path / "ok3", "src/a.test.ts", base, "/* header\n   comment */\n" + base)[0] == 0


def test_kickoff_exemption_needs_the_md_extension_and_one_segment(tmp_path):
    for i, name in enumerate(("changes/2026-11-24-x/kickoff-M1.txt", "changes/2026-11-24-x/kickoff-a/b.md", "changes/2026-11-24-x/kickoff-M1")):
        (tmp_path / str(i)).mkdir()
        repo = plan_repo(tmp_path / str(i))
        commit(repo, {"src/a.ts": "export const a = 2\n", name: "x\n"})
        code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
        assert code == 1 and f"outside milestone M1: {name}" in out, (name, out)
    (tmp_path / "ok").mkdir()
    repo = plan_repo(tmp_path / "ok")
    commit(repo, {"src/a.ts": "export const a = 2\n", "changes/2026-11-24-x/kickoff-M1.md": "k\n", "changes/2026-11-24-x/kickoff-all.md": "k\n"})
    code, out = run(repo, "main", str(repo / PLAN_PATH), "--milestone", "M1", "--approved", appr(repo))
    assert code == 0 and out.strip() == "INTEGRITY OK", out


# ---- parameterised and modified blocks are blocks ----
SEARCH_DOORS = """describe('search server door', () => {
  it.each([
    ['a', 1],
    ['b', 2],
  ])('search server door compatibility %s', (k, v) => {
    expect(door(k)).toBe(v)
    expect(door(k)).toEqual(v)
    expect(door(k)).toBeDefined()
    expect(door(k, true)).toBe(v)
  })
})
"""


def test_add_only_a_new_it_before_an_it_each_block_passes(tmp_path):
    new = SEARCH_DOORS.replace("  it.each([", "  it('a new door test', () => {\n    expect(1).toBe(1)\n  })\n  it.each([")
    code, out = addonly(tmp_path / "ok", "src/a.test.ts", SEARCH_DOORS, new)
    assert code == 0 and out.strip() == "INTEGRITY OK", out


def test_add_only_it_each_assertions_still_cannot_drop(tmp_path):
    new = SEARCH_DOORS.replace("    expect(door(k, true)).toBe(v)\n", "").replace("  it.each([", "  it('a new door test', () => {\n    expect(1).toBe(1)\n  })\n  it.each([")
    ao_fail(tmp_path / "bad", "src/a.test.ts", SEARCH_DOORS, new, "block search server door compatibility %s: assertions dropped from 4 to 3")


@pytest.mark.parametrize("head", [
    "it.each([[1]])('n', (x) => {", "test.each([[1]])('n', (x) => {", "describe.each([[1]])('n', (x) => {", "it.concurrent('n', () => {",
    "test.concurrent('n', () => {", "it.skipIf(win)('n', () => {", "it.runIf(ci)('n', () => {", "it.concurrent.each([[1]])('n', (x) => {",
    "it.each`\n a\n ${1}\n`('n', (x) => {", "it.each([\n  [1],\n  ['it(\"x\")'],\n])(\n  'n',\n  (x) => {",
])
def test_add_only_modified_and_parameterised_forms_are_blocks(tmp_path, head):
    old = head + "\n  expect(f()).toBe(1)\n})\nit('after', () => {\n  expect(g()).toBe(2)\n})\n"
    ao_fail(tmp_path / "gone", "src/a.test.ts", old, old.replace(head + "\n  expect(f()).toBe(1)\n})\n", ""), "block n: test block removed or renamed")
    new = "it('first', () => { expect(0).toBe(0) })\n" + old
    assert addonly(tmp_path / "ok", "src/a.test.ts", old, new)[0] == 0
    ao_fail(tmp_path / "weak", "src/a.test.ts", old, old.replace("expect(f()).toBe(1)", "f()"), "block n: assertions dropped from 1 to 0")


# ---- plan-listed renames and removals (testChanges) ----
def addonly_tc(tmp_path, path, old, new, tc, allow=None, at_head=False):
    """Like addonly, with `testChanges` on T1 in the plan at --approved (or, at_head, added to the plan only after the approved commit)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    t1 = {**AO_PLAN["milestones"][0]["tasks"][0]}
    if allow is not None:
        t1["allowTestEdits"] = allow
    plan = {**AO_PLAN, "milestones": [{**AO_PLAN["milestones"][0], "tasks": [{**t1, **({} if at_head else {"testChanges": tc})}, AO_PLAN["milestones"][0]["tasks"][1]]}, AO_PLAN["milestones"][1]]}
    repo = plan_repo(tmp_path, plan)
    commit(repo, {path: old}, "existing test")
    ms = head(repo)
    git(repo, "switch", "-qc", "t1")
    edits = {path: new}
    if at_head:
        edits[PLAN_PATH] = plan_text({**plan, "milestones": [{**plan["milestones"][0], "tasks": [{**t1, "testChanges": tc}, plan["milestones"][0]["tasks"][1]]}, plan["milestones"][1]]})
    commit(repo, edits)
    return run(repo, ms, str(repo / PLAN_PATH), "--task", "T1", "--approved", appr(repo))


RENAME = {"file": "src/a.test.ts", "block": "lists", "to": "lists the rows", "why": "req-3 changed the title"}
REMOVE = {"file": "src/a.test.ts", "block": "lists", "remove": True, "why": "owner dropped the list view"}


def test_test_changes_a_listed_rename_passes_when_the_counts_hold(tmp_path):
    code, out = addonly_tc(tmp_path, "src/a.test.ts", JS_OLD, JS_OLD.replace("it('lists'", "it('lists the rows'"), [RENAME])
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    spaced = {**RENAME, "block": "  lists ", "to": "lists   the rows"}  # the plan names are normalised like the gate's
    code, out = addonly_tc(tmp_path / "n", "src/a.test.ts", JS_OLD, JS_OLD.replace("it('lists'", "it('lists the  rows'"), [spaced])
    assert code == 0, out


def test_test_changes_a_listed_rename_still_compares_the_counts(tmp_path):
    weaker = JS_OLD.replace("it('lists'", "it('lists the rows'").replace("expect(list()).toHaveLength(2)", "list()")
    code, out = addonly_tc(tmp_path / "a", "src/a.test.ts", JS_OLD, weaker, [RENAME])
    assert code == 1 and "block lists the rows: assertions dropped from 1 to 0" not in out and "block lists: assertions dropped from 1 to 0" in out, out
    skipped = JS_OLD.replace("it('lists'", "it.skip('lists the rows'")
    code, out = addonly_tc(tmp_path / "b", "src/a.test.ts", JS_OLD, skipped, [RENAME])
    assert code == 1 and "skip or focus marker added" in out, out
    slower = JS_OLD.replace("it('lists'", "it('lists the rows'").replace("5000", "9000")
    code, out = addonly_tc(tmp_path / "c", "src/a.test.ts", JS_OLD, slower, [RENAME])
    assert code == 1 and "timeout raised from 5000 to 9000" in out, out


def test_test_changes_only_the_listed_rename_passes(tmp_path):
    code, out = addonly_tc(tmp_path / "a", "src/a.test.ts", JS_OLD, JS_OLD.replace("it('lists'", "it('lists them'"), [RENAME])
    assert code == 1 and "block lists: test block removed or renamed" in out, out
    code, out = addonly_tc(tmp_path / "b", "src/a.test.ts", JS_OLD, JS_OLD.replace("it('lists'", "it('lists the rows'").replace("it('adds'", "it('sums'"), [RENAME])
    assert code == 1 and "block adds: test block removed or renamed" in out and "block lists:" not in out, out
    code, out = addonly_tc(tmp_path / "c", "src/a.test.ts", JS_OLD, JS_OLD.replace("it('lists'", "it('adds'"), [{**RENAME, "to": "adds"}])
    assert code == 1 and "rename target adds already exists" in out, out


def test_test_changes_a_listed_removal_lets_that_block_go(tmp_path):
    gone = JS_OLD.split("  it('lists'")[0] + "})\n"
    code, out = addonly_tc(tmp_path / "a", "src/a.test.ts", JS_OLD, gone, [REMOVE])
    assert code == 0 and out.strip() == "INTEGRITY OK", out
    code, out = addonly_tc(tmp_path / "b", "src/a.test.ts", JS_OLD, "describe('x', () => {\n})\n", [REMOVE])
    assert code == 1 and "block adds: test block removed or renamed" in out and "block lists:" not in out, out
    kept = JS_OLD.replace("expect(list()).toHaveLength(2)", "list()")  # a listed removal that stays is compared as usual
    code, out = addonly_tc(tmp_path / "c", "src/a.test.ts", JS_OLD, kept, [REMOVE])
    assert code == 1 and "block lists: assertions dropped from 1 to 0" in out, out


def test_test_changes_are_ignored_for_a_file_outside_allow_test_edits(tmp_path):
    other = {**RENAME, "file": "src/b.test.ts"}
    code, out = addonly_tc(tmp_path / "a", "src/a.test.ts", JS_OLD, JS_OLD.replace("it('lists'", "it('lists the rows'"), [other])
    assert code == 1 and "block lists: test block removed or renamed" in out, out
    code, out = addonly_tc(tmp_path / "b", "src/a.test.ts", JS_OLD, JS_OLD.replace("it('lists'", "it('lists the rows'"), [RENAME], allow=["src/b.test.ts"])
    assert code == 1, out  # the file is not editable at all


def test_test_changes_are_read_from_the_approved_plan_only(tmp_path):
    code, out = addonly_tc(tmp_path, "src/a.test.ts", JS_OLD, JS_OLD.replace("it('lists'", "it('lists the rows'"), [RENAME], at_head=True)
    assert code == 1 and "block lists: test block removed or renamed" in out, out
