"""4.2: spec traceability (every spec item covered or waived by name) and an approved base per repo."""
import json
import re

import contract
import discover
import engine
import pytest
import store
import testkit as tk
from store import SdlcError

SPEC = [{"id": "F1", "text": "A guest can open a link", "source": "spec.md#guests"}, {"id": "F2", "text": "Mail is sent", "source": "spec.md#mail"}]
LIMITS = {"max_dispatches": 10}


def check(id, **kw):
    return tk.chk(id, "web", ["true"], count=False, **kw)


def run_with(tmp_path, monkeypatch, c, base_branch=False, push=True):
    """A repo with a remote and, when asked, a pushed `project/x` two commits ahead of main; a drafted run with contract `c`."""
    monkeypatch.setenv("SDLC_HOME", str(tmp_path / "home"))
    repo = tk.make_repo(tmp_path, "web", {"README.md": "x\n"}, remote=True)
    if base_branch:
        tk.git(repo, "checkout", "-qb", "project/x")
        tk.commit_file(repo, "a.txt", "1")
        tk.commit_file(repo, "b.txt", "2")
        if push:
            tk.git(repo, "push", "-q", "origin", "project/x")
        tk.git(repo, "checkout", "-q", "main")
    rid = discover.plan([str(repo)], "t")
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"limits": LIMITS, "waive_full": ["web"], **c}))
    discover.draft(rid, None, str(f), None, [], [])
    return repo, rid


def push_to_base(repo, name="c.txt"):
    tk.git(repo, "checkout", "-q", "project/x")
    sha = tk.commit_file(repo, name, "3")
    tk.git(repo, "push", "-q", "origin", "project/x")
    tk.git(repo, "checkout", "-q", "main")
    return sha


# ---- spec traceability -----------------------------------------------------------------------------------------------

def test_every_spec_item_needs_a_covering_check_or_a_named_waiver():
    base = {"spec": SPEC, "checks": [check("a", covers=["F1"])]}
    with pytest.raises(SdlcError, match="no covering check and no named waiver: F2"):
        contract.validate_contract(base)
    contract.validate_contract({**base, "spec_waivers": [{"id": "F2", "reason": "copy only, reviewed by hand"}]})
    for bad, why in (({"checks": [check("a", covers=["F1", "F9"])]}, "unknown spec id F9"),
                     ({"checks": [check("a", covers=["F1", "F2"])], "spec_waivers": [{"id": "F2"}]}, "needs the id of a spec item and a reason"),
                     ({"checks": [check("a", covers=["F1", "F2"])], "spec_waivers": [{"id": "F7", "reason": "x"}]}, "needs the id of a spec item"),
                     ({"checks": [check("a", covers=["F1", "F2"])], "spec": SPEC + SPEC[:1]}, "duplicate spec id F1"),
                     ({"checks": [check("a", covers=["F1", "F2"])], "spec": [{"id": "F1", "text": " "}, SPEC[1]]}, "needs an id, a text")):
        with pytest.raises(SdlcError, match=why):
            contract.validate_contract({"spec": SPEC, **bad})
    with pytest.raises(SdlcError, match="unknown spec id F1"):  # no spec key: nothing to cover, so a covers id is unknown
        contract.validate_contract({"checks": [check("a", covers=["F1"])]})
    contract.validate_contract({"checks": [check("a")]})  # optional: a contract with no spec is unchanged


def test_approve_refuses_an_uncovered_spec_item_and_the_screen_lists_waived_and_uncovered_first(tmp_path, monkeypatch):
    c = {"spec": SPEC, "checks": [check("a", covers=["F1"], task="t1")], "spec_waivers": [{"id": "F2", "reason": "copy only"}]}
    _, rid = run_with(tmp_path, monkeypatch, c)
    text = discover.screen(rid).read_text()
    table = text.split("## Spec coverage")[1].split("## Waived spec items")[0]
    assert table.index("| F2 |") < table.index("| F1 |") and "| F1 | A guest can open a link | a | t1 | covered |" in table  # waived first
    assert "| F2 | Mail is sent | - | - | WAIVED |" in table
    assert "## Waived spec items\n\n- **`F2`:** copy only" in text
    d = store.run_dir(rid)
    stored = store.read_json(d / "contract.json")
    stored["spec_waivers"] = []  # the waiver removed after draft: approve refuses
    store.write_json(d / "contract.json", stored)
    with pytest.raises(SdlcError, match="no covering check and no named waiver: F2"):
        tk.approve(rid)


def test_spec_status_rolls_up_receipts_and_pass_needs_the_sealed_final_head(tmp_path, monkeypatch):
    c = {"spec": [*SPEC, {"id": "F3", "text": "Waived", "source": "x#y"}],
         "checks": [check("a", covers=["F1", "F2"]), check("b", covers=["F2"])], "spec_waivers": [{"id": "F3", "reason": "later"}]}
    _, rid = run_with(tmp_path, monkeypatch, c)
    tk.approve(rid)
    meta, ck = store.load_meta(rid), {k["id"]: k for k in store.read_json(store.run_dir(rid) / "contract.json")["checks"]}
    head = contract.current_head(meta, "web")

    def receipt(cid, verdict):
        contract.write_receipt(rid, ck[cid], sha=head, verdict=verdict, exit_code=0, tests=1, base=None)

    def states(sealed):
        return {r["id"]: r["status"] for r in contract.spec_status(rid, sealed)}
    assert states(True) == {"F1": "PENDING", "F2": "PENDING", "F3": "WAIVED"}  # no receipts yet
    receipt("a", "PASS")
    assert states(True) == {"F1": "PASS", "F2": "PENDING", "F3": "WAIVED"}  # F2 needs both of its checks
    assert states(False)["F1"] == "PENDING"  # not sealed by the final gate: not a PASS yet
    receipt("b", "FAIL")
    assert states(True)["F2"] == "FAIL" and states(True)["F1"] == "PASS"
    receipt("b", "PASS")
    assert states(True) == {"F1": "PASS", "F2": "PASS", "F3": "WAIVED"}
    assert contract.spec_report(rid, True) == ["SPEC F3 WAIVED: waived: later", "SPEC F1 PASS: a", "SPEC F2 PASS: a, b"]  # waived first, as on the approval screen


def test_removing_or_changing_a_covering_check_after_approval_is_caught_by_the_bundle_digest(tmp_path, monkeypatch):
    c = {"spec": SPEC, "checks": [check("a", covers=["F1"]), check("b", covers=["F2"])]}
    _, rid = run_with(tmp_path, monkeypatch, c)
    before = contract.bundle_digest(rid)
    tk.approve(rid)
    assert contract.approved_digest_ok(rid) == (True, "approved bundle changed after approval") or contract.approved_digest_ok(rid)[0]
    d = store.run_dir(rid)
    original = store.read_json(d / "contract.json")
    for edit in (lambda x: x["checks"].pop(),  # a covering check removed
                 lambda x: x["checks"][1].update(covers=[]),  # a covering check no longer covers
                 lambda x: x["spec"][1].update(text="Mail is maybe sent")):  # the spec text changed
        changed = json.loads(json.dumps(original))
        edit(changed)
        store.write_json(d / "contract.json", changed)
        assert contract.bundle_digest(rid) != before
        assert contract.approved_digest_ok(rid) == (False, "approved bundle changed after approval")
        code, first, _ = contract.evaluate(rid)
        assert code == contract.BLOCKED and first.startswith("integrity:")
        store.write_json(d / "contract.json", original)
    assert contract.approved_digest_ok(rid)[0]


# ---- an approved base per repo ---------------------------------------------------------------------------------------

def test_the_base_ref_is_pinned_to_a_sha_in_the_contract_the_branch_and_the_screen(tmp_path, monkeypatch):
    repo, rid = run_with(tmp_path, monkeypatch, {"checks": [check("a")], "repos": {"web": {"base": "project/x"}}}, base_branch=True)
    sha = tk.git(repo, "rev-parse", "origin/project/x")
    meta = store.load_meta(rid)["repos"]["web"]
    assert store.read_json(store.run_dir(rid) / "contract.json")["repos"]["web"] == {"base": "project/x", "base_sha": sha, "base_source": "origin"}
    assert meta["base_sha"] == sha and tk.git(repo, "rev-parse", meta["branch"]) == sha  # the run branch is cut from that SHA
    text = discover.screen(rid).read_text()
    assert f"**base:** `web`: `project/x` @ `{sha}` (2 commits not on main)" in text and "`sdlc pr` still targets main" in text
    assert "carries these base commits" in text


def test_a_run_without_a_base_branches_from_the_default_branch_as_before(tmp_path, monkeypatch):
    repo, rid = run_with(tmp_path, monkeypatch, {"checks": [check("a")]}, base_branch=True)
    assert store.load_meta(rid)["repos"]["web"]["base_sha"] == tk.git(repo, "rev-parse", "origin/main")
    assert "## Base" not in discover.screen(rid).read_text()


def test_a_base_that_moved_blocks_approval_and_dispatch_and_names_the_ref(tmp_path, monkeypatch):
    repo, rid = run_with(tmp_path, monkeypatch, {"checks": [check("a")], "repos": {"web": {"base": "project/x"}}}, base_branch=True)
    assert contract.base_problem(rid) == ""
    moved = push_to_base(repo)
    with pytest.raises(SdlcError, match=r"not approvable: base ref project/x of web moved from .* to " + moved[:9]):
        tk.approve(rid)
    discover.draft(rid, None, None, None, [], [])  # a re-draft does not silently follow the ref either: the contract keeps its pin
    assert contract.base_problem(rid).startswith("base ref project/x of web moved")
    f = tmp_path / "again.json"
    f.write_text(json.dumps({"limits": LIMITS, "waive_full": ["web"], "checks": [check("a")], "repos": {"web": {"base": "project/x"}}}))
    discover.draft(rid, None, str(f), None, [], [])  # only an explicit new draft re-pins it, before approval
    assert contract.base_problem(rid) == "" and store.load_meta(rid)["repos"]["web"]["base_sha"] == moved
    tk.approve(rid)
    push_to_base(repo, "d.txt")
    with pytest.raises(SdlcError, match=r"BLOCKED integrity.*project/x"):
        engine.preflight(rid)


def test_the_base_sha_is_part_of_the_bundle_digest(tmp_path, monkeypatch):
    repo, rid = run_with(tmp_path, monkeypatch, {"checks": [check("a")], "repos": {"web": {"base": "project/x"}}}, base_branch=True)
    tk.approve(rid)
    d = store.run_dir(rid)
    c = store.read_json(d / "contract.json")
    c["repos"]["web"]["base_sha"] = tk.git(repo, "rev-parse", "origin/main")  # a different base written after approval
    store.write_json(d / "contract.json", c)
    assert contract.approved_digest_ok(rid) == (False, "approved bundle changed after approval")


def test_base_shapes_are_validated():
    for bad in ({"web": {"base": "../x"}}, {"web": {"base": "a b"}}, {"web": {"base": "x", "base_sha": "abc"}}, {"web": {"base_sha": "a" * 40}},
                {"web": {"other": 1}}, {"web": "x"}, []):
        with pytest.raises(SdlcError):
            contract.validate_contract({"checks": [], "repos": bad})
    contract.validate_contract({"checks": [], "repos": {"web": {"base": "project/x", "base_sha": "a" * 40}}})


# ---- a local-only base ref -------------------------------------------------------------------------------------------------

BASE = {"checks": [check("a")], "repos": {"web": {"base": "project/x"}}}


def test_a_local_only_base_branch_is_pinned_from_the_local_ref_and_marked_local(tmp_path, monkeypatch):
    repo, rid = run_with(tmp_path, monkeypatch, BASE, base_branch=True, push=False)  # never pushed: local by policy
    sha = tk.git(repo, "rev-parse", "refs/heads/project/x")
    assert tk.git(repo, "branch", "-r", "--list", "origin/project/x") == ""
    assert store.read_json(store.run_dir(rid) / "contract.json")["repos"]["web"] == {"base": "project/x", "base_sha": sha, "base_source": "local"}
    assert store.load_meta(rid)["repos"]["web"]["base_sha"] == sha
    assert f"@ `{sha}` (local only; 2 commits not on main)" in discover.screen(rid).read_text()
    tk.approve(rid)  # used to BLOCK: it fetched origin/project/x only


def test_the_moved_ref_check_reads_the_local_ref(tmp_path, monkeypatch):
    repo, rid = run_with(tmp_path, monkeypatch, BASE, base_branch=True, push=False)
    assert contract.base_problem(rid) == ""
    tk.git(repo, "checkout", "-q", "project/x")
    moved = tk.commit_file(repo, "later.txt", "x")
    tk.git(repo, "checkout", "-q", "main")
    assert re.search(r"base ref project/x of web moved from \w+ to " + moved[:9] + r" \(local branch\)", contract.base_problem(rid))
    with pytest.raises(SdlcError, match="not approvable: base ref project/x"):
        tk.approve(rid)


def test_a_base_that_differs_locally_and_on_origin_is_blocked_naming_both_shas(tmp_path, monkeypatch):
    repo, rid = run_with(tmp_path, monkeypatch, BASE, base_branch=True)  # pushed: origin and local agree
    pushed = tk.git(repo, "rev-parse", "origin/project/x")
    assert store.read_json(store.run_dir(rid) / "contract.json")["repos"]["web"]["base_source"] == "origin"
    tk.git(repo, "checkout", "-q", "project/x")
    local = tk.commit_file(repo, "unpushed.txt", "x")  # the local branch moved on without a push
    tk.git(repo, "checkout", "-q", "main")
    f = tmp_path / "again.json"
    f.write_text(json.dumps({"limits": LIMITS, "waive_full": ["web"], **BASE}))
    with pytest.raises(SdlcError, match=rf"local branch is at {local} and origin/project/x is at {pushed}"):
        discover.draft(rid, None, str(f), None, [], [])
    assert re.search(r"differ", contract.base_problem(rid))
    with pytest.raises(SdlcError, match="differ"):
        tk.approve(rid)


def test_a_base_that_exists_nowhere_is_an_env_block_and_the_source_is_in_the_digest(tmp_path, monkeypatch):
    repo, rid = run_with(tmp_path, monkeypatch, BASE, base_branch=True, push=False)
    other = tmp_path / "again.json"
    other.write_text(json.dumps({"limits": LIMITS, "waive_full": ["web"], "checks": [check("a")], "repos": {"web": {"base": "project/none"}}}))
    with pytest.raises(SdlcError, match="neither as a local branch nor on origin"):
        discover.draft(rid, None, str(other), None, [], [])
    tk.approve(rid)
    d = store.run_dir(rid)
    c = store.read_json(d / "contract.json")
    c["repos"]["web"]["base_source"] = "origin"  # the digest binds the source too
    store.write_json(d / "contract.json", c)
    assert contract.approved_digest_ok(rid) == (False, "approved bundle changed after approval")
    for bad in ({"base": "x", "base_source": "elsewhere", "base_sha": "a" * 40}, {"base": "x", "base_source": "local"}):
        with pytest.raises(SdlcError, match="base_source"):
            contract.validate_contract({"checks": [], "repos": {"web": bad}})
