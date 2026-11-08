"""Guard: the two phases that spawn per-item agents stay capped.

`test-behavior-writer` and `review-fix-implementer` are the most expensive agents in
the review→fix pipeline — each pays a full context load and runs the project's
test suite. Both were spawned as "one parallel batch" with no cap, so the
fan-out scaled with the fix-set size while review-code-run capped its far cheaper
read-only validators at ~5.

Run: pytest plugins/cct/skills/review-feedback-run/scripts/test_fanout_caps.py
"""

import re
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[3]
EXECUTE_PHASES = PLUGIN / "skills/review-feedback-run/references/execute-phases.md"


@pytest.fixture(scope="module")
def phases() -> str:
    return EXECUTE_PHASES.read_text(encoding="utf-8")


CAP = re.compile(r"~(\d+)[ -]concurrent")


def caps(text: str) -> set[int]:
    """Every `~N concurrent` cap stated in this text."""
    return {int(n) for n in CAP.findall(text)}


@pytest.mark.parametrize(
    "phase, agent", [("Phase RED", "test-behavior-writer"), ("Phase GREEN", "review-fix-implementer")]
)
def test_phase_spawn_is_capped(phases: str, phase: str, agent: str):
    heading = f"## {phase}"
    assert heading in phases, f"{phase} section missing"
    section = phases.split(heading, 1)[1].split("\n## ", 1)[0]
    assert agent in section, f"{phase} no longer spawns {agent}"
    assert caps(section), (
        f"{phase} spawns {agent} without a concurrency cap — an N-item fix set "
        f"would launch N sonnet agents and N test-suite runs at once"
    )


def test_cap_never_exceeds_the_validator_fan_out_cap(phases: str):
    """These agents cost more per item than a read-only validator, never less.

    Compared by MAGNITUDE, not by set membership: `{10} <= {5, 10}` is a true
    subset relation and would wave through a cap that genuinely drifted up, while
    a compliant lower cap like ~3 would fail it. The value itself is deliberately
    not pinned here — `review-feedback-run/CLAUDE.md` allows raising both caps
    together, and this test is what enforces the "together".
    """
    validate_agent = (PLUGIN / "skills/review-code-run/references/validate-agent.md").read_text(
        encoding="utf-8"
    )
    reference = caps(validate_agent)
    here = caps(phases)
    assert reference, "review-code-run's validator concurrency cap is no longer stated"
    assert here, "execute-phases states no concurrency cap"
    assert max(here) <= min(reference), (
        f"phase fan-out cap ~{max(here)} exceeds the validator cap ~{min(reference)} — "
        f"these agents each pay a full context load and run the test suite, so their "
        f"pool may never be larger than the validators'"
    )
