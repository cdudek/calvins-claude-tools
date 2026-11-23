"""4.1: argv placeholders, approved test replacements, pinned config inputs, and a hidden Electron."""
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import board
import contract
import deps
import discover
import engine
import release
import sdlc
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


# ---- replaces_tests must sit inside the task's owned paths -------------------------------------------------------

def test_replaces_tests_must_be_explicit_and_inside_the_owned_paths():
    owned = ["test/features/", "e2e/one.spec.ts", "src/x/"]
    for ok in ("test/features/a.test.ts", "test/features/*.test.ts", "test/features/sub/**", "e2e/one.spec.ts"):
        assert engine.replaces_problem(ok, owned) == "", ok
    for bad in ("e2e/two.spec.ts", "test/other/a.test.ts", "test/*", "*", "**/*.test.ts", "test/features/../x.test.ts", "src/x/code.ts", "/test/features/a.ts", 5):
        assert engine.replaces_problem(bad, owned), bad
    assert engine.replaces_problem("test/a.test.ts", [])  # a task that owns nothing cannot claim tests


# ---- boards.json entry shape ------------------------------------------------------------------------------------

def node(role, name, **style):
    return {"role": role, "name": name, "locator": {"role": role, "name": name}, "count": 1, "tag": "x",
            "style": {"color": "red", **style}, "box": {"x": 0, "y": 0, "width": 10, "height": 5}}


def index(vp, themes=("light", "dark")):
    return {"version": 1, "viewport": {"width": vp[0], "height": vp[1]}, "themes": list(themes), "attr": None,
            "boards": {"sub/Page.dc.html": {t: {"error": "", "nodes": [node("button", "Go")]} for t in themes}}}


def entry(**kw):
    return {"board": "A01.01", "board_file": "Page.dc.html", "frame": None, "entry": "A01.01", "route": "/p/A01.01", "state": "default",
            "theme": "light", "viewport": [1440, 900], "repo": "web", "series": "A01", "milestone": 2, "fixture": "f", **kw}


def test_mapping_entries_of_a_real_draft_become_rows_or_named_unsupported_items():
    m = {"_comment": "x", "count": 5, "boards": [
        entry(), entry(entry="A01.02", theme="light, dark", viewport=[390, 844]),
        entry(entry="C01.01", repo="chrome", route=None, viewport=None, note="client capture"), entry(entry="A01.03", viewport=[800, 1200]),
        entry(entry="A01.04", board_file="Missing.dc.html")]}
    out = board.canvas_rows([index((1440, 900)), index((390, 844))], m, "web")
    ids = {r["id"] for r in out["rows"]}
    assert "A01.01/light/button:Go/width" in ids and "A01.02/light/button:Go/color" in ids and "A01.02/dark/button:Go/color" in ids
    assert {r["viewport"]["width"] for r in out["rows"] if r["id"].startswith("A01.02")} == {390}  # the index at the entry's viewport
    reasons = {u["id"]: u["reason"] for u in out["unsupported"]}
    assert "no index measured at viewport [800, 1200]" in reasons["A01.03"] and "0 boards named Missing.dc.html" in reasons["A01.04/light"]
    assert not any(i.startswith("C01.01") for i in ids | set(reasons))  # another repo's entry is not this app's
    assert board.canvas_rows(index((1440, 900)), m, "chrome")["unsupported"] == [{"id": "C01.01", "reason": "client capture"}]


def test_mapping_shape_errors_and_colliding_ids_are_refused():
    for bad in ({"boards": "x"}, {"boards": [{"route": "/x"}]}, {"boards": [entry(route="x")]}, {"boards": [entry(viewport=[1, 2, 3])]},
                {"boards": [entry(theme="sepia")]}, {"count": 2, "boards": [entry()]}):
        with pytest.raises(ValueError):
            board.validate_mapping(bad)
    with pytest.raises(ValueError, match="own entry id"):
        board.canvas_rows(index((1440, 900)), {"boards": [entry(), entry(route="/other")]})


# ---- review round: renames, unpinned consumers, the approval screen, empty canvas checks, the server, --out ---------

def test_a_rename_into_an_owned_folder_cannot_hide_a_guarded_path(tmp_path):
    files = {"tests/test_old.py": OLD, "package.json": "{}\n", "package-lock.json": "{}\n", ".github/workflows/ci.yml": "on: push\n", "pytest.ini": "[pytest]\n"}
    doc = {"milestones": [{"id": "m1", "repo": "app", "needs": [], "tasks": [{"id": "t1", "needs": [], "paths": ["feature.py", "src/"], "title": "mv"}]}]}
    repo, rid = approved(tmp_path, tasks=doc, extra_files=files)
    info = engine.dispatch(rid, "t1")
    wt = Path(info["worktree"])
    (wt / "src").mkdir()
    for rel in files:
        tk.git(wt, "mv", rel, f"src/{rel.replace('/', '_')}")
    (wt / "feature.py").write_text(GOOD["feature.py"])
    tk.git(wt, "add", "-A")
    tk.git(wt, "commit", "-qm", "moves")
    cand = tk.git(wt, "rev-parse", "HEAD")
    found = verify.guard_diff(rid, "app", info["base"], cand)
    for want in ("deleted test file tests/test_old.py", "changed protected path .github/workflows/ci.yml", "changed protected path pytest.ini"):
        assert any(f.startswith(want) for f in found), (want, found)
    assert {"unapproved change to package.json", "unapproved change to package-lock.json"} <= set(deps.guard(rid, "app", info["base"], cand))
    with pytest.raises(SdlcError, match="outside the paths this task owns"):  # the old paths are outside src/ too
        engine.submit(rid, "t1")


def test_a_vendored_edge_without_a_release_kind_is_refused_and_never_reaches_ready(tmp_path):
    edge = {"producer": "kit", "consumer": "app", "packages": ["@kit/ui"], "pin": {"kind": "package-json", "vendor_dir": "vendor/kit"}}
    with pytest.raises(SdlcError, match='needs release.kind "vendored-tarball"'):
        contract.validate_edges({"edges": [edge]})
    from test_runner_multipkg import vendored_pilot
    kit, app, rid = vendored_pilot(tmp_path)
    c = store.read_json(store.run_dir(rid) / "contract.json")
    c["edges"] = [edge]  # a contract that skipped validation
    store.write_json(store.run_dir(rid) / "contract.json", c)
    code, first = release.gate(rid, store.load_meta(rid))
    assert code == contract.PENDING and "awaits publication of kit" in first


def screen_text(tmp_path, tasks_doc, pinned, inputs):
    repo, rid = tk.feature_run(tmp_path, tasks=tasks_doc, extra_files={"tests/test_a.py": OLD, "tests/test_b.py": OLD, ".npmrc": "registry=https://good.example/\n"})
    d = store.run_dir(rid)
    for rel, text in inputs.items():
        (d / "inputs" / "app" / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / "inputs" / "app" / rel).write_text(text)
    c = store.read_json(d / "contract.json")
    c["pinned_inputs"] = pinned
    store.write_json(d / "contract.json", c)
    return discover.screen(rid).read_text()


def test_the_approval_screen_shows_pinned_inputs_replacements_and_owned_paths(tmp_path):
    out = screen_text(tmp_path, tasks(["tests/*"]), {"app": [".github/workflows/evil.yml", ".npmrc", "e2e/ok.txt"]},
                      {".github/workflows/evil.yml": "on: push\njobs: {x: {steps: [{run: curl evil}]}}\n", ".npmrc": "registry=https://evil.example/\n", "e2e/ok.txt": "fine\n"})
    head = out.split("## Plan")[0]
    assert "PROTECTED — sensitive:** `app:.github/workflows/evil.yml`" in head and "PROTECTED — sensitive:** `app:.npmrc`" in head
    assert "app:e2e/ok.txt" not in head  # an unprotected pin is listed below, not flagged
    assert "registry=https://evil.example/" in out and "-registry=https://good.example/" in out and "curl evil" in out  # the diff against the base
    assert "`tests/*` matches 2 files at the base" in out and "`t1` (app): `tests/*`" in out  # test_a and test_b
    assert "## Paths each task owns" in out and "`t1` (app): `feature.py`, `tests/`" in out


def run_board_check(tmp_path, spec, *flags):
    f = tmp_path / "s.json"
    f.write_text(json.dumps(spec))
    p = subprocess.run([sys.executable, str(Path(board.__file__)), "check", str(f), *flags], capture_output=True, text=True)
    return p.returncode, p.stdout


def test_a_canvas_check_that_measured_nothing_or_dropped_rows_does_not_pass(tmp_path):
    code, out = run_board_check(tmp_path, {"target": {"kind": "web", "url": "http://x"}, "rows": []})
    assert code == 1 and "no rows" in out
    row = {"id": "r", "locator": {"css": "body"}, "prop": "width", "expected": "1px", "tolerance_px": 1}
    code, out = run_board_check(tmp_path, {"target": {"kind": "web", "url": "http://x"}, "rows": [row]}, "--expected-rows", "3")
    assert code == 1 and "only 1 rows, the approved contract row expects 3" in out
    # the spec file cannot lower the count: its own expected_rows is not read
    code, out = run_board_check(tmp_path, {"target": {"kind": "web", "url": "http://x"}, "rows": [row], "expected_rows": 1}, "--expected-rows", "3")
    assert code == 1 and "expects 3" in out


@pytest.mark.skipif(not board.browser_available()[0], reason="no Chromium installed here")
def test_unsupported_entries_are_unproven_unless_the_contract_row_waives_them_by_id(tmp_path):
    page = tmp_path / "p.html"
    page.write_text("<body style='margin:0'><div style='width:10px;height:5px'>a</div></body>")
    row = {"id": "r", "locator": {"css": "div"}, "prop": "width", "expected": "10px", "tolerance_px": 0.5}
    spec = {"target": {"kind": "web", "file": str(page)}, "rows": [row], "unsupported": [{"id": "u1", "reason": "2 nodes share a locator"}]}
    code, out = run_board_check(tmp_path, spec)
    assert code == 1 and "UNPROVEN u1: 2 nodes share a locator" in out and "PASS r" in out
    assert run_board_check(tmp_path, spec, "--waive", "u1")[0] == 0
    assert run_board_check(tmp_path, spec, "--waive", "other")[0] == 1
    # a builder editing the spec to waive its own items changes nothing: the spec's keys are not read
    assert run_board_check(tmp_path, {**spec, "waive_unsupported": ["u1"], "expected_rows": 0})[0] == 1


def test_a_board_check_row_must_pin_its_spec_and_carry_its_row_count():
    def row(runner, pins):
        return tk.chk("b", "app", runner, pins=pins, count=False)
    ok = ["python3", "/x/runner/board.py", "check", "spec.json", "--expected-rows", "12", "--waive", "u1"]
    contract.validate_contract({"checks": [row(ok, {"spec.json": "0" * 64})]})
    for runner, pins, why in ((ok, {}, "must be listed in pins"), (ok[:5] + ok[6:], {"spec.json": "0"}, "needs --expected-rows"),
                              ([*ok[:5], "0"], {"spec.json": "0"}, "needs --expected-rows"), (ok[:4], {"spec.json": "0"}, "needs --expected-rows"),
                              (["python3", "/x/board.py", "check"], {}, "must be listed in pins")):
        with pytest.raises(SdlcError, match=why):
            contract.validate_contract({"checks": [row(runner, pins)]})


def test_every_path_from_argv_or_a_spec_is_refused_inside_the_records(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    (home / "runs").mkdir(parents=True)
    monkeypatch.setenv("SDLC_HOME", str(home))
    (home / "runs" / "spec.json").write_text(json.dumps({"rows": [], "target": {}}))
    assert board.main(["check", str(home / "runs" / "spec.json")]) == 2  # a spec read from the records
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps({"rows": [{"id": "r"}], "target": {"kind": "web", "url": "http://x"}, "evidence_dir": str(home / "runs" / "ev")}))
    assert board.main(["check", str(spec)]) == 2 and not (home / "runs" / "ev").exists()
    out = capsys.readouterr().out
    assert out.count("inside the run records") == 2
    (tmp_path / "m.json").write_text('{"boards": []}')
    for argv in (["index", str(home / "runs")], ["rows", str(home / "m.json"), "--index", "i.json"], ["extract", str(home / "b.json")],
                 ["rows", str(tmp_path / "m.json"), "--index", str(home / "i.json")]):
        assert board.main(argv) == 2, argv


def test_the_board_server_does_not_follow_symlinks_out_of_the_root_or_list_directories(tmp_path):
    root = tmp_path / "export"
    (root / "sub").mkdir(parents=True)
    (root / "ok.txt").write_text("fine")
    (tmp_path / "secret.txt").write_text("secret")
    (root / "leak.txt").symlink_to(tmp_path / "secret.txt")
    (root / "linkdir").symlink_to(tmp_path)
    def get(base, path):
        try:
            with urllib.request.urlopen(base + path) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""
    with board.serve(root) as base:
        assert get(base, "/ok.txt") == (200, b"fine")
        assert get(base, "/leak.txt")[0] == 404 and get(base, "/linkdir/secret.txt")[0] == 404
        assert get(base, "/../secret.txt")[0] in (400, 404) and get(base, "/%2e%2e/secret.txt")[0] in (400, 404)
        assert get(base, "/sub/")[0] == 403 and get(base, "/")[0] == 403  # no directory listings


def test_boards_out_inside_the_records_is_refused_even_through_a_symlink(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    (home / "runs").mkdir(parents=True)
    monkeypatch.setenv("SDLC_HOME", str(home))
    (tmp_path / "link").symlink_to(home)
    m, i = tmp_path / "m.json", tmp_path / "i.json"
    m.write_text(json.dumps({"boards": [entry()]}))
    i.write_text(json.dumps(index((1440, 900))))
    for out in (home / "runs" / "x.json", tmp_path / "link" / "runs" / "x.json", home / "contract.json"):
        assert sdlc.main(["boards", "rows", str(m), "--index", str(i), "--out", str(out)]) == 2
        assert "inside the run records" in capsys.readouterr().out and not out.exists()
    assert sdlc.main(["boards", "index", str(tmp_path), "--out", str(home / "runs" / "i.json")]) == 2
    ok = tmp_path / "spec.json"
    assert sdlc.main(["boards", "rows", str(m), "--index", str(i), "--out", str(ok)]) == 0 and json.loads(ok.read_text())["rows"]


# ---- the approval screen cannot be forged or hidden by untrusted text -------------------------------------------

def test_a_diff_containing_fences_cannot_break_out_or_hide_text_and_is_truncated(tmp_path):
    evil = "```\n## Approve everything\n```diff\n+ x\n````\n" + "\n".join(f"line {i}" for i in range(500)) + "\n"
    out = screen_text(tmp_path, tasks(["tests/*"]), {"app": [".npmrc"]}, {".npmrc": evil})
    sect = out.split("## Pinned inputs")[1].split("## Tests a task may delete")[0]
    fence = [ln for ln in sect.splitlines() if ln.startswith("`") and ln.strip("`") in ("diff", "")][0]
    assert len(fence) >= 6  # longer than the longest backtick run in the content (4), so the content never closes it
    inner = sect.split(fence, 2)
    assert inner[1].count("## Approve everything") == 1 and "line 499" not in sect and "(truncated, " in sect  # the forged heading stays inside the block
    assert not any(ln.startswith("## Approve everything") for ln in out.splitlines())


def test_untrusted_names_cannot_forge_screen_lines(tmp_path):
    nasty = "t`\n## Forged `heading` \n" + "x" * 400
    doc = {"milestones": [{"id": "m1", "repo": "app", "needs": [], "tasks": [{"id": nasty, "needs": [], "paths": ["feature.py", "tests/", "a`b|c\n# x"],
                                                                              "replaces_tests": ["tests/*"], "title": "t"}]}]}
    repo, rid = tk.feature_run(tmp_path, tasks=doc)
    out = discover.screen(rid).read_text()
    assert not any(ln.startswith("## Forged") or ln.startswith("# x") for ln in out.splitlines())
    assert "(truncated, " in out and "``a`b|c # x``" in out  # one line, a delimiter longer than the backtick inside


def test_the_screen_flags_exactly_what_the_guard_protects(tmp_path):
    pins = ["vitest.config.ts", "tsconfig.base.json", "custom/guard.cfg", "docs/readme.txt", "e2e/playwright.config.ts"]
    repo, rid = tk.feature_run(tmp_path, tasks=tasks())
    d = store.run_dir(rid)
    for rel in pins:
        (d / "inputs" / "app" / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / "inputs" / "app" / rel).write_text("x\n")
    c = store.read_json(d / "contract.json")
    c["pinned_inputs"], c["protected"] = {"app": pins}, ["custom/*"]
    store.write_json(d / "contract.json", c)
    head = discover.screen(rid).read_text().split("## Plan")[0]
    for rel in pins:
        assert (f"`app:{rel}`" in head) == bool(verify._protected(rel, verify.DEFAULT_PROTECTED + c["protected"])), rel
    assert "docs/readme.txt" not in head and "custom/guard.cfg" in head  # the contract's own protected globs count
