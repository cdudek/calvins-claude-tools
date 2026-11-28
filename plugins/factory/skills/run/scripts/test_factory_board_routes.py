"""The board's routes over HTTP, and a notification for each new needs item."""
import urllib.error
import urllib.request

from test_factory_board import EVIL, NEED, FakeReader, card, data, fb, full_project, serve_in_thread


def fetch(port, path, host=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers={"Host": host} if host else {})
    try:
        r = urllib.request.urlopen(req)
        return r.status, r.read().decode(), r.headers["Content-Type"]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), e.headers.get("Content-Type")


def test_project_routes_and_404s():
    d = full_project()
    srv, port = serve_in_thread(fb.Snapshot(FakeReader(d), ["x"]))
    try:
        assert fetch(port, "/")[0] == 200
        for path in ("/p/app/", "/p/app", "/p/app/2026-11-24-v1", "/p/app/done"):
            status, body, ctype = fetch(port, path)
            assert status == 200 and "text/html" in ctype and "<h1>app</h1>" in body, path
        for path in ("/p/nope/", "/p/app/nope", "/p/app/a/b", "/p/", "/q", "/p/app/%3Cimg%20src=x%3E"):
            status, body, ctype = fetch(port, path)
            assert status == 404 and "Not found" in body and "<img" not in body and "text/html" in ctype, path
        assert fetch(port, "/p/app/%3Cimg%20src=x%3E")[1].count("src=x") == 0  # the unknown name is never echoed
        for path in ("/p/app/", "/p/app/done", "/nope"):
            assert fetch(port, path, host="evil.example")[0] == 403 and fetch(port, path, host=f"127.0.0.1:{port}")[0] in (200, 404)
        for method in ("POST", "PUT", "DELETE"):
            try:
                urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/p/app/", method=method, data=b"x"))
                raise AssertionError(method)
            except urllib.error.HTTPError as e:
                assert e.code in (404, 501)
    finally:
        srv.shutdown()
        srv.server_close()


def test_every_new_needs_item_notifies_once_keyed_by_milestone(tmp_path, monkeypatch):
    monkeypatch.setenv("FACTORY_HOME", str(tmp_path))
    sent = []
    fb.tick(data(card("a", "ready")), sent.append)
    two = data(card("a", "needs-you", stage="building", needs=NEED, needsAll=[NEED, {**NEED, "milestone": "M3"}, {**NEED, "kind": "question", "milestone": None, "text": "Which tiers?"}]))
    assert len(fb.tick(two, sent.append)) == 3 and any("Which tiers?" in t for t in sent)
    assert fb.tick(two, sent.append) == []
    keys = fb.needs_keys(two)
    assert any(k.endswith("|blocked|M2") for k in keys) and any(k.endswith("|blocked|M3") for k in keys) and any(k.endswith("|question|") for k in keys)
    assert EVIL not in "".join(keys)
