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
            entry = {"board": board["file"], "route": board.get("route"), "state": board.get("state", "default"),
                     **{k: board[k] for k in ("surface", "frame", "min_match", "tolerances") if k in board}}
            mapping = {"boards": [entry], **{k: board[k] for k in ("themes", "tolerances", "position") if k in board}}
            idx = index_export(board["root"], board.get("themes", THEMES), board.get("viewport"), board.get("attr"),
                               board.get("executable"), [board["file"]], _containers(mapping))
            out = canvas_rows(idx, mapping)
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




# ---- surfaces (4.2) -------------------------------------------------------------------------------------------------------
# A mapping entry names its surface: `route` (a web page, the default), `surface` {"kind": "chrome-extension", "dist", "page"}
# or {"kind": "electron", "app", "env", "args"}. dist and app are paths inside the consumer repo (the check's working directory).
ENV_KEY = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
ENV_DENY = re.compile(r"^(PATH|HOME|NODE_OPTIONS|ELECTRON_RUN_AS_NODE|LD_.*|DYLD_.*)$")
PAGE_RX = re.compile(r"^[A-Za-z0-9_./-]+(\?[A-Za-z0-9_.~%&=+,:@/-]*)?$")
ARG_DENY = ("--require", "--inspect", "--remote-debugging", "--js-flags", "--load-extension", "--disable-extensions")


def _rel_ok(p) -> bool:
    return isinstance(p, str) and p != "" and "\\" not in p and "\0" not in p and not p.startswith(("/", "~")) and ".." not in p.split("/")


def validate_surface(s) -> dict:
    """The surface of one entry, or ValueError. Paths are checked lexically here and against the real tree (symlinks) at check time."""
    if not isinstance(s, dict) or s.get("kind") not in ("chrome-extension", "electron"):
        raise ValueError('surface.kind must be "chrome-extension" or "electron" (a web route needs no surface)')
    if s["kind"] == "chrome-extension":
        page = s.get("page")
        if not _rel_ok(s.get("dist")) or not isinstance(page, str) or "://" in page or not PAGE_RX.match(page) \
                or ".." in page.partition("?")[0].split("/"):
            raise ValueError('surface needs dist (a path inside the repo) and page ("<path>?<query>", no scheme)')
        return s
    env, args = s.get("env", {}), s.get("args", [])
    if not _rel_ok(s.get("app")):
        raise ValueError("surface.app must be a path inside the repo")
    if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) and ENV_KEY.match(k) and not ENV_DENY.match(k)
                                            for k, v in env.items()):
        raise ValueError("surface.env keys must match [A-Z][A-Z0-9_]* and not be PATH, HOME, NODE_OPTIONS, ELECTRON_RUN_AS_NODE, LD_* or DYLD_*")
    if not isinstance(args, list) or not all(isinstance(a, str) and "\0" not in a and not a.lower().startswith(ARG_DENY) and a != "-r" for a in args):
        raise ValueError("surface.args must be a list of strings, none of them a code-loading or debugging flag")
    return s


def _inside(root: Path, rel: str) -> Path:
    """rel resolved under root, symlinks followed; one that leaves the repo is an error."""
    real = (root / rel).resolve()
    if not real.is_relative_to(root.resolve()):
        raise ValueError(f"{rel} resolves outside the repo")
    return real


def _skey(s: dict) -> str:
    """One browser session per surface: all web rows share one; an extension per dist; an electron per app, env and args."""
    return json.dumps({k: v for k, v in s.items() if k != "page"}, sort_keys=True)


def _ext_id(ctx) -> str:
    sw = ctx.service_workers[0] if ctx.service_workers else None
    if sw is None and ctx.background_pages:
        return ctx.background_pages[0].url.split("/")[2]
    if sw is None:
        try:
            sw = ctx.wait_for_event("serviceworker", timeout=15000)
        except Exception:  # noqa: BLE001 - a manifest-v2 extension has a background page instead
            if ctx.background_pages:
                return ctx.background_pages[0].url.split("/")[2]
            raise
    return sw.url.split("/")[2]


def _launch(p, target: dict, executable: str | None, root: Path | None = None):
    """(page, closer, base) for a target: base is the URL prefix rows navigate under (None for Electron, which has one window)."""
    import tempfile
    root = root or Path.cwd()
    kind = target.get("kind")
    try:
        if kind == "web":
            browser = p.chromium.launch(executable_path=executable) if executable else p.chromium.launch()
            page = browser.new_page()
            url = target.get("url") or Path(target["file"]).resolve().as_uri()
            if target.get("url") or target.get("file"):
                page.goto(url)
            return page, browser.close, (target.get("url") or "").rstrip("/")
        if kind == "chrome-extension":
            ext = str(_inside(root, validate_surface(target)["dist"]))
            ctx = p.chromium.launch_persistent_context(
                tempfile.mkdtemp(prefix="sdlc-ext-"),
                executable_path=executable,
                headless=False,
                args=["--headless=new", f"--disable-extensions-except={ext}", f"--load-extension={ext}"],
            )
            return ctx.new_page(), ctx.close, f"chrome-extension://{_ext_id(ctx)}"
        if kind == "electron":
            s = validate_surface(target)
            args, env = electron_hidden(str(_inside(root, s["app"])))
            app = p._electron.launch(args=[*args, *s.get("args", [])], env={**env, **s.get("env", {})}, cwd=str(root))  # noqa: SLF001
            page = app.first_window()
            page.wait_for_load_state("load")
            return page, app.close, None
    except ValueError:
        raise
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




def _read(target: dict, rows: list[dict], executable: str | None = None, evidence_dir: str | None = None) -> list[dict]:
    """Per row: {"value": measured string/number or None, "why": ...} (the per-node rows of structured and html boards)."""
    from playwright.sync_api import sync_playwright

    out: list[dict] = []
    with sync_playwright() as p:
        page, close, _ = _launch(p, target, executable)
        cache: dict = {}
        try:
            for row in rows:
                res = _read_row(page, target, row, cache)
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



# ---- design-canvas exports (4.2: one aggregate row per mapping entry and theme) ----------------------------------------------
# Token properties only. width and height come from the bounding box; x and y only when the mapping opts in.
CANVAS_STYLE = ["color", "background-color", "border-color", "font-family", "font-size", "font-weight", "line-height", "letter-spacing",
                "padding-top", "padding-right", "padding-bottom", "padding-left", "margin-top", "margin-right", "margin-bottom",
                "margin-left", "gap", "border-radius", "box-shadow"]
BOX, POS = ["width", "height"], ["x", "y"]
THEMES = ("light", "dark")
DEFAULT_CONTAINER = ".cell"
SELECTOR_RX = re.compile(r"^[A-Za-z0-9_.#\[\]=\"'\-:> *]{1,100}$")
UNMEASURABLE_MAX = 0.2  # more than this share of a row's nodes with a shared locator: the row is UNPROVEN, a failure
MIN_MATCH = 0.95

_COLOR = re.compile(r"rgba?\(([^)]*)\)|#[0-9a-fA-F]{3,8}\b|\btransparent\b")
_NUM = re.compile(r"^-?(\d+\.?\d*|\.\d+)(px)?$")
_TOK = re.compile(r"rgba\([^)]*\)|[^\s,]+|,")


def _rgba(m: re.Match) -> str:
    s = m[0]
    try:
        if s == "transparent":
            return "rgba(0,0,0,0)"
        if s.startswith("#"):
            h = s[1:]
            h = "".join(c * 2 for c in h) if len(h) in (3, 4) else h
            if len(h) not in (6, 8):
                return s
            r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
            a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        else:
            parts = re.split(r"[\s,/]+", m[1].strip())
            if len(parts) not in (3, 4):
                return s
            r, g, b = (float(x) for x in parts[:3])
            a = (float(parts[3].rstrip("%")) / (100 if parts[3].endswith("%") else 1)) if len(parts) == 4 else 1.0
        return f"rgba({round(r)},{round(g)},{round(b)},{round(a, 3):g})"
    except ValueError:
        return s


def norm_value(v) -> str:
    """A style value with every colour as rgba(r,g,b,a), quotes dropped and whitespace collapsed."""
    return " ".join(_COLOR.sub(_rgba, str(v)).replace('"', "").replace("'", "").split())


def tolerance(prop: str, board: str, override: dict) -> float:
    """Colours and text are exact; font and spacing +-1px; width and height +-2px or 1%, whichever is larger; x and y +-2px."""
    if prop in override:
        return float(override[prop])
    if prop in BOX:
        m = _NUM.match(board)
        return max(2.0, 0.01 * abs(float(m[1]))) if m else 2.0
    return 2.0 if prop in POS else 1.0


def same(prop: str, board: str, app: str, override: dict | None = None) -> bool:
    a, b = norm_value(board), norm_value(app)
    if prop == "font-family":
        return a.lower().replace(", ", ",") == b.lower().replace(", ", ",")
    ta, tb = _TOK.findall(a), _TOK.findall(b)
    if len(ta) != len(tb):
        return False
    tol = tolerance(prop, a, override or {})
    for x, y in zip(ta, tb, strict=True):
        x, y = ("0px" if t == "normal" else t for t in (x, y))
        mx, my = _NUM.match(x), _NUM.match(y)
        if mx and my:
            if (mx[2] is None and my[2] is None and float(mx[1]) != float(my[1])) or abs(float(mx[1]) - float(my[1])) > tol:
                return False
        elif x != y:
            return False
    return True


# Candidate nodes of one rendered board: headings, buttons, inputs, landmarks (by role plus accessible name) and text blocks
# (by their text). shortcut: a simplified accessible-name computation (aria-label, aria-labelledby, label, alt, content);
# a name the app computes differently shows up as "locator matched 0 elements" in the check, never as a silent pass.
_NODES = """([props, sels, srcImports]) => {
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
    node.el = el;
    out.push(node);
  }
  // frames. The design tool's runtime replaces every <dc-import> with `.sc-host[data-sc-name][data-dc-tpl]`, so the element's attributes
  // are only in the board's source: the top-level hosts, ordered by their template id, are paired with the source tags in order (when
  // the counts differ the pairing is unknown and attribute selection is refused for them). Container frames are elements matching a selector.
  // A label (an element with short own text) belongs to its closest import host, otherwise to its closest container of each selector.
  const IMP = '.sc-host[data-sc-name][data-dc-tpl]';
  const els = [], frames = [], at = new Map();
  const add = (el, kind, selector, attrs, known) => {
    at.set(el, els.length); els.push(el);
    frames.push({kind, selector, captions: [], attrs, known});
  };
  const hosts = [...document.querySelectorAll(IMP)];
  const top = hosts.filter(h => !h.parentElement.closest(IMP));
  const ids = [...new Set(top.map(h => Number(h.getAttribute('data-dc-tpl'))))].sort((a, b) => a - b);
  const paired = ids.length === srcImports.length;
  for (const h of hosts) {
    const isTop = top.includes(h), src = isTop && paired ? srcImports[ids.indexOf(Number(h.getAttribute('data-dc-tpl')))] : null;
    add(h, 'import', null, src || {name: h.getAttribute('data-sc-name')}, !isTop || paired);
  }
  for (const s of sels) document.querySelectorAll(s).forEach(e => add(e, 'container', s, {}, true));
  const caption = (el, i) => { const c = frames[i].captions; if (c.length < 40 && !c.includes(el)) c.push(el); };
  for (const el of document.body.querySelectorAll('*')) {
    if (['SCRIPT', 'STYLE'].includes(el.tagName) || !shown(el)) continue;
    const own = norm([...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' '));
    if (!own || own.length > 200) continue;
    const imp = el.closest(IMP);
    if (imp) caption(own, at.get(imp));
    else for (const s of sels) { const c = el.closest(s); if (c) caption(own, at.get(c)); }
  }
  for (const n of out) {
    n.frames = [];
    for (let a = n.el; a; a = a.parentElement) if (at.has(a)) n.frames.push(at.get(a));
    delete n.el;
  }
  return {nodes: out, frames};
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



_IMPORT = re.compile(r"<dc-import((?:[^>\"']|\"[^\"]*\"|'[^']*')*)/?>", re.I)
_ATTR = re.compile(r"([^\s=/]+)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+)))?")


def source_imports(path: Path) -> list[dict]:
    """The attributes of every <dc-import> tag in a board's source, in document order (the rendered page no longer has them)."""
    text = path.read_text(errors="replace")
    return [{m[1]: next((g for g in m.groups()[1:] if g is not None), "") for m in _ATTR.finditer(tag[1])} for tag in _IMPORT.finditer(text)]


NAV_TIMEOUT_MS = 30000
LOADS = ("domcontentloaded", "load")


def validate_ready(r, who: str) -> None:
    ok = isinstance(r, dict) and len(r) == 1 and (
        (isinstance(r.get("selector"), str) and 0 < len(r["selector"]) <= 200 and "\n" not in r["selector"]) or r.get("load") in LOADS)
    if not ok:
        raise ValueError(f'{who}: ready must be {{"selector": css}} or {{"load": "domcontentloaded" | "load"}}')


def goto(page, url: str, ready: dict | None = None) -> None:
    """Open a page and wait until it is ready: network idle by default, or the entry's `ready` (a selector that must appear, or a load
    event). A wait that times out raises: the board or row fails, it is never skipped."""
    if not ready:
        page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)
    elif "selector" in ready:
        page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        page.wait_for_selector(ready["selector"], state="attached", timeout=NAV_TIMEOUT_MS)
    else:
        page.goto(url, wait_until=ready["load"], timeout=NAV_TIMEOUT_MS)


def _containers(mapping: dict | None, extra: list[str] | None = None) -> list[str]:
    """The caption container selectors an index records frames for: the default plus every one a mapping entry names."""
    sels = [DEFAULT_CONTAINER, *(extra or [])]
    for m in (mapping or {}).get("boards", []):
        if isinstance(m, dict) and isinstance(m.get("container"), str):
            sels.append(m["container"])
    for s in sels:
        if not SELECTOR_RX.match(s):
            raise ValueError(f"container selector {s!r} is not a plain CSS selector")
    return list(dict.fromkeys(sels))


def index_export(root: str | Path, themes=THEMES, viewport: dict | None = None, attr: str | None = None,
                 executable: str | None = None, only: list[str] | None = None, containers: list[str] | None = None,
                 ready: dict[str, dict] | None = None) -> dict:
    """Walk every `*.dc.html` board of an export and list its candidate nodes per theme, with measured style and geometry, and its frames:
    every <dc-import> (its attributes) and every element matching a container selector, each with the label captions that sit in it.
    A node records the frames that contain it, so a frame is selected from the index without reloading the board.
    A board whose files did not all load (a 404 on the /_blob/ stylesheet) is recorded with its errors: nothing is measured from it."""
    from playwright.sync_api import sync_playwright

    root = Path(root)
    vp = viewport or {"width": 1280, "height": 800}
    sels = containers or [DEFAULT_CONTAINER]
    files = only if only is not None else sorted(p.relative_to(root).as_posix() for p in root.rglob("*.dc.html"))
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
                        goto(page, f"{base}/{urllib.parse.quote(f)}", (ready or {}).get(f))
                        if attr:
                            page.evaluate("([a, v]) => document.documentElement.setAttribute(a, v)", [attr, theme])
                        page.evaluate("document.fonts && document.fonts.ready")
                        found = page.evaluate(_NODES, [CANVAS_STYLE, sels, source_imports(root / f)])
                    except Exception as e:  # noqa: BLE001 - one broken board must not stop the walk
                        boards[f][theme] = {"error": str(e)[:160], "nodes": [], "frames": []}
                        continue
                    boards[f][theme] = {"error": "; ".join(errors[:3]) if errors else "", **found}
                ctx.close()
        finally:
            browser.close()
    return {"version": 2, "viewport": vp, "themes": list(themes), "attr": attr, "containers": sels, "boards": boards}


def validate_frame(fr, who: str) -> None:
    ok = isinstance(fr, dict) and (("attrs" in fr) != ("caption" in fr)) and set(fr) <= {"attrs", "caption", "container"}
    if ok and "attrs" in fr:
        ok = isinstance(fr["attrs"], dict) and bool(fr["attrs"]) and "container" not in fr and all(
            isinstance(k, str) and (v is None or isinstance(v, str)) for k, v in fr["attrs"].items())
    if ok and "caption" in fr:
        ok = isinstance(fr["caption"], str) and fr["caption"].strip() != "" and (
            "container" not in fr or (isinstance(fr["container"], str) and SELECTOR_RX.match(fr["container"]) is not None))
    if not ok:
        raise ValueError(f'{who}: frame must be {{"attrs": {{name: value or null}}}} or {{"caption": text, "container": selector (optional)}}')


def select_frame(entry: dict, m: dict, who: str) -> int:
    """The one frame of an indexed board that the entry's `frame` names. attrs is an exact subset match on a <dc-import> element
    (a null value means the attribute must be absent); a caption names a label, and the label's nearest frame container is the closest
    <dc-import>, otherwise the closest ancestor matching the entry's `container` selector (default .cell). Zero or several is an error."""
    fr = m["frame"]
    if "attrs" in fr:
        hit = [i for i, f in enumerate(entry["frames"]) if f["kind"] == "import" and f.get("known", True) and all(
            (k not in f["attrs"]) if v is None else f["attrs"].get(k) == v for k, v in fr["attrs"].items())]
    else:
        sel = fr.get("container", DEFAULT_CONTAINER)
        hit = [i for i, f in enumerate(entry["frames"]) if (f["kind"] == "import" or f["selector"] == sel)
               and " ".join(fr["caption"].split()) in f["captions"]]
    if len(hit) != 1:
        unknown = sum(1 for f in entry["frames"] if f["kind"] == "import" and not f.get("known", True))
        why = f" ({unknown} import frames cannot be paired with their source tags: the source and the render list different numbers of <dc-import>)" \
            if unknown and "attrs" in fr else ""
        raise ValueError(f"entry {who}: frame {json.dumps(fr, sort_keys=True)} matches {len(hit)} frames in the board, it must match exactly one{why}")
    return hit[0]


def check_frames(index: dict | list[dict], mapping: dict) -> None:
    """Every framed entry names exactly one frame of its board (boards missing from the index are rows' business)."""
    validate_mapping(mapping)
    for ix in index if isinstance(index, list) else [index]:
        for m in mapping["boards"]:
            f = m.get("board_file") or m["board"]
            if not m.get("frame") or (m.get("viewport") and list(m["viewport"]) != [ix["viewport"]["width"], ix["viewport"]["height"]]):
                continue
            hits = [k for k in ix["boards"] if k == f or k.rsplit("/", 1)[-1] == f]
            entry = ix["boards"][hits[0]].get(ix["themes"][0]) if len(hits) == 1 else None
            if entry is not None and not entry["error"]:
                _want_container(ix, m)
                select_frame(entry, m, m.get("entry") or f)


def _want_container(ix: dict, m: dict) -> None:
    sel = (m.get("frame") or {}).get("container", DEFAULT_CONTAINER)
    if "caption" in m.get("frame", {}) and sel not in ix.get("containers", [DEFAULT_CONTAINER]):
        raise ValueError(f"entry {m.get('entry') or m['board']}: the index was built without container {sel!r}: run `boards index --mapping` again")


def validate_mapping(mapping: dict) -> None:
    """The mapping file's shape: entries of board (or board_file), route (a path, or null), surface (an extension or Electron app),
    frame (one frame of a multi-frame board), state, theme ("light", "dark" or "light, dark"), viewport ([w, h] or null),
    min_match and tolerances (overrides). Other keys (entry, series, capture, note ...) are bookkeeping."""
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
        who = m.get("entry") or f
        if m.get("surface") is not None:
            if rt:
                raise ValueError(f"entry {who}: give a route or a surface, not both")
            try:
                validate_surface(m["surface"])
            except ValueError as e:
                raise ValueError(f"entry {who}: {e}") from None
        if m.get("frame") is not None:
            validate_frame(m["frame"], f"entry {who}")
        if m.get("ready") is not None:
            validate_ready(m["ready"], f"entry {who}")
        for key in ("tolerances", "min_match"):
            v = m.get(key, mapping.get(key))
            if v is not None and not (isinstance(v, dict) and all(isinstance(x, (int, float)) and x >= 0 for x in v.values()) if key == "tolerances"
                                      else isinstance(v, (int, float)) and 0 < v <= 1):
                raise ValueError(f"entry {who}: {key} is a map of property to px, or a ratio above 0 and up to 1")


def _pick(indexes: list[dict], vp) -> dict | None:
    """The index measured at this entry's viewport (the only one when the entry names none)."""
    return next((ix for ix in indexes if vp is None or [ix["viewport"]["width"], ix["viewport"]["height"]] == list(vp)), None)


def _lkey(loc: dict) -> str:
    return json.dumps(loc, sort_keys=True)


def _values(n: dict, props: list[str]) -> list[str]:
    return [n["style"].get(p, "") if p in CANVAS_STYLE else _fmt(n["box"][p], p) for p in props]


def canvas_rows(index: dict | list[dict], mapping: dict, repo: str | None = None) -> dict:
    """One aggregate row per mapping entry and theme: every node of the board (of the selected frame) whose locator is unique there,
    with the values of the token properties. Nodes that share a locator are listed on the row as unmeasurable, never dropped silently.
    What cannot be measured at all goes under unsupported. `index` is one index, or one per viewport; `repo` keeps one app's entries."""
    validate_mapping(mapping)
    indexes = index if isinstance(index, list) else [index]
    rows: list[dict] = []
    unsupported: list[dict] = []
    props = [*CANVAS_STYLE, *BOX, *(POS if mapping.get("position") else [])]
    ids: set[str] = set()
    for m in mapping["boards"]:
        if repo and m.get("repo") != repo:
            continue
        f = m.get("board_file") or m["board"]
        ident = m.get("entry") or f
        if not m.get("route") and not m.get("surface"):
            unsupported.append({"id": ident, "reason": m.get("note") or "no route or surface: not measured"})
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
            if entry["error"]:
                unsupported.append({"id": who, "reason": f"board did not load cleanly ({entry['error']})"})
                continue
            nodes = entry["nodes"]
            if m.get("frame"):
                _want_container(ix, m)
                fi = select_frame(entry, m, ident)
                nodes = [n for n in nodes if fi in n.get("frames", [])]
            if not nodes:
                unsupported.append({"id": who, "reason": "no candidate nodes" + (" in the frame" if m.get("frame") else "")})
                continue
            seen: dict[str, int] = {}
            for n in nodes:
                seen[_lkey(n["locator"])] = seen.get(_lkey(n["locator"]), 0) + 1
            if who in ids:
                raise ValueError(f"two mapping entries produce the row {who}: give each entry its own entry id")
            ids.add(who)
            label = lambda n: f"{n['role']}:{n['name']}" if n["name"] else n["role"]  # noqa: E731
            rows.append({"id": who, "entry": ident, "board": f, "route": m.get("route"), "surface": m.get("surface"),
                         "theme": theme, "theme_attr": ix.get("attr") or mapping.get("theme_attr"), "viewport": ix["viewport"],
                         "state": m.get("state", "default"), "frame": m.get("frame"), "ready": m.get("ready"), "props": props,
                         "nodes": [{"n": label(n), "l": n["locator"], "v": _values(n, props)} for n in nodes if seen[_lkey(n["locator"])] == 1],
                         "unmeasurable": sorted({label(n) for n in nodes if seen[_lkey(n["locator"])] > 1}),
                         "unmeasurable_nodes": sum(1 for n in nodes if seen[_lkey(n["locator"])] > 1),
                         "min_match": m.get("min_match", mapping.get("min_match", MIN_MATCH)),
                         "tol": {**mapping.get("tolerances", {}), **m.get("tolerances", {})}})
    return {"rows": rows, "unsupported": unsupported}


def judge(row: dict, app_nodes: list[dict]) -> dict:
    """Compare a row with the nodes found in the app: a board node is matched when its locator is found exactly once in the app."""
    found: dict[str, list[dict]] = {}
    for n in app_nodes:
        found.setdefault(_lkey(n["locator"]), []).append(n)
    props, ov = row["props"], row.get("tol") or {}
    matched, unmatched, mismatches = 0, [], []
    for bn in row["nodes"]:
        hit = found.get(_lkey(bn["l"]), [])
        if len(hit) != 1:
            unmatched.append(bn["n"])
            continue
        matched += 1
        for p, want, have in zip(props, bn["v"], _values(hit[0], props), strict=True):
            if not same(p, want, have, ov):
                mismatches.append({"node": bn["n"], "prop": p, "board": want, "app": have})
    return {"matched": matched, "measurable": len(row["nodes"]), "unmatched": unmatched, "mismatches": mismatches}


def verdict(row: dict, res: dict) -> tuple[bool, list[str]]:
    """(passed, report lines) of one row. Unmeasurable nodes are always reported and never waived."""
    if "error" in res:
        return False, [f"FAIL {row['id']}: {res['error']}"]
    n_un, total = row.get("unmeasurable_nodes", len(row.get("unmeasurable", []))), res["measurable"] + row.get("unmeasurable_nodes", 0)
    ratio = res["matched"] / res["measurable"] if res["measurable"] else 0.0
    unproven = total == 0 or n_un / total > UNMEASURABLE_MAX
    ok = not unproven and ratio >= row.get("min_match", MIN_MATCH) and not res["mismatches"]
    head = f"{res['matched']}/{res['measurable']} measurable nodes matched ({ratio:.1%}), {len(res['mismatches'])} mismatches, {n_un} unmeasurable"
    lines = [f"{'PASS' if ok else 'FAIL'} {row['id']}: {head}"]
    for m in res["mismatches"][:50]:
        lines.append(f"  MISMATCH {row['id']} {m['node']} {m['prop']}: board {m['board']}, app {m['app']}")
    if len(res["mismatches"]) > 50:
        lines.append(f"  ... {len(res['mismatches']) - 50} more mismatches")
    if ratio < row.get("min_match", MIN_MATCH):
        lines.append(f"  below min_match {row.get('min_match', MIN_MATCH):g}; not found once in the app: {', '.join(res['unmatched'][:10])}"
                     + (f" (+{len(res['unmatched']) - 10})" if len(res["unmatched"]) > 10 else ""))
    if n_un:
        lines.append(f"  UNMEASURABLE {row['id']}: {n_un} nodes share a locator on the board: {', '.join(row.get('unmeasurable', [])[:10])}")
    if unproven:
        lines.append(f"  UNPROVEN {row['id']}: {n_un} of {total} nodes are unmeasurable (more than {UNMEASURABLE_MAX:.0%}), the row proves nothing")
    return ok, lines


def _app_nodes(page, nav: str | None, row: dict, cur: dict) -> list[dict]:
    """Move the page to the row's route and theme, then list its candidate nodes the way the board's were listed."""
    s = row.get("surface")
    url = None
    if nav is not None:
        url = nav + (row["route"] if not s else "/" + s["page"].lstrip("/"))
    if url and url != cur.get("url"):
        goto(page, url, row.get("ready"))
        cur.update(url=url, theme=None)
    if row.get("viewport") and (s or {}).get("kind") != "electron":
        page.set_viewport_size(row["viewport"])
    if row["theme"] != cur.get("theme"):
        page.emulate_media(color_scheme=row["theme"])
        if row.get("theme_attr"):
            page.evaluate("([a, v]) => document.documentElement.setAttribute(a, v)", [row["theme_attr"], row["theme"]])
        cur["theme"] = row["theme"]
    page.evaluate("document.fonts && document.fonts.ready")
    return page.evaluate(_NODES, [CANVAS_STYLE, [], []])["nodes"]


def measure_rows(spec: dict, rows: list[dict], executable: str | None, root: Path) -> list[dict]:
    """Judge every row. All rows of one surface run in one browser session: one launch for the web rows, one per extension or app."""
    from playwright.sync_api import sync_playwright

    groups: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        groups.setdefault(_skey(r.get("surface") or {"kind": "web"}), []).append(i)
    out: list[dict] = [{}] * len(rows)
    with sync_playwright() as p:
        for idxs in groups.values():
            s = rows[idxs[0]].get("surface") or {"kind": "web", **spec.get("target", {})}
            page, close, nav = _launch(p, s if s.get("kind") != "web" else {"kind": "web", "url": spec.get("target", {}).get("url", "")},
                                       executable, root)
            cur: dict = {}
            try:
                for i in idxs:
                    try:
                        out[i] = judge(rows[i], _app_nodes(page, nav, rows[i], cur))
                    except Exception as e:  # noqa: BLE001 - a page that cannot be entered or read fails its row
                        out[i] = {"error": f"could not measure: {str(e)[:120]}"}
                    if spec.get("evidence_dir") and ("error" in out[i] or out[i]["mismatches"]):
                        _shot(page, spec["evidence_dir"], rows[i])
            finally:
                close()
    return out


def _check_aggregate(spec: dict, rows: list[dict], exe: str | None) -> int:
    root = Path.cwd()
    for r in rows:
        s = r.get("surface")
        if s:
            validate_surface(s)
            _inside(root, s.get("dist") or s["app"])
        elif not str(r.get("route", "")).startswith("/"):
            raise ValueError(f"row {r.get('id')}: a web row needs a route")
    if any(not r.get("surface") for r in rows) or any(r["surface"]["kind"] != "electron" for r in rows):
        ok, why = browser_available(exe)
        if not ok:
            print(f"env: browser unavailable ({why})")
            return 127
    try:
        results = measure_rows(spec, rows, exe, root)
    except EnvError as e:
        print(f"env: browser unavailable ({e})")
        return 127
    failed = 0
    for r, res in zip(rows, results, strict=True):
        ok, lines = verdict(r, res)
        failed += not ok
        print("\n".join(lines))
    print(f"Ran {len(rows)} checks")
    unproven = spec.get("unsupported", [])  # entries `boards rows` could not turn into a row: listed, never counted as passed, never waived
    for u in unproven:
        print(f"UNPROVEN {u['id']}: {u['reason']}")
    if failed:
        print(f"{failed} failed")
    if unproven:
        print(f"{len(unproven)} not proven (fix the mapping or the export; there is no waiver)")
    return 1 if failed or unproven else 0


def _check(spec_path: str, flags: list[str] | None = None) -> int:
    """`--expected-rows N` comes from the runner argv, i.e. the approved contract row: a spec file the candidate could edit never sets
    how many rows must run. There is no waiver (4.2): what cannot be measured is reported and fails or is fixed at the source."""
    flags = flags or []
    if "--waive" in flags:
        print("board: --waive is gone: unmeasurable nodes are reported and never waived")
        return 2
    spec = json.loads(_safe(spec_path).read_text())
    rows, target, exe = spec.get("rows", []), spec.get("target", {}), spec.get("executable")
    if spec.get("evidence_dir"):
        _safe(spec["evidence_dir"])
    if target.get("file"):
        _safe(target["file"])
    expected = int(_arg(flags, "--expected-rows", 0))
    if not rows:  # a check that measured nothing proves nothing
        print("Ran 0 checks\nFAIL no rows: the spec has nothing to measure")
        return 1
    if len(rows) < expected:
        print(f"FAIL only {len(rows)} rows, the approved contract row expects {expected}")
        return 1
    if any("nodes" in r for r in rows):
        if not all("nodes" in r for r in rows):
            raise ValueError("a spec holds aggregate rows or per-node rows, not both")
        return _check_aggregate(spec, rows, exe)
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
    lines, failed = evaluate(results)
    print("\n".join(lines))
    print(f"Ran {len(rows)} checks")
    unproven = spec.get("unsupported", [])
    for u in unproven:
        print(f"UNPROVEN {u['id']}: {u['reason']}")
    if failed:
        print(f"{failed} failed")
    if unproven:
        print(f"{len(unproven)} not proven (fix them; there is no waiver)")
    return 1 if failed or unproven else 0


def _extract_cli(argv: list[str]) -> int:
    board = json.loads(_safe(argv[0]).read_text())
    tokens = json.loads(_safe(argv[argv.index("--tokens") + 1]).read_text()) if "--tokens" in argv else None
    text = json.dumps(extract(board, tokens), indent=2)
    if out := _out(argv):
        out.write_text(text + "\n")
    print(text)
    return 0


def _safe(path) -> Path:
    """Every path taken from argv or a spec file goes through here: one inside the run records (SDLC_HOME, resolved) is refused,
    because only the runner reads or writes there."""
    home = Path(os.environ.get("SDLC_HOME") or Path.home() / ".sdlc").resolve()
    if Path(path).resolve().is_relative_to(home):
        raise ValueError(f"{path} is inside the run records; use a path outside {home}")
    return Path(path)


def _out(argv: list[str], default: str | None = None) -> Path | None:
    v = _arg(argv, "--out", default)
    return None if v is None else _safe(v)


def _arg(argv: list[str], flag: str, default=None):
    return argv[argv.index(flag) + 1] if flag in argv else default



def _index_cli(argv: list[str]) -> int:
    out = _out(argv, "index.json")  # refuse a records path before any work, whether or not a browser exists
    root = _safe(argv[0])
    mapping = json.loads(_safe(_arg(argv, "--mapping")).read_text()) if "--mapping" in argv else None
    if mapping:
        validate_mapping(mapping)
    ok, why = browser_available(_arg(argv, "--executable"))
    if not ok:
        print(f"env: browser unavailable ({why})")
        return 127
    w, _, h = _arg(argv, "--viewport", "1280x800").partition("x")
    vp = {"width": int(w), "height": int(h)}
    only = None
    if mapping:  # index only the boards the mapping names (at this viewport): a framed entry is checked against the real board here
        want = {m.get("board_file") or m["board"] for m in mapping["boards"] if not m.get("viewport") or list(m["viewport"]) == [vp["width"], vp["height"]]}
        only = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.dc.html") if p.name in want or p.relative_to(root).as_posix() in want)
    extra = [argv[i + 1] for i, a in enumerate(argv) if a == "--container"]
    ready: dict[str, dict] = {}
    for m in (mapping or {}).get("boards", []):  # a board is loaded once: entries sharing it must agree on how it is ready
        if m.get("ready"):
            for f in only or []:
                if f == (m.get("board_file") or m["board"]) or f.rsplit("/", 1)[-1] == (m.get("board_file") or m["board"]):
                    if ready.setdefault(f, m["ready"]) != m["ready"]:
                        raise ValueError(f"board {f}: entries name different ready waits")
    idx = index_export(root, _arg(argv, "--themes", ",".join(THEMES)).split(","), vp, _arg(argv, "--attr"), _arg(argv, "--executable"), only,
                       _containers(mapping, extra), ready)
    Path(out).write_text(json.dumps(idx, separators=(",", ":")) + "\n")
    bad = [f for f, t in idx["boards"].items() if any(v["error"] for v in t.values())]
    n_frames = sum(len(t[idx["themes"][0]]["frames"]) for t in idx["boards"].values() if idx["themes"][0] in t)
    print(f"indexed {len(idx['boards'])} boards, {sum(len(v['nodes']) for t in idx['boards'].values() for v in t.values())} nodes, "
          f"{n_frames} frames -> {out}")
    for f in bad:
        print(f"WARN {f}: " + "; ".join(v["error"] for v in idx["boards"][f].values() if v["error"]))
    if mapping:
        check_frames(idx, mapping)
    return 0


def _rows_cli(argv: list[str]) -> int:
    mapping = json.loads(_safe(argv[0]).read_text())
    files = [argv[i + 1] for i, a in enumerate(argv) if a == "--index"] or ["index.json"]  # one per viewport
    idx = [json.loads(_safe(f).read_text()) for f in files]
    try:
        res = canvas_rows(idx, mapping, _arg(argv, "--repo"))
    except ValueError as e:
        print(f"mapping: {e}")
        return 2
    out = {"version": 2, "target": {"kind": "web", "url": _arg(argv, "--url", mapping.get("url", ""))}, "rows": res["rows"],
           "unsupported": res["unsupported"]}
    _out(argv, "spec.json").write_text(json.dumps(out, separators=(",", ":")) + "\n")
    nodes = sum(len(r["nodes"]) for r in res["rows"])
    print(f"{len(res['rows'])} rows ({nodes} nodes), {len(res['unsupported'])} unsupported; the contract row needs --expected-rows {len(res['rows'])}")
    for r in res["rows"]:
        n_un = r["unmeasurable_nodes"]
        if n_un / (len(r["nodes"]) + n_un) > UNMEASURABLE_MAX:
            print(f"UNPROVEN {r['id']}: {n_un} of {len(r['nodes']) + n_un} nodes are unmeasurable")
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
        return _check(argv[1], argv[2:])
    if len(argv) >= 2 and argv[0] == "extract":
        return _extract_cli(argv[1:])
    print("usage: board.py check <spec.json> [--expected-rows N] | extract <board.json> [--tokens t.json] [--out rows.json]\n"
          "       board.py index <export-dir> [--out index.json] [--themes light,dark] [--viewport 1280x800] [--attr data-theme]\n"
          "                      [--mapping mapping.json] [--container SELECTOR]...\n"
          "       board.py rows <mapping.json> --index index.json [--index other.json] [--repo web] [--url http://app] [--out spec.json]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

