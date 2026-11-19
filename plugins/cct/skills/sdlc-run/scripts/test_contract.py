"""sdlc-run contract tests: the pieces that must agree with each other (templates, scripts,
SKILL.md, references) and a heuristic check of the skill's trigger description.

Layers 1-2 are structural: they read files, never run a model. Layer 3 is a HEURISTIC: it checks
that the description still carries the words people use, and that requests meant for other skills
carry none of them. It does not prove Claude routes correctly; a sandboxed end-to-end run
(a fresh repo, a scripted engineer, the real `/goal`) would, and is future work."""

from __future__ import annotations

import importlib.util
import re
import subprocess
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
        ("intent.md", ["## Asks", "## Job stories", "status: draft"]),
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


def test_goal_templates_name_the_status_command_and_the_plan_names_the_gate() -> None:
    for name in ("run", "feature", "milestone"):
        text = (TEMPLATES / "goal" / f"{name}.txt").read_text(encoding="utf-8")
        assert "python3 <STATUS> goal <ID>" in text
    plan = (TEMPLATES / "change" / "plan.md").read_text(encoding="utf-8")
    assert "verify_gate.py milestone {{CHANGE}}" in plan.split("## How to run")[1]
    assert "python3 <STATUS> goal {{CHANGE}}" in plan


# Layer 2: the agents the stages call exist and are read-only where the stages say so
def test_agents_named_in_the_stages_exist() -> None:
    agents = SKILL.parents[1] / "agents"
    named = set(re.findall(r"cct:([\w-]+)` agent", (SKILL / "references/stages.md").read_text()))
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


# Guard: verification entry points must share the owner contract, not a remote retry loop.
def test_local_first_contract_covers_failure_loop_and_names_no_local_gate() -> None:
    text = (SKILL / "references/local-first.md").read_text()
    for phrase in (
        'Never push to "see what CI says"',
        "Reproduce that test locally",
        "directly affected suite",
        "spec and its neighbours",
        "full suite once",
        "Never rerun a whole pipeline",
        "speculative",
        "required GitHub checks",
    ):
        assert phrase in text, phrase
    for gone in ("scripts/ci-local", "pre-push hook", "local-ci", "exact SHA", "Publication hook"):
        assert gone not in text, gone


@pytest.mark.parametrize(
    "relative",
    [
        "SKILL.md",
        "references/stages.md",
        "references/ci-blueprint.md",
        "templates/CLAUDE-section.md",
        "templates/docs-sdlc.md",
        "templates/change/plan.md",
        "../../agents/sdlc-feature-builder.md",
        "../../agents/review-fix-implementer.md",
        "../../agents/test-e2e-healer.md",
        "../../agents/test-e2e-generator.md",
        "../git-pr-run/SKILL.md",
        "../review-fix-run/SKILL.md",
        "../review-feedback-run/references/execution-tail.md",
        "../review-feedback-run/references/pr-finalize.md",
        "../test-flake-fix/SKILL.md",
        "../test-e2e-coverage-run/SKILL.md",
        "../test-e2e-policy/SKILL.md",
        "../test-e2e-setup/SKILL.md",
        "../../blueprint/local-first.md",
        "../../../../docs/sdlc-run.md",
    ],
)
def test_verification_entry_points_link_the_local_first_contract(relative: str) -> None:
    text = (SKILL / relative).read_text()
    assert "local-first.md" in text
    assert "No check, lint or test runs" not in text
    assert "no check, lint or test runs" not in text
    assert "make `check` the only required status" not in text


def test_decision4_is_advisory_no_workflow_or_gate_shipped() -> None:
    assert sorted(p.name for p in (TEMPLATES / "decision4").iterdir()) == [
        "AGENTS-section.md",
        "boundary-map.yaml",
    ]
    agents = (TEMPLATES / "decision4/AGENTS-section.md").read_text(encoding="utf-8")
    assert "Nothing blocks a merge on it" in agents
    assert "§" not in agents and "put-right" not in agents


def _blueprint_copies() -> list[tuple[Path, Path]]:
    """Every blueprint file that is a byte copy of a template, found by name."""
    names = {p.name: p for p in (TEMPLATES / "scripts").glob("*.py")}
    names["REVIEW.md"] = TEMPLATES / "REVIEW.md"
    root = SKILL.parents[1] / "blueprint"
    return [
        (p, names[p.name])
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name in names and p.parent.name in ("scripts", "web-nextjs-cloud-run")
    ]


def test_blueprint_copies_match_their_templates_F19() -> None:
    copies = _blueprint_copies()
    assert {p.name for p, _ in copies} >= {"verify_gate.py", "marks.py", "design_index.py"}
    stale = [str(p) for p, template in copies if p.read_bytes() != template.read_bytes()]
    assert not stale, f"refresh from templates/ with cp: {stale}"


# 3.20.1: the readiness rename (finding 4) and build QA without a loop (finding 10).
PLUGIN = SKILL.parents[1] / "skills"


def _read(*parts: str) -> str:
    return PLUGIN.joinpath(*parts).read_text(encoding="utf-8")


def test_every_reader_of_the_spec_verdict_takes_either_name_F4() -> None:
    for parts in (
        ("design-mockups-create", "SKILL.md"),
        ("ux-design-run", "references", "prototype.md"),
        ("ux-design-run", "SKILL.md"),
        ("ux-build-validate", "SKILL.md"),
        ("ux-build-validate", "references", "build.md"),
    ):
        text = _read(*parts)
        assert "readiness.md" in text and "validation.md" in text, parts


def test_the_writer_writes_readiness_with_its_own_type_and_the_changelog_never_asks_for_git_mv_F4() -> None:
    spec = _read("ux-spec-validate", "references", "spec.md")
    assert "Write `<spec>/readiness.md`." in spec and "type: readiness" in spec
    assert "type: validation" not in spec
    changelog = (SKILL / "references" / "changelog.md").read_text(encoding="utf-8")
    assert "git mv" not in changelog and "renaming it is optional" in changelog


def test_the_reading_map_names_a_legacy_verdict_file_as_written_F4(tmp_path: Path) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import change_docs

    (tmp_path / "spec").mkdir()
    (tmp_path / "spec" / "validation.md").write_text("verdict: ready\n")
    assert "[spec/validation.md](spec/validation.md)" in change_docs.readme(tmp_path, "2/7 UX plan")
    assert "spec/validation.md" not in change_docs.others(tmp_path)
    (tmp_path / "spec" / "readiness.md").write_text("verdict: ready\n")  # a new one wins
    assert "[spec/readiness.md](spec/readiness.md)" in change_docs.readme(tmp_path, "2/7 UX plan")


def test_build_qa_resolves_size_and_skips_before_it_asks_for_readiness_F10() -> None:
    body = _read("ux-build-validate", "SKILL.md")
    steps = body.split("## Read first", 1)[1].split("## Ask once", 1)[0]
    assert steps.index("size and skips") < steps.index("approved `readiness.md`")
    assert "authorises this QA" in steps and "never loop back" in steps
    assert "authorises the run" in _read("ux-build-validate", "references", "build.md")


# 3.20.2: round-2 review (finding 4, M6).
SKILLS = SKILL.parent


def test_the_readiness_writer_keeps_an_older_hooks_validation_md_current_F4() -> None:
    """adopt --upgrade leaves an old chain-gate.sh in place; it reads only spec/validation.md, so
    the writer mirrors its verdict there (no stale accept, no rejected fresh approval)."""
    text = (SKILLS / "ux-spec-validate/references/spec.md").read_text(encoding="utf-8")
    mirror = text.split("## Output Template", 1)[1].split("```markdown", 1)[0]
    assert "<spec>/validation.md" in mirror and "same content" in mirror
    assert "readiness.md" in mirror and "every write" in mirror


def test_build_qa_waives_only_the_files_the_size_preset_skips_M6_C10() -> None:
    """chain.md: S skips brief, ia and interaction; M skips ia; L skips none. Build QA waives a
    file only for a size that skips it: for size L a missing interaction.md fails the QA, and no
    check is made conditional on the file existing."""
    chain = (SKILL / "references/chain.md").read_text(encoding="utf-8")
    assert re.search(r"\| `S` \|[^\n]*`brief`, `ia`, `interaction`", chain)
    assert re.search(r"\| `M` \|[^\n]*`ia`, reason", chain) and "| `L` | a new screen, flow or feature | none |" in chain
    build = (SKILLS / "ux-build-validate/references/build.md").read_text(encoding="utf-8")
    inputs = build.split("## Steps", 1)[0]
    # the owner's record (`skips`) decides; the size is only the default for a record without it
    assert "`decisions.json` `skips`" in inputs and "exactly when `skips` lists it" in inputs
    assert "size S skips all three, size M skips `ia`, size L skips none" in inputs
    assert "A file missing for an activity" in inputs and "`verdict: fail`" in inputs
    for line in build.splitlines():
        if re.search(r"ia\.md|interaction\.md", line) and not line.startswith("- `<spec>/screens.md`"):
            assert not re.search(r"\bexists?\b", line, re.I), f"a check conditional on the file existing: {line}"


# 3.20.5: pass records were withdrawn; a pass is the gate's report in the checkout.
def test_no_shipped_script_or_hook_reads_or_writes_receipts() -> None:
    shipped = [
        p
        for root in (SKILL / "scripts", SKILL / "templates", SKILL.parents[1] / "blueprint")
        for p in root.rglob("*")
        if p.is_file() and p.suffix in {".py", ".sh"} and "__pycache__" not in p.parts and not p.name.startswith("test_")
    ]
    assert len(shipped) > 10
    assert not [str(p) for p in shipped if "receipts/" in p.read_text(encoding="utf-8")]


def test_the_gate_and_the_hook_number_a_milestone_branch_the_same_way_3_20_5(tmp_path: Path) -> None:
    sys.path[:0] = [str(SKILL / "templates" / "scripts"), str(SKILL / "templates" / "hooks")]
    import pass_proof
    import verify_gate

    change = tmp_path / "2026-01-01-ABC-1-big-thing"
    change.mkdir()
    (change / "decisions.json").write_text('{"milestone": {"slug": "big-thing"}}')
    for prefix in ("milestone/", "ms/"):
        cfg = {"milestones": {"branchPrefix": prefix}}
        for branch in (f"{prefix}big-thing", f"{prefix}big-thing-2", f"{prefix}big-thing-x", f"{prefix}other-3", "main", ""):
            assert verify_gate.milestone_number(change, cfg, branch) == pass_proof.milestone_of(branch, prefix, "big-thing"), branch
    assert pass_proof.milestone_of("milestone/big-thing", "milestone/", "big-thing") == 1
    assert pass_proof.milestone_of("milestone/big-thing-7", "milestone/", "big-thing") == 7
    assert pass_proof.milestone_of("ms/big-thing-7", "milestone/", "big-thing") is None


def test_the_readme_never_links_a_gitignored_path(tmp_path: Path) -> None:
    import change_docs

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("verify/\n")
    (tmp_path / "verify").mkdir()
    (tmp_path / "verify" / "report.json").write_text("{}")
    (tmp_path / "asks").mkdir()
    (tmp_path / "asks" / "a.md").write_text("x")
    text = change_docs.readme(tmp_path, "5/7 Build")
    assert "](verify/)" not in text and "(verify/)" not in text
    assert "verify/" in text  # still named, as plain text
    assert "[asks/](asks/)" in text  # a tracked folder is still linked


def test_the_readiness_writer_also_checks_the_installed_guardrail_test() -> None:
    """A repo that kept its old guardrail test still requires validation.md in CI: the mirror
    decision reads the hook and the test."""
    spec = (SKILL.parent / "ux-spec-validate/references/spec.md").read_text()
    mirror = " ".join(spec.split("**Mirror it for an older hook.**", 1)[1].split("```markdown", 1)[0].split())
    assert "tests/test_sdlc.py" in mirror and "tests/sdlc.test.ts" in mirror
    assert "guardrail test" in mirror


def test_stage_6_uses_the_local_project_ref_in_local_mode_and_names_every_id_form() -> None:
    stages = " ".join((SKILL / "references/stages.md").read_text().split())
    assert "the local `project/<slug>` and both local reviews and the gate's `{base}` use it" in stages
    assert "`RC-1`" in stages and "`U<position>`" in stages


def test_build_qa_writes_qa_md_for_a_visual_change_with_no_spec_folder() -> None:
    """The gate requires spec/qa.md for any visual change; its producer must not stop before writing it."""
    text = " ".join((SKILL.parent / "ux-build-validate/SKILL.md").read_text().split())
    assert "create `<change folder>/spec/` holding only `qa.md`" in text
    assert "a `Build commit` column" in " ".join((SKILL.parent / "ux-build-validate/references/build.md").read_text().split()) or "Build commit" in (SKILL.parent / "ux-build-validate/references/build.md").read_text()
