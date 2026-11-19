"""Usage: pytest scripts/test_sdd_lint.py

verify_gate lint pins the id families per layout: R is a rule and V a finding in layout 4.
"""

from __future__ import annotations

from pathlib import Path

from test_sdd_wiring import ID, TASKS, base_repo, gate, v4


# ------------------------------------------------------------------ lint: R is a rule, V a finding


def test_lint_reads_the_three_documents_and_pins_r_and_v_per_layout(tmp_path: Path) -> None:
    repo = base_repo(tmp_path)
    c = v4(repo)
    (c / "findings.md").write_text("- [ ] **V2** a finding\n- [ ] **F1** not a family here\n")
    assert gate(repo, "lint", ID).returncode == 0
    (c / "tasks.md").write_text(TASKS + "\nT2 repeats what R1 says and V2 too, and F1.\n")
    r = gate(repo, "lint", ID)
    assert r.returncode == 1
    assert "id R1 outside brackets" in r.stdout and "id V2 outside brackets" in r.stdout
    assert "id F1 outside" not in r.stdout
