import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "migrate-name.py"
OLD_PLAN = "# Plan\n\n```json cfactory\n{}\n```\n\n## Log\n"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def repo(tmp_path, files):
    git(tmp_path, "init", "-q")
    for name, text in files.items():
        f = tmp_path / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "x")


def migrate(*args, home=None):
    env = {**os.environ, **({"HOME": str(home)} if home else {})}
    p = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, env=env)
    return p.returncode, p.stdout


def test_repo_folder_moves_and_plan_fences_are_rewritten(tmp_path):
    repo(tmp_path, {".cfactory/check-plan.py": "x", "changes/a/plan.md": OLD_PLAN, "changes/a/plan-2.md": OLD_PLAN,
                    "changes/a/notes.md": OLD_PLAN, "docs/plan.md": OLD_PLAN})
    code, out = migrate(tmp_path)
    assert code == 0
    assert "moved .cfactory -> .factory" in out and "rewrote the plan fence in changes/a/plan.md" in out and "changes/a/plan-2.md" in out
    assert (tmp_path / ".factory/check-plan.py").exists() and not (tmp_path / ".cfactory").exists()
    assert "```json factory\n" in (tmp_path / "changes/a/plan.md").read_text()
    assert "cfactory" in (tmp_path / "changes/a/notes.md").read_text() and "cfactory" in (tmp_path / "docs/plan.md").read_text()
    assert git(tmp_path, "log", "--oneline").count("\n") == 0  # commits nothing
    assert migrate(tmp_path) == (0, "nothing to change\n")  # a second run changes nothing


def test_repo_refuses_when_factory_folder_exists(tmp_path):
    repo(tmp_path, {".cfactory/a": "x", ".factory/b": "y"})
    code, out = migrate(tmp_path)
    assert code == 1 and ".factory already exists" in out and (tmp_path / ".cfactory/a").exists()


def test_home_moves_and_refuses_when_target_exists(tmp_path):
    (tmp_path / ".cfactory/scenarios").mkdir(parents=True)
    code, out = migrate("--home", home=tmp_path)
    assert code == 0 and "moved ~/.cfactory -> ~/.factory" in out
    assert (tmp_path / ".factory/scenarios").exists() and not (tmp_path / ".cfactory").exists()
    (tmp_path / ".cfactory").mkdir()
    code, out = migrate("--home", home=tmp_path)
    assert code == 1 and "~/.factory already exists" in out and (tmp_path / ".cfactory").exists()


def test_home_without_old_folder_is_a_no_op(tmp_path):
    assert migrate("--home", home=tmp_path) == (0, "no ~/.cfactory: nothing to move\n")
