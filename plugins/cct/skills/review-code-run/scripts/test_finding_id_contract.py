"""Guards the one invariant behind the `#N` renumbering bug: every stage that names a
finding in prose must print its persisted `findings.json` id as `F<id>`, never a
positional index. The bug was pure prose drift across the shared report contracts, so
the regression guard is a prose check — each assertion below fails on a revert to the
form the bug actually took.

Run: pytest plugins/cct/skills/review-code-run/scripts/test_finding_id_contract.py
"""

import re
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[3]

# Every file that renders or specifies a report naming persisted findings.
ID_CONTRACT_FILES = [
    "skills/role-review-vocabulary/SKILL.md",
    "skills/review-code-run/references/finding-format.md",
    "skills/review-code-run/references/report-sections.md",
    "skills/role-code-analysis/references/synthesize.md",
    "agents/review-fixset-triager.md",
    "skills/review-fix-run/SKILL.md",
    "skills/review-feedback-run/references/execution-tail.md",
    "agents/review-feedback-runner.md",
]

# `### 1.` / `### 2.` detailed-finding headings — the positional form that made the
# same `#N` mean different findings in consecutive stages.
POSITIONAL_HEADING = re.compile(r"^#{2,4}\s+\d+\.\s", re.MULTILINE)

# `#1`, `#3` used as a finding reference. The observed report wrote
# `fix_now = #3, #4; recheck = #1, #2` — two schemes, one report.
BARE_HASH_REF = re.compile(r"(?<![\w`#])#\d+\b")

# Table header of a findings table: the identity column must be `ID`, not `#`.
POSITIONAL_TABLE_HEADER = re.compile(r"^\|\s*#\s*\|", re.MULTILINE)


def read(rel: str) -> str:
    return (PLUGIN / rel).read_text(encoding="utf-8")


@pytest.mark.parametrize("rel", ID_CONTRACT_FILES)
def test_states_the_id_is_the_identifier(rel):
    assert "F<id>" in read(rel), f"{rel} names findings in prose but never states the `F<id>` form"


@pytest.mark.parametrize(
    "rel",
    [
        "skills/review-code-run/references/finding-format.md",
        "skills/role-code-analysis/references/synthesize.md",
    ],
)
def test_no_positional_finding_headings(rel):
    assert not POSITIONAL_HEADING.search(read(rel)), (
        f"{rel} shows a positional `### N.` finding heading — headings carry `F<id>`"
    )


@pytest.mark.parametrize(
    "rel",
    [
        "skills/review-code-run/references/finding-format.md",
        "skills/role-code-analysis/references/synthesize.md",
    ],
)
def test_findings_table_identity_column_is_id(rel):
    text = read(rel)
    assert "| ID |" in text, f"{rel} has no `| ID |` findings-table column"
    assert not POSITIONAL_TABLE_HEADER.search(text), (
        f"{rel} still heads a findings table with a positional `#` column"
    )


def test_bucket_listings_use_ids_not_positions():
    """The reported defect verbatim: the validation stage numbered each bucket 1..N."""
    text = read("agents/review-fixset-triager.md")
    offenders = [m.group(0) for m in BARE_HASH_REF.finditer(text)]
    assert not offenders, (
        f"extra-validation-runner.md references findings positionally as {offenders} — "
        "bucket listings print `F<id>` (the `#<id>` wire label belongs in backticks)"
    )
    assert "fix_now = F" in text, "no worked example of an id-based bucket listing"


def test_posting_boundary_carries_the_id():
    """`posting-findings.sh` emits `id`; every field list downstream must keep it."""
    for rel in [
        "skills/review-code-run/references/posting-pipeline.md",
        "skills/review-code-run/references/reconcile-threads.md",
    ]:
        text = read(rel)
        assert "`id`" in text, f"{rel} drops `id` from the postable-finding shape"


def test_validator_wire_label_stays_numeric():
    """The validator echoes the id back as a number; `F<id>` there breaks the verdict join."""
    text = read("skills/review-code-run/references/validate-agent.md")
    assert "FINDING #<id>" in text
    assert "FINDING F<id>" not in text


def test_claude_md_bullet_matches_the_real_file_list():
    """The docs must describe what this script actually guards.

    `validate-agent.md` is guarded the OPPOSITE way (it must stay numeric), so
    listing it as `F<id>`-guarded is backwards; and three genuinely guarded files
    were omitted.
    """
    doc = read("skills/review-code-run/CLAUDE.md")
    bullet = doc.split("test_finding_id_contract.py", 1)[1].split("\n\n", 1)[0]

    # `validate-agent.md` is guarded the OPPOSITE way, so it may only be named in the
    # part of the bullet that says so — never in the F<id> file list.
    assert "(b)" in bullet, "the bullet no longer separates the two opposite guarantees"
    f_id_part, inverse_part = bullet.split("(b)", 1)
    assert "validate-agent" not in f_id_part, (
        "validate-agent.md is listed among the F<id>-guarded files; its guard enforces "
        "the numeric #<id> wire form and fails if it adopts F<id>"
    )
    assert "validate-agent" in inverse_part, "the inverse guarantee no longer names its file"

    for rel in ID_CONTRACT_FILES:
        leaf = rel.rsplit("/", 1)[-1]
        needle = "/".join(rel.rsplit("/", 2)[-2:]) if leaf == "SKILL.md" else leaf
        assert needle in f_id_part, f"the bullet omits {rel}, which IS in ID_CONTRACT_FILES"
