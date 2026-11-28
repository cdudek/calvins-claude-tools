#!/usr/bin/env python3
"""Usage: factory-board.py serve [--port 8765] [--roots DIR ...]
       factory-board.py install [--port 8765] [--roots DIR ...] [--dry-run]
       factory-board.py uninstall [--dry-run]
A small local board of every factory change, read only. It imports factory-status.py from its own folder and shows its JSON.
  serve      http.server on 127.0.0.1 only. GET / is the overview (needs you, projects by stage; refreshes every 15 s), GET /p/<project>/ and /p/<project>/<slug> a project page (unknown: 404);
             GET /status.json is the reader's JSON. A Host header other than 127.0.0.1:<port> or localhost:<port> gets 403. No POST, no state kept. Every 30 s the needs items are compared with
             ~/.factory/board/seen.json; an item that is new there triggers one macOS notification (osascript, no shell; nothing off macOS).
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
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

HERE = Path(__file__).resolve().parent
LABEL = "dev.factory.board"
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
    """{key: text} of every needs item: one key per project, change, kind and milestone, so a new kind or milestone on the same change notifies again."""
    return {f"{p['repo']}|{c['slug']}|{n.get('kind')}|{n.get('milestone') or ''}": f"{p['name']}: {c['title']} - {n.get('text', '')}"
            for p in data["projects"] for c in p["changes"] for n in needs_of(c)}


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
:root{color-scheme:light dark;--bg:#F8F9FC;--surface:#FFFFFF;--surface2:#F0F2F7;--sep:#F0F2F7;--border:#D0D4DE;--control:#808695;--fg:#101627;--fg2:#494F61;--muted:#626979;--def:#F0F2F7;--defH:#D0D4DE;--acc:#6E4EF0;--accSoft:#EAEDFF;--accSoftFg:#5A3CC3;--link:#6E4EF0;--focus:#8071FE;--hover:#F0F2F7;--sucSoft:#F0F9F4;--sucFg:#026E43;--warSoft:#FBF6EE;--warFg:#824F01;--danFg:#A4271E;--danSoft:#FFF4F2;--verSoft:#F4F7FE;--verFg:#1155BC;--sel:#F5F6FE;--pend:#808695}
@media (prefers-color-scheme:dark){:root{--bg:#121214;--surface:#19191C;--surface2:#232327;--sep:#26262B;--border:#303036;--control:#6B6B74;--fg:#F7F7F8;--fg2:#D2D2D7;--muted:#9C9CA5;--def:#2A2A2F;--defH:#36363C;--acc:#7357F6;--accSoft:#2D274C;--accSoftFg:#BABEFE;--link:#BABEFE;--focus:#9A98FF;--hover:#232327;--sucSoft:#1A322A;--sucFg:#89D9AB;--warSoft:#3A2D18;--warFg:#ECBB70;--danFg:#FFAB9E;--danSoft:#3E2323;--verSoft:#1B2944;--verFg:#A7C4FF;--sel:#212124;--pend:#6B6B74}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/21px "Plus Jakarta Sans",system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--link)}a:hover{color:var(--fg)}
.mono,code{font-family:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace;overflow-wrap:anywhere}
button:focus-visible,a:focus-visible,select:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.page{padding:24px 32px 48px}.wrap{max-width:1376px;margin:0 auto;display:flex;flex-direction:column;gap:32px}.wrap.tight{gap:24px}
h1,h2,h3,p{margin:0}h1{font-size:22px;line-height:30px;font-weight:800;letter-spacing:-.02em}
h2{font-size:16px;line-height:22px;font-weight:700;display:flex;align-items:center;flex-wrap:wrap;gap:8px}h2.big{font-size:18px;line-height:24px}
h2 small,.hint{font-size:12px;font-weight:400;color:var(--muted)}
.hd{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 16px}.sub{color:var(--muted);font-size:13px}.dim{color:var(--muted);font-size:12px}
.sec{display:flex;flex-direction:column;gap:12px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:16px}.pad{padding:20px}.col{display:flex;flex-direction:column;gap:12px}
.chip{display:inline-flex;align-items:center;gap:6px;padding:2px 10px;border-radius:999px;font-size:12px;line-height:18px;font-weight:600;background:var(--def);color:var(--fg2);white-space:nowrap}
.chip i{width:6px;height:6px;border-radius:50%;background:currentColor}
.st-late{background:var(--danSoft);color:var(--danFg)}.st-ready{background:var(--accSoft);color:var(--accSoftFg)}.st-deciding{background:var(--warSoft);color:var(--warFg)}
.st-progress{background:var(--acc);color:#fff}.st-accepted{background:var(--sucSoft);color:var(--sucFg)}.st-open{background:var(--def);color:var(--muted)}.qchip{background:var(--verSoft);color:var(--verFg)}
.cnt{display:inline-block;min-width:22px;padding:0 7px;border-radius:999px;background:var(--def);color:var(--fg2);font-size:12px;line-height:20px;font-weight:600;text-align:center}
.btn{font:inherit;font-weight:600;border:0;cursor:pointer;border-radius:12px;padding:0 14px;height:36px;background:var(--acc);color:#fff}
.btn.s{height:28px;font-size:12px;border-radius:10px;padding:0 12px}.btn.tonal{background:var(--def);color:var(--fg)}.btn.tonal:hover{background:var(--defH)}
.needs{list-style:none;margin:0;padding:0;overflow:hidden}.needs li,.pneed{display:flex;flex-wrap:wrap;align-items:flex-start;gap:10px 16px;padding:14px 20px;border-top:1px solid var(--sep)}.needs li:first-child{border-top:0}
.pneed{padding:12px 0}.nbody{flex:999 1 400px;min-width:0;display:flex;flex-direction:column;gap:6px}.nhead{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px}
.nhead a{font-weight:700;color:var(--fg);text-decoration:none}.nhead a:hover{text-decoration:underline}.ntext{color:var(--fg2);font-size:13px;line-height:19px}
.cmdbox{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:6px 6px 6px 12px;background:var(--surface2);border-radius:12px}.cmdbox code{flex:1 1 200px;min-width:0;font-size:12px}.cmdbox .btn{min-width:128px}
.live{font-size:12px;color:var(--muted);min-height:17px}
.scroll{overflow:auto;max-height:1100px}
table.lanes{border-collapse:separate;border-spacing:0;width:100%;min-width:1080px;table-layout:fixed}
table.lanes th,table.lanes td{vertical-align:top;text-align:left;border-top:1px solid var(--sep)}
table.lanes thead th{position:sticky;top:0;z-index:2;background:var(--surface2);border-top:0;border-bottom:1px solid var(--border);padding:10px 12px;font-weight:600;font-size:12px;line-height:16px}
table.lanes th[scope=row]{position:sticky;left:0;z-index:1;background:var(--surface);padding:14px 16px;width:180px;font-weight:400}
table.lanes thead th:first-child{left:0;z-index:3;width:180px}table.lanes td{padding:10px 8px;border-left:1px solid var(--sep)}
.defn{display:block;font-size:11px;line-height:15px;font-weight:400;color:var(--muted)}
.pname{font-weight:700;text-decoration:none;color:var(--fg)}.flag{font-size:12px;line-height:17px;display:block}.f-late{color:var(--danFg)}.f-hold{color:var(--warFg)}.f-q{color:var(--verFg)}.f-plan{color:var(--link)}.f-none{color:var(--muted)}
a.mini{display:flex;flex-direction:column;gap:6px;text-decoration:none;color:var(--fg);border:1px solid var(--border);border-radius:12px;padding:10px 12px;background:var(--surface)}a.mini:hover{background:var(--hover)}
.mini b{font-size:13px;line-height:19px;font-weight:600}.mini .meta{font-size:12px;line-height:17px;color:var(--fg2)}.cell{display:flex;flex-direction:column;gap:8px}.cell>a:not(.mini){font-size:12px}
.bar{display:flex;gap:2px}.bar i{flex:1;height:4px;border-radius:2px;box-shadow:inset 0 0 0 1px var(--pend)}.bar.lg i{height:6px;border-radius:3px}
.bar i.b-shipped{background:var(--sucFg);box-shadow:none}.bar i.b-building{background:var(--acc);box-shadow:none}.bar i.b-blocked{background:var(--danFg);box-shadow:none}.bar i.b-hold{background:var(--warFg);box-shadow:none}
.phone{display:none;flex-direction:column;gap:12px}.phone a{display:flex;flex-direction:column;gap:6px;padding:14px 16px;border:1px solid var(--border);border-radius:16px;background:var(--surface);text-decoration:none;color:var(--fg)}
.crumbs{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 16px}.crumbs ol{list-style:none;margin:0;padding:0;display:flex;gap:8px;font-size:13px;color:var(--muted)}
.crumbs label{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)}.crumbs select{height:32px;border-radius:12px;border:1px solid var(--control);background:var(--surface);color:var(--fg);font:inherit;font-size:13px;padding:0 8px}
.mono-s{font-size:11px;line-height:16px;color:var(--muted)}.accent{border-color:var(--acc)}
nav.tabs{display:flex;flex-wrap:wrap;gap:4px 24px;border-bottom:1px solid var(--border)}
nav.tabs a{display:inline-flex;align-items:center;gap:8px;padding:10px 2px 9px;margin-bottom:-1px;border-bottom:2px solid transparent;font-size:13px;font-weight:600;color:var(--fg2);text-decoration:none}
nav.tabs a[aria-current=page]{border-bottom-color:var(--acc);font-weight:700;color:var(--fg)}nav.tabs .stg{font-size:11px;color:var(--muted);font-weight:600}nav.tabs .chip{font-size:11px}
.twocol{display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start}.main{flex:999 1 640px;min-width:0;display:flex;flex-direction:column;gap:12px}.aside{flex:1 1 320px;min-width:0;display:flex;flex-direction:column;gap:16px}
.aside ol{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:10px}.aside li{font-size:13px}.fl{display:flex;flex-direction:column;gap:2px;padding-top:10px;border-top:1px solid var(--sep);font-size:13px}.fl .t{color:var(--danFg)}
.bar-h{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px;margin-top:12px}.seg{display:flex;gap:2px;padding:3px;background:var(--surface2);border-radius:999px}
.seg button{all:unset;cursor:pointer;padding:4px 12px;border-radius:999px;font-size:12px;font-weight:600;color:var(--fg2)}.seg button[aria-checked=true]{background:var(--surface);color:var(--fg)}.seg button:focus-visible{outline:2px solid var(--focus)}
.tools{display:flex;flex-wrap:wrap;gap:8px}.group{overflow:hidden}.group ul{list-style:none;margin:0;padding:0}.group>h3{margin:0}
button.grow{all:unset;box-sizing:border-box;display:flex;justify-content:space-between;gap:8px;width:100%;padding:10px 16px;background:var(--surface2);font-size:12px;line-height:16px;font-weight:600;color:var(--muted);cursor:pointer}
button.mrow{all:unset;box-sizing:border-box;display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;width:100%;padding:12px 16px;cursor:pointer}
button.mrow:hover,button.grow:hover{background:var(--hover)}button.mrow:focus-visible,button.grow:focus-visible{outline:2px solid var(--focus);outline-offset:-2px}
li.ms{border-top:1px solid var(--sep)}li.ms:first-child{border-top:0}.mid{width:44px;font-size:12px;font-weight:600;color:var(--fg2)}.mtitle{flex:999 1 220px;min-width:0;font-weight:600}.lbl{font-size:11px;color:var(--muted)}
.detail{padding:4px 16px 18px 72px;display:flex;flex-direction:column;gap:12px}.detail[hidden]{display:none}
.now{background:var(--sel)}.now .head{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:12px 16px}.now h3{flex:999 1 220px;min-width:0;font-size:14px;font-weight:700}
.box{display:flex;flex-direction:column;gap:4px;padding:12px 14px;border-radius:12px;font-size:13px}.box.bad{background:var(--danSoft);color:var(--danFg)}.box.q{background:var(--verSoft);color:var(--verFg)}.box b{font-weight:600}
.tasks{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}.tasks li{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;padding:8px 12px;border:1px solid var(--border);border-radius:12px}
.tasks .tid{width:72px;font-size:12px;color:var(--fg2)}.tasks .ttl{flex:999 1 200px;min-width:0;font-size:13px}
.facts{display:flex;flex-wrap:wrap;gap:8px 24px;font-size:13px;color:var(--fg2)}.facts b,.kv b{color:var(--fg);font-weight:600}.kv{display:flex;flex-direction:column;gap:6px;font-size:13px;color:var(--fg2)}
ul.plain{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:4px;color:var(--fg2)}ul.nolist{list-style:none;margin:0;padding:0}
.pm{border:1px solid var(--border);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:6px}.pm .r{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px}
.done-li{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 16px;padding:12px 0;border-top:1px solid var(--sep)}.done-li:first-child{border-top:0}
details summary{cursor:pointer}pre{margin:8px 0 0;white-space:pre-wrap;font-size:11px;line-height:16px}
.empty{color:var(--muted)}footer{font-size:12px;color:var(--muted)}
@media (max-width:720px){.page{padding:16px 16px 40px}.wide{display:none}.phone{display:flex}.detail{padding:4px 16px 16px}}
"""

JS = """
(function(){
var live=document.querySelector('[role=status]');
function say(t){if(live)live.textContent=t}
function setOpen(b,open){b.setAttribute('aria-expanded',open?'true':'false');var c=document.getElementById(b.getAttribute('aria-controls'));if(c)c.hidden=!open;var k=b.querySelector('.caret');if(k)k.textContent=open?'\\u2212':'+'}
function copy(b){var box=b.closest('.cmdbox'),code=box&&box.querySelector('code'),cmd=b.getAttribute('data-cmd'),title=b.getAttribute('data-title');
function done(ok){if(!ok&&code){var r=document.createRange();r.selectNodeContents(code);var s=getSelection();s.removeAllRanges();s.addRange(r)}
b.textContent=ok?'Copied':'Press Cmd+C';say(ok?'Copied the command for '+title+'.':'Copy did not work. Select the command and press Cmd+C.');
clearTimeout(b._t);b._t=setTimeout(function(){b.textContent='Copy command'},2000)}
try{navigator.clipboard.writeText(cmd).then(function(){done(true)},function(){done(false)})}catch(e){done(false)}}
function filter(f){document.querySelectorAll('[data-filter]').forEach(function(x){x.setAttribute('aria-checked',x.getAttribute('data-filter')===f?'true':'false')});
var any=false;document.querySelectorAll('li.ms').forEach(function(li){var show=f==='all'||(' '+li.getAttribute('data-tags')+' ').indexOf(' '+f+' ')>=0;li.hidden=!show;any=any||show});
document.querySelectorAll('.group').forEach(function(g){g.hidden=!g.querySelector('li.ms:not([hidden])')});var n=document.getElementById('nomatch');if(n)n.hidden=any}
function openHash(){var h=decodeURIComponent(location.hash.slice(1));if(!h)return;var li=document.getElementById(h);if(!li||!li.classList.contains('ms'))return;
if(li.hidden)filter('all');var g=li.closest('.group');if(g)setOpen(g.querySelector('.grow'),true);var b=li.querySelector('.mrow');setOpen(b,true);li.scrollIntoView({block:'center'});b.focus()}
document.querySelectorAll('[data-open]').forEach(function(b){setOpen(b,b.getAttribute('data-open')==='1')});
var touched=false;
document.addEventListener('click',function(ev){touched=true;var t=ev.target.closest('button');if(!t)return;
if(t.classList.contains('copy'))copy(t);
else if(t.classList.contains('mrow')||t.classList.contains('grow'))setOpen(t,t.getAttribute('aria-expanded')!=='true');
else if(t.hasAttribute('data-filter'))filter(t.getAttribute('data-filter'));
else if(t.id==='expand-all'||t.id==='collapse-all'){var on=t.id==='expand-all';document.querySelectorAll('.mrow,.grow').forEach(function(x){setOpen(x,on)})}});
document.addEventListener('keydown',function(){touched=true});
document.addEventListener('change',function(ev){var s=ev.target;if(s.matches&&s.matches('select[data-nav]'))location.href=s.value});
window.addEventListener('hashchange',openHash);openHash();
if(document.body.hasAttribute('data-refresh'))setTimeout(function(){if(!touched)location.reload()},15000);
})();
"""

STAGES = [("intent", "Intent", "An idea with outcomes, no plan"), ("plan", "Plan", "Plan written, waiting for approval"), ("ready", "Ready", "Approved, not started"),
          ("building", "Building", "A goal is running or stopped"), ("done", "Done", "Every milestone shipped")]
KINDS = {"blocked": ("Blocked", "st-late", 0), "hold-review": ("Review hold", "st-deciding", 1), "gallery": ("Gallery review", "st-deciding", 2), "release-pr": ("Release PR", "st-deciding", 2),
         "approve-plan": ("Approve plan", "st-ready", 3), "question": ("Question", "qchip", 4)}
MS_CHIP = {"shipped": ("Shipped", "st-accepted"), "merged": ("Merged", "st-accepted"), "building": ("Building", "st-progress"), "blocked": ("Blocked", "st-late"),
           "hold": ("Hold", "st-deciding"), "incomplete": ("Stopped", "st-deciding"), "pending": ("Pending", "st-open")}
TASK_CHIP = {"done": ("Done", "st-accepted"), "building": ("Building", "st-progress"), "failed": ("Failed", "st-late"), "pending": ("Pending", "st-open")}
BAR = {"shipped": "b-shipped", "merged": "b-shipped", "building": "b-building", "blocked": "b-blocked", "hold": "b-hold", "incomplete": "b-hold"}
GROUPS = {"components": "Components", "layouts": "Layouts", "backend": "Backend", "screens": "Screens", "rest": "Rest"}
ACTIVE = ("building", "blocked", "hold", "incomplete")


def safe_href(url):
    return e(url) if str(url).startswith(("https://", "http://")) else None


def e(v):
    """Every value that reaches the page goes through here: str() first (plan files are untrusted, numbers may be markup), then escape, quotes included."""
    return html.escape(str(v), quote=True)


def slugify(name):
    return re.sub(r"[^a-z0-9._-]+", "-", str(name).lower()).strip("-.") or "project"


def project_index(data):
    """[(url slug, project)]: the slug is the project name made safe, a second project of the same name gets -2, -3."""
    seen, out = {}, []
    for p in data["projects"]:
        s = slugify(p["name"])
        seen[s] = seen.get(s, 0) + 1
        out.append((s if seen[s] == 1 else f"{s}-{seen[s]}", p))
    return out


def url_project(pslug, cslug=None, anchor=None):
    u = "/p/" + quote(pslug, safe="") + "/" + (quote(cslug, safe="") if cslug else "")
    return u + ("#" + quote(anchor, safe="") if anchor else "")


def parse_ts(s):
    """A reader timestamp (`...Z` or a bare date) as an aware datetime, or None."""
    try:
        s = str(s)
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if "T" in s else datetime.strptime(s, "%Y-%m-%d").astimezone()
    except ValueError:
        return None


def fmt_age(secs):
    m = max(int(secs // 60), 0)
    if m < 60:
        return f"{m} min"
    if m < 1440:
        return f"{m // 60} h" + (f" {m % 60} min" if m % 60 else "")
    d = m // 1440
    return f"{d} day" + ("s" if d != 1 else "")


def fmt_at(s, now=None, date_only=False):
    d = parse_ts(s)
    if not d:
        return None
    d, now = d.astimezone(), (now or datetime.now().astimezone())
    if "T" not in str(s) or date_only:
        return f"{d.day} {d:%b}"
    return f"{d:%H:%M}" if d.date() == now.date() else f"{d.day} {d:%b} {d:%H:%M}"


def needs_of(c):
    items = c.get("needsAll") or ([c["needs"]] if c.get("needs") else [])
    return [n for n in items if isinstance(n, dict)]


def all_needs(data):
    """[(project slug, project, change, need)] longest waiting first; a need without a known start goes last."""
    out = [(ps, p, c, n) for ps, p in project_index(data) for c in p["changes"] for n in needs_of(c)]
    far = datetime.max.replace(tzinfo=timezone.utc)
    return sorted(out, key=lambda t: (parse_ts(t[3].get("since")) or far, KINDS.get(t[3].get("kind"), ("", "", 9))[2]))


def kind_chip(kind):
    label, cls, _ = KINDS.get(kind, (str(kind), "st-open", 9))
    return f'<span class="chip {cls}"><i></i>{e(label)}</span>'


def chip(label, cls):
    return f'<span class="chip {cls}"><i></i>{e(label)}</span>'


def cmd_box(cmd, title):
    if not cmd:
        return ""
    return (f'<div class="cmdbox"><code class="mono">{e(cmd)}</code><button type="button" class="btn s tonal copy" data-cmd="{e(cmd)}" data-title="{e(title)}" '
            f'aria-label="Copy command for {e(title)}">Copy command</button></div>')


def need_title(p, c, n, with_project=True):
    parts = ([p["name"]] if with_project else []) + [c["title"]] + ([n["milestone"]] if n.get("milestone") else [])
    return " · ".join(str(x) for x in parts)


def need_item(ps, p, c, n, now, overview=True):
    title = need_title(p, c, n, overview)
    href = url_project(ps, c["slug"], n.get("milestone"))
    since = parse_ts(n.get("since"))
    age = f'<span class="dim">waiting {e(fmt_age((now - since).total_seconds()))}</span>' if since else ""
    if overview:
        head = f'<div class="nhead"><a href="{e(href)}" aria-label="Open {e(title)}">{e(title)}</a>{age}</div>'
    else:
        head = f'<div class="nhead"><a href="{e(href)}">{e(title)}</a>{age}</div>'
    return (f'{kind_chip(n.get("kind"))}<div class="nbody">{head}<span class="ntext">{e(n.get("text", ""))}</span>'
            f'{cmd_box(n.get("cmd"), title)}<span class="dim">{e(n.get("where", ""))}</span></div>')


def num(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


def count_label(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


def task_counts(c):
    ms = c["milestones"]
    return len(ms), sum(1 for m in ms for t in m["tasks"] if "-gap" not in str(t.get("id")))


def card_meta(c):
    stage = c.get("stage")
    nm, nt = task_counts(c)
    cur = c.get("current") or {}
    if stage == "intent":
        n = len(c.get("outcomes", []))
        return (count_label(n, "outcome") + ", no plan yet") if n else "No outcomes recorded, no plan yet"
    if stage == "plan":
        return f"{count_label(nm, 'milestone')}, {count_label(nt, 'task')}"
    if stage == "ready":
        when = fmt_at(c.get("approvedAt"), date_only=True)
        return ("Approved " + (when + " · " if when else "") + count_label(nm, "milestone")) if c.get("approved") else count_label(nm, "milestone")
    if stage == "done":
        when = fmt_at(c.get("doneAt"), date_only=True)
        return "Shipped" + (f" {when}" if when else "")
    bits = []
    if cur:
        bits.append(f"Milestone {cur.get('milestoneIndex')} of {cur.get('milestoneCount')}")
        if cur.get("task") and "gap" not in str(cur["task"]):
            bits.append(f"task {cur.get('taskIndex')} of {cur.get('taskCount')} building")
        elif cur.get("task"):
            bits.append("fix task building")
        if cur.get("gapRound"):
            bits.append(f"fix round {cur['gapRound']} of {cur.get('gapRounds')}")
    return " · ".join(bits) or count_label(nm, "milestone")


def card_chip(c):
    kinds = [n.get("kind") for n in needs_of(c)]
    for k in ("blocked", "hold-review", "release-pr", "gallery", "approve-plan"):
        if k in kinds:
            return kind_chip(k)
    qn = sum(1 for q in c.get("questions", []) if q.get("open"))
    if qn:
        return chip(count_label(qn, "question"), "qchip")
    return chip("Building", "st-progress") if c.get("stage") == "building" and (c.get("run") or {}).get("state") == "running" else ""


def bar_html(ms, big=False):
    return f'<span class="bar{" lg" if big else ""}" aria-hidden="true">' + "".join(f'<i class="{BAR.get(m.get("state"), "")}"></i>' for m in ms) + "</span>"


def mini_card(ps, c):
    meta = card_meta(c)
    bar = bar_html(c["milestones"]) if c.get("stage") == "building" and c["milestones"] else ""
    return (f'<a class="mini" href="{e(url_project(ps, c["slug"]))}" aria-label="Open {e(c["title"])}: {e(meta)}"><b>{e(c["title"])}</b>{bar}'
            f'<span class="meta">{e(meta)}</span>{card_chip(c)}</a>')


def urgency(p):
    ranks = [KINDS.get(n.get("kind"), ("", "", 9))[2] for c in p["changes"] for n in needs_of(c)]
    if ranks:
        return min(ranks)
    return 5 if any(c.get("stage") == "building" for c in p["changes"]) else 6


def project_flag(p):
    kinds = [n.get("kind") for c in p["changes"] for n in needs_of(c)]
    n = lambda *ks: sum(1 for k in kinds if k in ks)  # noqa: E731
    bits = []
    if n("blocked"):
        bits.append(f"{n('blocked')} blocked")
    if n("hold-review"):
        bits.append(count_label(n("hold-review"), "hold") + " to review")
    if n("release-pr", "gallery"):
        bits.append(count_label(n("release-pr", "gallery"), "release") + " to merge")
    if n("approve-plan"):
        bits.append(count_label(n("approve-plan"), "plan") + " to approve")
    if n("question"):
        bits.append(count_label(n("question"), "open question"))
    cls = "f-late" if n("blocked") else "f-hold" if n("hold-review", "release-pr", "gallery") else "f-plan" if n("approve-plan") else "f-q" if n("question") else "f-none"
    return (", ".join(bits) or "Nothing waits on you"), cls


def page(title, body, refresh=False):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            + ('<meta http-equiv="refresh" content="15">' if refresh else "") + f"<title>{e(title)}</title><style>{CSS}</style></head>"
            f'<body{" data-refresh" if not refresh else ""}><div class="page"><div class="wrap{"" if refresh else " tight"}">{body}</div></div><script>{JS}</script></body></html>')


def as_of(data):
    d = parse_ts(data.get("generated"))
    return f"Data as of {d.astimezone():%H:%M}" if d else "Data time unknown"


def render(data):
    """GET /: the overview."""
    now = datetime.now(timezone.utc)
    idx = sorted(project_index(data), key=lambda t: (urgency(t[1]), t[1]["name"]))
    needs = all_needs(data)
    n_html = "".join(f"<li>{need_item(ps, p, c, n, now)}</li>" for ps, p, c, n in needs)
    counts = {k: sum(1 for _, p in idx for c in p["changes"] if c.get("stage") == k) for k, _, _ in STAGES}
    head = "".join(f'<th scope="col"><span>{e(name)} <span class="mono dim">{counts[k]}</span></span><span class="defn">{e(d)}</span></th>' for k, name, d in STAGES)
    rows, phone = [], []
    for ps, p in idx:
        flag, fcls = project_flag(p)
        cells = []
        for k, _, _ in STAGES:
            cs = [c for c in p["changes"] if c.get("stage") == k]
            more = f'<a href="{e(url_project(ps))}">{len(cs) - 2} more</a>' if len(cs) > 2 else ""
            cells.append("<td><div class=\"cell\">" + "".join(mini_card(ps, c) for c in cs[:2]) + more + ('<span class="dim" aria-label="None">–</span>' if not cs else "") + "</div></td>")
        rows.append(f'<tr><th scope="row"><a class="pname" href="{e(url_project(ps))}">{e(p["name"])}</a><span class="flag {fcls}">{e(flag)}</span></th>{"".join(cells)}</tr>')
        summary = " · ".join(f"{name} {n}" for k, name, _ in STAGES for n in [sum(1 for c in p["changes"] if c.get("stage") == k)] if n)
        phone.append(f'<a href="{e(url_project(ps))}"><b>{e(p["name"])}</b><span class="flag {fcls}">{e(flag)}</span><span class="dim">{e(summary)}</span></a>')
    warns = "".join(f"<div>{e(w)}</div>" for w in data.get("warnings", []))
    body = (f'<header class="hd"><h1>Factory</h1><span class="sub">{count_label(len(idx), "project")}. {e(as_of(data))}, refreshed every 15 seconds.</span></header>'
            f'<section aria-labelledby="needs" class="sec"><h2 id="needs">Needs you <span class="cnt">{len(needs)}</span><small>Longest waiting first</small></h2>'
            + (f'<ol class="card needs">{n_html}</ol>' if needs else '<p class="empty">Nothing waits on you.</p>')
            + '<p role="status" aria-live="polite" class="live"></p></section>'
            '<section aria-labelledby="projects" class="sec"><h2 id="projects">Projects<small>Most urgent first. A change moves left to right.</small></h2>'
            f'<div class="card scroll wide" role="region" aria-label="Projects by stage" tabindex="0"><table class="lanes"><thead><tr><th scope="col">Project</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div><div class="phone">{"".join(phone)}</div></section>'
            + (f'<div class="dim">{warns}</div>' if warns else "")
            + '<footer>Raw data: <a class="mono" href="/status.json">status.json</a></footer>')
    return page("Factory overview", body, refresh=True)


def short_home(path):
    h = str(Path.home())
    return "~" + str(path)[len(h):] if str(path).startswith(h + "/") else str(path)


def milestone_detail(m, fails, qs):
    out = []
    if fails:
        out.append('<div class="box bad"><b>What failed</b>' + "".join(f'<span>{e(f["text"])}' + (f' <span class="mono-s">({e(fmt_at(f.get("at")))})</span>' if fmt_at(f.get("at")) else "") + "</span>" for f in fails) + "</div>")
    if qs:
        out.append('<div class="box q"><b>Open question</b>' + "".join(f"<span>{e(q['id'])}. {e(q['text'])}</span>" for q in qs) + "</div>")
    v = m.get("verifier") or {}
    if v.get("result") == "PASS":
        vt = f"PASS on {str(v.get('sha'))[:7]}"
    elif v.get("result") == "FAIL":
        vt = "FAIL " + ", ".join(str(r) for r in v.get("reqs", [])) + f" on {str(v.get('sha'))[:7]}"
    else:
        vt = "not run yet" if m.get("state") == "pending" else "no result recorded"
    tasks = []
    for t in m["tasks"]:
        label, cls = TASK_CHIP.get(t.get("state"), ("Pending", "st-open"))
        meta = " ".join(str(x) for x in (t.get("model"), t.get("effort")) if x)
        tasks.append(f'<li><span class="mono tid">{e(t.get("id"))}</span><span class="ttl">{e(t.get("title") or "")}</span><span class="mono lbl">{e(meta)}</span>{chip(label, cls)}</li>')
    reqs = ", ".join(str(r) for r in m.get("requirements", [])) or "none listed"
    branch = ("planned: " if m.get("state") == "pending" else "") + str(m.get("branch") or "")
    out.append(f'<span class="sub"><b>Verifier</b> {e(vt)}</span>')
    out.append(f'<ul class="tasks" aria-label="Tasks of {e(m["id"])}">{"".join(tasks)}</ul>' if tasks else '<span class="dim">No tasks planned yet.</span>')
    out.append(f'<div class="facts"><span><b>Covers</b> <span class="mono">{e(reqs)}</span></span><span><b>Branch</b> <span class="mono">{e(branch)}</span></span></div>')
    return "".join(out)


def ms_labels(m):
    planned = [t for t in m["tasks"] if "-gap" not in str(t.get("id"))]
    done = sum(1 for t in planned if t.get("state") == "done")
    gap = f"fix round {m.get('gapRound')} of {m.get('gapRounds')}" if m.get("gapRound") else ""
    return f"{done} of {len(planned)} tasks", gap


def building_view(ps, p, c):
    ms = c["milestones"]
    fails = {m["id"]: [f for f in c.get("failures", []) if f.get("milestone") == m["id"]] for m in ms}
    openq = {m["id"]: [q for q in c.get("questions", []) if q.get("open") and q.get("milestone") == m["id"]] for m in ms}
    st = {s: sum(1 for m in ms if m["state"] == s) for s in MS_CHIP}
    shipped = st["shipped"] + st["merged"]
    nq = sum(1 for q in c.get("questions", []) if q.get("open"))
    act = next((i for i, m in enumerate(ms) if m["state"] in ACTIVE), None)
    summary = f"{shipped} of {len(ms)} milestones shipped."
    if act is not None:
        a = ms[act]
        phrase = {"blocked": "is blocked" + (" after its last fix round" if num(a.get("gapRound")) and num(a.get("gapRound")) >= num(a.get("gapRounds")) else ""), "hold": "is held for your review",
                  "building": "is building", "incomplete": "stopped before it finished"}[a["state"]]
        summary += f" {a['id']} (milestone {act + 1}) {phrase}" + (f", and {count_label(nq, 'question')} {'is' if nq == 1 else 'are'} open." if nq else ".")
    elif nq:
        summary += f" {count_label(nq, 'question')} {'is' if nq == 1 else 'are'} open."
    tail = (f" It lands on <span class=\"mono\">{e(c['integration'])}</span>" if c.get("integration") else "")
    if c.get("approvedSha"):
        when = fmt_at(c.get("approvedAt"), date_only=True)
        tail += (", approved" if tail else " Approved") + f" at <span class=\"mono\">{e(c['approvedSha'])}</span>" + (f" on {e(when)}" if when else "")
    tail = (tail + ".") if tail else ""
    run = c.get("run") or {}
    status = (next((kind_chip(k) for k in ("blocked", "hold-review") if k in [n.get("kind") for n in needs_of(c)]), None)
              or (chip("Building", "st-progress") if run.get("state") == "running" else chip("Stopped", "st-open")))
    legend = " · ".join(f"{n} {lbl}" for lbl, n in (("shipped", shipped), ("building", st["building"]), ("blocked", st["blocked"]), ("hold", st["hold"]), ("stopped", st["incomplete"]), ("pending", st["pending"])) if n)
    outs = c.get("outcomes", [])
    intent = ""
    if outs:
        rq = f", {count_label(num(c.get('requirementCount')), 'requirement')}" if num(c.get("requirementCount")) else ""
        intent = (f'<details><summary><b>Intent: {count_label(len(outs), "outcome")}{rq}</b></summary><ul class="plain">'
                  + "".join(f'<li><span class="mono dim">{e(o.get("id"))}</span> {e(o.get("text"))}</li>' for o in outs) + "</ul></details>")
    head = (f'<section class="card pad col"><div class="hd"><h2 class="big">{e(c["title"])}</h2>{status}<span class="mono-s">{e(c["slug"])}</span></div>'
            f'<p class="sub" style="font-size:14px">{e(summary)}{tail}</p><div class="col" style="gap:6px">{bar_html(ms, True)}<span class="dim">{e(legend)}</span></div>{intent}</section>')
    now_items = [m for m in ms if m["state"] in ACTIVE]
    now = "".join(
        f'<div class="now"><div class="head"><span class="mono mid">{e(m["id"])}</span><h3>{e(m.get("title") or "")}</h3><span class="mono lbl">{e(ms_labels(m)[0])}</span>'
        f'<span class="mono lbl">{e(ms_labels(m)[1])}</span>{chip(*MS_CHIP[m["state"]])}</div><div class="detail">{milestone_detail(m, fails[m["id"]], openq[m["id"]])}</div></div>' for m in now_items)
    groups, order = {}, []
    for m in ms:
        g = GROUPS.get(m.get("layer"), "Other")
        if g not in groups:
            order.append(g)
        groups.setdefault(g, []).append(m)
    gh = []
    for gi, g in enumerate(order):
        items, nship = groups[g], sum(1 for m in groups[g] if m["state"] in ("shipped", "merged"))
        rows = []
        for m in items:
            tags = " ".join(t for t, on in (("needs", fails[m["id"]] or openq[m["id"]] or m["state"] in ("blocked", "hold")), ("active", m["state"] in ACTIVE), ("shipped", m["state"] in ("shipped", "merged"))) if on)
            tl, gl = ms_labels(m)
            fl = f'<span class="dim" style="color:var(--danFg)">{count_label(len(fails[m["id"]]), "failure")}</span>' if fails[m["id"]] else ""
            ql = f'<span class="dim" style="color:var(--verFg)">{count_label(len(openq[m["id"]]), "question")}</span>' if openq[m["id"]] else ""
            rows.append(f'<li class="ms" id="{e(m["id"])}" data-tags="{e(tags)}"><button type="button" class="mrow" data-open="0" aria-expanded="false" aria-controls="d-{e(m["id"])}">'
                        f'<span class="mono mid">{e(m["id"])}</span><span class="mtitle">{e(m.get("title") or "")}</span>{fl}{ql}<span class="mono lbl">{e(tl)}</span><span class="mono lbl">{e(gl)}</span>'
                        f'{chip(*MS_CHIP.get(m["state"], MS_CHIP["pending"]))}<span class="caret dim" aria-hidden="true">+</span></button>'
                        f'<div class="detail" id="d-{e(m["id"])}">{milestone_detail(m, fails[m["id"]], openq[m["id"]])}</div></li>')
        gh.append(f'<div class="card group"><h3><button type="button" class="grow" data-open="{0 if nship == len(items) else 1}" aria-expanded="true" aria-controls="g-{gi}"><span>{e(g)}</span>'
                  f'<span class="mono">{nship} of {len(items)} shipped <span class="caret" aria-hidden="true">−</span></span></button></h3><ul id="g-{gi}">{"".join(rows)}</ul></div>')
    filt = "".join(f'<button type="button" role="radio" aria-checked="{"true" if k == "all" else "false"}" data-filter="{k}">{n}</button>' for k, n in (("all", "All"), ("needs", "Needs you"), ("active", "Active"), ("shipped", "Shipped")))
    main = ('<section aria-labelledby="ms" class="main"><h2>Now</h2>' + (f'<div class="card" style="overflow:hidden">{now}</div>' if now else '<div class="card pad empty">No milestone is active.</div>')
            + f'<div class="bar-h"><h2 id="ms">All milestones</h2><div class="tools"><div class="seg" role="radiogroup" aria-label="Show milestones">{filt}</div>'
            '<button type="button" class="btn s tonal" id="expand-all">Expand all</button><button type="button" class="btn s tonal" id="collapse-all">Collapse all</button></div></div>'
            + "".join(gh) + '<div class="card pad empty" id="nomatch" hidden>No milestone matches this filter.</div></section>')
    qs = c.get("questions", [])
    qh = "".join(f'<li><span>{e(q.get("text"))}</span>' + (f'<br><a href="#{e(quote(str(q["milestone"]), safe=""))}" class="dim">{e(q["milestone"])} · {e(q["id"])}</a>' if q.get("milestone") else f'<br><span class="dim">delta.md</span>')
                 + ("" if q.get("open") else ' <span class="dim">(answered)</span>') + "</li>" for q in qs)
    fh = "".join(f'<div class="fl"><span class="t">{e(f["text"])}</span><span class="dim">' + " · ".join(e(x) for x in (f.get("milestone"), (str(f["sha"])[:7] if f.get("sha") else None), fmt_at(f.get("at"))) if x)
                 + "</span></div>" for f in c.get("failures", []))
    rstate = {"running": chip("Running", "st-progress"), "stopped": chip("Stopped", "st-open")}.get(run.get("state"), chip("Idle", "st-open"))
    last = fmt_at(run.get("lastActivity"))
    end = run.get("lastEndState") or ("none recorded: the run stopped without SHIPPED, HOLD or BLOCKED" if run.get("state") == "stopped" else "no result recorded")
    wt = f'<span><b>Worktree</b> <span class="mono">{e(run["worktree"])}</span></span>' if run.get("worktree") else ""
    ll = "".join(e(x) + "\n" for x in run.get("logLines", []))
    aside = (f'<aside class="aside"><section aria-labelledby="qs" class="card pad col"><h2 id="qs">Questions <span class="mono-s">{sum(1 for q in qs if q.get("open"))} open</span></h2>'
             + (f"<ol>{qh}</ol>" if qs else '<span class="dim">None raised.</span>') + '</section>'
             f'<section aria-labelledby="er" class="card pad col"><h2 id="er">Failures <span class="mono-s">newest first</span></h2>' + (fh or '<span class="dim">None recorded.</span>') + '</section>'
             f'<section aria-labelledby="run" class="card pad col"><h2 id="run">Run {rstate}</h2><div class="kv"><span><b>Last activity</b> {e(last or "no activity recorded")}</span>'
             f'<span><b>Last end state</b> {e(end)}</span>{wt}</div>'
             + (f'<details class="dim"><summary>Log lines</summary><pre class="mono">{ll}</pre></details>' if ll else "") + "</section></aside>")
    return head + f'<div class="twocol">{main}{aside}</div>'


def plan_ms_list(c):
    out = []
    for m in c["milestones"]:
        tasks = " · ".join(f'{t.get("id")}' + (f' {t["title"]}' if t.get("title") else "") for t in m["tasks"] if "-gap" not in str(t.get("id")))
        out.append(f'<li class="pm"><div class="r"><span class="mono mid">{e(m["id"])}</span><b>{e(m.get("title") or "")}</b>' + (chip("Risky", "st-deciding") if m.get("risky") else "")
                   + f'</div><span class="sub">{e(tasks)}</span></li>')
    return f'<ul class="nolist col" style="gap:8px">{"".join(out)}</ul>'


def simple_view(c, p, kind):
    nm, nt = task_counts(c)
    risky = sum(1 for m in c["milestones"] if m.get("risky"))
    title = lambda chp: f'<div class="hd"><h2 class="big">{e(c["title"])}</h2>{chp}<span class="mono-s">{e(c["slug"])}</span></div>'  # noqa: E731
    run_cmd = f"/factory:run {c['slug']}"
    if kind == "intent":
        outs = "".join(f'<li><span class="mono dim">{e(o.get("id"))}</span> {e(o.get("text"))}</li>' for o in c.get("outcomes", []))
        return (f'<section class="card pad col">{title(chip("Intent only", "st-open"))}' + (f'<ul class="plain">{outs}</ul>' if outs else '<span class="dim">No outcomes recorded.</span>')
                + f'<p>No plan yet. To write one, run this in a Claude session in {e(p["name"])}:</p>{cmd_box(run_cmd, c["title"])}</section>')
    if kind == "plan":
        return (f'<section class="card pad col">{title(chip("Plan waiting for approval", "st-ready"))}<p class="sub" style="font-size:14px">{e(count_label(nm, "milestone"))}, {e(count_label(nt, "task"))}'
                + (f", {risky} risky" if risky else "") + ". Nothing is built until you approve.</p>" + plan_ms_list(c) + "</section>")
    when = fmt_at(c.get("approvedAt"), date_only=True)
    return (f'<section class="card pad col">{title(chip("Ready, not started", "st-ready"))}<p class="sub" style="font-size:14px">Approved'
            + (f" at <span class=\"mono\">{e(c['approvedSha'])}</span>" if c.get("approvedSha") else "") + (f" on {e(when)}" if when else "")
            + f". {e(count_label(nm, 'milestone'))}, {e(count_label(nt, 'task'))}. To start the run, use this in a Claude session in {e(p['name'])}:</p>{cmd_box(run_cmd, c['title'])}{plan_ms_list(c)}</section>")


def done_view(done):
    rows = []
    for c in done:
        nm = len(c["milestones"])
        when = fmt_at(c.get("doneAt"), date_only=True)
        href = next((safe_href(x.get("url")) for x in c.get("prs", []) if isinstance(x, dict) and safe_href(x.get("url"))), None)
        rows.append(f'<li class="done-li"><b style="flex:999 1 200px">{e(c["title"])}</b><span class="dim">{e(count_label(nm, "milestone"))}'
                    + (f" · shipped {e(when)}" if when else "") + "</span>" + (f'<a class="dim" href="{href}" rel="noopener">Release PR</a>' if href else "") + "</li>")
    return f'<section class="card" style="padding:8px 20px"><ul class="nolist">{"".join(rows)}</ul></section>'


def pick_change(p, ps, data):
    """The selected change when the URL names none: the first that needs you (longest waiting), else a building one, else the newest."""
    for _, pp, c, _ in all_needs(data):
        if pp is p:
            return c
    return next((c for c in p["changes"] if c.get("stage") == "building"), None) or p["changes"][-1]


def render_project(data, ps, cslug=None):
    """GET /p/<project>/ and /p/<project>/<slug>: one project; None when the project or change is unknown."""
    p = dict(project_index(data)).get(ps)
    if p is None:
        return None
    now = datetime.now(timezone.utc)
    changes = p["changes"]
    done = [c for c in changes if c.get("stage") == "done"]
    sel, view_done = None, False
    if cslug == "done" and not any(c["slug"] == "done" for c in changes):
        view_done = True
    elif cslug:
        sel = next((c for c in changes if c["slug"] == cslug), None)
        if sel is None:
            return None
        view_done = sel.get("stage") == "done"
    else:
        sel = pick_change(p, ps, data)
        view_done = sel.get("stage") == "done"
    sel = None if view_done else sel
    mine = [t for t in all_needs(data) if t[1] is p]
    needs = (f'<section aria-labelledby="ny" class="card pad accent col" style="gap:4px"><h2 id="ny">Needs you in this project <span class="cnt">{len(mine)}</span></h2>'
             + "".join(f'<div class="pneed">{need_item(ps_, pp, c, n, now, overview=False)}</div>' for ps_, pp, c, n in mine) + '<p role="status" aria-live="polite" class="live"></p></section>') if mine else ""
    tabs = []
    for k, label, _ in STAGES[:4]:
        for c in (c for c in changes if c.get("stage") == k):
            first = (needs_of(c) or [{}])[0].get("kind")
            attn = kind_chip(first) if first in KINDS else ""
            cur = ' aria-current="page"' if sel is c else ""
            tabs.append(f'<a href="{e(url_project(ps, c["slug"]))}"{cur}><span class="stg">{label}</span>{e(c["title"])}{attn}</a>')
    if done:
        tabs.append(f'<a href="{e(url_project(ps, "done"))}"' + (' aria-current="page"' if view_done else "") + f">Done ({len(done)})</a>")
    if view_done:
        view = done_view(done)
    elif sel.get("stage") == "building":
        view = building_view(ps, p, sel)
    else:
        view = simple_view(sel, p, sel.get("stage") if sel.get("stage") in ("intent", "plan") else "ready")
    options = "".join(f'<option value="{e(url_project(s))}"{" selected" if s == ps else ""}>{e(q["name"])}</option>' for s, q in project_index(data))
    links = "".join(f'<a href="{e(url_project(s))}">{e(q["name"])}</a> ' for s, q in project_index(data))
    body = ('<div class="crumbs"><nav aria-label="Breadcrumb"><ol><li><a href="/">Factory</a></li><li aria-hidden="true">/</li>'
            f'<li aria-current="page">{e(p["name"])}</li></ol></nav><label>Project<select data-nav aria-label="Project">{options}</select></label><noscript>{links}</noscript></div>'
            f'<header class="hd"><h1>{e(p["name"])}</h1><span class="mono-s">{e(short_home(p["repo"]))}</span><span class="dim">{e(as_of(data))}</span></header>'
            + needs + (f'<nav class="tabs" aria-label="Changes in {e(p["name"])}">{"".join(tabs)}</nav>' if tabs else "") + view)
    return page(f'{p["name"]} · Factory', body)


def render_404():
    return page("Not found", '<header class="hd"><h1>Not found</h1></header><p><a href="/">Back to the Factory overview</a></p>')


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
            status, ctype = 200, "text/html; charset=utf-8"
            if path == "/":
                body = render(snapshot.get()).encode()
            elif path == "/status.json":
                body, ctype = json.dumps(snapshot.get(), indent=1).encode(), "application/json"
            elif path.startswith("/p/"):
                parts = [unquote(x) for x in path[3:].split("/")]
                html_ = render_project(snapshot.get(), parts[0], parts[1] if len(parts) > 1 and parts[1] else None) if len(parts) <= 2 else None
                status, body = (200, html_.encode()) if html_ else (404, render_404().encode())
            else:
                status, body = 404, render_404().encode()
            self.send_response(status)
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
