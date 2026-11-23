"""Step 2: discovery, probes and the approval screen, against a repo with no SDLC files."""
import json

import contract
import discover
import engine
import store
import testkit as tk
from store import SdlcError

import pytest

FILES = {
    "package.json": json.dumps({"scripts": {"test": "vitest run", "lint": "eslint .", "typecheck": "tsc --noEmit", "build": "vite build"}}),
    "pnpm-lock.yaml": "lockfileVersion: 9\n",
    "CLAUDE.md": "# app\n\n```bash\npnpm test:e2e   # e2e\n```\n",
    ".github/workflows/ci.yml": "name: CI\non: push\njobs:\n  unit:\n    runs-on: ubuntu-latest\n  e2e:\n    runs-on: ubuntu-latest\n",
}


def test_discovery_reads_the_repos_own_files(tmp_path):
    repo = tk.make_repo(tmp_path, "web", FILES)
    d = discover.discover(repo)
    assert d["package_manager"] == "pnpm"
    assert d["commands"]["test"] == ["pnpm", "test"] and d["sources"]["test"] == "package.json"
    assert d["commands"]["typecheck"] == ["pnpm", "typecheck"]
    assert d["commands"]["e2e"][-1].startswith("pnpm test:e2e") and d["sources"]["e2e"] == "CLAUDE.md"
    assert [j["job"] for j in d["ci"]["jobs"]] == ["unit", "e2e"]
    assert discover.full_gate(d)[0] == "bash"


def test_plan_writes_nothing_into_the_repo_and_screen_shows_the_checks(tmp_path, monkeypatch):
    monkeypatch.setenv("SDLC_HOME", str(tmp_path / "home"))
    repo = tk.make_repo(tmp_path, "web", FILES)  # a repo with no sdlc files, hooks, workflow or records folder
    before = (tk.git(repo, "status", "--porcelain=v1", "--untracked-files=all"), sorted(p.name for p in repo.iterdir()))
    rid = discover.plan([str(repo)], "first-run", "First run")
    assert (tk.git(repo, "status", "--porcelain=v1", "--untracked-files=all"), sorted(p.name for p in repo.iterdir())) == before
    assert rid.endswith("-web-first-run") and tk.git(repo, "rev-parse", "--verify", f"sdlc/{rid}")
    c = store.read_json(store.run_dir(rid) / "contract.json")
    assert [k["id"] for k in c["checks"]] == ["full:web"] and c["checks"][0]["runner"][0] == "bash"
    p = discover.screen(rid)
    text = p.read_text()
    assert "Checks that decide the result" in text and "full:web" in text and "Dispatch cap" in text and "Missing tools" in text
    assert not str(repo) in text.split("## Plan")[0]  # the screen is for the owner; nothing else was written
    assert not (repo / ".sdlc").exists() and not (repo / "sdlc.json").exists()


def test_draft_pins_inputs_validates_the_graph_and_freezes_after_approval(tmp_path, monkeypatch):
    monkeypatch.setenv("SDLC_HOME", str(tmp_path / "home"))
    repo = tk.make_repo(tmp_path, "web", FILES)
    rid = discover.plan([str(repo)], "x")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    (scratch / "spec.py").write_text(tk.SPEC)
    (scratch / "contract.json").write_text(json.dumps({"checks": [tk.chk("spec", "web", tk.RUN, "m1", pins=["tests/test_feature.py"],
                                                                         expect={"kind": "fails_on_base"})]}))
    (scratch / "tasks.json").write_text(json.dumps({"milestones": [{"id": "m1", "repo": "web", "needs": [], "tasks": [{"id": "t1", "needs": []}]}]}))
    blockers = discover.draft(rid, None, str(scratch / "contract.json"), str(scratch / "tasks.json"), [f"web:tests/test_feature.py={scratch / 'spec.py'}"], [])
    c = store.read_json(store.run_dir(rid) / "contract.json")
    assert c["checks"][0]["pins"]["tests/test_feature.py"] == store.sha256(tk.SPEC)
    assert any("python3" in b for b in blockers) is False  # python3 exists here
    (scratch / "tasks.json").write_text(json.dumps({"milestones": [{"id": "m1", "repo": "web", "needs": ["m2"], "tasks": []}, {"id": "m2", "repo": "web", "needs": ["m1"], "tasks": []}]}))
    with pytest.raises(SdlcError, match="cycle"):
        discover.draft(rid, None, None, str(scratch / "tasks.json"), [], [])
    (scratch / "tasks.json").write_text(json.dumps({"milestones": [{"id": "m1", "repo": "web", "needs": [], "tasks": [{"id": "t1", "needs": []}]}]}))
    discover.draft(rid, None, None, str(scratch / "tasks.json"), [], [])
    contract.approve(rid, "owner")
    with pytest.raises(SdlcError, match="frozen"):
        discover.draft(rid, None, None, str(scratch / "tasks.json"), [], [])


def test_a_missing_tool_is_an_open_blocker_before_kickoff(tmp_path, monkeypatch):
    monkeypatch.setenv("SDLC_HOME", str(tmp_path / "home"))
    repo = tk.make_repo(tmp_path, "web", FILES)
    rid = discover.plan([str(repo)], "x")
    scratch = tmp_path / "s"
    scratch.mkdir()
    (scratch / "c.json").write_text(json.dumps({"checks": [tk.chk("e", "web", ["no-such-runner-xyz", "--go"])]}))
    assert any("no-such-runner-xyz" in b for b in discover.draft(rid, None, str(scratch / "c.json"), None, [], []))
