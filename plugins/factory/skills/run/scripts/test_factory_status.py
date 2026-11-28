import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "factory-status.py"
spec = importlib.util.spec_from_file_location("factory_status", SCRIPT)
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)

SLUG = "2026-11-28-saved-searches"
SHA = "a" * 40


def plan_of(n=2, **extra):
    ms = [{"id": f"M{i}", "layer": "backend", "covers": ["req-1"],
           "tasks": [{"id": "T1", "covers": ["req-1"], "files": [f"src/a{i}.ts"], "check": "true"},
                     {"id": "T2", "covers": ["req-1"], "files": [f"src/b{i}.ts"], "check": "true"}]} for i in range(1, n + 1)]
    return {"change": SLUG, "base": "main", "goalTurns": 12, "requirements": ["req-1"], "milestones": ms, **extra}


def plan_text(plan, log="", title="Saved searches"):
    return f"# {title}\n\nbody\n\n```json factory\n{json.dumps(plan, indent=1)}\n```\n\n## Progress log\n{log}\n"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args], capture_output=True, text=True, check=True).stdout.strip()


def make_repo(root, name="app", plan=None, log="", slug=SLUG, text=None):
    repo = Path(root) / name
    (repo / "changes" / slug).mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    (repo / "changes" / slug / "plan.md").write_text(text if text is not None else plan_text(plan or plan_of(), log))
    (repo / "changes" / slug / "intent.md").write_text("# Intent\n- outcome-1: x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "plan")
    (repo / ".git" / "info" / "exclude").write_text(".worktrees/\n")
    return repo


def add_worktree(repo, branch, dirname=None):
    path = repo / ".worktrees" / (dirname or branch.replace("/", "-"))
    git(repo, "worktree", "add", "-q", "-b", branch, str(path))
    return path


def write_state(wt, ms, state, age=0):
    f = wt / ".factory" / "state" / f"{ms}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state))
    t = time.time() - age
    os.utime(f, (t, t))


def fake_gh(tmp_path, prs, monkeypatch, fail=False):
    d = tmp_path / "bin"
    d.mkdir(exist_ok=True)
    gh = d / "gh"
    gh.write_text("#!/bin/sh\n" + ("exit 1\n" if fail else f"cat <<'EOF'\n{json.dumps(prs)}\nEOF\n"))
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{d}{os.pathsep}{os.environ['PATH']}")


def card_of(tmp_path, monkeypatch, repo, prs=(), fail=False):
    monkeypatch.setenv("FACTORY_HOME", str(tmp_path / "fh"))
    fake_gh(tmp_path, list(prs), monkeypatch, fail)
    out = fs.status([repo.parent])
    cards = [c for p in out["projects"] for c in p["changes"]]
    return cards[0], out


def pr(number, head, draft=False):
    return {"number": number, "title": f"PR {number}", "url": f"https://example.test/acme/app/pull/{number}", "headRefName": head, "isDraft": draft, "reviewDecision": ""}


def test_backlog_draft_plan_without_block(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, text="# Draft\n\nno block yet\n")
    c, out = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "backlog" and not c["approved"] and c["needs"] is None and out["warnings"] == []


def test_backlog_intent_only(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    (repo / "changes" / SLUG / "plan.md").unlink()
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "backlog" and c["title"] == "Intent"


def test_needs_you_approve_plan(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "needs-you" and c["needs"]["kind"] == "approve-plan" and f"/factory:run {SLUG}" in c["needs"]["where"]
    assert [m["state"] for m in c["milestones"]] == ["pending", "pending"] and c["current"] is None


def test_ready_when_approved_and_not_started(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, log=f"- approved: {SHA}\n")
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "ready" and c["approved"] and c["needs"] is None


def test_building_by_recent_state_file_and_current(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, log=f"approved: {SHA}\n### 2026-11-28 10:00 M1\nState: SHIPPED\n")
    wt = add_worktree(repo, f"milestone/{SLUG}-M2")
    write_state(wt, "M2", {"target": SHA, "checked": [], "tasks": {"T1": {"builder": "b", "merged": "m"}}}, age=60)
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "building"
    assert [m["state"] for m in c["milestones"]] == ["shipped", "building"]
    assert [t["state"] for t in c["milestones"][0]["tasks"]] == ["done", "done"]
    assert [t["state"] for t in c["milestones"][1]["tasks"]] == ["done", "pending"]
    cur = c["current"]
    assert (cur["milestone"], cur["milestoneIndex"], cur["milestoneCount"], cur["task"], cur["taskIndex"], cur["taskCount"]) == ("M2", 2, 2, "T2", 2, 2)
    assert cur["gapRound"] == 0 and cur["gapRounds"] == 3 and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", cur["since"])


def test_building_by_task_worktree_and_old_state_file(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, log=f"approved: {SHA}\n")
    wt = add_worktree(repo, f"milestone/{SLUG}-M1")
    write_state(wt, "M1", {"tasks": {}}, age=3600)  # stale file alone is not activity
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "ready"
    add_worktree(repo, f"{SLUG}-M1-T2")
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "building" and c["current"]["task"] == "T2"
    assert [t["state"] for t in c["milestones"][0]["tasks"]] == ["pending", "building"]


def test_gap_rounds(tmp_path, monkeypatch):
    log = f"approved: {SHA}\nGAP-FIX M1 round=1 files=a tests=\nGAP-FIX M1 round=2 files=b tests=\n"
    repo = make_repo(tmp_path, log=log)
    add_worktree(repo, f"{SLUG}-M1-gap2")
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "building" and c["current"]["gapRound"] == 2 and c["current"]["task"] == "M1-gap2" and c["current"]["taskIndex"] is None


def test_needs_you_blocked(tmp_path, monkeypatch):
    log = f"approved: {SHA}\n### 2026-11-28 M1\n- done T1\n- BLOCKED: owner decides the retention period\n"
    repo = make_repo(tmp_path, log=log)
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "needs-you" and c["needs"]["kind"] == "blocked"
    assert "retention period" in c["needs"]["text"] and f"/factory:run {SLUG}" in c["needs"]["where"]
    assert c["current"]["milestone"] == "M1"


def test_blocked_but_running_again_is_building(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, log=f"approved: {SHA}\n### M1\nBLOCKED: x\n")
    add_worktree(repo, f"{SLUG}-M1-T1")
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "building"


def test_needs_you_hold_review(tmp_path, monkeypatch):
    log = f"approved: {SHA}\n### M1\nHOLD-MERGED M1 abc1234\n### M2\nHOLD: pushed sha abc, verifier PASS\n"
    repo = make_repo(tmp_path, log=log)
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert [m["state"] for m in c["milestones"]] == ["merged", "hold"]
    assert c["column"] == "needs-you" and c["needs"]["kind"] == "hold-review" and c["current"]["milestone"] == "M2"


def test_release_pr_and_gallery(tmp_path, monkeypatch):
    plan = plan_of(1, integration="integration/saved", merge="owner")
    repo = make_repo(tmp_path, plan=plan, log=f"approved: {SHA}\n### M1\nSHIPPED, release PR is merge-ready\n")
    prs = [pr(7, "integration/saved"), pr(8, "someone-elses-branch")]
    c, _ = card_of(tmp_path, monkeypatch, repo, prs)
    assert c["column"] == "needs-you" and c["needs"]["kind"] == "release-pr" and c["needs"]["where"].endswith("/pull/7")
    assert c["prs"] == [{"number": 7, "url": "https://example.test/acme/app/pull/7", "title": "PR 7", "state": "open"}]
    g = repo / "changes" / SLUG / "evidence" / "M1"
    g.mkdir(parents=True)
    (g / "gallery.md").write_text("# gallery\n")
    monkeypatch.setenv("FACTORY_HOME", str(tmp_path / "fh2"))  # fresh gh cache
    c, _ = card_of(tmp_path, monkeypatch, repo, prs)
    assert c["needs"]["kind"] == "gallery"


def test_auto_merge_pr_is_not_a_need_and_done(tmp_path, monkeypatch):
    plan = plan_of(1)
    repo = make_repo(tmp_path, plan=plan, log=f"approved: {SHA}\n### M1\nSHIPPED\n")
    c, _ = card_of(tmp_path, monkeypatch, repo, [pr(3, f"milestone/{SLUG}-M1")])
    assert c["column"] == "done" and c["needs"] is None and c["prs"][0]["number"] == 3


def test_done_without_gh(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, plan=plan_of(1), log=f"approved: {SHA}\n### M1\nSHIPPED\n")
    c, out = card_of(tmp_path, monkeypatch, repo, fail=True)
    assert c["column"] == "done" and c["prs"] == [] and out["warnings"] == []


def test_malformed_plan_is_a_warning_not_a_crash(tmp_path, monkeypatch):
    good = make_repo(tmp_path, name="good", plan=plan_of(), log=f"approved: {SHA}\n")
    make_repo(tmp_path, name="bad", text="# Broken\n\n```json factory\n{not json\n```\n")
    make_repo(tmp_path, name="empty", slug="2026-11-28-other", text="# E\n\n```json factory\n{\"milestones\": []}\n```\n")
    monkeypatch.setenv("FACTORY_HOME", str(tmp_path / "fh"))
    fake_gh(tmp_path, [], monkeypatch)
    out = fs.status([good.parent])
    assert len(out["warnings"]) == 2 and any("bad/changes" in w for w in out["warnings"])
    cols = {p["name"]: p["changes"][0]["column"] for p in out["projects"]}
    assert cols == {"good": "ready", "bad": "backlog", "empty": "backlog"}


def test_bad_state_file_warns(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, log=f"approved: {SHA}\n")
    wt = add_worktree(repo, f"milestone/{SLUG}-M1")
    (wt / ".factory" / "state").mkdir(parents=True)
    (wt / ".factory" / "state" / "M1.json").write_text("{oops")
    c, out = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "ready" and any("M1.json" in w for w in out["warnings"])


def test_find_repos_depth_and_skips(tmp_path):
    a = make_repo(tmp_path / "x" / "y", name="deep")  # depth 3 from tmp_path
    make_repo(tmp_path / "x" / "y" / "z", name="too-deep")
    (tmp_path / "node_modules").mkdir()
    make_repo(tmp_path / "node_modules", name="skipped")
    assert fs.find_repos([tmp_path]) == [a]


def test_progress_log_comment_and_lowercase_hold_ignored(tmp_path, monkeypatch):
    log = f"<!-- ends SHIPPED, INCOMPLETE or BLOCKED -->\napproved: {SHA}\nno hold in this plan\n"
    repo = make_repo(tmp_path, log=log)
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "ready"


def run_cli(*args, env=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env={**os.environ, **(env or {})})


def test_cli_json_and_line(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, plan=plan_of(20), log=f"approved: {SHA}\n")
    log = f"approved: {SHA}\n### M1\nSHIPPED\n### M2\nSHIPPED\n"
    (repo / "changes" / SLUG / "plan.md").write_text(plan_text(plan_of(20), log))
    wt = add_worktree(repo, f"milestone/{SLUG}-M3")
    write_state(wt, "M3", {"tasks": {"T1": {"builder": "b", "merged": "m"}}}, age=30)
    env = {"FACTORY_HOME": str(tmp_path / "fh")}
    d = tmp_path / "bin"
    d.mkdir()
    (d / "gh").write_text("#!/bin/sh\necho '[]'\n")
    (d / "gh").chmod(0o755)
    env["PATH"] = f"{d}{os.pathsep}{os.environ['PATH']}"
    p = run_cli("--json", "--roots", str(tmp_path), env=env)
    data = json.loads(p.stdout)
    assert p.returncode == 0 and data["projects"][0]["changes"][0]["column"] == "building" and "generated" in data
    for target in (repo, wt):  # the main checkout and a worktree give the same line
        p = run_cli("--repo", str(target), "--line", env=env)
        assert p.returncode == 0
        assert re.fullmatch(r"M3 \(3/20\) · T2/2 building · gap 0/3 · \d+m", p.stdout.strip()), p.stdout


def test_line_names_a_gap_task_without_a_count(tmp_path):
    repo = make_repo(tmp_path, log=f"approved: {SHA}\n")
    add_worktree(repo, f"milestone/{SLUG}-M1")
    add_worktree(repo, f"{SLUG}-M1-gap3")
    p = run_cli("--repo", str(repo), "--line", env={"FACTORY_HOME": str(tmp_path / "fh")})
    assert re.fullmatch(r"M1 \(1/\d+\) · gap fix building · gap \d+/3", p.stdout.strip()), p.stdout


def test_line_is_empty_when_nothing_runs(tmp_path):
    repo = make_repo(tmp_path, log=f"approved: {SHA}\n")
    p = run_cli("--repo", str(repo), "--line", env={"FACTORY_HOME": str(tmp_path / "fh")})
    assert p.returncode == 0 and p.stdout == ""
    p = run_cli("--repo", str(tmp_path / "does-not-exist"), "--line")
    assert p.returncode == 0 and p.stdout == ""


def test_fmt_age():
    assert fs.fmt_age(38 * 60 + 5) == "38m" and fs.fmt_age(65 * 60) == "1h05m" and fs.fmt_age(-5) == "0m"


def test_gh_cache_is_used_for_a_minute(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_HOME", str(tmp_path / "fh"))
    fake_gh(tmp_path, [pr(1, "x")], monkeypatch)
    assert fs.open_prs(tmp_path)[0]["number"] == 1
    fake_gh(tmp_path, [pr(2, "x")], monkeypatch)
    assert fs.open_prs(tmp_path)[0]["number"] == 1


def test_foreign_changes_folder_is_ignored(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, text="# Some other tool's plan\n\nno factory block\n")
    (repo / "changes" / SLUG / "intent.md").write_text("# Intent\nfree text, no ids\n")
    monkeypatch.setenv("FACTORY_HOME", str(tmp_path / "fh"))
    assert fs.status([repo.parent])["projects"] == []


def test_change_only_in_a_worktree_and_old_cfactory_fence(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, text="# empty main\n")
    (repo / "changes" / SLUG / "intent.md").unlink()
    wt = add_worktree(repo, f"milestone/{SLUG}-M1")
    d = wt / "changes" / SLUG
    d.mkdir(parents=True, exist_ok=True)
    (d / "plan.md").write_text(plan_text(plan_of(1), f"approved: {SHA}\n").replace("```json factory", "```json cfactory"))
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["slug"] == SLUG and c["column"] == "ready" and c["title"] == "Saved searches"


def test_repo_with_changes_only_in_worktrees_is_found(tmp_path, monkeypatch):
    repo = tmp_path / "wtonly"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "commit", "-q", "--allow-empty", "-m", "x")
    (repo / ".git" / "info" / "exclude").write_text(".worktrees/\n")
    wt = add_worktree(repo, f"milestone/{SLUG}-M1")
    (wt / "changes" / SLUG).mkdir(parents=True)
    (wt / "changes" / SLUG / "plan.md").write_text(plan_text(plan_of(1), f"approved: {SHA}\n"))
    monkeypatch.setenv("FACTORY_HOME", str(tmp_path / "fh"))
    fake_gh(tmp_path, [], monkeypatch)
    assert [c["column"] for p in fs.status([tmp_path])["projects"] for c in p["changes"]] == ["ready"]


def test_leftover_task_worktrees_are_not_building(tmp_path, monkeypatch):
    log = f"approved: {SHA}\n### M1\nSHIPPED\n"
    repo = make_repo(tmp_path, log=log)
    add_worktree(repo, f"{SLUG}-M1-T1")  # leftover of a shipped milestone
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["column"] == "ready" and c["milestones"][0]["state"] == "shipped"
    # current milestone M1 (nothing logged): a merged task's worktree is done, an unmerged one is building
    repo2 = make_repo(tmp_path, name="app2", log=f"approved: {SHA}\n")
    mwt = add_worktree(repo2, f"milestone/{SLUG}-M1")
    t1 = add_worktree(repo2, f"{SLUG}-M1-T1")
    (t1 / "t1.txt").write_text("x")
    git(t1, "add", "-A")
    git(t1, "commit", "-qm", "t1")
    git(mwt, "merge", "--no-ff", "-q", "-m", f"factory-merge: {SLUG}-M1-T1", f"{SLUG}-M1-T1")
    monkeypatch.setenv("FACTORY_HOME", str(tmp_path / "fh3"))
    fake_gh(tmp_path, [], monkeypatch)
    cards = {p["name"]: p["changes"][0] for p in fs.status([tmp_path])["projects"]}
    c2 = cards["app2"]
    assert c2["column"] == "ready" and [t["state"] for t in c2["milestones"][0]["tasks"]] == ["done", "pending"]
    add_worktree(repo2, f"{SLUG}-M1-T2")
    c2 = {p["name"]: p["changes"][0] for p in fs.status([tmp_path])["projects"]}["app2"]
    assert c2["column"] == "building" and c2["current"]["task"] == "T2"


def test_real_style_log_headings_decide_state(tmp_path, monkeypatch):
    log = (f"approved: {SHA}\n### 2026-11-25 15:10, M1, HOLD (owner restores billing)\n- **Next action:** push, HOLD.\n"
           "### 2026-11-25 15:30, M1, SHIPPED to the integration branch (local merge)\n"
           "### 2026-11-26 02:55, M2, ready for verifier (HOLD pending)\n- **Next action:** verify, push and HOLD, or BLOCKED.\n")
    repo = make_repo(tmp_path, log=log)
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert [m["state"] for m in c["milestones"]] == ["shipped", "pending"] and c["column"] == "ready"


def test_untrusted_gap_rounds_and_ids_render_escaped(tmp_path, monkeypatch):
    evil = "<img src=x onerror=alert(1)>"
    plan = plan_of()
    plan["milestones"][0]["gapRounds"] = evil
    plan["milestones"][1]["id"] = "M2<b>"  # not a milestone id: dropped, never rendered
    repo = make_repo(tmp_path, plan=plan, log=f"approved: {SHA}\n")
    add_worktree(repo, f"{SLUG}-M1-T1")
    c, _ = card_of(tmp_path, monkeypatch, repo)
    assert c["current"]["gapRounds"] == 3 and all(m["gapRounds"] == 3 for m in c["milestones"])
    s = importlib.util.spec_from_file_location("fb", HERE / "factory-board.py")
    fb = importlib.util.module_from_spec(s)
    s.loader.exec_module(fb)
    page = fb.render({"generated": "x", "warnings": [], "projects": [{"repo": str(repo), "name": "app", "changes": [c]}]})
    assert "<img" not in page and "<b>" not in page


def test_bundled_copies_in_the_mod_are_identical():
    for name in ("factory-status.py", "factory-board.py"):
        bundled = HERE.parents[3] / "factory-status" / "bin" / name
        assert bundled.read_bytes() == (HERE / name).read_bytes(), f"cp plugins/factory/skills/run/scripts/{name} plugins/factory-status/bin/"
