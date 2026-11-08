"""pr-gate.sh: one PR per milestone, one push per milestone close. Each case is a PR or push a
real run opened on 2026-11-01 (records/*, fix/*, chore/merge-main-into-*) or the one it should
have opened instead."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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
    for name in ("pr-gate.sh", "sdlc-config.sh"):
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


def _pass(repo: Path, sha: str | None = None) -> None:
    verify = repo / "changes" / ID / "verify"
    verify.mkdir(exist_ok=True)
    sha = sha or _git(repo, "rev-parse", "HEAD")
    (verify / "report.json").write_text(
        json.dumps({"sha": sha, "result": f"VERIFY PASS milestone {ID} {sha}"})
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
