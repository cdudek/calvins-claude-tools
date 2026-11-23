"""Board extraction and real-surface UI checks (design 3.5).

extract() turns a board into expectation rows (or lists what it cannot measure),
measure() reads the live surface with Playwright, evaluate() makes the verdict lines.
A contract runner: `python3 board.py check spec.json`. verify.py imports browser_available.

Design-canvas exports (kind "canvas", 4.1): `index` serves an export over local HTTP and lists the candidate nodes of every
`*.dc.html` board with measured computed style and geometry, light and dark; `rows` turns that index plus a mapping file
(board -> route, state) into expectation rows. Screenshots are evidence only: there are no baselines.
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import json
import os
import re
import sys
import threading
import urllib.parse
from pathlib import Path

TOL = 0.5
GEOMETRY = {"x", "y", "width", "height"}
UNITLESS = {"font-weight", "opacity", "z-index", "line-height", "flex-grow", "flex-shrink"}
FIGMA = {"itemSpacing": "gap", "cornerRadius": "border-radius", "counterAxisSpacing": "row-gap"}
IMAGE_REASON = "image-only input: no measurable source"


class EnvError(Exception):
    """The browser or target could not start: an environment problem, not a verdict."""


def browser_available(executable: str | None = None) -> tuple[bool, str]:
    if executable:
        return (os.access(executable, os.X_OK), f"{executable} is not executable")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, "python playwright is not installed"
    try:
        with sync_playwright() as p:
            path = p.chromium.executable_path
        return (os.path.exists(path), "chromium is not downloaded (playwright install chromium)")
    except Exception as e:  # noqa: BLE001 - any failure to locate the browser is an env problem
        return False, str(e)[:100]


def css_name(prop: str) -> str:
    return FIGMA.get(prop) or re.sub(r"(?<!^)(?=[A-Z])", "-", prop).lower()


def _fmt(n: float, prop: str) -> str:
    return f"{n:g}" if prop in UNITLESS else f"{n:g}px"


def _row(board: dict, node: dict, prop: str, expected: str, source: str) -> dict:
    frame = board.get("frame", "board")
    return {
        "id": f"{frame}/{node['name']}/{prop}",
        "frame": frame,
        "node": node["name"],
        "locator": node["locator"],
        "state": node.get("state", "default"),
        "viewport": board.get("viewport"),
        "prop": prop,
        "expected": expected,
        "tolerance_px": TOL,
        "source": source,
    }


def _prop_names(node: dict) -> list[str]:
    return list(node.get("props") or [])


def extract(board: dict, tokens: dict | None = None) -> dict:
    """Expectation rows for a board; everything that cannot be measured goes under unsupported."""
    tokens = tokens or {}
    rows: list[dict] = []
    unsupported: list[dict] = []
    kind = board.get("kind")
    frame = board.get("frame", "board")

    def no(node: dict, prop: str, why: str) -> None:
        unsupported.append({"id": f"{frame}/{node['name']}/{css_name(prop)}", "reason": why})

    if kind == "image":
        for node in board.get("nodes", []):
            for prop in _prop_names(node):
                no(node, prop, IMAGE_REASON)
    elif kind == "structured":
        for node in board.get("nodes", []):
            for prop, val in (node.get("props") or {}).items():
                name = css_name(prop)
                if isinstance(val, dict) and "var" in val:
                    tok = tokens.get(val["var"])
                    if tok is None:
                        no(node, prop, f"token {val['var']} is not defined")
                        continue
                    exp = _fmt(tok, name) if isinstance(tok, (int, float)) else str(tok)
                    rows.append(_row(board, node, name, exp, "token"))
                elif isinstance(val, (int, float)) and not isinstance(val, bool):
                    rows.append(_row(board, node, name, _fmt(val, name), "literal"))
                else:
                    rows.append(_row(board, node, name, str(val), "literal"))
    elif kind == "html":
        _extract_html(board, rows, unsupported, no)
    elif kind == "canvas":
        ok, why = browser_available(board.get("executable"))
        if not ok:
            unsupported.append({"id": board["file"], "reason": f"browser unavailable ({why})"})
        else:
            idx = index_export(board["root"], board.get("themes", THEMES), board.get("viewport"), board.get("attr"),
                               board.get("executable"), [board["file"]])
            out = canvas_rows(idx, {"boards": [{"board": board["file"], "route": board["route"], "state": board.get("state", "default")}],
                                    **{k: board[k] for k in ("themes", "tolerance_px", "geometry_tolerance_px", "position") if k in board}})
            rows += out["rows"]
            unsupported += out["unsupported"]
    else:
        raise ValueError(f"unknown board kind: {kind!r}")
    return {"rows": rows, "unsupported": unsupported}


def _extract_html(board: dict, rows: list, unsupported: list, no) -> None:
    nodes = board.get("nodes", [])
    ok, why = browser_available(board.get("executable"))
    if not ok:
        for node in nodes:
            for prop in _prop_names(node):
                no(node, prop, f"browser unavailable ({why})")
        return
    target = {"kind": "web", "file": board["file"]}
    probes = [
        {**_row(board, n, css_name(p), "", "measured"), "tolerance_px": TOL}
        for n in nodes
        for p in _prop_names(n)
    ]
    for probe, got in zip(probes, _read(target, probes, board.get("executable")), strict=False):
        if got.get("value") is None:
            unsupported.append({"id": probe["id"], "reason": got["why"]})
        else:
            v = got["value"]
            rows.append({**probe, "expected": _fmt(v, probe["prop"]) if isinstance(v, (int, float)) else v})


# Loaded into Electron's main process before the app (`--require`): every window is created hidden and unfocusable, calls that show
# or focus one do nothing and the macOS dock icon is hidden, so a run never takes the owner's focus. Playwright still drives the
# page. shortcut: needs an Electron that honours --require (Playwright itself uses it); untested against a real app here.
_HIDDEN_SHIM = """const Module = require('module'), load = Module._load;
Module._load = function (request, ...rest) {
  const m = load.call(this, request, ...rest);
  if (request !== 'electron' || !m || !m.BrowserWindow || m.__sdlcHidden) return m;
  class Hidden extends m.BrowserWindow {
    constructor(o) { super({...(o || {}), show: false, focusable: false, skipTaskbar: true}); }
    show() {} showInactive() {} focus() {} moveTop() {}
  }
  const wrapped = new Proxy(m, {get: (t, k) => (k === 'BrowserWindow' ? Hidden : k === '__sdlcHidden' ? true : t[k])});
  if (process.platform === 'darwin' && m.app && m.app.dock) m.app.dock.hide();
  return wrapped;
};
"""


def electron_hidden(main: str) -> tuple[list[str], dict]:
    """Launch arguments and environment that keep an Electron run in the background."""
    import tempfile
    shim = Path(tempfile.mkdtemp(prefix="sdlc-electron-")) / "hidden.js"
    shim.write_text(_HIDDEN_SHIM)
    return ["--require", str(shim), "--disable-background-timer-throttling", "--disable-renderer-backgrounding", str(Path(main).resolve())], \
        {**os.environ, "SDLC_HIDDEN": "1", "ELECTRON_NO_ATTACH_CONSOLE": "1"}


def _launch(p, target: dict, executable: str | None):
    """(page, closer) for a target kind."""
    kind = target.get("kind")
    try:
        if kind == "web":
            browser = p.chromium.launch(executable_path=executable) if executable else p.chromium.launch()
            page = browser.new_page()
            url = target.get("url") or Path(target["file"]).resolve().as_uri()
            page.goto(url)
            return page, browser.close
        if kind == "extension":
            ext = str(Path(target["path"]).resolve())
            ctx = p.chromium.launch_persistent_context(
                "",
                executable_path=executable,
                headless=False,
                args=["--headless=new", f"--disable-extensions-except={ext}", f"--load-extension={ext}"],
            )
            sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker")
            page_url = target["page"]
            if "://" not in page_url:
                page_url = f"chrome-extension://{sw.url.split('/')[2]}/{page_url.lstrip('/')}"
            page = ctx.new_page()
            page.goto(page_url)
            return page, ctx.close
        if kind == "electron":
            args, env = electron_hidden(target["main"])
            app = p._electron.launch(args=args, env=env)  # noqa: SLF001
            return app.first_window(), app.close
    except Exception as e:  # noqa: BLE001
        raise EnvError(f"{kind} target did not start: {str(e)[:120]}") from e
    raise EnvError(f"unknown target kind {kind!r}")


def _locate(page, loc: dict):
    if "css" in loc:
        return page.locator(loc["css"])
    if "text" in loc:
        return page.get_by_text(loc["text"], exact=True)
    if loc.get("name") is None:
        return page.get_by_role(loc["role"])
    return page.get_by_role(loc["role"], name=loc["name"], exact=True)


def _one(page, loc: dict):
    """(element handle, None) or (None, why) when the locator does not match exactly one element."""
    found = _locate(page, loc)
    n = found.count()
    if n != 1:
        return None, f"locator matched {n} elements"
    return found.element_handle(), None


_BOX = "el => { const r = el.getBoundingClientRect(); return {x: r.x, y: r.y, width: r.width, height: r.height}; }"
_CSS = "(el, p) => getComputedStyle(el).getPropertyValue(p)"


def _enter(page, target: dict, row: dict, cur: dict) -> None:
    """Move the page to the row's route and theme (canvas rows): navigate when the route changes, re-theme when either changes."""
    route, theme = row.get("route"), row.get("theme")
    if route and route != cur.get("route"):
        base = target.get("url")
        if not base:
            raise EnvError("a row with a route needs a target with a url")
        page.goto(base.rstrip("/") + route, wait_until="networkidle")
    if theme and (theme, route) != (cur.get("theme"), cur.get("route")):
        page.emulate_media(color_scheme=theme)
        if row.get("theme_attr"):
            page.evaluate("([a, v]) => document.documentElement.setAttribute(a, v)", [row["theme_attr"], theme])
    if route or theme:
        page.evaluate("document.fonts && document.fonts.ready")
        cur.update(route=route, theme=theme)
        cur["cache"] = {}


def _read(target: dict, rows: list[dict], executable: str | None = None, evidence_dir: str | None = None) -> list[dict]:
    """Per row: {"value": measured string/number or None, "why": ...}."""
    from playwright.sync_api import sync_playwright

    out: list[dict] = []
    with sync_playwright() as p:
        page, close = _launch(p, target, executable)
        cur: dict = {"cache": {}}
        try:
            for row in rows:
                try:
                    _enter(page, target, row, cur)
                    res = _read_row(page, target, row, cur["cache"])
                except EnvError:
                    raise
                except Exception as e:  # noqa: BLE001 - a page that cannot be entered fails its rows
                    res = {"value": None, "why": f"could not open {row.get('route')}: {str(e)[:100]}"}
                if evidence_dir and res.get("value") is None:
                    _shot(page, evidence_dir, row)
                out.append(res)
        finally:
            close()
    return out


def _read_row(page, target: dict, row: dict, cache: dict | None = None) -> dict:
    vp = row.get("viewport")
    if vp and target.get("kind") != "electron":
        page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
    try:
        key = json.dumps(row["locator"], sort_keys=True)
        if cache is not None and key in cache:
            el, why = cache[key]
        else:
            el, why = _one(page, row["locator"])
            if cache is not None:
                cache[key] = (el, why)
        if el is None:
            return {"value": None, "why": why}
        prop = row["prop"]
        if "between" in row:
            other, why = _one(page, row["between"][1])
            first, why1 = _one(page, row["between"][0])
            if other is None or first is None:
                return {"value": None, "why": why or why1}
            a, b = first.evaluate(_BOX), other.evaluate(_BOX)
            v = b["x"] - (a["x"] + a["width"]) if prop == "gap-x" else b["y"] - (a["y"] + a["height"])
            return {"value": v}
        if prop in GEOMETRY:
            return {"value": el.evaluate(_BOX)[prop]}
        val = el.evaluate(_CSS, prop).strip()
        return {"value": "0px" if val == "normal" else val}
    except Exception as e:  # noqa: BLE001 - a broken page read is a failing row, not a crash
        return {"value": None, "why": f"could not measure: {str(e)[:100]}"}


def _shot(page, evidence_dir: str, row: dict) -> None:
    try:
        Path(evidence_dir).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(evidence_dir) / (re.sub(r"[^A-Za-z0-9]+", "-", row["id"]) + ".png")))
    except Exception:  # noqa: BLE001, S110 - evidence is diagnostic only
        pass


def _num(v) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)(px)?\b", str(v))
    return float(m[1]) if m else None


def compare(measured: float | str, expected: str, tol_px: float) -> bool:
    """Numeric values (px or bare) within tolerance; anything else must match as text."""
    want, got = _num(expected), _num(measured)
    if want is None or got is None:
        return str(measured).strip() == str(expected).strip()
    return abs(got - want) <= tol_px


def measure(target: dict, rows: list[dict], executable: str | None = None, evidence_dir: str | None = None) -> list[dict]:
    """One result per row: {id, status PASS|FAIL, why, expected, got, tolerance_px}."""
    results = []
    for row, got in zip(rows, _read(target, rows, executable, evidence_dir), strict=True):
        res = {"id": row["id"], "expected": row["expected"], "tolerance_px": row.get("tolerance_px", TOL)}
        if got.get("value") is None:
            results.append({**res, "status": "FAIL", "why": got["why"], "got": None})
            continue
        v = got["value"]
        shown = _fmt(v, row["prop"]) if isinstance(v, (int, float)) else v
        ok = compare(v, row["expected"], res["tolerance_px"])
        results.append({**res, "status": "PASS" if ok else "FAIL", "why": "", "got": shown})
    return results


def evaluate(results: list[dict]) -> tuple[list[str], int]:
    """Output lines (one per row) and the number of failures."""
    lines, failed = [], 0
    for r in results:
        if r["status"] == "PASS":
            lines.append(f"PASS {r['id']}: {r['got']}")
            continue
        failed += 1
        why = r["why"] or f"expected {r['expected']}, got {r['got']} (tolerance {r['tolerance_px']:g}px)"
        lines.append(f"FAIL {r['id']}: {why}")
    return lines, failed


# ---- design-canvas exports (4.1) ------------------------------------------------------------------------------------

CANVAS_STYLE = ["color", "background-color", "font-family", "font-size", "font-weight", "line-height", "letter-spacing",
                "padding-top", "padding-right", "padding-bottom", "padding-left", "border-radius", "gap", "opacity"]
THEMES = ("light", "dark")

# Candidate nodes of one rendered board: headings, buttons, inputs, landmarks (by role plus accessible name) and text blocks
# (by their text). shortcut: a simplified accessible-name computation (aria-label, aria-labelledby, label, alt, content);
# a name the app computes differently shows up as "locator matched 0 elements" in the check, never as a silent pass.
_NODES = """(props) => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const LAND = {NAV: 'navigation', MAIN: 'main', ASIDE: 'complementary', FORM: 'form'};
  const roleOf = el => {
    const r = norm(el.getAttribute('role')).split(' ')[0];
    if (r) return r;
    const t = el.tagName;
    if (/^H[1-6]$/.test(t)) return 'heading';
    if (t === 'BUTTON') return 'button';
    if (t === 'TEXTAREA') return 'textbox';
    if (t === 'SELECT') return 'combobox';
    if (t === 'INPUT') {
      const ty = (el.getAttribute('type') || 'text').toLowerCase();
      if (ty === 'hidden') return null;
      return {button: 'button', submit: 'button', reset: 'button', checkbox: 'checkbox', radio: 'radio', range: 'slider', search: 'searchbox'}[ty] || 'textbox';
    }
    if (LAND[t]) return LAND[t];
    if (t === 'HEADER' && !el.closest('article,section,main,aside,nav')) return 'banner';
    if (t === 'FOOTER' && !el.closest('article,section,main,aside,nav')) return 'contentinfo';
    return null;
  };
  const labelled = el => {
    const ids = norm(el.getAttribute('aria-labelledby'));
    if (ids) return norm(ids.split(' ').map(i => (document.getElementById(i) || {}).textContent || '').join(' '));
    return norm(el.getAttribute('aria-label'));
  };
  const nameOf = (el, role) => {
    const l = labelled(el);
    if (l) return l;
    if (['textbox', 'searchbox', 'combobox', 'checkbox', 'radio', 'slider'].includes(role)) {
      const lab = (el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]')) || el.closest('label');
      return norm((lab && lab.textContent) || el.getAttribute('placeholder') || el.getAttribute('title'));
    }
    if (el.tagName === 'INPUT') return norm(el.value);
    if (['banner', 'contentinfo', 'navigation', 'main', 'complementary', 'form'].includes(role)) return '';
    return norm(el.textContent);
  };
  const shown = el => {
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    return cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0;
  };
  const TEXT = 'p,li,label,th,td,figcaption,blockquote,div,span';
  const out = [];
  for (const el of document.body.querySelectorAll('*')) {
    if (!shown(el)) continue;
    const role = roleOf(el);
    let node = null;
    if (role) {
      const name = nameOf(el, role);
      node = {role, name, locator: name ? {role, name} : {role}};
    } else if (el.matches(TEXT) && !el.closest('button,[role=button],h1,h2,h3,h4,h5,h6,[role=heading],label,a')) {
      const own = norm([...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' '));
      const leaf = !el.querySelector('*') || (own && own === norm(el.textContent));
      if (!own || !leaf) continue;
      node = {role: 'text', name: own, locator: {text: own}};
    }
    if (!node) continue;
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    node.tag = el.tagName.toLowerCase();
    node.style = Object.fromEntries(props.map(p => [p, cs.getPropertyValue(p)]));
    node.box = {x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height};
    out.push(node);
  }
  const seen = {};
  out.forEach(n => { const k = JSON.stringify(n.locator); seen[k] = (seen[k] || 0) + 1; });
  out.forEach(n => { n.count = seen[JSON.stringify(n.locator)]; });
  return out;
}"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:  # noqa: D102 - the runner's output is the verdict, not an access log
        pass

    def translate_path(self, path: str) -> str:
        """Only files whose resolved path stays inside the resolved export root; a symlink out of it is a 404."""
        root = os.path.realpath(self.directory)
        real = os.path.realpath(super().translate_path(path))
        return real if real == root or real.startswith(root + os.sep) else os.path.join(root, "__sdlc_denied__")

    def list_directory(self, path):  # noqa: D102 - no directory listings
        self.send_error(403, "no directory listing")
        return None


@contextlib.contextmanager
def serve(root: str | Path):
    """The export root over local HTTP on 127.0.0.1 and a random port, so absolute `/_blob/...` paths resolve."""
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()


def index_export(root: str | Path, themes=THEMES, viewport: dict | None = None, attr: str | None = None,
                 executable: str | None = None, only: list[str] | None = None) -> dict:
    """Walk every `*.dc.html` board of an export and list its candidate nodes per theme, with measured style and geometry.
    A board whose files did not all load (a 404 on the /_blob/ stylesheet) is recorded with its errors: nothing is measured from it."""
    from playwright.sync_api import sync_playwright

    root = Path(root)
    vp = viewport or {"width": 1280, "height": 800}
    files = only or sorted(p.relative_to(root).as_posix() for p in root.rglob("*.dc.html"))
    boards: dict = {f: {} for f in files}
    with serve(root) as base, sync_playwright() as p:
        browser = p.chromium.launch(executable_path=executable) if executable else p.chromium.launch()
        try:
            for theme in themes:
                ctx = browser.new_context(color_scheme=theme, viewport=vp)
                page = ctx.new_page()
                errors: list[str] = []
                page.on("response", lambda r, e=errors: e.append(f"{r.status} {r.url.split('/', 3)[-1]}") if r.status >= 400 else None)
                page.on("requestfailed", lambda r, e=errors: e.append(f"failed {r.url.split('/', 3)[-1]}"))
                for f in files:
                    errors.clear()
                    try:
                        page.goto(f"{base}/{urllib.parse.quote(f)}", wait_until="networkidle")
                        if attr:
                            page.evaluate("([a, v]) => document.documentElement.setAttribute(a, v)", [attr, theme])
                        page.evaluate("document.fonts && document.fonts.ready")
                        nodes = page.evaluate(_NODES, CANVAS_STYLE)
                    except Exception as e:  # noqa: BLE001 - one broken board must not stop the walk
                        boards[f][theme] = {"error": str(e)[:160], "nodes": []}
                        continue
                    boards[f][theme] = {"error": "; ".join(errors[:3]) if errors else "", "nodes": nodes}
                ctx.close()
        finally:
            browser.close()
    return {"version": 1, "viewport": vp, "themes": list(themes), "attr": attr, "boards": boards}


def _norm(v: str) -> str:
    return "0px" if v.strip() == "normal" else v.strip()


def validate_mapping(mapping: dict) -> None:
    """The mapping file's shape: entries of board (or board_file), route (a path, or null when the screen is not a web route),
    state, theme ("light", "dark" or "light, dark"), viewport ([w, h] or null). Other keys (entry, series, capture, note ...) are bookkeeping."""
    boards = mapping.get("boards")
    if not isinstance(boards, list):
        raise ValueError("mapping needs a boards list")
    if "count" in mapping and mapping["count"] != len(boards):
        raise ValueError(f"mapping count {mapping['count']} is not the {len(boards)} boards listed")
    for i, m in enumerate(boards):
        f = m.get("board_file") or m.get("board") if isinstance(m, dict) else None
        vp, th, rt = (m.get("viewport"), m.get("theme"), m.get("route")) if isinstance(m, dict) else (0, 0, 0)
        if not isinstance(f, str) or not f:
            raise ValueError(f"boards[{i}] needs board or board_file")
        if rt is not None and not (isinstance(rt, str) and rt.startswith("/")):
            raise ValueError(f"boards[{i}] route must start with / or be null")
        if vp is not None and not (isinstance(vp, list) and len(vp) == 2 and all(isinstance(n, int) and n > 0 for n in vp)):
            raise ValueError(f"boards[{i}] viewport must be [width, height] or null")
        if th is not None and not (isinstance(th, str) and all(t.strip() in THEMES for t in th.split(","))):
            raise ValueError(f"boards[{i}] theme must be light, dark or 'light, dark'")


def _pick(indexes: list[dict], vp) -> dict | None:
    """The index measured at this entry's viewport (the only one when the entry names none)."""
    return next((ix for ix in indexes if vp is None or [ix["viewport"]["width"], ix["viewport"]["height"]] == list(vp)), None)


def canvas_rows(index: dict | list[dict], mapping: dict, repo: str | None = None) -> dict:
    """Expectation rows for every mapped board, theme and unambiguous node; what cannot be measured goes under unsupported.
    The mapping is the only hand-written input. `index` is one index, or one per viewport; `repo` keeps one app's entries."""
    validate_mapping(mapping)
    indexes = index if isinstance(index, list) else [index]
    rows: list[dict] = []
    unsupported: list[dict] = []
    tol, gtol = mapping.get("tolerance_px", TOL), mapping.get("geometry_tolerance_px", 1.0)
    geometry = ["x", "y", "width", "height"] if mapping.get("position") else ["width", "height"]
    ids: set[str] = set()
    for m in mapping["boards"]:
        if repo and m.get("repo") != repo:
            continue
        f = m.get("board_file") or m["board"]
        ident = m.get("entry") or f
        if not m.get("route"):
            unsupported.append({"id": ident, "reason": m.get("note") or "no route: not measured as a web route"})
            continue
        ix = _pick(indexes, m.get("viewport"))
        if ix is None:
            unsupported.append({"id": ident, "reason": f"no index measured at viewport {m['viewport']}"})
            continue
        hits = [k for k in ix["boards"] if k == f or k.rsplit("/", 1)[-1] == f]
        themes = [t.strip() for t in m["theme"].split(",")] if m.get("theme") else (mapping.get("themes") or ix["themes"])
        for theme in themes:
            who = f"{ident}/{theme}"
            entry = ix["boards"][hits[0]].get(theme) if len(hits) == 1 else None
            if entry is None:
                unsupported.append({"id": who, "reason": f"{len(hits)} boards named {f} in the index" if len(hits) != 1 else "theme is not in the index"})
                continue
            if entry["error"] or not entry["nodes"]:
                unsupported.append({"id": who, "reason": entry["error"] and f"board did not load cleanly ({entry['error']})" or "no candidate nodes"})
                continue
            for n in entry["nodes"]:
                label = f"{n['role']}:{n['name']}" if n["name"] else n["role"]
                if n["count"] > 1:
                    unsupported.append({"id": f"{who}/{label}", "reason": f"{n['count']} nodes on the board share this locator"})
                    continue
                for prop, val in [*n["style"].items(), *((g, n["box"][g]) for g in geometry)]:
                    want = _fmt(val, prop) if isinstance(val, (int, float)) else _norm(val)
                    rid = f"{who}/{label}/{prop}"
                    if rid in ids:
                        raise ValueError(f"two mapping entries produce the row {rid}: give each entry its own entry id")
                    ids.add(rid)
                    rows.append({"id": rid, "frame": f, "node": label, "locator": n["locator"], "state": m.get("state", "default"),
                                 "route": m["route"], "theme": theme, "theme_attr": ix.get("attr") or mapping.get("theme_attr"),
                                 "viewport": ix["viewport"], "prop": prop, "expected": want,
                                 "tolerance_px": gtol if prop in GEOMETRY else tol, "source": "measured"})
    return {"rows": rows, "unsupported": unsupported}


def _check(spec_path: str) -> int:
    spec = json.loads(Path(spec_path).read_text())
    rows, target, exe = spec.get("rows", []), spec.get("target", {}), spec.get("executable")
    if not rows:  # a check that measured nothing proves nothing
        print("Ran 0 checks\nFAIL no rows: the spec has nothing to measure")
        return 1
    if len(rows) < spec.get("expected_rows", 0):
        print(f"FAIL only {len(rows)} rows, the approved spec expects {spec['expected_rows']}")
        return 1
    if rows:
        if target.get("kind") != "electron":
            ok, why = browser_available(exe)
            if not ok:
                print(f"env: browser unavailable ({why})")
                return 127
        try:
            results = measure(target, rows, exe, spec.get("evidence_dir"))
        except EnvError as e:
            print(f"env: browser unavailable ({e})")
            return 127
    else:
        results = []
    lines, failed = evaluate(results)
    print("\n".join(lines))
    print(f"Ran {len(rows)} checks")
    waived = set(spec.get("waive_unsupported", []))
    unproven = [u for u in spec.get("unsupported", []) if u["id"] not in waived]  # listed, never counted as passed
    for u in unproven:
        print(f"UNPROVEN {u['id']}: {u['reason']}")
    if failed:
        print(f"{failed} failed")
    if unproven:
        print(f"{len(unproven)} not proven (waive each by id in waive_unsupported, or fix it)")
    return 1 if failed or unproven else 0


def _extract_cli(argv: list[str]) -> int:
    board = json.loads(Path(argv[0]).read_text())
    tokens = json.loads(Path(argv[argv.index("--tokens") + 1]).read_text()) if "--tokens" in argv else None
    text = json.dumps(extract(board, tokens), indent=2)
    if out := _out(argv):
        out.write_text(text + "\n")
    print(text)
    return 0


def _out(argv: list[str], default: str | None = None) -> Path | None:
    """The --out path; one under the run records (SDLC_HOME, resolved) is refused: only the runner writes there."""
    v = _arg(argv, "--out", default)
    if v is None:
        return None
    home = Path(os.environ.get("SDLC_HOME") or Path.home() / ".sdlc").resolve()
    if Path(v).resolve().is_relative_to(home):
        raise ValueError(f"--out {v} is inside the run records; write outside {home}")
    return Path(v)


def _arg(argv: list[str], flag: str, default=None):
    return argv[argv.index(flag) + 1] if flag in argv else default


def _index_cli(argv: list[str]) -> int:
    out = _out(argv, "index.json")  # refuse a records path before any work
    ok, why = browser_available(_arg(argv, "--executable"))
    if not ok:
        print(f"env: browser unavailable ({why})")
        return 127
    w, _, h = _arg(argv, "--viewport", "1280x800").partition("x")
    idx = index_export(argv[0], _arg(argv, "--themes", ",".join(THEMES)).split(","), {"width": int(w), "height": int(h)},
                       _arg(argv, "--attr"), _arg(argv, "--executable"))
    Path(out).write_text(json.dumps(idx, indent=1) + "\n")
    bad = [f for f, t in idx["boards"].items() if any(v["error"] for v in t.values())]
    print(f"indexed {len(idx['boards'])} boards, {sum(len(v['nodes']) for t in idx['boards'].values() for v in t.values())} nodes -> {out}")
    for f in bad:
        print(f"WARN {f}: " + "; ".join(v["error"] for v in idx["boards"][f].values() if v["error"]))
    return 0


def _rows_cli(argv: list[str]) -> int:
    mapping = json.loads(Path(argv[0]).read_text())
    files = [argv[i + 1] for i, a in enumerate(argv) if a == "--index"] or ["index.json"]  # one per viewport
    idx = [json.loads(Path(f).read_text()) for f in files]
    try:
        res = canvas_rows(idx, mapping, _arg(argv, "--repo"))
    except ValueError as e:
        print(f"mapping: {e}")
        return 2
    out = {"target": {"kind": "web", "url": _arg(argv, "--url", mapping.get("url", ""))}, "rows": res["rows"], "expected_rows": len(res["rows"]),
           "unsupported": res["unsupported"], "waive_unsupported": []}
    _out(argv, "spec.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(res['rows'])} rows, {len(res['unsupported'])} unsupported")
    for u in res["unsupported"][:20]:
        print(f"UNSUPPORTED {u['id']}: {u['reason']}")
    return 0 if res["rows"] else 2  # no rows is not a spec

def main(argv: list[str]) -> int:
    try:
        return _main(argv)
    except ValueError as e:
        print(f"board: {e}")
        return 2


def _main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "index":
        return _index_cli(argv[1:])
    if len(argv) >= 2 and argv[0] == "rows":
        return _rows_cli(argv[1:])
    if len(argv) >= 2 and argv[0] == "check":
        return _check(argv[1])
    if len(argv) >= 2 and argv[0] == "extract":
        return _extract_cli(argv[1:])
    print("usage: board.py check <spec.json> | extract <board.json> [--tokens t.json] [--out rows.json]\n"
          "       board.py index <export-dir> [--out index.json] [--themes light,dark] [--viewport 1280x800] [--attr data-theme]\n"
          "       board.py rows <mapping.json> --index index.json [--index other.json] [--repo web] [--url http://app] [--out spec.json]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
