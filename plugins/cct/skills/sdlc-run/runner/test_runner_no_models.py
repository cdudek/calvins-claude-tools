"""Models are named only in the kickoff: never in the 4.0 skill, runner, agents, hooks or docs page."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CCT = HERE.parents[2]
NAMES = re.compile(r"\b(opus|sonnet|haiku|fable)\b|\bclaude-(opus|sonnet|haiku)", re.I)


def test_no_model_names_in_the_4_0_surface():
    files = [f for f in HERE.glob("*.py") if not f.name.startswith("test_")]
    files += [HERE.parent / "SKILL.md", CCT / "agents/sdlc-task-builder.md", CCT / "agents/sdlc-task-verifier.md",
              CCT / "hooks/sdlc-records-guard.py", CCT.parents[1] / "docs/sdlc-run.md"]
    hits = [f"{f.name}: {m.group(0)}" for f in files for m in NAMES.finditer(f.read_text())]
    assert hits == []
    assert "model:" not in (CCT / "agents/sdlc-task-builder.md").read_text().split("---")[1]
