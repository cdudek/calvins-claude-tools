#!/usr/bin/env python3
"""Usage: migrate-name.py <repo> | migrate-name.py --home
One-shot rename of the old `cfactory` name to `factory`, committing nothing:
  <repo>   `git mv .cfactory .factory` (refused when .factory exists) and the plan fence ```json cfactory -> ```json factory
           in every git-tracked changes/**/plan*.md. Prints what it changed.
  --home   moves ~/.cfactory to ~/.factory (refused when ~/.factory exists).
Afterwards refresh the scripts copied into .factory/ from the plugin, and have the owner approve a new revision of any plan
whose approved revision still has the old fence (check-plan.py --approved compares the plan through its json block).
"""
import re
import subprocess
import sys
from pathlib import Path

FENCE = re.compile(r"^(\s*`{3,}json )cfactory\b", re.M)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def migrate_repo(repo):
    repo = Path(repo)
    if git(repo, "rev-parse", "--show-toplevel").returncode:
        return 1, [f"{repo} is not a git repo"]
    out = []
    old, new = repo / ".cfactory", repo / ".factory"
    if old.exists():
        if new.exists():
            return 1, [".factory already exists: merge it by hand, then remove .cfactory"]
        moved = git(repo, "mv", ".cfactory", ".factory")
        if moved.returncode:
            return 1, [f"git mv .cfactory .factory failed: {moved.stderr.strip()}"]
        out.append("moved .cfactory -> .factory")
    for rel in git(repo, "ls-files", "-z", "--", "changes").stdout.split("\0"):
        path = repo / rel
        if not rel or not re.fullmatch(r"plan[^/]*\.md", path.name) or not rel.startswith("changes/"):
            continue
        text = path.read_text(encoding="utf-8")
        fixed = FENCE.sub(r"\1factory", text)
        if fixed != text:
            path.write_text(fixed, encoding="utf-8")
            out.append(f"rewrote the plan fence in {rel}")
    return 0, out or ["nothing to change"]


def migrate_home():
    old, new = Path.home() / ".cfactory", Path.home() / ".factory"
    if not old.exists():
        return 0, ["no ~/.cfactory: nothing to move"]
    if new.exists():
        return 1, ["~/.factory already exists: merge it by hand, then remove ~/.cfactory"]
    old.rename(new)
    return 0, ["moved ~/.cfactory -> ~/.factory"]


def main():
    args = sys.argv[1:]
    if args == ["--home"]:
        code, lines = migrate_home()
    elif len(args) == 1 and not args[0].startswith("-"):
        code, lines = migrate_repo(args[0])
    else:
        print("usage: migrate-name.py <repo> | migrate-name.py --home", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
