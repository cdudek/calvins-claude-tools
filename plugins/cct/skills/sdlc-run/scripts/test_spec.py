"""Usage: pytest scripts/test_spec.py

spec.py: one file per rule, the drift check, renumbering, the local index, recall eval, the
three-document consistency check, and the exits for deadlocks D1, S1 and S3.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "templates" / "scripts"))
import spec  # noqa: E402


def sh(root: Path, *args: str) -> str:
    return subprocess.run(args, cwd=root, capture_output=True, text=True, check=True).stdout


def commit(root: Path, msg: str = "c") -> None:
    sh(root, "git", "add", "-A")
    sh(root, "git", "commit", "-q", "-m", msg)


def rule(root: Path, cap: str, n: int, text: str = "When x, the system shall y.", **meta) -> Path:
    d = root / "specs" / cap / "rules"
    d.mkdir(parents=True, exist_ok=True)
    fm = {"id": f"R{n}", "summary": text.split(".")[0], "status": "live", "proof": "test", **meta}
    p = d / f"R{n}.md"
    p.write_text("---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + f"---\n{text}\n")
    m = root / "specs" / cap / "manifest.yaml"
    if not m.exists():
        m.write_text(f"purpose: the {cap} area\naliases: []\ncode: [src/{cap}]\ntests: [tests]\n")
    return p


def tfile(root: Path, name: str, *lines: str) -> Path:
    p = root / "tests" / name
    p.parent.mkdir(exist_ok=True)
    p.write_text("\n".join(lines) + "\n")
    return p


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    sh(tmp_path, "git", "init", "-q", "-b", "main")
    sh(tmp_path, "git", "config", "user.email", "t@example.com")
    sh(tmp_path, "git", "config", "user.name", "t")
    (tmp_path / "README.md").write_text("x\n")
    commit(tmp_path, "init")
    return tmp_path


# ------------------------------------------------------------------ parsing, ids, tags


def test_flat_yaml_reads_scalars_lists_and_refuses_anything_else() -> None:
    got = spec.parse_flat("purpose: a b\naliases: [x, y]\ncode:\n  - src/a\n  - src/b\nowner: ")
    assert got == {"purpose": "a b", "aliases": ["x", "y"], "code": ["src/a", "src/b"], "owner": []}
    with pytest.raises(spec.SpecError):
        spec.parse_flat("a:\n  b: nested")


def test_tag_never_matches_a_longer_number_and_ids_sort_numerically(repo: Path) -> None:
    assert [int(m.group(1)) for m in spec.TAG.finditer("@R12 @R123 x@R9 @R1000")] == [12, 123, 1000]
    for n in (9, 10, 100):
        rule(repo, "a", n)
    assert [r.num for r in spec.load_rules(repo)[0]] == [9, 10, 100]


def test_next_id_is_the_highest_ever_used_plus_one_even_after_removal(repo: Path) -> None:
    rule(repo, "a", 7)
    rule(repo, "a", 8)
    commit(repo)
    (repo / "specs/a/rules/R8.md").unlink()
    commit(repo)
    assert spec.next_id(repo) == 9
    (repo / ".sdlc").mkdir()
    (repo / ".sdlc/last-rule-id").write_text("40\n")
    assert spec.next_id(repo) == 41


def test_a_moved_rule_keeps_its_history_for_the_next_id(repo: Path) -> None:
    rule(repo, "a", 5)
    commit(repo)
    (repo / "specs/b/rules").mkdir(parents=True)
    sh(repo, "git", "mv", "specs/a/rules/R5.md", "specs/b/rules/R5.md")
    commit(repo)
    assert spec.next_id(repo) == 6


# ------------------------------------------------------------------ check


def test_no_specs_dir_is_nothing_to_check(repo: Path) -> None:
    assert spec.check(repo) == []


def test_a_live_rule_needs_a_tagged_test_that_runs(repo: Path) -> None:
    rule(repo, "billing", 1)
    assert any("no test tagged @R1" in p for p in spec.check(repo))
    tfile(repo, "test_a.py", "# @R1", "def test_retry(): pass")
    assert spec.check(repo) == []
    tfile(repo, "test_a.py", "@pytest.mark.skip", "def test_retry():  # @R1", "    pass")
    assert any("only in skipped tests" in p for p in spec.check(repo))


def test_a_tag_without_a_rule_and_two_rules_with_one_number_fail(repo: Path) -> None:
    rule(repo, "a", 1)
    rule(repo, "b", 1)
    tfile(repo, "test_a.py", "# @R1 @R99")
    problems = " ".join(spec.check(repo))
    assert "R1 is in two places" in problems and "@R99" in problems


def test_manual_proof_needs_evidence_and_no_tag(repo: Path) -> None:
    rule(repo, "a", 1, proof="manual")
    assert any("needs `evidence:`" in p for p in spec.check(repo))
    rule(repo, "a", 1, proof="manual", evidence="support lead reads the report weekly")
    assert spec.check(repo) == []


def test_a_capability_needs_a_manifest_with_a_purpose(repo: Path) -> None:
    rule(repo, "a", 1)
    tfile(repo, "test_a.py", "# @R1")
    (repo / "specs/a/manifest.yaml").write_text("aliases: []\n")
    assert any("no purpose" in p for p in spec.check(repo))
    (repo / "specs/a/manifest.yaml").unlink()
    assert any("manifest.yaml is missing" in p for p in spec.check(repo))


def test_a_changed_rule_needs_a_changed_test_but_a_pure_move_does_not(repo: Path) -> None:
    rule(repo, "a", 1)
    rule(repo, "a", 2, text="When q, the system shall r.")
    tfile(repo, "test_a.py", "# @R1", "# @R2")
    commit(repo)
    sh(repo, "git", "checkout", "-q", "-b", "work")
    rule(repo, "a", 1, text="When x, the system shall z.")
    problems = spec.check(repo, "main")
    assert any("R1 changed but no test" in p for p in problems)
    tfile(repo, "test_a.py", "# @R1 now asserts z", "# @R2")
    assert spec.check(repo, "main") == []
    (repo / "specs/b/rules").mkdir(parents=True)
    (repo / "specs/b/manifest.yaml").write_text("purpose: b\n")
    sh(repo, "git", "mv", "specs/a/rules/R2.md", "specs/b/rules/R2.md")
    assert spec.changed_rules(repo, "main")["moved"] == [2]
    assert spec.check(repo, "main") == []


def test_a_removed_id_is_never_reused_and_a_taken_id_is_refused(repo: Path) -> None:
    rule(repo, "a", 1)
    rule(repo, "a", 2)
    tfile(repo, "test_a.py", "# @R1", "# @R2")
    commit(repo)
    (repo / "specs/a/rules/R2.md").unlink()
    tfile(repo, "test_a.py", "# @R1")
    commit(repo, "remove R2")
    sh(repo, "git", "checkout", "-q", "-b", "work")
    rule(repo, "a", 2)
    tfile(repo, "test_a.py", "# @R1", "# @R2")
    assert any("never reused" in p for p in spec.check(repo, "main"))


# ------------------------------------------------------------------ renumber


def test_renumber_moves_only_the_branchs_own_rule_and_its_own_tag_lines(repo: Path) -> None:
    rule(repo, "a", 42)
    tfile(repo, "test_x.py", "def test_old():  # @R42", "    pass")
    commit(repo)
    sh(repo, "git", "checkout", "-q", "-b", "work")
    sh(repo, "git", "checkout", "-q", "main")
    rule(repo, "c", 43)  # another PR merged R43 and R42 is already there; ours collides on 42
    tfile(
        repo,
        "test_x.py",
        "def test_old():  # @R42",
        "    pass",
        "def test_other():  # @R43",
        "    pass",
    )
    commit(repo, "other pr")
    sh(repo, "git", "checkout", "-q", "work")
    rule(repo, "b", 42, text="When n, the system shall m.")
    p = repo / "tests/test_x.py"
    p.write_text(p.read_text() + "def test_new():  # @R42\n    pass\n")
    (repo / "changes").mkdir()
    (repo / "changes/spec.md").write_text("R42 new\n")
    commit(repo, "ours")
    assert spec.renumber(repo, "main", dry_run=True) == {"R42": "R44"}
    assert spec.renumber(repo, "main") == {"R42": "R44"}
    text = p.read_text()
    assert "test_old():  # @R42" in text and "test_new():  # @R44" in text
    assert (repo / "specs/b/rules/R44.md").read_text().startswith("---\nid: R44")
    assert not (repo / "specs/b/rules/R42.md").exists()
    assert "R44 new" in (repo / "changes/spec.md").read_text()
    assert spec.renumber(repo, "main") == {}


# ------------------------------------------------------------------ find, index, capabilities, eval


def _billing(repo: Path) -> None:
    rule(repo, "billing", 1, text="When a charge fails, the system shall retry it once.")
    rule(repo, "reporting", 2, text="The system shall show invoice totals in euros.")
    (repo / "specs/billing/manifest.yaml").write_text(
        "purpose: charging customers\naliases: [invoice, payment]\ncode: [src/billing]\ntests: [tests]\n"
    )
    commit(repo)


def test_find_uses_aliases_and_stems_and_never_leaves_a_committed_index(repo: Path) -> None:
    _billing(repo)
    out = spec.find(repo, "invoice retries", limit=1)
    assert out[0].startswith("R1  billing  live")
    assert sh(repo, "git", "status", "--porcelain") == ""
    assert (repo / ".git" / "spec-index.json").exists()
    rows = json.loads((repo / ".git/spec-index.json").read_text())["rules"]
    assert set(rows[0]) == {"id", "cap", "summary", "status", "b"}


def test_find_rebuilds_when_a_rule_changes_and_finds_an_exact_id(repo: Path) -> None:
    _billing(repo)
    spec.find(repo, "invoice")
    rule(repo, "billing", 3, text="The system shall email a receipt.")
    assert spec.find(repo, "receipt")[0].startswith("R3  billing")
    assert spec.find(repo, "R2")[0].startswith("R2  reporting")


def test_a_miss_names_the_capability_code_and_tests_and_warns_about_partial_coverage(
    repo: Path,
) -> None:
    _billing(repo)
    (repo / "specs/billing/manifest.yaml").write_text(
        "purpose: charging customers\naliases: [refund]\ncode: [src/billing]\ntests: [tests/billing]\ncoverage: partial\n"
    )
    out = spec.find(repo, "settlements")
    assert "no rule matched" in out[0] and "src/billing" in out[1] and "partly catalogued" in out[1]


def test_find_flags_open_prs_and_stale_rules_only_when_asked(repo: Path, monkeypatch) -> None:
    _billing(repo)
    monkeypatch.setattr(spec, "open_pr_files", lambda root: [(7, ["specs/billing/rules/R1.md"])])
    assert "open PR #7" in spec.find(repo, "retry", prs=True)[0]
    assert "open PR" not in spec.find(repo, "retry")[0]


def test_open_prs_stay_quiet_when_gh_is_missing(repo: Path, monkeypatch) -> None:
    monkeypatch.setattr(spec.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    assert spec.open_pr_files(repo) == []


def test_capabilities_file_is_one_line_each_and_checkable(repo: Path, monkeypatch) -> None:
    _billing(repo)
    text = spec.render_capabilities(repo)
    assert "- **billing**: charging customers (also: invoice, payment)" in text
    assert "1 rule" not in text
    monkeypatch.chdir(repo)
    assert spec.main(["capabilities", "--check"]) == 1
    assert spec.main(["capabilities", "--write"]) == 0
    assert spec.main(["capabilities", "--check"]) == 0


def test_eval_scores_find_against_a_grep_and_counts_new_features_apart(repo: Path) -> None:
    _billing(repo)
    fixture = [
        {"id": "c1", "query": "invoice retries", "relevant": ["R1"]},
        {"id": "c2", "query": "a brand new thing", "relevant": []},
    ]
    res = spec.evaluate(repo, fixture, k=1)
    assert (res["cases"], res["no_prior"], res["find"], res["grep"]) == (1, 1, 1.0, 0.0)
    res = spec.evaluate(repo, [{**fixture[0], "rev": "HEAD"}], k=1)
    assert res["find"] == 1.0


# ------------------------------------------------------------------ the three documents

SPEC = """---
type: spec
change: 2026-11-20-retry
status: draft
scope: {scope}
ux: none
capabilities: [billing]
---

# Spec: retry

## Asks

| # | Date | Source | Words | Screen | Resources | Answered by |
|---|---|---|---|---|---|---|
| A1 | 2026-11-20 | owner | "retry failed charges" | none | none | {a1} |
| A2 | 2026-11-20 | owner | "no emails" | none | none | out of scope |

## Requirements

| Rule | Change | Capability | Plain words | Asks |
|---|---|---|---|---|
| R1 | new | billing | Retry a failed charge once | A1 |

## Success measure

Failed charges recovered, read in the billing report, target 20 percent.
"""
TASKS = """## Tasks

| # | Rules | Test | Needs | Milestone | State |
|---|---|---|---|---|---|
| T1 | R1 | test_retry | none | M1 | todo |
| T2 | R1 | test_email | T1 | M1 | todo |
"""
DESIGN = """## Test strategy

| Rule | Level | Real or faked | Data |
|---|---|---|---|
| R1 | integration | real db | one failed charge |

## Risks

| Risk | What we do | Proof before build | Lands |
|---|---|---|---|
| gateway rate limit | check | `curl -s ...` | T1 |
"""


def _change(
    repo: Path, scope: str = "S", a1: str = "R1", tasks: str = "", design: str = ""
) -> Path:
    c = repo / "changes" / "2026-11-20-retry"
    c.mkdir(parents=True, exist_ok=True)
    (c / "decisions.json").write_text('{"layout": 4}')
    (c / "spec.md").write_text(SPEC.format(scope=scope, a1=a1))
    if tasks:
        (c / "tasks.md").write_text(tasks)
    if design:
        (c / "design.md").write_text(design)
    rule(repo, "billing", 1)
    return c


def test_layout_is_pinned_per_change_and_the_old_layout_is_never_checked(repo: Path) -> None:
    old = repo / "changes" / "old"
    old.mkdir(parents=True)
    (old / "facts.md").write_text("x")
    assert spec.layout(old) == "legacy" and not spec.applies(old)
    assert spec.documents(old) == ["facts.md"]
    c = _change(repo)
    assert spec.applies(c) and spec.documents(c) == ["spec.md"]


def test_d1_the_draft_phase_takes_a_pending_ask_and_the_gate_does_not(repo: Path) -> None:
    c = _change(repo, a1="pending")
    assert spec.consistency(c, "draft") == []
    errs = spec.consistency(c, "approve")
    assert any("ask A1 is still pending" in e for e in errs)


def test_an_ask_answered_by_a_rule_that_is_not_listed_is_named(repo: Path) -> None:
    errs = spec.consistency(_change(repo, a1="R9"), "draft")
    assert any("A1 is answered by R9" in e for e in errs)


def test_s_needs_only_the_spec_and_m_needs_a_task_per_rule_with_a_test(repo: Path) -> None:
    c = _change(repo, "S")
    assert spec.consistency(c, "approve") == []
    c = _change(repo, "M")
    assert any("no tasks" in e for e in spec.consistency(c, "approve"))
    c = _change(repo, "M", tasks=TASKS)
    assert spec.consistency(c, "approve") == []
    (c / "tasks.md").write_text(
        TASKS.replace("| T2 | R1 |", "| T2 | R7 |").replace(
            "T1 | M1 | todo |\n", "T1 | M1 | todo |\n", 1
        )
    )
    errs = spec.consistency(c, "approve")
    assert any("cites R7" in e for e in errs)
    (c / "tasks.md").write_text(TASKS.replace("| none |", "| T2 |", 1))
    assert any("cycle" in e for e in spec.consistency(c, "approve"))


def test_l_needs_a_test_strategy_line_per_rule_and_a_proof_per_risk(repo: Path) -> None:
    c = _change(repo, "L", tasks=TASKS, design=DESIGN)
    assert spec.consistency(c, "approve") == []
    (c / "design.md").write_text(DESIGN.replace("`curl -s ...`", "-").replace("| R1 |", "| R5 |"))
    errs = " ".join(spec.consistency(c, "approve"))
    assert "R1 has no line" in errs and "Proof before build" in errs


def test_the_requirements_table_must_match_the_git_diff_of_the_rules(repo: Path) -> None:
    rule(repo, "billing", 1)
    tfile(repo, "test_a.py", "# @R1")
    commit(repo)
    sh(repo, "git", "checkout", "-q", "-b", "work")
    c = _change(repo)
    rule(repo, "billing", 2)
    errs = spec.consistency(c, "approve", repo, "main")
    assert any("disagree on R1, R2" in e for e in errs)  # R1 unchanged in git, R2 not listed


def test_s1_build_qa_is_decided_before_any_readiness_file_is_asked_for(repo: Path) -> None:
    c = _change(repo)
    s = (c / "spec.md").read_text()
    assert spec.qa_applicability(c)[0] is False  # ux: none
    (c / "spec.md").write_text(s.replace("ux: none", "ux: M\nprototype: none"))
    assert spec.qa_applicability(c) == (False, "prototype: none, recorded at Stage 2")
    (c / "spec.md").write_text(s.replace("ux: none", "ux: M\nprototype: required"))
    assert spec.qa_applicability(c)[0] is True
    (c / "spec.md").write_text(s.replace("ux: none", "ux: M"))
    assert any("record `prototype" in e for e in spec.consistency(c, "draft"))
    assert spec.qa_applicability(c)[0] is None  # not recorded: neither run nor skip


def test_s1_the_qa_command_exits_0_to_run_3_to_skip_and_2_when_unrecorded(
    repo: Path, monkeypatch
) -> None:
    c = _change(repo)
    s = (c / "spec.md").read_text()
    monkeypatch.chdir(repo)
    for text, code in [
        (s.replace("ux: none", "ux: M\nprototype: required"), 0),
        (s.replace("ux: none", "ux: M\nprototype: none"), 3),
        (s, 3),
        (s.replace("ux: none", "ux: M"), 2),
        (s.replace("ux: none\n", ""), 2),  # no ux key at all: a missing record, not a skip
    ]:
        (c / "spec.md").write_text(text)
        assert spec.main(["qa", str(c)]) == code
    assert any("`ux`" in e for e in spec.consistency(c, "draft"))


def test_the_base_falls_back_to_the_repos_default_branch(repo: Path) -> None:
    sh(repo, "git", "branch", "-m", "trunk")
    (repo / "sdlc.json").write_text('{"defaultBranch": "trunk"}')
    assert spec.tip_ref(repo, None) == "trunk"
    assert spec.tip_ref(repo, "HEAD") == "HEAD"


def test_s3_the_outcome_outlives_the_folder_with_no_tracker_and_no_later_pr(repo: Path) -> None:
    c = _change(repo)
    p = spec.outcome_write(repo, c, due="2026-12-01")
    rec = json.loads(p.read_text())
    assert rec["rules"] == ["R1"] and "20 percent" in rec["measure"] and rec["observed"] is None
    for f in c.iterdir():
        f.unlink()
    c.rmdir()
    assert spec.outcome_due(repo, "2026-12-02") == ["2026-11-20-retry"]
    assert spec.outcome_due(repo, "2026-11-30") == []
    spec.outcome_record(repo, "2026-11-20-retry", "23 percent", True, "2026-12-02")
    assert spec.outcome_due(repo, "2026-12-09") == []
    assert json.loads(p.read_text())["met"] is True


# ------------------------------------------------------------------ copies


def test_installed_copies_match_the_template() -> None:
    template = (SKILL / "templates/scripts/spec.py").read_bytes()
    kit = SKILL.parents[2].parent
    for copy in (
        kit / "scripts/spec.py",
        kit / "plugins/cct/blueprint/web-nextjs-cloud-run/scripts/spec.py",
    ):
        if copy.exists():
            assert copy.read_bytes() == template, copy


def test_the_shipped_templates_have_the_columns_consistency_reads(repo: Path) -> None:
    tpl = SKILL / "templates/change"
    c = repo / "changes" / "2026-11-20-x"
    c.mkdir(parents=True)
    (c / "decisions.json").write_text('{"layout": 4}')
    fill = {
        "{{CHANGE}}": c.name, "{{LINEAR}}": "none", "{{DESIGN}}": "none", "{{AUTHOR}}": "t",
        "{{DATE}}": "2026-11-20", "{{TITLE}}": "x",
        "<S | M | L, chosen by risk: see references/change-folder.md>": "L",
        "<none | S | M | L>": "none", "R<n>": "R1", "<capability>": "billing",
    }  # fmt: skip
    for name in ("spec.md", "design.md", "tasks.md"):
        text = (tpl / name).read_text()
        for k, v in fill.items():
            text = text.replace(k, v)
        (c / name).write_text(text)
    rule(repo, "billing", 1)
    errs = spec.consistency(c, "approve")
    # the template's own placeholders are not valid content, but every table is found and parsed
    assert not any("no asks found" in e or "no tasks" in e or "scope" in e for e in errs), errs
    assert 1 in spec.change_rules(c)
    for f in ("manifest.yaml",):
        assert spec.parse_flat((SKILL / "templates/specs" / f).read_text())["purpose"]
    assert (
        spec.split_frontmatter((SKILL / "templates/specs/rule.md").read_text())[0]["status"]
        == "live"
    )


def test_a_tick_never_moves_the_lock_but_a_changed_task_does(repo: Path) -> None:
    c = _change(repo, "M", tasks=TASKS)
    before = spec.lock_inputs(c)
    assert set(before) == {"spec.md", "tasks.md", "rules/R1.md"}
    (c / "tasks.md").write_text(
        TASKS.replace("none | M1 | todo", "none | M1 | done abc1234")
        + "\n## Handover\n\nnew words\n"
    )
    assert spec.lock_inputs(c) == before
    assert spec.task_states(c)[0] == ("T1", "done abc1234", "M1")
    (c / "tasks.md").write_text(TASKS.replace("test_retry", "test_other"))
    assert spec.lock_inputs(c) != before


# ------------------------------------------------------------------ hardening


def _cfg(root: Path, value) -> None:
    (root / "sdlc.json").write_text(json.dumps({"livingSpecs": value}))


@pytest.mark.parametrize("bad", ["../x", "/abs", "a/b", "..", ".", "sp ec", "s;rm"])
def test_living_specs_must_be_one_plain_name(repo: Path, bad: str) -> None:
    _cfg(repo, bad)
    with pytest.raises(spec.SpecError):
        spec.specs_name(repo)
    assert any("livingSpecs" in p for p in spec.check(repo))


def test_living_specs_may_not_be_a_link_out_of_the_repo(repo: Path, tmp_path_factory) -> None:
    outside = tmp_path_factory.mktemp("outside")
    (repo / "docs-specs").symlink_to(outside)
    _cfg(repo, "docs-specs")
    assert any("livingSpecs" in p for p in spec.check(repo))


def test_manifest_test_roots_stay_inside_the_repo(repo: Path, tmp_path_factory) -> None:
    outside = tmp_path_factory.mktemp("outside")
    (outside / "t.py").write_text("# @R1\n")
    (repo / "link").symlink_to(outside)
    rule(repo, "a", 1)
    for bad in ("/etc", "../x", "tests/../../x", "link"):
        (repo / "specs/a/manifest.yaml").write_text(f"purpose: p\ntests: [{bad}]\n")
        problems = " ".join(spec.check(repo))
        assert "outside the repo" in problems, bad
        assert "t.py" not in problems


def test_a_named_specs_folder_that_is_missing_is_a_problem_but_no_key_is_legacy(repo: Path) -> None:
    assert spec.check(repo) == []
    _cfg(repo, "contracts")
    assert any("contracts" in p and "missing" in p for p in spec.check(repo))


def test_an_unresolvable_base_fails_in_ci_or_when_given_and_not_otherwise(
    repo: Path, monkeypatch
) -> None:
    rule(repo, "a", 1)
    tfile(repo, "test_a.py", "# @R1")
    monkeypatch.delenv("CI", raising=False)
    sh(repo, "git", "branch", "-m", "trunk")
    assert spec.check(repo) == []
    assert any("base" in p for p in spec.check(repo, "nope"))
    monkeypatch.setenv("CI", "1")
    assert any("base" in p for p in spec.check(repo))


def test_a_git_call_that_fails_while_diffing_is_a_problem_in_strict_mode(
    repo: Path, monkeypatch
) -> None:
    rule(repo, "a", 1)
    tfile(repo, "test_a.py", "# @R1")
    commit(repo)
    real = spec.subprocess.run

    def broken(cmd, *a, **k):
        if "diff" in cmd:
            return subprocess.CompletedProcess(cmd, 128, "", "boom")
        return real(cmd, *a, **k)

    monkeypatch.setattr(spec.subprocess, "run", broken)
    assert any("git" in p for p in spec.check(repo, "main"))


@pytest.mark.parametrize(
    "name,lines",
    [
        (
            "test_m.py",
            [
                "import pytest",
                "pytestmark = pytest.mark.skip(reason='x')",
                "def test_a():  # @R1",
                "    pass",
            ],
        ),
        (
            "test_c.py",
            [
                "import pytest",
                "@pytest.mark.skip",
                "class TestA:",
                "    def test_a(self):",
                "        # @R1",
                "        pass",
            ],
        ),
        (
            "a.test.ts",
            ["describe.skip('x', () => {", "  it('works', () => {", "    // @R1", "  });", "});"],
        ),
        ("b.test.ts", ["test.skip(true, 'later');", "test('works @R1', async () => {", "});"]),
        (
            "c.test.ts",
            [
                "describe('x', () => {",
                "  test.skip();",
                "  test('works @R1', () => {",
                "  });",
                "});",
            ],
        ),
    ],
)
def test_a_skip_on_the_file_class_or_describe_covers_every_tag_inside(
    repo: Path, name: str, lines: list[str]
) -> None:
    rule(repo, "a", 1)
    tfile(repo, name, *lines)
    assert any("skipped tests" in p for p in spec.check(repo)), name


def test_a_live_test_next_to_a_skipped_class_still_counts(repo: Path) -> None:
    rule(repo, "a", 1)
    rule(repo, "a", 2)
    tfile(
        repo, "test_k.py",
        "import pytest", "@pytest.mark.skip", "class TestA:", "    def test_a(self):  # @R1", "        pass",
        "", "def test_b():  # @R2", "    pass",
    )  # fmt: skip
    problems = " ".join(spec.check(repo))
    assert "R1 is tagged only in skipped" in problems and "R2" not in problems


# ------------------------------------------------------------------ second wave


def test_find_pulls_in_the_rules_of_related_capabilities_after_the_direct_hits(repo: Path) -> None:
    _billing(repo)
    (repo / "specs/billing/manifest.yaml").write_text(
        "purpose: charging customers\naliases: [payment]\ncode: [src/billing]\nrelated: [reporting]\n"
    )
    out = spec.find(repo, "payment retry")
    assert out[0].startswith("R1  billing") and any(
        ln.startswith("R2  reporting") and "via billing" in ln for ln in out
    )
    (repo / "specs/billing/manifest.yaml").write_text(
        "purpose: charging customers\naliases: [payment]\n"
    )
    assert not any(ln.startswith("R2  reporting") for ln in spec.find(repo, "payment retry"))


CORPUS = SKILL.parents[2].parent / "tests" / "eval"


def test_the_committed_recall_fixture_beats_a_grep_on_the_repos_own_changes() -> None:
    fixture = json.loads((CORPUS / "fixture.json").read_text())
    rules, _, problems = spec.load_rules(CORPUS / "corpus")
    assert problems == [] and len(rules) > 200 and len(fixture) >= 50
    res = spec.evaluate(CORPUS / "corpus", fixture, 10)
    assert res["cases"] >= 50 and res["find"] >= res["grep"], res


def test_eval_takes_a_root_and_a_fail_under(repo: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(repo)
    args = ["eval", str(CORPUS / "fixture.json"), "--root", str(CORPUS / "corpus")]
    assert spec.main(args) == 0
    assert spec.main(args + ["--fail-under", "0.99"]) == 1


def test_the_corpus_builder_labels_each_ask_with_the_facts_that_cite_it(tmp_path: Path) -> None:
    sys.path.insert(0, str(SKILL / "scripts"))
    import eval_corpus

    ch = tmp_path / "changes" / "2026-11-01-retry-charges"
    ch.mkdir(parents=True)
    (ch / "intent.md").write_text(
        "# Intent: Retry charges\n\n| # | Date | Source | Words | Screen | Resources |\n|---|---|---|---|---|---|\n"
        '| A1 | d | owner | "please retry failed charges again. Also tell me when it happens." | none | none |\n'
    )
    (ch / "facts.md").write_text(
        "- [ ] **F1** (A1) When a charge fails, the system shall retry it once.\n"
        "- [ ] **F2** (A2) The system shall log it.\n"
    )
    out = tmp_path / "out"
    assert eval_corpus.build(tmp_path, out) == {"rules": 2, "cases": 3}
    fx = json.loads((out / "fixture.json").read_text())
    assert {c["id"] for c in fx} == {"retry-charges/A1", "retry-charges/A1.1", "retry-charges/A1.2"}
    assert all(c["relevant"] == ["R1"] for c in fx)
    assert spec.load_rules(out / "corpus")[2] == []


def test_the_letter_r_means_a_rule_in_layout_4_and_a_review_finding_before(repo: Path) -> None:
    sys.path.insert(0, str(SKILL / "scripts"))
    import change_docs

    assert spec.id_families(None)["R"][0] == "review finding"
    v4 = spec.id_families(_change(repo))
    assert v4["R"][0] == "rule" and v4["V"][0] == "review finding" and "F" not in v4
    c = _change(repo)
    (c / "tasks.md").write_text("Task T1 satisfies R1; the reviewer's V2 says add a test.\n")
    (c / "findings.md").write_text("- V2 The test for R1 does not assert the retry count.\n")
    out = "\n".join(change_docs.ids(c))
    assert "R1" in out and "The system shall" not in out and "When x, the system shall y" in out
    assert "specs/billing/rules/R1.md" in out
    assert "V2" in out and "does not assert the retry count" in out
    assert "no definition found" not in out


def test_the_old_layout_still_reads_r_as_a_finding(repo: Path) -> None:
    sys.path.insert(0, str(SKILL / "scripts"))
    import change_docs

    old = repo / "changes" / "2026-10-01-old"
    old.mkdir(parents=True)
    (old / "facts.md").write_text("see R1\n")
    (old / "findings.md").write_text("| R1 | finding | text of the finding |\n")
    assert "R1   " in "\n".join(change_docs.ids(old))


# ------------------------------------------------------------------ find: body, idf, caps, ties
# Shaped like the misses of the multi-repo recall eval (summary-only scoring, one common word
# outvoting a rare one, a capability name lifting a whole capability, every new rule tying).


def _ids(out: list[str]) -> list[str]:
    return [ln.split()[0] for ln in out if ln.startswith("R")]


def test_find_scores_the_whole_rule_body_and_the_summary_counts_more(repo: Path) -> None:
    rule(
        repo,
        "values",
        1,
        text="No rendered value shall be a lone dash. Missing configuration shall read Not set.",
    )
    rule(repo, "billing", 2, text="The invoice shall list the vat. Missing vat shall read Not set.")
    rule(repo, "billing", 3, text="The vat id shall be named.")
    out = spec.find(repo, "missing configuration")
    assert _ids(out)[0] == "R1"  # R1 has both words in its body; none is in a summary
    assert _ids(spec.find(repo, "vat id"))[0] == "R3"  # a summary hit beats a body hit
    rows = json.loads((repo / ".git/spec-index.json").read_text())["rules"]
    assert "configuration" in rows[0]["b"] and len(rows[0]["b"]) < 120


def test_a_query_word_found_in_many_rules_counts_far_less_than_a_rare_one(repo: Path) -> None:
    for n, w in enumerate("alpha beta gamma delta epsilon zeta eta theta iota kappa".split(), 1):
        rule(repo, "listing", n, text=f"The page shall show {w}.")
    rule(repo, "other", 11, text="The banner shall be hidden.")
    assert _ids(spec.find(repo, "page banner"))[0] == "R11"


def test_the_capability_name_cannot_lift_a_whole_capability_over_a_specific_rule(
    repo: Path,
) -> None:
    for n, w in enumerate("alpha beta gamma delta epsilon zeta eta theta".split(), 1):
        rule(repo, "mail-sequences", n, text=f"The editor shall open {w}.")
    rule(repo, "preferences", 20, text="The unsubscribe screen shall name the banner.")
    out = spec.find(repo, "mail sequences banner", limit=3)
    assert _ids(out)[0] == "R20"
    assert _ids(out)[1].startswith("R") and "mail-sequences" in out[1]  # the capability follows


def test_ties_break_on_age_and_unreleased_rules_do_not_all_tie_on_now(
    repo: Path, monkeypatch
) -> None:
    same = "The cart shall keep the gift note."
    monkeypatch.setenv("GIT_COMMITTER_DATE", "2020-01-01T00:00:00")
    rule(repo, "cart", 2, text=same)
    commit(repo)
    monkeypatch.setenv("GIT_COMMITTER_DATE", "2024-01-01T00:00:00")
    rule(repo, "cart", 1, text=same)
    commit(repo)
    rule(repo, "cart", 4, text=same)
    rule(repo, "cart", 3, text=same)
    assert _ids(spec.find(repo, "gift note")) == ["R2", "R1", "R3", "R4"]


def test_the_corpus_builder_reads_the_asks_and_spec_folders(tmp_path: Path) -> None:
    sys.path.insert(0, str(SKILL / "scripts"))
    import eval_corpus

    ch = tmp_path / "changes" / "2026-11-01-mute-alerts"
    (ch / "asks" / "2026-11-01").mkdir(parents=True)
    (ch / "spec").mkdir()
    (ch / "asks/2026-11-01/notes.md").write_text('A1: "let me mute the alerts at night."\n')
    (ch / "spec/brief.md").write_text('| A2 | spec | "the badge should show a count" |\n')
    (ch / "facts.md").write_text(
        "- [ ] **F1** (A1) The system shall mute alerts at night.\n"
        "- F2 (A2) The badge shall show a count.\n"
    )
    out = tmp_path / "out"
    assert eval_corpus.build(tmp_path, out) == {"rules": 2, "cases": 2}
    fx = json.loads((out / "fixture.json").read_text())
    assert {c["id"]: c["relevant"] for c in fx} == {
        "mute-alerts/A1": ["R1"],
        "mute-alerts/A2": ["R2"],
    }
