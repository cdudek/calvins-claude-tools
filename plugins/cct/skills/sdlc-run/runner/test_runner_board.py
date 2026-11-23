"""Board extraction and real-surface checks, against local HTML in real chromium."""

import json
import subprocess
import sys
from pathlib import Path

import board
import verify

HERE = Path(__file__).parent
PAGE = """<html><body style="margin:0"><button style="padding:0 %s;width:358px">Pay</button>
<div class=a style="width:10px;height:10px">a</div><div class=a>b</div></body></html>"""
TOKENS = {"space-4": "16px"}
VP = {"width": 390, "height": 844}


def page(tmp_path, pad="12px"):
    f = tmp_path / "app.html"
    f.write_text(PAGE % pad)
    return f


def structured(props=None):
    return {
        "kind": "structured",
        "frame": "Checkout/Mobile",
        "viewport": VP,
        "nodes": [
            {
                "name": "Pay button",
                "locator": {"role": "button", "name": "Pay"},
                "props": props or {"paddingLeft": {"var": "space-4"}, "width": 358},
            }
        ],
    }


def run_check(tmp_path, f, rows, executable=None):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"target": {"kind": "web", "file": str(f)}, "rows": rows, "executable": executable}))
    p = subprocess.run([sys.executable, str(HERE / "board.py"), "check", str(spec)], capture_output=True, text=True)
    return p.returncode, p.stdout


def test_spacing_failure_names_expected_and_got(tmp_path):
    rows = board.extract(structured(), TOKENS)["rows"]
    code, out = run_check(tmp_path, page(tmp_path, "12px"), rows)
    assert code == 1
    assert "FAIL Checkout/Mobile/Pay button/padding-left: expected 16px, got 12px (tolerance 0.5px)" in out
    assert "PASS Checkout/Mobile/Pay button/width" in out
    assert "Ran 2 checks" in out and "1 failed" in out


def test_spacing_pass(tmp_path):
    rows = board.extract(structured(), TOKENS)["rows"]
    code, out = run_check(tmp_path, page(tmp_path, "16px"), rows)
    assert code == 0 and "Ran 2 checks" in out


def test_row_sources():
    rows = board.extract(structured({"paddingLeft": {"var": "space-4"}, "paddingRight": 16, "itemSpacing": 8}), TOKENS)["rows"]
    assert [(r["prop"], r["expected"], r["source"]) for r in rows] == [
        ("padding-left", "16px", "token"),
        ("padding-right", "16px", "literal"),
        ("gap", "8px", "literal"),
    ]


def test_image_only_invents_nothing():
    img = {"kind": "image", "file": "x.png", "frame": "F", "nodes": [{"name": "Pay", "locator": {"css": "b"}, "props": ["padding-left", "gap"]}]}
    out = board.extract(img)
    assert out["rows"] == []
    assert [u["id"] for u in out["unsupported"]] == ["F/Pay/padding-left", "F/Pay/gap"]
    assert all(u["reason"] == "image-only input: no measurable source" for u in out["unsupported"])


def test_unresolved_token_is_unsupported():
    out = board.extract(structured({"paddingLeft": {"var": "space-9"}, "width": 358}), TOKENS)
    assert [r["prop"] for r in out["rows"]] == ["width"]
    assert out["unsupported"][0]["id"].endswith("padding-left") and "space-9" in out["unsupported"][0]["reason"]


def test_html_board_measured_then_app_compared(tmp_path):
    ref = tmp_path / "ref.html"
    ref.write_text(PAGE % "16px")
    hb = {
        "kind": "html",
        "file": str(ref),
        "frame": "Ref",
        "viewport": VP,
        "nodes": [{"name": "Pay", "locator": {"role": "button", "name": "Pay"}, "props": ["padding-left", "width"]}],
    }
    out = board.extract(hb)
    assert out["unsupported"] == []
    assert {r["source"] for r in out["rows"]} == {"measured"}
    assert [r["expected"] for r in out["rows"]] == ["16px", "358px"]
    assert run_check(tmp_path, page(tmp_path, "16px"), out["rows"])[0] == 0
    assert run_check(tmp_path, page(tmp_path, "12px"), out["rows"])[0] == 1


def test_browser_unavailable(tmp_path):
    assert board.browser_available("/nonexistent/chrome")[0] is False
    rows = board.extract(structured(), TOKENS)["rows"]
    code, out = run_check(tmp_path, page(tmp_path), rows, "/nonexistent/chrome")
    assert code == 127 and out.startswith("env: browser unavailable")


def test_locator_must_match_exactly_one(tmp_path):
    f = page(tmp_path)
    many = {"id": "m", "locator": {"css": "div.a"}, "prop": "width", "expected": "10px", "tolerance_px": 0.5}
    none = {"id": "n", "locator": {"role": "button", "name": "Nope"}, "prop": "width", "expected": "1px", "tolerance_px": 0.5}
    code, out = run_check(tmp_path, f, [many, none])
    assert code == 1
    assert "FAIL m: locator matched 2 elements" in out and "FAIL n: locator matched 0 elements" in out


def test_gap_between_two_locators(tmp_path):
    f = tmp_path / "g.html"
    f.write_text('<body style="margin:0"><button style="display:block;height:20px;margin:0">A</button>'
                 '<button style="display:block;height:20px;margin:8px 0 0">B</button></body>')
    row = {"id": "g", "locator": {"role": "button", "name": "A"}, "between": [{"role": "button", "name": "A"}, {"role": "button", "name": "B"}],
           "prop": "gap-y", "expected": "8px", "tolerance_px": 0.5}
    assert run_check(tmp_path, f, [row])[0] == 0


def test_compare():
    assert board.compare("16px", "16px", 0.5) and board.compare(16.4, "16px", 0.5)
    assert not board.compare("12px", "16px", 0.5)
    assert board.compare("center", "center", 0.5) and not board.compare("left", "center", 0.5)


def test_verify_classifies_cli_output(tmp_path):
    chk = {"count_regex": r"Ran (\d+) checks"}
    rows = board.extract(structured(), TOKENS)["rows"]
    code, out = run_check(tmp_path, page(tmp_path, "16px"), rows)
    assert verify.classify(chk, verify.Job(code, out)) == ("PASS", "", 2)
    code, out = run_check(tmp_path, page(tmp_path), rows, "/nonexistent/chrome")
    v, why, _ = verify.classify(chk, verify.Job(code, out))
    assert v == "BLOCKED" and why.startswith("env:")
    code, out = run_check(tmp_path, page(tmp_path), [])
    assert out.strip() == "Ran 0 checks"
    v, why, _ = verify.classify(chk, verify.Job(code, out))
    assert v == "BLOCKED" and "proves nothing" in why
