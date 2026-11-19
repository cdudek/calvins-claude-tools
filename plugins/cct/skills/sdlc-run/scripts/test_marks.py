"""Usage: pytest scripts/test_marks.py

Exercise owner-mark inventory, retained decisions, evidence checks and report output.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
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


def home_of(repo: Path) -> Path:
    return repo.parent / f"{repo.name}-home"


def run(repo: Path, mode: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "HOME": str(home_of(repo))}
    return subprocess.run(
        [sys.executable, str(SCRIPT), mode, ID], cwd=repo, capture_output=True, text=True, env=env
    )


OPTIONS = ["Fix it now", "Accept as is", "Defer to milestone 2", "Block the close"]


def owner_says(repo: Path, row_id: str, label: str = "Accept as is", n: int = 1) -> None:
    """The owner's structured answer to a dialog about one row, in the session transcript Claude
    Code keeps for this repo."""
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo.resolve()))
    folder = home_of(repo) / ".claude/projects" / slug
    folder.mkdir(parents=True, exist_ok=True)
    question = f"Change {ID}, finding {row_id}: the spacing differs. What now?"
    stamp = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=60 + n)).isoformat()
    entries = [
        {"type": "assistant", "timestamp": stamp, "message": {"content": [{
            "type": "tool_use", "id": f"t{n}", "name": "AskUserQuestion",
            "input": {"questions": [{"question": question, "options": [{"label": o} for o in OPTIONS]}]},
        }]}},
        {"type": "user", "timestamp": stamp, "toolUseResult": {"answers": {question: label}},
         "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{n}", "content": "ok"}]}},
    ]  # fmt: skip
    with (folder / "session.jsonl").open("a") as out:
        out.write("".join(json.dumps(e) + "\n" for e in entries))


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
    save(repo, data)
    result = run(repo, "check")
    assert result.returncode == 1 and problem in result.stdout
    assert result.stdout.splitlines()[-1].startswith("MARKS FAIL")


@pytest.mark.parametrize("status", ["partly", "not-fixed", "contradicted", "cant-see", None, ""])
def test_unresolved_needs_the_owners_answer_but_still_needs_evidence(
    repo: Path, status: str | None
) -> None:
    """Review finding 7: a typed `accepted` string settles nothing; only the owner's answer to the
    dialog about this row does."""
    data = resolved(repo)
    data[0].update(status=status, differs="Spacing still narrow.", accepted="Ship this gap; fix it.")
    save(repo, data)
    assert run(repo, "check").returncode == 1
    owner_says(repo, "2026-09-26/001.1", "Fix it now", 1)
    assert run(repo, "check").returncode == 1
    owner_says(repo, "2026-09-26/001.1", "Block the close", 2)
    assert run(repo, "check").returncode == 1
    owner_says(repo, "2026-09-26/001.1", "Defer to milestone 2", 3)
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
    data[0].update(status="partly", test="")
    save(repo, data)
    owner_says(repo, "2026-09-26/001.1")
    assert run(repo, "check").returncode == 0
    data[0].update(status="fixed", test="@F1")
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
    save(repo, data)
    owner_says(repo, row["id"])
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


# 3.21.0: one capture manifest; a capture is reused only while its inputs are unchanged.
def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def with_manifest(repo: Path, **tweak: object) -> dict:
    """A resolved change, committed, with a manifest whose cells all match the current build."""
    data = resolved(repo)
    write(repo / "src/app.ts", "v1")
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "build")
    sha = git(repo, "rev-parse", "HEAD")
    entries = []
    for i, row in enumerate(data):
        reference = hashlib.sha256((change(repo) / row["image"]).read_bytes()).hexdigest()
        entries.append(
            {
                "shot": row["shot"], "build": sha, "reference": reference,
                "screen": f"s{i}", "state": "open", "width": 1280, "zoom": 100,
            }
        )  # fmt: skip
        entries.append({**entries[-1], "zoom": 150})  # the required matrix has both zooms
    manifest = {"entries": entries, "qa": {"build": sha}} | tweak
    write(change(repo) / "verify/shots/manifest.json", json.dumps(manifest))
    return manifest


def test_a_manifest_whose_inputs_are_unchanged_passes(repo: Path) -> None:
    with_manifest(repo)
    assert run(repo, "check").returncode == 0


def test_a_records_only_commit_keeps_the_captures_valid(repo: Path) -> None:
    with_manifest(repo)
    write(change(repo) / "findings.md", "records")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "records")
    assert run(repo, "check").returncode == 0


def test_a_code_change_after_the_capture_makes_it_stale(repo: Path) -> None:
    with_manifest(repo)
    write(repo / "src/app.ts", "v2")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "fix")
    result = run(repo, "check")
    assert result.returncode == 1 and "stale: src/app.ts changed since build" in result.stdout


def test_a_changed_reference_makes_the_capture_stale(repo: Path) -> None:
    manifest = with_manifest(repo)
    first = rows(repo)[0]["image"]
    write(change(repo) / first, "a new reference revision")
    result = run(repo, "check")
    assert result.returncode == 1 and "reference changed since capture" in result.stdout
    assert manifest["entries"]


def test_a_shot_missing_from_the_manifest_is_a_problem(repo: Path) -> None:
    with_manifest(repo, entries=[])
    assert "not in the capture manifest" in run(repo, "check").stdout


def test_one_cell_captured_twice_is_a_problem(repo: Path) -> None:
    manifest = with_manifest(repo)
    manifest["entries"][1].update(manifest["entries"][0] | {"shot": manifest["entries"][1]["shot"]})
    write(change(repo) / "verify/shots/manifest.json", json.dumps(manifest))
    assert "captured twice" in run(repo, "check").stdout


def test_a_qa_verdict_is_stale_when_its_build_is(repo: Path) -> None:
    manifest = with_manifest(repo)
    write(repo / "src/app.ts", "v2")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "fix")
    manifest["entries"] = [e | {"build": git(repo, "rev-parse", "HEAD")} for e in manifest["entries"]]
    write(change(repo) / "verify/shots/manifest.json", json.dumps(manifest))
    assert "qa.md is stale" in run(repo, "check").stdout


def test_no_manifest_means_the_old_behaviour(repo: Path) -> None:
    resolved(repo)
    assert run(repo, "check").returncode == 0


# Review findings 12 and 13: a strict manifest (changes approved from 3.21.0) cannot be skipped,
# faked with a moving ref or kept alive by a metadata flag, and goes stale per cell.
SHA = r"[0-9a-f]{40}"


def strict(repo: Path, **tweak: object) -> dict:
    """with_manifest, then the 3.21.0 form: a lock that requires the manifest, per-cell sources, a
    shared list and a real qa.md in the spec folder recording its build."""
    manifest = with_manifest(repo)
    write(repo / "src/a.ts", "a1")
    write(repo / "src/b.ts", "b1")
    write(repo / "src/shared.ts", "s1")
    for i, entry in enumerate(manifest["entries"]):
        entry["sources"] = ["src/a.ts"] if i % 2 == 0 else ["src/b.ts"]
    manifest["shared"] = ["src/shared.ts"]
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "sources")
    sha = git(repo, "rev-parse", "HEAD")
    for entry in manifest["entries"]:
        entry["build"] = sha
    manifest.pop("qa", None)
    manifest |= tweak
    write(change(repo) / "verify/shots/manifest.json", json.dumps(manifest))
    write(change(repo) / "lock.json", json.dumps({"criteria": {}, "manifest": "required"}))
    write(change(repo) / "spec/qa.md", f"# QA\n\nBuild: {sha}\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "records")
    return manifest


def rewrite(repo: Path, manifest: dict) -> None:
    write(change(repo) / "verify/shots/manifest.json", json.dumps(manifest))


def test_a_strict_manifest_in_good_order_passes(repo: Path) -> None:
    strict(repo)
    assert run(repo, "check").returncode == 0, run(repo, "check").stdout


def test_a_missing_manifest_fails_a_visual_close_that_requires_it(repo: Path) -> None:
    resolved(repo)
    write(change(repo) / "lock.json", json.dumps({"criteria": {}, "manifest": "required"}))
    result = run(repo, "check")
    assert result.returncode == 1 and "capture manifest is required" in result.stdout


@pytest.mark.parametrize("build", ["HEAD", "main", "abc1234", "HEAD~1"])
def test_a_build_must_be_an_immutable_commit_sha(repo: Path, build: str) -> None:
    manifest = strict(repo)
    manifest["entries"][0]["build"] = build
    rewrite(repo, manifest)
    result = run(repo, "check")
    assert result.returncode == 1 and "build must be a full commit sha" in result.stdout


@pytest.mark.parametrize("digest", [None, "", "short", "g" * 64])
def test_the_reference_digest_is_required(repo: Path, digest: object) -> None:
    manifest = strict(repo)
    manifest["entries"][0]["reference"] = digest
    rewrite(repo, manifest)
    assert "reference digest is required" in run(repo, "check").stdout


def test_a_cell_must_name_its_source_files(repo: Path) -> None:
    manifest = strict(repo)
    manifest["entries"][0]["sources"] = []
    rewrite(repo, manifest)
    assert "must list the source files" in run(repo, "check").stdout


def test_manifest_qa_metadata_cannot_stand_in_for_the_qa_file(repo: Path) -> None:
    manifest = strict(repo)
    (change(repo) / "spec/qa.md").unlink()
    manifest["qa"] = {"build": manifest["entries"][0]["build"]}
    rewrite(repo, manifest)
    assert "qa.md is missing" in run(repo, "check").stdout


def test_qa_md_is_verified_by_its_own_recorded_build(repo: Path) -> None:
    strict(repo)
    write(change(repo) / "spec/qa.md", "# QA\n\nno build line\n")
    assert "qa.md records no `Build: <sha>`" in run(repo, "check").stdout
    write(change(repo) / "spec/qa.md", f"# QA\n\nBuild: {'1' * 40}\n")
    assert "qa.md is stale" in run(repo, "check").stdout


def commit_all(repo: Path, message: str) -> str:
    git(repo, "add", ".")
    git(repo, "commit", "-qm", message)
    return git(repo, "rev-parse", "HEAD")


def test_fixing_one_screen_and_recapturing_it_leaves_the_other_cells_valid(repo: Path) -> None:
    manifest = strict(repo)
    write(repo / "src/a.ts", "a2")  # screen A is fixed
    new = commit_all(repo, "fix a")
    write(change(repo) / "spec/qa.md", f"# QA\n\nBuild: {new}\n")
    commit_all(repo, "qa")
    result = run(repo, "check")
    assert result.returncode == 1 and "src/a.ts changed since build" in result.stdout
    assert "src/b.ts" not in result.stdout  # B's inputs did not move
    for entry in manifest["entries"][::2]:  # recapture only the A cells, from the new build
        entry["build"] = new
    rewrite(repo, manifest)
    assert run(repo, "check").returncode == 0, run(repo, "check").stdout


def test_a_shared_dependency_change_invalidates_every_cell(repo: Path) -> None:
    strict(repo)
    write(repo / "src/shared.ts", "s2")
    commit_all(repo, "shared")
    out = run(repo, "check").stdout
    assert out.count("src/shared.ts changed since build") >= 2


def test_a_well_formed_sha_that_is_no_commit_is_stale(repo: Path) -> None:
    manifest = strict(repo)
    manifest["entries"][0]["build"] = "0" * 40
    rewrite(repo, manifest)
    assert "is not a commit here" in run(repo, "check").stdout


# Security review of the strict manifest: no fail-open edges.
@pytest.mark.parametrize("content", ["{broken", "[]", "null", ""])
def test_a_corrupt_lock_turns_the_strict_checks_on_never_off(repo: Path, content: str) -> None:
    resolved(repo)
    write(change(repo) / "lock.json", content)
    result = run(repo, "check")
    assert result.returncode == 1 and "capture manifest is required" in result.stdout


def test_no_lock_at_all_keeps_the_legacy_behaviour(repo: Path) -> None:
    resolved(repo)
    assert not (change(repo) / "lock.json").exists()
    assert run(repo, "check").returncode == 0


def test_a_visual_change_without_any_qa_md_fails_even_without_a_spec_folder(repo: Path) -> None:
    strict(repo)
    import shutil

    shutil.rmtree(change(repo) / "spec")
    assert "qa.md is missing" in run(repo, "check").stdout


def test_a_strict_change_without_visual_rows_needs_no_qa_md(repo: Path) -> None:
    write(change(repo) / "marks.json", '{"rows": []}')
    for path in (change(repo) / "asks").rglob("*"):
        if path.is_file():
            path.unlink()
    write(change(repo) / "lock.json", json.dumps({"criteria": {}, "manifest": "required"}))
    out = run(repo, "check").stdout
    assert "qa.md" not in out and "capture manifest is required" not in out


def test_the_strict_qa_check_runs_even_when_the_manifest_is_missing(repo: Path) -> None:
    resolved(repo)
    write(change(repo) / "lock.json", json.dumps({"criteria": {}, "manifest": "required"}))
    out = run(repo, "check").stdout
    assert "capture manifest is required" in out and "qa.md is missing" in out


@pytest.mark.parametrize("source", ["/etc/passwd", "/", ".", "..", "../x", "src/../src/a.ts", "src/nothing.ts", "untracked.ts"])
def test_a_declared_source_must_be_a_plain_path_tracked_at_head(repo: Path, source: str) -> None:
    manifest = strict(repo)
    write(repo / "untracked.ts", "x")
    manifest["entries"][0]["sources"] = [source]
    rewrite(repo, manifest)
    out = run(repo, "check").stdout
    assert "is not a plain repo path tracked at HEAD" in out, out


def test_a_shared_dependency_must_be_tracked_too(repo: Path) -> None:
    manifest = strict(repo)
    manifest["shared"] = ["src/nowhere.ts"]
    rewrite(repo, manifest)
    assert "is not a plain repo path tracked at HEAD" in run(repo, "check").stdout


def test_a_source_folder_tracked_at_head_is_accepted(repo: Path) -> None:
    manifest = strict(repo)
    manifest["entries"][0]["sources"] = ["src"]
    rewrite(repo, manifest)
    assert run(repo, "check").returncode == 0, run(repo, "check").stdout


# Security follow-ups: canonical literal sources; qa.md freshness whenever it exists.
@pytest.mark.parametrize("source", ["src/*", "src/?.ts", "src/[ab].ts", "src\\a.ts", ":(top)src/a.ts", ":src/a.ts", "src/a.ts "])
def test_a_source_with_glob_or_pathspec_syntax_is_rejected(repo: Path, source: str) -> None:
    manifest = strict(repo)
    manifest["entries"][0]["sources"] = [source]
    rewrite(repo, manifest)
    assert "is not a plain repo path tracked at HEAD" in run(repo, "check").stdout


def test_the_staleness_check_watches_the_canonical_source_path(repo: Path) -> None:
    manifest = strict(repo)
    manifest["entries"][0]["sources"] = ["src/a.ts/"]  # a trailing slash is canonicalised, not raw
    rewrite(repo, manifest)
    assert run(repo, "check").returncode == 0, run(repo, "check").stdout
    write(repo / "src/a.ts", "a2")
    commit_all(repo, "fix a")
    assert "src/a.ts changed since build" in run(repo, "check").stdout


def test_a_stale_qa_md_fails_even_when_the_rows_look_non_visual(repo: Path) -> None:
    strict(repo)
    write(change(repo) / "marks.json", '{"rows": []}')  # rows edited away
    write(change(repo) / "spec/qa.md", f"# QA\n\nBuild: {'1' * 40}\n")
    out = run(repo, "check").stdout
    assert "qa.md is stale" in out


def test_a_missing_qa_md_fails_when_the_spec_folder_exists_even_without_visual_rows(repo: Path) -> None:
    strict(repo)
    write(change(repo) / "marks.json", '{"rows": []}')
    (change(repo) / "spec/qa.md").unlink()
    assert "qa.md is missing" in run(repo, "check").stdout


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


# 3.20.3: only the renderer's own suffix comes off an image name.
def test_a_screen_with_a_double_dash_name_is_satisfied_by_its_rendered_shot_C4(repo: Path) -> None:
    """render.sh writes <screen>--<viewport>@2x.png: home--compact.html gives
    home--compact--desktop@2x.png, which is that screen and not `home`."""
    folder = bundle(repo)
    write(folder / "home--compact.html", "<html>compact</html>")
    render = change(repo) / "asks/export-render"
    write(render / "index--desktop@2x.png")
    write(render / "home--desktop@2x.png")  # the screen `home`, which does not exist
    render_row(repo, "asks/export-render")
    assert "no image for screen: home--compact\n" in run(repo, "check").stdout
    write(render / "shots/home--compact--desktop@2x.png")
    out = run(repo, "check").stdout
    assert "no image for screen" not in out, out
    shot = render / "shots/home--compact--desktop@2x.png"
    for viewport in ("mobile", "zoom150"):  # the other two viewports are the same screen
        shot = shot.rename(render / f"shots/home--compact--{viewport}@2x.png")
        assert "no image for screen" not in run(repo, "check").stdout
