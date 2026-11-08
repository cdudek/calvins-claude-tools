# Usage: uvx pytest -q plugins/cct/skills/ux-assessment-run/scripts/test_visual_check.py
# Purpose: prove incomplete visual reviews cannot pass the screenshot guard.
# Output sections: pytest's test summary.

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("visual-check.py")
spec = importlib.util.spec_from_file_location("visual_check", SCRIPT)
visual = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visual)


@pytest.fixture
def capture(tmp_path):
    run = tmp_path / "run with spaces"
    shot = run / "shots" / "nested" / "settings.PNG"
    shot.parent.mkdir(parents=True)
    # The guard inventories bytes; image decoding belongs to the image-reading tool.
    shot.write_bytes(b"captured screenshot bytes")
    repo = tmp_path / "product"
    repo.mkdir()
    (repo / "DESIGN.md").write_text("# Errors\nError labels must remain visible.\n")
    row = {
        "file": "shots/nested/settings.PNG",
        "screen_state": "Settings / error / 100%",
        "width": 390,
        "opened_with": "view_image call-123",
        "sha256": hashlib.sha256(shot.read_bytes()).hexdigest(),
        "observations": "The error label is visible above the footer.",
        "verdict": "compliant",
        "issues": [],
    }
    return run, repo, row


def write(run, rows):
    (run / "visual.json").write_text(json.dumps({"screenshots": rows}))


def issue(**over):
    return {
        "id": "VIS-001",
        "summary": "The footer clips the error",
        "verdict": "violates DESIGN.md#Errors",
        "quote": "Error labels must remain visible.",
        **over,
    }


def check_issue(capture, value):
    run, repo, row = capture
    row.update(verdict="issues", issues=[value])
    write(run, [row])
    return visual.check(run, repo)


def test_opened_clean_screenshot_passes(capture):
    run, repo, row = capture
    write(run, [row])
    assert visual.check(run, repo) == []


@pytest.mark.parametrize(
    "value",
    [
        issue(),
        issue(verdict="allowed by DESIGN.md#Errors"),
        issue(verdict="no convention", proposal="Require visible errors via cct:ux-decision-log"),
    ],
)
def test_all_three_convention_verdicts_pass(capture, value):
    assert check_issue(capture, value) == []


def test_inventory_catches_new_nested_capture_and_names_it(capture):
    run, repo, row = capture
    write(run, [row])
    (run / "shots" / "nested" / "menu.webp").write_bytes(b"new")
    assert visual.check(run, repo) == ["shots/nested/menu.webp: missing screenshot row"]


def test_missing_ledger_names_every_unreviewed_image(capture):
    run, repo, row = capture
    assert any(row["file"] in error for error in visual.check(run, repo))


@pytest.mark.parametrize(
    "content",
    [
        "{",
        "null",
        "[]",
        '{"screenshots": {}}',
        '{"screenshots": [], "screenshots": []}',
    ],
)
def test_malformed_ledger_fails(capture, content):
    run, repo, _ = capture
    (run / "visual.json").write_text(content)
    assert visual.check(run, repo)


def test_empty_capture_set_cannot_pass(tmp_path):
    write(tmp_path, [])
    assert "no screenshots" in visual.check(tmp_path, tmp_path)[0]


def test_nonexistent_run_cannot_pass(tmp_path):
    assert visual.check(tmp_path / "missing", tmp_path)


@pytest.mark.parametrize(
    "field", ["opened_with", "observations", "screen_state", "sha256", "width"]
)
def test_capture_only_or_incomplete_row_cannot_pass(capture, field):
    run, repo, row = capture
    del row[field]
    write(run, [row])
    assert any(field in error for error in visual.check(run, repo))


def test_recapture_requires_new_inspection(capture):
    run, repo, row = capture
    write(run, [row])
    (run / row["file"]).write_bytes(b"recaptured")
    assert "open it again" in visual.check(run, repo)[0]


def test_duplicate_and_unknown_rows_fail(capture):
    run, repo, row = capture
    write(run, [row, row, {**row, "file": "elsewhere.png"}])
    errors = visual.check(run, repo)
    assert any("duplicate" in error for error in errors)
    assert any("not a captured screenshot" in error for error in errors)


@pytest.mark.parametrize(
    ("verdict", "issues"),
    [("issues", []), ("compliant", [issue()]), ("pass", []), ("issues", None)],
)
def test_screenshot_verdict_must_match_issues(capture, verdict, issues):
    run, repo, row = capture
    row.update(verdict=verdict, issues=issues)
    write(run, [row])
    assert visual.check(run, repo)


@pytest.mark.parametrize(
    "value",
    [
        {},
        "a clipping issue without a verdict",
        issue(verdict=None),
        issue(verdict=["no convention", "violates DESIGN.md#Errors"]),
        issue(verdict="violates DESIGN.md"),
        issue(verdict="maybe okay"),
        issue(verdict="violates DESIGN.md#Errors; allowed by DESIGN.md#Errors"),
        issue(quote=""),
        issue(quote="An invented rule."),
        issue(verdict="violates MISSING.md#Errors"),
        issue(verdict="allowed by DESIGN.md#Errors", quote=""),
        issue(verdict="no convention", proposal=""),
        issue(id=""),
        issue(summary=""),
    ],
)
def test_incomplete_or_ungrounded_issue_cannot_pass(capture, value):
    errors = check_issue(capture, value)
    assert errors
    assert all("settings.PNG" in error for error in errors)


def test_each_issue_needs_its_own_verdict(capture):
    run, repo, row = capture
    row.update(verdict="issues", issues=[issue(), {"id": "VIS-002", "summary": "Wrong colour"}])
    write(run, [row])
    assert any("issue 2" in error and "verdict" in error for error in visual.check(run, repo))


def test_quote_cannot_escape_product_repo(capture):
    run, _, _ = capture
    (run.parent / "outside.md").write_text("Error labels must remain visible.\n")
    assert any(
        "product repo" in error
        for error in check_issue(capture, issue(verdict="violates ../outside.md#Errors"))
    )


def test_cli_exit_and_section_are_fail_closed(capture):
    run, repo, row = capture
    command = [sys.executable, str(SCRIPT), str(run), "--repo", str(repo)]
    failed = subprocess.run(command, capture_output=True, text=True)
    assert failed.returncode == 1
    assert "-#-#- VISUAL_CHECK -#-#-" in failed.stdout
    assert "review did not run" in failed.stdout and row["file"] in failed.stdout
    write(run, [row])
    passed = subprocess.run(command, capture_output=True, text=True)
    assert passed.returncode == 0 and "coverage checked" in passed.stdout


def test_linked_capture_directory_cannot_hide_unreviewed_images(capture):
    run, repo, row = capture
    write(run, [row])
    outside = run.parent / "other captures"
    outside.mkdir()
    (outside / "missed.png").write_bytes(b"not inspected")
    (run / "linked shots").symlink_to(outside, target_is_directory=True)
    assert any("linked directory" in error for error in visual.check(run, repo))
