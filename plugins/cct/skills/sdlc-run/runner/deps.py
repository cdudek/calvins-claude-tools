"""The safe dependency path (design 3.6): approved manifest and lockfile contents, applied by the runner, nothing else."""
from __future__ import annotations

import difflib
import re
import subprocess
from pathlib import Path

import contract
import store
from contract import git

MANIFEST = re.compile(r"(^|/)(package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|pyproject\.toml|uv\.lock|poetry\.lock|"
                      r"requirements[^/]*\.txt|Gemfile(\.lock)?|go\.mod|go\.sum|Cargo\.(toml|lock))$")
FROZEN = {"pnpm-lock.yaml": ["pnpm", "install", "--frozen-lockfile", "--ignore-scripts"],
          "yarn.lock": ["yarn", "install", "--immutable", "--mode=skip-build"],
          "package-lock.json": ["npm", "ci", "--ignore-scripts"],
          "uv.lock": ["uv", "sync", "--frozen"], "poetry.lock": ["poetry", "install", "--no-root"]}


def approved(rid: str, repo: str) -> dict:
    return store.read_json(store.run_dir(rid) / "contract.json").get("deps", {}).get(repo, {}).get("files", {})


def guard(rid: str, repo: str, base: str, cand: str) -> list[str]:
    """A candidate changes a manifest or lockfile only to exactly the approved content."""
    path = store.load_meta(rid)["repos"][repo]["path"]
    ok = approved(rid, repo)
    bad = []
    for rel in contract.git(path, "diff", "--name-only", f"{base}..{cand}").splitlines():
        if MANIFEST.search(rel):
            blob = subprocess.run(["git", "show", f"{cand}:{rel}"], cwd=path, capture_output=True).stdout
            if rel not in ok:
                bad.append(f"unapproved change to {rel}")
            elif store.sha256(blob) != ok[rel]:
                bad.append(f"{rel} differs from the approved resolution")
    return bad


def frozen_install(path: str | Path) -> list[str] | None:
    for lock, argv in FROZEN.items():
        if (Path(path) / lock).exists():
            return argv
    return None


def diff_text(rid: str, repo: str) -> str:
    """Unified diff of every approved manifest or lockfile against the repo at its base: the approval screen shows this."""
    meta = store.load_meta(rid)["repos"][repo]
    out = []
    for rel in approved(rid, repo):
        try:
            old = git(meta["path"], "show", f"{meta['base_sha']}:{rel}").splitlines(True)
        except store.SdlcError:
            old = []
        new = (store.run_dir(rid) / "deps" / repo / rel).read_text().splitlines(True)
        out += difflib.unified_diff(old, new, f"a/{rel}", f"b/{rel}")
    return "".join(out)


def apply(rid: str, repo: str, worktree: Path) -> bool:
    """Copy the approved files into a worktree and commit them; the caller then runs frozen_install as a job."""
    src = store.run_dir(rid) / "deps" / repo
    files = approved(rid, repo)
    for rel in files:
        (worktree / rel).parent.mkdir(parents=True, exist_ok=True)
        (worktree / rel).write_bytes((src / rel).read_bytes())
    if not git(worktree, "status", "--porcelain"):
        return False
    git(worktree, "add", "-A")
    git(worktree, "commit", "-qm", "sdlc: approved dependency change")
    return True
