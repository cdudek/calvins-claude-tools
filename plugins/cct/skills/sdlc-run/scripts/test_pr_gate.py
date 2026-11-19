"""pr-gate.sh: one PR per milestone, one push per milestone close. Each case is a PR or push a
real run opened on 2026-11-01 (records/*, fix/*, chore/merge-main-into-*) or the one it should
have opened instead."""

from __future__ import annotations

import json
import re
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "templates" / "hooks"
ID = "2026-11-01-trial"
ACTIVE = [{"type": "attachment", "attachment": {"type": "goal_status", "met": False}}]


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo, check=True, env=_env(), capture_output=True, text=True,
    ).stdout.strip()  # fmt: skip


def _commit(repo: Path, path: str, text: str) -> str:
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", path)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "master", str(origin))
    repo = tmp_path / "repo"
    (repo / ".claude" / "hooks").mkdir(parents=True)
    for name in ("pr-gate.sh", "sdlc-config.sh", "goal_active.py", "block_state.py", "pass_proof.py"):
        if (HOOKS / name).exists():  # the helpers sit beside the hook; absent in older trees
            shutil.copy(HOOKS / name, repo / ".claude" / "hooks" / name)
    (repo / "sdlc.json").write_text(
        json.dumps({"defaultBranch": "master", "changesDir": "changes"})
    )
    (repo / ".gitignore").write_text("/changes/*/verify/\n")
    change = repo / "changes" / ID
    change.mkdir(parents=True)
    (change / "decisions.json").write_text(json.dumps({"milestone": {"slug": "trial"}}))
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "remote", "add", "origin", str(origin))
    _commit(repo, "src/app.ts", "1\n")
    _git(repo, "push", "-q", "origin", "master")
    _git(repo, "checkout", "-qb", "milestone/trial-1")
    _commit(repo, "src/app.ts", "2\n")
    return repo


def _pass(
    repo: Path, sha: str | None = None, milestone: int | None = None, owner: str | None = None, change: str = ID
) -> None:
    """The report the gate writes: it names the change, the milestone number and the owning project."""
    verify = repo / "changes" / ID / "verify"
    verify.mkdir(exist_ok=True)
    sha = sha or _git(repo, "rev-parse", "HEAD")
    if milestone is None:  # the number the current branch is
        found = re.search(r"-(\d+)$", _git(repo, "rev-parse", "--abbrev-ref", "HEAD"))
        milestone = int(found[1]) if found else 1
    if owner is None:  # the owner the change record names now, as the gate reads it
        project = json.loads((repo / "changes" / ID / "decisions.json").read_text()).get("project") or {}
        owner = f"project/{project['slug']}" if project.get("slug") and project.get("branch", True) else ""
    (verify / "report.json").write_text(
        json.dumps(
            {
                "scope": "milestone", "sha": sha, "result": f"VERIFY PASS milestone {change} {sha}",
                "change": change, "milestone": milestone, "owner": owner,
            }  # fmt: skip
        )
    )


def _run(repo: Path, command: str, goal: bool = False) -> subprocess.CompletedProcess[str]:
    transcript = repo.parent / "t.jsonl"
    transcript.write_text("".join(json.dumps(e) + "\n" for e in (ACTIVE if goal else [])))
    payload = {
        "tool_input": {"command": command},
        "cwd": str(repo),
        "transcript_path": str(transcript),
    }
    return subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / "pr-gate.sh")],
        input=json.dumps(payload), capture_output=True, text=True,
        env={**_env(), "CLAUDE_PROJECT_DIR": str(repo)},
    )  # fmt: skip


@pytest.mark.parametrize(
    "head", ["records/m3-close", "fix/kit-follow-up", "chore/merge-main-into-x"]
)
def test_interior_pr_from_anything_but_a_milestone_is_refused(repo: Path, head: str) -> None:
    r = _run(repo, f"gh pr create --base project/trial --head {head} --title t --body b")
    assert r.returncode == 2 and "only milestone branches" in r.stderr


def test_milestone_pr_needs_the_gate_on_its_head(repo: Path) -> None:
    cmd = "gh pr create --base project/trial --title 'Milestone 1' --body x"
    assert _run(repo, cmd).returncode == 2
    _pass(repo)
    assert _run(repo, cmd).returncode == 0


def test_records_after_the_gate_ride_along_but_code_does_not(repo: Path) -> None:
    _pass(repo)
    _commit(repo, f"changes/{ID}/milestone.md", "gate line\n")
    assert _run(repo, "git push -u origin milestone/trial-1").returncode == 0
    _commit(repo, "src/app.ts", "3\n")
    r = _run(repo, "git push -u origin milestone/trial-1")
    assert r.returncode == 2 and "without a passing milestone gate" in r.stderr


def test_milestone_push_without_the_gate_is_refused_with_or_without_goal(repo: Path) -> None:
    assert _run(repo, "git push origin HEAD").returncode == 2
    assert _run(repo, "rtk git push", goal=True).returncode == 2


def test_other_branches_push_only_outside_a_goal(repo: Path) -> None:
    _git(repo, "checkout", "-qb", "fix/thing")
    assert _run(repo, "git push -u origin fix/thing").returncode == 0
    r = _run(repo, "git push -u origin fix/thing", goal=True)
    assert r.returncode == 2 and "inside a /goal run" in r.stderr


def test_pr_into_the_default_branch_is_the_engineers_ask_outside_a_goal(repo: Path) -> None:
    _git(repo, "checkout", "-qb", "docs/pricing")
    assert _run(repo, "gh pr create --title t --body b").returncode == 0
    assert _run(repo, "gh pr create --title t --body b", goal=True).returncode == 2


def test_project_branch_is_created_from_the_trunk_and_never_pushed_again(repo: Path) -> None:
    ok = _run(repo, "git push origin origin/master:refs/heads/project/trial")
    assert ok.returncode == 0
    r = _run(repo, "git push --force-with-lease origin milestone/trial-1:project/trial")
    assert r.returncode == 2 and "only through milestone PRs" in r.stderr


def test_the_default_branch_is_never_pushed(repo: Path) -> None:
    assert _run(repo, "git push origin HEAD:master").returncode == 2


def test_tags_and_deletions_pass(repo: Path) -> None:
    assert _run(repo, "git push origin --tags", goal=True).returncode == 0
    assert _run(repo, "git push origin --delete fix/old", goal=True).returncode == 0
    assert _run(repo, "git push origin :fix/old", goal=True).returncode == 0


def test_an_exception_needs_the_engineers_words(repo: Path) -> None:
    decisions = repo / "changes" / ID / "decisions.json"
    cmd = "gh pr create --base project/trial --head fix/urgent --title t --body b"
    data = json.loads(decisions.read_text())
    decisions.write_text(
        json.dumps({**data, "prExceptions": [{"branch": "fix/urgent", "words": ""}]})
    )
    assert _run(repo, cmd).returncode == 2
    rows = [{"branch": "fix/urgent", "words": "ship the kit fix now, I accept the extra run"}]
    decisions.write_text(json.dumps({**data, "prExceptions": rows}))
    assert _run(repo, cmd).returncode == 0


def test_heredoc_body_and_cd_prefix_are_read(repo: Path, tmp_path: Path) -> None:
    body = "gh pr create --base project/trial --head records/x --title t --body \"$(cat <<'EOF'\nIt's done; really.\nEOF\n)\""
    assert _run(repo, body).returncode == 2
    other = tmp_path / "elsewhere"
    other.mkdir()
    assert _run(repo, f"cd {other} && cd {repo} && git push origin HEAD").returncode == 2


def test_a_heredoc_that_only_mentions_push_is_left_alone(repo: Path) -> None:
    cmd = "cat > notes.md <<'EOF'\nWe don't push before the gate.\nEOF"
    assert _run(repo, cmd, goal=True).returncode == 0


def test_feature_prs_delivery_allows_feature_prs_into_the_milestone(repo: Path) -> None:
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "delivery": "feature-prs"}))
    _git(repo, "checkout", "-qb", "feat/trial-login")
    assert _run(repo, "git push -u origin feat/trial-login", goal=True).returncode == 0
    cmd = "gh pr create --base milestone/trial-1 --title t --body b"
    assert _run(repo, cmd, goal=True).returncode == 0


def test_a_repo_without_sdlc_json_gets_no_opinion(repo: Path) -> None:
    (repo / "sdlc.json").unlink()
    assert _run(repo, "gh pr create --base project/trial --head records/x").returncode == 0


def test_a_pass_still_counts_after_the_archive_move(repo: Path) -> None:
    # Stage 7 moves the change into changes/archive/ as the last commit before the push.
    _pass(repo)
    (repo / "changes" / "archive").mkdir()
    _git(repo, "mv", f"changes/{ID}", f"changes/archive/{ID}")
    _git(repo, "commit", "-qm", "archive")
    assert _run(repo, "git push -u origin milestone/trial-1").returncode == 0


# Negative fixtures (3.9.0).
def test_a_gate_pass_for_an_older_head_does_not_open_the_pr(repo: Path) -> None:
    _pass(repo, sha="0" * 40)  # a stale PASS: the head moved after the gate
    cmd = "gh pr create --base project/trial --title 'Milestone 1' --body x"
    assert _run(repo, cmd).returncode == 2


def test_a_failed_gate_line_is_not_a_pass(repo: Path) -> None:
    verify = repo / "changes" / ID / "verify"
    verify.mkdir()
    sha = _git(repo, "rev-parse", "HEAD")
    (verify / "report.json").write_text(
        json.dumps({"sha": sha, "result": f"VERIFY FAIL milestone {ID} check=unit"})
    )
    assert _run(repo, "git push -u origin milestone/trial-1").returncode == 2


def test_force_pushing_the_default_branch_is_refused(repo: Path) -> None:
    _pass(repo)
    assert _run(repo, "git push --force origin milestone/trial-1:master").returncode == 2


# The push gate judges only its own push (F6-F8).
@pytest.mark.parametrize(
    "redirect",
    ["2>&1", "> push.log", ">push.log", "2>> push.log", "2>>push.log", "&>push.log", "&> push.log"],
)
def test_a_redirect_is_not_a_refspec_F6(repo: Path, redirect: str) -> None:
    _pass(repo)
    cmd = f"git push -u origin milestone/trial-1 {redirect}"
    assert _run(repo, cmd, goal=True).returncode == 0
    assert _run(repo, f"git push {redirect} origin milestone/trial-1", goal=True).returncode == 0
    assert _run(repo, f"git push origin HEAD {redirect} | tail -3", goal=True).returncode == 0


@pytest.mark.parametrize("redirect", ["2>&1", ">push.log", "&>push.log"])
def test_a_redirect_does_not_hide_a_refused_push_F6(repo: Path, redirect: str) -> None:
    # no gate pass: still refused, and for the milestone reason
    r = _run(repo, f"git push -u origin milestone/trial-1 {redirect}", goal=True)
    assert r.returncode == 2 and "without a passing milestone gate" in r.stderr
    assert _run(repo, f"git push origin HEAD:master {redirect}").returncode == 2


def _other_repo(tmp_path: Path) -> Path:
    """A second repo with its own sdlc.json, on a plain branch."""
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-q", "-b", "master")
    (other / "sdlc.json").write_text(
        json.dumps({"defaultBranch": "master", "changesDir": "changes"})
    )
    _commit(other, "src/app.ts", "1\n")
    _git(other, "checkout", "-qb", "fix/other")
    return other


def test_the_goal_rule_skips_pushes_in_another_repo_F7(repo: Path, tmp_path: Path) -> None:
    other = _other_repo(tmp_path)
    assert _run(repo, f"cd {other} && git push -u origin fix/other", goal=True).returncode == 0
    assert _run(repo, f"git -C {other} push -u origin fix/other", goal=True).returncode == 0
    pr = _run(repo, f"cd {other} && gh pr create --title t --body b", goal=True)
    assert pr.returncode == 0
    # the session's own repo is still bound by the goal
    _git(repo, "checkout", "-qb", "fix/thing")
    r = _run(repo, "git push -u origin fix/thing", goal=True)
    assert r.returncode == 2 and "inside a /goal run" in r.stderr


def test_other_rules_still_apply_in_another_repo_F7(repo: Path, tmp_path: Path) -> None:
    other = _other_repo(tmp_path)
    r = _run(repo, f"cd {other} && git push origin HEAD:master", goal=True)
    assert r.returncode == 2 and "a push to master" in r.stderr


def test_a_worktree_of_the_start_repo_is_the_start_repo_F7(repo: Path, tmp_path: Path) -> None:
    wt = tmp_path / "wt"
    _git(repo, "worktree", "add", "-q", "-b", "fix/wt", str(wt))
    r = _run(repo, f"cd {wt} && git push -u origin fix/wt", goal=True)
    assert r.returncode == 2 and "inside a /goal run" in r.stderr
    assert _run(repo, f"cd {wt} && git push -u origin fix/wt").returncode == 0  # no goal


def test_an_exception_in_the_start_repo_is_honoured_for_another_repo_F8(
    repo: Path, tmp_path: Path
) -> None:
    other = _other_repo(tmp_path)
    cmd = f"cd {other} && gh pr create --base project/trial --head fix/urgent --title t --body b"
    assert _run(repo, cmd).returncode == 2  # no row anywhere yet
    decisions = repo / "changes" / ID / "decisions.json"
    data = json.loads(decisions.read_text())
    empty = [{"branch": "fix/urgent", "words": ""}]
    decisions.write_text(json.dumps({**data, "prExceptions": empty}))
    assert _run(repo, cmd).returncode == 2  # an empty `words` is no exception
    rows = [{"branch": "fix/urgent", "words": "ship the kit fix now, I accept the extra run"}]
    decisions.write_text(json.dumps({**data, "prExceptions": rows}))
    assert _run(repo, cmd).returncode == 0
    assert _run(repo, cmd.replace("fix/urgent", "fix/else")).returncode == 2  # that branch only


def test_an_exception_in_the_pushed_repo_still_counts_F8(repo: Path, tmp_path: Path) -> None:
    other = _other_repo(tmp_path)
    change = other / "changes" / "2026-11-01-x"
    change.mkdir(parents=True)
    rows = [{"branch": "fix/urgent", "words": "ship it, I accept the extra run"}]
    (change / "decisions.json").write_text(json.dumps({"prExceptions": rows}))
    cmd = f"cd {other} && gh pr create --base project/trial --head fix/urgent --title t --body b"
    assert _run(repo, cmd).returncode == 0


# 3.14.0: sdlc.json `milestones.merge: "local"`. Milestones and the project branch stay on this
# machine; only the PR into the default branch goes online.
def _local(repo: Path, merge: str | None = "local", project: bool = True) -> None:
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg = {**cfg, "milestones": {"merge": merge}} if merge else cfg
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    decisions = repo / "changes" / ID / "decisions.json"
    data = json.loads(decisions.read_text())
    if project:
        data["project"] = {"slug": "trial", "branch": True}
    decisions.write_text(json.dumps(data))
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "local milestones")
    _git(repo, "branch", "project/trial")  # same commit, so it carries the config


def _pass_project(repo: Path, sha: str | None = None) -> None:
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    verify = common / "sdlc" / "projects" / "trial" / "verify"
    verify.mkdir(parents=True, exist_ok=True)
    sha = sha or _git(repo, "rev-parse", "project/trial")
    (verify / "report.json").write_text(
        json.dumps({"sha": sha, "result": f"VERIFY PASS project trial {sha}"})
    )


def test_local_mode_refuses_the_milestone_push_even_with_a_pass(repo: Path) -> None:
    _local(repo)
    _pass(repo)
    r = _run(repo, "git push -u origin milestone/trial-1")
    assert r.returncode == 2 and "local milestones mode" in r.stderr
    assert "git switch project/trial && git merge --no-ff milestone/trial-1" in r.stderr


def test_local_mode_without_a_project_sends_the_milestone_to_the_default_branch(repo: Path) -> None:
    _local(repo, project=False)
    assert _run(repo, "git push -u origin milestone/trial-1").returncode == 2  # no gate yet
    _pass(repo)
    assert _run(repo, "git push -u origin milestone/trial-1").returncode == 0
    assert _run(repo, "gh pr create --base master --title t --body b").returncode == 0


@pytest.mark.parametrize("merge", [None, "pr"])
def test_pr_mode_still_pushes_the_milestone_and_opens_its_pr(repo: Path, merge: str | None) -> None:
    _local(repo, merge)
    _pass(repo)
    assert _run(repo, "git push -u origin milestone/trial-1").returncode == 0
    cmd = "gh pr create --base project/trial --title 'Milestone 1' --body x"
    assert _run(repo, cmd).returncode == 0


def test_local_mode_refuses_the_milestone_pr_into_the_project(repo: Path) -> None:
    _local(repo)
    _pass(repo)
    r = _run(repo, "gh pr create --base project/trial --head milestone/trial-1 --title t --body b")
    assert r.returncode == 2 and "local milestones mode" in r.stderr
    assert "git merge --no-ff milestone/trial-1" in r.stderr


def test_local_mode_pushes_the_project_only_with_its_own_pass(repo: Path) -> None:
    _local(repo)
    _git(repo, "checkout", "-q", "project/trial")
    assert _run(repo, "git push -u origin project/trial").returncode == 2  # never gated
    assert _run(repo, "git push origin origin/master:refs/heads/project/trial").returncode == 2
    _pass(repo)  # a milestone PASS is not a project PASS
    r = _run(repo, "git push -u origin project/trial")
    assert r.returncode == 2 and "VERIFY PASS project" in r.stderr
    _pass_project(repo, sha="0" * 40)  # stale: the head moved after the gate
    assert _run(repo, "git push -u origin project/trial").returncode == 2
    _pass_project(repo)
    assert _run(repo, "git push -u origin project/trial").returncode == 0
    assert _run(repo, "git push origin project/trial:refs/heads/project/trial").returncode == 0


def test_local_project_pass_survives_the_archive_move_but_not_code(repo: Path) -> None:
    _local(repo)
    _git(repo, "checkout", "-q", "project/trial")
    _pass_project(repo)
    (repo / "changes" / "archive").mkdir()
    _git(repo, "mv", f"changes/{ID}", f"changes/archive/{ID}")
    _git(repo, "commit", "-qm", "archive")
    assert _run(repo, "git push -u origin project/trial").returncode == 0
    _commit(repo, "src/app.ts", "late\n")
    assert _run(repo, "git push -u origin project/trial").returncode == 2


def test_local_mode_opens_the_project_pr_into_the_default_branch_only(repo: Path) -> None:
    _local(repo)
    ok = "gh pr create --head project/trial --base master --title t --body b"
    assert _run(repo, ok).returncode == 0
    r = _run(repo, "gh pr create --head project/trial --base other --title t --body b")
    assert r.returncode == 2 and "default branch" in r.stderr


def test_pr_mode_keeps_the_project_branch_rule(repo: Path) -> None:
    _local(repo, None)
    _git(repo, "checkout", "-q", "project/trial")
    _pass_project(repo)  # ignored outside local mode
    r = _run(repo, "git push -u origin project/trial")
    assert r.returncode == 2 and "only through milestone PRs" in r.stderr


def test_local_merge_into_the_project_needs_the_milestone_pass(repo: Path) -> None:
    _local(repo)
    here = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    assert here == "milestone/trial-1"
    _git(repo, "checkout", "-q", "project/trial")
    for cmd in (
        "git merge --no-ff milestone/trial-1",
        "git merge --no-ff -m 'merge m1' milestone/trial-1",
        "rtk git merge refs/heads/milestone/trial-1 --no-edit",
    ):
        r = _run(repo, cmd)
        assert r.returncode == 2 and "without a passing milestone gate" in r.stderr, cmd
    _git(repo, "checkout", "-q", "milestone/trial-1")
    _pass(repo)
    _git(repo, "checkout", "-q", "project/trial")
    assert _run(repo, "git merge --no-ff milestone/trial-1").returncode == 0
    assert _run(repo, "git merge --no-ff -m 'merge m1' milestone/trial-1").returncode == 0


def test_local_merge_sees_a_pass_recorded_in_another_worktree(repo: Path, tmp_path: Path) -> None:
    _local(repo)
    _pass(repo)  # the gate ran here, on milestone/trial-1
    other = tmp_path / "project-wt"
    _git(repo, "worktree", "add", "-q", str(other), "project/trial")
    assert _run_in(other, repo, "git merge --no-ff milestone/trial-1").returncode == 0
    _commit(repo, "src/app.ts", "3\n")  # code after the gate: no longer the gated head
    assert _run_in(other, repo, "git merge --no-ff milestone/trial-1").returncode == 2


def test_local_merge_leaves_other_merges_alone(repo: Path) -> None:
    _local(repo)
    _git(repo, "checkout", "-q", "project/trial")
    assert _run(repo, "git merge origin/master").returncode == 0
    assert _run(repo, "git merge --abort").returncode == 0
    assert _run(repo, "git merge --no-ff -m 'about milestone/x' fix/thing").returncode == 0
    _git(repo, "checkout", "-q", "milestone/trial-1")  # not a project branch
    assert _run(repo, "git merge --no-ff project/trial").returncode == 0


def test_pr_mode_does_not_look_at_merges(repo: Path) -> None:
    _local(repo, None)
    _git(repo, "checkout", "-q", "project/trial")
    assert _run(repo, "git merge --no-ff milestone/trial-1").returncode == 0


def _run_in(where: Path, repo: Path, command: str) -> subprocess.CompletedProcess[str]:
    """Run the hook of `repo` for a command typed in the worktree `where`."""
    transcript = repo.parent / "t.jsonl"
    transcript.write_text("")
    payload = {
        "tool_input": {"command": command},
        "cwd": str(where),
        "transcript_path": str(transcript),
    }
    return subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / "pr-gate.sh")],
        input=json.dumps(payload), capture_output=True, text=True,
        env={**_env(), "CLAUDE_PROJECT_DIR": str(repo)},
    )  # fmt: skip


def test_local_merge_is_read_after_a_switch_in_the_same_command(repo: Path) -> None:
    """The route the hook recommends is `git switch project/x && git merge --no-ff milestone/x`:
    the hook runs before the switch, so it must follow it."""
    _local(repo)  # HEAD stays milestone/trial-1
    for cmd in (
        "git switch project/trial && git merge --no-ff milestone/trial-1",
        "git checkout project/trial; git merge milestone/trial-1",
        f"git -C {repo} switch project/trial && git -C {repo} merge milestone/trial-1",
    ):
        r = _run(repo, cmd)
        assert r.returncode == 2 and "without a passing milestone gate" in r.stderr, cmd
    _pass(repo)
    for cmd in (
        "git switch project/trial && git merge --no-ff milestone/trial-1",
        "git checkout project/trial; git merge milestone/trial-1",
    ):
        assert _run(repo, cmd).returncode == 0, cmd


def test_local_merge_after_a_switch_to_another_branch_is_left_alone(repo: Path) -> None:
    _local(repo)
    assert _run(repo, "git switch -c fix/x && git merge milestone/trial-1").returncode == 0


def test_pr_mode_ignores_a_switch_and_merge(repo: Path) -> None:
    _local(repo, None)
    cmd = "git switch project/trial && git merge --no-ff milestone/trial-1"
    assert _run(repo, cmd).returncode == 0


@pytest.mark.parametrize(
    "cmd",
    [
        "git switch other; git merge milestone/trial-1",
        "git switch other || git merge milestone/trial-1",
        "git switch nonexistent && git merge milestone/trial-1",
    ],
)
def test_a_switch_away_never_hides_the_real_project_branch(repo: Path, cmd: str) -> None:
    _local(repo)
    _git(repo, "checkout", "-q", "project/trial")
    r = _run(repo, cmd)
    assert r.returncode == 2 and "without a passing milestone gate" in r.stderr


def test_local_merge_refuses_a_pass_gated_before_the_project_moved_F6(repo: Path) -> None:
    """Two milestones cut from one project tip: after the first merges, the second's pass is old."""
    _local(repo)
    _git(repo, "checkout", "-q", "-b", "milestone/trial-2", "project/trial")
    _commit(repo, "src/other.ts", "m2\n")
    _pass(repo)  # the gate passed on M2 against the old project tip
    _git(repo, "checkout", "-q", "milestone/trial-1")
    _commit(repo, "src/m1.ts", "m1\n")
    _git(repo, "checkout", "-q", "project/trial")
    _git(repo, "merge", "-q", "--no-ff", "-m", "m1", "milestone/trial-1")
    r = _run(repo, "git merge --no-ff milestone/trial-2")
    assert r.returncode == 2 and "project/trial" in r.stderr and "older" in r.stderr
    _git(repo, "checkout", "-q", "milestone/trial-2")
    _git(repo, "merge", "-q", "project/trial")  # parent-sync, then gate again
    _pass(repo)
    _git(repo, "checkout", "-q", "project/trial")
    assert _run(repo, "git merge --no-ff milestone/trial-2").returncode == 0


def test_local_merge_refuses_another_projects_branch_F6(repo: Path) -> None:
    _local(repo)
    _pass(repo)
    _git(repo, "branch", "project/other", "milestone/trial-1")
    _git(repo, "checkout", "-q", "project/other")
    r = _run(repo, "git merge --no-ff milestone/trial-1")
    assert r.returncode == 2 and "belongs to project/trial" in r.stderr


def test_a_pass_counts_after_a_year_month_archive_move_F10(repo: Path) -> None:
    _pass(repo)
    (repo / "changes" / "archive" / "2026" / "2026-11").mkdir(parents=True)
    _git(repo, "mv", f"changes/{ID}", f"changes/archive/2026/2026-11/{ID}")
    _git(repo, "commit", "-qm", "archive")
    assert _run(repo, "git push -u origin milestone/trial-1").returncode == 0


def _other_change_pass(repo: Path, where: str = "changes/2026-11-02-other") -> None:
    """A passing report of ANOTHER change, gated on this very commit."""
    sha = _git(repo, "rev-parse", "HEAD")
    folder = repo / where
    (folder / "verify").mkdir(parents=True)
    (folder / "decisions.json").write_text(json.dumps({"milestone": {"slug": "other"}}))
    (folder / "verify" / "report.json").write_text(
        json.dumps(
            {
                "scope": "milestone",
                "id": "2026-11-02-other",
                "sha": sha,
                "result": f"VERIFY PASS milestone 2026-11-02-other {sha}",
            }
        )
    )


def test_a_pass_of_another_change_on_the_same_sha_does_not_admit_the_push(repo: Path) -> None:
    _other_change_pass(repo)
    r = _run(repo, "git push -u origin milestone/trial-1")
    assert r.returncode == 2 and "without a passing milestone gate" in r.stderr
    pr = "gh pr create --base project/trial --title t --body x"
    assert _run(repo, pr).returncode == 2
    _pass(repo)  # this change's own pass still admits it
    assert _run(repo, "git push -u origin milestone/trial-1").returncode == 0


def test_a_report_in_an_unsupported_folder_depth_is_not_read(repo: Path) -> None:
    _pass(repo)
    folder = repo / "changes" / ID
    deep = repo / "changes" / "archive" / "a" / "b" / "c" / "d" / ID
    deep.parent.mkdir(parents=True)
    _git(repo, "mv", str(folder), str(deep))
    _git(repo, "commit", "-qm", "archive too deep")
    assert _run(repo, "git push -u origin milestone/trial-1").returncode == 2


def test_local_merge_into_an_unresolvable_project_branch_is_refused(repo: Path) -> None:
    _local(repo, project=False)
    _pass(repo)
    r = _run(repo, "git switch -c project/nowhere && git merge --no-ff milestone/trial-1")
    assert r.returncode == 2 and "project branch" in r.stderr and "project/nowhere" in r.stderr


# 3.20.1: what a pass proves, the merge owner and the PR base (review findings 1, 6, 7, 5, 13).
def _push(repo: Path) -> int:
    return _run(repo, "git push -u origin milestone/trial-1").returncode


@pytest.mark.parametrize(
    "name", ["facts.md", "done.json", "lock.json", "marks.json", "asks/shot.png"]
)
def test_a_locked_input_or_evidence_edited_after_the_gate_voids_the_pass_F6(
    repo: Path, name: str
) -> None:
    _commit(repo, f"changes/{ID}/{name}", "first\n")
    _pass(repo)
    _commit(repo, f"changes/{ID}/milestone.md", "gate line\n")  # a close record rides along
    assert _push(repo) == 0
    _commit(repo, f"changes/{ID}/{name}", "easier\n")
    assert _push(repo) == 2


def _archive(repo: Path, edit: str = "") -> Path:
    """The Stage 7 archive commit: move the change, and `edit` rewrites facts.md while moving."""
    (repo / "changes" / "archive" / "2026" / "2026-11").mkdir(parents=True)
    _git(repo, "mv", f"changes/{ID}", f"changes/archive/2026/2026-11/{ID}")
    facts = repo / "changes" / "archive" / "2026" / "2026-11" / ID / "facts.md"
    if edit:
        facts.write_text(edit)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "archive")
    return facts


def test_an_archive_move_keeps_the_pass_only_while_the_locked_files_keep_their_content_F6(
    repo: Path,
) -> None:
    _commit(repo, f"changes/{ID}/facts.md", "F1 the first\n")
    _pass(repo)
    _archive(repo)
    assert _push(repo) == 0
    (repo / "changes" / "archive" / "2026" / "2026-11" / ID / "facts.md").write_text("F1 easier\n")
    _git(repo, "commit", "-qam", "edit while archiving")
    assert _push(repo) == 2


FACTS = "---\nstatus: approved\n---\nF1 the first\n"


def test_the_archive_commit_may_add_archived_at_to_facts_and_nothing_else_H1(repo: Path) -> None:
    _commit(repo, f"changes/{ID}/facts.md", FACTS)
    _pass(repo)
    _archive(repo, FACTS.replace("status: approved\n", "status: approved\narchived_at: 2026-11-19\n"))
    assert _push(repo) == 0


@pytest.mark.parametrize(
    "edited",
    [
        "---\nstatus: approved\narchived_at: 2026-11-19\n---\nF1 easier\n",  # a fact moved too
        "---\nstatus: draft\narchived_at: 2026-11-19\n---\nF1 the first\n",  # frontmatter moved too
        "---\nstatus: approved\narchived_at: a\narchived_at: b\n---\nF1 the first\n",  # twice
        "---\nstatus: approved\n---\nF1 the first\narchived_at: 2026-11-19\n",  # in the body
    ],
)
def test_the_archive_commit_may_not_edit_facts_beyond_archived_at_H1(
    repo: Path, edited: str
) -> None:
    _commit(repo, f"changes/{ID}/facts.md", FACTS)
    _pass(repo)
    _archive(repo, edited)
    assert _push(repo) == 2


def test_archived_at_added_to_a_live_facts_file_voids_the_pass_H1(repo: Path) -> None:
    _commit(repo, f"changes/{ID}/facts.md", FACTS)
    _pass(repo)
    _commit(repo, f"changes/{ID}/facts.md", FACTS.replace("---\nF1", "archived_at: 1\n---\nF1"))
    assert _push(repo) == 2


def test_the_goal_check_and_the_hook_read_the_same_proof_F6(repo: Path) -> None:
    sys.path.insert(0, str(HOOKS))
    from pass_proof import proves

    _commit(repo, f"changes/{ID}/facts.md", "F1\n")
    gated = _git(repo, "rev-parse", "HEAD")
    records = _commit(repo, f"changes/{ID}/milestone.md", "line\n")
    edited = _commit(repo, f"changes/{ID}/facts.md", "F1 easier\n")
    assert proves(repo, "changes", gated, records) and not proves(repo, "changes", gated, edited)


def test_local_merge_knows_the_owner_from_the_gated_ref_not_the_receiving_checkout_F7(
    repo: Path, tmp_path: Path
) -> None:
    _git(repo, "checkout", "-q", "master")
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "milestones": {"merge": "local"}}))
    _git(repo, "commit", "-qam", "local milestones")
    _git(repo, "branch", "project/other")  # cut before any record named a project
    _git(repo, "checkout", "-q", "milestone/trial-1")
    _git(repo, "merge", "-q", "master")
    decisions = repo / "changes" / ID / "decisions.json"
    decisions.write_text(json.dumps({"milestone": {"slug": "trial"}, "project": {"slug": "trial", "branch": True}}))
    _git(repo, "commit", "-qam", "the milestone names its project")
    _pass(repo)
    other = tmp_path / "other-wt"
    _git(repo, "worktree", "add", "-q", str(other), "project/other")
    r = _run_in(other, repo, "git merge --no-ff milestone/trial-1")
    assert r.returncode == 2 and "belongs to project/trial" in r.stderr


def test_local_merge_refuses_a_milestone_without_one_owner_F7(repo: Path) -> None:
    _local(repo)
    twin = repo / "changes" / "2026-11-02-twin"
    twin.mkdir()
    (twin / "decisions.json").write_text(
        json.dumps({"milestone": {"slug": "trial"}, "project": {"slug": "other", "branch": True}})
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "a second change with the same milestone slug")
    _pass(repo)
    _git(repo, "checkout", "-q", "project/trial")
    r = _run(repo, "git merge --no-ff milestone/trial-1")
    assert r.returncode == 2 and "no single owner" in r.stderr


def test_a_milestone_pr_names_its_project_as_the_base_F1(repo: Path) -> None:
    _local(repo, None)  # PR mode, the change belongs to project/trial
    _pass(repo)
    assert _run(repo, "gh pr create --title t --body x").returncode == 2
    assert _run(repo, "gh pr create --base master --title t --body x").returncode == 2
    assert _run(repo, "gh pr create --base project/trial --title t --body x").returncode == 0


def test_a_hook_run_leaves_a_clean_checkout_clean_F13(repo: Path) -> None:
    _git(repo, "checkout", "-qb", "fix/thing")  # refused inside a goal: loads goal_active + block_state
    transcript = repo.parent / "t.jsonl"
    transcript.write_text("".join(json.dumps(e) + "\n" for e in ACTIVE))
    payload = {
        "tool_input": {"command": "git push -u origin fix/thing"},
        "cwd": str(repo),
        "transcript_path": str(transcript),
    }
    env = {k: v for k, v in _env().items() if k != "PYTHONDONTWRITEBYTECODE"}
    r = subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / "pr-gate.sh")],
        input=json.dumps(payload), capture_output=True, text=True,
        env={**env, "CLAUDE_PROJECT_DIR": str(repo)},
    )  # fmt: skip
    assert r.returncode == 2
    assert _git(repo, "status", "--porcelain") == ""


def test_local_merge_reads_the_owner_at_the_gated_sha_not_the_tip_F7(repo: Path) -> None:
    _local(repo)
    _pass(repo)  # gated while the change belonged to project/trial
    decisions = repo / "changes" / ID / "decisions.json"
    data = json.loads(decisions.read_text())
    decisions.write_text(json.dumps({**data, "project": {"slug": "other", "branch": True}}))
    _git(repo, "commit", "-qam", "the change moves to another project")  # a record: the pass holds
    _git(repo, "branch", "project/other", "project/trial")
    _git(repo, "checkout", "-q", "project/other")
    r = _run(repo, "git merge --no-ff milestone/trial-1")
    assert r.returncode == 2 and "belongs to project/trial" in r.stderr


def test_a_pr_create_naming_the_same_repo_is_still_gated_F1(repo: Path) -> None:
    _local(repo, None)
    _git(repo, "remote", "add", "gh", "git@github.com:acme/trial.git")
    cmd = "gh pr create --repo {} --base project/trial --title t --body x"
    for name in ("acme/trial", "github.com/acme/trial", "https://github.com/acme/trial.git"):
        r = _run(repo, cmd.format(name))
        assert r.returncode == 2 and "without a passing milestone gate" in r.stderr, name
    assert _run(repo, cmd.format("acme/elsewhere")).returncode == 0  # another repo: not ours to read
    _pass(repo)
    assert _run(repo, cmd.format("acme/trial")).returncode == 0
    wrong = "gh pr create --repo acme/trial --base master --title t --body x"
    assert _run(repo, wrong).returncode == 2


@pytest.mark.parametrize("value", ["not-a-date", "2026-13-45", "'2026-11-19'", "2026-1-9", "2026-11-19T10:00:00"])
def test_the_archive_commit_voids_the_pass_unless_archived_at_is_a_real_date_C8(
    repo: Path, value: str
) -> None:
    _commit(repo, f"changes/{ID}/facts.md", FACTS)
    _pass(repo)
    _archive(repo, FACTS.replace("status: approved\n", f"status: approved\narchived_at: {value}\n"))
    assert _push(repo) == 2


def test_the_hook_reads_each_change_record_once_per_command_M1(repo: Path, tmp_path: Path) -> None:
    log = tmp_path / "git.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    real = shutil.which("git")
    (bin_dir / "git").write_text(f'#!/bin/sh\necho "$@" >> {log}\nexec {real} "$@"\n')
    (bin_dir / "git").chmod(0o755)
    _pass(repo)
    transcript = repo.parent / "t.jsonl"
    transcript.write_text("")
    payload = {"tool_input": {"command": "git push -u origin milestone/trial-1"}, "cwd": str(repo), "transcript_path": str(transcript)}
    r = subprocess.run(
        ["bash", str(repo / ".claude" / "hooks" / "pr-gate.sh")], input=json.dumps(payload), capture_output=True, text=True,
        env={**_env(), "CLAUDE_PROJECT_DIR": str(repo), "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"},
    )  # fmt: skip
    assert r.returncode == 0, r.stderr
    shows = [line for line in log.read_text().splitlines() if " show " in line and "decisions.json" in line]
    assert len(shows) == len(set(shows)), shows  # no record read twice


def test_a_receipt_file_in_the_git_dir_admits_nothing_3_20_5(repo: Path) -> None:
    """Pass records were withdrawn: the hook reads the gate's report in the checkout only."""
    sha = _git(repo, "rev-parse", "HEAD")
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    out = common / "sdlc" / "receipts" / ID
    out.mkdir(parents=True)
    record = {"scope": "milestone", "milestone": 1, "change": ID, "sha": sha, "verdict": "pass", "owner": ""}
    (out / "milestone-1.json").write_text(json.dumps({**record, "result": f"VERIFY PASS milestone {ID} {sha}"}))
    (out / "garbage.json").write_text("not json")
    assert _push(repo) == 2
    _pass(repo)
    assert _push(repo) == 0


# 3.20.5: the report binds a pass to its change, milestone number and owning project.
def test_m1s_pass_does_not_admit_milestone_2_push(repo: Path) -> None:
    _git(repo, "checkout", "-q", "-b", "milestone/trial-2")
    _pass(repo, milestone=1)  # gated as M1
    r = _run(repo, "git push -u origin milestone/trial-2")
    assert r.returncode == 2 and "without a passing milestone gate" in r.stderr
    _pass(repo)  # gated as M2
    assert _run(repo, "git push -u origin milestone/trial-2").returncode == 0


def test_a_report_without_change_and_milestone_is_no_pass_for_a_numbered_milestone(repo: Path) -> None:
    _pass(repo)
    path = repo / "changes" / ID / "verify" / "report.json"
    full = json.loads(path.read_text())
    assert _push(repo) == 0
    for dropped in ("milestone", "change"):
        path.write_text(json.dumps({k: v for k, v in full.items() if k != dropped}))
        assert _push(repo) == 2, dropped


def test_the_unnumbered_branch_is_milestone_1_and_the_prefix_is_the_configured_one(repo: Path) -> None:
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "milestones": {"branchPrefix": "ms/"}}))
    _git(repo, "commit", "-qam", "prefix")
    _git(repo, "checkout", "-q", "-b", "ms/trial")
    _pass(repo, milestone=1)
    assert _run(repo, "git push -u origin ms/trial").returncode == 0
    _git(repo, "checkout", "-q", "-b", "ms/trial-2")
    assert _run(repo, "git push -u origin ms/trial-2").returncode == 2  # the report says M1


def test_a_pass_gated_for_another_project_is_refused_on_push_pr_and_merge(repo: Path) -> None:
    _local(repo, None)  # PR mode; the change belongs to project/trial
    _pass(repo, owner="project/elsewhere")
    assert _push(repo) == 2
    r = _run(repo, "gh pr create --base project/trial --title t --body x")
    assert r.returncode == 2 and "without a passing milestone gate" in r.stderr
    _pass(repo)
    assert _push(repo) == 0


def test_a_local_merge_refuses_a_pass_whose_report_names_another_project(repo: Path) -> None:
    _local(repo)
    _pass(repo, owner="project/elsewhere")
    _git(repo, "checkout", "-q", "project/trial")
    r = _run(repo, "git merge --no-ff milestone/trial-1")
    assert r.returncode == 2 and "gated for another project" in r.stderr
    _git(repo, "checkout", "-q", "milestone/trial-1")
    _pass(repo)
    _git(repo, "checkout", "-q", "project/trial")
    assert _run(repo, "git merge --no-ff milestone/trial-1").returncode == 0
