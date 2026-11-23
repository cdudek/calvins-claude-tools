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
                                                                   "default_branch": "main"}}})
    (d / "plan.md").write_text("# plan\n")
    store.write_json(d / "contract.json", {"version": 1, "checks": checks, "limits": {"max_dispatches": 50, **(limits or {})}})
    store.write_json(d / "tasks.json", tasks or {"milestones": []})
    for rel, text in (inputs or {}).items():
        p = d / "inputs" / repo.name / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return rid


def chk(id: str, repo: str, runner: list[str] | None = None, milestone: str | None = None, **kw) -> dict:
    return {"id": id, "repo": repo, "milestone": milestone, "runner": runner or ["true"], "expect": {"kind": "pass"}, **kw}


def pin(rid: str, repo: str, rel: str) -> str:
    return store.sha256((store.run_dir(rid) / "inputs" / repo / rel).read_bytes())


SPEC = (
    "import sys, unittest\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
    "import feature\n\n\nclass T(unittest.TestCase):\n    def test_greet(self):\n        self.assertEqual(feature.greet(), 'hello')\n\n\n"
    "if __name__ == '__main__':\n    unittest.main()\n"
)
RUN = ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"]


def feature_run(tmp_path: Path, tasks: dict | None = None, limits: dict | None = None, extra_files: dict | None = None):
    """A repo whose acceptance spec (pinned, approved) wants greet() == 'hello'; base returns 'hi'."""
    files = {"feature.py": "def greet():\n    return 'hi'\n", **(extra_files or {})}
    repo = make_repo(tmp_path, "app", files)
    tasks = tasks or {"milestones": [{"id": "m1", "repo": "app", "needs": [],
                                      "tasks": [{"id": "t1", "needs": [], "paths": ["feature.py"], "title": "greet says hello"}]}]}
    rid = new_run(tmp_path / "home", repo, [], tasks, limits=limits, inputs={"tests/test_feature.py": SPEC})
    p = pin(rid, "app", "tests/test_feature.py")
    checks = [chk("spec", "app", RUN, "m1", task="t1", pins={"tests/test_feature.py": p}, expect={"kind": "fails_on_base"}),
              chk("full", "app", RUN, None, due="each", pins={"tests/test_feature.py": p})]
    d = store.run_dir(rid)
    c = store.read_json(d / "contract.json")
    c["checks"] = checks
    store.write_json(d / "contract.json", c)
    return repo, rid


def build(rid: str, tid: str, files: dict, msg: str = "work") -> str:
    """What a builder subagent does: edit its worktree, commit."""
    import engine
    info = engine.dispatch(rid, tid)
    wt = Path(info["worktree"])
    for rel, text in files.items():
        (wt / rel).parent.mkdir(parents=True, exist_ok=True)
        (wt / rel).write_text(text)
    git(wt, "add", "-A")
    git(wt, "commit", "-qm", msg)
    return git(wt, "rev-parse", "HEAD")


def approve(rid: str, by: str = "owner"):
    """Stands in for the owner's gate: writes the marker the approval gate writes for this exact bundle, then approves."""
    import contract
    store.write_json(store.gate_marker(rid, "approve"), {"digest": contract.bundle_digest(rid)})
    return contract.approve(rid, by)


def owner_restart(rid: str) -> None:
    store.write_json(store.gate_marker(rid, "restart"), {"nonce": "x"})
