"""One test per finding of the independent review of the first 4.0.0 build; each fails without its fix."""
import json
import os
import subprocess
import time
from pathlib import Path

import contract
import deps
import discover
import engine
import pytest
import release
import store
import testkit as tk
import verify
from contract import BLOCKED, PENDING, READY
from store import SdlcError
from test_runner_engine import GOOD, _owning, approved
from test_runner_release import land, pilot

# ---- 1 an empty or partial contract never reaches READY -------------------------------------------


def _run(tmp_path, checks, tasks, limits=None):
    repo = tk.make_repo(tmp_path, "app", {"feature.py": "x = 1\n"})
    return repo, tk.new_run(tmp_path / "home", repo, checks, tasks, limits=limits)


def test_approve_refuses_an_empty_contract_a_bare_milestone_and_an_unproven_task(tmp_path):
    _, rid = _run(tmp_path, [], {"milestones": []})
    with pytest.raises(SdlcError, match="no checks"):
        tk.approve(rid)
    one = {"milestones": [{"id": "m1", "repo": "app", "needs": [], "tasks": [{"id": "t1", "needs": []}]}]}
    _, rid = _run(tmp_path / "b", [tk.chk("x", "app", ["true"], count=False)], one)
    with pytest.raises(SdlcError, match="milestone m1 has no contract check"):
        tk.approve(rid)
    _, rid = _run(tmp_path / "c", [tk.chk("x", "app", ["true"], "m1", count=False)], one)
    with pytest.raises(SdlcError, match="task t1 has no check and no named waiver"):
        tk.approve(rid)
    one["milestones"][0]["tasks"][0]["waiver"] = "docs only"
    _, rid = _run(tmp_path / "d", [tk.chk("x", "app", ["true"], "m1", count=False)], one)
    assert tk.approve(rid)["digest"]


def test_an_empty_result_set_is_blocked_not_ready(tmp_path):
    _, rid = approved(tmp_path)
    code, first, _ = contract.evaluate(rid, repo="nobody")  # no check applies: nothing was proven
    assert code == BLOCKED and "empty result set" in first


def test_a_planner_contract_cannot_drop_the_discovered_full_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("SDLC_HOME", str(tmp_path / "home"))
    repo = tk.make_repo(tmp_path, "web", {"Makefile": "test:\n\ttrue\n"})
    rid = discover.plan([str(repo)], "x")
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"checks": [tk.chk("only", "web", ["true"], count=False)]}))
    discover.draft(rid, None, str(f), None, [], [])
    assert {c["id"] for c in store.read_json(store.run_dir(rid) / "contract.json")["checks"]} == {"only", "full:web"}
    f.write_text(json.dumps({"checks": [tk.chk("only", "web", ["true"], count=False)], "waive_full": ["web"]}))
    discover.draft(rid, None, str(f), None, [], [])
    assert {c["id"] for c in store.read_json(store.run_dir(rid) / "contract.json")["checks"]} == {"only"}


# ---- 3 READY reads the PRs' checks; the approval carries local_only_ok ----------------------------


def test_ready_waits_for_the_pr_checks_once_a_pr_exists(tmp_path, monkeypatch):
    repo, rid = approved(tmp_path)
    meta = store.load_meta(rid)
    head = contract.current_head(meta, "app")
    for c in store.read_json(store.run_dir(rid) / "contract.json")["checks"]:
        contract.write_receipt(rid, c, sha=head, verdict="PASS", exit_code=0, tests=1, base=None)
    assert contract.evaluate(rid)[0] == READY
    meta["prs"] = {"app": "https://example.test/pr/1"}  # what ci.open_pr records
    store.save_meta(rid, meta)
    monkeypatch.setattr("ci.gate", lambda rid, meta, heads: (PENDING, "check unit is still running"))
    code, first, _ = contract.evaluate(rid)
    assert code == PENDING and "unit" in first
    assert contract.evaluate(rid, skip_ci=True)[0] == READY


def test_approval_copies_local_only_ok_from_the_approved_contract(tmp_path):
    repo, rid = approved(tmp_path)
    assert store.load_meta(rid)["local_only_ok"] == []
    _, rid2 = _run(tmp_path / "b", [tk.chk("x", "app", ["true"], count=False)], {"milestones": []})
    d = store.run_dir(rid2)
    c = store.read_json(d / "contract.json")
    c["local_only_ok"] = ["app"]
    store.write_json(d / "contract.json", c)
    tk.approve(rid2)
    assert store.load_meta(rid2)["local_only_ok"] == ["app"]


# ---- 4 a PR (and auto-merge) only on local READY; a consumer waits for its producer ----------------


def test_pr_guard_refuses_until_the_repos_own_proof_is_ready_and_consumers_wait(tmp_path):
    lib, app, rid = pilot(tmp_path)
    with pytest.raises(SdlcError, match="not ready for a PR of lib"):
        engine.pr_guard(rid, "lib")  # nothing verified yet
    land(rid, "a", {"lib.py": "V = 2\n"})
    engine.close_milestone(rid, "m1")
    release.pack(rid, "lib")
    engine.next_batch(rid)
    land(rid, "b", {"app.py": "import lib\n"})
    engine.close_milestone(rid, "m2")
    engine.final_verify(rid)
    engine.pr_guard(rid, "lib")  # the producer may open its PR first
    with pytest.raises(SdlcError, match="awaits publication of lib"):
        engine.pr_guard(rid, "app")  # a consumer may not, before the producer is published and pinned


def test_the_pr_command_never_opens_a_pr_when_the_guard_refuses(tmp_path, monkeypatch):
    import ci
    import sdlc
    _, rid = approved(tmp_path)
    monkeypatch.setattr(ci, "open_pr", lambda *a, **k: pytest.fail("a PR was opened without READY proof"))
    monkeypatch.setattr(ci, "arm_auto_merge", lambda *a, **k: pytest.fail("auto-merge was armed without READY proof"))
    assert sdlc.main(["pr", rid, "app", "--auto-merge"]) == 2


# ---- 5 approval and restart need the owner's gate, once ---------------------------------------------


def test_approve_needs_the_gate_marker_for_this_exact_bundle_and_a_finite_cap(tmp_path):
    _, rid = _run(tmp_path, [tk.chk("x", "app", ["true"], count=False)], {"milestones": []})
    with pytest.raises(SdlcError, match="approval gate"):
        contract.approve(rid, "agent")  # an agent cannot approve on its own
    store.write_json(store.gate_marker(rid, "approve"), {"digest": "0" * 64})
    with pytest.raises(SdlcError, match="approval gate"):
        contract.approve(rid, "agent")  # a marker for another bundle
    _, rid2 = _run(tmp_path / "b", [tk.chk("x", "app", ["true"], count=False)], {"milestones": []})
    c = store.read_json(store.run_dir(rid2) / "contract.json")
    c["limits"].pop("max_dispatches")
    store.write_json(store.run_dir(rid2) / "contract.json", c)
    with pytest.raises(SdlcError, match="max_dispatches"):
        tk.approve(rid2)


def test_re_approval_is_refused_so_caps_and_deadline_cannot_be_reset(tmp_path):
    _, rid = approved(tmp_path)
    first = store.read_json(store.run_dir(rid) / "approval.json")
    with pytest.raises(SdlcError, match="already approved"):
        tk.approve(rid)
    assert store.read_json(store.run_dir(rid) / "approval.json") == first


def test_restart_needs_the_owner_gate(tmp_path):
    _, rid = approved(tmp_path)
    engine.stop(rid)
    with pytest.raises(SdlcError, match="only the owner restarts"):
        engine.restart(rid)
    tk.owner_restart(rid)
    engine.restart(rid)
    assert not store.is_stopped(rid) and not store.gate_marker(rid, "restart").exists()  # the marker is single use


# ---- 8 sdlc check is read-only; packing happens in a detached worktree ------------------------------


def test_check_never_runs_a_command_and_pack_uses_a_detached_worktree(tmp_path, monkeypatch):
    lib, app, rid = pilot(tmp_path)
    land(rid, "a", {"lib.py": "V = 2\n"})
    engine.close_milestone(rid, "m1")
    seen = []
    real = verify.run_job
    monkeypatch.setattr(verify, "run_job", lambda *a, **k: (seen.append(Path(a[3]).resolve()), real(*a, **k))[1])
    release.pack(rid, "lib")
    assert seen and all(".worktrees" in str(p) and p != lib.resolve() for p in seen)  # never the owner's checkout
    monkeypatch.setattr(verify, "run_job", lambda *a, **k: pytest.fail("sdlc check ran a command"))
    monkeypatch.setattr(release, "identity", lambda *a, **k: pytest.fail("sdlc check packed an artifact"))
    contract.evaluate(rid)


# ---- 9 pack and fetch: exact shapes -------------------------------------------------------------------


@pytest.mark.parametrize("argv", [["git", "ls-tree", "-r", "{ref}", "--evil"], ["git", "archive", "--output=x", "{ref}"], ["npm", "pack"],
                                  ["npm", "pack", "--ignore-scripts", "--pack-destination", "/tmp"], ["uv", "build"],
                                  ["python3", "-m", "build"], ["git", "ls-tree", "-r", "HEAD"]])
def test_pack_and_fetch_must_match_an_exact_shape(argv):
    e = {"producer": "lib", "consumer": "app", "pack": argv, "release": {"kind": "none"}}
    with pytest.raises(SdlcError, match="allowlist"):
        contract.validate_edges({"edges": [e]})
    assert contract.argv_allowed(["npm", "pack", "--ignore-scripts"]) and contract.argv_allowed(["git", "rev-parse", "{ref}"])


# ---- 10 publish touches only the pin line and only that path ---------------------------------------


def test_publish_commits_only_the_pin_file(tmp_path):
    lib, app, rid = pilot(tmp_path)
    land(rid, "a", {"lib.py": "V = 2\n"})
    engine.close_milestone(rid, "m1")
    release.pack(rid, "lib")
    tk.git(lib, "push", "-q", "origin", f"{store.load_meta(rid)['repos']['lib']['branch']}:main")
    pwt = engine.project_wt(rid, "app")
    (pwt / "stray.txt").write_text("not mine\n")
    (pwt / "notes.txt").write_text("edited\n")
    release.publish(rid, "lib")
    shown = tk.git(pwt, "show", "--name-only", "--format=", "HEAD").splitlines()
    assert shown == ["deps/lib.pin"] and (pwt / "stray.txt").exists()
    assert "stray.txt" in tk.git(pwt, "status", "--porcelain")  # still uncommitted


# ---- 11 dependencies: wired into the engine, inputs validated, config protected ------------------------


def _deps_repo(tmp_path):
    repo = tk.make_repo(tmp_path, "web", {"package.json": '{"dependencies": {}}\n', "src.js": "1\n"})
    tasks = {"milestones": [{"id": "m1", "repo": "web", "needs": [], "tasks": [{"id": "t1", "needs": [], "paths": ["src.js"], "waiver": "fixture"}]}]}
    rid = tk.new_run(tmp_path / "home", repo, [tk.chk("g", "web", ["python3", "-c", "import os,sys;sys.exit(0 if os.path.exists('installed') else 1)"],
                                                   "m1", count=False)], tasks)
    good = '{"dependencies": {"left-pad": "1.3.0"}}\n'
    d = store.run_dir(rid)
    (d / "deps" / "web").mkdir(parents=True)
    (d / "deps" / "web" / "package.json").write_text(good)
    c = store.read_json(d / "contract.json")
    c["deps"] = {"web": {"files": {"package.json": store.sha256(good)}}}
    store.write_json(d / "contract.json", c)
    tk.approve(rid)
    return repo, rid


def test_the_engine_applies_approved_dependencies_and_runs_the_frozen_install(tmp_path, monkeypatch):
    monkeypatch.setattr(deps, "frozen_install", lambda p: ["python3", "-c", "open('installed','w').write('1')"])
    repo, rid = _deps_repo(tmp_path)
    wt = engine.open_milestone(rid, "m1")
    assert "left-pad" in (wt / "package.json").read_text() and (wt / "installed").exists()  # applied, committed and installed
    assert "approved dependency change" in tk.git(wt, "log", "-1", "--format=%s")
    c = store.read_json(store.run_dir(rid) / "contract.json")["checks"][0]
    sha = tk.git(wt, "rev-parse", "HEAD")
    assert verify.verify_check(rid, c, ref=sha)["verdict"] == "PASS"  # a fresh verify checkout is installed too


def test_the_approval_screen_shows_the_real_manifest_diff(tmp_path):
    _, rid = _deps_repo(tmp_path)
    assert '+{"dependencies": {"left-pad": "1.3.0"}}' in discover.screen(rid).read_text()


@pytest.mark.parametrize("name", [".npmrc", ".pnpmfile.cjs", ".yarnrc.yml", "setup.cfg", "tsconfig.json", ".mocharc.json", "cypress.config.ts",
                                  "noxfile.py", ".coveragerc", "sub/tsconfig.base.json"])
def test_install_and_test_config_is_protected(tmp_path, name):
    _, rid = approved(tmp_path, tasks=_owning("feature.py", name))
    tk.build(rid, "t1", {**GOOD, name: "x\n"})
    with pytest.raises(SdlcError, match="protected path"):
        engine.submit(rid, "t1")


def test_draft_and_overlay_refuse_paths_that_escape(tmp_path, monkeypatch):
    monkeypatch.setenv("SDLC_HOME", str(tmp_path / "home"))
    repo = tk.make_repo(tmp_path, "web", {"a": "1"})
    rid = discover.plan([str(repo)], "x")
    src = tmp_path / "s.txt"
    src.write_text("x")
    for spec in (f"web:../../etc/x={src}", f"web:/abs={src}", f"nope:a={src}", f"web:a/../../b={src}"):
        with pytest.raises(SdlcError, match="relative path"):
            discover.draft(rid, None, None, None, [spec], [])
        with pytest.raises(SdlcError, match="relative path"):
            discover.draft(rid, None, None, None, [], [spec])
    with pytest.raises(SdlcError, match="not a relative path"):
        verify.overlay(rid, "web", tmp_path, {"../escape": "0"})


# ---- 12 guard_diff: runner entry, config, and per-test assertions -------------------------------------


def test_swapping_a_real_assertion_for_assert_true_is_rejected(tmp_path):
    other = "import unittest\nclass O(unittest.TestCase):\n    def test_a(self):\n        self.assertEqual(len('ab'), 2)\n        self.assertIn('a', 'abc')\n"
    _, rid = approved(tmp_path, extra_files={"tests/test_other.py": other}, tasks=_owning("feature.py", "tests/test_other.py"))
    swapped = other.replace("        self.assertIn('a', 'abc')\n", "        assert True\n")  # same count, one assertion gone
    tk.build(rid, "t1", {**GOOD, "tests/test_other.py": swapped})
    with pytest.raises(SdlcError, match="removed an assertion in test_a"):
        engine.submit(rid, "t1")


def test_the_runner_entry_the_contract_names_is_protected(tmp_path):
    repo = tk.make_repo(tmp_path, "app", {"feature.py": "x = 1\n", "run_checks.sh": "true\n", "Makefile": "test:\n\ttrue\n"})
    tasks = _owning("feature.py", "run_checks.sh", "Makefile")
    tasks["milestones"][0]["tasks"][0]["waiver"] = "fixture"
    rid = tk.new_run(tmp_path / "home", repo, [tk.chk("g", "app", ["make", "test"], "m1", count=False), tk.chk("h", "app", ["bash", "run_checks.sh"], "m1", count=False)], tasks)
    tk.approve(rid)
    tk.build(rid, "t1", {"run_checks.sh": "exit 0\n"})
    with pytest.raises(SdlcError, match="protected path run_checks.sh"):
        engine.submit(rid, "t1")
    store.update_cp(rid, lambda cp: cp["tasks"]["t1"].update(status="pending"))
    info = engine.dispatch(rid, "t1")
    wt = Path(info["worktree"])
    tk.git(wt, "checkout", "-q", info["base"], "--", "run_checks.sh")
    (wt / "Makefile").write_text("test:\n\ttrue # weakened\n")
    tk.git(wt, "add", "-A")
    tk.git(wt, "commit", "-qm", "make")
    with pytest.raises(SdlcError, match="protected path Makefile"):
        engine.submit(rid, "t1")


# ---- 13 dispatch decides readiness itself; submit stays inside the task's paths -------------------------


def test_dispatch_refuses_a_task_that_is_not_ready_and_a_builder_beyond_the_cap(tmp_path):
    doc = {"milestones": [{"id": "m1", "repo": "app", "needs": [], "tasks": [
        {"id": "a", "needs": [], "paths": ["a/"], "waiver": "f"}, {"id": "b", "needs": ["a"], "paths": ["b/"], "waiver": "f"},
        {"id": "c", "needs": [], "paths": ["c/"], "waiver": "f"}]}]}
    repo, rid = tk.feature_run(tmp_path, tasks=doc, limits={"builders": 1})
    tk.approve(rid)
    with pytest.raises(SdlcError, match="waits on a"):
        engine.dispatch(rid, "b")
    engine.dispatch(rid, "a")
    with pytest.raises(SdlcError, match="not ready for a dispatch"):
        engine.dispatch(rid, "a")  # already running
    with pytest.raises(SdlcError, match="builders are at their cap of 1"):
        engine.dispatch(rid, "c")


def test_submit_rejects_a_diff_outside_the_tasks_paths(tmp_path):
    _, rid = approved(tmp_path)
    tk.build(rid, "t1", {**GOOD, "elsewhere.py": "y = 2\n"})
    with pytest.raises(SdlcError, match="outside the paths this task owns"):
        engine.submit(rid, "t1")


# ---- 14 resume kills only what it started; finished runs leave the active folder -----------------------


def test_resume_does_not_kill_a_recycled_pid_but_does_kill_the_recorded_job(tmp_path):
    _, rid = approved(tmp_path)
    other = subprocess.Popen(["sleep", "30"], start_new_session=True)
    jobs = store.run_dir(rid) / "jobs"
    (jobs / "stale.pid").write_text(json.dumps({"pid": other.pid, "ident": "Thu Jan  1 00:00:00 1970 some other command"}))
    engine.resume(rid)
    time.sleep(0.3)
    assert other.poll() is None  # a different process now holds that PID: left alone
    (jobs / "mine.pid").write_text(json.dumps({"pid": other.pid, "ident": store.proc_ident(other.pid)}))
    engine.resume(rid)
    assert other.wait(timeout=10) is not None  # the recorded job is cancelled


def test_a_stopped_or_finished_run_is_removed_from_the_active_folder(tmp_path):
    _, rid = approved(tmp_path)
    link = store.home() / "active" / rid
    assert link.is_symlink()
    engine.stop(rid)
    assert not link.exists() and not link.is_symlink()
    tk.owner_restart(rid)
    engine.restart(rid)
    assert link.is_symlink()  # a restarted run is live again
    store.set_status(rid, "done")
    assert not link.is_symlink()


# ---- 20 candidate commands get a minimal environment ---------------------------------------------------


def test_candidate_commands_get_no_tokens_unless_the_contract_names_them(tmp_path, monkeypatch):
    _, rid = approved(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "k")
    monkeypatch.setenv("PROJECT_FLAG", "yes")
    probe = ["python3", "-c", "import os;print('Ran 1 tests');print(sorted(k for k in os.environ if k in ('GITHUB_TOKEN','AWS_SECRET_ACCESS_KEY','PROJECT_FLAG')))"]
    verify.verify_check(rid, tk.chk("e", "app", probe))
    log = (store.run_dir(rid) / "evidence" / "app--e.log").read_text()
    assert "[]" in log
    verify.verify_check(rid, tk.chk("e2", "app", probe, env=["PROJECT_FLAG"]))
    assert "PROJECT_FLAG" in (store.run_dir(rid) / "evidence" / "app--e2.log").read_text()
    assert os.environ["GITHUB_TOKEN"] == "secret-token" and "GITHUB_TOKEN" not in verify.clean_env()


# Output recorded from real `plannotator annotate <doc> --gate --json` runs (the log of each run begins with a Resolved: line).
REAL_APPROVED = 'Resolved: /x/plan.md\n{"decision":"approved"}\n'
REAL_DISMISSED = 'Folder: /x/changes\n{"decision":"dismissed"}\n'
REAL_ANNOTATED = 'Resolved: /x/plan.md\n{"decision":"annotated","feedback":"# File Feedback\\n\\nWhy S3?"}\n'


def test_the_gate_command_is_fixed_and_needs_an_explicit_approval_field(tmp_path, monkeypatch):
    _, rid = _run(tmp_path, [tk.chk("x", "app", ["true"], count=False)], {"milestones": []})
    monkeypatch.setenv("SDLC_GATE_CMD", "true")  # the old override: it must change nothing
    seen = []
    monkeypatch.setattr(discover, "GATE_RUN", lambda cmd: (seen.append(cmd), (0, "ok"))[1])
    assert discover.gate(rid) is False  # exit 0 without a decision is not an approval
    assert seen[0][:2] == ["plannotator", "annotate"] and seen[0][-2:] == ["--gate", "--json"] and "true" not in seen[0]
    assert not store.gate_marker(rid, "approve").exists()
    for said in (REAL_DISMISSED, REAL_ANNOTATED, 'The user approved. {"note": "approved"}', '{"decision": "not approved"}', "approved"):
        monkeypatch.setattr(discover, "GATE_RUN", lambda cmd, s=said: (0, s))
        assert discover.gate(rid) is False, said
    monkeypatch.setattr(discover, "GATE_RUN", lambda cmd: (1, REAL_APPROVED))
    assert discover.gate(rid) is False  # a failing exit never approves
    monkeypatch.setattr(discover, "GATE_RUN", lambda cmd: (0, REAL_APPROVED))
    assert discover.gate(rid) is True and store.gate_marker(rid, "approve").exists()
