import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "migrate-ids.py"


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


def migrate(tmp_path, *extra):
    p = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path), *extra], capture_output=True, text=True)
    return p.returncode, p.stdout


def test_happy_path(tmp_path):
    repo(tmp_path, {
        "specs/2026-12/2026-12-20__guests.md": "---\nid: guests\n---\n- guests/R159: When x, the system shall y.\n",
        "changes/2026-12-01-a/intent.md": "# intent\n- I1: people save\n- C1: no cost\n",
        "changes/2026-12-01-a/delta.md": "### ADDED Requirements\n- guests/R160: z [I1] [C1]\n",
        "changes/2026-12-01-a/plan.md": "Covers guests/R160.\n",
        ".cfactory/check-plan.py": "# guests/R999 stays\n",
        "logo.bin": "x",
    })
    (tmp_path / "logo.bin").write_bytes(b"\xff\xfe guests/R1")
    code, out = migrate(tmp_path)
    assert code == 0 and "MIGRATE OK 4 files changed" in out and "mapped guests/R159 -> req-159" in out, out
    assert "- req-159: When x" in (tmp_path / "specs/2026-12/2026-12-20__guests.md").read_text()
    assert (tmp_path / "changes/2026-12-01-a/intent.md").read_text() == "# intent\n- outcome-1: people save\n- constraint-1: no cost\n"
    assert "- req-160: z [outcome-1] [constraint-1]" in (tmp_path / "changes/2026-12-01-a/delta.md").read_text()
    assert (tmp_path / "changes/2026-12-01-a/plan.md").read_text() == "Covers req-160.\n"
    assert (tmp_path / ".cfactory/check-plan.py").read_text() == "# guests/R999 stays\n"
    assert git(tmp_path, "log", "--oneline").count("\n") == 0  # no commit was made


def test_slug_limits_the_intent_rewrite(tmp_path):
    repo(tmp_path, {"changes/2026-12-01-a/intent.md": "- I1: a\n", "changes/2026-12-02-b/intent.md": "- I1: b\n"})
    code, _ = migrate(tmp_path, "--slug", "2026-12-01-a")
    assert code == 0
    assert (tmp_path / "changes/2026-12-01-a/intent.md").read_text() == "- outcome-1: a\n"
    assert (tmp_path / "changes/2026-12-02-b/intent.md").read_text() == "- I1: b\n"


def test_number_conflict_refuses_and_changes_nothing(tmp_path):
    repo(tmp_path, {"specs/a.md": "- guests/R1: a\n", "specs/b.md": "- saved-searches/R1: b\n", "changes/x/intent.md": "- I1: a\n"})
    code, out = migrate(tmp_path)
    assert code == 1 and "MIGRATE FAIL req-1 would merge guests/R1, saved-searches/R1" in out
    assert (tmp_path / "specs/a.md").read_text() == "- guests/R1: a\n" and (tmp_path / "changes/x/intent.md").read_text() == "- I1: a\n"
