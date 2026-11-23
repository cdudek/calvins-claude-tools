"""Step 8: producer and consumer through the final merge sequence, plus the approved-dependency guard."""

import contract
import deps
import engine
import pytest
import release
import store
import testkit as tk
from contract import PENDING, READY
from store import SdlcError

CONSUME = ["python3", "-c", "import os,sys\nsys.exit(0 if 'SDLC_ARTIFACT_LIB' in os.environ and print('Ran 1 tests') is None else 1)"]
ONE = ["python3", "-c", "print('Ran 1 tests')"]


def pilot(tmp_path):
    lib = tk.make_repo(tmp_path, "lib", {"lib.py": "V = 1\n"}, remote=True)
    app = tk.make_repo(tmp_path, "app", {"pin.txt": "\n"}, remote=True)
    rid = tk.new_run(tmp_path / "home", lib, [])
    meta = store.load_meta(rid)
    tk.git(app, "branch", f"sdlc/{rid}", "main")
    meta["repos"]["app"] = {"path": str(app), "base_sha": tk.git(app, "rev-parse", "main"), "branch": f"sdlc/{rid}", "default_branch": "main"}
    store.save_meta(rid, meta)
    d = store.run_dir(rid)
    store.write_json(d / "tasks.json", {"milestones": [
        {"id": "m1", "repo": "lib", "needs": [], "tasks": [{"id": "a", "needs": [], "paths": ["lib.py"]}]},
        {"id": "m2", "repo": "app", "needs": ["m1"], "tasks": [{"id": "b", "needs": [], "paths": ["app.py"]}]}]})
    store.write_json(d / "contract.json", {"checks": [
        tk.chk("lib-gate", "lib", ONE, "m1", count=True, expect={"kind": "pass"}),
        tk.chk("app-gate", "app", CONSUME, "m2", consumes=["lib"])],
        "edges": [{"producer": "lib", "consumer": "app", "pack": ["git", "ls-tree", "-r", "{ref}"],
                   "release": {"kind": "git-tag", "fetch": ["git", "ls-tree", "-r", "{ref}"]}, "pin": {"file": "pin.txt", "line": "lib={digest}"}}]})
    engine.validate_plan(rid)
    contract.approve(rid, "owner")
    return lib, app, rid


def land(rid, tid, files):
    tk.build(rid, tid, files)
    engine.submit(rid, tid)
    store.update_cp(rid, lambda cp: cp["tasks"][tid].update(verified=cp["tasks"][tid]["sha"]))
    engine.integrate(rid, tid)


def test_producer_consumer_pilot_through_the_final_merge_sequence(tmp_path):
    lib, app, rid = pilot(tmp_path)
    assert release.merge_order(rid) == ["lib", "app"]
    land(rid, "a", {"lib.py": "V = 2\n"})
    assert engine.close_milestone(rid, "m1")["status"] == "merged"
    ident = release.pack(rid, "lib")
    land_app = engine.next_batch(rid)
    assert [t["id"] for t in land_app] == ["b"]  # the consumer builds once the producer milestone merged
    land(rid, "b", {"app.py": "import lib\n"})
    assert engine.close_milestone(rid, "m2")["status"] == "merged"
    engine.final_verify(rid)
    code, first, _ = contract.evaluate(rid)
    assert code == PENDING and "awaits publication of lib" in first
    # the owner merges the producer PR first: simulate by moving main on the remote
    engine.push(rid, "lib")
    branch = store.load_meta(rid)["repos"]["lib"]["branch"]
    tk.git(lib, "push", "-q", "origin", f"{branch}:main")
    rec = release.publish(rid, "lib")
    assert rec["digest"] == ident["digest"]
    assert contract.evaluate(rid)[0] == PENDING  # the pin moved the consumer head: its proof is stale
    engine.final_verify(rid)
    code, first, _ = contract.evaluate(rid)
    assert code == READY, first
    pin = tk.git(app, "show", f"{store.load_meta(rid)['repos']['app']['branch']}:pin.txt")
    assert pin == f"lib={rec['digest']}"
    # a changed producer invalidates the consumer's proof
    tk.commit_file(engine.project_wt(rid, "lib"), "lib.py", "V = 3\n")
    assert contract.evaluate(rid)[0] == PENDING


def test_published_artifact_that_differs_is_blocked(tmp_path):
    lib, app, rid = pilot(tmp_path)
    land(rid, "a", {"lib.py": "V = 2\n"})
    engine.close_milestone(rid, "m1")
    release.pack(rid, "lib")  # main on the remote still has V = 1
    with pytest.raises(SdlcError, match="differs from the packed"):
        release.publish(rid, "lib")


def test_cyclic_repos_are_a_planning_error(tmp_path):
    lib, app, rid = pilot(tmp_path)
    c = store.read_json(store.run_dir(rid) / "contract.json")
    c["edges"].append({"producer": "app", "consumer": "lib", "pack": ["true"]})
    store.write_json(store.run_dir(rid) / "contract.json", c)
    with pytest.raises(SdlcError, match="depend on each other"):
        release.merge_order(rid)


def test_only_the_approved_manifest_resolution_may_change(tmp_path):
    repo = tk.make_repo(tmp_path, "web", {"package.json": '{"dependencies": {}}\n', "src.js": "1\n"})
    rid = tk.new_run(tmp_path / "home", repo, [])
    good = '{"dependencies": {"left-pad": "1.3.0"}}\n'
    d = store.run_dir(rid)
    (d / "deps" / "web").mkdir(parents=True)
    (d / "deps" / "web" / "package.json").write_text(good)
    c = store.read_json(d / "contract.json")
    c["deps"] = {"web": {"files": {"package.json": store.sha256(good)}}}
    store.write_json(d / "contract.json", c)
    base = tk.git(repo, "rev-parse", "HEAD")
    sha = tk.commit_file(repo, "package.json", good)
    assert deps.guard(rid, "web", base, sha) == []
    sha2 = tk.commit_file(repo, "package.json", '{"dependencies": {"evil": "9"}}\n')
    assert "differs from the approved" in deps.guard(rid, "web", base, sha2)[0]
    sha3 = tk.commit_file(repo, "package-lock.json", "{}\n")
    assert any("unapproved change to package-lock.json" in b for b in deps.guard(rid, "web", base, sha3))
    assert "left-pad" in deps.diff_text(rid, "web")
    assert deps.frozen_install(repo) == ["npm", "ci", "--ignore-scripts"]
