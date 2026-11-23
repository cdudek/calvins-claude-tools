"""4.1: design-canvas boards: an export served over local HTTP, generated node locators, light and dark, measured rows."""
import json
import subprocess
import sys
from pathlib import Path

import board
import pytest
import sdlc

HERE = Path(__file__).parent
needs_browser = pytest.mark.skipif(not board.browser_available()[0], reason="no Chromium installed here (playwright install chromium)")

# the export's stylesheet is an absolute /_blob/ path, as in a real design-canvas export; the theme comes from the colour scheme
BLOB = """body{margin:0;font:16px/24px sans-serif;background:#fff;color:#111}
.pay{padding:0 16px;width:358px;height:44px;background:rgb(0, 100, 200);color:#fff;border:0;border-radius:8px}
@media (prefers-color-scheme: dark){body{background:#111;color:#eee}.pay{background:rgb(10, 20, 30)}}"""
BOARD = """<!doctype html><html><head><link rel="stylesheet" href="/_blob/theme.css"><script src="./support.js"></script></head><body>
<header aria-label="Top"><h1>Checkout</h1></header><main><p>Review your order</p><button class="pay">Pay</button>
<label>Email <input type="email"></label><p>Same</p><p>Same</p></main></body></html>"""
APP = """<!doctype html><html><head><style>%s</style></head><body><header aria-label="Top"><h1>Checkout</h1></header>
<main><p>Review your order</p><button class="pay">Pay</button><label>Email <input type="email"></label><p>Same</p><p>Same</p></main></body></html>"""
MAPPING = {"boards": [{"board": "checkout.dc.html", "route": "/checkout.html", "state": "default"}]}


def export(tmp_path, blob=True, board_html=BOARD):
    root = tmp_path / "export"
    (root / "_blob").mkdir(parents=True)
    if blob:
        (root / "_blob" / "theme.css").write_text(BLOB)
    (root / "support.js").write_text("window.__support = 1")
    (root / "checkout.dc.html").write_text(board_html)
    return root


def app(tmp_path, css=BLOB):
    root = tmp_path / "app"
    root.mkdir(parents=True)
    (root / "checkout.html").write_text(APP % css)
    return root


def check(spec: dict, tmp_path):
    f = tmp_path / "spec.json"
    f.write_text(json.dumps(spec))
    p = subprocess.run([sys.executable, str(HERE / "board.py"), "check", str(f)], capture_output=True, text=True)
    return p.returncode, p.stdout


def by_label(idx, theme="light"):
    return {(n["role"], n["name"]): n for n in idx["boards"]["checkout.dc.html"][theme]["nodes"]}


@needs_browser
def test_the_export_is_served_over_local_http_so_absolute_blob_paths_resolve(tmp_path):
    idx = board.index_export(export(tmp_path))
    nodes = by_label(idx)
    assert idx["boards"]["checkout.dc.html"]["light"]["error"] == ""  # the /_blob/ stylesheet and ./support.js loaded
    pay = nodes[("button", "Pay")]
    assert pay["style"]["background-color"] == "rgb(0, 100, 200)" and pay["style"]["padding-left"] == "16px"  # the blob css applied
    assert (pay["box"]["width"], pay["box"]["height"]) == (358, 44) and pay["locator"] == {"role": "button", "name": "Pay"}


@needs_browser
def test_candidates_are_headings_buttons_inputs_landmarks_and_text_found_by_role_and_name_or_text(tmp_path):
    nodes = by_label(board.index_export(export(tmp_path)))
    assert ("heading", "Checkout") in nodes and ("button", "Pay") in nodes and ("textbox", "Email") in nodes
    assert nodes[("banner", "Top")]["locator"] == {"role": "banner", "name": "Top"} and ("main", "") in nodes
    assert nodes[("text", "Review your order")]["locator"] == {"text": "Review your order"}
    assert nodes[("text", "Same")]["count"] == 2  # an ambiguous locator is flagged, not guessed


@needs_browser
def test_light_and_dark_are_both_measured(tmp_path):
    idx = board.index_export(export(tmp_path))
    assert by_label(idx, "light")[("button", "Pay")]["style"]["background-color"] == "rgb(0, 100, 200)"
    assert by_label(idx, "dark")[("button", "Pay")]["style"]["background-color"] == "rgb(10, 20, 30)"


@needs_browser
def test_a_board_whose_stylesheet_404s_is_recorded_and_nothing_is_measured_from_it(tmp_path):
    idx = board.index_export(export(tmp_path, blob=False))
    assert "404 _blob/theme.css" in idx["boards"]["checkout.dc.html"]["light"]["error"]
    out = board.canvas_rows(idx, MAPPING)
    assert out["rows"] == [] and all("did not load cleanly" in u["reason"] for u in out["unsupported"])


@needs_browser
def test_rows_come_from_the_mapping_and_the_index_only_and_ambiguous_nodes_are_unsupported(tmp_path):
    out = board.canvas_rows(board.index_export(export(tmp_path)), {**MAPPING, "themes": ["light"]})
    ids = {r["id"] for r in out["rows"]}
    assert "checkout.dc.html/light/button:Pay/padding-left" in ids and "checkout.dc.html/light/button:Pay/width" in ids
    assert all(r["route"] == "/checkout.html" and r["theme"] == "light" and r["source"] == "measured" for r in out["rows"])
    assert any(u["id"].endswith("text:Same") and "2 nodes" in u["reason"] for u in out["unsupported"])
    assert not any("/x" in i or i.endswith("/y") for i in ids)  # position is opt-in: layouts differ between a canvas and an app


@needs_browser
def test_app_is_compared_on_computed_style_and_geometry_in_light_and_dark(tmp_path):
    idx = board.index_export(export(tmp_path))
    rows = board.canvas_rows(idx, MAPPING)["rows"]
    with board.serve(app(tmp_path)) as url:
        spec = {"target": {"kind": "web", "url": url}, "rows": rows}
        code, out = check(spec, tmp_path)
        assert code == 0, out
        assert "PASS checkout.dc.html/dark/button:Pay/background-color: rgb(10, 20, 30)" in out
        # a padding and a size that drift beyond the tolerances fail, naming the node, theme and values
        drift = BLOB.replace("padding:0 16px;width:358px", "padding:0 12px;width:358px").replace("height:44px", "height:47px")
        with board.serve(app(tmp_path / "x", drift)) as url2:
            code, out = check({"target": {"kind": "web", "url": url2}, "rows": rows}, tmp_path)
        assert code == 1
        assert "FAIL checkout.dc.html/light/button:Pay/padding-left: expected 16px, got 12px" in out and "button:Pay/height" in out
        # a dark-only colour drift fails only the dark rows
        dark = BLOB.replace("rgb(10, 20, 30)", "rgb(10, 20, 31)")
        with board.serve(app(tmp_path / "y", dark)) as url3:
            code, out = check({"target": {"kind": "web", "url": url3}, "rows": rows}, tmp_path)
        assert code == 1 and "FAIL checkout.dc.html/dark/button:Pay/background-color" in out and "FAIL checkout.dc.html/light" not in out
        # within the geometry tolerance (1px) it still passes
        near = BLOB.replace("height:44px", "height:44.6px")
        with board.serve(app(tmp_path / "z", near)) as url4:
            assert check({"target": {"kind": "web", "url": url4}, "rows": rows}, tmp_path)[0] == 0


@needs_browser
def test_theme_attribute_boards_are_supported(tmp_path):
    css = ":root[data-theme=dark] .pay{background:rgb(1, 2, 3)} .pay{background:rgb(9, 9, 9)}"
    root = export(tmp_path, board_html="<html><body><button class=pay>Pay</button><style>%s</style></body></html>" % css)
    idx = board.index_export(root, attr="data-theme")
    rows = board.canvas_rows(idx, MAPPING)["rows"]
    assert {r["theme_attr"] for r in rows} == {"data-theme"}
    a = tmp_path / "a"
    a.mkdir()
    (a / "checkout.html").write_text("<html><body><button class=pay>Pay</button><style>%s</style></body></html>" % css)
    with board.serve(a) as url:
        assert check({"target": {"kind": "web", "url": url}, "rows": [r for r in rows if r["prop"] == "background-color"]}, tmp_path)[0] == 0


@needs_browser
def test_extract_supports_the_canvas_kind_and_the_cli_writes_index_then_spec(tmp_path):
    root = export(tmp_path)
    out = board.extract({"kind": "canvas", "root": str(root), "file": "checkout.dc.html", "route": "/checkout.html", "themes": ["dark"]})
    assert out["rows"] and {r["theme"] for r in out["rows"]} == {"dark"}
    m = tmp_path / "mapping.json"
    m.write_text(json.dumps(MAPPING))
    assert sdlc.main(["boards", "index", str(root), "--out", str(tmp_path / "idx.json")]) == 0
    assert sdlc.main(["boards", "rows", str(m), "--index", str(tmp_path / "idx.json"), "--url", "http://x", "--out", str(tmp_path / "s.json")]) == 0
    spec = json.loads((tmp_path / "s.json").read_text())
    assert spec["target"] == {"kind": "web", "url": "http://x"} and spec["rows"] and spec["unsupported"]


def test_browser_unavailable_is_an_environment_problem_not_a_verdict(tmp_path, capsys):
    assert sdlc.main(["boards", "index", str(tmp_path), "--executable", "/nonexistent/chrome"]) == 127
    assert "env: browser unavailable" in capsys.readouterr().out
    out = board.extract({"kind": "canvas", "root": str(tmp_path), "file": "a.dc.html", "route": "/", "executable": "/nonexistent/chrome"})
    assert out["rows"] == [] and "browser unavailable" in out["unsupported"][0]["reason"]


def test_no_baseline_or_image_approval_exists_in_the_canvas_path():
    src = (HERE / "board.py").read_text()
    assert "baseline" not in src.lower().replace("no baselines", "") and "approve" not in src
