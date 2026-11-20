"""The generated Python guardrail suite accepts a size S change that has no UX stage (3.24.0)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "tests" / "test_sdlc.py"
ID = "2026-11-20-words"


def _suite(tmp_path: Path, size: str, template: str | None = None) -> subprocess.CompletedProcess[str]:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_sdlc.py").write_text(
        (template or TEMPLATE.read_text(encoding="utf-8")).replace("{{ROOT_DEPTH}}", "1")
    )
    (tmp_path / "sdlc.json").write_text(json.dumps({"tiers": False, "blocked": []}))
    change = tmp_path / "changes" / ID
    change.mkdir(parents=True)
    (change / "decisions.json").write_text(json.dumps({"size": size, "kind": "chore", "skips": {}}))
    (change / "plan.md").write_text("---\nstatus: approved\n---\n")
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_sdlc.py", "-q", "-k", "v3_approved_plan", "-p", "no:cacheprovider"],
        cwd=tmp_path, capture_output=True, text=True,
    )  # fmt: skip


@pytest.mark.parametrize("size", ["S", "none"])
def test_a_change_with_no_ux_stage_needs_no_spec_files(tmp_path: Path, size: str) -> None:
    r = _suite(tmp_path, size)
    assert r.returncode == 0, r.stdout[-1500:]


def test_a_size_m_change_still_needs_them(tmp_path: Path) -> None:
    r = _suite(tmp_path, "M")
    assert r.returncode != 0 and "screens" in r.stdout


def test_the_node_suite_and_the_hooks_list_the_same_two_sizes() -> None:
    root = TEMPLATE.parents[1]
    assert 'new Set(["none", "S"])' in (root / "tests" / "sdlc.test.ts").read_text()
    assert '("none", "S")' in (root / "hooks" / "chain-gate.sh").read_text()


@pytest.mark.parametrize("design", ["none", "spec", "null"])
def test_a_change_with_no_separate_design_document_passes_the_design_checks(tmp_path: Path, design: str) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_sdlc.py").write_text(TEMPLATE.read_text(encoding="utf-8").replace("{{ROOT_DEPTH}}", "1"))
    (tmp_path / "sdlc.json").write_text(json.dumps({"tiers": False, "blocked": []}))
    change = tmp_path / "changes" / ID
    change.mkdir(parents=True)
    (change / "decisions.json").write_text(json.dumps({"size": "S", "kind": "chore", "skips": {}}))
    (change / "plan.md").write_text(f"---\nstatus: approved\nlinear: none\ncreated: 2026-11-20\nchange: {ID}\ndesign: {design}\n---\n")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_sdlc.py", "-q", "-k", "frontmatter_names or lists_the_change", "-p", "no:cacheprovider"],
        cwd=tmp_path, capture_output=True, text=True,
    )  # fmt: skip
    assert r.returncode == 0, r.stdout[-1500:]


def test_the_node_suite_accepts_the_same_no_design_words() -> None:
    node = (TEMPLATE.parents[1] / "tests" / "sdlc.test.ts").read_text()
    assert 'new Set(["null", "none", "spec"])' in node and 'fm.design !== "null"' not in node and 'fm.design === "null"' not in node
