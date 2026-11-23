"""Board extraction and real-surface UI checks (design 3.5).

extract() turns a board into expectation rows (or lists what it cannot measure),
measure() reads the live surface with Playwright, evaluate() makes the verdict lines.
A contract runner: `python3 board.py check spec.json`. verify.py imports browser_available.
"""

from __future__ import annotations

import json
import os
import re
import sys
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
            app = p._electron.launch(args=[str(Path(target["main"]).resolve())])  # noqa: SLF001
            return app.first_window(), app.close
    except Exception as e:  # noqa: BLE001
        raise EnvError(f"{kind} target did not start: {str(e)[:120]}") from e
    raise EnvError(f"unknown target kind {kind!r}")


def _locate(page, loc: dict):
    if "css" in loc:
        return page.locator(loc["css"])
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
    """Per row: {"value": measured string/number or None, "why": ...}."""
    from playwright.sync_api import sync_playwright

    out: list[dict] = []
    with sync_playwright() as p:
        page, close = _launch(p, target, executable)
        try:
            for row in rows:
                res = _read_row(page, target, row)
                if evidence_dir and res.get("value") is None:
                    _shot(page, evidence_dir, row)
                out.append(res)
        finally:
            close()
    return out


def _read_row(page, target: dict, row: dict) -> dict:
    vp = row.get("viewport")
    if vp and target.get("kind") != "electron":
        page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
    try:
        el, why = _one(page, row["locator"])
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


def _check(spec_path: str) -> int:
    spec = json.loads(Path(spec_path).read_text())
    rows, target, exe = spec.get("rows", []), spec.get("target", {}), spec.get("executable")
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
    if failed:
        print(f"{failed} failed")
    return 1 if failed else 0


def _extract_cli(argv: list[str]) -> int:
    board = json.loads(Path(argv[0]).read_text())
    tokens = json.loads(Path(argv[argv.index("--tokens") + 1]).read_text()) if "--tokens" in argv else None
    text = json.dumps(extract(board, tokens), indent=2)
    if "--out" in argv:
        Path(argv[argv.index("--out") + 1]).write_text(text + "\n")
    print(text)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "check":
        return _check(argv[1])
    if len(argv) >= 2 and argv[0] == "extract":
        return _extract_cli(argv[1:])
    print("usage: board.py check <spec.json> | extract <board.json> [--tokens t.json] [--out rows.json]")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
