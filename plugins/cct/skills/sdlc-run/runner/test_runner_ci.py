"""Step 7: existing CI as proof. No network: `run` is a fake that returns recorded JSON."""

import json
import re

import ci
import contract
import engine
import pytest
import store
import testkit as tk
from contract import BLOCKED, FAIL, PENDING, READY
from store import SdlcError

H, OLD = "a" * 40, "b" * 40


def run_(name, conclusion="SUCCESS", status="COMPLETED", **kw):
    return {"name": name, "status": status, "conclusion": conclusion, **kw}


def item(job):
    return {"id": f"c-{job}", "repo": "app", "site": f"ci:{job}"}


CASES = [
    ("success", H, ["build"], [run_("build")], [], False, READY),
    ("pending not reported", H, ["build"], [], [], False, PENDING),
    ("pending running", H, ["build"], [run_("build", None, "IN_PROGRESS")], [], False, PENDING),
    ("pending queued", H, ["build"], [run_("build", None, "QUEUED")], [], False, PENDING),
    ("stale pr head", OLD, ["build"], [run_("build")], [], False, PENDING),
    ("stale check sha", H, ["build"], [run_("build", head_sha=OLD)], [], False, PENDING),
    ("skipped", H, ["build"], [run_("build", "SKIPPED")], [], False, PENDING),
    ("neutral", H, ["build"], [run_("build", "NEUTRAL")], [], False, PENDING),
    ("failed", H, ["build", "lint"], [run_("build"), run_("lint", "FAILURE")], [], False, FAIL),
    ("cancelled", H, ["build"], [run_("build", "CANCELLED")], [], False, FAIL),
    ("fail beats pending", H, ["a", "b"], [run_("a", "FAILURE")], [], False, FAIL),
    ("unreadable policy", H, None, [run_("build")], [], True, BLOCKED),
    ("blocked beats fail", H, None, [run_("build", "FAILURE")], [], True, BLOCKED),
    ("absent policy, not approved", H, [], [], [], False, BLOCKED),
    ("absent policy, local only ok", H, [], [], [], True, READY),
    ("ci item missing", H, [], [], [item("e2e")], True, PENDING),
    ("ci item present", H, [], [run_("e2e")], [item("e2e")], True, READY),
    (
        "ci item failed",
        H,
        ["build"],
        [run_("build"), run_("e2e", "FAILURE")],
        [item("e2e")],
        False,
        FAIL,
    ),
    ("ci item skipped", H, [], [run_("e2e", "SKIPPED")], [item("e2e")], True, PENDING),
    ("status context ok", H, ["ci/x"], [{"context": "ci/x", "state": "SUCCESS"}], [], False, READY),
    (
        "status context pending",
        H,
        ["ci/x"],
        [{"context": "ci/x", "state": "PENDING"}],
        [],
        False,
        PENDING,
    ),
    ("status context error", H, ["ci/x"], [{"context": "ci/x", "state": "ERROR"}], [], False, FAIL),
]


@pytest.mark.parametrize("name,pr,req,checks,items,local,want", CASES, ids=[c[0] for c in CASES])
def test_classify(name, pr, req, checks, items, local, want):
    code, first = ci.classify(pr, H, req, checks, items, local)
    assert code == want and first


def test_lines_name_the_cause():
    assert "stale" in ci.classify(H, H, ["b"], [run_("b", head_sha=OLD)], [])[1]
    assert "skipped" in ci.classify(H, H, ["b"], [run_("b", "SKIPPED")], [])[1]
    assert "lint" in ci.classify(H, H, ["lint"], [run_("lint", "FAILURE")], [])[1]
    assert "policy" in ci.classify(H, H, None, [], [])[1]


# ---- IO wrappers ------------------------------------------------------------------------------


def test_required_checks_sources_and_absence():
    def fake(protection, rules):
        def run(args, cwd=None):
            out = protection if "protection" in args[2] else rules
            if isinstance(out, Exception):
                raise out
            return json.dumps(out)

        return run

    prot = {"contexts": ["build"], "checks": [{"context": "lint"}]}
    rule = [
        {
            "type": "required_status_checks",
            "parameters": {"required_status_checks": [{"context": "e2e"}]},
        }
    ]
    assert ci.required_checks("/r", "main", fake(prot, rule)) == ["build", "e2e", "lint"]
    nope = SdlcError("gh api failed: Branch not protected (HTTP 404)")
    assert ci.required_checks("/r", "main", fake(nope, [])) == []
    assert ci.required_checks("/r", "main", fake(nope, rule)) == ["e2e"]
    assert ci.required_checks("/r", "main", fake(SdlcError("HTTP 403 forbidden"), [])) is None
    assert ci.required_checks("/r", "main", fake(prot, SdlcError("HTTP 500"))) is None


def test_repo_allows_auto_merge():
    assert ci.repo_allows_auto_merge("/r", lambda a, c=None: '{"autoMergeAllowed": true}') is True
    assert ci.repo_allows_auto_merge("/r", lambda a, c=None: '{"autoMergeAllowed": false}') is False

    def boom(a, c=None):
        raise SdlcError("x")

    assert ci.repo_allows_auto_merge("/r", boom) is False


# ---- gate on a fake run -----------------------------------------------------------------------


class Gh:
    """Recorded gh answers; counts the writes."""

    def __init__(self, head, rollup, required=None, auto=True, existing=None):
        self.head, self.rollup, self.required, self.auto, self.existing = (
            head,
            rollup,
            ["build"] if required is None else required,
            auto,
            existing or [],
        )
        self.calls = []

    def __call__(self, args, cwd=None):
        self.calls.append(args)
        if args[:3] == ["gh", "pr", "view"]:
            return json.dumps(
                {
                    "headRefOid": self.head,
                    "statusCheckRollup": self.rollup,
                    "mergeStateStatus": "CLEAN",
                    "autoMergeRequest": None,
                    "baseRefName": "main",
                    "url": "https://x/pr/1",
                    "state": "OPEN",
                }
            )
        if args[:3] == [
            "gh",
            "api",
            "repos/{owner}/{repo}/branches/main/protection/required_status_checks",
        ]:
            return json.dumps({"contexts": self.required, "checks": []})
        if args[:2] == ["gh", "api"]:
            return "[]"
        if args[:3] == ["gh", "repo", "view"]:
            return json.dumps({"autoMergeAllowed": self.auto})
        if args[:3] == ["gh", "pr", "list"]:
            return json.dumps(self.existing)
        if args[:3] == ["gh", "pr", "create"]:
            return "https://x/pr/1\n"
        return ""


def approved(tmp_path, extra=None, checks=None):
    repo = tk.make_repo(tmp_path, "app")
    rid = tk.new_run(tmp_path / "home", repo, checks or [tk.chk("local", "app")])
    extra = dict(extra or {})
    if "local_only_ok" in extra:  # approved the real way: it is part of the contract the owner approves
        d = store.run_dir(rid)
        c = store.read_json(d / "contract.json")
        c["local_only_ok"] = extra.pop("local_only_ok")
        store.write_json(d / "contract.json", c)
    tk.approve(rid)
    meta = store.load_meta(rid)
    meta.update({k: v for k, v in extra.items() if k != "extra_gates"})  # a PR is recorded by open_pr, not a flag
    store.save_meta(rid, meta)
    return repo, rid


def head(rid):
    return contract.current_head(store.load_meta(rid), "app")


def test_gate_no_pr_then_ready_stale_and_failed(tmp_path, monkeypatch):
    repo, rid = approved(tmp_path, {"extra_gates": ["ci"]})
    meta, h = store.load_meta(rid), head(rid)
    assert ci.gate(rid, meta, {"app": h}) == (PENDING, "no PR for app")
    meta["prs"] = {"app": "https://x/pr/1"}
    monkeypatch.setattr(ci, "RUN", Gh(h, [run_("build")]))
    assert ci.gate(rid, meta, {"app": h})[0] == READY
    monkeypatch.setattr(ci, "RUN", Gh(OLD, [run_("build")]))
    assert ci.gate(rid, meta, {"app": h})[0] == PENDING
    monkeypatch.setattr(ci, "RUN", Gh(h, [run_("build", "FAILURE")]))
    code, first = ci.gate(rid, meta, {"app": h})
    assert code == FAIL and "app" in first and "build" in first


def test_gate_honours_local_only_and_ci_items(tmp_path, monkeypatch):
    items = [tk.chk("local", "app"), {**tk.chk("e2e", "app"), "site": "ci:e2e"}]
    _, rid = approved(tmp_path, {"prs": {"app": "u"}, "local_only_ok": ["app"]}, items)
    meta, h = store.load_meta(rid), head(rid)
    monkeypatch.setattr(ci, "RUN", Gh(h, [], required=[]))
    assert ci.gate(rid, meta, {"app": h})[0] == PENDING  # the CI-only job has not reported
    monkeypatch.setattr(ci, "RUN", Gh(h, [run_("e2e")], required=[]))
    assert ci.gate(rid, meta, {"app": h})[0] == READY
    meta["local_only_ok"] = []
    assert ci.gate(rid, meta, {"app": h})[0] == BLOCKED  # absence not approved


def test_evaluate_reaches_ci_gate_only_after_local_proof(tmp_path, monkeypatch):
    _, rid = approved(tmp_path, {"extra_gates": ["ci"]})
    code, first, _ = contract.evaluate(rid)
    assert (
        code == PENDING and "no receipt" in first
    )  # local proof first; ci.gate is not consulted yet


# ---- body and PR ------------------------------------------------------------------------------


def test_pr_body_shape_and_no_leaks(tmp_path, monkeypatch):
    _, rid = approved(tmp_path)
    d = store.run_dir(rid)
    (d / "plan.md").write_text(
        "# plan\nAdd greeting. See /Users/x/notes and ~/y with sonnet drafts. Third sentence.\n"
        "## Why\nUsers asked for it. It is cheap. Really.\n"
    )
    engine.store.update_cp(rid, lambda c: c["milestones"].__setitem__("m1", {"status": "merged"}))
    engine.store.update_cp(
        rid, lambda c: c["external"].__setitem__("push:app", {"state": "done", "sha": "s"})
    )
    monkeypatch.setattr(ci, "RUN", Gh(head(rid), []))
    body = ci.pr_body(rid)
    heads = [ln for ln in body.splitlines() if ln.startswith("## ")]
    assert heads == ["## What", "## Why", "## Proof", "## Undo"]
    bullets = [ln for ln in body.splitlines() if ln.startswith("- ")]
    assert bullets and all(re.match(r"- \*\*[^*]+:\*\* ", b) for b in bullets)
    assert not re.search(r"/Users|~/|opus|sonnet|haiku", body, re.I)
    assert "m1" in body and "push:app" in body and "merge commit" in body and "local" in body
    for para in body.split("\n\n"):
        assert (
            len(re.findall(r"[.!?](\s|$)", para)) <= 2
            or para.startswith("-")
            or para.startswith("##")
        )


def test_open_pr_once_and_auto_merge(tmp_path):
    _, rid = approved(tmp_path)
    gh = Gh(head(rid), [])
    assert ci.open_pr(rid, "app", run=gh) == "done"
    assert ci.open_pr(rid, "app", run=gh) == "already-done"
    creates = [c for c in gh.calls if c[:3] == ["gh", "pr", "create"]]
    assert len(creates) == 1 and "--base" in creates[0] and "--head" in creates[0]
    assert store.load_meta(rid)["prs"]["app"] == "https://x/pr/1"
    assert ci.arm_auto_merge(rid, "app", run=gh) is True
    assert ["gh", "pr", "merge", "https://x/pr/1", "--squash", "--auto", "--match-head-commit", head(rid)] in gh.calls
    no = Gh(head(rid), [], auto=False)
    assert ci.arm_auto_merge(rid, "app", run=no) is False
    assert not [c for c in no.calls if c[:3] == ["gh", "pr", "merge"]]
    assert "owner merges" in (store.run_dir(rid) / "log.md").read_text()


def test_open_pr_reconciles_after_a_crash(tmp_path):
    _, rid = approved(tmp_path)
    sha = head(rid)
    store.update_cp(
        rid, lambda c: c["external"].__setitem__("pr:app", {"state": "started", "sha": sha})
    )
    gh = Gh(sha, [], existing=[{"url": "https://x/pr/9"}])
    assert ci.open_pr(rid, "app", run=gh) == "reconciled"
    assert not [c for c in gh.calls if c[:3] == ["gh", "pr", "create"]]
    assert store.load_meta(rid)["prs"]["app"] == "https://x/pr/9"


def test_same_named_jobs_use_the_worst_result():
    checks = [{"name": "unit", "status": "COMPLETED", "conclusion": "SUCCESS"}, {"name": "unit", "status": "COMPLETED", "conclusion": "FAILURE"},
              {"name": "unit", "status": "COMPLETED", "conclusion": "SUCCESS"}]
    code, line = ci.classify("a" * 40, "a" * 40, ["unit"], checks, [])
    assert code == ci.FAIL and "unit" in line
    pend = [{"name": "unit", "status": "COMPLETED", "conclusion": "SUCCESS"}, {"name": "unit", "status": "IN_PROGRESS", "conclusion": None}]
    assert ci.classify("a" * 40, "a" * 40, ["unit"], pend, [])[0] == ci.PENDING


def test_auto_merge_is_refused_without_required_ci_or_for_a_stale_pr_head(tmp_path):
    _, rid = approved(tmp_path)
    ci.open_pr(rid, "app", run=Gh(head(rid), []))
    none_required = Gh(head(rid), [], required=[])
    with pytest.raises(SdlcError, match="no required CI is configured"):
        ci.arm_auto_merge(rid, "app", run=none_required)
    stale = Gh("0" * 40, [])
    with pytest.raises(SdlcError, match="not the proven head"):
        ci.arm_auto_merge(rid, "app", run=stale)
    for g in (none_required, stale):
        assert not [c for c in g.calls if c[:3] == ["gh", "pr", "merge"]]
    ok = Gh(head(rid), [])
    assert ci.arm_auto_merge(rid, "app", run=ok) is True
    merge = next(c for c in ok.calls if c[:3] == ["gh", "pr", "merge"])
    assert merge[-2:] == ["--match-head-commit", head(rid)]


def test_auto_merge_is_allowed_with_no_required_ci_only_for_an_approved_local_only_repo(tmp_path):
    _, rid = approved(tmp_path, {"local_only_ok": ["app"]})
    ci.open_pr(rid, "app", run=Gh(head(rid), [], required=[]))
    assert ci.arm_auto_merge(rid, "app", run=Gh(head(rid), [], required=[])) is True


def test_the_pr_guard_refuses_arming_for_the_same_cases(tmp_path, monkeypatch):
    _, rid = approved(tmp_path)
    ci.open_pr(rid, "app", run=Gh(head(rid), []))
    monkeypatch.setattr(ci, "RUN", Gh("0" * 40, []))
    monkeypatch.setattr(contract, "evaluate", lambda *a, **k: (READY, "ok", []))  # the repo's own proof is ready
    with pytest.raises(SdlcError, match="not arming auto-merge"):
        engine.pr_guard(rid, "app", arming=True)
    engine.pr_guard(rid, "app")  # opening the PR itself is not refused
