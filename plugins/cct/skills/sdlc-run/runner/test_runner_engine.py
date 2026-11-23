"""Steps 3-5: checkpoints and resume, builder + verifier, graph, caps, stop, pushes."""
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import contract
import engine
import graph
import pytest
import store
import testkit as tk
import verify
from contract import PENDING, READY
from store import SdlcError

GOOD = {"feature.py": "def greet():\n    return 'hello'\n"}


def approved(tmp_path, **kw):
    repo, rid = tk.feature_run(tmp_path, **kw)
    engine.validate_plan(rid)
    tk.approve(rid)
    return repo, rid


def _retry(rid, tid):
    store.update_cp(rid, lambda cp: cp["tasks"][tid].update(status="pending"))  # as a rejected or failed verification does


def _owning(*paths):
    return {"milestones": [{"id": "m1", "repo": "app", "needs": [], "tasks": [{"id": "t1", "needs": [], "paths": list(paths)}]}]}


def deliver(rid, tid="t1", files=GOOD):
    tk.build(rid, tid, files)
    engine.submit(rid, tid)
    res = engine.verify_task(rid, tid)
    engine.integrate(rid, tid)
    return res


# ---- step 4: one feature through a builder and an independent verifier ---------------------------

def test_one_feature_end_to_end_reaches_ready(tmp_path):
    repo, rid = approved(tmp_path)
    assert [t["id"] for t in engine.next_batch(rid)] == ["t1"]
    res = deliver(rid)
    assert res[0]["verdict"] == "PASS" and res[0]["base"]["exit"] != 0  # failed on the base, passes on the candidate
    out = engine.close_milestone(rid, "m1")
    assert out["status"] == "merged"
    assert engine.final_verify(rid) and contract.evaluate(rid)[0] == READY
    meta = store.load_meta(rid)
    assert tk.git(repo, "show", f"{meta['repos']['app']['branch']}:feature.py").count("hello") == 1


def test_a_builder_cannot_change_the_pinned_assertion(tmp_path):
    _, rid = approved(tmp_path)
    tk.build(rid, "t1", {**GOOD, "tests/test_feature.py": tk.SPEC.replace("'hello'", "'hi'")})
    with pytest.raises(SdlcError, match="pinned input"):
        engine.submit(rid, "t1")
    cp = store.load_cp(rid)["tasks"]["t1"]
    assert cp["status"] == "pending" and "pinned input" in cp["reason"] and cp["attempts"] == 1  # back in the queue, attempt counted


def test_the_verifier_ignores_a_tampered_spec_even_without_the_guard(tmp_path):
    repo, rid = approved(tmp_path)
    sha = tk.build(rid, "t1", {"feature.py": "def greet():\n    return 'hi'\n", "tests/test_feature.py": tk.SPEC.replace("'hello'", "'hi'")})
    c = {k["id"]: k for k in store.read_json(store.run_dir(rid) / "contract.json")["checks"]}["spec"]
    b = verify.verify_check(rid, c, ref=sha, base_sha=store.load_cp(rid)["tasks"]["t1"]["base"])
    assert b["verdict"] == "BLOCKED" and "changed pinned input" in b["reason"]


def test_removed_assertion_and_added_skip_are_rejected(tmp_path):
    other = "import unittest\nclass O(unittest.TestCase):\n    def test_a(self):\n        self.assertEqual(len('ab'), 2)\n        self.assertIn('a', 'abc')\n"
    _, rid = approved(tmp_path, extra_files={"tests/test_other.py": other}, tasks=_owning("feature.py", "tests/test_other.py"))
    tk.build(rid, "t1", {**GOOD, "tests/test_other.py": other.replace("        self.assertIn('a', 'abc')\n", "")})
    with pytest.raises(SdlcError, match="removed an assertion"):
        engine.submit(rid, "t1")


def test_wrong_code_is_FAIL_not_pass_and_a_results_file_is_ignored(tmp_path):
    _, rid = approved(tmp_path, tasks=_owning("feature.py", "results.json"))
    tk.build(rid, "t1", {"feature.py": "def greet():\n    return 'nope'\n", "results.json": '{"passed": true}'})
    engine.submit(rid, "t1")
    res = engine.verify_task(rid, "t1")
    assert res[0]["verdict"] == "FAIL"
    with pytest.raises(SdlcError, match="no passing verifier"):
        engine.integrate(rid, "t1")


def test_a_hand_written_receipt_for_another_head_or_bundle_does_not_count(tmp_path):
    repo, rid = approved(tmp_path)
    for c in store.read_json(store.run_dir(rid) / "contract.json")["checks"]:
        store.write_json(contract.receipt_path(rid, c["id"], "app"), {"body": {
            "run": rid, "check": c["id"], "repo": "app", "verdict": "PASS", "sha": "0" * 40,
            "bundle": contract.bundle_digest(rid), "pins": contract.pins_digest(c), "deps": {}}})
    code, first, _ = contract.evaluate(rid)
    assert code == PENDING and "head is" in first  # the receipt must name the head it ran on


def test_rejected_task_goes_back_to_pending_and_a_fix_passes(tmp_path):
    _, rid = approved(tmp_path)
    tk.build(rid, "t1", {**GOOD, "tests/test_feature.py": tk.SPEC.replace("'hello'", "'hi'")})
    with pytest.raises(SdlcError, match="pinned input"):
        engine.submit(rid, "t1")
    assert [t["id"] for t in engine.next_batch(rid)] == ["t1"]  # a fix attempt is schedulable again
    assert graph.deadlock(engine.tasks_doc(rid), store.load_cp(rid)) == ""
    info = engine.dispatch(rid, "t1")
    wt = Path(info["worktree"])
    tk.git(wt, "rm", "-q", "-f", "tests/test_feature.py")
    tk.git(wt, "commit", "-qm", "drop the edited spec")
    engine.submit(rid, "t1")
    assert engine.verify_task(rid, "t1")[0]["verdict"] == "PASS"
    engine.integrate(rid, "t1")
    assert store.load_cp(rid)["tasks"]["t1"]["status"] == "done" and store.load_cp(rid)["tasks"]["t1"]["attempts"] == 2


def test_check_that_passes_on_base_proves_nothing(tmp_path):
    _, rid = approved(tmp_path)
    c = {k["id"]: k for k in store.read_json(store.run_dir(rid) / "contract.json")["checks"]}["spec"]
    c = {**c, "runner": ["python3", "-c", "print('Ran 1 tests')"], "pins": {}}
    b = verify.verify_check(rid, c)
    assert b["verdict"] == "BLOCKED" and "passes on the base" in b["reason"]


@pytest.mark.parametrize("runner,why", [(["python3", "-c", "print('Ran 0 tests')"], "0 tests"),
                                        (["definitely-not-installed-xyz"], "env"),
                                        (["python3", "-c", "print('hello')"], "no test count")])
def test_zero_tests_missing_tool_and_uncountable_output_are_blocked(tmp_path, runner, why):
    _, rid = approved(tmp_path)
    c = tk.chk("x", "app", runner)
    assert verify.verify_check(rid, c)["verdict"] == "BLOCKED"
    assert why in verify.verify_check(rid, c)["reason"]


def test_real_failure_is_FAIL_and_missing_prerequisite_is_BLOCKED_env(tmp_path):
    _, rid = approved(tmp_path)
    assert verify.verify_check(rid, tk.chk("f", "app", ["python3", "-c", "import sys;print('1 failed');sys.exit(1)"]))["verdict"] == "FAIL"
    b = verify.verify_check(rid, tk.chk("p", "app", prereqs=[{"tool": "no-such-tool-xyz"}], runner=["true"], count=False))
    assert b["verdict"] == "BLOCKED" and b["reason"].startswith("env: tool no-such-tool-xyz")


def test_negative_control_for_an_invariant(tmp_path):
    _, rid = approved(tmp_path)
    ok = ["python3", "-c", "print('Ran 1 tests')"]
    good = tk.chk("inv", "app", ok, expect={"kind": "negative_control", "control": ["python3", "-c", "import sys;print('1 failed');sys.exit(1)"]})
    assert verify.verify_check(rid, good)["verdict"] == "PASS"
    bad = tk.chk("inv2", "app", ok, expect={"kind": "negative_control", "control": ok})
    assert verify.verify_check(rid, bad)["verdict"] == "BLOCKED"


# ---- step 3: checkpoints and resume --------------------------------------------------------------

KILL = """
import sys, time, os
sys.path.insert(0, {runner!r})
os.environ['SDLC_HOME'] = {home!r}
import engine
engine.dispatch({rid!r}, 't1')
open({flag!r}, 'w').write('running')
time.sleep(60)
"""


def test_kill_mid_milestone_then_resume_keeps_counters(tmp_path):
    repo, rid = approved(tmp_path, limits={"max_dispatches": 5})
    flag = tmp_path / "flag"
    p = subprocess.Popen([sys.executable, "-c", KILL.format(runner=str(Path(__file__).parent), home=str(tmp_path / "home"), rid=rid, flag=str(flag))])
    for _ in range(100):
        if flag.exists():
            break
        time.sleep(0.1)
    p.send_signal(signal.SIGKILL)
    p.wait()
    cp = store.load_cp(rid)
    assert cp["tasks"]["t1"]["status"] == "running" and cp["dispatches"] == 1
    out = engine.resume(rid)
    assert out["requeued"] == ["t1"] and out["dispatches"] == 1 and out["next"] == ["t1"]
    info = engine.dispatch(rid, "t1")  # the same worktree is reused, the attempt is the second
    assert store.load_cp(rid)["tasks"]["t1"]["attempts"] == 2 and Path(info["worktree"]).exists()
    assert store.load_cp(rid)["dispatches"] == 2


def test_resume_refuses_a_changed_bundle_and_a_stopped_run(tmp_path):
    _, rid = approved(tmp_path)
    (store.run_dir(rid) / "plan.md").write_text("weakened")
    with pytest.raises(SdlcError, match="integrity"):
        engine.resume(rid)


def test_run_id_branch_and_active_link(tmp_path):
    repo, rid = approved(tmp_path)
    assert rid == "2026-11-23-app-t" and (store.home() / "active" / rid).is_symlink()
    assert store.load_meta(rid)["repos"]["app"]["branch"] == f"sdlc/{rid}"
    assert store.make_run_id("app", "t", "2026-11-23") == "2026-11-23-app-t-2"  # a number only on a collision
    tk.git(repo, "checkout", "-q", f"sdlc/{rid}")
    assert store.resolve_run(None, repo) == rid
    store.set_status(rid, "done")
    assert not (store.home() / "active" / rid).exists()


# ---- step 5: graph, parallel builders, caps, stop, pushes ----------------------------------------

def _tasks(*ms):
    for m in ms:
        for t in m["tasks"]:
            t.setdefault("waiver", "fixture: no behaviour to prove")
    return {"milestones": list(ms)}


def test_cycle_is_a_planning_error_naming_it(tmp_path):
    doc = _tasks({"id": "m1", "repo": "app", "needs": ["m2"], "tasks": [{"id": "a", "needs": []}]},
                 {"id": "m2", "repo": "app", "needs": [], "tasks": [{"id": "b", "needs": ["a"]}]})
    repo, rid = tk.feature_run(tmp_path, tasks=doc)
    with pytest.raises(SdlcError, match="cycle"):
        engine.validate_plan(rid)
    t2 = _tasks({"id": "m1", "repo": "app", "needs": [], "tasks": [{"id": "a", "needs": ["b"]}, {"id": "b", "needs": ["a"]}]})
    assert "a->b->a" in graph.describe(graph.find_cycle(graph.build(t2))) or "b->a->b" in graph.describe(graph.find_cycle(graph.build(t2)))


def test_run_time_deadlock_is_found_when_nothing_can_progress():
    # m1 needs m2, but m2's only task is blocked for good: nothing running, nothing ready
    doc = _tasks({"id": "m1", "repo": "app", "needs": ["m2"], "tasks": [{"id": "a", "needs": []}]},
                 {"id": "m2", "repo": "app", "needs": [], "tasks": [{"id": "b", "needs": []}]})
    cp = {"tasks": {"b": {"status": "blocked"}}, "milestones": {"m2": {"status": "open"}}}
    assert "m1 waits on m2" in graph.deadlock(doc, cp)
    ok = {"tasks": {}, "milestones": {"m2": {"status": "open"}}}
    assert graph.deadlock(doc, ok) == ""  # a ready task exists


def test_dispatch_records_blocked_deadlock_with_the_cycle(tmp_path):
    _, rid = approved(tmp_path)
    store.update_cp(rid, lambda cp: cp.__setitem__("extra_tasks", {"x": {"milestone": "m1", "needs": ["y"]}, "y": {"milestone": "m1", "needs": ["x"]}}))
    with pytest.raises(SdlcError, match="BLOCKED deadlock cycle"):
        engine.dispatch(rid, "t1")
    assert contract.evaluate(rid)[0] == contract.BLOCKED and "deadlock" in contract.evaluate(rid)[1]


def test_parallel_batches_respect_disjoint_paths_and_the_cap(tmp_path):
    ts = [{"id": f"t{i}", "needs": [], "paths": [f"src/p{i}/"]} for i in range(10)]
    doc = _tasks({"id": "m1", "repo": "app", "needs": [], "tasks": ts + [{"id": "clash", "needs": [], "paths": ["src/p0/x.py"]}]})
    repo, rid = tk.feature_run(tmp_path, tasks=doc)
    tk.approve(rid)
    ids = [t["id"] for t in engine.next_batch(rid)]
    assert len(ids) == 8 and "clash" not in ids  # default cap 8; the overlapping task waits
    repo2, rid2 = tk.feature_run(tmp_path / "b", tasks=doc, limits={"builders": 3})
    tk.approve(rid2)
    assert len(engine.next_batch(rid2)) == 3
    fewer = _tasks({"id": "m1", "repo": "app", "needs": [], "tasks": [{"id": "a", "needs": [], "paths": ["a"]}, {"id": "b", "needs": ["a"], "paths": ["b"]}]})
    repo3, rid3 = tk.feature_run(tmp_path / "c", tasks=fewer)
    tk.approve(rid3)
    assert [t["id"] for t in engine.next_batch(rid3)] == ["a"]  # the graph allows only one


def test_two_builders_in_parallel_worktrees_integrate_in_order(tmp_path):
    doc = _tasks({"id": "m1", "repo": "app", "needs": [], "tasks": [{"id": "a", "needs": [], "paths": ["a.py"]}, {"id": "b", "needs": [], "paths": ["b.py"]}]})
    repo, rid = tk.feature_run(tmp_path, tasks=doc)
    d = store.run_dir(rid)
    c = store.read_json(d / "contract.json")
    c["checks"] = [tk.chk("full", "app", ["python3", "-c", "print('Ran 1 tests')"], due="each")]
    store.write_json(d / "contract.json", c)
    tk.approve(rid)
    batch = [t["id"] for t in engine.next_batch(rid)]
    assert batch == ["a", "b"]
    for t in batch:
        tk.build(rid, t, {f"{t}.py": "x = 1\n"})
    wts = {Path(engine.wt_path(store.load_meta(rid)["repos"]["app"]["path"], rid, f"t-{t}")) for t in batch}
    assert len(wts) == 2 and all(w.parent.name == ".worktrees" for w in wts)
    for t in batch:
        engine.submit(rid, t)
        store.update_cp(rid, lambda cp, t=t: cp["tasks"][t].update(verified=cp["tasks"][t]["sha"]))
        engine.integrate(rid, t)
    assert engine.close_milestone(rid, "m1")["status"] == "merged"
    assert ".worktrees/" in (Path(store.load_meta(rid)["repos"]["app"]["path"]) / ".git" / "info" / "exclude").read_text()
    assert tk.git(repo, "status", "--porcelain") == ""  # nothing the runner did shows in the repo


def test_caps_are_counted_before_launch_and_block(tmp_path):
    _, rid = approved(tmp_path, limits={"max_dispatches": 2})
    tk.build(rid, "t1", GOOD)
    _retry(rid, "t1")
    tk.build(rid, "t1", {"feature.py": "def greet():\n    return 'hello'\n# fix\n"}, "fix1")
    with pytest.raises(SdlcError, match="BLOCKED cap dispatch cap 2"):
        engine.dispatch(rid, "t1")
    assert contract.evaluate(rid)[0] == contract.BLOCKED
    repo2, rid2 = approved(tmp_path / "x")
    for _ in range(3):
        engine.dispatch(rid2, "t1")
        _retry(rid2, "t1")
    with pytest.raises(SdlcError, match="used its 3 attempts"):
        engine.dispatch(rid2, "t1")


def test_deadline_passed_blocks_dispatch(tmp_path):
    _, rid = approved(tmp_path)
    a = store.read_json(store.run_dir(rid) / "approval.json")
    a["deadline"] = time.time() - 5
    store.write_json(store.run_dir(rid) / "approval.json", a)
    with pytest.raises(SdlcError, match="deadline"):
        engine.dispatch(rid, "t1")


def test_stop_cancels_a_live_job_and_blocks_further_work(tmp_path):
    _, rid = approved(tmp_path)
    c = tk.chk("slow", "app", ["python3", "-c", "import time;time.sleep(60)"], count=False)
    res = {}
    th = threading.Thread(target=lambda: res.update(b=verify.verify_check(rid, c)))
    th.start()
    pids = []
    for _ in range(100):
        pids = list((store.run_dir(rid) / "jobs").glob("*.pid"))
        if pids:
            break
        time.sleep(0.1)
    assert pids, "the job never started"
    pid = json.loads(pids[0].read_text())["pid"]
    t0 = time.time()
    killed = engine.stop(rid)
    th.join(15)
    assert not th.is_alive() and time.time() - t0 < 10 and pid in killed
    with pytest.raises(ProcessLookupError):
        os.killpg(pid, 0)  # the whole process group is gone
    assert res["b"]["verdict"] == "BLOCKED" and "stopped" in res["b"]["reason"]
    with pytest.raises(SdlcError, match="STOPPED"):
        engine.dispatch(rid, "t1")
    assert contract.evaluate(rid)[0] == contract.BLOCKED and "STOPPED" in contract.evaluate(rid)[1]
    assert not (store.home() / "active" / rid).exists() or store.load_meta(rid)["status"] == "stopped"
    tk.owner_restart(rid)
    engine.restart(rid)
    assert not store.is_stopped(rid)


def test_push_is_not_redone_after_a_crash(tmp_path):
    repo = tk.make_repo(tmp_path, "app", {"feature.py": "x\n"}, remote=True)
    rid = tk.new_run(tmp_path / "home", repo, [tk.chk("a", "app", ["true"], count=False)])
    tk.approve(rid)
    meta = store.load_meta(rid)
    assert engine.push(rid, "app") == "done"
    assert engine.push(rid, "app") == "already-done"
    remote = tk.git(repo, "ls-remote", "origin", f"refs/heads/{meta['repos']['app']['branch']}").split()[0]
    assert remote == tk.git(repo, "rev-parse", meta["repos"]["app"]["branch"])
    # a crash between the push and the checkpoint: intent recorded, push happened, no `done`
    sha = remote
    store.update_cp(rid, lambda cp: cp["external"].__setitem__("push:app", {"state": "started", "sha": sha}))
    assert engine.push(rid, "app") == "reconciled"  # found on the remote: not pushed a second time


def test_transient_retry_keeps_the_artifact_environment(tmp_path):
    _, rid = approved(tmp_path)
    store.update_cp(rid, lambda cp: cp.__setitem__("artifacts", {"lib": {"source": "abc", "digest": "d"}}))
    flag = tmp_path / "flag"
    code = (f"import os,sys\nf={str(flag)!r}\nif not os.path.exists(f):\n    open(f,'w').write('1')\n    print('ECONNRESET')\n    sys.exit(1)\n"
            "assert 'SDLC_ARTIFACT_LIB' in os.environ, 'retry lost the artifact env'\nprint('Ran 1 tests')\n")
    c = tk.chk("net", "app", ["python3", "-c", code], consumes=["lib"])
    b = verify.verify_check(rid, c)
    assert b["verdict"] == "PASS" and store.load_cp(rid)["retries"]["app:net"] == 1
