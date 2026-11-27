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


def test_repo_folder_moves_and_every_mention_is_rewritten(tmp_path):
    repo(tmp_path, {".cfactory/check-plan.py": "keep cfactory here", "changes/a/plan.md": OLD_PLAN,
                    "changes/a/notes.md": "see ~/.cfactory/scenarios and .cfactory/goal-brief.py\n",
                    "tests/sdlc.test.ts": "x.includes('```json cfactory') && process.env.CFACTORY_EVAL\n",
                    "CLAUDE.md": "Run /factory:run; scripts live in .cfactory/.\n", "docs/mycfactory.md": "mycfactory stays\n"})
    (tmp_path / "logo.bin").write_bytes(b"\xff\xfecfactory\x00")
    git(tmp_path, "add", "logo.bin")
    git(tmp_path, "commit", "-q", "-m", "bin")
    code, out = migrate(tmp_path)
    assert code == 0
    assert "moved .cfactory -> .factory" in out and "rewrote 1 mention in changes/a/plan.md" in out
    assert "rewrote 2 mentions in tests/sdlc.test.ts" in out and "CLAUDE.md" in out
    assert (tmp_path / ".factory/check-plan.py").exists() and not (tmp_path / ".cfactory").exists()
    assert "```json factory\n" in (tmp_path / "changes/a/plan.md").read_text()
    assert (tmp_path / "changes/a/notes.md").read_text() == "see ~/.factory/scenarios and .factory/goal-brief.py\n"
    assert (tmp_path / "tests/sdlc.test.ts").read_text() == "x.includes('```json factory') && process.env.FACTORY_EVAL\n"
    assert (tmp_path / "docs/mycfactory.md").read_text() == "mycfactory stays\n"  # part of a longer word: not the name
    assert (tmp_path / ".factory/check-plan.py").read_text() == "keep cfactory here"  # the script copy is resynced, not edited
    assert (tmp_path / "logo.bin").read_bytes() == b"\xff\xfecfactory\x00"  # binary left alone
    assert git(tmp_path, "log", "--oneline").count("\n") == 1  # commits nothing (two commits from the fixture)
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
