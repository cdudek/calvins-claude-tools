#!/usr/bin/env python3
"""Usage: heavy.py <command> [args...]
Runs the command while holding one global file lock, so E2E suites, hidden-test runs and app servers of parallel
eval runs never overlap. The lock file is $CFACTORY_EVAL_HEAVY_LOCK, default ~/.cfactory/eval/heavy.lock.
Runs get it as `heavy <cmd>` (a wrapper in their PATH); grade.py imports `locked()`.
"""
import contextlib
import fcntl
import os
import subprocess
import sys
from pathlib import Path


GIT = ["git", "-c", "gc.auto=0"]  # a background gc collides with rmtree of run directories (gc.pid)


def no_gc_env():
    """Also stop the git calls of child scripts (test-integrity.sh, migrate-ids.py) from auto-gc: GIT_CONFIG_* in this process."""
    n = int(os.environ.get("GIT_CONFIG_COUNT") or 0)
    if not any(os.environ.get(f"GIT_CONFIG_KEY_{i}") == "gc.auto" for i in range(n)):
        os.environ.update({"GIT_CONFIG_COUNT": str(n + 1), f"GIT_CONFIG_KEY_{n}": "gc.auto", f"GIT_CONFIG_VALUE_{n}": "0"})


no_gc_env()


def lock_path():
    return Path(os.environ.get("CFACTORY_EVAL_HEAVY_LOCK") or Path.home() / ".cfactory/eval/heavy.lock")


@contextlib.contextmanager
def locked(path=None):
    p = Path(path) if path else lock_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # blocks until the other heavy step ends; released when the file closes
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    with locked():
        return subprocess.call(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
