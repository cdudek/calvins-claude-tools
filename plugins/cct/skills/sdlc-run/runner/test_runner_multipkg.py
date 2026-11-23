"""4.1: several packages per release edge, vendored tarballs, the runner-made npm pin, and the builder cap."""
import json
import shutil

import contract
import deps
import engine
import pytest
import release
import store
import testkit as tk
from contract import PENDING, READY
from store import SdlcError
from test_runner_release import land

needs_npm = pytest.mark.skipif(not shutil.which("npm"), reason="npm is not installed here")
PKGS = ["@kit/annotations", "@kit/ui"]
# the consumer's gate: it saw the packed artifact, and once the tarballs are vendored they must be what node_modules holds
GATE = ["python3", "-c", "import os,sys\nfrom pathlib import Path\nok='SDLC_ARTIFACT_KIT' in os.environ\n"
        "if Path('vendor/kit').is_dir(): ok = ok and Path('node_modules/@kit/ui/package.json').is_file()\nprint('Ran 1 tests')\nsys.exit(0 if ok else 1)"]


def pkg(name, version="1.0.0", **extra):
    return json.dumps({"name": name, "version": version, "main": "i.js", **extra}) + "\n"


def kit_files(ui_js="y\n"):
    return {"package.json": '{"name":"kit","private":true,"workspaces":["packages/*"]}\n',
            "packages/annotations/package.json": pkg("@kit/annotations"), "packages/annotations/i.js": "x\n",
            "packages/ui/package.json": pkg("@kit/ui", dependencies={"@kit/annotations": "1.0.0"}), "packages/ui/i.js": ui_js}


def consumer_manifest(ann="^0.9.0", ui="^0.9.0"):
    return json.dumps({"name": "app", "version": "0.0.1", "private": True, "dependencies": {"@kit/annotations": ann, "@kit/ui": ui}}, indent=2) + "\n"


def vendored_pilot(tmp_path, app_files=None, consumers=("app",), edge=None, deps_block=None):
    kit = tk.make_repo(tmp_path, "kit", kit_files(), remote=True)
    rid = tk.new_run(tmp_path / "home", kit, [])
    meta = store.load_meta(rid)
    d = store.run_dir(rid)
    waiver = "covered by the milestone gate"
    ms = [{"id": "m1", "repo": "kit", "needs": [], "tasks": [{"id": "a", "needs": [], "paths": ["packages/ui"], "waiver": waiver}]}]
    checks, edges = [tk.chk("kit-gate", "kit", ["python3", "-c", "print('Ran 1 tests')"], "m1")], []
    for i, name in enumerate(consumers):
        app = tk.make_repo(tmp_path, name, app_files or {"package.json": consumer_manifest(), "src.js": "1\n"}, remote=True)
        tk.git(app, "branch", f"sdlc/{rid}", "main")
        meta["repos"][name] = {"path": str(app), "base_sha": tk.git(app, "rev-parse", "main"), "branch": f"sdlc/{rid}", "default_branch": "main"}
        ms.append({"id": f"m{i + 2}", "repo": name, "needs": ["m1"], "tasks": [{"id": f"b{i}", "needs": [], "paths": ["src.js"], "waiver": waiver}]})
        checks.append(tk.chk(f"{name}-gate", name, GATE, f"m{i + 2}", consumes=["kit"]))
        edges.append(edge or {"producer": "kit", "consumer": name, "packages": PKGS, "release": {"kind": contract.VENDORED}, "pin": {"dir": "vendor/kit"}})
        edges[-1] = {**edges[-1], "consumer": name}
    store.save_meta(rid, meta)
    store.write_json(d / "tasks.json", {"milestones": ms})
    store.write_json(d / "contract.json", {"checks": checks, "edges": edges, "limits": {"max_dispatches": 20}, **({"deps": deps_block} if deps_block else {})})
    engine.validate_plan(rid)
    tk.approve(rid)
    return kit, tk_repo(meta, "app"), rid


def tk_repo(meta, name):
    from pathlib import Path
    return Path(meta["repos"][name]["path"])


def publish_ready(kit, rid):
    """The owner merged the producer PR: main on the remote moves to the run branch."""
    engine.push(rid, "kit")
    tk.git(kit, "push", "-q", "origin", f"{store.load_meta(rid)['repos']['kit']['branch']}:main")


# ---- gap 1: the allowlist and the per-package identity ------------------------------------------------------------

def test_workspace_pack_is_allowlisted_and_names_are_validated():
    ok = ["npm", "pack", "--ignore-scripts", "--workspace", "@kit/ui"]
    assert contract.argv_allowed(ok) and contract.argv_allowed([*ok[:4], "plain-name"])
    for bad in (["npm", "pack", "--workspace", "@kit/ui"],  # scripts on
                ["npm", "pack", "--ignore-scripts", "--workspace", "--foo"], ["npm", "pack", "--ignore-scripts", "--workspace", "../x"],
                ["npm", "pack", "--ignore-scripts", "--workspace", "a b"], ["npm", "pack", "--ignore-scripts", "--workspace", "x\n"],
                ["npm", "pack", "--ignore-scripts", "--workspace", "a", "--workspace", "b"], ["pnpm", "pack"], ["npm", "publish"],
                ["npm", "pack", "--ignore-scripts", "--workspace", 5]):
        assert not contract.argv_allowed(bad), bad
    base = {"producer": "kit", "consumer": "app", "release": {"kind": contract.VENDORED}, "pin": {"dir": "vendor/kit"}}
    contract.validate_edges({"edges": [{**base, "packages": PKGS}]})
    for bad_pk in ([], ["-x"], ["a", "a"], "ui", ["../ui"]):
        with pytest.raises(SdlcError, match="packages"):
            contract.validate_edges({"edges": [{**base, "packages": bad_pk}]})
    for bad_pin in ({"dir": "../v"}, {"dir": "/v"}, {"dir": "v", "manifest": "../package.json"}, {"dir": "v", "manifest": "pkg.json"}, {}):
        with pytest.raises(SdlcError, match="pin.dir"):
            contract.validate_edges({"edges": [{**base, "packages": PKGS, "pin": bad_pin}]})
    with pytest.raises(SdlcError, match="needs packages"):
        contract.validate_edges({"edges": [{**base, "pack": ok}]})


@needs_npm
def test_identity_is_a_digest_per_package_and_a_combined_digest(tmp_path):
    kit, app, rid = vendored_pilot(tmp_path)
    a = release.pack(rid, "kit")
    b = release.identity(rid, store.read_json(store.run_dir(rid) / "contract.json")["edges"][0], "main")
    assert set(a["packages"]) == set(PKGS) and a["packages"]["@kit/ui"]["file"] == "kit-ui-1.0.0.tgz"
    assert a == {**b, "dir": a["dir"]} and a["digest"] == store.sha256(store.canon({n: p["digest"] for n, p in a["packages"].items()}))
    tk.commit_file(kit, "packages/ui/i.js", "changed\n")
    store.update_cp(rid, lambda cp: None)
    c = release.identity(rid, store.read_json(store.run_dir(rid) / "contract.json")["edges"][0], "main")
    assert c["packages"]["@kit/annotations"] == a["packages"]["@kit/annotations"]  # untouched package, same bytes
    assert c["packages"]["@kit/ui"]["digest"] != a["packages"]["@kit/ui"]["digest"] and c["digest"] != a["digest"]


# ---- gap 2: publish -> pin -> verify -> READY ---------------------------------------------------------------------

@needs_npm
def test_two_package_workspace_publish_pin_verify_ready(tmp_path):
    kit, app, rid = vendored_pilot(tmp_path)
    land(rid, "a", {"packages/ui/i.js": "z\n"})
    assert engine.close_milestone(rid, "m1")["status"] == "merged"
    ident = release.pack(rid, "kit")
    assert (store.run_dir(rid) / "artifacts" / "kit" / "kit-ui-1.0.0.tgz").is_file()
    land(rid, "b0", {"src.js": "2\n"})
    assert engine.close_milestone(rid, "m2")["status"] == "merged"
    engine.final_verify(rid)
    code, first, _ = contract.evaluate(rid)
    assert code == PENDING and "awaits publication of kit" in first
    publish_ready(kit, rid)
    rec = release.publish(rid, "kit")
    assert rec["digest"] == ident["digest"]
    branch = store.load_meta(rid)["repos"]["app"]["branch"]
    man = json.loads(tk.git(app, "show", f"{branch}:package.json"))
    assert man["dependencies"] == {"@kit/annotations": "file:vendor/kit/kit-annotations-1.0.0.tgz", "@kit/ui": "file:vendor/kit/kit-ui-1.0.0.tgz"}
    lock = json.loads(tk.git(app, "show", f"{branch}:package-lock.json"))
    assert lock["packages"]["node_modules/@kit/ui"]["resolved"] == "file:vendor/kit/kit-ui-1.0.0.tgz"
    assert "integrity" in lock["packages"]["node_modules/@kit/ui"]
    files = set(tk.git(app, "ls-tree", "-r", "--name-only", branch).splitlines())
    assert {"vendor/kit/kit-ui-1.0.0.tgz", "vendor/kit/kit-annotations-1.0.0.tgz", "package-lock.json"} <= files
    # the runner recorded exactly these bytes as the approved ones
    recd = deps.pin_record(rid, "app")
    assert set(recd) == {"package.json", "package-lock.json", "vendor/kit/kit-ui-1.0.0.tgz", "vendor/kit/kit-annotations-1.0.0.tgz"}
    assert recd["vendor/kit/kit-ui-1.0.0.tgz"] == ident["packages"]["@kit/ui"]["digest"]
    assert contract.evaluate(rid)[0] == PENDING  # the pin moved the consumer head
    engine.final_verify(rid)  # the consumer gate now runs against the vendored files: npm ci puts them in node_modules
    code, first, _ = contract.evaluate(rid)
    assert code == READY, first
    # the guard accepts the pinned bytes and refuses any other drift
    base = store.load_meta(rid)["repos"]["app"]["base_sha"]
    cand = tk.git(app, "rev-parse", branch)
    assert deps.guard(rid, "app", base, cand) == []
    lock["packages"]["node_modules/@kit/ui"]["integrity"] = "sha512-evil"
    bad = tk.commit_file(engine.project_wt(rid, "app"), "package-lock.json", json.dumps(lock))
    assert any("package-lock.json differs from the approved" in b for b in deps.guard(rid, "app", cand, bad))
    other = tk.commit_file(engine.project_wt(rid, "app"), "vendor/kit/kit-ui-1.0.0.tgz", "swapped")
    assert any("vendor/kit/kit-ui-1.0.0.tgz differs" in b for b in deps.guard(rid, "app", bad, other))
    stray = tk.commit_file(engine.project_wt(rid, "app"), "vendor/kit/extra.tgz", "x")
    assert any("unapproved change to vendor/kit/extra.tgz" in b for b in deps.guard(rid, "app", other, stray))
    assert contract.evaluate(rid)[0] == PENDING  # a head that moved is no longer proven


@needs_npm
def test_a_package_that_differs_after_publication_is_named(tmp_path):
    kit, app, rid = vendored_pilot(tmp_path)
    land(rid, "a", {"packages/ui/i.js": "z\n"})
    engine.close_milestone(rid, "m1")
    release.pack(rid, "kit")
    tk.commit_file(kit, "packages/annotations/i.js", "sneaky\n")  # what lands on main is not what was packed
    tk.git(kit, "push", "-q", "origin", "main:main")
    with pytest.raises(SdlcError, match=r"kit \(package @kit/annotations\) differs from the packed"):
        release.publish(rid, "kit")
    assert deps.pin_record(rid, "app") == {}


@needs_npm
def test_a_failing_lockfile_step_leaves_the_consumer_untouched(tmp_path, monkeypatch):
    kit, app, rid = vendored_pilot(tmp_path)
    land(rid, "a", {"packages/ui/i.js": "z\n"})
    engine.close_milestone(rid, "m1")
    release.pack(rid, "kit")
    publish_ready(kit, rid)
    monkeypatch.setattr(release, "LOCK", ["python3", "-c", "import sys; print('ENOTCACHED'); sys.exit(1)"])
    with pytest.raises(SdlcError, match="BLOCKED env the lockfile of app could not be rewritten offline"):
        release.publish(rid, "kit")
    pwt = engine.project_wt(rid, "app")
    assert tk.git(pwt, "status", "--porcelain") == "" and not (pwt / "vendor").exists()
    assert deps.pin_record(rid, "app") == {}


@needs_npm
def test_an_old_vendored_tarball_is_replaced_and_a_missing_dependency_is_a_plan_error(tmp_path):
    old = consumer_manifest("file:vendor/kit/kit-annotations-0.9.0.tgz", "file:vendor/kit/kit-ui-0.9.0.tgz")
    kit, app, rid = vendored_pilot(tmp_path, {"package.json": old, "vendor/kit/kit-ui-0.9.0.tgz": "old", "vendor/kit/kit-annotations-0.9.0.tgz": "old",
                                              "src.js": "1\n"})
    land(rid, "a", {"packages/ui/i.js": "z\n"})
    engine.close_milestone(rid, "m1")
    release.pack(rid, "kit")
    publish_ready(kit, rid)
    release.publish(rid, "kit")
    branch = store.load_meta(rid)["repos"]["app"]["branch"]
    files = set(tk.git(app, "ls-tree", "-r", "--name-only", branch).splitlines())
    assert "vendor/kit/kit-ui-0.9.0.tgz" not in files and "vendor/kit/kit-ui-1.0.0.tgz" in files
    assert "vendor/kit/kit-ui-0.9.0.tgz" not in deps.pin_record(rid, "app")
    # a consumer that does not depend on a declared package has nothing to pin
    kit2, app2, rid2 = vendored_pilot(tmp_path / "b", {"package.json": '{"name":"app","dependencies":{"@kit/ui":"^0.9.0"}}\n', "src.js": "1\n"})
    land(rid2, "a", {"packages/ui/i.js": "z\n"})
    engine.close_milestone(rid2, "m1")
    release.pack(rid2, "kit")
    publish_ready(kit2, rid2)
    with pytest.raises(SdlcError, match="does not depend on @kit/annotations"):
        release.publish(rid2, "kit")


def test_gate_is_pending_when_the_consumer_head_lacks_the_pinned_bytes(tmp_path):
    kit, app, rid = vendored_pilot(tmp_path)
    store.update_cp(rid, lambda cp: (cp.setdefault("artifacts", {}).__setitem__("kit", {"source": tk.git(kit, "rev-parse", store.load_meta(rid)["repos"]["kit"]["branch"]), "digest": "d"}),
                                      cp.setdefault("release", {}).__setitem__("kit", {"digest": "d", "consumers": {"app": {"files": {"package.json": "0" * 64}}}})))
    code, first = release.gate(rid, store.load_meta(rid))
    assert code == PENDING and "does not carry the pin for kit" in first


# ---- gap 4: the builder cap -----------------------------------------------------------------------------------

def test_builder_cap_defaults_to_8_and_the_contract_may_set_up_to_10(tmp_path):
    repo, rid = tk.feature_run(tmp_path)
    assert engine.lim(rid)["builders"] == 8
    for n in (1, 10):
        contract.validate_contract({"limits": {"builders": n}})
    for bad in (0, 11, -1, 2.5, "8", True):
        with pytest.raises(SdlcError, match="limits.builders"):
            contract.validate_contract({"limits": {"builders": bad}})
    c = store.read_json(store.run_dir(rid) / "contract.json")
    c["limits"]["builders"] = 10
    store.write_json(store.run_dir(rid) / "contract.json", c)
    assert engine.lim(rid)["builders"] == 10
    c["limits"]["builders"] = 50  # tampered after approval: the runtime clamp still holds
    store.write_json(store.run_dir(rid) / "contract.json", c)
    assert engine.lim(rid)["builders"] == 10


@needs_npm
def test_one_producer_with_three_consumers_is_packed_once_and_pinned_in_each(tmp_path):
    kit, app, rid = vendored_pilot(tmp_path, consumers=("app", "ext", "mac"))
    land(rid, "a", {"packages/ui/i.js": "z\n"})
    engine.close_milestone(rid, "m1")
    ident = release.pack(rid, "kit")
    for i, name in enumerate(("app", "ext", "mac")):
        land(rid, f"b{i}", {"src.js": "2\n"})
        assert engine.close_milestone(rid, f"m{i + 2}")["status"] == "merged"
    engine.final_verify(rid)
    code, first, _ = contract.evaluate(rid)
    assert code == PENDING and "awaits publication of kit" in first
    publish_ready(kit, rid)
    rec = release.publish(rid, "kit")
    assert set(rec["consumers"]) == {"app", "ext", "mac"} and rec["digest"] == ident["digest"]
    for name in ("app", "ext", "mac"):
        branch = store.load_meta(rid)["repos"][name]["branch"]
        path = tk_repo(store.load_meta(rid), name)
        assert "vendor/kit/kit-ui-1.0.0.tgz" in tk.git(path, "ls-tree", "-r", "--name-only", branch).splitlines()
        assert deps.pin_record(rid, name)["vendor/kit/kit-ui-1.0.0.tgz"] == ident["packages"]["@kit/ui"]["digest"]
    engine.final_verify(rid)
    code, first, _ = contract.evaluate(rid)
    assert code == READY, first


@needs_npm
@pytest.mark.parametrize("indent", ["    ", "\t", "  "])
def test_package_json_is_edited_structurally_and_keeps_its_indent_and_key_order(tmp_path, indent):
    text = json.dumps({"name": "app", "scripts": {"b": "x"}, "dependencies": {"@kit/ui": "^0.9.0", "@kit/annotations": "^0.9.0"}},
                      indent=indent) + "\n"
    kit, app, rid = vendored_pilot(tmp_path, {"package.json": text, "src.js": "1\n"})
    land(rid, "a", {"packages/ui/i.js": "z\n"})
    engine.close_milestone(rid, "m1")
    release.pack(rid, "kit")
    publish_ready(kit, rid)
    release.publish(rid, "kit")
    out = tk.git(app, "show", f"{store.load_meta(rid)['repos']['app']['branch']}:package.json")
    want = text.replace("^0.9.0", "@@").replace('"@kit/ui": "@@"', '"@kit/ui": "file:vendor/kit/kit-ui-1.0.0.tgz"').replace(
        '"@kit/annotations": "@@"', '"@kit/annotations": "file:vendor/kit/kit-annotations-1.0.0.tgz"')
    assert out.strip() == want.strip()


# ---- field shapes of a real draft: object packages, a structural pin object, approved dependency lines ---------------

DRAFT_EDGE = {"producer": "kit", "pack": ["npm", "pack", "--ignore-scripts"],
              "packages": [{"name": "@kit/annotations", "dir": "packages/annotations"}, {"name": "@kit/ui", "dir": "packages/ui"}],
              "release": {"kind": "git-main", "fetch": ["npm", "pack", "--ignore-scripts"]},
              "pin": {"kind": "package-json", "file": "package.json", "section": "dependencies", "vendor_dir": "vendor/kit/",
                      "value": "file:vendor/kit/kit-{name}-{version}.tgz", "lockfile": "package-lock.json",
                      "lockfile_update": "npm install --package-lock-only --ignore-scripts, run by the runner"},
              "uses_4_1": ["bookkeeping"]}
LINES = ['    "@kit/annotations": "file:vendor/kit/kit-annotations-1.0.0.tgz"', '    "@kit/ui": "file:vendor/kit/kit-ui-1.0.0.tgz"']


def drive(kit, rid):
    land(rid, "a", {"packages/ui/i.js": "z\n"})
    engine.close_milestone(rid, "m1")
    release.pack(rid, "kit")
    publish_ready(kit, rid)


@needs_npm
def test_the_draft_edge_shape_pins_and_checks_the_approved_lines(tmp_path):
    contract.validate_edges({"edges": [{**DRAFT_EDGE, "consumer": "app"}]})
    kit, app, rid = vendored_pilot(tmp_path, edge=DRAFT_EDGE, deps_block={"app": {"files": {}, "kit_tarball_lines": LINES, "lockfile": ["pending"]}})
    drive(kit, rid)
    rec = release.publish(rid, "kit")
    man = json.loads(tk.git(app, "show", f"{store.load_meta(rid)['repos']['app']['branch']}:package.json"))
    assert man["dependencies"]["@kit/ui"] == "file:vendor/kit/kit-ui-1.0.0.tgz" and rec["consumers"]["app"]["files"]
    assert deps.guard(rid, "app", store.load_meta(rid)["repos"]["app"]["base_sha"], tk.git(app, "rev-parse", store.load_meta(rid)["repos"]["app"]["branch"])) == []


@needs_npm
@pytest.mark.parametrize("what", ["lines", "value", "lockfile"])
def test_a_pin_that_differs_from_the_approved_shape_is_blocked_and_leaves_the_consumer_clean(tmp_path, what):
    edge = {**DRAFT_EDGE, "pin": {**DRAFT_EDGE["pin"], **({"value": "file:vendor/kit/other-{name}-{version}.tgz"} if what == "value" else {}),
                                  **({"lockfile": "sub/package-lock.json"} if what == "lockfile" else {})}}
    lines = [LINES[0], '    "@kit/ui": "file:vendor/kit/kit-ui-9.9.9.tgz"'] if what == "lines" else LINES
    kit, app, rid = vendored_pilot(tmp_path, edge=edge, deps_block={"app": {"kit_tarball_lines": lines}})
    drive(kit, rid)
    with pytest.raises(SdlcError, match={"lines": "lacks the approved line", "value": "pin.value gives", "lockfile": "pin.lockfile"}[what]):
        release.publish(rid, "kit")
    pwt = engine.project_wt(rid, "app")
    assert tk.git(pwt, "status", "--porcelain") == "" and not (pwt / "vendor").exists() and deps.pin_record(rid, "app") == {}


def test_edge_shapes_are_validated():
    base = {**DRAFT_EDGE, "consumer": "app"}
    for bad in ({"packages": [{"name": "../x"}]}, {"packages": [{"name": "a", "dir": "../d"}]}, {"pack": ["npm", "publish"]},
                {"pin": {**DRAFT_EDGE["pin"], "vendor_dir": "../v"}}, {"pin": {**DRAFT_EDGE["pin"], "section": "scripts"}},
                {"pin": {**DRAFT_EDGE["pin"], "file": "x.json"}}, {"pin": {**DRAFT_EDGE["pin"], "lockfile": "/abs"}}):
        with pytest.raises(SdlcError):
            contract.validate_edges({"edges": [{**base, **bad}]})


def test_pinned_inputs_accept_both_shapes_and_reject_bad_paths():
    for ok in ({"app": ["e2e/playwright.config.ts"]}, [{"repo": "app", "path": "e2e/playwright.config.ts", "source": "x", "why": "y"}]):
        contract.validate_contract({"pinned_inputs": ok})
        assert contract.pinned_map({"pinned_inputs": ok}) == {"app": ["e2e/playwright.config.ts"]}
    for bad in ({"app": ["../x"]}, [{"repo": "app", "path": "/abs"}], [{"path": "x"}], "x", {"app": "x"}):
        with pytest.raises(SdlcError, match="pinned_inputs"):
            contract.validate_contract({"pinned_inputs": bad})


def test_argv_placeholders_are_validated_in_the_contract():
    ok = tk.chk("a", "app", ["bash", "-c", "gitleaks --log-opts '{base}..HEAD' --web {head} --c {producer_sha:chrome}"], count=False)
    contract.validate_contract({"checks": [ok, tk.chk("b", "chrome", ["true"])]})
    for bad in ("{producer_sha:ghost}", "{producer_sha:}", "{producer_sha:a b}"):
        with pytest.raises(SdlcError, match="producer_sha"):
            contract.validate_contract({"checks": [tk.chk("a", "app", ["echo", bad]), tk.chk("b", "chrome", ["true"])]})
    contract.validate_contract({"checks": [tk.chk("a", "app", ["echo", "{other} ${x}"])]})  # not a placeholder: left alone
