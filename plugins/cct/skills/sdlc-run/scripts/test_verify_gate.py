"""verify_gate.py: the sentinel line, the criteria lock, the breaker, the stdout cap, the lint.
And the two /goal templates, which must stay short enough to read in one go."""

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

SKILL = Path(__file__).resolve().parents[1]
GATE = SKILL / "templates" / "scripts" / "verify_gate.py"
ID = "2026-10-09-trial"
CONVERGED = "## Converge\n\nConverged: round 1\n"


def _env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
        env=_env(),
        capture_output=True,
    )


def _repo(tmp_path: Path, feature: list) -> Path:
    repo = tmp_path / "repo"
    change = repo / "changes" / ID
    change.mkdir(parents=True)
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"feature": feature}}))
    (repo / ".gitignore").write_text("/changes/*/verify/\n")
    (change / "facts.md").write_text("---\nstatus: approved\n---\n\n- [ ] **F1** It works.\n")
    (change / "done.json").write_text('{"facts": ["F1"]}\n')
    (change / "decisions.json").write_text('{"size": "S"}\n')  # a current-format change has one
    # on a milestone branch the plan's Milestones rows say which facts each milestone proves
    (change / "plan.md").write_text(
        "## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n"
        "| M1 a | F1 | none |\n| M2 b | F1 | M1 |\n"
    )
    # a milestone passes only with a met row and evidence for every approved fact
    (change / "validation.md").write_text("| F1 | It works | ran | tests/x.py::test_f1 | met |\n")
    (change / "findings.md").write_text(CONVERGED)  # a current-format close needs its Converged line
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "init")
    return repo


def _with_design(repo: Path) -> None:
    """From 3.26.0 a change with a visual source lists the boards of it: one board, mapped by the first screen."""
    change = repo / "changes" / ID
    try:
        decisions = json.loads((change / "decisions.json").read_text())
        rows = json.loads((change / "screens.json").read_text())
    except (OSError, ValueError):
        return
    entries = rows.get("entries") if isinstance(rows, dict) else rows
    if not decisions.get("visualSource") or (change / "design.json").exists() or not isinstance(entries, list) or not entries:
        return
    entries[0].setdefault("design", ["b1"])
    (change / "screens.json").write_text(json.dumps(rows))
    (change / "design.json").write_text(json.dumps({"source": "asks", "boards": [{"id": "b1", "name": "Board one"}]}))
    _confirm_inventory(repo)


def _confirm_inventory(repo: Path) -> None:
    """The owner's answer to the inventory dialog of the design.json as it stands."""
    from capture import inventory_id

    import test_capture as tc

    design = json.loads((repo / "changes" / ID / "design.json").read_text())
    tc.owner_answers(repo, inventory_id(design), label="Confirm inventory", change_id=ID, options=("Confirm inventory", "Hold"))


def _gate(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    if args[:1] == ("approve",):
        _with_design(repo)
    return subprocess.run(
        [sys.executable, str(GATE), *args], cwd=repo, capture_output=True, text=True,
        env={**_env(), "HOME": str(repo.parent / "home")},  # where the owner's answers are read
    )  # fmt: skip


def _approve(repo: Path) -> None:
    assert _gate(repo, "approve", ID).returncode == 0
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "approved")


def _approve_legacy(repo: Path) -> None:
    """A change approved before 3.25.0 (no `"visual": "app"`): the six-layer path keeps working for it.
    Approve with a placeholder screens.json, then rewrite the lock the way 3.24 wrote it."""
    change = repo / "changes" / ID
    (change / "screens.json").write_text('[{"id": "x", "route": "/x", "viewport": [1, 1], "fixture": "f"}]')
    assert _gate(repo, "approve", ID).returncode == 0
    (change / "screens.json").unlink()
    (change / "design.json").unlink(missing_ok=True)
    lock = json.loads((change / "lock.json").read_text())
    lock.pop("visual"), lock.pop("design", None), lock["criteria"].pop("screens.json"), lock["criteria"].pop("design.json", None)
    lock["screens"] = "required"
    (change / "lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "approved before 3.25.0")


def _last(r: subprocess.CompletedProcess[str]) -> str:
    return r.stdout.strip().splitlines()[-1]


def test_pass_names_the_commit_and_writes_the_report(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true", {"name": "unit", "run": "echo {id}"}])
    _approve(repo)
    r = _gate(repo, "feature", ID)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    assert r.returncode == 0 and _last(r) == f"VERIFY PASS feature {ID} {head}"
    report = json.loads((repo / "changes" / ID / "verify" / "report.json").read_text())
    assert [c["status"] for c in report["checks"]] == ["pass", "pass"]
    assert report["checks"][1]["run"] == f"echo {ID}"
    assert (repo / "changes" / ID / "verify" / "report.md").exists()


def test_without_approval_it_blocks(tmp_path: Path) -> None:
    r = _gate(_repo(tmp_path, ["true"]), "feature", ID)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=not-approved"


@pytest.mark.parametrize("target", ["facts.md", "done.json", "sdlc.json"])
def test_an_edit_to_the_locked_criteria_blocks(tmp_path: Path, target: str) -> None:
    repo = _repo(tmp_path, ["true"])
    _approve(repo)
    if target == "sdlc.json":
        (repo / target).write_text(json.dumps({"checks": {"feature": []}}))
    else:
        path = repo / "changes" / ID / target
        path.write_text(path.read_text() + "\n- [ ] **F2** Weaker.\n")
    _git(repo, "commit", "-qam", "moved the goalposts")
    r = _gate(repo, "feature", ID)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=protected-path"


def test_a_failure_fails_and_the_same_failure_three_times_blocks(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [{"name": "unit", "run": "echo 'boom in 12ms'; exit 1"}, "true"])
    _approve(repo)
    first = _gate(repo, "feature", ID)
    assert first.returncode == 1 and _last(first) == f"VERIFY FAIL feature {ID} check=unit"
    assert _gate(repo, "feature", ID).returncode == 1
    third = _gate(repo, "feature", ID)
    assert third.returncode == 3 and _last(third) == "VERIFY BLOCKED reason=no-progress"


def _commit_n(repo: Path, n: int) -> None:
    (repo / "n").write_text(str(n))
    _git(repo, "add", "n")
    _git(repo, "commit", "-qm", f"n{n}")


def test_a_different_failure_resets_the_breaker(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["sh -c 'cat n 2>/dev/null; exit 1'"])
    _approve(repo)
    for i in range(2):
        _commit_n(repo, i)
        assert _gate(repo, "feature", ID).returncode == 1


def test_three_failed_attempts_block_whatever_the_failures(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["sh -c 'cat n 2>/dev/null; exit 1'"])
    _approve(repo)
    for i in range(2):
        _commit_n(repo, i)
        assert _gate(repo, "feature", ID).returncode == 1
    _commit_n(repo, 2)
    r = _gate(repo, "feature", ID)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=attempts"
    assert (
        "VERIFY BLOCKED reason=attempts"
        in (repo / "changes" / ID / "verify" / "report.md").read_text()
    )


def test_a_pass_resets_the_attempt_count(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["sh -c 'cat n; test $(cat n) -ge 100'"])
    _approve(repo)
    for n, code in ((1, 1), (2, 1), (100, 0), (3, 1), (4, 1)):
        _commit_n(repo, n)
        assert _gate(repo, "feature", ID).returncode == code


def test_a_pass_on_the_same_tree_is_cached(tmp_path: Path) -> None:
    count = tmp_path / "count"
    repo = _repo(tmp_path, [f"echo x >> {count}"])
    _approve(repo)
    first = _gate(repo, "feature", ID)
    again = _gate(repo, "feature", ID)
    assert first.returncode == again.returncode == 0
    assert _last(again) == _last(first) and "ok (cached)" in again.stdout
    assert count.read_text().count("x") == 1
    report = json.loads((repo / "changes" / ID / "verify" / "report.json").read_text())
    assert report["checks"][0]["cached"] is True


def test_a_changed_tree_misses_the_cache(tmp_path: Path) -> None:
    count = tmp_path / "count"
    repo = _repo(tmp_path, [f"echo x >> {count}"])
    _approve(repo)
    _gate(repo, "feature", ID)
    _commit_n(repo, 1)
    r = _gate(repo, "feature", ID)
    assert "cached" not in r.stdout and count.read_text().count("x") == 2


@pytest.mark.parametrize(
    "rerun_exit,verdict", [(0, "did not reproduce (flaky)"), (1, "reproduced (real)")]
)
def test_a_failing_e2e_check_is_rerun_with_last_failed(
    tmp_path: Path, rerun_exit: int, verdict: str
) -> None:
    cmd = f"sh -c 'case \"$*\" in *--last-failed*) exit {rerun_exit};; esac; exit 1' x test:e2e"
    repo = _repo(tmp_path, [cmd])
    _approve(repo)
    r = _gate(repo, "feature", ID)
    assert r.returncode == 1 and _last(r) == f"VERIFY FAIL feature {ID} check=check-1"
    assert verdict in r.stdout
    report = json.loads((repo / "changes" / ID / "verify" / "report.json").read_text())
    assert report["checks"][0]["rerun"] == verdict


def test_a_check_can_block_with_its_own_reason(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["echo 'retry differed'; echo 'VERIFY BLOCKED reason=flaky'; exit 3"])
    _approve(repo)
    r = _gate(repo, "feature", ID)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=flaky"


def test_stdout_is_capped(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["seq 1 5000; exit 1"])
    _approve(repo)
    r = _gate(repo, "feature", ID)
    assert len(r.stdout.splitlines()) < 80 and "5000" in r.stdout and "\n1\n" not in r.stdout


def test_uncommitted_work_cannot_pass(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    _approve(repo)
    (repo / "src.py").write_text("x = 1\n")
    r = _gate(repo, "feature", ID)
    assert r.returncode == 1 and _last(r) == f"VERIFY FAIL feature {ID} check=uncommitted"


def test_no_checks_blocks_instead_of_passing_vacuously(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [])
    _approve(repo)
    r = _gate(repo, "milestone", ID)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env"


def test_lint_flags_long_sentences_and_open_questions(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    change = repo / "changes" / ID
    assert _gate(repo, "lint", ID).returncode == 0
    (change / "intent.md").write_text(
        "# Intent\n\n" + " ".join(["word"] * 30) + ".\n\n| a | " + "x " * 40 + "|\n"
    )
    (change / "plan.md").write_text("Short.\n[NEEDS CLARIFICATION: who?]\n")
    r = _gate(repo, "lint", ID)
    assert r.returncode == 1 and "intent.md: 30 words" in r.stdout
    assert "plan.md: an open [NEEDS CLARIFICATION]" in r.stdout
    assert _last(r) == f"LINT FAIL {ID} problems=2"


# Ids the change defines. An id that is defined nowhere is ordinary text ("Press F5", "before Q4").
DEFINED = "| # | What |\n|---|---|\n" + "".join(
    f"| {i} | defined |\n" for i in ("Q202", "B19", "F13", "F14", "Q7", "A1", "F1000")
)
GOOD_IDS = [
    "Designs win over today's app (Q202).",
    "The list stays sorted (F13, F14; rules SEC-2).",
    "Nothing blocks the build [see B19].",
    "- **Q1 (2026-11-18) When to lock the tests?** The default is one commit.",
    "- [ ] **F3** (A1) When a row is added, the list refreshes.",
    "Run `verify_gate.py` and read `F13` in the table.",
    "| F13 | a table row is data |",
    "Tag the test `@F13`.",
    "Never gate on HTTP 404 or SEC-2.",
    "Press F5 to refresh before Q4.",  # F5 and Q4 are defined nowhere in the change
    "Ticket F1001 stays out of scope.",
    "The list stays sorted (see\nF13 and Q202 for the rule).",  # a bracket across a line wrap
    "| 1 | Sort | F13, F14 | todo |",  # a cell of ids is structural
]
BAD_IDS = [
    ("Done per Q202.", "Q202"),
    ("B19 blocks the build.", "B19"),
    ("**B19 blocks the build.**", "B19"),
    ("- **B19 blocks the build.**", "B19"),
    ("We ship F13 first, then (A1) later.", "F13"),
    ("> Decided in Q7 and nowhere else.", "Q7"),
    ("Ticket F1000 is the reason.", "F1000"),
    ("(the rule)\nDone per Q202.", "Q202"),
    ("| 1 | Done per Q202 because it is simpler | todo |", "Q202"),
]


def test_lint_passes_an_id_in_brackets_and_flags_a_bare_one(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    (repo / "changes" / ID / "analyze.md").write_text(DEFINED)
    path = repo / "changes" / ID / "intent.md"
    path.write_text("# Intent\n\n" + "\n\n".join(GOOD_IDS) + "\n")
    r = _gate(repo, "lint", ID)
    assert r.returncode == 0, r.stdout
    for text, bare in BAD_IDS:
        path.write_text(f"# Intent\n\n{text}\n")
        r = _gate(repo, "lint", ID)
        assert r.returncode == 1 and f"intent.md: id {bare} outside brackets" in r.stdout, text
        assert _last(r) == f"LINT FAIL {ID} problems=1"


def test_lint_exempts_the_verbatim_words_column_of_the_asks_table_only(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    change = repo / "changes" / ID
    (change / "analyze.md").write_text(
        "| # | What |\n|---|---|\n| F3 | defined |\n| A3 | defined |\n"
    )
    path = change / "intent.md"
    asks = '## Asks\n\n| # | Words |\n|---|---|\n| A3 | "Fix F3 like last time" |\n'
    path.write_text("# Intent\n\n" + asks)
    r = _gate(repo, "lint", ID)
    assert r.returncode == 0, r.stdout
    path.write_text("# Intent\n\n" + asks + '\nThe owner said "Fix F3 like last time".\n')
    r = _gate(repo, "lint", ID)
    assert r.returncode == 1 and "intent.md: id F3 outside brackets" in r.stdout


@pytest.mark.parametrize("name", ["plan.md", "milestone.md", "questions.md", "pr-body.md"])
def test_lint_reads_every_owner_file_for_bare_ids_but_not_facts(tmp_path: Path, name: str) -> None:
    repo = _repo(tmp_path, ["true"])
    change = repo / "changes" / ID
    (change / "analyze.md").write_text(DEFINED)
    (change / "facts.md").write_text("- [ ] **F1** (A1) It works, see F13.\n")
    assert _gate(repo, "lint", ID).returncode == 0
    (change / name).write_text("Because of Q202 we wait.\n")
    r = _gate(repo, "lint", ID)
    assert r.returncode == 1 and f"{name}: id Q202 outside brackets" in r.stdout


BODY = "## What\n\n- **Requirement F13:** Filters stay readable.\n- **Proof (F14):** 12 passed.\n"


@pytest.mark.parametrize("via", ["file", "stdin"])
def test_lint_checks_the_pr_body_that_is_published(tmp_path: Path, via: str) -> None:
    """The body `gh pr create --body-file` gets lives outside the change folder."""
    repo = _repo(tmp_path, ["true"])
    (repo / "changes" / ID / "analyze.md").write_text(DEFINED)
    body = tmp_path / "proposed-pr-body.md"
    body.write_text(BODY)
    args = ["lint", ID, "--pr-body", str(body) if via == "file" else "-"]
    r = subprocess.run(
        [sys.executable, str(GATE), *args],
        cwd=repo,
        input=BODY,
        capture_output=True,
        text=True,
        env=_env(),
    )
    assert r.returncode == 1 and "pr-body: id F13 outside brackets" in r.stdout, r.stdout
    assert "F14" not in r.stdout
    assert _last(r) == f"LINT FAIL {ID} problems=1"
    body.write_text(BODY.replace("Requirement F13:", "Requirement (F13):"))
    r = subprocess.run(
        [sys.executable, str(GATE), *args],
        cwd=repo,
        input=body.read_text(),
        capture_output=True,
        text=True,
        env=_env(),
    )
    assert r.returncode == 0, r.stdout


def test_the_canonical_pr_body_example_passes_the_lint(tmp_path: Path) -> None:
    text = (SKILL / "references" / "pr-body.md").read_text()
    example = text.split("```markdown\n", 1)[1].split("\n```", 1)[0]
    repo = _repo(tmp_path, ["true"])
    (repo / "changes" / ID / "facts.md").write_text("- [ ] **F1** (A1) It works.\n")
    r = subprocess.run(
        [sys.executable, str(GATE), "lint", ID, "--pr-body", "-"],
        cwd=repo,
        input=example,
        capture_output=True,
        text=True,
        env=_env(),
    )
    assert r.returncode == 0, r.stdout


def test_approve_runs_the_lint_first_and_refuses_on_failure(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    change = repo / "changes" / ID
    (change / "intent.md").write_text("# Intent\n\n" + " ".join(["word"] * 30) + ".\n")
    r = _gate(repo, "approve", ID)
    assert r.returncode == 1 and "intent.md: 30 words" in r.stdout
    assert _last(r).startswith(f"APPROVE FAIL {ID}")
    assert not (change / "lock.json").exists()


@pytest.mark.parametrize("name", ["run", "project"])
def test_goal_templates_are_end_states_not_processes(name: str) -> None:
    """2026-11-11: a process in the condition cannot be satisfied after the merge, so it never clears."""
    text = (SKILL / "templates" / "goal" / f"{name}.txt").read_text()
    assert len(text) < 600, len(text)
    assert "python3 <STATUS> goal <ID>" in text and "DONE" in text and "BLOCKED" in text
    assert "<TURNS> turns" in text
    assert not [w for w in ("milestone/", "builder", "push") if w in text]


def test_skill_asks_through_dialogs_with_a_recommendation() -> None:
    """The owner's rule (2026-10-09): dialogs, plain words, always a recommendation with a reason."""
    text = (SKILL / "SKILL.md").read_text()
    head = text.split("---", 2)[1]
    assert "AskUserQuestion" in head, "allowed-tools must grant AskUserQuestion"
    assert "## Talking to the engineer" in text and "(Recommended)" in text


def test_the_plan_template_keeps_the_process_the_goal_dropped() -> None:
    """The process left the condition, not the run: How to run carries it, the handover starts it."""
    plan = (SKILL / "templates" / "change" / "plan.md").read_text()
    run = " ".join(plan.split("## How to run")[1].split("## Goal handover")[0].split())
    handover = plan.split("## Goal handover")[1].split("## Revisions")[0]
    assert "cct:ux-assessment-run" in run and "before arming auto-merge" in run  # 2026-10-12 rule
    assert "right before each close" in run and "re-locks" in run and "supervisor's worktree" in run
    assert "`## How to run`" in handover and "/goal `python3 <STATUS> goal" in handover


@pytest.mark.parametrize("scope", ["feature", "milestone"])
def test_visual_failure_is_a_failed_gate_check_and_cannot_reuse_earlier_pass(
    tmp_path: Path,
    scope: str,
) -> None:
    repo = _repo(tmp_path, ["true"])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {scope: ["true"]}}))
    _approve(repo)
    assert _gate(repo, scope, ID).returncode == 0  # preliminary build/test gate
    checker = SKILL.parent / "ux-assessment-run/scripts/visual-check.py"
    run = tmp_path / "visual run"
    run.mkdir()
    shot = run / "screen.png"
    shot.write_bytes(b"capture")
    args = (scope, ID, "--visual-check", str(checker), "--visual-run", str(run))
    result = _gate(repo, *args)
    assert result.returncode == 1
    assert _last(result) == f"VERIFY FAIL {scope} {ID} check=ux-visual-1"
    report = repo / "changes" / ID / "verify" / "report.json"
    check = json.loads(report.read_text())["checks"][-1]
    assert check["name"] == "ux-visual-1" and check["status"] == "fail"
    assert "screen.png: missing screenshot row" in check["tail"]
    assert "ux-visual-1" in report.with_suffix(".md").read_text()

    (run / "visual.json").write_text(
        json.dumps(
            {
                "screenshots": [
                    {
                        "file": "screen.png",
                        "screen_state": "default",
                        "width": 1280,
                        "opened_with": "Read call-123",
                        "sha256": hashlib.sha256(shot.read_bytes()).hexdigest(),
                        "observations": "Aligned labels and legible controls.",
                        "verdict": "compliant",
                        "issues": [],
                    }
                ]
            }
        )
    )
    assert _gate(repo, *args).returncode == 0
    second = tmp_path / "another run"
    second.mkdir()
    result = _gate(repo, *args, "--visual-run", str(second))
    assert result.returncode == 1
    assert _last(result) == f"VERIFY FAIL {scope} {ID} check=ux-visual-2"


@pytest.mark.parametrize(
    "flags",
    [("--visual-run", "run"), ("--visual-check", "checker")],
)
def test_visual_gate_rejects_half_configured_flags(tmp_path: Path, flags: tuple) -> None:
    repo = _repo(tmp_path, ["true"])
    result = _gate(repo, "feature", ID, *flags)
    assert result.returncode == 2 and "must be supplied together" in result.stderr


@pytest.mark.parametrize("trigger", ["session", "ledger", "reference"])
def test_owner_marks_is_automatic_at_milestone_only(tmp_path: Path, trigger: str) -> None:
    repo = _repo(tmp_path, ["true"])
    cfg = {"checks": {"feature": ["true"], "milestone": ["true"]}, "ux": "off"}
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    change = repo / "changes" / ID
    if trigger == "session":
        session = change / "asks/2026-09-26"
        session.mkdir(parents=True)
        (session / "session.md").write_text(
            "# 2026-09-26 08.43\n\n## 001 · 16:11\n\n"
            "![Screenshot 1](img/001.png)\n\n1. Add spacing.\n"
        )
    elif trigger == "reference":
        (change / "asks").mkdir(parents=True)
        (change / "asks/wireframe.png").write_bytes(b"reference")
        (change / "marks.json").write_text('{"rows": []}')
    else:
        (change / "marks.json").write_text("{")
    _approve(repo)
    legacy = json.loads((change / "lock.json").read_text())
    del legacy["manifest"]  # an approval before 3.21.0: no capture manifest is required of it
    (change / "lock.json").write_text(json.dumps(legacy))
    _git(repo, "commit", "-qam", "an older lock")
    lock = (change / "lock.json").read_bytes()
    assert _gate(repo, "feature", ID).returncode == 0
    result = _gate(repo, "milestone", ID)
    assert result.returncode == 1
    assert _last(result) == f"VERIFY FAIL milestone {ID} check=owner-marks"
    report = json.loads((change / "verify/report.json").read_text())
    assert [c["name"] for c in report["checks"]] == ["owner-marks"]  # evidence first, 3.21.0
    assert "owner-marks" in (change / "verify/report.md").read_text()
    assert (change / "lock.json").read_bytes() == lock

    # Resolve the evidence without changing configuration or approval.
    if trigger == "ledger":
        (change / "marks.json").write_text('{"rows": []}')
    else:
        marks = GATE.with_name("marks.py")
        proc = subprocess.run(
            [sys.executable, str(marks), "init", ID], cwd=repo, capture_output=True
        )
        assert proc.returncode == 0
        data = json.loads((change / "marks.json").read_text())
        shot = change / "verify/shots/fresh.png"
        shot.parent.mkdir(parents=True)
        shot.write_bytes(b"fresh")
        for row in data["rows"]:
            row.update(
                expected="Spacing is visible.",
                shot="verify/shots/fresh.png",
                status="match" if row["kind"] == "reference" else "fixed",
            )
            if row["kind"] == "note":
                row["test"] = "@F1"
        (repo / "tests").mkdir(exist_ok=True)
        (repo / "tests/marks.test.ts").write_text("test('spacing @F1', () => {})")
        (change / "marks.json").write_text(json.dumps(data))
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "resolve marks")
    assert _gate(repo, "milestone", ID).returncode == 0
    assert (change / "lock.json").read_bytes() == lock


def test_unrelated_session_does_not_enable_owner_marks(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"milestone": ["true"]}}))
    asks = repo / "changes" / ID / "asks"
    asks.mkdir()
    (asks / "session.md").write_text("# Planning session\n\n## Notes\n\n1. Discuss it.\n")
    _approve(repo)
    assert _gate(repo, "milestone", ID).returncode == 0
    report = json.loads((asks.parent / "verify/report.json").read_text())
    assert [c["name"] for c in report["checks"]] == ["check-1"]


def _warn_for(tmp_path: Path, stamp: str | None, kit: str) -> tuple[str, str]:
    repo = _repo(tmp_path, ["true"])
    cfg = json.loads((repo / "sdlc.json").read_text())
    if stamp:
        cfg["sdlcVersion"] = stamp
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "stamp", "--allow-empty")
    _approve(repo)
    r = subprocess.run(
        [sys.executable, str(GATE), "feature", ID],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**_env(), "SDLC_KIT_VERSION": kit},
    )
    warns = [ln for ln in r.stdout.splitlines() if ln.startswith("WARN")]
    return (warns[0] if warns else ""), _last(r)


@pytest.mark.parametrize(
    ("stamp", "kit", "expect"),
    [
        (None, "3.3.0", "runs sdlc-run none; the kit is 3.3.0"),
        ("3.2.0", "3.3.0", "runs sdlc-run 3.2.0; the kit is 3.3.0"),
        ("3.3.0", "3.3.0", ""),
        ("3.4.0", "3.3.0", "newer than the installed kit 3.3.0"),
    ],
)
def test_a_stale_stamp_warns_and_never_changes_the_verdict(
    tmp_path: Path, stamp: str | None, kit: str, expect: str
) -> None:
    warn, last = _warn_for(tmp_path, stamp, kit)
    assert last.startswith("VERIFY PASS feature")
    assert (expect in warn) if expect else (warn == "")


def test_milestone_gate_fails_until_the_parent_is_merged_in(tmp_path: Path) -> None:
    # After milestone n merges, n+1 must take the new parent in locally before its gate passes.
    repo = _repo(tmp_path, ["true"])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(
        json.dumps({**cfg, "defaultBranch": "master", "checks": {"milestone": ["true"]}})
    )
    _git(repo, "commit", "-qam", "milestone checks")
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "master", str(origin))
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-q", "origin", "master")
    _git(repo, "checkout", "-qb", "milestone/trial-2")
    _approve(repo)
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(origin), str(other))
    (other / "merged.txt").write_text("milestone 1\n")
    _git(other, "add", ".")
    _git(other, "commit", "-qm", "milestone 1 merged")
    _git(other, "push", "-q", "origin", "master")
    r = _gate(repo, "milestone", ID)
    assert r.returncode == 1 and _last(r) == f"VERIFY FAIL milestone {ID} check=parent-sync"
    assert "git merge origin/master" in r.stdout
    _git(repo, "merge", "-q", "--no-edit", "origin/master")
    assert _last(_gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")


@pytest.mark.parametrize(
    "check",
    [
        "git -c user.name=t -c user.email=t@t commit --allow-empty -qm merged-mid-gate",
        "echo stray > stray.txt",
    ],
)
def test_a_head_that_moves_during_the_checks_fails(tmp_path: Path, check: str) -> None:
    # 3.7.0: a PASS names one frozen head. A merge or an edit while the checks run means they
    # tested something other than the commit the line would name.
    repo = _repo(tmp_path, ["true", check])
    _approve(repo)
    r = _gate(repo, "feature", ID)
    assert r.returncode == 1 and _last(r) == f"VERIFY FAIL feature {ID} check=moved"


def _project_repo(tmp_path: Path, project: dict) -> Path:
    repo = _repo(tmp_path, ["true"])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(
        json.dumps({**cfg, "defaultBranch": "master", "checks": {"milestone": ["true"]}})
    )
    (repo / "changes" / ID / "decisions.json").write_text(json.dumps({"project": project}))
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "milestone checks, project")
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "master", str(origin))
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-q", "origin", "master")
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(origin), str(other))
    _git(other, "checkout", "-qb", "project/big")
    (other / "project.txt").write_text("on the project branch only\n")
    _git(other, "add", ".")
    _git(other, "commit", "-qm", "project work")
    _git(other, "push", "-q", "origin", "project/big")
    _git(repo, "checkout", "-qb", "milestone/big-1")
    _approve(repo)
    return repo


def test_a_project_without_a_branch_is_no_parent(tmp_path: Path) -> None:
    # 3.7.0: a project is planning unless it says branch: true; its milestones sync with the
    # default branch only.
    repo = _project_repo(tmp_path, {"slug": "big", "branch": False})
    assert _last(_gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")


@pytest.mark.parametrize("project", [{"slug": "big"}, {"slug": "big", "branch": True}])
def test_a_project_with_a_branch_or_from_before_3_7_still_syncs(
    tmp_path: Path, project: dict
) -> None:
    repo = _project_repo(tmp_path, project)
    r = _gate(repo, "milestone", ID)
    assert _last(r) == f"VERIFY FAIL milestone {ID} check=parent-sync"
    assert "git merge origin/project/big" in r.stdout


# 3.14.0: `milestones.merge: "local"` keeps milestones and the project branch on this machine.
def _local_repo(tmp_path: Path, merge: str | None = "local") -> Path:
    """master with the approved change, a never-pushed project/big at the same commit."""
    repo = _repo(tmp_path, ["true"])
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg = {**cfg, "defaultBranch": "master", "checks": {"milestone": ["true"]}}
    if merge:
        cfg["milestones"] = {"merge": merge}
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    (repo / "changes" / ID / "decisions.json").write_text(
        json.dumps({"project": {"slug": "big", "branch": True}})
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "checks, project")
    _approve(repo)
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "master", str(origin))
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-q", "origin", "master")
    _git(repo, "branch", "project/big")
    return repo


def _merge_milestone_one_locally(repo: Path) -> None:
    """Milestone 2 was cut from the trunk; milestone 1 then merges into the local project branch."""
    _git(repo, "branch", "milestone/big-2")
    _git(repo, "checkout", "-qb", "milestone/big-1")
    (repo / "m1.txt").write_text("milestone 1\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "milestone 1")
    _git(repo, "switch", "-q", "project/big")
    _git(repo, "merge", "-q", "--no-ff", "--no-edit", "milestone/big-1")
    _git(repo, "switch", "-q", "milestone/big-2")


def test_local_mode_milestone_must_contain_the_local_project_branch(tmp_path: Path) -> None:
    repo = _local_repo(tmp_path)
    _merge_milestone_one_locally(repo)
    r = _gate(repo, "milestone", ID)
    assert r.returncode == 1 and _last(r) == f"VERIFY FAIL milestone {ID} check=parent-sync"
    assert "project/big has commits this milestone lacks" in r.stdout
    assert "git merge project/big" in r.stdout
    _git(repo, "merge", "-q", "--no-edit", "project/big")
    assert _last(_gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")


def test_a_newer_gate_beside_an_older_marks_py_still_approves_audits_and_lints_F3(
    tmp_path: Path,
) -> None:
    """A one-file upgrade: verify_gate.py replaced, marks.py not (it has no `bundles` yet): approve,
    lint and audit still run."""
    old = tmp_path / "scripts"
    old.mkdir()
    for f in GATE.parent.glob("*.py"):
        (old / f.name).write_text(f.read_text())
    (old / "marks.py").write_text("def sessions(change):\n    return []\n")
    repo = _repo(tmp_path, ["true"])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": ["true"]}}))
    _git(repo, "commit", "-qam", "milestone checks")
    for args in (("approve", ID), ("lint", ID), ("audit", "--no-evidence")):
        r = subprocess.run(
            [sys.executable, str(old / "verify_gate.py"), *args],
            cwd=repo, capture_output=True, text=True, env=_env(),
        )  # fmt: skip
        assert "Error" not in r.stderr and "Traceback" not in r.stderr, (args, r.stderr)
        if args[0] != "audit":
            assert r.returncode == 0, (args, r.stdout)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "approved")
    r = subprocess.run(
        [sys.executable, str(old / "verify_gate.py"), "milestone", ID],
        cwd=repo, capture_output=True, text=True, env=_env(),
    )  # fmt: skip
    # a marks.py without `bundles` is refused only for a milestone with a design bundle (H5, below)
    assert _last(r).startswith(f"VERIFY PASS milestone {ID}"), r.stdout + r.stderr


@pytest.mark.parametrize("merge", [None, "pr"])
def test_without_local_mode_a_local_project_branch_is_no_parent(
    tmp_path: Path, merge: str | None
) -> None:
    repo = _local_repo(tmp_path, merge)
    _merge_milestone_one_locally(repo)
    assert _last(_gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")


def test_project_gate_records_a_pass_on_the_project_head(tmp_path: Path) -> None:
    repo = _local_repo(tmp_path)
    _merge_milestone_one_locally(repo)
    _git(repo, "switch", "-q", "project/big")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, env=_env()
    ).stdout.strip()
    r = _gate(repo, "project", "big")
    assert r.returncode == 0 and _last(r) == f"VERIFY PASS project big {head}"
    common = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=repo, capture_output=True, text=True, env=_env(),
    ).stdout.strip()  # fmt: skip
    record = json.loads((Path(common) / "sdlc/projects/big/verify/report.json").read_text())
    assert record["result"] == f"VERIFY PASS project big {head}" and record["sha"] == head
    assert not (repo / "changes" / "big").exists()


def test_project_gate_wants_the_project_branch_checked_out(tmp_path: Path) -> None:
    repo = _local_repo(tmp_path)  # HEAD is master
    r = _gate(repo, "project", "big")
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env"
    assert "check out project/big" in r.stdout


def test_project_gate_fails_until_the_default_branch_is_merged_in(tmp_path: Path) -> None:
    repo = _local_repo(tmp_path)
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(tmp_path / "origin.git"), str(other))
    (other / "trunk.txt").write_text("the default branch moved\n")
    _git(other, "add", ".")
    _git(other, "commit", "-qm", "trunk moved")
    _git(other, "push", "-q", "origin", "master")
    _git(repo, "switch", "-q", "project/big")
    r = _gate(repo, "project", "big")
    assert r.returncode == 1 and _last(r) == "VERIFY FAIL project big check=parent-sync"
    assert "git merge origin/master" in r.stdout
    _git(repo, "merge", "-q", "--no-edit", "origin/master")
    assert _last(_gate(repo, "project", "big")).startswith("VERIFY PASS project big")


def test_project_gate_runs_the_milestone_checks_and_fails_with_them(tmp_path: Path) -> None:
    repo = _local_repo(tmp_path)
    cfg = json.loads((repo / "sdlc.json").read_text())
    _git(repo, "switch", "-q", "project/big")
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": ["false"]}}))
    _git(repo, "commit", "-qam", "failing check")
    r = _gate(repo, "project", "big")
    assert r.returncode == 1 and _last(r) == "VERIFY FAIL project big check=check-1"


def test_project_gate_without_milestone_checks_blocks(tmp_path: Path) -> None:
    repo = _local_repo(tmp_path)
    cfg = json.loads((repo / "sdlc.json").read_text())
    _git(repo, "switch", "-q", "project/big")
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {}}))
    _git(repo, "commit", "-qam", "no checks")
    r = _gate(repo, "project", "big")
    assert r.returncode == 3 and "checks.milestone is empty" in r.stdout


# 3.8.0: the plan gate refuses unfinished quality records; the milestone gate refuses open ones.
GOOD_INTENT = "---\nstatus: approved\n---\n\n# Intent\n"
VIOLATIONS = (
    "# Plan\n\n### Justified violations\n\n"
    "| Violation | Why needed | Simpler alternative rejected because |\n|---|---|---|\n{row}\n\n"
    "## Design changes\n"
)


def _commit_files(repo: Path, **files: str) -> None:
    for name, text in files.items():
        (repo / "changes" / ID / name.replace("_", ".", 1)).write_text(text)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "records")


@pytest.mark.parametrize(
    ("files", "needle"),
    [
        (
            {"checklist_md": "- [x] **Gap** F1 done\n- [ ] **Ambiguity** F2: is it 10 or 20?\n"},
            "checklist.md: unchecked",
        ),
        ({"analyze_md": "| X1 | CRITICAL | rules | F1 | breaks SEC-2 | open |\n"}, "open CRITICAL"),
        (
            {"challenge_md": "| H1 | CRITICAL | existence | plan | no ask needs it | open |\n"},
            "challenge.md: open CRITICAL",
        ),
        ({"plan_md": VIOLATIONS.format(row="| SEC-2: no PII | | |")}, "unjustified violation"),
    ],
)
def test_approve_refuses_unfinished_quality_records(
    tmp_path: Path, files: dict[str, str], needle: str
) -> None:
    repo = _repo(tmp_path, ["true"])
    files = {"intent_md": GOOD_INTENT, **files}
    _commit_files(repo, **files)
    r = _gate(repo, "approve", ID)
    assert r.returncode == 1 and needle in r.stdout and _last(r).startswith("APPROVE FAIL")
    assert not (repo / "changes" / ID / "lock.json").exists()


def test_approve_passes_with_finished_records(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    _commit_files(
        repo,
        intent_md=GOOD_INTENT,
        checklist_md="- [x] **Gap** F1 answered\n",
        analyze_md="| X1 | CRITICAL | rules | F1 | breaks SEC-2 | fixed |\n| X2 | LOW | wording | F1 | x | open |\n",
        challenge_md="| H1 | CRITICAL | existence | plan | why? | accepted |\n"
        "| H2 | HIGH | failure | plan | x | open |\n",
        plan_md=VIOLATIONS.format(
            row="| SEC-2: no PII | audit log | a hash, which cannot be searched |"
        ),
    )
    assert _gate(repo, "approve", ID).returncode == 0


@pytest.mark.parametrize(
    ("files", "reason"),
    [
        (
            {"validation_md": "| F1 | x | y | z | met |\n| F2 | x | y | z | not met |\n"},
            "validation-not-met",
        ),
        ({"validation_md": "| F1 | x | y | z | partly |\n"}, "validation-not-met"),
        ({"findings_md": "## Blocking\n\n- [x] done\n- [ ] **B2** still open\n"}, "findings-open"),
        ({"findings_md": "## Converge\n\n- [x] **C1** missing: F3 - a.ts:1\n"}, "not-converged"),
    ],
)
def test_milestone_blocks_on_open_records(
    tmp_path: Path, files: dict[str, str], reason: str
) -> None:
    repo = _repo(tmp_path, ["true"])
    _approve(repo)
    _commit_files(repo, **files)
    r = _gate(repo, "milestone", ID)
    assert r.returncode == 3 and _last(r) == f"VERIFY BLOCKED reason={reason}"


def test_milestone_passes_when_records_are_closed(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": ["true"]}}))
    _git(repo, "commit", "-qam", "milestone checks")
    _approve(repo)
    _commit_files(
        repo,
        validation_md="| F1 | x | y | z | met |\n",
        findings_md="## Blocking\n\n- [x] **B1** fixed\n\n## Converge\n\nConverged: round 2\n\n"
        "## Advisory\n\n- [ ] **A1** rename a variable\n",
    )
    assert _last(_gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")


def _milestone_repo(tmp_path: Path) -> Path:
    repo = _repo(tmp_path, [])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": ["true"]}}))
    _git(repo, "commit", "-qam", "milestone checks")
    _approve(repo)
    return repo


OPEN_ITEM = "## Blocking\n\n- [ ] **B2** the card overflows at 320\n\n"
OPTIONS = ["Fix it now", "Accept as is", "Defer to milestone 2", "Block the close"]


def _later(n: int = 0) -> str:
    """A timestamp after the commit that holds the finding."""
    stamp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=60 + n)
    return stamp.isoformat().replace("+00:00", "Z")


def _dialog(
    finding: str = "B2",
    label: str = "Accept as is",
    n: int = 1,
    change: str = ID,
    options: list[str] | None = None,
    stamp: str | None = None,
    tool: str = "AskUserQuestion",
    sidechain: bool = False,
) -> list[dict]:
    """The two transcript entries of one answered AskUserQuestion: the agent's tool_use and the
    structured tool result carrying the owner's selected option."""
    question = f"Change {change}, finding {finding}: the card overflows at 320. What now?"
    stamp = stamp or _later(n)
    base = {"timestamp": stamp, "isSidechain": sidechain}
    return [
        {
            **base,
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": f"toolu_{n}", "name": tool,
                "input": {"questions": [{
                    "question": question,
                    "options": [{"label": o} for o in (options or OPTIONS)],
                }]},
            }]},
        },  # fmt: skip
        {
            **base,
            "type": "user",
            "toolUseResult": {"answers": {question: label}},
            "message": {"content": [
                {"type": "tool_result", "tool_use_id": f"toolu_{n}", "content": f'"{question}"="{label}"'}
            ]},
        },  # fmt: skip
    ]


def _owner_gate(
    repo: Path,
    entries: list[dict] | None = None,
    symlinked: bool = False,
    cwd: Path | None = None,
    home_for: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """The milestone gate with a session transcript, found where Claude Code keeps it
    (`$HOME/.claude/projects/<repo slug>/`) and holding `entries`."""
    home = repo.parent / "home"
    slug = re.sub(r"[^A-Za-z0-9]", "-", str((home_for or repo).resolve()))
    folder = home / ".claude/projects" / slug
    if symlinked:
        real = repo.parent / "real-transcripts"
        real.mkdir(exist_ok=True)
        folder.parent.mkdir(parents=True, exist_ok=True)
        folder.symlink_to(real)
        folder = real
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "session.jsonl").write_text("\n".join(json.dumps(e) for e in entries or []) + "\n")
    return subprocess.run(
        [sys.executable, str(GATE), "milestone", ID],
        cwd=cwd or repo,
        capture_output=True,
        text=True,
        env={**_env(), "HOME": str(home)},
    )


def _dispose(repo: Path, item: str = OPEN_ITEM) -> None:
    item = item if "Converged:" in item else item + CONVERGED
    _commit_files(repo, validation_md="| F1 | x | y | z | met |\n", findings_md=item)


def _verdict(r: subprocess.CompletedProcess[str]) -> str:
    return _last(r)


@pytest.mark.parametrize("label", ["Accept as is", "Defer to milestone 2"])
def test_the_owners_answer_settles_a_residual_finding(tmp_path: Path, label: str) -> None:
    """3.21.0 (S2): accepted or deferred settles a residual only through the owner's structured
    answer to the dialog, so an agent cannot accept its own finding."""
    repo = _milestone_repo(tmp_path)
    _dispose(repo)
    assert _verdict(_owner_gate(repo, _dialog(label=label))).startswith(f"VERIFY PASS milestone {ID}")


@pytest.mark.parametrize("label", ["Fix it now", "Block the close"])
def test_a_refusal_or_a_fix_request_never_settles(tmp_path: Path, label: str) -> None:
    """Review finding 2: an explicit refusal is not acceptance."""
    repo = _milestone_repo(tmp_path)
    _dispose(repo)
    r = _owner_gate(repo, _dialog(label=label))
    want = "findings-blocked" if label == "Block the close" else "findings-open"
    assert r.returncode == 3 and _verdict(r) == f"VERIFY BLOCKED reason={want}"


def _text(text: str, **extra: object) -> dict:
    return {"type": "user", "timestamp": _later(), "message": {"content": text}, **extra}


@pytest.mark.parametrize(
    "entries",
    [
        [_text("I reject B2 and require a fix before we ship.")],
        [_text("Change " + ID + ", finding B2: accept it, B2 is fine to ship as it is")],
        [_text("B2 is fine to ship as it is, we build it in M2", promptSource="system", turnOrigin="peer")],
        [_text("Accept as is", isMeta=True)],
        [],
    ],
)
def test_typed_text_never_settles_a_finding(tmp_path: Path, entries: list[dict]) -> None:
    """Review finding 3: no text matching, so another speaker or a screenshot message cannot
    forge or lose a decision."""
    repo = _milestone_repo(tmp_path)
    _dispose(repo)
    assert _verdict(_owner_gate(repo, entries)) == "VERIFY BLOCKED reason=findings-open"


@pytest.mark.parametrize(
    "entries",
    [
        _dialog(label="Accept as is B2, go ahead"),  # a free-text "Other" answer, not an option
        _dialog(finding="B9"),  # another finding
        _dialog(change="2026-01-01-other-change"),  # another change
        _dialog(tool="SomethingElse"),  # not the AskUserQuestion tool
        _dialog(sidechain=True),  # a subagent
        _dialog(options=["Fix it now", "Block the close"]),  # the answer is not an offered option
        _dialog(stamp="2001-01-01T00:00:00Z"),  # said before the finding existed
        _dialog(stamp="not a time"),
    ],
)
def test_only_an_answer_bound_to_this_change_and_finding_in_time_settles(
    tmp_path: Path, entries: list[dict]
) -> None:
    repo = _milestone_repo(tmp_path)
    _dispose(repo)
    assert _verdict(_owner_gate(repo, entries)) == "VERIFY BLOCKED reason=findings-open"


def test_the_latest_answer_wins(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    _dispose(repo)
    accept, fix = _dialog(n=1), _dialog(label="Fix it now", n=2)
    assert _verdict(_owner_gate(repo, accept + fix)) == "VERIFY BLOCKED reason=findings-open"
    assert _verdict(_owner_gate(repo, fix + _dialog(n=3))).startswith("VERIFY PASS")


def test_a_ticked_item_cannot_override_a_block_until_the_owner_answers_again(tmp_path: Path) -> None:
    """Review finding 10: a terminal block is evaluated against every finding, ticked or not."""
    repo = _milestone_repo(tmp_path)
    _dispose(repo, "## Blocking\n\n- [x] **B2** the card overflows at 320\n\n")
    block = _dialog(label="Block the close", n=1)
    r = _owner_gate(repo, block)
    assert r.returncode == 3 and _verdict(r) == "VERIFY BLOCKED reason=findings-blocked"
    assert "B2" in r.stdout and "ticked" in r.stdout
    # "Fix it now" is an instruction, not a settlement: the box must be ticked again after it
    fix = _verdict(_owner_gate(repo, block + _dialog(label="Fix it now", n=2)))
    assert fix == "VERIFY BLOCKED reason=findings-open"


def test_a_convergence_id_is_dispositioned_through_the_gate(tmp_path: Path) -> None:
    """Review finding 9: the id the stage produces (**C1**) is in the grammar the gate reads."""
    repo = _milestone_repo(tmp_path)
    item = "## Converge\n\n- [ ] **C1** missing: F3 - a.ts:1\n\nConverged: round 2\n"
    _dispose(repo, item)
    assert _verdict(_owner_gate(repo, [])) == "VERIFY BLOCKED reason=findings-open"
    assert _verdict(_owner_gate(repo, _dialog("C1", "Defer to milestone 2"))).startswith("VERIFY PASS")
    _dispose(repo, item.replace("- [ ]", "- [x]"))
    assert _verdict(_owner_gate(repo, _dialog("C1", "Block the close"))) == (
        "VERIFY BLOCKED reason=findings-blocked"
    )


def test_a_worktree_or_a_subfolder_reads_the_owners_session_in_either_checkout(
    tmp_path: Path,
) -> None:
    """Review finding 4: the owner may have answered in the main checkout while the gate runs in
    a milestone worktree, or from a subfolder."""
    repo = _milestone_repo(tmp_path)
    _dispose(repo)
    wt = tmp_path / "wt"
    _git(repo, "worktree", "add", "-q", "-b", "side", str(wt))
    answer = _dialog()
    assert _verdict(_owner_gate(repo, answer, cwd=wt, home_for=repo)).startswith("VERIFY PASS")
    sub = repo / "changes"
    assert _verdict(_owner_gate(repo, answer, cwd=sub)).startswith("VERIFY PASS")


def test_without_a_readable_transcript_nothing_is_settled(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    _dispose(repo)
    env = {**_env(), "HOME": str(tmp_path / "empty-home")}
    r = subprocess.run(
        [sys.executable, str(GATE), "milestone", ID], cwd=repo, capture_output=True, text=True, env=env
    )  # fmt: skip
    assert _last(r) == "VERIFY BLOCKED reason=findings-open"


def test_the_caller_cannot_pick_the_evidence_file(tmp_path: Path) -> None:
    """No env var names the transcript: a file the agent wrote is never read as the owner."""
    repo = _milestone_repo(tmp_path)
    _dispose(repo)
    fake = tmp_path / "fake.jsonl"
    fake.write_text("\n".join(json.dumps(e) for e in _dialog()) + "\n")
    env = {**_env(), "HOME": str(tmp_path / "empty-home"), "SDLC_TRANSCRIPT": str(fake)}
    r = subprocess.run(
        [sys.executable, str(GATE), "milestone", ID], cwd=repo, capture_output=True, text=True, env=env
    )  # fmt: skip
    assert _last(r) == "VERIFY BLOCKED reason=findings-open"


def test_a_symlinked_transcript_folder_is_refused(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    _dispose(repo)
    r = _owner_gate(repo, _dialog(), symlinked=True)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=findings-open"


def test_a_disposition_needs_an_explicit_bold_id(tmp_path: Path) -> None:
    """An item with no `**<ID>**` has no id to bind to, so an answer can never settle it."""
    repo = _milestone_repo(tmp_path)
    _dispose(repo, "## Blocking\n\n- [ ] the card overflows at 320\n\n")
    for finding in ("the", "Z2", "B2"):
        assert _verdict(_owner_gate(repo, _dialog(finding))) == "VERIFY BLOCKED reason=findings-open"


def test_an_id_that_matches_two_open_items_settles_neither(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    _dispose(repo, "## Blocking\n\n- [ ] **B2** one\n- [ ] **B2** two\n\n")
    assert _verdict(_owner_gate(repo, _dialog())) == "VERIFY BLOCKED reason=findings-open"


def test_acceptance_never_turns_a_partly_met_fact_into_met(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    _commit_files(
        repo,
        validation_md="| F1 | x | y | z | partly |\n",
        findings_md=OPEN_ITEM,
    )
    assert _last(_owner_gate(repo, _dialog("F1"))) == "VERIFY BLOCKED reason=validation-not-met"


def test_the_report_carries_operational_metrics(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true", "false"])
    _approve(repo)
    _commit_files(repo, findings_md="## Blocking\n\n- [ ] **B1** open\n\nConverged: round 2\n")
    _gate(repo, "feature", ID)
    verify = repo / "changes" / ID / "verify"
    m = json.loads((verify / "report.json").read_text())["metrics"]
    assert (m["checks_run"], m["checks_passed"], m["checks_failed"]) == (2, 1, 1)
    assert (m["retries"], m["review_rounds"], m["open_findings"]) == (0, 2, 1)
    assert "elapsed_s" in m and "- open findings: 1" in (verify / "report.md").read_text()
    _gate(repo, "feature", ID)
    again = json.loads((verify / "report.json").read_text())["metrics"]
    assert again["retries"] == 1


# 3.9.0: audit is read-only and reports installed, configured, executed and passed apart.
WORKFLOW = """name: ci
on: [pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: echo lint-it
  unit:
    name: Unit tests
    runs-on: ubuntu-latest
    steps:
      - run: echo unit-it
  extra:
    runs-on: ubuntu-latest
    steps:
      - run: echo extra-it
  check:
    needs:
      - lint
      - unit
    runs-on: ubuntu-latest
    steps:
      - run: echo done
"""


def _audit_repo(tmp_path: Path, checks: list, required: list[str] | None) -> tuple[Path, dict]:
    repo = _repo(tmp_path, [])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(
        json.dumps({**cfg, "defaultBranch": "master", "checks": {"milestone": checks}})
    )
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text(WORKFLOW)
    hooks = repo / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    for name in ("chain-gate.sh", "sdlc-config.sh"):
        (hooks / name).write_text("#!/bin/sh\n")
    (hooks / "chain-gate.sh").chmod(0o755)
    (repo / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Edit|Write",
                            "hooks": [
                                {"type": "command", "command": '"$X"/.claude/hooks/chain-gate.sh'}
                            ],
                        }
                    ]
                }
            }
        )
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    if required is None:
        gh.write_text("#!/bin/sh\nexit 1\n")
    else:
        rules = [
            {
                "type": "required_status_checks",
                "parameters": {"required_status_checks": [{"context": c} for c in required]},
            }
        ]
        gh.write_text(f"#!/bin/sh\ncat <<'EOF'\n{json.dumps(rules)}\nEOF\n")
    gh.chmod(0o755)
    env = {**_env(), "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    return repo, env


def _audit(repo: Path, env: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE), "audit"], cwd=repo, capture_output=True, text=True, env=env
    )


def _ran(repo: Path, *runs: str) -> None:
    verify = repo / "changes" / ID / "verify"
    verify.mkdir()
    checks = [{"name": r, "run": r, "status": "pass"} for r in runs]
    (verify / "report.json").write_text(json.dumps({"sha": "abc1234def", "checks": checks}))


def test_audit_passes_when_every_gate_is_required_and_ran(tmp_path: Path) -> None:
    repo, env = _audit_repo(tmp_path, ["echo lint-it", "echo unit-it"], required=["check"])
    _ran(repo, "echo lint-it", "echo unit-it")
    r = _audit(repo, env)
    assert r.returncode == 0 and _last(r) == "AUDIT PASS problems=0 unknown=0"
    assert "required=yes" in r.stdout and "last run: pass @abc1234" in r.stdout
    assert "hook chain-gate.sh: installed=yes invoked by [PreToolUse Edit|Write]" in r.stdout


def test_audit_fails_a_ci_check_that_is_not_a_required_status(tmp_path: Path) -> None:
    repo, env = _audit_repo(tmp_path, ["echo extra-it"], required=["check"])
    _ran(repo, "echo extra-it")
    r = _audit(repo, env)  # `extra` is not in check's needs
    assert r.returncode == 1 and "not a required status" in r.stdout


def test_audit_says_unknown_when_gh_cannot_answer_and_does_not_fail_on_it(tmp_path: Path) -> None:
    repo, env = _audit_repo(tmp_path, ["echo lint-it"], required=None)
    _ran(repo, "echo lint-it")
    r = _audit(repo, env)
    assert r.returncode == 0 and "required=unknown" in r.stdout and "unknown=1" in _last(r)


def test_audit_fails_a_check_that_never_ran_or_whose_checker_is_missing(tmp_path: Path) -> None:
    repo, env = _audit_repo(tmp_path, ["echo lint-it", "no-such-tool-xyz --go"], required=["check"])
    r = _audit(repo, env)
    assert r.returncode == 1
    assert "never ran" in r.stdout and "`no-such-tool-xyz` does not exist" in r.stdout


def test_audit_treats_a_check_no_ci_job_runs_as_local(tmp_path: Path) -> None:
    repo, env = _audit_repo(tmp_path, ["echo only-here"], required=["check"])
    _ran(repo, "echo only-here")
    r = _audit(repo, env)
    assert r.returncode == 0 and "required=local" in r.stdout


def test_audit_fails_a_hook_that_is_missing_or_not_registered(tmp_path: Path) -> None:
    repo, env = _audit_repo(tmp_path, ["echo lint-it"], required=["check"])
    _ran(repo, "echo lint-it")
    stray = repo / ".claude" / "hooks" / "stray.sh"
    stray.write_text("#!/bin/sh\n")
    stray.chmod(0o755)
    (repo / ".claude" / "hooks" / "chain-gate.sh").unlink()
    r = _audit(repo, env)
    assert r.returncode == 1
    assert "chain-gate.sh: registered but missing" in r.stdout
    assert "stray.sh: installed but not registered" in r.stdout


def test_audit_changes_nothing(tmp_path: Path) -> None:
    repo, env = _audit_repo(tmp_path, ["echo lint-it"], required=["check"])
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "all")
    _audit(repo, env)
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
    ).stdout
    assert status == ""


def test_audit_without_evidence_skips_the_never_ran_test(tmp_path: Path) -> None:
    repo, env = _audit_repo(tmp_path, ["echo lint-it"], required=["check"])
    r = subprocess.run(
        [sys.executable, str(GATE), "audit", "--no-evidence"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0 and "last run: never" in r.stdout


def _order(repo: Path) -> list[str]:
    report = json.loads((repo / "changes" / ID / "verify" / "report.json").read_text())
    return [c["name"] for c in report["checks"]]


def _checks(*names_and_cmds: tuple[str, str], **extra: object) -> list[dict]:
    return [{"name": n, "run": c, **extra} for n, c in names_and_cmds]


def test_checks_run_cheapest_first_by_a_static_guess(tmp_path: Path) -> None:
    """No durations yet: lint, format and typecheck first, build/e2e last, the rest between,
    whatever the order in sdlc.json."""
    repo = _repo(tmp_path, _checks(("e2e", "true"), ("unit", "true"), ("lint", "true")))
    _approve(repo)
    assert _gate(repo, "feature", ID).returncode == 0
    assert _order(repo) == ["lint", "unit", "e2e"]


def test_the_first_failure_stops_before_the_expensive_checks(tmp_path: Path) -> None:
    repo = _repo(tmp_path, _checks(("e2e", "true"), ("lint", "false")))
    _approve(repo)
    r = _gate(repo, "feature", ID)
    assert r.returncode == 1 and _last(r) == f"VERIFY FAIL feature {ID} check=lint"
    assert _order(repo) == ["lint"]


def test_recorded_seconds_beat_the_guess_and_a_pass_records_them(tmp_path: Path) -> None:
    repo = _repo(tmp_path, _checks(("lint", "echo a"), ("unit", "echo b")))
    _approve(repo)
    durations = repo / "changes" / ID / "verify" / "durations.json"
    durations.parent.mkdir(exist_ok=True)
    durations.write_text(json.dumps({"echo a": 90.0, "echo b": 0.1}))
    assert _gate(repo, "feature", ID).returncode == 0
    assert _order(repo) == ["unit", "lint"]
    assert set(json.loads(durations.read_text())) == {"echo a", "echo b"}
    assert json.loads(durations.read_text())["echo a"] < 90  # re-measured on the pass


def test_a_serial_check_is_a_wall_nothing_moves_across(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path, [*_checks(("e2e", "true"), ("unit", "true")), *_checks(("lint", "true"))]
    )
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["checks"]["feature"][2]["serial"] = True  # needs what the two before it produced
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    _git(repo, "commit", "-qam", "serial")
    _approve(repo)
    assert _gate(repo, "feature", ID).returncode == 0
    assert _order(repo) == ["unit", "e2e", "lint"]


def test_keep_going_runs_every_check_and_names_the_first_failure(tmp_path: Path) -> None:
    repo = _repo(tmp_path, _checks(("e2e", "true"), ("unit", "false"), ("lint", "false")))
    _approve(repo)
    r = _gate(repo, "feature", ID, "--keep-going")
    assert r.returncode == 1 and _last(r) == f"VERIFY FAIL feature {ID} check=lint"
    assert _order(repo) == ["lint", "unit", "e2e"] and "failed: lint, unit" in r.stdout


def test_missing_evidence_fails_before_the_suite_starts(tmp_path: Path) -> None:
    """3.21.0: offline evidence checks (marks, visual checkers) run before the suites, so a
    missing screenshot never costs a full E2E run."""
    repo = _repo(tmp_path, ["true"])
    ran = repo / "suite-ran"
    suite = f"touch {ran}"
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"milestone": [suite]}}))
    export = repo / "changes" / ID / "asks/export"
    export.mkdir(parents=True)
    (export / "index.html").write_text("<html>screen</html>")
    _approve_legacy(repo)
    result = _gate(repo, "milestone", ID)
    assert _last(result) == f"VERIFY FAIL milestone {ID} check=owner-marks"
    assert not ran.exists()


def test_a_supplied_bundle_requires_a_valid_ledger_at_milestone(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"milestone": ["true"]}}))
    export = repo / "changes" / ID / "asks/export"
    export.mkdir(parents=True)
    (export / "index.html").write_text("<html>screen</html>")
    _approve_legacy(repo)
    result = _gate(repo, "milestone", ID)
    assert _last(result) == f"VERIFY FAIL milestone {ID} check=owner-marks"


def test_after_orders_a_check_behind_the_one_it_needs_F13(tmp_path: Path) -> None:
    """Codegen must run before the typecheck even though the typecheck is the cheaper guess."""
    repo = _repo(tmp_path, _checks(("tsc", "true"), ("types", "true")))
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["checks"]["feature"][0]["after"] = ["types"]
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    _git(repo, "commit", "-qam", "after")
    _approve(repo)
    assert _gate(repo, "feature", ID).returncode == 0
    assert _order(repo) == ["types", "tsc"]


def test_a_new_approval_records_cost_order_and_an_old_lock_keeps_declared_order_F13(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, _checks(("e2e", "true"), ("unit", "true"), ("lint", "true")))
    _approve(repo)
    lock_path = repo / "changes" / ID / "lock.json"
    lock = json.loads(lock_path.read_text())
    assert lock["order"] == "cost"
    assert _gate(repo, "feature", ID).returncode == 0
    assert _order(repo) == ["lint", "unit", "e2e"]
    del lock["order"]  # approved before this version: the order it saw is the order it keeps
    lock_path.write_text(json.dumps(lock))
    _git(repo, "commit", "-qam", "old lock")
    assert _gate(repo, "feature", ID).returncode == 0
    assert _order(repo) == ["e2e", "unit", "lint"]


def test_keep_going_does_not_stop_at_a_blocked_check_F23(tmp_path: Path) -> None:
    blocked = "echo 'VERIFY BLOCKED reason=env'; exit 1"
    repo = _repo(tmp_path, _checks(("lint", "false"), ("unit", blocked), ("e2e", "true")))
    _approve(repo)
    r = _gate(repo, "feature", ID, "--keep-going")
    assert _last(r) == f"VERIFY FAIL feature {ID} check=lint"  # the first verdict stands
    assert _order(repo) == ["lint", "unit", "e2e"]


def test_keep_going_reports_a_first_blocked_verdict_after_running_the_rest_F23(
    tmp_path: Path,
) -> None:
    blocked = "echo 'VERIFY BLOCKED reason=env'; exit 1"
    repo = _repo(tmp_path, _checks(("lint", blocked), ("unit", "false"), ("e2e", "true")))
    _approve(repo)
    r = _gate(repo, "feature", ID, "--keep-going")
    assert _last(r) == "VERIFY BLOCKED reason=env" and r.returncode == 3
    assert _order(repo) == ["lint", "unit", "e2e"]


# --- Review finding 1: the milestone checks name the full suite and the full E2E -------------


def _e2e_repo(tmp_path: Path, milestone: list, config: str | None = "playwright.config.ts") -> Path:
    repo = _repo(tmp_path, ["true"])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": milestone}}))
    if config:
        (repo / config).parent.mkdir(parents=True, exist_ok=True)
        (repo / config).write_text("x")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "e2e config")
    return repo


@pytest.mark.parametrize("config", ["playwright.config.ts", "e2e/test_login.py"])
@pytest.mark.parametrize(
    "milestone",
    [["pytest -q"], ["pnpm test"], ["pnpm test:e2e --grep @x"], ["pnpm exec playwright test e2e/a.spec.ts"]],
)
def test_approve_refuses_a_milestone_check_list_without_the_full_e2e(
    tmp_path: Path, milestone: list, config: str
) -> None:
    repo = _e2e_repo(tmp_path, milestone, config)
    r = _gate(repo, "approve", ID)
    assert r.returncode == 1 and "checks.milestone" in r.stdout and "full E2E" in r.stdout
    assert _last(r).startswith("APPROVE FAIL")
    assert not (repo / "changes" / ID / "lock.json").exists()


@pytest.mark.parametrize(
    "milestone",
    [
        ["pytest -q", "pnpm test:e2e --max-failures=10", "pnpm exec playwright test --repeat-each=3 $specs"],
        ["pytest -q", "uv run pytest e2e -q", "for i in 1 2 3; do uv run pytest e2e/a.py -q; done"],
    ],
)
def test_approve_accepts_a_named_full_e2e_entry(tmp_path: Path, milestone: list) -> None:
    repo = _e2e_repo(tmp_path, milestone)
    assert _gate(repo, "approve", ID).returncode == 0


def test_a_repo_without_an_e2e_config_needs_no_e2e_entry(tmp_path: Path) -> None:
    repo = _e2e_repo(tmp_path, ["pytest -q"], config=None)
    assert _gate(repo, "approve", ID).returncode == 0


def test_an_old_lock_reports_an_upgrade_gap_and_still_runs(tmp_path: Path) -> None:
    """An approval made before the rule keeps working: the gate says what is missing, never fails."""
    repo = _e2e_repo(tmp_path, ["true"], config=None)
    assert _gate(repo, "approve", ID).returncode == 0
    _old = repo / "changes" / ID / "lock.json"
    _lock = json.loads(_old.read_text())
    _lock.pop("format")
    _old.write_text(json.dumps(_lock))
    (repo / "e2e").mkdir()
    (repo / "e2e" / "a.spec.ts").write_text("x")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "e2e appears")
    _commit_files(repo, validation_md="| F1 | x | y | z | met |\n")
    r = _gate(repo, "milestone", ID)
    assert "upgrade gap" in r.stdout and _last(r).startswith(f"VERIFY PASS milestone {ID}")
    report = json.loads((repo / "changes" / ID / "verify" / "report.json").read_text())
    assert any("full E2E" in g for g in report["upgrade_gaps"])


@pytest.mark.parametrize("name", ["node", "python"])
def test_the_presets_run_the_full_e2e_and_repeat_changed_and_flaky_specs_three_times(name: str) -> None:
    preset = json.loads((SKILL / "templates" / "presets" / f"{name}.json").read_text())
    milestone = " ".join(c if isinstance(c, str) else c["run"] for c in preset["checks"]["milestone"])
    assert "e2e" in milestone
    assert "flaky-specs.txt" in milestone
    assert "--repeat-each=3" in milestone or "seq 3" in milestone or "1 2 3" in milestone
    assert "git diff --name-only" in milestone and "{base}" in milestone


# --- Review finding 6: the validation rows come from the approved facts of the milestone -----


def _facts_repo(tmp_path: Path, facts: list, plan: str = "") -> Path:
    repo = _repo(tmp_path, [])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": ["true"]}}))
    change = repo / "changes" / ID
    (change / "done.json").write_text(json.dumps({"facts": facts}))
    (change / "plan.md").write_text(plan)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "facts")
    _approve(repo)
    return repo


@pytest.mark.parametrize(
    "validation",
    [
        None,  # no validation.md at all
        "| F1 | x | y | z | met |\n",  # F2 has no row
        "| F1 | x | y |  | met |\n| F2 | x | y | t.test.ts > it | met |\n",  # empty evidence
        "| F1 | x | y | <test or shot> | met |\n| F2 | x | y | t | met |\n",  # a placeholder
        "| F1 | x | y | - | met |\n| F2 | x | y | t | met |\n",
        "| F1 | x | y | z | met |\n| F2 | x | y | z | unknown |\n",  # not a met verdict
    ],
)
def test_a_pass_needs_a_met_row_with_evidence_for_every_approved_fact(
    tmp_path: Path, validation: str | None
) -> None:
    repo = _facts_repo(tmp_path, ["F1", "F2"])
    if validation is not None:
        _commit_files(repo, validation_md=validation)
    else:
        (repo / "changes" / ID / "validation.md").unlink()
        _git(repo, "commit", "-qam", "no validation")
    r = _gate(repo, "milestone", ID)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=validation-not-met", r.stdout


def test_every_fact_with_a_met_row_and_evidence_passes(tmp_path: Path) -> None:
    repo = _facts_repo(tmp_path, [{"id": "F1", "tag": "@F1"}, "N1"])
    _commit_files(
        repo, validation_md="| F1/A1 | x | y | e2e: login.spec.ts @F1 | met |\n| N1 | x | y | shot: a.png | met |\n"
    )
    assert _last(_gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")


def test_only_the_facts_of_this_milestone_are_expected(tmp_path: Path) -> None:
    plan = "## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n| M1 a | F1 | none |\n| M2 b | F2 | M1 |\n"
    repo = _facts_repo(tmp_path, ["F1", "F2"], plan)
    _git(repo, "checkout", "-q", "-b", "milestone/trial-1")
    _commit_files(repo, validation_md="| F1 | x | y | z | met |\n")
    assert _last(_gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")
    _git(repo, "checkout", "-q", "-b", "milestone/trial-2")
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=validation-not-met"


# --- shell safety: the change id and the branch go into a shell command ------------------------


@pytest.mark.parametrize("name", ["x;touch PWNED", "a b", "x$(touch PWNED)", "x`touch PWNED`"])
def test_a_change_id_that_is_not_a_plain_path_is_refused_before_any_check_runs(
    tmp_path: Path, name: str
) -> None:
    repo = _repo(tmp_path, ["true"])
    (repo / "changes" / name).mkdir()
    for scope in ("feature", "milestone"):
        r = _gate(repo, scope, name)
        assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env", r.stdout
        assert "change id" in r.stdout
    assert not (repo / "PWNED").exists() and not (repo / "changes" / name / "PWNED").exists()


def test_a_default_branch_that_is_not_a_plain_ref_is_refused(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "defaultBranch": "x;touch PWNED"}))
    r = _gate(repo, "milestone", ID)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env" and "defaultBranch" in r.stdout
    assert not (repo / "PWNED").exists()


# --- Review finding 7: the required visual runs come from the UX decision and the sources -----


def _visual_repo_unapproved(tmp_path: Path, decisions: dict | None, ux: str = "on") -> Path:
    repo = _repo(tmp_path, [])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"milestone": ["true"]}, "ux": ux}))
    if decisions is not None:
        (repo / "changes" / ID / "decisions.json").write_text(json.dumps(decisions))
    return repo


def _visual_repo(
    tmp_path: Path, decisions: dict | None, ux: str = "on", loose_reference: bool = False
) -> Path:
    repo = _repo(tmp_path, [])
    cfg = {"checks": {"milestone": ["true"]}, "ux": ux}
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    change = repo / "changes" / ID
    if decisions is not None:
        (change / "decisions.json").write_text(json.dumps(decisions))
    if loose_reference:
        (change / "asks").mkdir()
        (change / "asks/wireframe.png").write_bytes(b"reference")
    (_approve_legacy if ux != "off" and (decisions and decisions.get("visualSource") or loose_reference) else _approve)(repo)
    return repo


VISUAL = {"size": "M", "visualSource": {"kind": "images", "path": "asks"}}


def test_a_milestone_with_a_visual_source_fails_before_the_suites_without_a_visual_run(
    tmp_path: Path,
) -> None:
    repo = _visual_repo(tmp_path, VISUAL)
    r = _gate(repo, "milestone", ID)
    assert _last(r) == f"VERIFY FAIL milestone {ID} check=ux-visual-required"
    report = json.loads((repo / "changes" / ID / "verify/report.json").read_text())
    assert [c["name"] for c in report["checks"]] == ["owner-marks", "ux-visual-required"]  # the suite never ran


@pytest.mark.parametrize(
    ("decisions", "ux"),
    [
        ({**VISUAL, "skips": {"visual": "skip -- the screens are unchanged, the owner agreed"}}, "on"),
        ({"size": "none"}, "on"),  # no interface change and no visual source
        (VISUAL, "off"),
        (None, "on"),  # no visual source, no reference, no manifest
    ],
)
def test_a_recorded_skip_or_no_interface_needs_no_visual_run(
    tmp_path: Path, decisions: dict | None, ux: str
) -> None:
    repo = _visual_repo(tmp_path, decisions, ux)
    answer = _skip_answer() if decisions and "skips" in decisions else []
    assert _last(_owner_gate(repo, answer)).startswith(f"VERIFY PASS milestone {ID}")


def _skip_answer(label: str = "Skip visual evidence", n: int = 1) -> list[dict]:
    return _dialog(
        finding="visual-skip", label=label, n=n, options=["Skip visual evidence", "Run visual evidence"]
    )


def test_a_skip_in_decisions_json_alone_is_not_enough_the_owner_must_attest_it(
    tmp_path: Path,
) -> None:
    """Review (security) 4: decisions.json is not part of the approval lock, so `skips.visual` counts
    only with the owner's answer to `Change <id>, finding visual-skip: ...`."""
    skip = {**VISUAL, "skips": {"visual": "skip -- the screens are unchanged"}}
    repo = _visual_repo(tmp_path, skip)
    assert _last(_owner_gate(repo, [])).endswith("check=ux-visual-required")
    assert _last(_owner_gate(repo, _skip_answer("Run visual evidence"))).endswith("check=ux-visual-required")
    assert _last(_owner_gate(repo, _skip_answer())).startswith(f"VERIFY PASS milestone {ID}")


def test_a_skip_without_a_reason_is_not_a_recorded_skip(tmp_path: Path) -> None:
    repo = _visual_repo(tmp_path, {**VISUAL, "skips": {"visual": "skip -- "}})
    assert _last(_gate(repo, "milestone", ID)).endswith("check=ux-visual-required")


def test_a_loose_reference_image_alone_triggers_the_owner_marks_check(tmp_path: Path) -> None:
    repo = _visual_repo(tmp_path, {"size": "M"}, loose_reference=True)
    r = _gate(repo, "milestone", ID)
    assert _last(r) == f"VERIFY FAIL milestone {ID} check=owner-marks"


def test_a_capture_manifest_alone_triggers_the_owner_marks_check(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"milestone": ["true"]}, "ux": "off"}))
    shots = repo / "changes" / ID / "verify/shots"
    shots.mkdir(parents=True)
    (shots / "manifest.json").write_text('{"entries": []}')
    _approve(repo)
    assert _last(_gate(repo, "milestone", ID)).endswith("check=owner-marks")


# --- Review (security): plain names, quoting, the change path inside the changes folder ----------


@pytest.mark.parametrize("name", ["a..b", ".hidden-start"])  # a leading `-` never gets past argparse
def test_a_change_id_must_start_alphanumeric_and_hold_no_dotdot(tmp_path: Path, name: str) -> None:
    repo = _repo(tmp_path, ["true"])
    (repo / "changes" / name).mkdir(exist_ok=True)
    r = _gate(repo, "milestone", name)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env" and "change id" in r.stdout


def test_a_change_path_outside_the_changes_folder_is_refused(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    (repo / "outside").mkdir()
    r = _gate(repo, "milestone", "../outside")
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env" and "change id" in r.stdout
    assert not (repo / "outside" / "verify").exists()


@pytest.mark.parametrize("branch", ["-x", "a/../b", "../x", "a//b"])
def test_a_default_branch_must_not_lead_with_a_dash_or_hold_a_dotdot_component(
    tmp_path: Path, branch: str
) -> None:
    repo = _milestone_repo(tmp_path)
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "defaultBranch": branch}))
    r = _gate(repo, "milestone", ID)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env" and "defaultBranch" in r.stdout


def test_expand_quotes_what_it_substitutes() -> None:
    sys.path.insert(0, str(GATE.parent))
    import verify_gate

    assert verify_gate.expand("git diff {base} {id}", "x-1", {"defaultBranch": "feat/a"}) == (
        "git diff origin/feat/a x-1"
    )
    assert verify_gate.shlex.quote("a b") == "'a b'"
    src = GATE.read_text()
    assert "shlex.quote(" in src.split("def expand", 1)[1].split("def ", 1)[0]


# --- Review (security): current-format changes cannot lose the records the gate derives from ----


def test_an_unparsable_done_json_is_refused_at_approval(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": ["true"]}}))
    (repo / "changes" / ID / "done.json").write_text("{not json")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "broken facts")
    r = _gate(repo, "approve", ID)
    assert r.returncode == 1 and "done.json" in r.stdout


def test_an_unparsable_done_json_after_approval_blocks_as_a_moved_lock(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    (repo / "changes" / ID / "done.json").write_text("{not json")
    _git(repo, "commit", "-qam", "broken facts")
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=protected-path"


def test_a_legacy_change_without_done_json_keeps_the_old_behaviour(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": ["true"]}}))
    (repo / "changes" / ID / "done.json").unlink()
    (repo / "changes" / ID / "validation.md").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "legacy")
    lock = {"approved_at": "x", "sha": "", "criteria": criteria_of_legacy(repo)}  # a pre-format lock
    (repo / "changes" / ID / "lock.json").write_text(json.dumps(lock))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "old lock")
    assert _last(_gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")


def criteria_of_legacy(repo: Path) -> dict:
    def digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    change = repo / "changes" / ID
    return {
        "facts.md": digest((change / "facts.md").read_bytes()),
        "checks": digest(json.dumps(json.loads((repo / "sdlc.json").read_text())["checks"], sort_keys=True).encode()),
    }


def test_a_missing_decisions_json_on_a_current_format_change_blocks(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    (repo / "changes" / ID / "decisions.json").unlink()  # present at approval, gone later: a moved lock
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "no decisions")
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=protected-path"


def test_a_decisions_json_that_never_existed_fails_the_check_on_a_current_format_change(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": ["true"]}}))
    (repo / "changes" / ID / "decisions.json").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "no decisions")
    _approve(repo)
    assert _last(_gate(repo, "milestone", ID)) == f"VERIFY FAIL milestone {ID} check=decisions-json"


@pytest.mark.parametrize("content", ["{broken", "[]", "null", '"s"'])
def test_an_unparsable_or_non_object_decisions_json_after_approval_blocks(
    tmp_path: Path, content: str
) -> None:
    repo = _milestone_repo(tmp_path)
    (repo / "changes" / ID / "decisions.json").write_text(content)
    _git(repo, "commit", "-qam", "odd decisions")
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=protected-path"  # routing is locked


PLAN2 = "## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n| M1 a | F1 | none |\n"


@pytest.mark.parametrize(
    "plan",
    [
        "## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n| M2 b | F2 | none |\n",  # no M1 row
        "## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n| M1 a | none | none |\n",  # no facts
        "",  # no plan at all
    ],
)
def test_a_milestone_branch_whose_plan_row_is_missing_or_empty_blocks(tmp_path: Path, plan: str) -> None:
    repo = _facts_repo(tmp_path, ["F1"], plan)
    _git(repo, "checkout", "-q", "-b", "milestone/trial-1")
    r = _gate(repo, "milestone", ID)
    assert _last(r) == "VERIFY BLOCKED reason=validation-not-met" and "M1" in r.stdout


def test_the_plan_milestones_section_is_part_of_the_approval_lock(tmp_path: Path) -> None:
    repo = _facts_repo(tmp_path, ["F1"], PLAN2)
    lock = json.loads((repo / "changes" / ID / "lock.json").read_text())
    assert "plan.milestones" in lock["criteria"]
    (repo / "changes" / ID / "plan.md").write_text(PLAN2.replace("| F1 |", "| F9 |"))
    _git(repo, "commit", "-qam", "move the milestone rows")
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=protected-path"


def test_an_old_lock_without_the_plan_hash_reports_an_upgrade_gap_and_still_runs(
    tmp_path: Path,
) -> None:
    repo = _facts_repo(tmp_path, ["F1"], PLAN2)
    path = repo / "changes" / ID / "lock.json"
    lock = json.loads(path.read_text())
    del lock["criteria"]["plan.milestones"]
    path.write_text(json.dumps(lock))
    _git(repo, "commit", "-qam", "an older lock")
    r = _gate(repo, "milestone", ID)
    assert "upgrade gap" in r.stdout and "plan.milestones" in r.stdout
    assert _last(r).startswith(f"VERIFY PASS milestone {ID}")


def test_a_new_approval_requires_the_capture_manifest_for_visual_work(tmp_path: Path) -> None:
    """Review finding 12: the version boundary lives in the lock; an older lock lacks the key."""
    repo = _repo(tmp_path, ["true"])
    _approve(repo)
    assert json.loads((repo / "changes" / ID / "lock.json").read_text())["manifest"] == "required"


def test_a_filled_copy_of_the_real_templates_is_approved_F9(tmp_path: Path) -> None:
    """The shipped instructions stay in a filled copy, so they must pass the gate they ship with:
    placeholders are filled and the one open-question marker is answered, nothing else is touched."""
    import re

    repo = _repo(tmp_path, ["true"])
    change = repo / "changes" / ID
    values = {"AUTHOR": "me", "CHANGE": ID, "DATE": "2026-11-19", "DESIGN": "none", "LINEAR": "none"}
    values |= {"TITLE": "Trial", "VERIFY": "make test"}
    for name in ("intent.md", "facts.md", "plan.md", "done.json"):
        text = (SKILL / "templates" / "change" / name).read_text()
        text = re.sub(r"\{\{(\w+)\}\}", lambda m: values.get(m.group(1), m.group(0)), text)
        text = re.sub(r"<(?!/?details|/?summary|!--)[^<>\n]*>", "filled", text)  # the writer's words
        text = text.replace("- [ ] [NEEDS CLARIFICATION: filled]\n", "none\n")  # answered
        (change / name).write_text(text)
    r = _gate(repo, "approve", ID)
    assert r.returncode == 0, r.stdout


def test_an_open_question_in_running_text_still_blocks_but_one_in_code_does_not_F9(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, ["true"])
    plan = repo / "changes" / ID / "plan.md"
    plan.write_text("Use `[NEEDS CLARIFICATION: x]` to mark one.\n")
    assert _gate(repo, "lint", ID).returncode == 0
    plan.write_text("Short.\n- [ ] [NEEDS CLARIFICATION: who?]\n")
    assert "an open [NEEDS CLARIFICATION]" in _gate(repo, "lint", ID).stdout


def test_the_gate_and_every_hook_keep_a_clean_tree_clean_F13(tmp_path: Path) -> None:
    """Imports of sibling helpers must not leave __pycache__ in the repo the gate runs in."""
    repo = _local_repo(tmp_path)
    scripts = repo / "scripts"
    scripts.mkdir()
    for name in ("verify_gate.py", "marks.py", "sdlc_version.py", "spec.py"):
        (scripts / name).write_text((GATE.parent / name).read_text())
    (repo / ".gitignore").write_text("/changes/*/verify/\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "installed")
    r = subprocess.run(
        [sys.executable, "scripts/verify_gate.py", "lint", ID],
        cwd=repo, capture_output=True, text=True,
        env={k: v for k, v in _env().items() if k != "PYTHONDONTWRITEBYTECODE"},
    )  # fmt: skip
    assert r.returncode == 0, r.stdout
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
    ).stdout
    assert status == ""
    hooks = GATE.parents[1] / "hooks"
    for hook in sorted(hooks.glob("*.sh")):
        if hook.name not in ("sdlc-config.sh", "plan-gate.sh"):
            assert "PYTHONDONTWRITEBYTECODE=1" in hook.read_text(), hook.name
    assert "PYTHONDONTWRITEBYTECODE=1" in (hooks / "sdlc-config.sh").read_text()


def test_a_kept_legacy_marks_py_blocks_the_milestone_gate_and_names_the_upgrade_H5(
    tmp_path: Path,
) -> None:
    """A marks.py with no `bundles` cannot inventory design bundles: that is a blocked gate, never
    an empty inventory that lets an unrendered bundle pass."""
    old = tmp_path / "scripts"
    old.mkdir()
    for f in GATE.parent.glob("*.py"):
        (old / f.name).write_text(f.read_text())
    (old / "marks.py").write_text("def sessions(change):\n    return []\n")
    repo = _repo(tmp_path, ["true"])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": ["true"]}}))
    bundle = repo / "changes" / ID / "asks" / "export"
    bundle.mkdir(parents=True)
    (bundle / "index.html").write_text("<html>screen</html>")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "a bundle nobody rendered")
    gate = [sys.executable, str(old / "verify_gate.py")]
    approve = subprocess.run([*gate, "approve", ID], cwd=repo, capture_output=True, text=True, env=_env())
    assert approve.returncode == 0, approve.stdout
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "approved")
    r = subprocess.run([*gate, "milestone", ID], cwd=repo, capture_output=True, text=True, env=_env())
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env", r.stdout
    assert "scripts/marks.py" in r.stdout and "adopt --upgrade --replace scripts/marks.py" in r.stdout
    assert r.stdout.index("remove it from `keep`") < r.stdout.index("adopt --upgrade --replace")  # keep first


def test_a_kept_legacy_marks_py_blocks_only_a_milestone_with_design_inputs(tmp_path: Path) -> None:
    """A code-only milestone has nothing for the old marks.py to miss: it passes."""
    old = tmp_path / "scripts"
    old.mkdir()
    for f in GATE.parent.glob("*.py"):
        (old / f.name).write_text(f.read_text())
    (old / "marks.py").write_text("def sessions(change):\n    return []\n")
    repo = _repo(tmp_path, ["true"])
    cfg = json.loads((repo / "sdlc.json").read_text())
    (repo / "sdlc.json").write_text(json.dumps({**cfg, "checks": {"milestone": ["true"]}}))
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "code only")
    gate = [sys.executable, str(old / "verify_gate.py")]
    assert subprocess.run([*gate, "approve", ID], cwd=repo, capture_output=True, env=_env()).returncode == 0
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "approved")
    r = subprocess.run([*gate, "milestone", ID], cwd=repo, capture_output=True, text=True, env=_env())
    assert r.returncode == 0 and _last(r).startswith(f"VERIFY PASS milestone {ID}"), r.stdout


def test_an_open_question_inside_a_gherkin_block_still_blocks_approval_M5(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    facts = repo / "changes" / ID / "facts.md"
    scenario = "```gherkin\nScenario: list\n  Then the list shows {}\n```\n"
    facts.write_text("---\nstatus: approved\n---\n\n" + scenario.format("[NEEDS CLARIFICATION: how many rows?]"))
    r = _gate(repo, "lint", ID)
    assert r.returncode == 1 and "facts.md: an open [NEEDS CLARIFICATION]" in r.stdout
    assert _gate(repo, "approve", ID).returncode == 1
    # the template's own instruction text is not a question
    facts.write_text("---\nstatus: approved\n---\n\n" + scenario.format("[NEEDS CLARIFICATION: <question>]"))
    assert _gate(repo, "lint", ID).returncode == 0


def test_an_open_question_with_angle_brackets_is_not_the_placeholder_M5(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    facts = repo / "changes" / ID / "facts.md"
    scenario = "```gherkin\nScenario: list\n  Then {}\n```\n"
    facts.write_text("---\nstatus: approved\n---\n\n" + scenario.format("[NEEDS CLARIFICATION: <admin or owner?>]"))
    r = _gate(repo, "lint", ID)
    assert r.returncode == 1 and "facts.md: an open [NEEDS CLARIFICATION]" in r.stdout
    facts.write_text("---\nstatus: approved\n---\n\n" + scenario.format("[NEEDS CLARIFICATION: ...]"))
    assert _gate(repo, "lint", ID).returncode == 0  # the template's own two placeholders stay free




# 3.20.5: the report binds a pass to its change, milestone number and owning project.
@pytest.mark.parametrize(
    ("branch", "prefix", "number"),
    [("milestone/trial-2", "milestone/", 2), ("milestone/trial", "milestone/", 1), ("ms/trial-3", "ms/", 3)],
)
def test_a_milestone_report_names_its_change_milestone_and_owner_3_20_5(
    tmp_path: Path, branch: str, prefix: str, number: int
) -> None:
    repo = _repo(tmp_path, ["true"])
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg = {**cfg, "checks": {"milestone": ["true"]}, "milestones": {"branchPrefix": prefix}}
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    _git(repo, "commit", "-qam", "milestone checks")
    _git(repo, "checkout", "-qb", branch)
    (repo / "changes" / ID / "plan.md").write_text(
        f"## Milestones\n\n| Milestone | Features | needs |\n|---|---|---|\n| M{number} a | F1 | none |\n"
    )
    _git(repo, "commit", "-qam", "plan row")
    _approve(repo)
    r = _gate(repo, "milestone", ID)
    assert _last(r).startswith(f"VERIFY PASS milestone {ID}"), r.stdout
    verify = repo / "changes" / ID / "verify"
    for name in ("report.json", f"milestone-{number}.json"):
        data = json.loads((verify / name).read_text())
        assert (data["change"], data["milestone"], data["owner"]) == (ID, number, ""), name


def test_a_feature_report_names_its_change_and_a_project_report_none_3_20_5(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    _approve(repo)
    assert _last(_gate(repo, "feature", ID)).startswith("VERIFY PASS")
    data = json.loads((repo / "changes" / ID / "verify" / "report.json").read_text())
    assert data["change"] == ID and "milestone" not in data


def test_approve_records_the_layout_in_the_lock(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    _approve(repo)
    assert json.loads((repo / "changes" / ID / "lock.json").read_text())["layout"] == 3


def _installed_gate(tmp_path: Path, heavy: str | None) -> Path:
    """A copy of the gate's scripts folder, as a repo installs it, with `heavy` as scripts/heavy.py."""
    import shutil

    dest = tmp_path / "installed"
    shutil.copytree(GATE.parent, dest, ignore=shutil.ignore_patterns("__pycache__"))
    if heavy is not None:
        (dest / "heavy.py").write_text(heavy)
    return dest / "verify_gate.py"


def test_the_gate_refuses_a_heavy_py_that_is_not_a_kit_version(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    _approve(repo)
    own = _installed_gate(tmp_path, "import sys\nsys.exit(0)\n")  # exits zero without running the check
    r = subprocess.run([sys.executable, str(own), "feature", ID], cwd=repo, capture_output=True, text=True, env=_env())
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=env"
    assert "heavy.py" in r.stdout and not (repo / "changes" / ID / "verify" / "report.json").exists()


def test_the_gate_runs_with_the_kit_heavy_py_or_none(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    _approve(repo)
    for name, heavy in (("kit", None), ("none", "")):
        gate = _installed_gate(tmp_path / name, heavy)
        if heavy == "":
            gate.with_name("heavy.py").unlink()
        r = subprocess.run([sys.executable, str(gate), "feature", ID], cwd=repo, capture_output=True, text=True, env=_env())
        assert r.returncode == 0, (name, r.stdout)


def test_the_gates_heavy_hashes_are_adopts() -> None:
    import adopt

    gate = (GATE).read_text()
    assert set(re.findall(r'"([0-9a-f]{16})"', re.search(r"^KIT_HEAVY = \{(.*?)\}", gate, re.M | re.S).group(1))) == adopt.KIT_HEAVY


def _pkg(repo: Path, rel: str, version: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"dependencies": {"@acme/ds": version}}))


def _ds_repo(tmp_path: Path, **ds: object) -> Path:
    repo = _repo(tmp_path, ["true"])
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["designSystem"] = {
        "package": "@acme/ds",
        "consumers": ["package.json", "apps/x/package.json"],
        **ds,
    }
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    _pkg(repo, "package.json", "1.2.0")
    _pkg(repo, "apps/x/package.json", "1.2.0")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "ds")
    return repo


def _lock(repo: Path) -> dict:
    return json.loads((repo / "changes" / ID / "lock.json").read_text())


def _screens(repo: Path, n: int) -> None:
    bundle = repo / "changes" / ID / "asks" / "bundle"
    bundle.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        (bundle / f"s{i}.html").write_text("<html></html>")
    decisions = repo / "changes" / ID / "decisions.json"
    decisions.write_text(json.dumps({"size": "S", "visualSource": {"path": "asks/bundle"}}))
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "screens")


SCREENS = [
    {"id": f"{s}.list.{st}", "route": f"/preview/{s}?state={st}", "viewport": [1440, 900], "fixture": "seed-1"}
    for s in ("leads", "deals")
    for st in ("empty", "full")
]


def _screens_json(repo: Path, entries: list | None = None) -> None:
    (repo / "changes" / ID / "screens.json").write_text(json.dumps(SCREENS if entries is None else entries))
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "screens.json")


def test_approval_locks_the_app_flow_the_screens_and_the_design_system_pin(tmp_path: Path) -> None:
    repo = _ds_repo(tmp_path)
    _screens_json(repo)
    (repo / "changes" / ID / "plan.md").write_text(
        (repo / "changes" / ID / "plan.md").read_text() + "\n## Where things go\n\n- `src/screens/`: x\n- `../out/`: y\n"
    )
    _approve(repo)
    lock = _lock(repo)
    assert lock["visual"] == "app" and "screens" not in lock
    assert lock["criteria"]["screens.json"] == hashlib.sha256((repo / "changes" / ID / "screens.json").read_bytes()).hexdigest()
    assert lock["scopeFolders"] == ["src/screens"]
    assert lock["designSystem"]["version"] == "1.2.0"


def _design_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boards: tuple[str, ...] = ("b1", "b2", "b3")) -> Path:
    """The change has a design source with three boards; the first two screens map b1 and b2, b3 is unmapped."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))  # where the owner's answers are read
    repo = _repo(tmp_path, [])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"milestone": ["true"]}, "ux": "on"}))
    change = repo / "changes" / ID
    (change / "decisions.json").write_text(json.dumps(VISUAL))
    rows = [{**r, "design": [b]} if b else r for r, b in zip(SCREENS, ("b1", "b2", "", ""))]
    (change / "design.json").write_text(json.dumps({"source": "https://design.example/f/1", "boards": [{"id": b, "name": f"Board {b}"} for b in boards]}))
    _screens_json(repo, rows)
    return repo


def _design(repo: Path, **fields: object) -> None:
    path = repo / "changes" / ID / "design.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), **fields}))
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "design.json")


def test_the_design_is_binding_for_which_screens_exist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from capture import inventory_id

    repo = _design_repo(tmp_path, monkeypatch)
    r = _gate(repo, "approve", ID)  # three boards, two mapped, one not
    assert r.returncode == 1 and "board b3 is mapped by no screens.json entry and is not dropped" in r.stdout
    _design(repo, boards=[{"id": b, "name": b} for b in ("b1", "b2")])
    rows = json.loads((repo / "changes" / ID / "screens.json").read_text())
    rows[2]["design"] = ["b9"]
    _screens_json(repo, rows)
    assert "entry deals.list.empty maps board b9, which design.json does not list" in _gate(repo, "approve", ID).stdout
    rows[2].pop("design")
    _screens_json(repo, rows)
    refused = _gate(repo, "approve", ID)  # two boards, both mapped, but nobody confirmed the inventory
    iid = inventory_id(json.loads((repo / "changes" / ID / "design.json").read_text()))
    assert refused.returncode == 1 and "an agent cannot confirm" in refused.stdout and f"finding {iid}: these 2 boards are the whole design" in refused.stdout
    _confirm_inventory(repo)
    assert _gate(repo, "approve", ID).returncode == 0
    (repo / "changes" / ID / "lock.json").unlink()
    _design(repo, boards=[{"id": b, "name": b} for b in ("b1", "b2", "b3")], dropped=[{"board": "b3", "reason": "the detail panel replaces it"}])
    refused = _gate(repo, "approve", ID)  # the answer for the old list covers nothing here: one dialog for boards and dropped list
    assert refused.returncode == 1 and "or drop 1 of them" in refused.stdout and "dropped: b3 (the detail panel replaces it)" in refused.stdout
    _confirm_inventory(repo)
    assert _gate(repo, "approve", ID).returncode == 0
    lock = _lock(repo)
    assert lock["design"] == "inventory" and lock["inventory"].startswith("inventory-") and "design.json" in lock["criteria"]
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "approved")
    _design(repo, dropped=[{"board": "b3", "reason": "changed after the owner said yes"}])  # the list the owner saw is locked
    r = _gate(repo, "milestone", ID)
    assert _last(r) == "VERIFY BLOCKED reason=protected-path" and "design.json" in r.stdout


def test_a_design_input_makes_it_an_app_change_whatever_the_size_and_an_empty_folder_is_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    repo = _repo(tmp_path, [])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"milestone": ["true"]}, "ux": "on"}))
    change = repo / "changes" / ID
    (change / "decisions.json").write_text(json.dumps({"size": "M"}))
    (change / "asks" / "design").mkdir(parents=True)
    assert _gate(repo, "approve", ID).returncode == 0  # an empty asks/design/ is no design input
    (change / "asks" / "design" / "checkout.fig").write_bytes(b"x")
    r = _gate(repo, "approve", ID)  # a design file, no visualSource, no screens.json
    assert r.returncode == 1 and "screens.json is missing" in r.stdout


def test_a_board_image_is_locked_and_a_changed_one_stops_the_gallery_and_the_close(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _design_repo(tmp_path, monkeypatch, boards=("b1", "b2"))
    change = repo / "changes" / ID
    (change / "asks" / "design").mkdir(parents=True)
    (change / "asks" / "design" / "b1.png").write_bytes(b"one")
    _design(repo, boards=[{"id": "b1", "name": "b1", "image": "asks/design/b1.png"}, {"id": "b2", "name": "b2"}])
    _confirm_inventory(repo)
    assert _gate(repo, "approve", ID).returncode == 0
    assert _lock(repo)["designImages"] == {"b1": hashlib.sha256(b"one").hexdigest()}
    (change / "asks" / "design" / "b1.png").write_bytes(b"two")
    import capture

    assert capture.image_problems(change) == ["board b1: its image changed or is missing since approval (approval locked it)"]
    sys.path.insert(0, str(GATE.parent))
    r = subprocess.run([sys.executable, str(GATE.parent / "evidence.py"), "gallery", str(change)], cwd=repo, capture_output=True, text=True)
    assert r.returncode == 1 and "board b1: its image changed" in r.stderr


def test_an_older_lock_keeps_its_hash_algorithm_even_when_design_json_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sys.path.insert(0, str(GATE.parent))
    import verify_gate

    repo = _design_repo(tmp_path, monkeypatch, boards=("b1", "b2"))
    change = repo / "changes" / ID
    old = verify_gate.criteria_hash(change, {}, design=False)
    assert "design.json" not in old and old["screens.json"] == hashlib.sha256((change / "screens.json").read_bytes()).hexdigest()
    assert "design.json" in verify_gate.criteria_hash(change, {}, design=True)


def test_a_deviation_is_the_one_field_the_build_may_add_after_approval(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = _design_repo(tmp_path, monkeypatch, boards=("b1", "b2"))
    _confirm_inventory(repo)
    _approve(repo)
    rows = json.loads((repo / "changes" / ID / "screens.json").read_text())
    rows[0]["deviates"] = "the list has one column less: the owner's screenshot shows it"
    _screens_json(repo, rows)
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=env"  # not protected-path: the approval holds
    rows[0]["route"] = "/preview/elsewhere"
    _screens_json(repo, rows)
    assert _last(_gate(repo, "milestone", ID)) == "VERIFY BLOCKED reason=protected-path"


def test_a_visual_change_without_screens_json_is_refused_at_approval(tmp_path: Path) -> None:
    repo = _visual_repo_unapproved(tmp_path, VISUAL)
    r = _gate(repo, "approve", ID)
    assert r.returncode == 1 and "screens.json is missing" in r.stdout


def test_a_bad_screens_json_is_refused_at_approval(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    _screens_json(repo, [{"id": "a", "route": "nope", "viewport": [1, 1], "fixture": "f"}])
    r = _gate(repo, "approve", ID)
    assert r.returncode == 1 and "route must start" in r.stdout


def test_many_screens_need_no_design_system_audit_in_the_app_flow(tmp_path: Path) -> None:
    repo = _ds_repo(tmp_path, auditAbove=2)
    _screens_json(repo, [{**SCREENS[0], "id": f"s{i}", "route": f"/preview/s{i}"} for i in range(30)])
    assert _gate(repo, "approve", ID).returncode == 0


def test_editing_screens_json_after_approval_blocks_the_milestone(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"milestone": ["true"]}}))
    _screens_json(repo)
    _approve(repo)
    _screens_json(repo, SCREENS[:1])
    r = _gate(repo, "milestone", ID)
    assert _last(r) == "VERIFY BLOCKED reason=protected-path" and "screens.json" in r.stdout


def test_an_app_milestone_runs_the_capture_and_never_the_bundle_checks(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"milestone": ["true"]}, "ux": "on"}))
    (repo / "changes" / ID / "decisions.json").write_text(json.dumps(VISUAL))
    _screens_json(repo)
    _approve(repo)  # no visual run, no marks rows, no bundle: only screens.json
    r = _gate(repo, "milestone", ID)
    names = [c["name"] for c in json.loads((repo / "changes" / ID / "verify/report.json").read_text())["checks"]]
    assert names[:1] == ["app-screens"] and "owner-marks" not in names and "ux-visual-required" not in names
    assert _last(r) == "VERIFY BLOCKED reason=env" and "visual.start" in r.stdout  # no app configured here


def test_no_design_system_key_or_no_visual_work_records_nothing(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    _approve(repo)
    assert "designSystem" not in _lock(repo) and "screens" not in _lock(repo)


def test_a_moved_pin_blocks_the_milestone_until_reapproved(tmp_path: Path) -> None:
    repo = _ds_repo(tmp_path)
    _screens(repo, 2)
    _approve_legacy(repo)
    _pkg(repo, "apps/x/package.json", "1.3.0")
    _git(repo, "commit", "-qam", "bump")
    r = _gate(repo, "milestone", ID)
    assert _last(r) == "VERIFY BLOCKED reason=protected-path"
    assert "the design system moved from 1.2.0 to 1.3.0 in apps/x/package.json" in r.stdout
    assert "re-approve with the new release" in r.stdout
    _pkg(repo, "package.json", "1.3.0")  # re-approval locks the new release
    _git(repo, "commit", "-qam", "bump root")
    _screens_json(repo)  # a re-approval from 3.25.0 on is an app approval: it needs screens.json
    assert _gate(repo, "approve", ID).returncode == 0
    assert _lock(repo)["designSystem"]["version"] == "1.3.0"


def test_the_milestone_schedules_marks_from_the_lock_not_from_the_inputs(tmp_path: Path) -> None:
    repo = _visual_repo(tmp_path, VISUAL)  # a visual source, but nothing under asks/ yet
    assert _lock(repo)["screens"] == "required"
    _gate(repo, "milestone", ID)
    names = [c["name"] for c in json.loads((repo / "changes" / ID / "verify/report.json").read_text())["checks"]]
    assert "owner-marks" in names
    (repo / "changes" / ID / "asks").mkdir()
    (repo / "changes" / ID / "asks/home.png").write_bytes(b"x")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "reference")
    r = _gate(repo, "milestone", ID)
    assert _last(r) == f"VERIFY FAIL milestone {ID} check=owner-marks"


def test_a_screens_milestone_is_blocked_when_the_installed_marks_cannot_check_screens(tmp_path: Path) -> None:
    repo = _visual_repo(tmp_path, VISUAL)
    scripts = tmp_path / "old-scripts"
    scripts.mkdir()
    for f in GATE.parent.glob("*.py"):
        (scripts / f.name).write_text(f.read_text())
    marks = (scripts / "marks.py").read_text().replace("def screens_check(", "def renamed_screens_check(")
    (scripts / "marks.py").write_text(marks)
    r = subprocess.run([sys.executable, str(scripts / "verify_gate.py"), "milestone", ID], cwd=repo, capture_output=True, text=True, env=_env())
    assert _last(r) == "VERIFY BLOCKED reason=env" and "cannot check per-screen records" in r.stdout


def test_dirty_screen_records_block_a_close(tmp_path: Path) -> None:
    repo = _visual_repo(tmp_path, VISUAL)
    screens = repo / "changes" / ID / "screens"
    screens.mkdir()
    (screens / "home.json").write_text("{}")
    r = _gate(repo, "milestone", ID)
    assert _last(r).endswith("check=uncommitted") and f"{ID}/screens/home.json" in r.stdout


def test_has_visual_source_ignores_none_and_empty() -> None:
    sys.path.insert(0, str(GATE.parent))
    import verify_gate

    for no in (None, "", "none", " None ", {}, {"kind": "none"}, {"kind": "None", "path": "x"}):
        assert not verify_gate.has_visual_source(no), no
    for yes in ("https://example.test/d", {"kind": "images", "path": "asks"}, {"path": "asks"}):
        assert verify_gate.has_visual_source(yes), yes


def _lockfile(repo: Path, rel: str, text: str) -> None:
    (repo / rel).write_text(text)
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "lockfile")


NPM_LOCK = '{"lockfileVersion": 3, "packages": {"node_modules/@acme/ds": {"version": "%s"}}}'


def test_the_pin_records_the_resolved_version_and_a_lockfile_move_blocks(tmp_path: Path) -> None:
    repo = _ds_repo(tmp_path)
    _pkg(repo, "package.json", "^1.2.0")
    _pkg(repo, "apps/x/package.json", "^1.2.0")
    _lockfile(repo, "package-lock.json", NPM_LOCK % "1.2.4")
    _screens(repo, 2)
    _approve_legacy(repo)
    ds = _lock(repo)["designSystem"]
    assert ds["version"] == "1.2.4" and [c["resolved"] for c in ds["consumers"]] == ["1.2.4", "1.2.4"]
    _lockfile(repo, "package-lock.json", NPM_LOCK % "1.2.9")  # the range is unchanged, the install moved
    r = _gate(repo, "milestone", ID)
    assert _last(r) == "VERIFY BLOCKED reason=protected-path"
    assert "the design system moved from 1.2.4 to 1.2.9 in package.json" in r.stdout


def test_another_package_or_an_unchecked_consumer_blocks_the_milestone(tmp_path: Path) -> None:
    repo = _ds_repo(tmp_path)
    _screens(repo, 2)
    _approve_legacy(repo)
    cfg = json.loads((repo / "sdlc.json").read_text())
    cfg["designSystem"]["consumers"].append("apps/y/package.json")
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    _pkg(repo, "apps/y/package.json", "1.2.0")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "y")
    r = _gate(repo, "milestone", ID)
    assert _last(r) == "VERIFY BLOCKED reason=protected-path" and "also used in apps/y/package.json" in r.stdout
    cfg["designSystem"]["consumers"].pop()
    cfg["designSystem"]["package"] = "@other/ds"
    (repo / "sdlc.json").write_text(json.dumps(cfg))
    sys.path.insert(0, str(GATE.parent))
    import verify_gate

    moves = verify_gate.design_system_moves(_lock(repo), cfg, repo)
    assert any("package moved from @acme/ds to @other/ds" in m for m in moves)


def test_lockfile_readers_for_pnpm_and_yarn(tmp_path: Path) -> None:
    sys.path.insert(0, str(GATE.parent))
    import verify_gate

    pnpm = "importers:\n  .:\n    dependencies:\n      '@acme/ds':\n        specifier: ^1.2.0\n        version: 1.2.5(react@18.0.0)\n  apps/x:\n    dependencies:\n      '@acme/ds':\n        specifier: ^1.2.0\n        version: 1.2.7\n"
    assert verify_gate._lock_version("pnpm-lock.yaml", pnpm, "@acme/ds", ".", "^1.2.0") == "1.2.5"
    assert verify_gate._lock_version("pnpm-lock.yaml", pnpm, "@acme/ds", "apps/x", "^1.2.0") == "1.2.7"
    classic = '"@acme/ds@^1.2.0", "@acme/ds@^1.0.0":\n  version "1.2.6"\n  resolved "x"\n\nother@^1:\n  version "9.9.9"\n'
    assert verify_gate._lock_version("yarn.lock", classic, "@acme/ds", ".", "^1.2.0") == "1.2.6"
    berry = '"@acme/ds@npm:^1.2.0":\n  version: 1.2.8\n  resolution: "x"\n'
    assert verify_gate._lock_version("yarn.lock", berry, "@acme/ds", ".", "^1.2.0") == "1.2.8"




def test_the_milestone_gate_captures_the_fixture_app_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Close job: one app start, every entry twice; no baseline blocks, an approved baseline passes,
    a changed page fails with the entry name. The browser is the fake driver of test_capture.py."""
    import hashlib

    import test_capture as tc

    monkeypatch.setenv("HOME", str(tmp_path / "home"))  # where the owner's answers are read
    repo = _repo(tmp_path, [])
    (repo / "app.py").write_text(tc.APP)
    (repo / "driver.py").write_text(tc.DRIVER)
    visual = {"start": f"{sys.executable} app.py", "driver": f"{sys.executable} driver.py", "startTimeout": 20}
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"milestone": ["true"]}, "ux": "on", "visual": visual}))
    _screens_json(repo, tc.ENTRIES)
    _approve(repo)
    r = _gate(repo, "milestone", ID)
    assert _last(r) == "VERIFY BLOCKED reason=needs-baseline" and "4 of 4 entries have no approved shot" in r.stdout
    change = repo / "changes" / ID
    (change / "screens").mkdir()
    entries = {}
    for e in tc.ENTRIES:
        shot = change / "verify/shots" / f"{e['id']}.png"
        (change / "screens" / f"{e['id']}.png").write_bytes(shot.read_bytes())
        entries[e["id"]] = {"sha256": hashlib.sha256(shot.read_bytes()).hexdigest(), "file": f"screens/{e['id']}.png"}
    tc._seal(repo, {"format": 1, "entries": entries}, owner=False, change_id=ID)  # approved.json as an agent could write it
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "approved.json without the owner")
    r = _gate(repo, "milestone", ID)
    assert _last(r) == f"VERIFY FAIL milestone {ID} check=app-screens" and "no owner decision covers" in r.stdout
    tc.owner_answers(repo, next(iter(json.loads((change / "screens/approved.json").read_text())["batches"])), change_id=ID)
    r = _gate(repo, "milestone", ID)
    assert _last(r).startswith(f"VERIFY PASS milestone {ID}"), r.stdout
    (repo / "app.py").write_text(tc.APP.replace("'MARK', ''", "'MARK', 'x'"))
    _git(repo, "commit", "-qam", "the page changed")
    r = _gate(repo, "milestone", ID)
    assert _last(r) == f"VERIFY FAIL milestone {ID} check=app-screens"
    assert "leads.list.empty: differs from the approved shot" in r.stdout


def test_a_visual_hotfix_runs_the_capture_in_its_feature_gate(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"feature": ["true"]}}))
    (repo / "changes" / ID / "decisions.json").write_text(json.dumps({**VISUAL, "milestone": {"kind": "hotfix"}}))
    _screens_json(repo)
    _approve(repo)
    _git(repo, "checkout", "-qb", "hotfix/trial")
    r = _gate(repo, "feature", ID)
    names = [c["name"] for c in json.loads((repo / "changes" / ID / "verify/report.json").read_text())["checks"]]
    assert names[:1] == ["app-screens"], r.stdout
    assert _last(r) == "VERIFY BLOCKED reason=env" and "visual.start" in r.stdout  # no app configured here


def test_a_plain_feature_gate_of_an_app_change_does_not_capture(tmp_path: Path) -> None:
    repo = _repo(tmp_path, [])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"feature": ["true"]}}))
    _screens_json(repo)
    _approve(repo)
    r = _gate(repo, "feature", ID)
    names = [c["name"] for c in json.loads((repo / "changes" / ID / "verify/report.json").read_text())["checks"]]
    assert "app-screens" not in names, r.stdout


def test_an_early_milestone_asks_the_capture_only_for_the_entries_due(tmp_path: Path) -> None:
    sys.path.insert(0, str(GATE.parent))
    import verify_gate

    repo = _repo(tmp_path, [])  # the plan's milestones are M1 and M2
    change = repo / "changes" / ID
    assert verify_gate.capture_upto(change, 1) == 1  # M1 closes with the entries up to milestone 1
    assert verify_gate.capture_upto(change, 2) is None  # the last milestone requires every entry
    assert verify_gate.capture_upto(change, None) is None  # no number: everything
    (change / "plan.md").write_text("# no milestone table\n")
    assert verify_gate.capture_upto(change, 1) is None  # cannot tell which is last: require all
    (change / "tasks.md").write_text("## Milestones\n\n| Milestone | Tasks | needs |\n|---|---|---|\n| M1 a | T1 | none |\n| M2 b | T2 | M1 |\n")
    assert verify_gate.capture_upto(change, 1) == 1  # layout 4 keeps the table in tasks.md
