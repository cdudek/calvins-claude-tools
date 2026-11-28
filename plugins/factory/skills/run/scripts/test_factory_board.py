import importlib.util
import json
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "factory-board.py"
spec = importlib.util.spec_from_file_location("factory_board", SCRIPT)
fb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fb)


def ms(mid, state, title=None, layer="backend", tasks=(), **kw):
    return {"id": mid, "title": title or f"Title of {mid}", "layer": layer, "risky": False, "requirements": ["req-1"], "branch": f"milestone/s-{mid}", "state": state,
            "tasks": list(tasks), "gapRound": 0, "gapRounds": 3, "verifier": {"result": None, "sha": None, "reqs": []}, **kw}


def task(tid, state="pending", title=None, model=None, effort=None):
    return {"id": tid, "state": state, "title": title or f"Task {tid}", "model": model, "effort": effort}


def card(slug, column, title="Saved searches", needs=None, prs=(), milestones=(), current=None, stage=None, **kw):
    needs_all = kw.pop("needsAll", [needs] if needs else [])
    stage = stage or {"needs-you": "plan", "building": "building", "ready": "ready", "backlog": "intent", "done": "done"}[column]
    return {"slug": slug, "title": title, "column": column, "stage": stage, "approved": column != "backlog", "approvedSha": None, "approvedAt": None, "integration": None, "doneAt": None,
            "outcomes": [], "requirementCount": 0, "milestones": list(milestones), "current": current, "needs": needs, "needsAll": needs_all, "questions": [], "failures": [],
            "run": {"state": "idle", "lastActivity": None, "lastEndState": None, "worktree": None, "logLines": []}, "prs": list(prs), **kw}


def data(*cards, warnings=(), name="app"):
    return {"generated": "2026-11-28T10:00:00Z", "warnings": list(warnings), "projects": [{"repo": "/home/u/projects/acme/" + name, "name": name, "changes": list(cards)}]}


NEED = {"kind": "blocked", "text": "Owner decides the retention period.", "where": "Paste it in a new Claude session in app.", "cmd": "/factory:run x", "since": "2026-11-28T08:00:00Z", "milestone": "M2"}
CUR = {"milestone": "M2", "milestoneIndex": 2, "milestoneCount": 3, "task": "T1", "taskIndex": 1, "taskCount": 2, "gapRound": 1, "gapRounds": 3, "since": None}
EVIL = "<img src=x onerror=alert(1)>"
EVIL2 = '"><svg onload=alert(2)>'


def script_of(page):
    return page.split("<script>")[1].split("</script>")[0]


def test_overview_has_header_needs_and_table_with_counts():
    d = data(card("a", "needs-you", title="Plan one", needs={**NEED, "kind": "approve-plan", "milestone": None, "text": "Waits for approval."}),
             card("b", "building", title="Build one", stage="building", needs=NEED, current=CUR, milestones=[ms("M1", "shipped"), ms("M2", "blocked"), ms("M3", "pending")]),
             card("c", "backlog", title="Idea", outcomes=[{"id": "outcome-1", "text": "x"}]), card("d", "done", title="Old", doneAt="2026-11-01T10:00:00Z"))
    page = fb.render(d)
    assert re.search(r"Data as of \d\d:\d\d", page) and 'http-equiv="refresh" content="15"' in page and "prefers-color-scheme:dark" in page and "width=device-width" in page
    assert re.search(r'<h2 id="needs">Needs you <span class="cnt">2</span>', page)
    assert page.index("Owner decides the retention period.") < page.index("Waits for approval.")  # longest waiting first: the blocked one has a since, the plan one has not
    assert 'href="/p/app/b#M2"' in page and 'href="/p/app/a"' in page  # title links go to the change, anchored at the milestone
    assert '<table class="lanes">' in page and page.count('<th scope="col"') == 6 and '<th scope="row">' in page
    for name in ("Intent", "Plan", "Ready", "Building", "Done"):
        assert re.search(rf'<span>{name} <span class="mono dim">1</span></span>', page) or name == "Ready"
    assert re.search(r'<span>Ready <span class="mono dim">0</span>', page) and "An idea with outcomes, no plan" in page
    assert "1 outcome, no plan yet" in page and "Milestone 2 of 3 · task 1 of 2 building · fix round 1 of 3" in page and "Shipped 1 Nov" in page
    assert 'aria-label="None">–</span>' in page and '<div class="phone">' in page and "1 blocked, 1 plan to approve" in page
    assert 'Raw data: <a class="mono" href="/status.json">status.json</a>' in page and 'class="bar"' in page


def test_table_shows_two_cards_per_cell_then_a_more_link():
    cards = [card(f"s{i}", "done", title=f"Done {i}") for i in range(5)]
    page = fb.render(data(*cards))
    assert page.count('class="mini"') == 2 and ">3 more</a>" in page
    assert 'href="/p/app/"' in page


def test_projects_are_sorted_most_urgent_first():
    d = {"generated": "2026-11-28T10:00:00Z", "warnings": [], "projects": [
        {"repo": "/r/idle", "name": "idle", "changes": [card("a", "done")]},
        {"repo": "/r/hold", "name": "held", "changes": [card("b", "needs-you", needs={**NEED, "kind": "hold-review"}, stage="building")]},
        {"repo": "/r/blk", "name": "blocked-one", "changes": [card("c", "needs-you", needs=NEED, stage="building")]}]}
    page = fb.render(d)
    rows = re.findall(r'<a class="pname" href="/p/([^/"]+)/"', page)
    assert rows == ["blocked-one", "held", "idle"]


def test_copy_button_carries_the_command_in_data_attributes_not_in_the_script():
    page = fb.render(data(card("a", "needs-you", needs={**NEED, "cmd": f"/factory:run {EVIL} {EVIL2}"})))
    assert 'class="btn s tonal copy"' in page and 'data-cmd="/factory:run &lt;img src=x onerror=alert(1)&gt; &quot;&gt;&lt;svg onload=alert(2)&gt;"' in page
    assert 'aria-label="Copy command for app · Saved searches · M2"' in page and 'role="status" aria-live="polite"' in page
    js = script_of(page)
    assert "factory:run" not in js and "alert" not in js and "navigator.clipboard.writeText(cmd)" in js and "Press Cmd+C" in js and "2000" in js
    assert "<img" not in page and "<svg" not in page


def full_project():
    q = [{"id": "q1", "milestone": "M2", "text": "Keep comments?", "source": "log", "open": True, "at": None}, {"id": "d1", "milestone": None, "text": "Which tiers?", "source": "delta.md", "open": True, "at": None}]
    f = [{"milestone": "M2", "text": "Verifier FAIL req-1: drops comments", "sha": "abcdef1", "at": "2026-11-28T09:41:00Z", "kind": "verify", "reqs": ["req-1"]}]
    building = card("2026-11-24-v1", "needs-you", title="v1 beta", stage="building", needs=NEED, current=CUR, questions=q, failures=f, outcomes=[{"id": "outcome-1", "text": "A reviewer pins."}], requirementCount=4,
                    approvedSha="9c1e4b2", approvedAt="2026-11-24T10:00:00Z", integration="integration/v1",
                    run={"state": "stopped", "lastActivity": "2026-11-28T09:44:00Z", "lastEndState": None, "worktree": ".worktrees/m", "logLines": ["VERIFY M2 FAIL abcdef1 req-1: x"]},
                    milestones=[ms("M1", "shipped", layer="components", tasks=[task("T1", "done", model="sonnet", effort="high")], verifier={"result": "PASS", "sha": "4be19d0", "reqs": []}),
                                ms("M2", "blocked", layer="backend", gapRound=3, tasks=[task("T2", "done"), task("M2-gap3", "failed", title="Fix round 3")], verifier={"result": "FAIL", "sha": "abcdef1", "reqs": ["req-1"]}),
                                ms("M3", "pending", layer="screens", tasks=[task("T3")])])
    plan = card("2026-11-28-share", "needs-you", title="Share links", stage="plan", needs={**NEED, "kind": "approve-plan", "milestone": None, "cmd": "/factory:run 2026-11-28-share"},
                milestones=[ms("M1", "pending", tasks=[task("T1")]), ms("M2", "pending", risky=True, tasks=[task("T2")])])
    intent = card("2026-11-29-invites", "backlog", title="Invites", outcomes=[{"id": "outcome-1", "text": "Invite by link."}])
    ready = card("2026-11-27-pdf", "ready", title="PDF export", approvedSha="1234567", approvedAt="2026-11-27T10:00:00Z", milestones=[ms("M1", "pending", tasks=[task("T1")])])
    done = card("2026-11-02-old", "done", title="Brand v4", doneAt="2026-11-02T10:00:00Z", milestones=[ms("M1", "shipped")], prs=[{"number": 3, "url": "https://example.test/pr/3", "title": "R", "state": "open"}])
    return data(intent, plan, ready, building, done)


def test_project_page_building_view():
    page = fb.render_project(full_project(), "app", "2026-11-24-v1")
    assert page.count("<h1>") == 1 and "<h1>app</h1>" in page and "~" not in page.split("<h1>")[0] and 'aria-label="Breadcrumb"' in page and '<select data-nav aria-label="Project">' in page
    assert re.search(r'<h2 id="ny">Needs you in this project <span class="cnt">2</span>', page)
    tabs = page.split('<nav class="tabs"')[1].split("</nav>")[0]
    assert tabs.index("Invites") < tabs.index("Share links") < tabs.index("PDF export") < tabs.index("v1 beta") < tabs.index("Done (1)")  # stage order, Done collapsed
    assert tabs.count('aria-current="page"') == 1 and re.search(r'aria-current="page"><span class="stg">Building</span>v1 beta', tabs)
    assert "1 of 3 milestones shipped. M2 (milestone 2) is blocked after its last fix round, and 2 questions are open." in page
    assert "It lands on <span class=\"mono\">integration/v1</span>, approved at <span class=\"mono\">9c1e4b2</span> on 24 Nov." in page
    assert "1 shipped · 1 blocked · 1 pending" in page and "Intent: 1 outcome, 4 requirements" in page
    # Now block first, then the filter, expand/collapse and layer groups with shipped layers collapsed
    assert page.index("<h2>Now</h2>") < page.index("All milestones") and 'data-filter="needs"' in page and 'id="expand-all"' in page and 'id="collapse-all"' in page
    now = page.split("<h2>Now</h2>")[1].split("All milestones")[0]
    assert now.index("What failed") < now.index("Open question") < now.index("<b>Verifier</b>") < now.index('aria-label="Tasks of M2"') < now.index("Covers") < now.index("Branch")
    assert "FAIL req-1 on abcdef1" in now and "fix round 3 of 3" in now and "Failed" in now and "1 failure" in page and "1 question" in page
    assert re.search(r'class="grow" data-open="0"[^>]*><span>Components</span>', page) and re.search(r'class="grow" data-open="1"[^>]*><span>Backend</span>', page)
    assert 'id="M2"' in page and 'data-tags="needs active"' in page and 'data-tags="shipped"' in page and "not run yet" in page and "sonnet high" in page
    # aside
    assert re.search(r'<h2 id="qs">Questions <span class="mono-s">2 open</span>', page) and 'href="#M2"' in page and "delta.md" in page
    assert page.index("Failures") < page.index("newest first") and "abcdef1" in page.split('id="er"')[1]
    assert "Stopped" in page and "none recorded: the run stopped without SHIPPED, HOLD or BLOCKED" in page and "<summary>Log lines</summary>" in page and ".worktrees/m" in page


def test_project_page_other_views():
    d = full_project()
    plan = fb.render_project(d, "app", "2026-11-28-share")
    assert "Plan waiting for approval" in plan and "2 milestones, 2 tasks, 1 risky" in plan and "Risky" in plan and "Nothing is built until you approve." in plan
    intent = fb.render_project(d, "app", "2026-11-29-invites")
    assert "Intent only" in intent and "outcome-1" in intent and "No plan yet. To write one, run this in a Claude session in app:" in intent and 'data-cmd="/factory:run 2026-11-29-invites"' in intent
    ready = fb.render_project(d, "app", "2026-11-27-pdf")
    assert "Ready, not started" in ready and "1234567" in ready and "/factory:run 2026-11-27-pdf" in ready
    done = fb.render_project(d, "app", "done")
    assert "Brand v4" in done and "shipped 2 Nov" in done and '<a class="dim" href="https://example.test/pr/3"' in done and done.split('<nav class="tabs"')[1].count('aria-current="page"') == 1
    assert "Brand v4" in fb.render_project(d, "app", "2026-11-02-old") and fb.render_project(d, "app", "2026-11-02-old").split("<nav class=\"tabs\"")[1].count("aria-current=\"page\"") == 1


def test_project_page_default_change_needs_first_then_building_then_newest():
    d = full_project()
    assert 'aria-current="page"><span class="stg">Building</span>v1 beta' in fb.render_project(d, "app")  # blocked since 08:00 waits longest
    for c in d["projects"][0]["changes"]:
        c["needs"], c["needsAll"] = None, []
        if c["slug"] == "2026-11-28-share":
            c["stage"], c["column"] = "building", "building"
    assert 'aria-current="page"><span class="stg">Building</span>Share links' in fb.render_project(d, "app")
    for c in d["projects"][0]["changes"]:
        c["stage"] = "ready"
    assert 'aria-current="page"><span class="stg">Ready</span>Brand v4' in fb.render_project(d, "app")  # the newest


def test_project_urls_use_a_safe_slug_and_unknown_is_none():
    d = data(card("a", "ready"), name="My App/../x")
    assert [s for s, _ in fb.project_index(d)] == ["my-app-..-x"]
    page = fb.render(d)
    assert 'href="/p/my-app-..-x/"' in page and "My App/../x" in page
    assert fb.render_project(d, "my-app-..-x") and fb.render_project(d, "nope") is None and fb.render_project(d, "my-app-..-x", "zzz") is None
    two = {"generated": "x", "warnings": [], "projects": [{"repo": "/a", "name": "app", "changes": [card("a", "ready")]}, {"repo": "/b", "name": "app", "changes": [card("a", "ready")]}]}
    assert [s for s, _ in fb.project_index(two)] == ["app", "app-2"]


def test_every_interpolated_value_is_escaped_on_every_page():
    hostile = card(EVIL, "needs-you", title=EVIL, stage="building", needs={"kind": EVIL, "text": EVIL, "where": EVIL, "cmd": EVIL2, "since": EVIL, "milestone": EVIL},
                   outcomes=[{"id": EVIL, "text": EVIL}], approvedSha=EVIL, approvedAt=EVIL, integration=EVIL, doneAt=EVIL, requirementCount=EVIL,
                   questions=[{"id": EVIL, "milestone": EVIL, "text": EVIL, "source": EVIL, "open": True, "at": EVIL}],
                   failures=[{"milestone": EVIL, "text": EVIL, "sha": EVIL, "at": EVIL, "kind": EVIL, "reqs": [EVIL]}],
                   run={"state": EVIL, "lastActivity": EVIL, "lastEndState": EVIL, "worktree": EVIL, "logLines": [EVIL]},
                   current={"milestone": EVIL, "milestoneIndex": EVIL, "milestoneCount": EVIL, "task": EVIL, "taskIndex": EVIL, "taskCount": EVIL, "gapRound": EVIL, "gapRounds": EVIL, "since": EVIL},
                   milestones=[ms(EVIL, EVIL, title=EVIL, layer=EVIL, gapRound=EVIL, gapRounds=EVIL, requirements=[EVIL], branch=EVIL, verifier={"result": EVIL, "sha": EVIL, "reqs": [EVIL]},
                                  tasks=[task(EVIL, EVIL, EVIL, EVIL, EVIL)])],
                   prs=[{"number": EVIL, "url": "javascript:" + EVIL2, "title": EVIL, "state": EVIL}])
    for stage in ("intent", "plan", "ready", "building", "done"):
        d = data(card("x", "ready"), {**hostile, "stage": stage}, name=EVIL)
        d["projects"][0]["repo"] = "/home/" + EVIL
        d["warnings"] = [EVIL]
        pages = [fb.render(d)] + [fb.render_project(d, s, c) for s, _ in fb.project_index(d) for c in (None, EVIL, "done")]
        for pg in pages:
            if pg is None:
                continue
            assert "<img" not in pg and "<svg" not in pg and 'href="javascript' not in pg and "onerror=alert" not in pg.replace("&lt;img src=x onerror=alert(1)&gt;", "")
            assert "alert" not in script_of(pg)


def test_a_hostile_project_page_renders_and_escapes_the_slug_in_urls():
    d = data(card(EVIL, "needs-you", title="t", stage="building", needs={**NEED, "milestone": EVIL}, milestones=[ms("M1", "building")]), name="ok")
    pg = fb.render(d)
    assert "%3Cimg" in pg and "<img" not in pg
    assert fb.render_project(d, "ok", EVIL) is not None and "<img" not in fb.render_project(d, "ok", EVIL)


def serve_in_thread(snapshot):
    srv = fb.make_server(snapshot, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


class FakeReader:
    def __init__(self, d):
        self.d, self.calls = d, 0

    def status(self, roots):
        self.calls += 1
        return self.d


def test_server_serves_board_and_json_read_only():
    d = data(card("a", "ready"))
    srv, port = serve_in_thread(fb.Snapshot(FakeReader(d), ["x"]))
    try:
        assert srv.server_address[0] == "127.0.0.1"
        base = f"http://127.0.0.1:{port}"
        r = urllib.request.urlopen(base + "/")
        assert r.status == 200 and "text/html" in r.headers["Content-Type"] and b"Needs you" in r.read()
        r = urllib.request.urlopen(base + "/status.json")
        assert json.loads(r.read()) == d and r.headers["Content-Type"] == "application/json"
        for method, path in (("GET", "/nope"), ("POST", "/"), ("PUT", "/status.json"), ("DELETE", "/")):
            try:
                urllib.request.urlopen(urllib.request.Request(base + path, method=method, data=b"x" if method != "GET" else None))
                raise AssertionError(f"{method} {path} must fail")
            except urllib.error.HTTPError as e:
                assert e.code in (404, 501)
    finally:
        srv.shutdown()
        srv.server_close()


def test_foreign_host_header_is_refused():
    srv, port = serve_in_thread(fb.Snapshot(FakeReader(data()), ["x"]))
    try:
        def get(path, host):
            req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers={"Host": host})
            try:
                return urllib.request.urlopen(req).status
            except urllib.error.HTTPError as e:
                return e.code
        for path in ("/", "/status.json"):
            assert get(path, f"127.0.0.1:{port}") == 200 and get(path, f"localhost:{port}") == 200
            for bad in ("evil.example", f"evil.example:{port}", "127.0.0.1", f"127.0.0.1.evil.example:{port}", f"localhost:{port + 1}"):
                assert get(path, bad) == 403, (path, bad)
    finally:
        srv.shutdown()
        srv.server_close()


def test_snapshot_caches_between_requests():
    r = FakeReader(data())
    s = fb.Snapshot(r, [])
    s.get()
    s.get()
    assert r.calls == 1
    s.get(max_age=-1)
    assert r.calls == 2


def test_tick_notifies_a_new_needs_you_card_once(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_HOME", str(tmp_path))
    sent = []
    base = data(card("a", "ready"))
    assert fb.tick(base, sent.append) == []  # first run records, never floods
    one = data(card("a", "needs-you", needs=NEED))
    assert len(fb.tick(one, sent.append)) == 1 and "Owner decides" in sent[0]
    assert fb.tick(one, sent.append) == [] and len(sent) == 1  # same card: once
    fb.tick(base, sent.append)  # card left the column
    assert len(fb.tick(one, sent.append)) == 1 and len(sent) == 2  # and came back
    two = data(card("a", "needs-you", needs={**NEED, "kind": "release-pr"}), card("b", "needs-you", needs=NEED))
    assert len(fb.tick(two, sent.append)) == 2  # a new kind on the same change and a second change
    assert json.loads((tmp_path / "board" / "seen.json").read_text())


def test_tick_survives_a_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_HOME", str(tmp_path))
    sent = []
    fb.tick(data(card("a", "ready")), sent.append)
    fb.tick(data(card("a", "needs-you", needs=NEED)), sent.append)
    assert fb.tick(data(card("a", "needs-you", needs=NEED)), sent.append) == []  # seen.json is read again each time


def test_applescript_quote_and_notify_without_a_shell(monkeypatch):
    assert fb.applescript_quote('say "hi" \\ now\nok') == '"say \\"hi\\" \\\\ now ok"'
    calls = []
    monkeypatch.setattr(fb.sys, "platform", "darwin")
    monkeypatch.setattr(fb.shutil, "which", lambda n: "/usr/bin/osascript")
    monkeypatch.setattr(fb.subprocess, "run", lambda cmd, **kw: calls.append((cmd, kw)) or subprocess.CompletedProcess(cmd, 0))
    assert fb.notify('app: "x"; rm -rf ~') is True
    cmd, kw = calls[0]
    assert cmd[:2] == ["osascript", "-e"] and "shell" not in kw and isinstance(cmd, list) and '\\"x\\"' in cmd[2]
    monkeypatch.setattr(fb.sys, "platform", "linux")
    assert fb.notify("x") is False and len(calls) == 1


def run_cli(*args, home):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          env={"HOME": str(home), "PATH": "/usr/bin:/bin", "FACTORY_HOME": str(home / ".factory")})


def test_install_dry_run_prints_paths_and_changes_nothing(tmp_path):
    p = run_cli("install", "--dry-run", "--port", "9123", "--roots", str(tmp_path / "work"), home=tmp_path)
    out = p.stdout
    assert p.returncode == 0
    assert f"{tmp_path}/.factory/bin/factory-board.py" in out and f"{tmp_path}/.factory/bin/factory-status.py" in out
    assert f"{tmp_path}/Library/LaunchAgents/dev.factory.board.plist" in out
    assert "launchctl bootout gui/" in out and "launchctl bootstrap gui/" in out
    assert "<key>RunAtLoad</key><true/>" in out and "<key>KeepAlive</key><true/>" in out and sys.executable in out
    assert f"{tmp_path}/.factory/board/board.log" in out and "<string>9123</string>" in out and str((tmp_path / "work").resolve()) in out
    assert out.strip().endswith("Board: http://127.0.0.1:9123/ (dry run, nothing changed)")
    assert not (tmp_path / "Library").exists() and not (tmp_path / ".factory").exists()


def test_uninstall_dry_run(tmp_path):
    p = run_cli("uninstall", "--dry-run", home=tmp_path)
    assert p.returncode == 0 and "launchctl bootout gui/" in p.stdout and "dev.factory.board.plist" in p.stdout


def test_plist_escapes_arguments(tmp_path):
    text = fb.plist_text(8765, ["/tmp/a&b"], tmp_path / "bin", tmp_path / "log")
    assert "/tmp/a&amp;b" in text and "<string>serve</string>" in text
