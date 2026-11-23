"""Step 1: contract, approval digest, receipts and the sdlc check exit codes."""
import contract
import store
import testkit as tk
from contract import BLOCKED, FAIL, PENDING, READY


def setup(tmp_path):
    repo = tk.make_repo(tmp_path, "app")
    rid = tk.new_run(tmp_path / "home", repo, [tk.chk("a", "app", milestone="m1"), tk.chk("b", "app")])
    return repo, rid


def receipt(rid, repo, check_id, verdict="PASS", sha=None):
    c = {k["id"]: k for k in store.read_json(store.run_dir(rid) / "contract.json")["checks"]}[check_id]
    meta = store.load_meta(rid)
    return contract.write_receipt(rid, c, sha=sha or contract.current_head(meta, "app"), verdict=verdict,
                                  exit_code=0 if verdict == "PASS" else 1, tests=3, base=None, reason="x")


def test_unapproved_run_is_blocked(tmp_path):
    _, rid = setup(tmp_path)
    assert contract.evaluate(rid)[0] == BLOCKED


def test_missing_receipt_is_pending_then_ready(tmp_path):
    repo, rid = setup(tmp_path)
    tk.approve(rid)
    code, first, _ = contract.evaluate(rid)
    assert code == PENDING and "no receipt" in first
    receipt(rid, repo, "a")
    assert contract.evaluate(rid)[0] == PENDING
    receipt(rid, repo, "b")
    assert contract.evaluate(rid)[0] == READY


def test_stale_pass_after_a_new_commit(tmp_path):
    repo, rid = setup(tmp_path)
    tk.approve(rid)
    receipt(rid, repo, "a")
    receipt(rid, repo, "b")
    meta = store.load_meta(rid)
    tk.git(repo, "checkout", "-q", meta["repos"]["app"]["branch"])
    tk.commit_file(repo, "new.txt", "x")
    code, first, _ = contract.evaluate(rid)
    assert code == PENDING and "head is" in first


def test_receipt_for_another_bundle_does_not_count(tmp_path):
    repo, rid = setup(tmp_path)
    tk.approve(rid)
    receipt(rid, repo, "a")
    rec = receipt(rid, repo, "b")
    rec["body"]["bundle"] = "0" * 64
    store.write_json(contract.receipt_path(rid, "b", "app"), rec)
    code, first, _ = contract.evaluate(rid)
    assert code == PENDING and "another contract" in first


def test_fail_and_blocked_codes(tmp_path):
    repo, rid = setup(tmp_path)
    tk.approve(rid)
    receipt(rid, repo, "a", "FAIL")
    receipt(rid, repo, "b")
    assert contract.evaluate(rid)[0] == FAIL
    receipt(rid, repo, "a", "BLOCKED")
    assert contract.evaluate(rid)[0] == BLOCKED


def test_changed_contract_after_approval_is_blocked(tmp_path):
    repo, rid = setup(tmp_path)
    tk.approve(rid)
    receipt(rid, repo, "a")
    receipt(rid, repo, "b")
    d = store.run_dir(rid)
    c = store.read_json(d / "contract.json")
    c["checks"][0]["runner"] = ["true", "weakened"]
    store.write_json(d / "contract.json", c)
    code, first, _ = contract.evaluate(rid)
    assert code == BLOCKED and "integrity" in first


def test_stop_marker_blocks(tmp_path):
    repo, rid = setup(tmp_path)
    tk.approve(rid)
    store.stop_marker(rid).write_text("1")
    assert "STOPPED" in contract.evaluate(rid)[1]


def test_status_line_carries_run_heads_and_first_unmet(tmp_path):
    repo, rid = setup(tmp_path)
    tk.approve(rid)
    code, first, _ = contract.evaluate(rid)
    line = contract.status_line(rid, code, first)
    assert line.startswith("PENDING run=") and rid in line and "app@" in line and "first=" in line
