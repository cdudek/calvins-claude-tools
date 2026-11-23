"""4.1: argv placeholders, approved test replacements, pinned config inputs, and a hidden Electron."""
import shutil
import subprocess
from pathlib import Path

import board
import engine
import pytest
import store
import testkit as tk
import verify
from store import SdlcError
from test_runner_engine import GOOD, approved

OLD = "import unittest\nclass O(unittest.TestCase):\n    def test_old(self):\n        self.assertEqual(1, 1)\n"
NEW = "import unittest\nclass N(unittest.TestCase):\n    def test_new(self):\n        self.assertEqual(2, 2)\n"


# ---- 7 named placeholders only ----------------------------------------------------------------------------------

def test_only_base_head_and_producer_sha_are_substituted_with_full_shas(tmp_path):
    repo, rid = approved(tmp_path)
    head, base = tk.git(repo, "rev-parse", store.load_meta(rid)["repos"]["app"]["branch"]), store.load_meta(rid)["repos"]["app"]["base_sha"]
    out = verify.resolve_argv(rid, ["x", "{head}", "a-{base}", "{producer_sha:app}", "{other}", "{'k': 1}", "$(id)", "{producer_sha:app;id}"], head, base)
    assert out == ["x", head, f"a-{base}", head, "{other}", "{'k': 1}", "$(id)", "{producer_sha:app;id}"] and len(head) == 40
    with pytest.raises(SdlcError, match="names a repo that is not in this run"):
        verify.resolve_argv(rid, ["{producer_sha:nope}"], head, base)


def test_a_check_runs_with_the_resolved_shas(tmp_path):
    repo, rid = tk.feature_run(tmp_path)
    c = store.read_json(store.run_dir(rid) / "contract.json")
    c["checks"].append(tk.chk("args", "app", ["python3", "-c", "import sys; print('Ran 1 tests'); print('ARGS', *sys.argv[1:])", "{head}", "{base}", "{producer_sha:app}"],
                              "m1", pins={}))
    store.write_json(store.run_dir(rid) / "contract.json", c)
    rec = verify.verify_check(rid, c["checks"][-1])
    assert rec["verdict"] == "PASS"
    head = tk.git(repo, "rev-parse", store.load_meta(rid)["repos"]["app"]["branch"])
    log = (store.run_dir(rid) / "evidence" / "app--args.log").read_text()
    assert f"ARGS {head} {store.load_meta(rid)['repos']['app']['base_sha']} {head}" in log


# ---- 8 approved test replacements -------------------------------------------------------------------------------

def tasks(replaces=None):
    t = {"id": "t1", "needs": [], "paths": ["feature.py", "tests/"], "title": "rewrite"}
    if replaces is not None:
        t["replaces_tests"] = replaces
    return {"milestones": [{"id": "m1", "repo": "app", "needs": [], "tasks": [t]}]}


def rewrite(rid, delete, add):
    """What a builder does for a greenfield rewrite: delete old tests, add new ones, commit."""
    info = engine.dispatch(rid, "t1")
    wt = Path(info["worktree"])
    for rel in delete:
        tk.git(wt, "rm", "-q", rel)
    for rel, text in {**GOOD, **add}.items():
        (wt / rel).parent.mkdir(parents=True, exist_ok=True)
        (wt / rel).write_text(text)
    tk.git(wt, "add", "-A")
    tk.git(wt, "commit", "-qm", "rewrite")


def test_a_declared_replacement_may_delete_and_rewrite_exactly_those_tests(tmp_path):
    _, rid = approved(tmp_path, tasks=tasks(["tests/test_old*.py", "tests/legacy/*"]),
                      extra_files={"tests/test_old.py": OLD, "tests/legacy/test_a.py": OLD, "tests/test_keep.py": OLD})
    rewrite(rid, ["tests/test_old.py", "tests/legacy/test_a.py"], {"tests/test_new.py": NEW})
    assert engine.submit(rid, "t1")  # no tamper findings, and the contract's own check rows still decide the verdict later
    res = engine.verify_task(rid, "t1")
    assert all(r["verdict"] == "PASS" for r in res)


def test_a_test_outside_the_declaration_still_cannot_be_deleted_or_weakened(tmp_path):
    _, rid = approved(tmp_path, tasks=tasks(["tests/test_old.py"]), extra_files={"tests/test_old.py": OLD, "tests/test_keep.py": OLD})
    rewrite(rid, ["tests/test_old.py", "tests/test_keep.py"], {})
    with pytest.raises(SdlcError, match="deleted test file tests/test_keep.py"):
        engine.submit(rid, "t1")
    _, rid2 = approved(tmp_path / "b", tasks=tasks(), extra_files={"tests/test_old.py": OLD})  # nothing declared
    rewrite(rid2, ["tests/test_old.py"], {})
    with pytest.raises(SdlcError, match="deleted test file tests/test_old.py"):
        engine.submit(rid2, "t1")


def test_a_replacement_cannot_cover_a_pinned_spec_add_a_skip_or_name_a_non_test_path(tmp_path):
    _, rid = approved(tmp_path, tasks=tasks(["tests/*"]))
    rewrite(rid, [], {"tests/test_feature.py": "x = 1\n"})  # the pinned acceptance spec
    with pytest.raises(SdlcError, match="changed pinned input tests/test_feature.py"):
        engine.submit(rid, "t1")
    _, rid2 = approved(tmp_path / "b", tasks=tasks(["tests/*"]), extra_files={"tests/test_old.py": OLD})
    rewrite(rid2, ["tests/test_old.py"], {"tests/test_new.py": NEW.replace("    def test_new", "    @unittest.skip('x')\n    def test_new")})
    with pytest.raises(SdlcError, match="added a skip"):
        engine.submit(rid2, "t1")
    for bad in (["src/**"], ["../tests/x.py"], ["/tests/x.py"], ["*"]):
        repo, rid3 = tk.feature_run(tmp_path / ("c" + str(len(bad[0]))), tasks=tasks(bad))
        with pytest.raises(SdlcError, match="replaces_tests"):
            engine.validate_plan(rid3)


# ---- 10 pinned config inputs ------------------------------------------------------------------------------------

CFG = "export default { testDir: 'e2e' }\n"


def pinned_run(tmp_path):
    repo, rid = tk.feature_run(tmp_path, tasks=tasks())
    d = store.run_dir(rid)
    (d / "inputs" / "app").mkdir(parents=True, exist_ok=True)
    (d / "inputs" / "app" / "playwright.config.ts").write_text(CFG)
    c = store.read_json(d / "contract.json")
    c["pinned_inputs"] = {"app": ["playwright.config.ts"]}
    store.write_json(d / "contract.json", c)
    engine.validate_plan(rid)
    tk.approve(rid)
    return repo, rid


def test_the_runner_writes_pinned_config_before_the_first_dispatch_and_a_builder_cannot_touch_it(tmp_path):
    repo, rid = pinned_run(tmp_path)
    info = engine.dispatch(rid, "t1")
    wt = Path(info["worktree"])
    assert (wt / "playwright.config.ts").read_text() == CFG  # present at the integration SHA the builder starts from
    (wt / "playwright.config.ts").write_text("export default {}\n")
    (wt / "feature.py").write_text(GOOD["feature.py"])
    tk.git(wt, "add", "-A")
    tk.git(wt, "commit", "-qm", "touch")
    with pytest.raises(SdlcError, match="changed pinned input playwright.config.ts"):
        engine.submit(rid, "t1")
    tk.git(wt, "checkout", "-q", info["base"], "--", "playwright.config.ts")
    tk.git(wt, "commit", "-qm", "restore")
    # an unpinned config file stays refused
    (wt / "vitest.config.ts").write_text("x\n")
    tk.git(wt, "add", "-A")
    tk.git(wt, "commit", "-qm", "v")
    with pytest.raises(SdlcError, match="protected path vitest.config.ts"):
        engine.submit(rid, "t1")


def test_a_check_checkout_gets_the_approved_bytes_even_if_the_head_was_altered(tmp_path):
    repo, rid = pinned_run(tmp_path)
    tk.commit_file(repo, "x.txt", "1\n")  # a head with no config at all: the checkout still gets the approved copy
    chk = tk.chk("cfg", "app", ["python3", "-c", "from pathlib import Path; print('Ran 1 tests'); "
                                f"raise SystemExit(0 if Path('playwright.config.ts').read_text() == {CFG!r} else 1)"], "m1")
    assert verify.verify_check(rid, chk)["verdict"] == "PASS"


def test_approval_needs_the_pinned_file_among_the_inputs(tmp_path):
    repo, rid = tk.feature_run(tmp_path, tasks=tasks())
    c = store.read_json(store.run_dir(rid) / "contract.json")
    c["pinned_inputs"] = {"app": ["playwright.config.ts"]}
    store.write_json(store.run_dir(rid) / "contract.json", c)
    with pytest.raises(SdlcError, match="pinned_inputs app:playwright.config.ts"):
        tk.approve(rid)


# ---- 9 Electron runs hidden -------------------------------------------------------------------------------------

def test_electron_launch_is_hidden_and_the_shim_makes_every_window_unfocusable(tmp_path):
    args, env = board.electron_hidden("main.js")
    assert args[0] == "--require" and args[-1].endswith("main.js") and "--disable-renderer-backgrounding" in args and env["SDLC_HIDDEN"] == "1"
    if not shutil.which("node"):
        pytest.skip("node is not installed here")
    fake = tmp_path / "node_modules" / "electron"
    fake.mkdir(parents=True)
    (fake / "index.js").write_text("class BrowserWindow { constructor(o){ this.o = o; } show(){ this.shown = true; } focus(){ this.focused = true; } }\n"
                                   "module.exports = { BrowserWindow, app: { dock: { hide(){ global.dockHidden = true; } } } };\n")
    (tmp_path / "t.js").write_text("require(%r);\nconst e = require('electron'); const w = new e.BrowserWindow({show: true});\nw.show(); w.focus();\n"
                                   "console.log(JSON.stringify([w.o, w.shown, w.focused, process.platform === 'darwin' ? global.dockHidden : true]));\n" % args[1])
    out = subprocess.run(["node", "t.js"], cwd=tmp_path, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == '[{"show":false,"focusable":false,"skipTaskbar":true},null,null,true]'
