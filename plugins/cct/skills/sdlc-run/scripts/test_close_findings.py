"""Usage: pytest scripts/test_close_findings.py

Review finding 11: the close's visual and convergence findings reach the fix set the triager reads
(findings.json + verdicts.json of the code review's state directory), with their own ids.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "close_findings.py"
HANDOFF = Path(__file__).resolve().parents[2] / "review-code-run/scripts/fix-handoff.sh"
ID = "2026-11-19-x"

FINDINGS = """## Blocking

- [ ] **B2** the card overflows at 320 (web/card.tsx:12)
- [x] **B3** already fixed
- [ ] **V1** heading differs from the reference

## Converge

- [ ] **C1** missing: F3 - a.ts:1

## Advisory

- [ ] **A1** rename a variable
"""


def run(state: Path, findings: Path, home: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(state), str(findings), "--change", ID],
        capture_output=True,
        text=True,
        env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
        cwd=state,
    )


def fix_now(state: Path) -> list[dict]:
    out = subprocess.run(
        ["bash", str(HANDOFF), str(state / "findings.json"), str(state / "verdicts.json")],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out)["fix_now"]


def test_a_clean_code_review_plus_blocking_close_findings_gives_a_non_empty_fix_set(tmp_path: Path) -> None:
    state = tmp_path / "rev-1"
    state.mkdir()
    (state / "findings.json").write_text('{"findings": []}')  # the code review found nothing
    (state / "verdicts.json").write_text("[]")
    md = tmp_path / "findings.md"
    md.write_text(FINDINGS)
    r = run(state, md, tmp_path / "home")
    assert r.returncode == 0, r.stderr
    got = fix_now(state)
    assert [f["id"] for f in got] == ["B2", "V1", "C1"]  # ids kept; ticked and advisory left out
    assert got[0]["file"] == "web/card.tsx" and got[0]["line"] == "12"
    run(state, md, tmp_path / "home")  # idempotent
    assert len(fix_now(state)) == 3


def test_existing_code_review_findings_are_kept(tmp_path: Path) -> None:
    state = tmp_path / "rev-1"
    state.mkdir()
    (state / "findings.json").write_text(
        json.dumps({"findings": [{"id": 4, "file": "a.py", "line": "1", "severity": "high", "body": "x"}]})
    )
    (state / "verdicts.json").write_text(json.dumps([{"id": 4, "verdict": "confirmed"}]))
    md = tmp_path / "findings.md"
    md.write_text(FINDINGS)
    run(state, md, tmp_path / "home")
    assert [f["id"] for f in fix_now(state)] == [4, "B2", "V1", "C1"]


def test_a_specialist_id_and_an_unlabelled_blocker_reach_the_fix_set(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / "findings.json").write_text(json.dumps({"findings": []}))
    (state / "verdicts.json").write_text("[]")
    md = tmp_path / "findings.md"
    md.write_text(
        "## Blocking\n\n- [ ] **RC-1** the card overflows at 320 - src/card.tsx:9\n"
        "- [ ] the footer clips at 320\n- [x] **B1** done\n\n## Advisory\n\n- [ ] **A1** rename\n"
    )
    run(state, md, tmp_path / "home")
    got = [f["id"] for f in fix_now(state)]
    assert got == ["RC-1", "U2"], got  # U<position among the open items>
