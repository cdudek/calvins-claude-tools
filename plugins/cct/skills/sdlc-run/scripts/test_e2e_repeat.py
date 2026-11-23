"""templates/scripts/e2e-repeat.sh: the safe x3 repeat of changed and flaky E2E specs."""

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "templates" / "scripts" / "e2e-repeat.sh"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, check=True, capture_output=True)


def _repo(tmp_path: Path, flaky: str | None = None) -> Path:
    (tmp_path / "e2e").mkdir()
    (tmp_path / "e2e" / "a.spec.ts").write_text("x")
    if flaky is not None:
        (tmp_path / "e2e" / "flaky-specs.txt").write_text(flaky)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")
    return tmp_path


def _run(repo: Path) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "E2E_REPEAT_RUNNER": "printf RAN:%s\\n"}
    return subprocess.run(["bash", str(SCRIPT), "HEAD"], cwd=repo, capture_output=True, text=True, env=env)


def test_no_specs_exits_zero_and_runs_nothing(tmp_path: Path) -> None:
    r = _run(_repo(tmp_path))
    assert r.returncode == 0 and "RAN" not in r.stdout


def test_comments_and_blanks_are_stripped_and_a_listed_spec_runs_after_dashes(tmp_path: Path) -> None:
    r = _run(_repo(tmp_path, "# flaky\n\n  e2e/a.spec.ts  # still flaky\n"))
    assert r.returncode == 0, r.stderr
    assert "RAN:--repeat-each=3" in r.stdout and "RAN:--" in r.stdout and "RAN:e2e/a.spec.ts" in r.stdout
    assert "--pass-with-no-tests" not in SCRIPT.read_text()


def test_a_stale_path_fails(tmp_path: Path) -> None:
    r = _run(_repo(tmp_path, "e2e/gone.spec.ts\n"))
    assert r.returncode == 1 and "RAN" not in r.stdout


def test_a_path_starting_with_a_dash_fails(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "--ui.spec.ts\n")
    (repo / "--ui.spec.ts").write_text("x")
    r = _run(repo)
    assert r.returncode == 1 and "RAN" not in r.stdout


def test_a_path_with_a_space_fails(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "e2e/a b.spec.ts\n")
    (repo / "e2e" / "a b.spec.ts").write_text("x")
    r = _run(repo)
    assert r.returncode == 1 and "RAN" not in r.stdout


def test_an_unknown_base_fails(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
    r = subprocess.run(["bash", str(SCRIPT), "origin/nope"], cwd=repo, capture_output=True, text=True, env=env)
    assert r.returncode != 0
