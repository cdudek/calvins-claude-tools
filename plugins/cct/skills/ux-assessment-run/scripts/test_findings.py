"""The findings contract is what lets eight passes become one report without an LLM retyping it.

What breaks silently and costs a review: a merge that folds two different places into one
finding, or drops one; a clean report that cannot say who looked; a round comparison that calls
something fixed when nobody checked it; and a schema rule the stdlib validator quietly ignores.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

MODULE = pathlib.Path(__file__).resolve().parent / "findings.py"
spec = importlib.util.spec_from_file_location("findings", MODULE)
findings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(findings)


def finding(**over) -> dict:
    base = {
        "id": "L7.2",
        "lens": "laws",
        "impact": "Medium",
        "rung": "R5",
        "location": "/leads table 1280",
        "summary": "Row actions are too small to hit",
        "current": "The three dots in each row are 16 px wide.",
        "recommendation": "Make the target 24 px.",
        "tradeoff": "Rows get slightly taller.",
        "decision_needed": "Routine fix: no individual decision needed",
        "verified": "measured",
        "evidence": ["16x16 px via getBoundingClientRect"],
        "owner_words": "no earlier request found",
    }
    return {**base, **over}


def doc(skill="laws", items=(), passed=(), did_not_run=(), **over) -> dict:
    base = {
        "skill": skill,
        "version": "1",
        "scope": {"pr": "12", "widths": [1280]},
        "method": "running PR build, screenshots at 1280",
        "findings": list(items),
        "passed": list(passed),
        "did_not_run": list(did_not_run),
        "exceptions_used": [],
        "notes": [],
    }
    return {**base, **over}


# -#-#- schema and validator -#-#-


def test_the_schema_is_draft_2020_12_and_a_valid_pass_validates():
    schema = findings.load_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert findings.validate(doc(items=[finding()], passed=["L1"])) == []


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        (finding(impact="Severe"), "is not one of"),
        (finding(verified="seen", evidence=[]), "at least 1"),
        (finding(rung="R7", impact="High"), "Design choice"),
        (finding(rung="R1", impact="High"), "Critical"),
        (finding(colour="red"), "unknown field colour"),
        ({k: v for k, v in finding().items() if k != "location"}, "missing location"),
        (finding(summary="x" * 241), "longer than 240"),
    ],
)
def test_a_broken_finding_is_refused_with_a_reason(bad, message):
    errors = findings.validate(doc(items=[bad]))
    assert any(message in e for e in errors), errors


def test_a_method_must_be_one_line_and_exceptions_carry_ids():
    assert findings.validate(doc(method="one line\n")) != []
    assert findings.validate(doc(exceptions_used=["EX3"])) != []
    assert findings.validate(doc(exceptions_used=["EX-3"])) == []


def test_an_unimplemented_schema_keyword_fails_loudly_instead_of_being_skipped():
    schema = {"type": "string", "format": "uri"}
    with pytest.raises(ValueError, match="format"):
        findings.validate("x", schema)


def test_the_real_json_schema_implementation_agrees_when_installed():
    jsonschema = pytest.importorskip("jsonschema")
    schema = findings.load_schema()
    jsonschema.Draft202012Validator.check_schema(schema)
    good = doc(items=[finding()])
    bad = doc(items=[finding(rung="R7", impact="High")])
    assert jsonschema.Draft202012Validator(schema).is_valid(good)
    assert not jsonschema.Draft202012Validator(schema).is_valid(bad)


def test_expect_names_every_law_nobody_accounted_for():
    d = doc(
        items=[finding(id="L7.2")],
        passed=["L1", "L2"],
        not_applicable=[{"id": "L3", "reason": "no list"}],
    )
    assert findings.unaccounted(d, "L1-L4") == ["L4"]
    assert findings.unaccounted(d, "L7,WCAG-2.5.8") == ["WCAG-2.5.8"]


# -#-#- merge -#-#-


def test_the_same_id_at_the_same_place_merges_and_lists_every_source():
    a = doc("laws", [finding(evidence=["a.png"])])
    b = doc("accessibility", [finding(impact="High", evidence=["b.png"])])
    merged = findings.merge([a, b], "cct:ux-assessment-run")
    assert len(merged["findings"]) == 1
    only = merged["findings"][0]
    assert only["sources"] == ["laws", "accessibility"]
    assert only["evidence"] == ["a.png", "b.png"]
    assert only["impact"] == "High"
    assert any("impact differs" in n for n in merged["notes"])


def test_the_same_id_in_two_places_stays_two_findings_and_nothing_is_dropped():
    a = doc("laws", [finding(location="/leads 1280"), finding(location="/leads 390")])
    b = doc("heuristics", [finding(id="H4", lens="heuristics", location="/leads 1280")])
    merged = findings.merge([a, b], "cct:ux-assessment-run")
    assert len(merged["findings"]) == 3
    assert merged["_duplicates"] == 0


def test_a_check_that_passed_in_one_pass_and_failed_in_another_is_reported_failed():
    a = doc("laws", passed=["L7", "L1"])
    b = doc("ux-usability-reviewer", [finding(id="L7.2")])
    merged = findings.merge([a, b], "cct:ux-assessment-run")
    assert merged["passed"] == ["L1"]
    assert any("L7 passed in laws but failed in ux-usability-reviewer" in n for n in merged["notes"])


def test_merge_sorts_by_impact_and_is_byte_for_byte_repeatable():
    a = doc(
        "laws",
        [finding(impact="Low", location="b"), finding(impact="Critical", location="a", rung="R3")],
    )
    one = json.dumps(findings.merge([a], "r"), indent=2)
    two = json.dumps(findings.merge([a], "r"), indent=2)
    assert one == two
    assert [f["impact"] for f in findings.merge([a], "r")["findings"]] == ["Critical", "Low"]


def test_a_merged_file_is_itself_valid_and_merges_again_without_losing_passes():
    merged = findings.merge(
        [doc("laws"), doc("conformance", degraded="ran from lenses.md")], "cct:ux-assessment-run"
    )
    merged.pop("_duplicates")
    assert findings.validate(merged) == []
    again = findings.merge([merged, doc("spec")], "cct:ux-assessment-run")
    assert [p["skill"] for p in again["passes"]] == ["laws", "conformance", "spec"]
    assert "conformance" in again["degraded"]


# -#-#- render -#-#-


def test_no_issues_found_names_who_looked():
    merged = findings.merge([doc("laws", passed=["L1"]), doc("conformance", passed=["IG-8"])], "r")
    text = findings.render(merged, "Review")
    assert "No issues found by laws, conformance." in text
    assert "## Passed\n\nIG-8, L1" in text
    assert "## Did not run\n\n- none" in text


def test_render_has_the_finding_format_shape_and_the_degraded_banner():
    d = doc(
        "ux-usability-reviewer",
        [finding(evidence=["shots/1.png", "16 px"], supporting_notes=["Other products: Linear"])],
        degraded="ran without cct:ux-usability-reviewer",
    )
    text = findings.render(findings.merge([d], "r"), "Review")
    assert text.startswith("# Review\n\n> **Degraded run.**")
    for line in ("### F001: Row actions", "- **Impact:** Medium", "- **Verified:** measured",
                 "- **Visual:** ![F001](shots/1.png)", "- Evidence: 16 px", "- Other products: Linear", "- Seen by: ux-usability-reviewer (1 pass)"):  # fmt: skip
        assert line in text, line
    assert "**Totals:** Critical 0, High 0, Medium 1" in text


# -#-#- compare -#-#-


def test_compare_sorts_every_finding_into_exactly_one_bucket():
    prev = findings.merge(
        [
            doc(
                "laws",
                [
                    finding(id="L7.2"),
                    finding(id="L3.1", location="x"),
                    finding(id="L9.1", location="y"),
                ],
                passed=["WCAG-2.5.8"],
            ),
            doc("responsive", [finding(id="RESP-1", lens="responsive", location="z")]),
        ],
        "r",
    )
    cur = findings.merge(
        [
            doc(
                "laws",
                [
                    finding(id="L7.2", impact="High"),
                    finding(id="WCAG-2.5.8", lens="wcag", rung="R2", impact="High"),
                    finding(id="L4.1", location="n"),
                ],
                did_not_run=[{"id": "L9", "reason": "no long job in this PR"}],
            )
        ],
        "r",
    )
    result = {k: [f["id"] for f, _ in v] for k, v in findings.compare(prev, cur).items()}
    assert result == {
        "Regressed": ["WCAG-2.5.8"],
        "New": ["L4.1"],
        "Persistent": ["L7.2"],
        "Fixed": ["L3.1"],
        "Not re-checked": ["L9.1", "RESP-1"],
    }
    text = findings.render_compare(findings.compare(prev, cur))
    assert "(High, was Medium)" in text
    assert "responsive did not run this round" in text


# -#-#- CLI -#-#-


def test_the_cli_refuses_an_invalid_pass_and_renders_a_valid_run(tmp_path, capsys):
    good, bad = tmp_path / "laws.json", tmp_path / "bad.json"
    good.write_text(json.dumps(doc(items=[finding()])))
    bad.write_text(json.dumps(doc(items=[finding(impact="Severe")])))
    assert findings.main(["validate", str(good), str(bad)]) == 1
    assert "- failed: 1" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        findings.main(["merge", str(bad), "--skill", "r", "-o", str(tmp_path / "m.json")])
    merged, report = tmp_path / "merged.json", tmp_path / "findings.md"
    assert findings.main(["merge", str(good), "--skill", "cct:ux-assessment-run", "-o", str(merged)]) == 0
    assert findings.main(["render", str(merged), "-o", str(report), "--previous", str(merged)]) == 0
    text = report.read_text()
    assert "## Since the last round" in text and "Persistent 1" in text
    assert findings.main(["validate", str(merged), "--expect", "L1-L2"]) == 1
