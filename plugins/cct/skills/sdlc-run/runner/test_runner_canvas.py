"""4.2: design-canvas boards as aggregate rows (one per mapping entry and theme), frames, and the extension and Electron surfaces."""
import json
import socket
import subprocess
import sys
from pathlib import Path

import board
import contract
import pytest
import sdlc
import testkit as tk
import verify
import store
from store import SdlcError

HERE = Path(__file__).parent
needs_browser = pytest.mark.skipif(not board.browser_available()[0], reason="no Chromium installed here (playwright install chromium)")

# the export's stylesheet is an absolute /_blob/ path, as in a real design-canvas export; the theme comes from the colour scheme
BLOB = """body{margin:0;font:16px/24px sans-serif;background:#fff;color:#111}
.pay{padding:0 16px;width:358px;height:44px;background:rgb(0, 100, 200);color:#fff;border:0;border-radius:8px}
.a{background:rgb(1, 2, 3)} .b{background:rgb(4, 5, 6)}
@media (prefers-color-scheme: dark){body{background:#111;color:#eee}.pay{background:rgb(10, 20, 30)}}"""
# a stand-in for the design tool's runtime: it replaces every <dc-import> by a `.sc-host[data-sc-name][data-dc-tpl]` holding the rendered
# component (the element and its attributes are gone from the page, as in a real export); an import marked `hidden` renders nothing
SUPPORT = """document.addEventListener('DOMContentLoaded', () => { let id = 3;
  document.querySelectorAll('dc-import').forEach(e => {
    if (e.hasAttribute('hidden')) { e.remove(); return; }
    const t = e.getAttribute('tone'), h = document.createElement('div');
    h.className = 'sc-host'; h.setAttribute('data-sc-name', e.getAttribute('name')); h.setAttribute('data-dc-tpl', String(id)); id += 5;
    h.innerHTML = '<button class="pay ' + t + '">Save</button><span>Tone ' + t + '</span>'; e.replaceWith(h); }); });"""
BOARD = """<!doctype html><html><head><link rel="stylesheet" href="/_blob/theme.css"><script src="./support.js"></script></head><body>
<header aria-label="Top"><h1>Checkout</h1></header><main><p>Review your order</p><button class="pay">Pay</button>
<label>Email <input type="email"></label><p>Same</p><p>Same</p><p>Aa</p><p>Bb</p><p>Cc</p><p>Dd</p></main></body></html>"""
APP = """<!doctype html><html><head><style>%s</style></head><body><header aria-label="Top"><h1>Checkout</h1></header>
<main><p>Review your order</p><button class="pay">Pay</button><label>Email <input type="email"></label><p>Same</p><p>Same</p><p>Aa</p><p>Bb</p><p>Cc</p><p>Dd</p></main></body></html>"""
# two frames of one board by <dc-import> attributes, and a board with no <dc-import> whose frames are `.cell` containers with a label
FRAMES = """<!doctype html><html><head><link rel="stylesheet" href="/_blob/theme.css"><script src="./support.js"></script></head><body>
<dc-import name="Card" tone="a" dlg="x"></dc-import><dc-import name="Card" tone="a"></dc-import><dc-import name="Card" tone="b" dlg="y"></dc-import></body></html>"""
CELLS = """<!doctype html><html><head><link rel="stylesheet" href="/_blob/theme.css"></head><body>
<div class="cell"><span class="lbl">Empty</span><button class="pay">Pay</button></div>
<div class="cell"><span class="lbl">Full</span><button class="pay" style="padding:0 20px">Pay</button><button>Other</button></div></body></html>"""
MIXED = """<!doctype html><html><head><link rel="stylesheet" href="/_blob/theme.css"><script src="./support.js"></script></head><body>
<dc-import name="Card" tone="a" hidden></dc-import><dc-import name="Card" tone="b"></dc-import></body></html>"""
LIST = """<!doctype html><html><head><link rel="stylesheet" href="/_blob/theme.css"></head><body><main><h2>Members</h2><ul>
<li style="width:100px">Row</li><li style="width:110px">Row</li><li style="width:120px">Row</li><li style="width:130px">Row</li><li style="width:140px">Row</li>
</ul></main></body></html>"""
POPUP = """<!doctype html><html><head><link rel="stylesheet" href="/_blob/theme.css"></head><body><button class="pay">Pay</button></body></html>"""
MAPPING = {"boards": [{"board": "checkout.dc.html", "route": "/checkout.html", "state": "default"}]}


def export(tmp_path, blob=True, **boards):
    root = tmp_path / "export"
    (root / "_blob").mkdir(parents=True)
    if blob:
        (root / "_blob" / "theme.css").write_text(BLOB)
    (root / "support.js").write_text(SUPPORT)
    for name, html in {"checkout": BOARD, "frames": FRAMES, "cells": CELLS, "popup": POPUP, "mixed": MIXED, "list": LIST, **boards}.items():
        (root / f"{name}.dc.html").write_text(html)
    return root


def app(tmp_path, html=APP, css=BLOB):
    root = tmp_path / "app"
    root.mkdir(parents=True, exist_ok=True)
    (root / "checkout.html").write_text(html % css if "%s" in html else html)
    return root


def check(spec: dict, tmp_path, cwd=None, *flags):
    f = tmp_path / "spec.json"
    f.write_text(json.dumps(spec))
    p = subprocess.run([sys.executable, str(HERE / "board.py"), "check", str(f), *flags], capture_output=True, text=True, cwd=cwd)
    return p.returncode, p.stdout


def web_spec(url, rows, **kw):
    return {"target": {"kind": "web", "url": url}, "rows": rows, **kw}


@pytest.fixture(scope="module")
def idx(tmp_path_factory):
    if not board.browser_available()[0]:
        pytest.skip("no Chromium installed here (playwright install chromium)")
    return board.index_export(export(tmp_path_factory.mktemp("exp")), containers=[".cell"])


def labels(row):
    return {n["n"] for n in row["nodes"]}


# ---- 1 aggregate rows ------------------------------------------------------------------------------------------------

@needs_browser
def test_the_export_is_served_over_local_http_and_light_and_dark_are_both_indexed(idx):
    light, dark = idx["boards"]["checkout.dc.html"]["light"], idx["boards"]["checkout.dc.html"]["dark"]
    assert light["error"] == "" and dark["error"] == ""  # the /_blob/ stylesheet and ./support.js loaded
    pay = {(n["role"], n["name"]): n for n in light["nodes"]}[("button", "Pay")]
    assert pay["style"]["background-color"] == "rgb(0, 100, 200)" and pay["style"]["margin-top"] == "0px" and "box-shadow" in pay["style"]
    assert (pay["box"]["width"], pay["box"]["height"]) == (358, 44) and pay["locator"] == {"role": "button", "name": "Pay"}
    assert {(n["role"], n["name"]): n for n in dark["nodes"]}[("button", "Pay")]["style"]["background-color"] == "rgb(10, 20, 30)"


@needs_browser
def test_one_row_per_entry_and_theme_with_token_properties_and_unmeasurable_nodes_listed(idx):
    out = board.canvas_rows(idx, MAPPING)
    assert [r["id"] for r in out["rows"]] == ["checkout.dc.html/light", "checkout.dc.html/dark"] and out["unsupported"] == []
    row = out["rows"][0]
    assert labels(row) >= {"button:Pay", "heading:Checkout", "text:Review your order"} and "text:Same" not in labels(row)
    # the two identical paragraphs are anchored to `main` and numbered: measurable, with the anchored locator in the report
    assert labels(row) >= {"text:Same[0] in main", "text:Same[1] in main"} and row["unmeasurable"] == [] and row["unmeasurable_nodes"] == 0
    same = [n for n in row["nodes"] if n["n"].startswith("text:Same")]
    assert [(n["i"], n["g"], n["a"]) for n in same] == [(0, 2, {"role": "main"}), (1, 2, {"role": "main"})]
    assert row["props"][:3] == ["color", "background-color", "border-color"] and row["props"][-2:] == ["width", "height"]
    assert "x" not in row["props"] and board.canvas_rows(idx, {**MAPPING, "position": True})["rows"][0]["props"][-2:] == ["x", "y"]  # position is opt-in
    assert row["min_match"] == 0.95
    pay = next(n for n in row["nodes"] if n["n"] == "button:Pay")
    assert pay["v"][row["props"].index("padding-left")] == "16px" and pay["v"][row["props"].index("width")] == "358px"


@needs_browser
def test_app_rows_pass_and_a_drift_lists_node_property_board_value_and_app_value(idx, tmp_path):
    rows = board.canvas_rows(idx, MAPPING)["rows"]
    with board.serve(app(tmp_path)) as url:
        code, out = check(web_spec(url, rows), tmp_path)
        assert code == 0, out
        assert "PASS checkout.dc.html/dark: " in out and "0 mismatches, 0 unmeasurable" in out
        assert "Ran 2 checks" in out
        # padding and height beyond their tolerances, and a dark-only colour: each is listed as locator, property, board value, app value
        drift = BLOB.replace("padding:0 16px", "padding:0 12px").replace("height:44px", "height:47px").replace("rgb(10, 20, 30)", "rgb(10, 20, 31)")
        with board.serve(app(tmp_path / "x", css=drift)) as url2:
            code, out = check(web_spec(url2, rows), tmp_path)
        assert code == 1 and "FAIL checkout.dc.html/light: " in out
        assert "MISMATCH checkout.dc.html/light button:Pay padding-left: board 16px, app 12px" in out
        assert "MISMATCH checkout.dc.html/light button:Pay height: board 44px, app 47px" in out
        assert "MISMATCH checkout.dc.html/dark button:Pay background-color: board rgb(10, 20, 30), app rgb(10, 20, 31)" in out
        # within the tolerances (padding 1px, height 2px) it still passes
        near = BLOB.replace("padding:0 16px", "padding:0 16.9px").replace("height:44px", "height:45.9px")
        with board.serve(app(tmp_path / "y", css=near)) as url3:
            assert check(web_spec(url3, rows), tmp_path)[0] == 0


def row_of(nodes, unmeasurable=0, **kw):
    return {"id": "r", "props": ["width", "color"], "nodes": [{"n": n, "l": {"text": n}, "v": ["10px", "red"]} for n in nodes],
            "unmeasurable": ["dup"] * min(unmeasurable, 1), "unmeasurable_nodes": unmeasurable, **kw}


def app_nodes(names, color="red", width=10):
    return [{"locator": {"text": n}, "style": {"color": color}, "box": {"width": width}} for n in names]


def test_pass_needs_the_match_ratio_and_no_mismatch_among_the_matched_nodes():
    names = [f"n{i}" for i in range(20)]
    ok, lines = board.verdict(row_of(names), board.judge(row_of(names), app_nodes(names)))
    assert ok and "20/20 measurable nodes matched (100.0%), 0 mismatches" in lines[0]
    assert board.verdict(row_of(names), board.judge(row_of(names), app_nodes(names[:19])))[0]  # 19/20 = 95%, the default min_match
    ok, lines = board.verdict(row_of(names), board.judge(row_of(names), app_nodes(names[:18])))
    assert not ok and "below min_match 0.95" in lines[-1] and "n18" in lines[-1]
    assert not board.verdict(row_of(names, min_match=0.9), board.judge(row_of(names, min_match=0.9), app_nodes(names[:18])))[0]  # floored at 0.95
    ok, lines = board.verdict(row_of(names), board.judge(row_of(names), app_nodes(names, color="blue")))  # one wrong value fails a full match
    assert not ok and "MISMATCH r n0 color: board red, app blue" in lines[1]
    both = app_nodes(["n0"]) * 2  # a locator found twice in the app is not matched
    assert board.judge(row_of(["n0"]), both)["unmatched"] == ["n0"]


def test_tolerances_default_and_per_row_overrides():
    assert board.same("padding-left", "16px", "17px") and not board.same("padding-left", "16px", "17.5px")
    assert board.same("width", "1000px", "1010px") and not board.same("width", "1000px", "1011px") and board.same("width", "100px", "102px")
    assert board.same("color", "#0064c8", "rgb(0, 100, 200)") and not board.same("color", "rgb(0, 100, 200)", "rgb(0, 100, 201)")
    assert board.same("box-shadow", "rgba(0, 0, 0, 0.1) 0px 1px 2px", "rgba(0,0,0,0.1) 0px 1px 2px") and board.same("font-weight", "700", "700")
    assert not board.same("font-weight", "700", "600") and board.same("font-family", '"Inter", sans-serif', "Inter,sans-serif")
    assert not board.same("font-size", "14px", "16px") and board.same("font-size", "14px", "16px", {"font-size": 2})
    row = row_of(["n"], tol={"width": 5})
    assert board.judge(row, app_nodes(["n"], width=14))["mismatches"] == [] and board.judge(row_of(["n"]), app_nodes(["n"], width=14))["mismatches"]


def test_more_than_a_fifth_unmeasurable_is_unproven_and_a_failure_never_waived(tmp_path, capsys):
    names = [f"n{i}" for i in range(8)]
    row = row_of(names, unmeasurable=2)  # 2 of 10 = 20%: reported, not a failure
    ok, lines = board.verdict(row, board.judge(row, app_nodes(names)))
    assert ok and any("UNMEASURABLE r: 2 nodes" in ln for ln in lines) and not any("UNPROVEN" in ln for ln in lines)
    row = row_of(names, unmeasurable=3)  # 3 of 11 = 27%
    ok, lines = board.verdict(row, board.judge(row, app_nodes(names)))
    assert not ok and any("UNPROVEN r: 3 of 11 nodes are unmeasurable" in ln for ln in lines)
    f = tmp_path / "s.json"
    f.write_text(json.dumps(web_spec("http://x", [row])))
    assert board.main(["check", str(f), "--waive", "r"]) == 2 and "--waive is gone" in capsys.readouterr().out


@needs_browser
def test_a_series_check_runs_all_its_rows_in_one_browser_session_and_keeps_expected_rows(idx, tmp_path, monkeypatch):
    rows = board.canvas_rows(idx, MAPPING)["rows"]
    rows += [{**r, "id": r["id"] + "-again"} for r in rows]
    launches = []
    real = board._launch
    monkeypatch.setattr(board, "_launch", lambda *a, **k: (launches.append(1), real(*a, **k))[1])
    with board.serve(app(tmp_path)) as url:
        res = board.measure_rows({"target": {"url": url}}, rows, None, tmp_path)
    assert launches == [1] and [r["mismatches"] for r in res] == [[]] * 4
    code, out = check(web_spec("http://x", rows[:2]), tmp_path, None, "--expected-rows", "4")
    assert code == 1 and "only 2 rows, the approved contract row expects 4" in out


@needs_browser
def test_boards_rows_prints_the_count_and_the_cli_writes_index_then_spec(tmp_path, capsys):
    root = export(tmp_path)
    m = tmp_path / "mapping.json"
    m.write_text(json.dumps(MAPPING))
    assert sdlc.main(["boards", "index", str(root), "--out", str(tmp_path / "idx.json"), "--mapping", str(m)]) == 0
    assert "indexed 1 boards" in capsys.readouterr().out  # only the mapped board
    assert sdlc.main(["boards", "rows", str(m), "--index", str(tmp_path / "idx.json"), "--url", "http://x", "--out", str(tmp_path / "s.json")]) == 0
    assert "2 rows (" in capsys.readouterr().out and "--expected-rows 2" in capsys.readouterr().out + "--expected-rows 2"
    spec = json.loads((tmp_path / "s.json").read_text())
    assert spec["target"] == {"kind": "web", "url": "http://x"} and len(spec["rows"]) == 2 and spec["unsupported"] == []
    out = board.extract({"kind": "canvas", "root": str(root), "file": "checkout.dc.html", "route": "/checkout.html", "themes": ["dark"]})
    assert [r["id"] for r in out["rows"]] == ["checkout.dc.html/dark"]


@needs_browser
def test_a_mapping_that_names_no_board_at_this_viewport_indexes_nothing(tmp_path):
    root = export(tmp_path)
    assert board.index_export(root, only=[])["boards"] == {}


def test_browser_unavailable_is_an_environment_problem_not_a_verdict(tmp_path, capsys):
    assert sdlc.main(["boards", "index", str(tmp_path), "--executable", "/nonexistent/chrome"]) == 127
    assert "env: browser unavailable" in capsys.readouterr().out
    out = board.extract({"kind": "canvas", "root": str(tmp_path), "file": "a.dc.html", "route": "/", "executable": "/nonexistent/chrome"})
    assert out["rows"] == [] and "browser unavailable" in out["unsupported"][0]["reason"]


def test_no_baseline_or_image_approval_exists_in_the_canvas_path():
    src = (HERE / "board.py").read_text()
    assert "baseline" not in src.lower().replace("no baselines", "") and "approve(" not in src and "image approval" not in src.replace("no image approval", "")


# ---- 3 frames --------------------------------------------------------------------------------------------------------

def framed(**frame):
    return {"boards": [{"board": "frames.dc.html", "route": "/checkout.html", "entry": "F1", "theme": "light", "frame": frame}]}


@needs_browser
def test_the_index_records_frames_per_board_and_the_nodes_inside_each(idx):
    light = idx["boards"]["frames.dc.html"]["light"]
    imports = [f for f in light["frames"] if f["kind"] == "import"]
    assert [f["attrs"].get("tone") for f in imports] == ["a", "a", "b"] and imports[0]["attrs"]["dlg"] == "x" and "dlg" not in imports[1]["attrs"]
    assert all(f["known"] and f["attrs"]["name"] == "Card" for f in imports)  # attributes come from the source tags, paired in order
    assert "Tone b" in imports[2]["captions"]
    assert sorted(len(n["frames"]) for n in light["nodes"]) == [1] * len(light["nodes"])  # every node sits in exactly one frame
    cells = [f for f in idx["boards"]["cells.dc.html"]["light"]["frames"] if f["kind"] == "container"]
    assert [f["selector"] for f in cells] == [".cell", ".cell"] and "Empty" in cells[0]["captions"] and "Full" in cells[1]["captions"]


@needs_browser
def test_attrs_select_by_exact_subset_and_null_means_the_attribute_is_absent(idx):
    def only(**frame):
        out = board.canvas_rows(idx, framed(**frame))["rows"]
        return out[0]["nodes"], out[0]["unmeasurable_nodes"]
    nodes, _ = only(attrs={"tone": "b"})
    assert {n["n"] for n in nodes} == {"button:Save", "text:Tone b"}
    assert only(attrs={"tone": "a", "dlg": None})[0] and only(attrs={"tone": "a", "dlg": "x"})[0]  # exactly one of the two tone=a frames each
    with pytest.raises(ValueError, match=r"entry F1: frame .* matches 2 frames"):  # without the absent-attribute rule: 2 siblings
        board.canvas_rows(idx, framed(attrs={"tone": "a"}))
    with pytest.raises(ValueError, match=r"entry F1: .* matches 0 frames"):
        board.canvas_rows(idx, framed(attrs={"tone": "z"}))


@needs_browser
def test_a_caption_selects_the_closest_dc_import_else_the_closest_container(idx, tmp_path):
    assert {n["n"] for n in board.canvas_rows(idx, framed(caption="Tone b"))["rows"][0]["nodes"]} == {"button:Save", "text:Tone b"}
    with pytest.raises(ValueError, match="entry F1: .* matches 2 frames"):
        board.canvas_rows(idx, framed(caption="Tone a"))  # two <dc-import> frames carry it
    cells = {"boards": [{"board": "cells.dc.html", "route": "/checkout.html", "entry": "C1", "theme": "light", "frame": {"caption": "Full"}}]}
    row = board.canvas_rows(idx, cells)["rows"][0]
    assert {n["n"] for n in row["nodes"]} == {"text:Full", "button:Pay", "button:Other"} and row["unmeasurable_nodes"] == 0
    empty = board.canvas_rows(idx, {"boards": [{**cells["boards"][0], "frame": {"caption": "Empty"}}]})["rows"][0]
    assert {n["n"] for n in empty["nodes"]} == {"text:Empty", "button:Pay"}  # measured inside the cell only
    with pytest.raises(ValueError, match="entry C1: .* matches 0 frames"):
        board.canvas_rows(idx, {"boards": [{**cells["boards"][0], "frame": {"caption": "Nothing"}}]})
    with pytest.raises(ValueError, match="built without container"):
        board.canvas_rows(idx, {"boards": [{**cells["boards"][0], "frame": {"caption": "Full", "container": ".other"}}]})


@needs_browser
def test_a_framed_row_is_compared_with_the_app(idx, tmp_path):
    cells = {"boards": [{"board": "cells.dc.html", "route": "/checkout.html", "entry": "C1", "theme": "light", "frame": {"caption": "Full"}}]}
    rows = board.canvas_rows(idx, cells)["rows"]
    html = '<span class="lbl">Full</span><button class="pay" style="padding:0 20px">Pay</button><button>Other</button><style>%s</style>'
    with board.serve(app(tmp_path, html)) as url:
        assert check(web_spec(url, rows), tmp_path)[0] == 0
    with board.serve(app(tmp_path / "x", html.replace("0 20px", "0 25px"))) as url:
        code, out = check(web_spec(url, rows), tmp_path)
    assert code == 1 and "button:Pay padding-left: board 20px, app 25px" in out


@needs_browser
def test_boards_index_with_a_mapping_names_the_entry_whose_frame_matches_nothing_or_many(tmp_path, capsys):
    root = export(tmp_path)
    m = tmp_path / "m.json"
    m.write_text(json.dumps(framed(caption="Tone a")))
    assert sdlc.main(["boards", "index", str(root), "--out", str(tmp_path / "i.json"), "--mapping", str(m)]) == 2
    assert "entry F1: frame" in capsys.readouterr().out
    assert sdlc.main(["boards", "rows", str(m), "--index", str(tmp_path / "i.json"), "--out", str(tmp_path / "s.json")]) == 2
    assert "matches 2 frames" in capsys.readouterr().out


@needs_browser
def test_attrs_are_refused_where_the_source_and_the_render_list_different_imports(idx):
    mixed = {"boards": [{"board": "mixed.dc.html", "route": "/checkout.html", "entry": "M1", "theme": "light", "frame": {"attrs": {"tone": "b"}}}]}
    assert not any(f["known"] for f in idx["boards"]["mixed.dc.html"]["light"]["frames"] if f["kind"] == "import")
    with pytest.raises(ValueError, match=r"entry M1: .* matches 0 frames .*cannot be paired"):
        board.canvas_rows(idx, mixed)
    assert board.canvas_rows(idx, {"boards": [{**mixed["boards"][0], "frame": {"caption": "Tone b"}}]})["rows"]  # a caption still selects it


def test_frame_and_container_shapes_are_validated():
    for bad in ({"attrs": {}}, {"attrs": {"a": 1}}, {"caption": ""}, {"attrs": {"a": "b"}, "caption": "x"}, {"caption": "x", "container": "a{"},
                {"attrs": {"a": "b"}, "container": ".c"}, {"other": 1}):
        with pytest.raises(ValueError, match="entry E: frame must be"):
            board.validate_mapping({"boards": [{"board": "a", "route": "/", "entry": "E", "frame": bad}]})
    board.validate_mapping({"boards": [{"board": "a", "route": "/", "frame": {"attrs": {"a": None, "b": "c"}}},
                                       {"board": "a", "route": "/", "frame": {"caption": "x", "container": ".cell > .x"}}]})


# ---- 2 surfaces ------------------------------------------------------------------------------------------------------

def test_surface_shapes_and_the_paths_and_env_they_may_name(tmp_path):
    good_ext = {"kind": "chrome-extension", "dist": "dist/ext", "page": "popup.html?tab=1"}
    good_app = {"kind": "electron", "app": "out/main.js", "env": {"APP_THEME": "dark"}, "args": ["--lang=en"]}
    allow = {"args": ["--lang"], "env": ["APP_THEME"]}
    assert board.validate_surface(good_ext) and board.validate_surface(good_app, allow)
    for bad in ({**good_ext, "dist": "../x"}, {**good_ext, "dist": "/abs"}, {**good_ext, "page": "https://evil/x"}, {**good_ext, "page": "../a.html"},
                {**good_ext, "page": "a b.html"}, {**good_app, "app": "../main.js"}, {**good_app, "app": "/usr/bin/x"},
                *({**good_app, "env": {k: "x"}} for k in ("PATH", "HOME", "NODE_OPTIONS", "NODE_PATH", "ELECTRON_RUN_AS_NODE", "ELECTRON_ENABLE_LOGGING",
                                                          "BASH_ENV", "SDLC_HOME", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "lower", "A-B")),
                *({**good_app, "args": [a]} for a in ("--user-data-dir=/tmp/x", "--renderer-cmd-prefix=sh", "--inspect", "--js-flags=--x", "--load-extension=/x",
                                                      "--require", "bare", "-x", "--UPPER", "--a b")),
                {**good_app, "args": ["--require=/x.js"]}, {**good_app, "args": ["-r", "x"]}, {"kind": "web"}, {**good_app, "env": {"A": 1}}):
        with pytest.raises(ValueError):
            board.validate_surface(bad)
    with pytest.raises(ValueError, match="route or a surface, not both"):
        board.validate_mapping({"boards": [{"board": "a", "route": "/", "surface": good_ext}]})
    (tmp_path / "real").mkdir()
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "link").symlink_to(tmp_path / "real")
    with pytest.raises(ValueError, match="outside the repo"):  # a symlink out of the repo is refused when the check resolves it
        board._inside(tmp_path / "repo", "link")


def test_a_row_with_a_surface_outside_the_repo_is_refused_before_any_browser_starts(tmp_path):
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "dist").symlink_to(tmp_path)
    row = {**row_of(["n"]), "props": [*board.CANVAS_STYLE, *board.BOX], "theme": "light",
           "surface": {"kind": "chrome-extension", "dist": "dist", "page": "p.html"}}
    row["nodes"][0]["v"] = ["1"] * 21
    code, out = check(web_spec("http://x", [row]), tmp_path, tmp_path / "repo")
    assert code == 2 and "resolves outside the repo" in out


@needs_browser
def test_a_chrome_extension_is_loaded_alone_and_its_page_is_measured(idx, tmp_path):
    repo = tmp_path / "repo"
    ext = repo / "dist" / "ext"
    ext.mkdir(parents=True)
    (ext / "manifest.json").write_text(json.dumps({"manifest_version": 3, "name": "fake", "version": "1", "background": {"service_worker": "sw.js"}}))
    (ext / "sw.js").write_text("// nothing")
    (ext / "popup.html").write_text('<!doctype html><html><head><link rel="stylesheet" href="popup.css"></head><body><button class="pay">Pay</button></body></html>')
    (ext / "popup.css").write_text(BLOB)
    m = {"boards": [{"board": "popup.dc.html", "entry": "X1", "theme": "light", "surface": {"kind": "chrome-extension", "dist": "dist/ext", "page": "popup.html?tab=1"}}]}
    rows = board.canvas_rows(idx, m)["rows"]
    assert rows[0]["surface"]["page"] == "popup.html?tab=1" and rows[0]["route"] is None
    code, out = check({"rows": rows}, tmp_path, repo)
    assert code == 0, out
    (ext / "popup.css").write_text(BLOB.replace("padding:0 16px", "padding:0 9px"))
    code, out = check({"rows": rows}, tmp_path, repo)
    assert code == 1 and "button:Pay padding-left: board 16px, app 9px" in out


class _Win:
    def __init__(self):
        self.waited = []

    def wait_for_load_state(self, s):
        self.waited.append(s)


class _Playwright:
    """Records the Electron launch without Electron: what it was given, and that it asked for the first window and its load."""
    def __init__(self):
        self.calls, self.win = [], _Win()
        self._electron = self

    def launch(self, **kw):
        self.calls.append(kw)
        win = self.win
        return type("App", (), {"first_window": lambda s: win, "close": lambda s: None})()


def test_electron_reuses_the_hidden_launch_waits_for_the_first_window_and_its_load(tmp_path):
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "main.js").write_text("")
    p = _Playwright()
    page, close, nav = board._launch(p, {"kind": "electron", "app": "out/main.js", "env": {"APP_X": "1"}, "args": ["--lang=en"]}, None, tmp_path,
                                     {"args": ["--lang"], "env": ["APP_X"]})
    kw = p.calls[0]
    assert page is p.win and p.win.waited == ["load"] and nav is None
    assert kw["args"][0] == "--require" and "--disable-renderer-backgrounding" in kw["args"] and kw["args"][-2] == str((tmp_path / "out" / "main.js").resolve())
    assert kw["args"][-1] == "--lang=en" and kw["env"]["SDLC_HIDDEN"] == "1" and kw["env"]["APP_X"] == "1" and kw["cwd"] == str(tmp_path)
    with pytest.raises(ValueError, match="inside the repo"):
        board._launch(p, {"kind": "electron", "app": "../../x.js"}, None, tmp_path, None)


# ---- 4 contract rows: kind board, no hard-coded runner path -----------------------------------------------------------

def board_row(**kw):
    return tk.chk("b", "app", None, kind="board", pins={"specs/web.json": "0" * 64}, count=False,
                  board={"spec": "specs/web.json", "expected_rows": 12, **kw})


def test_a_board_row_names_no_runner_path_and_the_runner_runs_its_own_board_py():
    row = board_row()
    del row["runner"]
    contract.validate_contract({"checks": [row]})
    argv = contract.runner_of(row)
    assert Path(argv[1]) == HERE / "board.py" and argv[2:] == ["check", "specs/web.json", "--expected-rows", "12"]
    assert verify.count_rx(row) == r"Ran (\d+) checks"
    contract.validate_contract({"checks": [{**row, "board": {**row["board"], "start": ["npm", "run", "preview"], "ready_url": "http://127.0.0.1:4173/", "ready_timeout": 90}}]})
    for bad, why in (({"spec": "specs/web.json"}, "expected_rows"), ({"spec": "other.json", "expected_rows": 1}, "listed in pins"),
                     ({"spec": "specs/web.json", "expected_rows": 0}, "expected_rows"),
                     ({"spec": "specs/web.json", "expected_rows": 1, "start": ["x"]}, "needs board.ready_url"),
                     ({"spec": "specs/web.json", "expected_rows": 1, "start": ["x"], "ready_url": "http://evil.example/"}, "127.0.0.1 or http://localhost"),
                     ({"spec": "specs/web.json", "expected_rows": 1, "extra": 1}, "only")):
        with pytest.raises(SdlcError, match=why):
            contract.validate_contract({"checks": [{**row, "board": bad}]})


def test_the_web_app_of_a_board_row_is_started_awaited_and_stopped_around_the_check(tmp_path):
    repo = tk.make_repo(tmp_path / "r", "app", {"index.html": "<p>up</p>"})
    rid = tk.new_run(tmp_path / "home", repo, [])
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url = f"http://127.0.0.1:{port}/"
    row = board_row(start=[sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], ready_url=url, ready_timeout=20)
    probe = [sys.executable, "-c", f"import urllib.request; print(urllib.request.urlopen('{url}').read()[:12].decode()); print('Ran 1 checks')"]
    job = verify.run_checked(rid, row, probe, repo, None)
    assert job.exit == 0 and "up" in job.out and "Ran 1 checks" in job.out
    with pytest.raises(OSError), socket.create_connection(("127.0.0.1", port), timeout=1):  # stopped afterwards
        pass
    late = board_row(start=[sys.executable, "-c", "import time; time.sleep(30)"], ready_url=url, ready_timeout=1)
    job = verify.run_checked(rid, late, probe, repo, None)
    assert job.exit == 127 and "did not answer" in job.out


def test_a_board_build_runs_first_and_a_failed_build_fails_the_row_unmeasured(tmp_path):
    repo = tk.make_repo(tmp_path / "r", "app", {"index.html": "x"})
    rid = tk.new_run(tmp_path / "home", repo, [])
    marker = repo / "built.txt"
    ok = board_row(build=[sys.executable, "-c", f"open({str(marker)!r}, 'w').write('1')"])
    measured = [sys.executable, "-c", f"import os; print('Ran 1 checks' if os.path.exists({str(marker)!r}) else 'NOT BUILT')"]
    job = verify.run_checked(rid, ok, measured, repo, None)
    assert job.exit == 0 and "Ran 1 checks" in job.out  # the build ran before the measuring
    marker.unlink()
    bad = board_row(build=[sys.executable, "-c", "import sys; print('boom'); sys.exit(3)"])
    job = verify.run_checked(rid, bad, measured, repo, None)
    assert job.exit == 3 and "NOT BUILT" not in job.out and not marker.exists()  # never measured
    assert verify.classify(bad, job)[:2] == ("FAIL", "BUILD FAILED (exit 3): the row was not measured")
    contract.validate_contract({"checks": [{**bad, "runner": None}]} if False else {"checks": [{k: v for k, v in bad.items() if k != "runner"}]})
    with pytest.raises(SdlcError, match="board.build is an argv list"):
        contract.validate_contract({"checks": [board_row(build="make")]})


def test_board_rows_use_the_check_env_allowlist_for_build_start_and_check_and_the_screen_shows_it(tmp_path, monkeypatch):
    monkeypatch.setenv("SDLC_SECRET_A", "alpha")
    monkeypatch.setenv("SDLC_SECRET_B", "beta")
    repo = tk.make_repo(tmp_path / "r", "app", {"index.html": "x"})
    rid = tk.new_run(tmp_path / "home", repo, [])
    show = [sys.executable, "-c", "import os; print(os.environ.get('SDLC_SECRET_A'), os.environ.get('SDLC_SECRET_B'), 'Ran 1 checks')"]
    row = board_row(build=show)
    row["env"] = ["SDLC_SECRET_A"]  # the same `env` field the E2E rows use
    job = verify.run_checked(rid, row, show, repo, None)
    assert job.exit == 0 and "alpha None Ran 1 checks" in job.out  # only the allowlisted variable reaches the build and the check
    row.pop("runner", None)
    d = store.run_dir(rid)
    store.write_json(d / "contract.json", {"checks": [{**row, "runner": ["true"]}]})
    import discover
    text = discover.screen(rid).read_text()
    assert "| Env passed |" in text and "| SDLC_SECRET_A |" in text


POLL = """<!doctype html><html><head><link rel="stylesheet" href="/_blob/theme.css"></head><body><button class="pay">Pay</button>
<script>setInterval(() => fetch('/_blob/theme.css?' + Math.random()), 40)</script></body></html>"""


@needs_browser
def test_ready_replaces_the_networkidle_wait_and_a_wait_that_times_out_still_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(board, "NAV_TIMEOUT_MS", 2500)
    root = export(tmp_path, poll=POLL)
    ix = board.index_export(root, only=["poll.dc.html"])  # the default stays networkidle: a page that never idles times out
    assert "Timeout" in ix["boards"]["poll.dc.html"]["light"]["error"]
    for ready in ({"selector": "button.pay"}, {"load": "domcontentloaded"}, {"load": "load"}):
        ok = board.index_export(root, only=["poll.dc.html"], ready={"poll.dc.html": ready})["boards"]["poll.dc.html"]["light"]
        assert ok["error"] == "" and any(n["name"] == "Pay" for n in ok["nodes"]), ready
    never = board.index_export(root, only=["poll.dc.html"], ready={"poll.dc.html": {"selector": ".nope"}})
    assert "Timeout" in never["boards"]["poll.dc.html"]["light"]["error"]  # not skipped: the board yields no rows
    m = {"boards": [{"board": "poll.dc.html", "route": "/p.html", "ready": {"selector": "button.pay"}}]}
    ok = board.index_export(root, only=["poll.dc.html"], ready={"poll.dc.html": m["boards"][0]["ready"]})
    rows = board.canvas_rows(ok, m)["rows"]
    assert rows[0]["ready"] == {"selector": "button.pay"}
    page = tmp_path / "app"
    page.mkdir()
    (page / "p.html").write_text(POLL)
    (page / "_blob").mkdir()
    (page / "_blob" / "theme.css").write_text(BLOB)
    with board.serve(page) as url:
        res = board.measure_rows({"target": {"url": url}}, rows, None, tmp_path)
        assert res[0]["mismatches"] == [] and res[0]["matched"] > 0  # the app page never idles either: it is measured on `ready`
        res = board.measure_rows({"target": {"url": url}}, [{**r, "ready": {"selector": ".nope"}} for r in rows], None, tmp_path)
    assert "Timeout" in res[0]["error"]
    for bad in ({"selector": ""}, {"load": "idle"}, {"selector": "a", "load": "load"}, "x"):
        with pytest.raises(ValueError, match="entry E: ready must be"):
            board.validate_mapping({"boards": [{"board": "a", "route": "/", "entry": "E", "ready": bad}]})


# ---- review round -----------------------------------------------------------------------------------------------------

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def a_board_run(tmp_path, **board_kw):
    repo = tk.make_repo(tmp_path / "r", "app", {"index.html": "x", "package.json": "{}", "scripts/build.sh": "echo"})
    row = board_row(**board_kw)
    row["repo"] = "app"
    return repo, row, tk.new_run(tmp_path / "home", repo, [])


def test_a_board_row_can_be_drafted_and_its_tools_come_from_build_and_start(tmp_path, monkeypatch):
    import discover
    monkeypatch.setenv("SDLC_HOME", str(tmp_path / "home"))
    repo = tk.make_repo(tmp_path, "web", {"README.md": "x"})
    rid = discover.plan([str(repo)], "t")
    spec = tmp_path / "web.json"
    spec.write_text(json.dumps({"target": {"kind": "web", "url": "http://127.0.0.1:4173"}, "rows": [
        {"id": "r", "props": [*board.CANVAS_STYLE, *board.BOX], "min_match": 0.95, "tol": {"width": 3}, "nodes": [{"n": "a", "l": {}, "v": []}] * 4,
         "unmeasurable_nodes": 1}]}))
    c = tmp_path / "c.json"
    row = {"id": "b", "repo": "web", "milestone": None, "kind": "board", "expect": {"kind": "pass"}, "pins": ["specs/web.json"], "env": ["API_URL"],
           "board": {"spec": "specs/web.json", "expected_rows": 1, "build": ["no-such-tool-xyz", "build"], "start": ["npm", "run", "preview"],
                     "ready_url": "http://127.0.0.1:4173/"}}
    c.write_text(json.dumps({"checks": [row], "limits": {"max_dispatches": 5}, "waive_full": ["web"]}))
    blockers = discover.draft(rid, None, str(c), None, [f"web:specs/web.json={spec}"], [])  # used to raise KeyError: 'runner'
    assert any("needs no-such-tool-xyz" in b for b in blockers)
    text = discover.screen(rid).read_text()
    assert "board check specs/web.json (1 rows); build: no-such-tool-xyz build" in text and "app at `http://127.0.0.1:4173/`" in text
    assert "| API_URL |" in text and "## Board checks" in text
    assert "1 rows (expected 1), 4 nodes, min_match 0.95, 21 properties, tolerance overrides: {\"width\": 3}, unmeasurable nodes 1" in text


def test_a_stale_server_on_ready_url_is_refused_and_an_app_that_dies_is_not_measured(tmp_path):
    repo, _, rid = a_board_run(tmp_path)
    probe = [sys.executable, "-c", "print('Ran 1 checks')"]
    with board.serve(tmp_path) as stale:  # a decoy already answering: the probe used `start = sleep 2; exit 1` and the old app passed
        row = board_row(start=["sh", "-c", "sleep 2; exit 1"], ready_url=stale + "/", ready_timeout=5)
        job = verify.run_checked(rid, row, probe, repo, None)
        assert job.exit == 127 and "already answers" in job.out and verify.classify(row, job)[0] == "BLOCKED"
    port = free_port()
    url = f"http://127.0.0.1:{port}/"
    dies = board_row(start=["sh", "-c", "exit 1"], ready_url=url, ready_timeout=5)
    job = verify.run_checked(rid, dies, probe, repo, None)
    assert job.exit == 127 and "the app exited" in job.out
    once = f"import http.server as h; h.HTTPServer(('127.0.0.1', {port}), h.SimpleHTTPRequestHandler).handle_request()"
    row = board_row(start=[sys.executable, "-c", once], ready_url=url, ready_timeout=10)  # answers once, then is gone
    job = verify.run_checked(rid, row, probe, repo, None)
    assert job.exit in (1, 127) and "the app exited" in job.out and verify.classify(row, job)[0] != "PASS"


def test_the_spec_url_must_be_the_origin_of_ready_url_and_the_runner_hands_that_origin_to_the_check(tmp_path):
    repo, _, rid = a_board_run(tmp_path)
    port = free_port()
    (repo / "specs").mkdir()
    (repo / "specs" / "web.json").write_text(json.dumps({"target": {"kind": "web", "url": "http://127.0.0.1:1"}, "rows": []}))
    row = board_row(start=[sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], ready_url=f"http://127.0.0.1:{port}/", ready_timeout=20)
    job = verify.run_checked(rid, row, [sys.executable, "-c", "print('Ran 1 checks')"], repo, None)
    assert job.exit == 127 and "is not the origin of ready_url" in job.out
    (repo / "specs" / "web.json").write_text(json.dumps({"rows": []}))  # no url of its own: the check is told the origin
    job = verify.run_checked(rid, row, [sys.executable, "-c", "import sys; print(sys.argv[-2:]); print('Ran 1 checks')"], repo, None)
    assert job.exit == 0 and f"['--url', 'http://127.0.0.1:{port}']" in job.out


@needs_browser
def test_the_check_takes_its_url_from_the_runner_flag(idx, tmp_path):
    rows = board.canvas_rows(idx, MAPPING)["rows"]
    with board.serve(app(tmp_path)) as url:
        spec = {"rows": rows}
        assert check(spec, tmp_path, None, "--url", url)[0] == 0


def test_a_row_cannot_lower_the_bar_it_is_judged_by(tmp_path, capsys):
    names = [f"n{i}" for i in range(20)]
    row = row_of(names, min_match=0.01)
    assert not board.verdict(row, board.judge(row, app_nodes(names[:1])))[0]  # 1 of 20 matched with min_match 0.01
    for bad in ({"min_match": 0.01}, {"min_match": 1.5}, {"tolerances": {"width": 99999}}, {"tolerances": {"color": 1}}, {"tolerances": {"font-size": -1}},
                {"tolerances": {"nonsense": 1}}):
        with pytest.raises(ValueError, match="entry E"):
            board.validate_mapping({"boards": [{"board": "a", "route": "/", "entry": "E", **bad}]})
    board.validate_mapping({"boards": [{"board": "a", "route": "/", "entry": "E", "min_match": 0.97, "tolerances": {"width": 4, "padding-left": 2}}]})
    assert board.tolerance("width", "100px", {"width": 99999}) == 4.0 and board.tolerance("width", "1000px", {"width": 99999}) == 20.0
    assert board.tolerance("padding-left", "8px", {"padding-left": 99999}) == 4.0
    assert board.tolerance("color", "red", {"color": 99999}) == 1.0 and not board.same("color", "rgb(0, 0, 0)", "rgb(0, 0, 5)", {"color": 99999})
    assert not board.same("width", "100px", "300px", {"width": 99999})


def test_a_spec_that_lists_no_or_odd_properties_is_refused_before_measuring(tmp_path, capsys):
    good = {"id": "r", "theme": "light", "route": "/x", "props": [*board.CANVAS_STYLE, *board.BOX], "nodes": [{"n": "a", "l": {"text": "a"}, "v": ["1"] * 21}]}
    assert board.row_problem(good) == ""
    for bad in ({**good, "props": []}, {**good, "props": ["width"]}, {**good, "props": [*good["props"], "bogus"]}, {**good, "tol": {"color": 1}},
                {**good, "tol": {"width": 99999}}, {**good, "nodes": [{"n": "a", "l": {"text": "a"}, "v": []}]}):
        assert board.row_problem(bad), bad
        f = tmp_path / "s.json"
        f.write_text(json.dumps(web_spec("http://x", [bad])))
        assert board.main(["check", str(f)]) == 2 and "board: row r" in capsys.readouterr().out


def test_the_files_a_board_build_and_start_execute_are_protected_like_a_checks_runner(tmp_path):
    repo, row, rid = a_board_run(tmp_path, build=["npm", "run", "build"], start=["sh", "scripts/build.sh"], ready_url="http://127.0.0.1:4173/")
    store.write_json(store.run_dir(rid) / "contract.json", {"checks": [row], "limits": {"max_dispatches": 5}})
    base = tk.git(repo, "rev-parse", "HEAD")
    pkg = tk.commit_file(repo, "package.json", '{"scripts": {"build": "curl evil"}}')
    sh = tk.commit_file(repo, "scripts/build.sh", "curl evil")
    assert any("protected path package.json" in b for b in verify.guard_diff(rid, "app", base, pkg))
    assert any("protected path scripts/build.sh" in b for b in verify.guard_diff(rid, "app", base, sh))
    assert verify._argv_files(str(repo), base, ["pnpm", "run", "x", "scripts/build.sh", "nope.sh"]) == ["package.json", "scripts/build.sh"]


def test_sdlc_stop_kills_the_started_app_through_its_pidfile_and_wait_ready_polls_for_it(tmp_path):
    import os
    import threading
    import time
    repo, _, rid = a_board_run(tmp_path)
    url = f"http://127.0.0.1:{free_port()}/"
    row = board_row(start=["sleep", "60"], ready_url=url, ready_timeout=60)
    seen = {}

    def stopper():
        pidf = store.run_dir(rid) / "jobs" / f"app-{row['id']}-app.pid"
        for _ in range(100):
            if pidf.exists():
                seen["pid"] = json.loads(pidf.read_text())["pid"]
                store.stop_marker(rid).write_text("stop")
                return
            time.sleep(0.1)
    t = threading.Thread(target=stopper)
    t.start()
    job = verify.run_checked(rid, row, [sys.executable, "-c", "print('Ran 1 checks')"], repo, None)
    t.join()
    assert job.killed == "stop" and verify.classify(row, job)[0] == "BLOCKED"
    with pytest.raises(ProcessLookupError):
        os.kill(seen["pid"], 0)  # the app is gone, and so is its pidfile
    assert not (store.run_dir(rid) / "jobs" / f"app-{row['id']}-app.pid").exists()
    timeout = board_row(start=["sleep", "60"], ready_url=url, ready_timeout=1)
    store.stop_marker(rid).unlink()
    assert verify.run_checked(rid, timeout, [sys.executable, "-c", "x"], repo, None).exit == 127


# ---- security review -------------------------------------------------------------------------------------------------------

ALLOW = {"args": ["--theme", "--page"], "env": ["APP_THEME"]}


def electron(**kw):
    return {"kind": "electron", "app": "out/main.js", **kw}


def test_surface_args_and_env_need_the_contract_rows_allowlist_and_launcher_switches_stay_denied():
    ok = electron(args=["--theme=dark", "--page=a/b.html", "--theme"], env={"APP_THEME": "dark"})
    assert board.validate_surface(ok, ALLOW, enforce=True)
    for bad in (electron(args=["--gpu-launcher=sh"]), electron(args=["--utility-cmd-prefix=x"]), electron(args=["--browser-subprocess-path=/x"]),
                electron(args=["--other"]), electron(args=["--theme=/etc/passwd"]), electron(args=["--theme=../x"]), electron(args=["--theme=a;rm"]),
                electron(args=["--theme=$(id)"]), electron(args=["--theme=~/x"]), electron(args=["--theme=a b"]), electron(env={"OTHER": "1"})):
        with pytest.raises(ValueError):
            board.validate_surface(bad, ALLOW, enforce=True)
    with pytest.raises(ValueError, match="not in the contract row's surface_allow.args"):
        board.validate_surface(electron(args=["--theme=dark"]), None, enforce=True)  # no allowlist: nothing may be passed
    assert board.validate_surface(electron(), None, enforce=True)
    for bad in ({"args": ["--gpu-launcher"]}, {"args": ["--user-data-dir"]}, {"args": ["theme"]}, {"env": ["NODE_OPTIONS"]}, {"env": ["PATH"]},
                {"env": ["lower"]}, {"other": []}, {"args": "x"}):
        with pytest.raises(ValueError):
            board.validate_allow(bad)
    row = board_row(surface_allow=ALLOW)
    row.pop("runner", None)
    contract.validate_contract({"checks": [row]})
    assert contract.runner_of(row)[-2:] == ["--surface-allow", json.dumps(ALLOW, sort_keys=True)]
    assert "--surface-allow" not in contract.runner_of(board_row())
    with pytest.raises(SdlcError, match="surface_allow must be"):
        contract.validate_contract({"checks": [board_row(surface_allow={"args": ["--gpu-launcher"]})]})


def test_a_spec_or_mapping_cannot_widen_what_the_contract_allows(tmp_path, capsys):
    row = {**row_of(["n"]), "props": [*board.CANVAS_STYLE, *board.BOX], "theme": "light", "surface": electron(args=["--theme=dark"]),
           "allow": ALLOW}  # an `allow` of its own in the row or the spec is not read
    row["nodes"][0]["v"] = ["1"] * 21
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"rows": [row], "surface_allow": ALLOW, "target": {}}))
    assert board.main(["check", str(f)]) == 2 and "not in the contract row's surface_allow.args" in capsys.readouterr().out
    capsys.readouterr()
    assert board.main(["check", str(f), "--surface-allow", json.dumps({"args": ["--gpu-launcher"]})]) == 2
    assert "surface_allow must be" in capsys.readouterr().out  # the flag is validated too


def test_the_runner_picks_the_port_and_passes_it_as_port_and_in_start_and_ready_url(tmp_path):
    repo, _, rid = a_board_run(tmp_path)
    row = board_row(start=[sys.executable, "-m", "http.server", "{port}", "--bind", "127.0.0.1"], ready_url="http://127.0.0.1:{port}/", ready_timeout=20)
    row.pop("runner", None)
    contract.validate_contract({"checks": [row]})
    probe = [sys.executable, "-c", "import os, sys; print(os.environ['PORT'], sys.argv[-1]); print('Ran 1 checks')"]
    job = verify.run_checked(rid, row, probe, repo, None)
    port = job.out.split()[0]
    assert job.exit == 0 and port.isdigit() and f"{port} http://127.0.0.1:{port}" in job.out


def test_a_server_that_answers_but_is_not_the_started_app_is_refused(tmp_path):
    import http.server
    import threading
    import time
    repo, _, rid = a_board_run(tmp_path)
    port = free_port()
    started = []

    def late_decoy():  # appears after the runner's "already answers" check, as a race would
        time.sleep(1.0)
        srv = http.server.HTTPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler)
        started.append(srv)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    threading.Thread(target=late_decoy).start()
    row = board_row(start=["sleep", "30"], ready_url=f"http://127.0.0.1:{port}/", ready_timeout=10)
    job = verify.run_checked(rid, row, [sys.executable, "-c", "print('Ran 1 checks')"], repo, None)
    assert job.exit == 127 and "not owned by the app this run started" in job.out and verify.classify(row, job)[0] == "BLOCKED"
    started[0].shutdown()
    started[0].server_close()
    with socket.socket() as s:  # listener_pgids names the owner of a listening socket
        s.bind(("127.0.0.1", 0))
        s.listen()
        import os
        mine = verify.listener_pgids(s.getsockname()[1])
        assert mine == {os.getpgid(0)} and os.getpgid(0) != 1


def test_without_lsof_the_row_is_blocked_env_and_never_passes(tmp_path, monkeypatch):
    repo, _, rid = a_board_run(tmp_path)
    port = free_port()
    row = board_row(start=[sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], ready_url=f"http://127.0.0.1:{port}/", ready_timeout=20)
    real = verify.shutil.which
    monkeypatch.setattr(verify.shutil, "which", lambda n, *a, **k: None if n == "lsof" else real(n, *a, **k))
    job = verify.run_checked(rid, row, [sys.executable, "-c", "print('Ran 1 checks')"], repo, None)
    v, why, _ = verify.classify(row, job)
    assert v == "BLOCKED" and "lsof is not installed" in why
    with pytest.raises(OSError), socket.create_connection(("127.0.0.1", port), timeout=1):  # and the app was stopped
        pass


def test_a_check_id_is_one_safe_name_and_the_job_label_is_one_file_name(tmp_path):
    for bad in ("../../x", "a b", "a/../b", "", "/abs", "x" * 81, "a\nb", ".hidden"):
        with pytest.raises(SdlcError, match="check id"):
            contract.validate_contract({"checks": [tk.chk(bad, "app", ["true"])]})
    contract.validate_contract({"checks": [tk.chk("full:web", "app", ["true"]), tk.chk("ui/checkout-1.a", "app", ["true"])]})
    assert verify.safe_label("app", "../../x") == "app-x" and "/" not in verify.safe_label("a/b", "c d")
    repo, _, rid = a_board_run(tmp_path)
    port = free_port()
    row = board_row(start=["sleep", "60"], ready_url=f"http://127.0.0.1:{port}/", ready_timeout=1)
    row["id"] = "../../../escape"  # a hand-edited contract that skipped validation still cannot write outside jobs/
    verify.run_checked(rid, row, [sys.executable, "-c", "x"], repo, None)
    assert not (tmp_path / "escape-app.pid").exists() and not any(p.name.startswith("escape") for p in tmp_path.rglob("*escape*") if p.is_file())


def test_every_path_that_can_launch_a_surface_enforces_the_contract_allowlist(tmp_path, capsys):
    unlisted = electron(args=["--theme=dark"], env={"APP_THEME": "dark"})
    with pytest.raises(ValueError, match="surface_allow"):
        board.validate_surface(unlisted)  # enforcement is the default: a new caller cannot forget it
    assert board.validate_surface(unlisted, ALLOW)
    # _launch (used by measure and by the aggregate path), with no allowlist or one that does not list the arg
    for allow in (None, {"args": ["--page"], "env": ["APP_THEME"]}, {"args": ["--theme"], "env": []}):
        with pytest.raises(ValueError, match="surface_allow"):
            board._launch(_Playwright(), unlisted, None, tmp_path, allow)
    # the mapping: `boards rows` and `boards index --mapping` refuse an entry whose surface the contract row does not allow
    m = {"boards": [{"board": "a.dc.html", "entry": "E", "surface": unlisted, "theme": "light"}]}
    with pytest.raises(ValueError, match="entry E: surface.* not in the contract row's surface_allow"):
        board.validate_mapping(m)
    board.validate_mapping(m, ALLOW)
    with pytest.raises(ValueError, match="entry E"):
        board.canvas_rows({"boards": {}, "viewport": {"width": 1, "height": 1}, "themes": ["light"]}, m)
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps(m))
    assert sdlc.main(["boards", "rows", str(mf), "--index", str(mf), "--out", str(tmp_path / "s.json")]) == 2
    assert "surface_allow" in capsys.readouterr().out
    # a non-aggregate (per-node) row: the check refuses the unlisted arg and env before any launch
    spec = {"target": unlisted, "rows": [{"id": "r", "locator": {"css": "body"}, "prop": "width", "expected": "1px", "tolerance_px": 1}]}
    f = tmp_path / "spec.json"
    f.write_text(json.dumps(spec))
    assert board.main(["check", str(f)]) == 2 and "not in the contract row's surface_allow" in capsys.readouterr().out
    assert board.main(["check", str(f), "--surface-allow", json.dumps({"args": ["--theme"], "env": ["OTHER"]})]) == 2
    assert "surface.env APP_THEME is not in the contract row's surface_allow.env" in capsys.readouterr().out


# ---- ordinal locators for repeated nodes -----------------------------------------------------------------------------------
# (`position` is the x and y geometry option and does not do this: it measures where a node is, not which of several it is.)

LIST_MAP = {"boards": [{"board": "list.dc.html", "route": "/list.html", "entry": "L1", "theme": "light"}]}


def list_app(tmp_path, widths=(100, 110, 120, 130, 140)):
    root = tmp_path / "listapp"
    root.mkdir(parents=True)
    rows = "".join(f'<li style="width:{w}px">Row</li>' for w in widths)
    (root / "list.html").write_text(f'<!doctype html><html><head><style>{BLOB}</style></head><body><main><h2>Members</h2><ul>{rows}</ul></main></body></html>')
    return root


@needs_browser
def test_a_list_of_five_identical_rows_matches_five_of_five_and_a_reorder_or_a_dropped_row_fails(idx, tmp_path):
    row = board.canvas_rows(idx, LIST_MAP)["rows"][0]
    rows_ = [n for n in row["nodes"] if n["n"].startswith("text:Row")]
    assert [(n["i"], n["g"]) for n in rows_] == [(i, 5) for i in range(5)] and rows_[0]["a"] == {"role": "main"} and row["unmeasurable_nodes"] == 0
    assert rows_[2]["n"] == "text:Row[2] in main"  # the report shows the anchored locator

    def run(widths):
        with board.serve(list_app(tmp_path / str(len(widths)) / "-".join(map(str, widths)), widths)) as url:
            return check({"target": {"kind": "web", "url": url}, "rows": [{**row, "id": "L1/light", "route": "/list.html"}]}, tmp_path)
    code, out = run((100, 110, 120, 130, 140))
    assert code == 0 and "PASS L1/light: 7/7 measurable nodes matched (100.0%), 0 mismatches, 0 unmeasurable" in out, out  # same order: 5 of 5 rows
    code, out = run((100, 120, 110, 130, 140))  # reordered: the 2nd and 3rd rows swap their widths
    assert code == 1 and "MISMATCH L1/light text:Row[1] in main width: board 110px, app 120px" in out
    code, out = run((100, 110, 120, 130))  # one row dropped
    assert code == 1 and "MISMATCH L1/light text:Row[0] in main occurrences: board 5, app 4" in out and "not found once in the app: text:Row[4] in main" in out
    code, out = run((100, 110, 120, 130, 140, 150))  # one row added
    assert code == 1 and "occurrences: board 5, app 6" in out


def idx_node(role, name, parent=-1, **loc):
    return {"role": role, "name": name, "locator": loc or ({"role": role, "name": name} if name else {"role": role}), "parent": parent, "frames": [],
            "tag": "x", "style": {}, "box": {"width": 10, "height": 5, "x": 0, "y": 0}}


def test_anchors_are_the_nearest_unique_ancestor_else_the_root_and_a_long_rootless_group_stays_unmeasurable():
    props = ["width", "height"]
    nodes = [idx_node("main", ""), idx_node("heading", "Team", 0), idx_node("region", "Inner", 0),  # 0 main, 1 heading, 2 region
             idx_node("text", "Item", 2, text="Item"), idx_node("text", "Item", 2, text="Item"),  # two items under the region
             idx_node("region", "Dup", 0), idx_node("region", "Dup", 0),  # two same-named regions: not unique, so not anchors
             idx_node("text", "Leaf", 5, text="Leaf"), idx_node("text", "Leaf", 6, text="Leaf")]  # each under a different "Dup"
    out, bad = board.anchor_nodes(nodes, None, props)
    by = {n["n"]: n for n in out}
    assert by["text:Item[0] in region:Inner"]["a"] == {"role": "region", "name": "Inner"} and by["text:Item[1] in region:Inner"]["i"] == 1
    assert by["text:Leaf[0] in main"]["a"] == {"role": "main"} and by["text:Leaf[1] in main"]["g"] == 2  # skipped the duplicate regions
    assert bad == []
    rootless = [idx_node("text", "Row", -1, text="Row") for _ in range(board.MAX_ROOT_GROUP + 1)] + [idx_node("text", "One", -1, text="One")]
    out, bad = board.anchor_nodes(rootless, None, props)
    assert [n["n"] for n in out] == ["text:One"] and len(bad) == board.MAX_ROOT_GROUP + 1  # order alone is no anchor for a long list
    short, bad = board.anchor_nodes(rootless[:5], None, props)
    assert bad == [] and [n["n"] for n in short][0] == "text:Row[0] in page" and short[0]["a"] is None
    framed, _ = board.anchor_nodes(nodes, {id(n) for n in nodes[2:5]}, props)  # inside a frame: the anchor must be in the frame too
    assert {n["n"] for n in framed} == {"region:Inner", "text:Item[0] in region:Inner", "text:Item[1] in region:Inner"}


def app_node(role, name, parent=-1, **loc):
    n = idx_node(role, name, parent, **loc)
    n["style"] = {}
    return n


def test_an_anchor_or_index_the_app_cannot_resolve_is_unmatched_never_passed():
    props = ["width"]
    row = {"props": props, "nodes": [{"n": "text:Row[1] in main", "l": {"text": "Row"}, "v": ["10px"], "a": {"role": "main"}, "i": 1, "g": 2}]}
    ok = [app_node("main", ""), app_node("text", "Row", 0, text="Row"), app_node("text", "Row", 0, text="Row")]
    assert board.judge(row, ok)["matched"] == 1
    assert board.judge(row, ok[:1] + [app_node("text", "Row", -1, text="Row")] * 2)["matched"] == 0  # the rows are outside the anchor
    assert board.judge(row, [*ok, app_node("main", "")])["matched"] == 0  # the anchor is no longer unique in the app
    assert board.judge(row, ok[1:])["matched"] == 0  # no anchor in the app at all
    short = board.judge(row, ok[:2])  # the 2nd row is missing: unmatched, and the count differs
    assert short["matched"] == 0 and short["unmatched"] == ["text:Row[1] in main"] and short["mismatches"][0]["prop"] == "occurrences"
    passed, lines = board.verdict({**row, "id": "r", "min_match": 0.95}, short)
    assert not passed and "occurrences: board 2, app 1" in "\n".join(lines)
