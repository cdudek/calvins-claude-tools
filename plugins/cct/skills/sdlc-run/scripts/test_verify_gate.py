"""verify_gate.py: the sentinel line, the criteria lock, the breaker, the stdout cap, the lint.
And the two /goal templates, which must stay short enough to read in one go."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
GATE = SKILL / "templates" / "scripts" / "verify_gate.py"
ID = "2026-10-09-trial"


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
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "init")
    return repo


def _gate(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE), *args], cwd=repo, capture_output=True, text=True, env=_env()
    )


def _approve(repo: Path) -> None:
    assert _gate(repo, "approve", ID).returncode == 0
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "approved")


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
DEFINED = (
    "| # | What |\n|---|---|\n"
    + "".join(f"| {i} | defined |\n" for i in ("Q202", "B19", "F13", "F14", "Q7", "A1", "F1000"))
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


@pytest.mark.parametrize("name", ["run", "feature", "milestone", "project"])
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


def test_milestone_gate_keeps_its_own_receipt_beside_report_json(tmp_path: Path) -> None:
    repo = _local_repo(tmp_path)
    _merge_milestone_one_locally(repo)
    _git(repo, "merge", "-q", "--no-edit", "project/big")
    assert _last(_gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")
    verify = repo / "changes" / ID / "verify"
    receipt = json.loads((verify / "milestone-2.json").read_text())
    assert receipt == json.loads((verify / "report.json").read_text())
    assert receipt["result"].startswith("VERIFY PASS milestone") and receipt["sha"]


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
TABLE = "## Dispositions\n\n| item | disposition | owner | reason |\n|---|---|---|---|\n"


@pytest.mark.parametrize("kind", ["accepted", "deferred"])
def test_a_named_owner_and_reason_settle_a_residual_finding(tmp_path: Path, kind: str) -> None:
    """3.21.0 (S2): the one fix round leaves a residual; accepted or deferred by a named owner
    with a reason is a disposition the gate understands, so the milestone can close."""
    repo = _milestone_repo(tmp_path)
    _commit_files(
        repo,
        validation_md="| F1 | x | y | z | met |\n",
        findings_md=OPEN_ITEM + TABLE + f"| B2 | {kind} | Dana | Low on a phone; M2 builds it |\n",
    )
    assert _last(_gate(repo, "milestone", ID)).startswith(f"VERIFY PASS milestone {ID}")


@pytest.mark.parametrize(
    "row",
    [
        "| B2 | accepted | | no reason given as owner |\n",
        "| B2 | deferred | Dana | |\n",
        "| B9 | accepted | Dana | wrong item |\n",
        "| B2 | fixed | Dana | a ticked box is the proof of a fix |\n",
    ],
)
def test_a_disposition_without_owner_reason_or_item_leaves_the_finding_open(
    tmp_path: Path, row: str
) -> None:
    repo = _milestone_repo(tmp_path)
    _commit_files(
        repo,
        validation_md="| F1 | x | y | z | met |\n",
        findings_md=OPEN_ITEM + TABLE + row,
    )
    r = _gate(repo, "milestone", ID)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=findings-open"


def test_a_blocked_disposition_is_terminal(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    _commit_files(
        repo,
        validation_md="| F1 | x | y | z | met |\n",
        findings_md=OPEN_ITEM + TABLE + "| B2 | blocked | Dana | needs a design-system release |\n",
    )
    r = _gate(repo, "milestone", ID)
    assert r.returncode == 3 and _last(r) == "VERIFY BLOCKED reason=findings-blocked"
    assert "B2" in r.stdout


def test_acceptance_never_turns_a_partly_met_fact_into_met(tmp_path: Path) -> None:
    repo = _milestone_repo(tmp_path)
    _commit_files(
        repo,
        validation_md="| F1 | x | y | z | partly |\n",
        findings_md=OPEN_ITEM + TABLE + "| F1 | accepted | Dana | good enough |\n",
    )
    r = _gate(repo, "milestone", ID)
    assert _last(r) == "VERIFY BLOCKED reason=validation-not-met"


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
    _approve(repo)
    result = _gate(repo, "milestone", ID)
    assert _last(result) == f"VERIFY FAIL milestone {ID} check=owner-marks"
    assert not ran.exists()


def test_a_supplied_bundle_requires_a_valid_ledger_at_milestone(tmp_path: Path) -> None:
    repo = _repo(tmp_path, ["true"])
    (repo / "sdlc.json").write_text(json.dumps({"checks": {"milestone": ["true"]}}))
    export = repo / "changes" / ID / "asks/export"
    export.mkdir(parents=True)
    (export / "index.html").write_text("<html>screen</html>")
    _approve(repo)
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
