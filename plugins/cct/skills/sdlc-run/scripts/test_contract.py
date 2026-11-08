"""sdlc-run contract tests: the pieces that must agree with each other (templates, scripts,
SKILL.md, references) and a heuristic check of the skill's trigger description.

Layers 1-2 are structural: they read files, never run a model. Layer 3 is a HEURISTIC: it checks
that the description still carries the words people use, and that requests meant for other skills
carry none of them. It does not prove Claude routes correctly; a sandboxed end-to-end run
(a fresh repo, a scripted engineer, the real `/goal`) would, and is future work."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL / "templates"
BODY = (SKILL / "SKILL.md").read_text(encoding="utf-8")


def _frontmatter(path: Path) -> dict[str, str]:
    head = path.read_text(encoding="utf-8").split("---", 2)[1]
    return dict(re.findall(r"^([\w-]+):\s*(.*)$", head, re.M))


def _gate():
    sys.path.insert(0, str(TEMPLATES / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "verify_gate", TEMPLATES / "scripts/verify_gate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Layer 1: structure
@pytest.mark.parametrize(
    ("template", "needles"),
    [
        ("intent.md", ["class: null", "## Asks", "## Job stories", "status: draft"]),
        ("facts.md", ["## Goal", "## Acceptance criteria", "status: draft"]),
        (
            "plan.md",
            [
                "## Rules check",
                "### Justified violations",
                "## Where things go",
                "## Goal handover",
            ],
        ),
        ("milestone.md", ["## Features", "## Done", "## Outcome", "status: building"]),
    ],
)
def test_change_templates_keep_the_sections_the_gates_read(
    template: str, needles: list[str]
) -> None:
    text = (TEMPLATES / "change" / template).read_text(encoding="utf-8")
    assert not [n for n in needles if n not in text]
    assert (
        text.startswith("---\n")
        and "type:" in text.split("---", 2)[1]
        or template == "milestone.md"
    )


def test_every_path_skill_md_names_exists() -> None:
    paths = set(re.findall(r"`((?:references|templates|scripts)/[\w./-]+?)`", BODY))
    # scripts/verify_gate.py is the adopting repo's copy of templates/scripts/verify_gate.py
    here = lambda p: (SKILL / p).exists() or (TEMPLATES / p).exists()  # noqa: E731
    missing = sorted(p for p in paths if "<" not in p and "*" not in p and not here(p))
    assert not missing, missing


def test_every_reference_file_is_listed_in_skill_md() -> None:
    unlisted = [
        p.name for p in (SKILL / "references").glob("*.md") if f"references/{p.name}" not in BODY
    ]
    assert not unlisted, unlisted


def test_skill_version_is_the_changelogs_newest() -> None:
    newest = re.search(
        r"^## (\d+\.\d+\.\d+)", (SKILL / "references/changelog.md").read_text(), re.M
    )
    assert newest and f"version: {newest[1]}" in BODY


def test_every_blocked_reason_is_documented_in_skill_md() -> None:
    undocumented = sorted(r for r in _gate().REASONS if f"`{r}`" not in BODY)
    assert not undocumented, undocumented


def test_every_hook_template_is_registered_by_adopt() -> None:
    adopt = (SKILL / "scripts/adopt.py").read_text(encoding="utf-8")
    hooks = [p.name for p in (TEMPLATES / "hooks").glob("*.sh") if p.name != "sdlc-config.sh"]
    assert not [h for h in hooks if f'"{h}"' not in adopt]


def test_goal_templates_name_the_gate_script_they_run() -> None:
    for name in ("run", "feature", "milestone"):
        assert "verify_gate.py" in (TEMPLATES / "goal" / f"{name}.txt").read_text(encoding="utf-8")


# Layer 2: the agents the stages call exist and are read-only where the stages say so
def test_agents_named_in_the_stages_exist() -> None:
    agents = SKILL.parents[1] / "agents"
    named = set(
        re.findall(r"cct:([\w-]+)` agent", (SKILL / "references/stages.md").read_text())
    )
    assert not [a for a in named if not (agents / f"{a}.md").exists()]
    assert "Edit" not in _frontmatter(agents / "review-code-reviewer.md")["tools"]


# Layer 3: trigger discrimination. HEURISTIC, see the module docstring.
DESCRIPTION = " ".join(BODY.split("description:", 1)[1].split("allowed-tools:", 1)[0].split())
TRIGGER_TERMS = [
    "feature",
    "bug fix",
    "refactor",
    "docs change",
    "chore",
    "hotfix",
    "milestone",
    "project",
    "run sdlc",
    "adopt sdlc",
    "sdlc status",
]
SHOULD_TRIGGER = [
    "I want to start a new feature for the pricing page",
    "continue the milestone we paused on Friday",
    "run sdlc on this ticket",
    "adopt sdlc in this repo",
    "sdlc status please",
    "how do we ship a hotfix here?",
    "there is a bug fix waiting, where do I begin",
    "plan a refactor of the billing module",
]
SHOULD_NOT_TRIGGER = [
    "review this pull request for security problems",
    "write a LinkedIn post about our new podcast",
    "query BigQuery for last month's revenue",
    "audit the accessibility of the checkout page",
    "rename this variable",
    "what does this regex match?",
]


def _hits(request: str) -> list[str]:
    return [t for t in TRIGGER_TERMS if t in request.lower()]


def test_the_description_still_carries_every_trigger_term() -> None:
    assert not [t for t in TRIGGER_TERMS if t not in DESCRIPTION.lower()]


@pytest.mark.parametrize("request_text", SHOULD_TRIGGER)
def test_requests_for_the_chain_hit_a_trigger_term(request_text: str) -> None:
    assert _hits(request_text)


@pytest.mark.parametrize("request_text", SHOULD_NOT_TRIGGER)
def test_requests_for_other_skills_hit_none(request_text: str) -> None:
    assert not _hits(request_text)
