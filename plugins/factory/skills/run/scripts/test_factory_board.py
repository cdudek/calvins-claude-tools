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


def card(slug, column, title="Saved searches", needs=None, prs=(), milestones=(), current=None):
    return {"slug": slug, "title": title, "column": column, "approved": column != "backlog", "milestones": list(milestones), "current": current,
            "needs": needs, "prs": list(prs)}


def data(*cards, warnings=()):
    return {"generated": "2026-11-28T10:00:00Z", "warnings": list(warnings), "projects": [{"repo": "/home/u/projects/acme/app", "name": "app", "changes": list(cards)}]}


NEED = {"kind": "blocked", "text": "Owner decides the retention period.", "where": "In ~/projects/acme/app, run /factory:run x"}
CUR = {"milestone": "M2", "milestoneIndex": 2, "milestoneCount": 3, "task": "T1", "taskIndex": 1, "taskCount": 2, "gapRound": 1, "gapRounds": 3, "since": None}


def test_html_has_every_column_in_order_and_the_card_parts():
    page = fb.render(data(card("a", "needs-you", needs=NEED), card("b", "building", current=CUR, milestones=[{"id": "M1", "state": "shipped"}, {"id": "M2", "state": "building"}],
                                                                   prs=[{"number": 5, "url": "https://example.test/pr/5", "title": "Add it", "state": "draft"}])))
    heads = re.findall(r"<h2>([^<(]+)", page)
    assert heads == ["Needs you ", "Building ", "Ready ", "Backlog ", "Done "]
    assert 'http-equiv="refresh" content="15"' in page and "prefers-color-scheme:dark" in page and "width=device-width" in page
    assert "Owner decides the retention period." in page and "run /factory:run x" in page
    assert "M2 (2/3) · T1/2 · gap 1/3" in page and '<a href="https://example.test/pr/5"' in page and "#5 Add it (draft)" in page
    assert '<i class="shipped"' in page and "Nothing here." in page


def test_html_escapes_text_and_refuses_script_urls():
    evil = "<script>alert(1)</script>"
    page = fb.render(data(card("a", "needs-you", title=evil, needs={"kind": "blocked", "text": evil, "where": evil},
                               prs=[{"number": 1, "url": "javascript:alert(1)", "title": evil, "state": "open"}]), warnings=[evil]))
    assert "<script>" not in page and "&lt;script&gt;" in page and "javascript:" not in page.split("<body>")[1].split("href")[0]
    assert 'href="javascript' not in page


def test_html_escapes_every_interpolated_value_including_numbers():
    x = "<img src=x onerror=alert(1)>"
    cur = {"milestone": "M<b>", "milestoneIndex": x, "milestoneCount": x, "task": "T<i>", "taskIndex": 1, "taskCount": x, "gapRound": x, "gapRounds": x, "since": None}
    page = fb.render(data(card("a", "building", current=cur, milestones=[{"id": "M<b>", "state": x}],
                               prs=[{"number": x, "url": 'https://e.test/"><script>', "title": x, "state": "open"}])))
    assert "<img" not in page and "<b>" not in page and "<i>" not in page and "<script>" not in page
    assert page.count("&lt;img src=x onerror=alert(1)&gt;") >= 6


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
        assert r.status == 200 and "text/html" in r.headers["Content-Type"] and b"Factory board" in r.read()
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
