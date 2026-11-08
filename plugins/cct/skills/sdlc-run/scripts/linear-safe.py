"""Make a Markdown body safe to post to Linear: no local paths, repo paths as permalinks.

    python3 linear-safe.py <file.md>            prints the rewritten body
    python3 linear-safe.py --check <file.md>    exit 2 and list the offending lines, print nothing

A Linear reader cannot open `docs/designs/x.md` or `changes/REV-1-x/plan.md`; they can open
https://github.com/<org>/<repo>/blob/<sha>/docs/designs/x.md. Every repo-relative path that
exists in the working tree is rewritten to that permalink at HEAD. Paths that can only
mean this laptop (`~/`, `/Users/`, `/home/`, `.worktrees/`, `.claude/plans/`) are refused:
exit 2, the offending lines on stderr. stdlib only.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

LOCAL = re.compile(r"(~/|/Users/|/home/|\.worktrees/|\.claude/plans/)")
# `docs/designs/...md`, `changes/REV-1-x/plan.md`, `docs/sdlc.md`, `src/lib/x.ts:12` — a repo path
# is a bare token with a slash and a file extension, optionally wrapped in backticks.
REPO_PATH = re.compile(
    r"`?(?<![\w/.-])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9]+)(?::\d+)?`?"
)


def sh(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def permalink_base() -> str:
    url = sh("git", "remote", "get-url", "origin")
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
    if not m:
        sys.exit(f"origin is not a GitHub remote: {url}")
    return f"https://github.com/{m.group(1)}/{m.group(2)}/blob/{sh('git', 'rev-parse', 'HEAD')}"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    files = [a for a in argv[1:] if not a.startswith("--")]
    if len(files) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    text = Path(files[0]).read_text(encoding="utf-8")
    bad = [
        f"{n}: {line.strip()}" for n, line in enumerate(text.splitlines(), 1) if LOCAL.search(line)
    ]
    if bad:
        print("REFUSED: local paths in text bound for Linear:\n" + "\n".join(bad), file=sys.stderr)
        return 2
    root = Path(sh("git", "rev-parse", "--show-toplevel"))
    base = permalink_base()

    def link(m: re.Match[str]) -> str:
        rel = m.group(1)
        if rel.startswith("http") or not (root / rel).exists():
            return m.group(0)
        return f"[{rel}]({base}/{rel})"

    out = REPO_PATH.sub(link, text)
    if not check:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
