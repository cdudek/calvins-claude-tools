#!/usr/bin/env python3
"""Usage: factory-board.py serve [--port 8765] [--roots DIR ...]
       factory-board.py install [--port 8765] [--roots DIR ...] [--dry-run]
       factory-board.py uninstall [--dry-run]
A small local board of every factory change, read only. It imports factory-status.py from its own folder and shows its JSON.
  serve      http.server on 127.0.0.1 only. GET / is the board (columns: needs you, building, ready, backlog, done; refreshes every 15 s);
             GET /status.json is the reader's JSON. A Host header other than 127.0.0.1:<port> or localhost:<port> gets 403. No POST, no state kept. Every 30 s the needs-you cards are compared with
             ~/.factory/board/seen.json; a card that is new there triggers one macOS notification (osascript, no shell; nothing off macOS).
  install    copies factory-board.py and factory-status.py to ~/.factory/bin/, writes ~/Library/LaunchAgents/dev.factory.board.plist
             (RunAtLoad, KeepAlive, log ~/.factory/board/board.log) and loads it with launchctl (a loaded copy is booted out first).
  uninstall  boots the agent out and removes the plist; ~/.factory/bin stays.
  --dry-run  prints what install or uninstall would do and changes nothing.
Env FACTORY_HOME overrides ~/.factory. Needs python3 3.9+.
"""
import argparse
import html
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
LABEL = "dev.factory.board"
COLUMNS = [("needs-you", "Needs you"), ("building", "Building"), ("ready", "Ready"), ("backlog", "Backlog"), ("done", "Done")]
TICK_SECS = 30


def load_reader():
    spec = importlib.util.spec_from_file_location("factory_status", HERE / "factory-status.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def home():
    return Path(os.environ.get("FACTORY_HOME") or Path.home() / ".factory")


# ---- notifications -------------------------------------------------------------------------------------------------

def needs_keys(data):
    """{key: text} of every needs-you card: one key per change and kind, so a new kind on the same change notifies again."""
    return {f"{p['repo']}|{c['slug']}|{c['needs']['kind']}": f"{p['name']}: {c['title']} - {c['needs']['text']}"
            for p in data["projects"] for c in p["changes"] if c["column"] == "needs-you" and c["needs"]}


def applescript_quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def notify(text):
    """One macOS notification; no shell, the text is an escaped AppleScript string. A no-op elsewhere. Returns True when it ran."""
    if sys.platform != "darwin" or not shutil.which("osascript"):
        return False
    script = f"display notification {applescript_quote(text[:240])} with title {applescript_quote('Factory needs you')}"
    try:
        return subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def tick(data, send=notify):
    """Notify for needs-you cards not seen before, then persist the current set (a card that left and comes back notifies again)."""
    seen_file = home() / "board" / "seen.json"
    try:
        seen = set(json.loads(seen_file.read_text()))
    except (OSError, ValueError, TypeError):
        seen = None  # first run: record, never flood
    now = needs_keys(data)
    new = [t for k, t in now.items() if seen is not None and k not in seen]
    for text in new:
        send(text)
    try:
        seen_file.parent.mkdir(parents=True, exist_ok=True)
        seen_file.write_text(json.dumps(sorted(now)))
    except OSError:
        pass
    return new


# ---- page ----------------------------------------------------------------------------------------------------------

CSS = """
:root{--bg:#f6f7f9;--fg:#1c2128;--mut:#5d6773;--card:#fff;--line:#d9dee4;--acc:#0b63ce;--warn:#b42318;--ok:#17703a}
@media (prefers-color-scheme:dark){:root{--bg:#14171b;--fg:#e6e9ed;--mut:#9aa4af;--card:#1e2329;--line:#333b44;--acc:#6aaaf5;--warn:#ff8b80;--ok:#6fd49a}}
*{box-sizing:border-box}body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:15px/1.4 system-ui,sans-serif}
h1{font-size:18px;margin:0 0 4px}.sub{color:var(--mut);font-size:13px;margin-bottom:16px}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;align-items:start}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:0 0 8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin-bottom:10px;overflow-wrap:anywhere}
.card.needs{border-left:4px solid var(--warn)}.proj{color:var(--mut);font-size:12px}.title{font-weight:600}
.bar{display:flex;gap:3px;margin:8px 0}.bar i{flex:1;height:6px;border-radius:3px;background:var(--line)}
.bar i.shipped,.bar i.merged{background:var(--ok)}.bar i.building{background:var(--acc)}.bar i.blocked,.bar i.hold{background:var(--warn)}
.cur,.where{font-size:13px;color:var(--mut)}.need{font-size:13px;color:var(--warn);margin-top:6px}
a{color:var(--acc)}.empty{color:var(--mut);font-size:13px}.warn{margin-top:20px;color:var(--mut);font-size:12px}
"""


def safe_href(url):
    return e(url) if str(url).startswith(("https://", "http://")) else None


def e(v):
    """Every value that reaches the page goes through here: str() first (plan files are untrusted, numbers may be markup), then escape, quotes included."""
    return html.escape(str(v), quote=True)


def card_html(p, c):
    out = [f'<div class="card{" needs" if c["column"] == "needs-you" else ""}">', f'<div class="proj">{e(p["name"])}</div>', f'<div class="title">{e(c["title"])}</div>']
    if c["milestones"]:
        out.append('<div class="bar">' + "".join(f'<i class="{e(m["state"])}" title="{e(m["id"])}: {e(m["state"])}"></i>' for m in c["milestones"]) + "</div>")
    cur = c["current"]
    if cur:
        task = f' · {e(cur["task"])}/{e(cur["taskCount"])}' if cur["task"] else ""
        out.append(f'<div class="cur">{e(cur["milestone"])} ({e(cur["milestoneIndex"])}/{e(cur["milestoneCount"])}){task} · gap {e(cur["gapRound"])}/{e(cur["gapRounds"])}</div>')
    if c["needs"]:
        out.append(f'<div class="need">{e(c["needs"]["text"])}</div><div class="where">{e(c["needs"]["where"])}</div>')
    for pr in c["prs"]:
        href = safe_href(pr["url"])
        label = e(f'#{pr["number"]} {pr["title"]}' + (" (draft)" if pr["state"] == "draft" else ""))
        out.append(f'<div class="where"><a href="{href}" rel="noopener">{label}</a></div>' if href else f'<div class="where">{label}</div>')
    out.append("</div>")
    return "".join(out)


def render(data):
    cols = []
    for key, label in COLUMNS:
        cards = [card_html(p, c) for p in data["projects"] for c in p["changes"] if c["column"] == key]
        cols.append(f'<section><h2>{label} ({len(cards)})</h2>' + ("".join(cards) or '<div class="empty">Nothing here.</div>') + "</section>")
    warns = "".join(f"<div>{e(w)}</div>" for w in data["warnings"])
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="refresh" content="15"><title>Factory board</title>'
            f'<style>{CSS}</style></head><body><h1>Factory board</h1><div class="sub">Updated {e(data["generated"])}. Read only.</div>'
            f'<div class="cols">{"".join(cols)}</div>' + (f'<div class="warn">{warns}</div>' if warns else "") + "</body></html>")


# ---- server --------------------------------------------------------------------------------------------------------

class Snapshot:
    """The reader's JSON, recomputed at most every `max_age` seconds however many tabs ask."""

    def __init__(self, reader, roots):
        self.reader, self.roots, self.lock, self.data, self.at = reader, roots, threading.Lock(), None, 0.0

    def get(self, max_age=10.0):
        with self.lock:
            if self.data is None or time.time() - self.at > max_age:
                self.data, self.at = self.reader.status(self.roots), time.time()
            return self.data


def make_server(snapshot, port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            port = self.server.server_address[1]  # DNS rebinding: a page on another origin can reach 127.0.0.1 but cannot choose the Host header it sends
            if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
                self.send_error(403)
                return
            path = urlparse(self.path).path
            if path == "/":
                body, ctype = render(snapshot.get()).encode(), "text/html; charset=utf-8"
            elif path == "/status.json":
                body, ctype = json.dumps(snapshot.get(), indent=1).encode(), "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(port, roots):
    reader = load_reader()
    snap = Snapshot(reader, roots)

    def loop():
        while True:
            try:
                tick(snap.get(max_age=0))
            except Exception as e:  # the notifier must never take the board down
                print(f"tick failed: {e}", file=sys.stderr, flush=True)
            time.sleep(TICK_SECS)

    threading.Thread(target=loop, daemon=True).start()
    srv = make_server(snap, port)
    print(f"Factory board on http://127.0.0.1:{port}/", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


# ---- launchd -------------------------------------------------------------------------------------------------------

def plist_text(port, roots, bin_dir, log):
    def s(x):
        return f"<string>{html.escape(str(x))}</string>"
    args = [sys.executable, bin_dir / "factory-board.py", "serve", "--port", port] + (["--roots", *roots] if roots else [])
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            f'<plist version="1.0"><dict><key>Label</key>{s(LABEL)}<key>ProgramArguments</key><array>{"".join(s(a) for a in args)}</array>'
            f'<key>RunAtLoad</key><true/><key>KeepAlive</key><true/><key>StandardOutPath</key>{s(log)}<key>StandardErrorPath</key>{s(log)}</dict></plist>\n')


def plist_path():
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def launchctl(*args, dry):
    print("launchctl " + " ".join(args))
    return 0 if dry else subprocess.run(["launchctl", *args], capture_output=True).returncode


def install(port, roots, dry):
    bin_dir, log, plist = home() / "bin", home() / "board" / "board.log", plist_path()
    for name in ("factory-board.py", "factory-status.py"):
        print(f"copy {HERE / name} -> {bin_dir / name}")
    print(f"write {plist}")
    if dry:
        print(plist_text(port, roots, bin_dir, log))
    else:
        bin_dir.mkdir(parents=True, exist_ok=True)
        log.parent.mkdir(parents=True, exist_ok=True)
        plist.parent.mkdir(parents=True, exist_ok=True)
        for name in ("factory-board.py", "factory-status.py"):
            shutil.copy2(HERE / name, bin_dir / name)
        plist.write_text(plist_text(port, roots, bin_dir, log))
    uid = os.getuid()
    launchctl("bootout", f"gui/{uid}/{LABEL}", dry=dry)  # fails when not loaded: fine
    rc = launchctl("bootstrap", f"gui/{uid}", str(plist), dry=dry)
    print(f"Board: http://127.0.0.1:{port}/" + (" (dry run, nothing changed)" if dry else ""))
    return rc


def uninstall(dry):
    plist = plist_path()
    launchctl("bootout", f"gui/{os.getuid()}/{LABEL}", dry=dry)
    print(f"remove {plist}")
    if not dry:
        plist.unlink(missing_ok=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Factory board; see the file header.")
    ap.add_argument("cmd", choices=["serve", "install", "uninstall"])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--roots", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    roots = [str(Path(r).expanduser().resolve()) for r in a.roots] if a.roots else None
    if a.cmd == "serve":
        return serve(a.port, roots or [Path.home() / "projects"])
    return install(a.port, roots, a.dry_run) if a.cmd == "install" else uninstall(a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
