"""design_index.py: every entry says when to read it, from `read_when` or from its type and tags."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates" / "scripts"))
import design_index  # noqa: E402


def _designs(tmp_path: Path) -> Path:
    designs = tmp_path / "docs" / "designs"
    designs.mkdir(parents=True)
    (designs / "2026-11-14-adr-sessions.md").write_text(
        "---\ntitle: Sessions end on press\nstatus: accepted\ntags: [safety, cleanup]\n---\n"
    )
    (designs / "2026-11-13-note-research.md").write_text("---\nstatus: active\n---\n# Research\n")
    (designs / "tracker.md").write_text(
        "---\ntitle: Tracker\ntype: design\nstatus: active\ntags: [mod]\n"
        "read_when: you change what the tracker shows\n---\n"
    )
    (designs / "plain.md").write_text("# Plain design\n")
    return designs


def test_read_when_comes_from_the_field_or_falls_back_by_type_and_tags(tmp_path: Path) -> None:
    out = design_index.render(_designs(tmp_path))
    assert "Read when: you change what the tracker shows" in out
    assert "Read when: before you change what it decided (safety, cleanup)" in out
    assert "Read when: when you need the background" in out
    assert "Read when: when your change touches it" in out


def test_every_entry_is_followed_by_its_read_when_line(tmp_path: Path) -> None:
    lines = design_index.render(_designs(tmp_path)).splitlines()
    entries = [i for i, ln in enumerate(lines) if ln.startswith("- [")]
    assert len(entries) == 4
    assert all(lines[i + 1].startswith("  Read when: ") for i in entries)
