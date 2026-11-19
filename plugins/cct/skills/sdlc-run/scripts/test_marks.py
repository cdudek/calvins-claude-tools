"""Usage: pytest scripts/test_marks.py

Exercise owner-mark inventory, retained decisions, evidence checks and report output.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "templates/scripts/marks.py"
ID = "2026-10-21-feedback"
SAMPLE = """# 2026-09-26 08.43

## 001 · 16:11

![Screenshot 1](img/001.png)

1. dskfjalsdfkjdsfj5555

## 002 · 19:26

![Screenshot 2](img/002.png)

1. where is the spacing. this is super uncomfortable.
2. same here where is the spacing
3. Overall the dashboard is weak. Don't they want to see how many new leads since the last time they logged in?
"""
MULTILINE = '\n4. Keep the `div` and "quotes".\n\n   Here is a second paragraph with a | pipe.\n'


def run(repo: Path, mode: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), mode, ID], cwd=repo, capture_output=True, text=True
    )


def write(path: Path, content: str = "image") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    write(tmp_path / "sdlc.json", "{}")
    change = tmp_path / "changes" / ID
    session = change / "asks/2026-09-26"
    write(session / "session.md", SAMPLE)
    for mark in ("001", "002"):
        write(session / f"img/{mark}.png")
    return tmp_path


def change(repo: Path) -> Path:
    cfg = json.loads((repo / "sdlc.json").read_text())
    return repo / cfg.get("changesDir", "changes") / ID


def rows(repo: Path) -> list[dict]:
    return json.loads((change(repo) / "marks.json").read_text())["rows"]


def save(repo: Path, data: list[dict]) -> None:
    (change(repo) / "marks.json").write_text(json.dumps({"rows": data}))


def resolved(repo: Path) -> list[dict]:
    assert run(repo, "init").returncode == 0
    write(change(repo) / "verify/shots/fresh.png")
    data = rows(repo)
    for row in data:
        row.update(
            expected="The marked screen has spacing.",
            shot="verify/shots/fresh.png",
            status="fixed" if row["kind"] == "note" else "match",
        )
        if row["kind"] == "note":
            row["test"] = "@F1"
    write(repo / "tests/spec.test.ts", "test('spacing @F1 @change', () => {})")
    save(repo, data)
    assert run(repo, "check").returncode == 0
    return data


def test_sample_and_multiline_words_are_verbatim(repo: Path) -> None:
    session = change(repo) / "asks/2026-09-26/session.md"
    session.write_text(SAMPLE + MULTILINE)
    assert run(repo, "init").returncode == 0
    data = rows(repo)
    assert [row["id"] for row in data] == [
        "2026-09-26/001.1",
        "2026-09-26/002.1",
        "2026-09-26/002.2",
        "2026-09-26/002.3",
        "2026-09-26/002.4",
    ]
    assert data[0]["words"] == "dskfjalsdfkjdsfj5555"
    assert data[1]["words"] == "where is the spacing. this is super uncomfortable."
    assert data[2]["words"] == "same here where is the spacing"
    assert data[3]["words"] == SAMPLE.split("3. ")[1].rstrip("\n")
    assert data[4]["words"] == MULTILINE.split("4. ")[1].rstrip("\n")
    assert data[4]["session"] == "asks/2026-09-26"
    assert data[4]["mark"] == "002" and data[4]["note"] == 4
    assert data[4]["image"] == "asks/2026-09-26/img/002.png"


def test_init_preserves_filled_fields_adds_notes_and_reports_orphans(repo: Path) -> None:
    data = resolved(repo)
    data[0].update(decision="docs/designs/choice.md", differs="pending", accepted="Ship this.")
    save(repo, data)
    assert run(repo, "init").returncode == 0
    assert rows(repo) == data
    previous = (change(repo) / "marks.json").read_bytes()
    assert run(repo, "init").returncode == 0
    assert (change(repo) / "marks.json").read_bytes() == previous
    session = change(repo) / "asks/2026-09-26/session.md"
    session.write_text(SAMPLE + MULTILINE)
    assert "added=1" in run(repo, "init").stdout
    assert rows(repo)[:4] == data
    session.write_text(SAMPLE)
    result = run(repo, "init")
    assert "2026-09-26/002.4: orphan retained" in result.stdout
    assert len(rows(repo)) == 5
    assert "orphan row" in run(repo, "check").stdout


def test_inventory_references_and_only_snapmark_shaped_sessions(repo: Path) -> None:
    root = change(repo)
    write(root / "asks/wireframe.PNG")
    write(root / "spec/prototype/mobile/screen.webp")  # generated mockup: advisory, no row
    write(root / "asks/ordinary/session.md", "# Session\n\n## Notes\n\n1. Not a mark.\n")
    write(root / "asks/no-title/session.md", "## 001 · 12:00\n1. Not a session.\n")
    write(root / "asks/ordinary/reference.jpg")
    write(root / "spec/not-a-prototype.png")
    write(root / "asks/export.pdf")
    data = resolved(repo)
    assert len(data) == 6
    refs = [row["image"] for row in data if row["kind"] == "reference"]
    assert refs == ["asks/ordinary/reference.jpg", "asks/wireframe.PNG"]
    assert run(repo, "check").returncode == 0


def test_custom_directories_and_same_basename_sessions(repo: Path) -> None:
    (repo / "changes").rename(repo / "work")
    (repo / "sdlc.json").write_text(
        json.dumps({"changesDir": "work", "designsDir": "architecture"})
    )
    write(change(repo) / "asks/nested/2026-09-26/session.md", SAMPLE)
    data = resolved(repo)
    assert len(data) == 8
    assert "nested/2026-09-26/001.1" in [row["id"] for row in data]
    write(repo / "architecture/choice.md", "# ADR\n")
    data[0].update(decision="architecture/choice.md", status="ruled-out", expected="", shot="")
    save(repo, data)
    assert run(repo, "check").returncode == 0


@pytest.mark.parametrize(
    "field,value,problem",
    [
        ("expected", "", "expected is required"),
        ("expected", "  ", "expected is required"),
        ("shot", "", "shot must be"),
        ("shot", "verify/shots/missing.png", "shot must be"),
        ("shot", "verify/shots", "shot must be"),
        ("shot", "../../outside.png", "shot must be"),
        ("decision", "docs/designs/missing.md", "decision must be"),
        ("decision", "docs/designs", "decision must be"),
        ("decision", "outside.md", "decision must be"),
        ("decision", "docs/designs/../../outside.md", "decision must be"),
        ("decision", "", "decision must be"),
        ("status", "typo", "invalid status"),
        ("status", "match", "invalid status"),
        ("status", [], "invalid status"),
        ("status", None, "unresolved status"),
        ("status", "", "unresolved status"),
        ("status", "ruled-out", "decision must be"),
        ("differs", "still wrong", "fixed/match must have no differs"),
        ("words", "paraphrased", "source fields differ"),
        ("image", "wrong.png", "source fields differ"),
        ("kind", "reference", "source fields differ"),
    ],
)
def test_check_failures(repo: Path, field: str, value: object, problem: str) -> None:
    data = resolved(repo)
    write(repo / "outside.png")
    write(repo / "outside.md")
    (repo / "docs/designs").mkdir(parents=True)
    data[0][field] = value
    data[0]["accepted"] = "Accept the gap." if problem != "unresolved status" else ""
    save(repo, data)
    result = run(repo, "check")
    assert result.returncode == 1 and problem in result.stdout
    assert result.stdout.splitlines()[-1].startswith("MARKS FAIL")


@pytest.mark.parametrize("status", ["partly", "not-fixed", "contradicted", "cant-see", None, ""])
def test_unresolved_needs_engineer_words_but_still_needs_evidence(
    repo: Path, status: str | None
) -> None:
    data = resolved(repo)
    data[0].update(status=status, differs="Spacing still narrow.", accepted=" ")
    save(repo, data)
    assert run(repo, "check").returncode == 1
    data[0]["accepted"] = True
    save(repo, data)
    assert run(repo, "check").returncode == 1
    data[0]["accepted"] = "Ship this gap; fix spacing next milestone."
    save(repo, data)
    assert run(repo, "check").returncode == 0
    data[0]["shot"] = ""
    save(repo, data)
    assert run(repo, "check").returncode == 1


def test_fixed_needs_a_tag_found_in_a_spec(repo: Path) -> None:
    data = resolved(repo)
    data[0]["test"] = "@F10"
    save(repo, data)
    result = run(repo, "check")
    assert result.returncode == 1 and "001.1: test tag @F10 appears in no spec" in result.stdout
    for missing in ("", None):
        data[0]["test"] = missing
        save(repo, data)
        result = run(repo, "check")
        assert result.returncode == 1 and "fixed needs a test tag" in result.stdout
    del data[0]["test"]
    save(repo, data)
    assert "fixed needs a test tag" in run(repo, "check").stdout
    data[0]["test"] = "@F1"
    save(repo, data)
    assert run(repo, "check").returncode == 0


def test_open_mark_needs_no_tag_and_testglobs_is_honoured(repo: Path) -> None:
    data = resolved(repo)
    data[0].update(status="partly", test="", accepted="Ship it.")
    save(repo, data)
    assert run(repo, "check").returncode == 0
    data[0].update(status="fixed", accepted="", test="@F1")
    save(repo, data)
    (repo / "sdlc.json").write_text(json.dumps({"testGlobs": ["proofs/*.ts"]}))
    assert "appears in no spec" in run(repo, "check").stdout
    write(repo / "proofs/a.ts", "// @F1")
    assert run(repo, "check").returncode == 0


def test_reference_status_rules(repo: Path) -> None:
    write(change(repo) / "asks/reference.png")
    data = resolved(repo)
    row = data[-1]
    row["differs"] = "Toolbar is narrow."
    save(repo, data)
    assert "fixed/match must have no differs" in run(repo, "check").stdout
    row["status"] = "differs"
    save(repo, data)
    assert run(repo, "check").returncode == 1
    row["accepted"] = "Accept the narrower toolbar."
    save(repo, data)
    assert run(repo, "check").returncode == 0
    for invalid in ("fixed", "ruled-out"):
        row["status"] = invalid
        save(repo, data)
        assert "invalid status" in run(repo, "check").stdout


def test_waits_on_design_system_is_not_a_failure_but_names_the_gap(repo: Path) -> None:
    write(change(repo) / "asks/reference.png")
    data = resolved(repo)
    row = data[-1]
    row["status"] = "waits-on-design-system"
    row["differs"] = ""
    save(repo, data)
    assert "must name the missing design-system parts" in run(repo, "check").stdout
    row["differs"] = "Date range picker is not in the design system yet."
    save(repo, data)
    assert run(repo, "check").returncode == 0


def test_decisions_and_ruled_out_pass_with_an_adr(repo: Path) -> None:
    data = resolved(repo)
    write(repo / "docs/designs/choice.md", "# Decision\n")
    data[0].update(status="ruled-out", decision="docs/designs/choice.md", shot="", expected="")
    data[1]["decision"] = "docs/designs/choice.md"
    save(repo, data)
    assert run(repo, "check").returncode == 0


@pytest.mark.parametrize("field", ["shot", "decision"])
def test_evidence_cannot_escape_via_symlink_or_absolute_path(repo: Path, field: str) -> None:
    data = resolved(repo)
    outside = write(repo / "outside.png")
    base = change(repo) if field == "shot" else repo / "docs/designs"
    base.mkdir(parents=True, exist_ok=True)
    (base / "link.png").symlink_to(outside)
    for value in (str(outside), "link.png" if field == "shot" else "docs/designs/link.png"):
        data[0][field] = value
        save(repo, data)
        assert run(repo, "check").returncode == 1


@pytest.mark.parametrize(
    "mutation,problem",
    [("missing", "missing row"), ("duplicate", "duplicate row"), ("orphan", "orphan row")],
)
def test_inventory_coverage(repo: Path, mutation: str, problem: str) -> None:
    data = resolved(repo)
    if mutation == "missing":
        data.pop()
    elif mutation == "duplicate":
        data.append(data[0].copy())
    else:
        data.append(data[0] | {"id": "orphan", "kind": "bad"})
    save(repo, data)
    result = run(repo, "check")
    assert result.returncode == 1 and problem in result.stdout


@pytest.mark.parametrize(
    "content", [None, "{", "[]", '{"rows": {}}', '{"rows": [null]}', '{"rows": [{"id": 4}]}']
)
def test_missing_or_malformed_ledger_fails_cleanly(repo: Path, content: str | None) -> None:
    if content is not None:
        write(change(repo) / "marks.json", content)
    result = run(repo, "check")
    assert result.returncode == 1 and not result.stderr
    assert result.stdout.splitlines()[-1].startswith("MARKS FAIL")


def test_duplicate_source_ids_do_not_drop_notes(repo: Path) -> None:
    session = change(repo) / "asks/2026-09-26/session.md"
    session.write_text(SAMPLE + "\n3. Another third note.\n")
    result = run(repo, "init")
    assert result.returncode == 1 and "duplicate source IDs" in result.stdout


def test_table_renders_literal_words_paths_and_acceptance(repo: Path) -> None:
    session = change(repo) / "asks/2026-09-26/session.md"
    session.write_text(SAMPLE + MULTILINE)
    data = resolved(repo)
    data[0].update(status="partly", differs="Narrow <toolbar>.", accepted="Ship the gap.")
    data[1]["decision"] = "docs/designs/choice.md"
    save(repo, data)
    result = run(repo, "table")
    assert result.returncode == 0
    assert len(result.stdout.splitlines()) == 7
    assert "| mark | words | decision | shot | status | test | still differs |" in result.stdout
    assert '\\`div\\` and "quotes"' in result.stdout
    assert "<br><br>   Here" in result.stdout and "\\| pipe" in result.stdout
    assert "&lt;toolbar&gt;" in result.stdout
    assert "accepted: Ship the gap" in result.stdout
    assert "docs/designs/choice" in result.stdout and "verify/shots/fresh" in result.stdout


def bundle(repo: Path) -> Path:
    folder = change(repo) / "asks/2026-11-01-export"
    write(folder / "index.html", "<html>screen</html>")
    write(folder / "assets/logo.png")
    return folder


def test_export_bundle_is_one_input_and_its_files_are_not_references(repo: Path) -> None:
    bundle(repo)
    assert run(repo, "init").returncode == 0
    by_id = {row["id"]: row for row in rows(repo)}
    row = by_id["bundle:asks/2026-11-01-export"]
    assert row["kind"] == "bundle" and len(row["hash"]) == 64 and row["rendered"] == ""
    assert not any("logo.png" in rid for rid in by_id)


def test_bundle_needs_rendering_until_images_exist_and_stays_pinned(repo: Path) -> None:
    resolved(repo)  # the sample rows pass; the bundle is not in marks.json yet
    folder = bundle(repo)
    assert run(repo, "init").returncode == 0
    result = run(repo, "check")
    assert (
        result.returncode == 1 and "bundle:asks/2026-11-01-export: needs rendering" in result.stdout
    )
    write(change(repo) / "asks/2026-11-01-export-render/index--desktop@2x.png")
    run(repo, "init")
    data = rows(repo)
    for row in data:
        if row["kind"] == "bundle":
            row["rendered"] = "asks/2026-11-01-export-render"
        elif row["kind"] == "reference":
            row.update(expected="Home matches.", shot="verify/shots/fresh.png", status="match")
    save(repo, data)
    assert run(repo, "check").returncode == 0, run(repo, "check").stdout
    write(folder / "index.html", "<html>edited</html>")
    result = run(repo, "check")
    assert result.returncode == 1 and "source fields differ" in result.stdout


def test_bundle_render_folder_must_hold_an_image_under_asks(repo: Path) -> None:
    bundle(repo)
    run(repo, "init")
    data = rows(repo)
    (change(repo) / "empty").mkdir()
    for row in data:
        if row["kind"] == "bundle":
            row["rendered"] = "empty"
    save(repo, data)
    assert "rendered must be a folder under asks/" in run(repo, "check").stdout


def test_table_reports_bundle_as_needs_rendering(repo: Path) -> None:
    bundle(repo)
    run(repo, "init")
    assert "needs rendering" in run(repo, "table").stdout


def test_bundle_hash_covers_files_when_the_repo_sits_under_a_worktrees_folder(
    tmp_path: Path,
) -> None:
    repo = tmp_path / ".worktrees" / "feature"
    write(repo / "sdlc.json", "{}")
    folder = repo / "changes" / ID / "asks/export"
    write(folder / "index.html", "<html>one</html>")
    assert run(repo, "init").returncode == 0
    first = rows(repo)[0]["hash"]
    assert first != hashlib.sha256(b"").hexdigest()
    write(folder / "index.html", "<html>two</html>")
    assert "source fields differ" in run(repo, "check").stdout


def test_generated_mockups_are_advisory_not_reference_rows(repo: Path) -> None:
    write(change(repo) / "spec/prototype/home.png")
    assert run(repo, "init").returncode == 0
    assert not any("prototype" in row["id"] for row in rows(repo))


def render_row(repo: Path, rendered: str) -> None:
    run(repo, "init")
    data = rows(repo)
    for row in data:
        if row["kind"] == "bundle":
            row["rendered"] = rendered
    save(repo, data)


def test_render_folder_must_be_separate_from_the_bundle(repo: Path) -> None:
    folder = bundle(repo)
    write(folder / "shots/index--desktop@2x.png")
    render_row(repo, "asks/2026-11-01-export/shots")
    assert "must be separate from the bundle" in run(repo, "check").stdout
    render_row(repo, "asks/2026-11-01-export")
    assert "must be separate from the bundle" in run(repo, "check").stdout


def test_render_folder_must_cover_every_bundle_screen(repo: Path) -> None:
    folder = bundle(repo)
    write(folder / "about.html", "<html>about</html>")
    write(change(repo) / "asks/export-render/index.png")
    render_row(repo, "asks/export-render")
    assert "rendered has no image for screen: about" in run(repo, "check").stdout


def test_bundle_without_index_html_is_found_through_visual_source(repo: Path) -> None:
    folder = change(repo) / "asks/react-export"
    write(folder / "src/App.tsx", "export default 1")
    write(
        change(repo) / "decisions.json",
        json.dumps({"visualSource": {"kind": "export-bundle", "path": "asks/react-export"}}),
    )
    assert run(repo, "init").returncode == 0
    row = {r["id"]: r for r in rows(repo)}["bundle:asks/react-export"]
    assert row["kind"] == "bundle" and len(row["hash"]) == 64


def test_render_folder_needs_an_image_for_each_screen_by_name_F11(repo: Path) -> None:
    """render.sh names a shot <screen>--<viewport>@2x.png: two viewports of one screen are one
    screen rendered, not two."""
    folder = bundle(repo)
    write(folder / "about.html", "<html>about</html>")
    render = change(repo) / "asks/export-render"
    write(render / "index--desktop@2x.png")
    write(render / "index--mobile@2x.png")  # two images, but about has none
    render_row(repo, "asks/export-render")
    out = run(repo, "check").stdout
    assert "rendered has no image for screen: about\n" in out
    write(render / "about--desktop@2x.png")
    out = run(repo, "check").stdout
    assert "no image for screen" not in out


def test_a_directory_named_like_an_image_is_not_a_render_F11(repo: Path) -> None:
    folder = bundle(repo)
    (change(repo) / "asks/export-render/index.png").mkdir(parents=True)
    render_row(repo, "asks/export-render")
    assert "rendered has no image for screen: index" in run(repo, "check").stdout
    assert folder.exists()


def test_a_passing_legacy_ledger_survives_the_new_inventory_F8(repo: Path) -> None:
    """The ledger of a milestone in flight, passing under the old inventory: it had a row for a
    generated mockup and one for an image inside what is now a recognised bundle."""
    resolved(repo)
    root = change(repo)
    folder = bundle(repo)
    write(folder / "assets/hero.png")
    write(root / "spec/prototype/home.png")
    legacy = rows(repo) + [
        {
            "id": "ref:spec/prototype/home.png",
            "kind": "reference",
            "image": "spec/prototype/home.png",
            "expected": "Home matches.",
            "shot": "verify/shots/fresh.png",
            "status": "match",
        },
        {
            "id": "ref:asks/2026-11-01-export/assets/hero.png",
            "kind": "reference",
            "image": "asks/2026-11-01-export/assets/hero.png",
            "decision": "docs/designs/choice.md",
            "expected": "Hero matches.",
            "shot": "verify/shots/fresh.png",
            "status": "match",
        },
    ]
    save(repo, legacy)
    write(repo / "docs/designs/choice.md")
    assert "orphan row" in run(repo, "check").stdout  # the failure the migration removes
    init = run(repo, "init")
    assert init.returncode == 0 and "orphans=0" in init.stdout, init.stdout
    data = json.loads((root / "marks.json").read_text())
    assert [r for r in data["retired"]] == [legacy[-2]]  # the evidence is kept whole
    bundle_row = next(r for r in data["rows"] if r["kind"] == "bundle")
    assert bundle_row["folded"] == [legacy[-1]]  # with its owner decision
    assert not any(r["id"].startswith("ref:spec/prototype") for r in data["rows"])
    write(root / "asks/2026-11-01-export-render/index--desktop@2x.png")
    for row in data["rows"]:
        if row["kind"] == "bundle":
            row["rendered"] = "asks/2026-11-01-export-render"
        elif row["id"].startswith("ref:asks/2026-11-01-export-render"):
            row.update(expected="Home matches.", shot="verify/shots/fresh.png", status="match")
    (root / "marks.json").write_text(json.dumps(data))
    run(repo, "init")  # the rendered image becomes a reference row
    data = json.loads((root / "marks.json").read_text())
    for row in data["rows"]:
        if row["id"].startswith("ref:asks/2026-11-01-export-render"):
            row.update(expected="Home matches.", shot="verify/shots/fresh.png", status="match")
    (root / "marks.json").write_text(json.dumps(data))
    final = run(repo, "check")
    assert final.returncode == 0, final.stdout
    run(repo, "init")
    again = (root / "marks.json").read_bytes()
    run(repo, "init")
    assert (root / "marks.json").read_bytes() == again  # migrating twice changes nothing


def test_marks_py_still_exports_what_an_older_gate_imports_F3() -> None:
    """The other upgrade order: marks.py replaced, verify_gate.py not (it imports both names)."""
    spec = __import__("importlib.util").util.spec_from_file_location("marks_new", SCRIPT)
    mod = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.bundles) and callable(mod.sessions)


# 3.20.2: round-2 review (findings 11 and M4).
def test_a_nested_screen_needs_its_own_image_not_another_screens_F11(repo: Path) -> None:
    """settings/index.html and index.html are two screens; one `index` shot is only the second."""
    folder = bundle(repo)
    write(folder / "settings/index.html", "<html>settings</html>")
    render = change(repo) / "asks/export-render"
    write(render / "index--desktop@2x.png")
    render_row(repo, "asks/export-render")
    out = run(repo, "check").stdout
    assert "rendered has no image for screen: settings/index\n" in out
    write(render / "settings/index--desktop@2x.png")
    assert "no image for screen" not in run(repo, "check").stdout
    # render.sh puts a screen's shots in a shots/ folder beside it
    (render / "settings/index--desktop@2x.png").unlink()
    write(render / "settings/shots/index--desktop@2x.png")
    assert "no image for screen" not in run(repo, "check").stdout


def test_a_screen_in_a_folder_is_not_satisfied_by_a_same_named_stem_elsewhere_F11(
    repo: Path,
) -> None:
    folder = bundle(repo)
    write(folder / "a/home.html", "<html>a</html>")
    write(folder / "b/home.html", "<html>b</html>")
    render = change(repo) / "asks/export-render"
    for name in ("index.png", "a/home.png"):
        write(render / name)
    render_row(repo, "asks/export-render")
    assert "no image for screen: b/home\n" in run(repo, "check").stdout


def test_migration_keeps_a_row_whose_bundle_image_never_existed_M4(repo: Path) -> None:
    """A legacy image row folds into its bundle only when the image is still on disk: a deleted
    one stays a failing row, never a passing ledger."""
    resolved(repo)
    root = change(repo)
    folder = bundle(repo)
    write(folder / "assets/hero.png")
    gone = {
        "id": "ref:asks/2026-11-01-export/assets/gone.png",
        "kind": "reference",
        "image": "asks/2026-11-01-export/assets/gone.png",
        "expected": "Gone matches.",
        "shot": "verify/shots/fresh.png",
        "status": "match",
    }
    save(repo, rows(repo) + [gone])
    init = run(repo, "init")
    assert "folded into" not in init.stdout and "orphans=1" in init.stdout, init.stdout
    data = json.loads((root / "marks.json").read_text())
    assert gone in data["rows"] and not any(r.get("folded") for r in data["rows"])
    assert "ref:asks/2026-11-01-export/assets/gone.png: orphan row" in run(repo, "check").stdout
