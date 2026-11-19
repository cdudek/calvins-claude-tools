"""Speed A close: the tier workflow's hold decision and the PR status table (no dead end)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
WORKFLOW = (SKILL / "templates/workflows/ship-show-ask.yml").read_text(encoding="utf-8")


def _classify_script(gates: bool = True) -> str:
    """The `Classify changed paths` run block with the template markers resolved."""
    text = re.sub(r"\{\{#(?:notify)\}\}.*?\{\{/notify\}\}", "", WORKFLOW, flags=re.S)
    keep, drop = ("ASK_GATES_MERGE", "ASK_MERGES_ON_GREEN") if gates else ("ASK_MERGES_ON_GREEN", "ASK_GATES_MERGE")
    text = re.sub(rf"\{{\{{#{drop}\}}\}}.*?\{{\{{/{drop}\}}\}}", "", text, flags=re.S)
    text = re.sub(rf"\{{\{{[#/]{keep}\}}\}}\n?", "", text)
    block = text.split("- name: Classify changed paths", 1)[1].split("run: |\n", 1)[1]
    block = block.split("      - name: Apply the one label", 1)[0]
    return "\n".join(line[10:] for line in block.splitlines())


def _run_classify(tmp_path: Path, labels: str | None, bot: str = "false") -> dict[str, str]:
    (tmp_path / "scripts").mkdir()
    (tmp_path / ".github").mkdir()
    (tmp_path / "scripts/ship_show_ask.py").write_text((SKILL / "templates/scripts/ship_show_ask.py").read_text())
    (tmp_path / ".github/tiers.json").write_text('{"order": ["ask", "show", "ship"], "ask": [], "show": [], "ship": ["*"]}')
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    lookup = "exit 1" if labels is None else f"printf '%s' '{labels}'"
    gh.write_text(f'#!/bin/sh\ncase "$*" in *labels*) {lookup} ;; *) echo a.md ;; esac\n')
    gh.chmod(0o755)
    out = tmp_path / "out"
    out.write_text("")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "PR": "1", "IS_BOT": bot, "GITHUB_OUTPUT": str(out)}
    subprocess.run(["bash", "-c", _classify_script()], cwd=tmp_path, env=env, capture_output=True, text=True)
    return dict(line.split("=", 1) for line in out.read_text().splitlines() if "=" in line)


@pytest.mark.parametrize(("labels", "arm"), [(None, "false"), ("hold", "false"), ("awaiting-owner", "false"), ("", "true")])
def test_the_hold_lookup_fails_closed(tmp_path: Path, labels: str | None, arm: str) -> None:
    assert _run_classify(tmp_path, labels)["arm"] == arm


def test_the_workflow_reacts_to_a_label_added_after_classification() -> None:
    assert re.search(r"types: \[[^\]]*\blabeled\b", WORKFLOW)
    assert "--disable-auto" in WORKFLOW  # a hold added to an armed PR disarms it


# --- no dead end: tier x armed x merged x owner answer x labels ---------------------------------

import itertools  # noqa: E402
import sys  # noqa: E402

from test_sdlc_status import BRANCH, ID, PASS, _gate, _goal, _pr, repo  # noqa: E402, F401

import sdlc_status  # noqa: E402

LABELS = [(), ("ask",), ("show",), ("ship",), ("ask", "hold"), ("show", "awaiting-owner"), ("ship", "hold")]
STATES = ["merged", "armed", "unarmed", "closed"]
ANSWERS = ["", "accepted", "hold"]
CASES = list(itertools.product(LABELS, STATES, ANSWERS, [False, True], [False, True]))


def _table_pr(labels: tuple, state: str, failed: bool) -> list:
    pr = _pr({"merged": "MERGED", "closed": "CLOSED"}.get(state, "OPEN"), armed=state == "armed", labels=labels)
    if failed:
        pr[0]["statusCheckRollup"] = [{"conclusion": "FAILURE"}]
    return pr


@pytest.mark.parametrize(("labels", "state", "answer", "workflow", "failed"), CASES)
def test_every_pr_state_is_done_or_names_a_command_that_leaves_it(
    repo: Path, monkeypatch, labels, state, answer, workflow, failed  # noqa: F811
) -> None:
    import marks

    monkeypatch.setattr(marks, "owner_decisions", lambda *a, **k: {"PR7": (answer, "")} if answer else {})
    if workflow:
        flow = repo / ".github" / "workflows"
        flow.mkdir(parents=True, exist_ok=True)
        (flow / "ship-show-ask.yml").write_text("name: tier\n")
    _gate(repo, PASS)
    code, line = _goal(repo, {BRANCH: _table_pr(labels, state, failed)})
    gating = "ask" in labels
    held = (answer == "hold" and state in ("armed", "unarmed")) or "hold" in labels  # a Hold blocks at any tier (open PRs are read)
    if code == 0:  # DONE: only a merged or an armed PR, never an unsigned ask, never a held one
        assert state in ("merged", "armed"), line
        assert not held, line
        assert not (gating and answer != "accepted"), line
        assert not (failed and state != "merged"), line
        assert state == "merged" or "awaiting-owner" not in labels or answer == "accepted", line
        return
    sentence = sdlc_status.blocker(ID, line)
    assert sentence.startswith("Blocking:") and "`" in sentence, f"{line!r} names no command: {sentence!r}"


def test_an_accepted_ask_pr_leaves_the_awaits_owner_state(repo: Path, monkeypatch) -> None:  # noqa: F811
    import marks

    _gate(repo, PASS)
    monkeypatch.setattr(marks, "owner_decisions", lambda *a, **k: {})
    assert _goal(repo, {BRANCH: _pr("OPEN", labels=("ask",))})[1].endswith("pr-7-awaits-owner")
    monkeypatch.setattr(marks, "owner_decisions", lambda *a, **k: {"PR7": ("accepted", "")})
    line = _goal(repo, {BRANCH: _pr("OPEN", labels=("ask",))})[1]
    assert line.endswith("pr-7-not-merged-or-armed")  # the workflow never arms ask: the agent does now
    assert "gh pr merge 7" in sdlc_status.blocker(ID, line)
