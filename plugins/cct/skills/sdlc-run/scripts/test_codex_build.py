"""codex-build.sh: the Codex builder wrapper, with a fake codex on PATH and a real worktree."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "codex-build.sh"

# A fake `codex`: `login status` succeeds unless NO_LOGIN is set; `exec` records its argv and
# stdin, runs $FAKE_WORK in the worktree (-C) and writes $FAKE_RESULT to the -o file.
FAKE_CODEX = r"""#!/usr/bin/env bash
set -u
if [ "${1:-}" = "login" ]; then [ -n "${NO_LOGIN:-}" ] && exit 1; exit 0; fi
printf '%s\n' "$@" > "$FAKE_DIR/argv"
cat > "$FAKE_DIR/stdin"
out=""; wt=""
while [ $# -gt 0 ]; do
  case "$1" in -o) out="$2"; shift 2;; -C) wt="$2"; shift 2;; *) shift;; esac
done
[ -n "${FAKE_EXIT:-}" ] && exit "$FAKE_EXIT"
if [ -n "${FAKE_WORK:-}" ]; then (cd "$wt" && eval "$FAKE_WORK"); fi
printf '%s' "${FAKE_RESULT:-}" > "$out"
exit 0
"""

DONE = json.dumps(
    {
        "status": "done",
        "title": "feat: hello file",
        "files": ["hello.txt"],
        "tests": ["none"],
        "blockers": [],
        "summary": "hello.txt says hi",
    }
)
WRITE_HELLO = "echo hi > hello.txt"


def _env(tmp_path: Path, **extra: str) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / "codex").write_text(FAKE_CODEX)
    (bin_dir / "codex").chmod(0o755)
    fake_dir = tmp_path / "fake"
    fake_dir.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "FAKE_", "NO_LOGIN"))}
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"
    env["FAKE_DIR"] = str(fake_dir)
    env["HOME"] = str(tmp_path)  # no global git identity: the wrapper's fallback shows
    env["XDG_CONFIG_HOME"] = str(tmp_path)
    env["TMPDIR"] = str(tmp_path / "tmp")
    (tmp_path / "tmp").mkdir(exist_ok=True)
    env.update(extra)
    return env


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo_with_worktree(tmp_path: Path, name: str = "wt") -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    (repo / "README.md").write_text("x\n")
    (repo / "sdlc.json").write_text(
        json.dumps({"changesDir": "changes", "protected": ["e2e/baselines/**"]})
    )
    (repo / "changes" / "c1").mkdir(parents=True)
    (repo / "changes" / "c1" / "facts.md").write_text("facts\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "init")
    wt = tmp_path / name
    _git(repo, "worktree", "add", "-q", "-b", "feat", str(wt))
    return repo, wt


def _run(
    tmp_path: Path, wt: Path, env: dict[str, str], brief: str = "build hello"
) -> subprocess.CompletedProcess[str]:
    brief_file = tmp_path / "brief.md"
    brief_file.write_text(brief)
    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--worktree",
            str(wt),
            "--change",
            "c1",
            "--brief",
            str(brief_file),
            "--model",
            "gpt-test",
            "--reasoning",
            "high",
            "--out",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
        env=env,
    )


def _rows(out: str) -> dict[str, str]:
    return dict(re.findall(r"^- (\w+): (.*)$", out, re.M))


def test_done_run_is_committed_by_the_wrapper_and_recorded(tmp_path: Path) -> None:
    _, wt = _repo_with_worktree(tmp_path)
    base = _git(wt, "rev-parse", "HEAD")
    env = _env(tmp_path, FAKE_WORK=WRITE_HELLO, FAKE_RESULT=DONE)
    res = _run(tmp_path, wt, env, brief="make hello.txt say hi")
    rows = _rows(res.stdout)
    assert res.returncode == 0, res.stdout + res.stderr
    head = _git(wt, "rev-parse", "HEAD")
    assert rows["status"] == "done" and rows["commit"] == head and head != base
    assert rows["files"].startswith("1 files")
    assert _git(wt, "log", "-1", "--format=%s|%an") == "feat: hello file|codex-build"
    assert "hello.txt says hi" in _git(wt, "log", "-1", "--format=%b")
    assert _git(wt, "status", "--porcelain") == ""

    argv = (tmp_path / "fake" / "argv").read_text().splitlines()
    assert argv[0] == "exec"
    assert argv[argv.index("--sandbox") + 1] == "workspace-write"
    assert argv[argv.index("-C") + 1] == str(wt)
    assert "--add-dir" not in argv  # .git stays read-only for Codex: the wrapper commits
    assert "model=gpt-test" in argv and "model_reasoning_effort=high" in argv
    assert "--ephemeral" in argv and argv[-1] == "-"
    assert not any("network" in a for a in argv)

    prompt = (tmp_path / "fake" / "stdin").read_text()
    assert "## Never edit" in prompt and "make hello.txt say hi" in prompt
    assert "The wrapper commits" in prompt and base in prompt
    assert "---" not in prompt.split("## What to do")[0]  # frontmatter dropped

    run = json.loads((tmp_path / "out" / "run.json").read_text())
    assert run["model"] == "gpt-test" and run["reasoning"] == "high"
    assert run["branch"] == "feat" and run["base"] == base and run["pid"] > 0
    git_dir = Path(_git(wt, "rev-parse", "--path-format=absolute", "--git-dir"))
    assert not (git_dir / "codex-build.lock").exists()


def test_configured_identity_is_kept(tmp_path: Path) -> None:
    _, wt = _repo_with_worktree(tmp_path)
    _git(wt, "config", "user.name", "Alice")
    _git(wt, "config", "user.email", "alice@example.com")
    res = _run(tmp_path, wt, _env(tmp_path, FAKE_WORK=WRITE_HELLO, FAKE_RESULT=DONE))
    assert res.returncode == 0, res.stdout
    assert _git(wt, "log", "-1", "--format=%an") == "Alice"


def test_codex_failure_and_bad_results_are_errors(tmp_path: Path) -> None:
    _, wt = _repo_with_worktree(tmp_path)
    res = _run(tmp_path, wt, _env(tmp_path, FAKE_EXIT="1"))
    assert res.returncode == 1 and _rows(res.stdout)["status"] == "error"
    assert "codex exec failed" in _rows(res.stdout)["reason"]

    res = _run(tmp_path, wt, _env(tmp_path, FAKE_RESULT=""))
    assert res.returncode == 1 and "no result" in _rows(res.stdout)["reason"]

    res = _run(tmp_path, wt, _env(tmp_path, FAKE_RESULT='{"status": "done"}'))
    assert res.returncode == 1 and "misses or mistypes" in _rows(res.stdout)["reason"]


def test_missing_codex_or_login_is_a_prerequisite_failure(tmp_path: Path) -> None:
    _, wt = _repo_with_worktree(tmp_path)
    env = _env(tmp_path)
    env["PATH"] = "/usr/bin:/bin"
    res = _run(tmp_path, wt, env)
    assert res.returncode == 2 and "codex login" in _rows(res.stdout)["reason"]

    res = _run(tmp_path, wt, _env(tmp_path, NO_LOGIN="1"))
    assert res.returncode == 2 and "not signed in" in _rows(res.stdout)["reason"]


def test_blocked_report_is_passed_through_and_nothing_is_committed(tmp_path: Path) -> None:
    _, wt = _repo_with_worktree(tmp_path)
    base = _git(wt, "rev-parse", "HEAD")
    blocked = json.loads(DONE) | {
        "status": "blocked",
        "blockers": ["needs the engineer's words on X"],
    }
    env = _env(tmp_path, FAKE_WORK=WRITE_HELLO, FAKE_RESULT=json.dumps(blocked))
    res = _run(tmp_path, wt, env)
    assert res.returncode == 4
    rows = _rows(res.stdout)
    assert rows["status"] == "blocked" and "engineer's words on X" in rows["reason"]
    assert _git(wt, "rev-parse", "HEAD") == base and (wt / "hello.txt").exists()


def test_done_with_an_unchanged_tree_is_rejected(tmp_path: Path) -> None:
    _, wt = _repo_with_worktree(tmp_path)
    res = _run(tmp_path, wt, _env(tmp_path, FAKE_RESULT=DONE))
    assert res.returncode == 3, res.stdout
    rows = _rows(res.stdout)
    assert rows["status"] == "rejected" and "unchanged" in rows["reason"]


@pytest.mark.parametrize(
    "path",
    [
        "changes/c1/facts.md",
        "sdlc.json",
        "e2e/baselines/home.png",
        "pnpm-lock.yaml",
        "pkg/package.json",
    ],
)
def test_protected_paths_are_rejected_and_left_uncommitted(tmp_path: Path, path: str) -> None:
    _, wt = _repo_with_worktree(tmp_path)
    base = _git(wt, "rev-parse", "HEAD")
    work = f"mkdir -p \"$(dirname '{path}')\" && echo x >> '{path}' && echo hi > hello.txt"
    res = _run(tmp_path, wt, _env(tmp_path, FAKE_WORK=work, FAKE_RESULT=DONE))
    assert res.returncode == 3, res.stdout
    rows = _rows(res.stdout)
    assert rows["status"] == "rejected" and path in rows["reason"]
    assert _git(wt, "rev-parse", "HEAD") == base and _git(wt, "status", "--porcelain")


def test_tests_are_protected_while_test_locked(tmp_path: Path) -> None:
    _, wt = _repo_with_worktree(tmp_path)
    (wt / "changes" / "c1" / "decisions.json").write_text(json.dumps({"testLocked": True}))
    _git(wt, "add", "-A")
    _git(wt, "commit", "-qm", "lock")
    work = "mkdir -p tests && echo x > tests/a.test.ts"
    res = _run(tmp_path, wt, _env(tmp_path, FAKE_WORK=work, FAKE_RESULT=DONE))
    assert res.returncode == 3, res.stdout
    assert "tests/a.test.ts" in _rows(res.stdout)["reason"]


def test_worktree_path_with_a_space_works(tmp_path: Path) -> None:
    _, wt = _repo_with_worktree(tmp_path, name="work tree")
    res = _run(tmp_path, wt, _env(tmp_path, FAKE_WORK=WRITE_HELLO, FAKE_RESULT=DONE))
    assert res.returncode == 0, res.stdout + res.stderr
    argv = (tmp_path / "fake" / "argv").read_text().splitlines()
    assert argv[argv.index("-C") + 1] == str(wt)


def test_second_run_on_a_locked_worktree_is_refused(tmp_path: Path) -> None:
    _, wt = _repo_with_worktree(tmp_path)
    git_dir = Path(_git(wt, "rev-parse", "--path-format=absolute", "--git-dir"))
    lock = git_dir / "codex-build.lock"
    lock.write_text(str(os.getpid()))  # a live pid: this test process
    res = _run(tmp_path, wt, _env(tmp_path, FAKE_WORK=WRITE_HELLO, FAKE_RESULT=DONE))
    assert res.returncode == 5 and "another codex build" in _rows(res.stdout)["reason"]
    assert lock.exists()  # not ours to remove
    lock.unlink()


def test_dirty_worktree_at_start_is_refused(tmp_path: Path) -> None:
    _, wt = _repo_with_worktree(tmp_path)
    (wt / "dirty.txt").write_text("x")
    res = _run(tmp_path, wt, _env(tmp_path, FAKE_WORK=WRITE_HELLO, FAKE_RESULT=DONE))
    assert res.returncode == 6 and "not clean" in _rows(res.stdout)["reason"]


def test_usage_without_model_or_reasoning(tmp_path: Path) -> None:
    _, wt = _repo_with_worktree(tmp_path)
    res = subprocess.run(
        ["bash", str(SCRIPT), "--worktree", str(wt), "--change", "c1", "--brief", "x"],
        capture_output=True,
        text=True,
        env=_env(tmp_path),
    )
    assert res.returncode == 6 and "usage:" in res.stderr


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
