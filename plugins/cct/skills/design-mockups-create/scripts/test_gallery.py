"""The gallery is the deliverable, so its assembly gets a check.

Three things break silently and cost the whole review: a direction folder that is skipped, a
screenshot path that does not resolve from the gallery's own directory, and a title that falls
back to the slug when `notes.md` had one. None of them raises — the page just comes out wrong.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

MODULE = pathlib.Path(__file__).resolve().parent / "gallery.py"
spec = importlib.util.spec_from_file_location("gallery", MODULE)
gallery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gallery)


def _run(tmp_path, slugs=("01-safe", "02-bold"), notes=True, shots=True):
    (tmp_path / "brief.md").write_text("Axis: risk.\n", encoding="utf-8")
    for slug in slugs:
        d = tmp_path / slug
        d.mkdir()
        (d / "index.html").write_text("<!doctype html><p>x", encoding="utf-8")
        if notes:
            title = slug.split("-", 1)[1].title()
            (d / "notes.md").write_text(f"# {title} direction\n\nWhy it looks like this.\n", "utf-8")
        if shots:
            (d / "shots").mkdir()
            (d / "shots" / "index--desktop@2x.png").write_bytes(b"\x89PNG\r\n")
    return gallery.build(tmp_path)


def test_every_direction_folder_becomes_a_card(tmp_path):
    page, n_dirs, n_shots = _run(tmp_path)
    assert n_dirs == 2
    assert n_shots == 2
    assert 'id="01-safe"' in page and 'id="02-bold"' in page


def test_the_title_comes_from_notes_not_the_slug(tmp_path):
    page, _, _ = _run(tmp_path, slugs=("01-safe",))
    assert "Safe direction" in page
    assert "Why it looks like this." in page


def test_the_slug_is_the_fallback_when_notes_are_missing(tmp_path):
    page, _, _ = _run(tmp_path, slugs=("01-bold-editorial",), notes=False)
    assert "Bold Editorial" in page


def test_image_paths_are_relative_to_the_gallery(tmp_path):
    # gallery.html sits in the run root, so an absolute path would break the moment the
    # folder is copied, zipped or opened on another machine.
    page, _, _ = _run(tmp_path, slugs=("01-safe",))
    assert 'src="01-safe/shots/index--desktop@2x.png"' in page
    assert str(tmp_path) not in page


def test_a_direction_without_screenshots_still_appears(tmp_path):
    # Rendering can fail for one direction; dropping it silently would hide that.
    page, n_dirs, n_shots = _run(tmp_path, slugs=("01-safe",), shots=False)
    assert n_dirs == 1 and n_shots == 0
    assert "No screenshot yet" in page


def test_folders_that_are_not_directions_are_ignored(tmp_path):
    _run(tmp_path, slugs=("01-safe",))
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "shots").mkdir()
    _, n_dirs, _ = gallery.build(tmp_path)
    assert n_dirs == 1


def test_an_empty_run_reports_zero_rather_than_crashing(tmp_path):
    page, n_dirs, _ = gallery.build(tmp_path)
    assert n_dirs == 0
    assert "Design directions" in page


def test_spec_mode_screen_folders_become_cards(tmp_path):
    # spec mode names folders for the screen, not NN-<slug>; they must not vanish
    for screen in ("project-patterns", "pattern-kit-editor"):
        (tmp_path / screen / "shots").mkdir(parents=True)
        (tmp_path / screen / "shots" / f"{screen}--default.png").write_bytes(b"\x89PNG\r\n")
    page, n_dirs, n_shots = gallery.build(tmp_path)
    assert n_dirs == 2 and n_shots == 2
    assert 'src="project-patterns/shots/project-patterns--default.png"' in page


if __name__ == "__main__":
    sys.exit(__import__("pytest").main([__file__, "-q"]))
