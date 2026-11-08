"""Usage: pytest scripts/test_marks.py

Exercise owner-mark inventory, retained decisions, evidence checks and report output.
"""

from __future__ import annotations

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
    write(root / "spec/prototype/mobile/screen.webp")
    write(root / "asks/ordinary/session.md", "# Session\n\n## Notes\n\n1. Not a mark.\n")
    write(root / "asks/no-title/session.md", "## 001 · 12:00\n1. Not a session.\n")
    write(root / "asks/ordinary/reference.jpg")
    write(root / "spec/not-a-prototype.png")
    write(root / "asks/export.pdf")
    data = resolved(repo)
    assert len(data) == 7
    refs = [row["image"] for row in data if row["kind"] == "reference"]
    assert refs == [
        "asks/ordinary/reference.jpg",
        "asks/wireframe.PNG",
        "spec/prototype/mobile/screen.webp",
    ]
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
