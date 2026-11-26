#!/usr/bin/env python3
"""Usage: migrate-ids.py <repo> [--slug <slug>]
One-shot rewrite of the old factory ids in the git-tracked text files of <repo> (never `.factory/` or `.git/`), committing nothing:
  <spec-id>/R<n>  ->  req-<n>        every tracked text file; refused, with the conflicts listed, when two spec ids share a number
  - I<n>: / - C<n>:  ->  - outcome-<n>: / - constraint-<n>:   in changes/*/intent.md
  [I<n>] / [C<n>]    ->  [outcome-<n>] / [constraint-<n>]     in changes/*/ and specs/ files
With --slug the intent and citation rewrites only touch changes/<slug>/. Prints the files changed and the ids mapped.
Afterwards run check-plan.py: a bare id in plan or intent prose still needs its explainer, which only a person can write.
"""
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

OLD_REQ = re.compile(r"(?<![\w/.-])([a-z0-9]+(?:-[a-z0-9]+)*)/R(\d+)\b")
OLD_DEF = re.compile(r"^(\s*-\s*)([IC])(\d+)(\s*:)", re.M)
OLD_CITE = re.compile(r"\[([IC])(\d+)\]")
WORD = {"I": "outcome", "C": "constraint"}


def tracked(repo):
    out = subprocess.run(["git", "-C", str(repo), "ls-files", "-z"], capture_output=True, text=True, check=True).stdout
    return [p for p in out.split("\0") if p and not p.startswith(".factory/")]


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None  # binary or unreadable


def migrate(repo, slug=None):
    """(files changed, ids mapped, conflicts); nothing is written when there are conflicts."""
    repo = Path(repo)
    texts = {p: t for p in tracked(repo) if (t := read_text(repo / p)) is not None}
    owners = defaultdict(set)
    for t in texts.values():
        for spec, n in OLD_REQ.findall(t):
            owners[n].add(spec)
    conflicts = {f"req-{n}": sorted(s) for n, s in owners.items() if len(s) > 1}
    if conflicts:
        return [], {}, conflicts
    scope = f"changes/{slug}/" if slug else "changes/"
    mapped, changed = {}, []
    for p, t in texts.items():
        new = OLD_REQ.sub(lambda m: mapped.setdefault(m.group(0), f"req-{m.group(2)}"), t)
        if p.startswith(scope) or (p.startswith("specs/") and not slug):
            new = OLD_CITE.sub(lambda m: mapped.setdefault(m.group(0), f"[{WORD[m.group(1)]}-{m.group(2)}]"), new)
        if p.startswith(scope) and p.endswith("/intent.md"):
            def define(m):
                mapped[m.group(2) + m.group(3)] = f"{WORD[m.group(2)]}-{m.group(3)}"
                return f"{m.group(1)}{mapped[m.group(2) + m.group(3)]}{m.group(4)}"
            new = OLD_DEF.sub(define, new)
        if new != t:
            (repo / p).write_text(new, encoding="utf-8")
            changed.append(p)
    return changed, mapped, {}


def main():
    args = sys.argv[1:]
    slug = None
    if "--slug" in args and args.index("--slug") == len(args) - 2:
        args, slug = args[:-2], args[-1]
    if len(args) != 1:
        print("usage: migrate-ids.py <repo> [--slug <slug>]", file=sys.stderr)
        return 2
    try:
        changed, mapped, conflicts = migrate(args[0], slug)
    except (subprocess.CalledProcessError, OSError) as e:
        print(f"MIGRATE FAIL {e}")
        return 1
    if conflicts:
        for rid, specs in sorted(conflicts.items()):
            print(f"MIGRATE FAIL {rid} would merge {', '.join(f'{s}/R{rid[4:]}' for s in specs)}: renumber one of them first, then run again")
        return 1
    for p in changed:
        print(f"changed {p}")
    for old, new in sorted(mapped.items()):
        print(f"mapped {old} -> {new}")
    print(f"MIGRATE OK {len(changed)} files changed, {len(mapped)} ids mapped; nothing committed. Run check-plan.py next: bare ids in prose need an explainer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
