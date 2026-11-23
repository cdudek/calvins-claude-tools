"""Shared fixtures for the runner tests: throwaway git repos and a run home in a temp folder."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import store

ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, env={**os.environ, **ENV})
    assert r.returncode == 0, f"git {args}: {r.stderr}"
    return r.stdout.strip()


def make_repo(root: Path, name: str = "app", files: dict | None = None, remote: bool = False) -> Path:
    repo = root / name
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    for rel, text in (files or {"README.md": "x\n"}).items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    if remote:
        bare = root / f"{name}.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
        git(repo, "remote", "add", "origin", str(bare))
        git(repo, "push", "-q", "origin", "main")
    return repo


def commit_file(repo: Path, rel: str, text: str, msg: str = "c") -> str:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", msg)
    return git(repo, "rev-parse", "HEAD")


def new_run(home: Path, repo: Path, checks: list[dict], tasks: dict | None = None, slug: str = "t",
            limits: dict | None = None, inputs: dict | None = None) -> str:
    """A run on branch sdlc/<id> with a contract and tasks written the way `sdlc plan` writes them."""
    os.environ["SDLC_HOME"] = str(home)
    rid = store.make_run_id(repo.name, slug, "2026-11-23")
    git(repo, "branch", f"sdlc/{rid}", "main")
    base = git(repo, "rev-parse", "main")
    d = store.init_run(rid, {"title": slug, "repos": {repo.name: {"path": str(repo), "base_sha": base, "branch": f"sdlc/{rid}",
                                                                   "default_branch": "main"}}, "limits": limits or {}})
    (d / "plan.md").write_text("# plan\n")
    store.write_json(d / "contract.json", {"version": 1, "checks": checks})
    store.write_json(d / "tasks.json", tasks or {"milestones": []})
    for rel, text in (inputs or {}).items():
        p = d / "inputs" / repo.name / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return rid


def chk(id: str, repo: str, runner: list[str] | None = None, milestone: str | None = None, **kw) -> dict:
    return {"id": id, "repo": repo, "milestone": milestone, "runner": runner or ["true"], "expect": {"kind": "pass"}, **kw}
