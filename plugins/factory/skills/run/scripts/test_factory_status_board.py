"""The reader's board fields: stage, outcomes, the progress-log line formats, questions, failures, needs with commands, run."""
import importlib.util
import json
from pathlib import Path

from test_factory_status import SHA, SLUG, add_worktree, card_of, fs, git, make_repo, plan_of, plan_text, pr, write_state

HERE = Path(__file__).parent


def rich_text(log="", plan=None, title="Saved searches"):
    prose = (f"# {title}\n\n## Milestones\n### M1 backend: Table and endpoints\n- **T1:** Create the table. Covers req-1. Owns `src/a1.ts`.\n- **T2:** List endpoint. Owns `src/b1.ts`.\n\n"
             "### M2 screens: Sidebar and save flow\n- **T1:** Sidebar list.\n\n")
    plan = plan or plan_of()
    return prose + f"```json factory\n{json.dumps(plan, indent=1)}\n```\n\n## Progress log\n{log}\n"


def rich_plan():
    plan = plan_of()
    plan["milestones"][0]["tasks"][0].update(model="opus", effort="low")
    plan["milestones"][1].update(risky=True, layer="screens", gapRounds=2)
    plan["integration"] = "integration/saved"
    return plan


LOG = f"""approved: {SHA}
### 2026-11-28 10:00 M1
SHIPPED
VERIFY M1 PASS 1234567
### 2026-11-28 11:00 M2
QUESTION M2 q1: Keep comments after a restore?
QUESTION M2 q2: Does Reopen need a note?
ANSWERED M2 q2: optional
GAP-FIX M2 round=1 files=src/b2.ts tests=
VERIFY M2 FAIL abcdef1 req-1,req-2: restore drops comments
- 11:30 ERROR M2: the gate crashed
"""


def test_log_lines_questions_failures_and_verifier(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, text=rich_text(LOG, rich_plan()))
    c, _ = card_of(tmp_path, monkeypatch, repo)
    qs = {q["id"]: q for q in c["questions"]}
    assert qs["q1"]["open"] is True and qs["q2"]["open"] is False and qs["q1"]["milestone"] == "M2" and qs["q1"]["source"] == "log"
    assert qs["q1"]["text"] == "Keep comments after a restore?"
    assert [(f["kind"], f["milestone"]) for f in c["failures"]] == [("error", "M2"), ("verify", "M2")]  # newest first
    err, ver = c["failures"]
    assert err["text"] == "the gate crashed" and err["at"] == fs.to_iso("2026-11-28", "11:30")
    assert ver["sha"] == "abcdef1" and ver["reqs"] == ["req-1", "req-2"] and "restore drops comments" in ver["text"] and ver["at"] == fs.to_iso("2026-11-28", "11:00")
    m1, m2 = c["milestones"]
    assert m1["verifier"]["result"] == "PASS" and m1["verifier"]["sha"] == "1234567"
    assert m2["verifier"]["result"] == "FAIL" and m2["verifier"]["sha"] == "abcdef1"


def test_question_is_a_need_while_open_and_answering_clears_it(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, text=rich_text(LOG, rich_plan()))
    c, _ = card_of(tmp_path, monkeypatch, repo)
    qn = [n for n in c["needsAll"] if n["kind"] == "question"]
    assert c["column"] == "needs-you" and len(qn) == 1 and qn[0]["milestone"] == "M2" and qn[0]["cmd"] == f"/factory:run {SLUG}"
    assert "Keep comments after a restore?" in qn[0]["text"] and qn[0]["since"] == fs.to_iso("2026-11-28", "11:00")
    (repo / "changes" / SLUG / "plan.md").write_text(rich_text(LOG + "ANSWERED M2 q1: hide them\n", rich_plan()))
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert not any(q["open"] for q in c["questions"]) and c["needsAll"] == [] and c["needs"] is None and c["column"] == "ready"


def test_question_on_a_shipped_milestone_is_not_a_need(tmp_path, monkeypatch):
    log = f"approved: {SHA}\n### 2026-11-28 10:00 M1\nQUESTION M1 q1: old question\nSHIPPED\n"
    repo = make_repo(tmp_path, text=rich_text(log))
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["questions"][0]["open"] is True and c["needsAll"] == []


def test_needs_clarification_in_delta_is_an_open_question(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, text=rich_text(f"approved: {SHA}\n"))
    (repo / "changes" / SLUG / "delta.md").write_text("## ADDED\n- req-1 Save it [NEEDS CLARIFICATION: how many per user?]\n- req-2 Share it [NEEDS CLARIFICATION: who may see it?]\n")
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert [(q["id"], q["source"], q["open"], q["milestone"]) for q in c["questions"]] == [("d1", "delta.md", True, None), ("d2", "delta.md", True, None)]
    assert c["questions"][0]["text"] == "how many per user?"
    assert [n["kind"] for n in c["needsAll"]] == ["question"] and "(+1 more)" in c["needsAll"][0]["text"] and c["column"] == "needs-you"


def test_delta_question_on_an_intent_only_change(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    (repo / "changes" / SLUG / "plan.md").unlink()
    (repo / "changes" / SLUG / "delta.md").write_text("[NEEDS CLARIFICATION: which plan tiers?]\n")
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["stage"] == "intent" and c["column"] == "needs-you" and c["needs"]["kind"] == "question"


def test_needs_commands_by_kind(tmp_path, monkeypatch):
    # approve-plan and blocked: the run command, with a plain where sentence
    repo = make_repo(tmp_path, text=rich_text(""))
    c, _ = card_of(tmp_path, monkeypatch, repo)
    n = c["needsAll"][0]
    assert c["needs"] == n and n["kind"] == "approve-plan" and n["cmd"] == f"/factory:run {SLUG}" and "new Claude session in app" in n["where"] and n["since"]
    repo = make_repo(tmp_path / "two", text=rich_text(f"approved: {SHA}\n### 2026-11-28 09:30 M1\nBLOCKED: owner decides retention\n"))
    c, _ = card_of(tmp_path, monkeypatch, repo)
    n = c["needsAll"][0]
    assert n["kind"] == "blocked" and n["cmd"] == f"/factory:run {SLUG}" and n["milestone"] == "M1" and n["since"] == fs.to_iso("2026-11-28", "09:30")


def test_hold_review_command_depends_on_the_remote(tmp_path, monkeypatch):
    log = f"approved: {SHA}\n### 2026-11-28 10:00 M1\nHOLD: pushed abc1234def, verifier PASS\n"
    repo = make_repo(tmp_path, text=rich_text(log))
    c, _ = card_of(tmp_path, monkeypatch, repo)
    n = c["needs"]
    assert n["kind"] == "hold-review" and n["cmd"] == "git log -1 abc1234def" and n["milestone"] == "M1"
    git(repo, "remote", "add", "origin", "https://github.com/acme/app.git")
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["needs"]["cmd"] == f"gh browse --branch milestone/{SLUG}-M1"


def test_release_pr_and_gallery_commands(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, plan=plan_of(1, integration="integration/saved", merge="owner"), log=f"approved: {SHA}\n### M1\nSHIPPED\n")
    c, _ = card_of(tmp_path, monkeypatch, repo, [pr(7, "integration/saved")])
    assert c["needs"]["kind"] == "release-pr" and c["needs"]["cmd"] == "gh pr view https://example.test/acme/app/pull/7 --web"
    g = repo / "changes" / SLUG / "evidence" / "M1"
    g.mkdir(parents=True)
    (g / "gallery.md").write_text("# gallery\n")
    monkeypatch.setenv("FACTORY_HOME", str(tmp_path / "fh2"))
    c, _ = card_of(tmp_path, monkeypatch, repo, [pr(7, "integration/saved")])
    assert c["needs"]["kind"] == "gallery" and c["needs"]["cmd"].endswith("/pull/7 --web")


def test_stage_per_change(tmp_path, monkeypatch):
    def stage(name, text, log_only=False):
        repo = make_repo(tmp_path / name, text=text)
        c, _ = card_of(tmp_path, monkeypatch, repo)
        return c["stage"], c["column"]
    assert stage("a", "# Draft\n\nno block\n") == ("intent", "backlog")
    assert stage("b", rich_text("")) == ("plan", "needs-you")
    assert stage("c", rich_text(f"approved: {SHA}\n")) == ("ready", "ready")
    assert stage("d", rich_text(f"approved: {SHA}\n### M1\nBLOCKED: x\n")) == ("building", "needs-you")
    assert stage("e", rich_text(f"approved: {SHA}\n### M1\nSHIPPED\n### M2\nSHIPPED\n")) == ("done", "done")
    repo = make_repo(tmp_path / "f", text=rich_text(f"approved: {SHA}\n"))
    wt = add_worktree(repo, f"milestone/{SLUG}-M1")
    write_state(wt, "M1", {"tasks": {}}, age=30)
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert (c["stage"], c["column"]) == ("building", "building")


def test_outcomes_titles_and_plan_details(tmp_path, monkeypatch):
    log = f"### 2026-11-27 16:45 first entry\n- approved: {SHA}\n"
    repo = make_repo(tmp_path, text=rich_text(log, rich_plan()))
    (repo / "changes" / SLUG / "intent.md").write_text("# Intent\n- outcome-1: A user saves a search.\n- outcome-2: A saved search keeps its filters.\n- constraint-1: no new table\n")
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["outcomes"] == [{"id": "outcome-1", "text": "A user saves a search."}, {"id": "outcome-2", "text": "A saved search keeps its filters."}]
    assert c["slug"] == SLUG and c["title"] == "Saved searches" and c["integration"] == "integration/saved" and c["requirementCount"] == 1
    assert c["approvedSha"] == SHA[:7] and c["approvedAt"] == fs.to_iso("2026-11-27", "16:45")
    m1, m2 = c["milestones"]
    assert m1["title"] == "backend: Table and endpoints" and m1["layer"] == "backend" and m1["risky"] is False and m1["requirements"] == ["req-1"] and m1["gapRounds"] == 3
    assert m2["title"] == "screens: Sidebar and save flow" and m2["risky"] is True and m2["layer"] == "screens" and m2["gapRounds"] == 2
    t = m1["tasks"]
    assert (t[0]["title"], t[0]["model"], t[0]["effort"]) == ("Create the table", "opus", "low")
    assert (t[1]["title"], t[1]["model"], t[1]["effort"]) == ("List endpoint", None, None)  # never invented
    assert m1["verifier"] == {"result": None, "sha": None, "reqs": []} and m1["branch"] == f"milestone/{SLUG}-M1"


def test_a_failed_last_gap_round_marks_the_gap_task_failed(tmp_path, monkeypatch):
    log = (f"approved: {SHA}\nGAP-FIX M1 round=1 files=a.ts tests=\nGAP-FIX M1 round=2 files=b.ts tests=\n"
           "### 2026-11-28 10:00 M1\nVERIFY M1 FAIL abcdef1 req-1: still wrong\n")
    repo = make_repo(tmp_path, text=rich_text(log))
    c, _ = card_of(tmp_path, monkeypatch, repo)
    tasks = c["milestones"][0]["tasks"]
    assert [(t["id"], t["state"]) for t in tasks] == [("T1", "pending"), ("T2", "pending"), (f"M1-gap1", "done"), ("M1-gap2", "failed")]
    assert tasks[3]["title"] == "Fix round 2: b.ts"
    assert c["current"] is None or c["current"]["task"] != "M1-gap1"


def test_run_state_and_last_end_state(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, text=rich_text(f"approved: {SHA}\n"))
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["run"]["state"] == "idle" and c["run"]["lastEndState"] is None and c["run"]["lastActivity"] is None
    wt = add_worktree(repo, f"milestone/{SLUG}-M1")
    write_state(wt, "M1", {"tasks": {}}, age=30)
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["run"]["state"] == "running" and c["run"]["lastActivity"] and c["run"]["worktree"] == f".worktrees/milestone-{SLUG}-M1"
    (repo / "changes" / SLUG / "plan.md").write_text(rich_text(f"approved: {SHA}\n### 2026-11-28 10:00 M1\nSHIPPED\nVERIFY M1 PASS 1234567\n"))
    wt2 = repo / ".worktrees" / "x"
    del wt2
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["run"]["lastEndState"] == "SHIPPED" and c["run"]["state"] == "stopped" and any(x.startswith("VERIFY M1 PASS") for x in c["run"]["logLines"])


def test_done_date_and_old_fields_are_kept(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, text=rich_text(f"approved: {SHA}\n### 2026-11-28 10:00 M1\nSHIPPED\n### 2026-11-29 12:00 M2\nSHIPPED\n"))
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "done" and c["stage"] == "done" and c["doneAt"] == fs.to_iso("2026-11-29", "12:00")
    for key in ("slug", "title", "column", "approved", "milestones", "current", "needs", "prs"):
        assert key in c
    assert all({"id", "state", "tasks", "gapRound", "gapRounds"} <= set(m) for m in c["milestones"])


def test_status_json_is_serialisable_and_mod_fields_survive(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, text=rich_text(LOG, rich_plan()))
    _, out = card_of(tmp_path, monkeypatch, repo)
    again = json.loads(json.dumps(out))
    c = again["projects"][0]["changes"][0]
    # what hooks/status.ts parseBoard reads
    assert isinstance(c["slug"], str) and isinstance(c["milestones"][0]["tasks"], list) and isinstance(c["needs"].get("text"), str) and isinstance(c["needs"].get("where"), str)


def test_log_line_parsers_ignore_unknown_milestones_and_duplicates():
    log = "VERIFY M9 PASS abcdef1\nQUESTION M1 q1: a\nQUESTION M1 q1: a\nERROR M1: x\nERROR M1: x\nVERIFY M1 FAIL abcdef1 req-1: no\n"
    r = fs.log_records(log, {"M1"})
    assert len(r["questions"]) == 1 and len(r["errors"]) == 1 and [v["result"] for v in r["verifies"]] == ["FAIL"]
    assert fs.stamp_of("19:44 ERROR M1: x", ("2026-11-28", None)) == fs.to_iso("2026-11-28", "19:44")
    assert fs.stamp_of("ERROR M1: x", None) is None
