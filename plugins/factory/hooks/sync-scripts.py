#!/usr/bin/env python3
"""SessionStart hook: keep <repo>/.factory/ equal to the plugin's own scripts, so the model never reads and rewrites them.
Runs in the session's cwd repo only when it already uses the factory (a `changes/*/plan.md` or a `.factory/` folder).
Copies check-plan.py, goal-brief.py, task-step.py, test-integrity.sh and the kickoff template (as kickoff.md) when their bytes differ,
and prints one line when it changed something. A repo that still has the pre-0.3.0 folder (named in migrate-name.py) is left alone and told the one migration command.
Never fails the session: any error prints nothing and exits 0.
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)
RUN = ROOT / "skills" / "run"
FILES = {"check-plan.py": RUN / "scripts" / "check-plan.py", "goal-brief.py": RUN / "scripts" / "goal-brief.py",
         "task-step.py": RUN / "scripts" / "task-step.py", "test-integrity.sh": RUN / "scripts" / "test-integrity.sh",
         "kickoff.md": RUN / "templates" / "kickoff.md"}


def old_dir():
    """The pre-0.3.0 folder name, owned by the migration script."""
    spec = importlib.util.spec_from_file_location("migrate_name", RUN / "scripts" / "migrate-name.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.OLD_DIR


def toplevel(cwd):
    p = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(p.stdout.strip()) if p.returncode == 0 and p.stdout.strip() else None


def sync(cwd):
    """Returns the message to print, or ''."""
    repo = toplevel(cwd)
    if repo is None:
        return ""
    old = old_dir()
    if (repo / old).exists():
        return (f"factory: this repo still has {old}/. Run once: python3 {RUN / 'scripts' / 'migrate-name.py'} {repo} "
                f"(and with --home for the old home folder), then start a new session.")
    if not (repo / ".factory").is_dir() and not any((repo / "changes").glob("*/plan.md")):
        return ""
    dest = repo / ".factory"
    changed = []
    for name, src in FILES.items():
        data = src.read_bytes()
        target = dest / name
        if not target.exists() or target.read_bytes() != data:
            dest.mkdir(exist_ok=True)
            target.write_bytes(data)
            changed.append(name)
    return f"factory: updated .factory/ ({', '.join(changed)}); commit it on the change branch." if changed else ""


def main():
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ""
        cwd = (json.loads(raw).get("cwd") if raw.strip() else None) or os.getcwd()
        msg = sync(cwd)
        if msg:
            print(msg)
    except Exception:  # a hook must never break a session
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
