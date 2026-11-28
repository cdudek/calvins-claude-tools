import copy
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "check-plan.py"

VALID = {
    "change": "2026-11-24-search", "base": "main", "goalTurns": 12,
    "requirements": ["req-1", "req-2"],
    "milestones": [
        {"id": "M1", "layer": "components", "covers": ["req-1"],
         "tasks": [{"id": "T1", "covers": ["req-1"], "files": ["a.tsx"], "check": "npm test", "needs": []}]},
        {"id": "M2", "layer": "backend", "covers": ["req-2"],
         "tasks": [{"id": "T2", "covers": ["req-2"], "files": ["b.py"], "check": "pytest", "needs": ["T1"]}]},
        {"id": "M3", "layer": "screens", "covers": []},
    ],
}


INTENT = "# intent\n- outcome-1: people save a search\n- constraint-1: no change to guest search\n"


def write_plan(tmp_path, plan, delta=True, log="", intent=True):
    tmp_path.mkdir(parents=True, exist_ok=True)
    f = tmp_path / "plan.md"
    f.write_text("# Plan\n\n```json factory\n" + json.dumps(plan) + "\n```\n" + log)
    if delta:  # a delta that lists exactly the plan's requirements, each citing an intent id
        (tmp_path / "delta.md").write_text(
            "# delta\n### ADDED Requirements\n" + "".join(f"- {r}: When ..., the system shall ... [outcome-1]\n" for r in plan["requirements"]))
    if intent:
        (tmp_path / "intent.md").write_text(INTENT)
    return f


def run(tmp_path, plan, delta=True, *extra):
    f = write_plan(tmp_path, plan, delta)
    p = subprocess.run([sys.executable, str(SCRIPT), str(f), *extra], capture_output=True, text=True)
    return p.returncode, p.stdout


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def committed(tmp_path):
    """A temp repo whose plan and delta are committed; returns (plan file, sha)."""
    git(tmp_path, "init", "-q")
    sub = tmp_path / "changes" / "x"
    sub.mkdir(parents=True)
    f = write_plan(sub, VALID)
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "plan")
    return f, git(tmp_path, "rev-parse", "HEAD")


def approved(f, sha):
    p = subprocess.run([sys.executable, str(SCRIPT), str(f), "--approved", sha], capture_output=True, text=True)
    return p.returncode, p.stdout


def mutated(fn):
    plan = copy.deepcopy(VALID)
    fn(plan)
    return plan


def test_valid(tmp_path):
    code, out = run(tmp_path, VALID)
    assert code == 0 and out.strip() == "PLAN OK 3 milestones 2 tasks"

def test_layer_backwards(tmp_path):
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][2].update(layer="layouts")))
    assert code == 1 and "PLAN FAIL M3 layer layouts goes backwards" in out


def test_needs_same_or_later_milestone(tmp_path):
    def f(p):
        p["milestones"][0]["tasks"][0]["needs"] = ["T2"]  # later milestone
        p["milestones"][1]["tasks"][0]["needs"] = ["T2"]  # itself
    code, out = run(tmp_path, mutated(f))
    assert code == 1 and "M1/T1 needs T2" in out and "M2/T2 needs T2" in out


def test_shared_file(tmp_path):
    def f(p):
        p["milestones"][0]["covers"] = ["req-1"]
        p["milestones"][0]["tasks"].append(
            {"id": "T3", "covers": ["req-1"], "files": ["a.tsx"], "check": "npm test", "needs": []})
    code, out = run(tmp_path, mutated(f))
    assert code == 1 and "both own a.tsx" in out


def test_uncovered_requirement(tmp_path):
    code, out = run(tmp_path, mutated(lambda p: p["requirements"].append("req-3")))
    assert code == 1 and "requirement req-3 is covered by no milestone" in out


def test_coverage_mismatch(tmp_path):
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][0].update(covers=["req-1", "req-2"])))
    assert code == 1 and "M1 task coverage" in out


def test_empty_check(tmp_path):
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][0]["tasks"][0].update(check=" ")))
    assert code == 1 and "M1/T1 has an empty check" in out


def test_missing_run_fields(tmp_path):
    def f(p):
        del p["base"]
        p["goalTurns"] = 0
        p["change"] = "search"
    code, out = run(tmp_path, mutated(f))
    assert code == 1 and "missing base" in out and "goalTurns must be a positive whole number" in out
    assert "change must be the dated slug" in out


def test_bad_effort(tmp_path):
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][0]["tasks"][0].update(effort="max")))
    assert code == 1 and "M1/T1 effort must be low, medium or high" in out


def test_merge_and_integration_keys(tmp_path):
    for merge in ("auto", "owner"):
        code, out = run(tmp_path, mutated(lambda p: p.update(merge=merge, integration="integration/v1-beta")))
        assert code == 0 and out.startswith("PLAN OK")
    code, out = run(tmp_path, mutated(lambda p: p.update(merge="never")))
    assert code == 1 and 'merge must be "auto" or "owner"' in out
    for bad in ("main", "", "has space", 3):
        code, out = run(tmp_path, mutated(lambda p: p.update(integration=bad)))
        assert code == 1 and "integration must be a branch name different from base" in out


def test_bare_requirement_id_refused(tmp_path):
    def f(p):
        p["requirements"].append("R9")
        p["requirements"].append("guests/R9")
        p["milestones"][2]["covers"] = ["R9", "guests/R9"]
    code, out = run(tmp_path, mutated(f))
    assert code == 1 and "requirement id R9 must look like req-<n>" in out
    assert "requirement id guests/R9 must look like req-<n> (old form: rewrite it as req-<n>" in out


def test_plan_matches_delta(tmp_path):
    write_plan(tmp_path, VALID, delta=False)
    (tmp_path / "delta.md").write_text(
        "# x: delta, revision 2\n## specs/2026-12/2026-12-20__saved-searches.md\n### ADDED Requirements\n"
        "- req-1: When ..., the system shall ... [outcome-1]\n### MODIFIED Requirements\n"
        "- req-5: (was) ... (now) ... [constraint-1]\n")
    p = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path / "plan.md")], capture_output=True, text=True)
    out = p.stdout
    assert p.returncode == 1
    assert "requirement req-2 is not ADDED, MODIFIED or REMOVED in delta.md" in out
    assert "delta requirement req-5 is in no plan requirement" in out


def test_removed_requirement_is_buildable(tmp_path):
    write_plan(tmp_path, VALID, delta=False)
    (tmp_path / "delta.md").write_text(
        "### ADDED Requirements\n- req-1: x [outcome-1]\n### REMOVED Requirements\n- req-2: gone. [constraint-1]\n")
    p = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path / "plan.md")], capture_output=True, text=True)
    assert p.returncode == 0 and p.stdout.startswith("PLAN OK")


def test_subheadings_keep_the_section_open(tmp_path):
    write_plan(tmp_path, VALID, delta=False)
    (tmp_path / "delta.md").write_text(
        "## ADDED Requirements\n### Public site\n- req-1: x [outcome-1]\n### Guests\n- req-2: y [constraint-1]\n"
        "## Journeys\n- req-9: not a requirement line [outcome-1]\n")
    p = subprocess.run([sys.executable, str(SCRIPT), str(tmp_path / "plan.md")], capture_output=True, text=True)
    assert p.returncode == 0 and p.stdout.startswith("PLAN OK"), p.stdout


def test_missing_delta(tmp_path):
    code, out = run(tmp_path, VALID, delta=False)
    assert code == 1 and "PLAN FAIL missing delta.md next to the plan" in out


def test_approved_unchanged_and_log_edit_pass(tmp_path):
    f, sha = committed(tmp_path)
    assert approved(f, sha)[0] == 0
    f.write_text(f.read_text() + "\n## Progress\n- M1 done\n")
    code, out = approved(f, sha)
    assert code == 0 and out.startswith("PLAN OK")


def test_approved_changed_block_fails(tmp_path):
    f, sha = committed(tmp_path)
    f.write_text(f.read_text().replace('"goalTurns": 12', '"goalTurns": 13'))
    code, out = approved(f, sha)
    assert code == 1 and f"PLAN FAIL plan.md changed since approved {sha}: owner approves a new revision" in out


def test_approved_changed_delta_fails(tmp_path):
    f, sha = committed(tmp_path)
    d = f.parent / "delta.md"
    d.write_text(d.read_text() + "\n")
    code, out = approved(f, sha)
    assert code == 1 and f"PLAN FAIL delta.md changed since approved {sha}: owner approves a new revision" in out


def test_approved_intent_changed_fails(tmp_path):
    f, sha = committed(tmp_path)
    (f.parent / "intent.md").write_text(INTENT + "- outcome-2: more\n")
    code, out = approved(f, sha)
    assert code == 1 and f"PLAN FAIL intent.md changed since approved {sha}" in out


def test_approved_bad_sha_fails(tmp_path):
    f, _ = committed(tmp_path)
    code, out = approved(f, "deadbeef")
    assert code == 1 and "PLAN FAIL approved deadbeef is not a commit" in out


def test_new_keys_valid(tmp_path):
    code, out = run(tmp_path, mutated(lambda p: p.update(
        hold="owner restores billing", setup="npm ci", preflight=["command -v squawk"], deployOnMerge=True)))
    assert code == 0 and out.startswith("PLAN OK")


def test_new_keys_wrong_types(tmp_path):
    def f(p):
        p.update(hold=" ", setup=3, preflight=["ok", ""], deployOnMerge="yes")
    code, out = run(tmp_path, mutated(f))
    assert "hold must be a non-empty string" in out and "setup must be a non-empty string" in out
    assert "preflight must be a list of non-empty strings" in out and "deployOnMerge must be true or false" in out
    code, out = run(tmp_path, mutated(lambda p: p.update(preflight="npm ci")))
    assert "preflight must be a list of non-empty strings" in out


def one_task_plan(**extra):
    return {"change": "2026-11-24-fix", "base": "main", "goalTurns": 5, "requirements": ["req-1"],
            "milestones": [{"id": "M1", "layer": "rest", "covers": ["req-1"],
                            "tasks": [{"id": "T1", "covers": ["req-1"], "files": ["a.py"], "check": "pytest"}]}], **extra}


def test_kind(tmp_path):
    for kind in ("bug", "feature"):
        code, out = run(tmp_path, one_task_plan(kind=kind))
        assert code == 0, out
    code, out = run(tmp_path, one_task_plan(kind="chore"))
    assert 'kind must be "bug" or "feature"' in out
    code, out = run(tmp_path, mutated(lambda p: p.update(kind="bug")))
    assert "kind bug needs exactly one milestone with one task and at most 3 requirements" in out
    big = one_task_plan(kind="feature")
    big["requirements"] = [f"fix/R{i}" for i in range(1, 5)]
    big["milestones"][0]["covers"] = big["milestones"][0]["tasks"][0]["covers"] = big["requirements"]
    code, out = run(tmp_path, big)
    assert "at most 3 requirements" in out


def test_allow_test_edits_moved(tmp_path):
    code, out = run(tmp_path, mutated(lambda p: p.update(allowTestEdits=["a.test.ts"])))
    assert code == 1 and "PLAN FAIL move allowTestEdits into the task that edits them" in out
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][0]["tasks"][0].update(allowTestEdits=["a.test.ts"])))
    assert code == 0
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][0]["tasks"][0].update(allowTestEdits="a.test.ts")))
    assert "M1/T1 allowTestEdits must be a list of strings" in out


def test_milestone_needs_duplicates_and_task_needs_type(tmp_path):
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][1].update(needs=["M1"])))
    assert "M2 needs is not allowed on a milestone" in out
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][2].update(id="M2")))
    assert "milestone id M2 is not unique" in out
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][1]["tasks"][0].update(needs="T1")))
    assert "M2/T2 needs must be a list" in out


def test_missing_intent(tmp_path):
    f = write_plan(tmp_path, VALID, intent=False)
    p = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True)
    assert p.returncode == 1 and "PLAN FAIL missing intent.md next to the plan" in p.stdout


def test_delta_requirement_must_cite_a_defined_intent_id(tmp_path):
    f = write_plan(tmp_path, VALID)
    d = f.parent / "delta.md"
    d.write_text("### ADDED Requirements\n- req-1: no citation\n- req-2: unknown [outcome-9]\n")
    out = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True).stdout
    assert "PLAN FAIL requirement req-1 in delta.md cites no [outcome-<n>] or [constraint-<n>]" in out
    assert "PLAN FAIL requirement req-2 in delta.md cites outcome-9, which intent.md does not define" in out
    d.write_text("### ADDED Requirements\n- req-1: ok [outcome-1]\n- req-2: both [constraint-1][outcome-1]\n")
    out = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True).stdout
    assert out.startswith("PLAN OK")


def test_intent_without_ids_fails(tmp_path):
    f = write_plan(tmp_path, VALID)
    (f.parent / "intent.md").write_text("# intent\noutcome-1 people save a search\n")
    out = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True).stdout
    assert "intent.md defines no ids" in out and "cites outcome-1, which intent.md does not define" in out


def test_open_clarification_fails(tmp_path):
    for name in ("intent.md", "delta.md"):
        f = write_plan(tmp_path, VALID)
        p = f.parent / name
        p.write_text(p.read_text() + "- [NEEDS CLARIFICATION: who may share?]\n")
        out = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True).stdout
        assert f"PLAN FAIL {name} still has [NEEDS CLARIFICATION" in out


def risky(**surface):
    def f(p):
        p["milestones"][1]["risky"] = True
        if surface:
            p["milestones"][1].update(surface)
    return mutated(f)


GOOD_SURFACE = [{"exposure": "list endpoint", "requirement": "req-2", "scenario": "guest-reads-list"}]


def test_risky_milestone_with_tasks_needs_surface(tmp_path):
    code, out = run(tmp_path, risky())
    assert code == 1 and "PLAN FAIL M2 surface is required on a risky milestone" in out
    code, out = run(tmp_path, risky(surface=[]))
    assert "M2 surface is required" in out
    code, out = run(tmp_path, risky(surface=GOOD_SURFACE))
    assert code == 0, out
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][2].update(risky=True)))  # no tasks yet: not required
    assert code == 0, out


def test_surface_entries(tmp_path):
    ok = {"exposure": "x", "requirement": "req-2"}
    cases = {
        "needs a non-empty exposure": {**ok, "exposure": " ", "scenario": "s"},
        "needs a non-empty requirement": {**ok, "requirement": "", "scenario": "s"},
        "requirement req-1 is not in M2 covers": {**ok, "requirement": "req-1", "scenario": "s"},
        "needs a non-empty scenario, or deferred": {**ok, "scenario": " "},
        "deferred needs a non-empty reason and probe": {**ok, "deferred": {"reason": "later", "probe": ""}},
    }
    for text, entry in cases.items():
        code, out = run(tmp_path, risky(surface=[entry]))
        assert code == 1 and f"M2 surface[0] {text}" in out, (text, out)
    code, out = run(tmp_path, risky(surface=[{**ok, "deferred": {"reason": "no staging", "probe": "curl -I /x showed 404"}}]))
    assert code == 0, out


def test_milestone_deferred(tmp_path):
    good = [{"item": "rate limit", "reason": "needs gateway", "probe": "curl /x showed 200 without limit"}]
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][0].update(deferred=good)))
    assert code == 0, out
    for bad in ([{"item": "a", "reason": "b", "probe": " "}], [{"item": "a", "reason": "b"}], ["x"]):
        code, out = run(tmp_path, mutated(lambda p: p["milestones"][0].update(deferred=bad)))
        assert code == 1 and "M1 deferred[0] needs a non-empty item, reason and probe" in out
    code, out = run(tmp_path, mutated(lambda p: p["milestones"][0].update(deferred="later")))
    assert "M1 deferred must be a list" in out


def test_a_plan_needs_a_requirement_and_a_kind_task_must_cover_one(tmp_path):
    empty = one_task_plan(kind="bug")
    empty["requirements"] = empty["milestones"][0]["covers"] = empty["milestones"][0]["tasks"][0]["covers"] = []
    code, out = run(tmp_path / "a", empty)
    assert code == 1 and "PLAN FAIL plan has no requirements" in out
    plan = one_task_plan(kind="feature")
    plan["milestones"][0]["tasks"][0]["covers"] = []
    code, out = run(tmp_path / "b", plan)
    assert code == 1 and "PLAN FAIL M1/T1 covers no requirement" in out
    plan.pop("kind")  # without kind a task that covers nothing stays allowed
    code, out = run(tmp_path / "c", plan)
    assert "covers no requirement" not in out


def test_delta_ids_count_only_under_added_modified_removed(tmp_path):
    f = write_plan(tmp_path, VALID, delta=False)
    d = tmp_path / "delta.md"
    d.write_text("### ADDED Requirements\n- req-1: x [outcome-1]\n## Out of scope\n- req-2: not built [constraint-1]\n"
                 "- req-7: also not built [constraint-1]\n")
    out = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True).stdout
    assert "PLAN FAIL requirement req-2 is not ADDED, MODIFIED or REMOVED in delta.md" in out
    assert "req-7" not in out  # an id outside the three headings is not a delta requirement
    d.write_text("## ADDED\n- req-1: x [outcome-1]\n#### REMOVED Requirements\n- req-2: gone [constraint-1]\n")
    out = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True).stdout
    assert out.startswith("PLAN OK")


def test_duplicate_delta_id_fails(tmp_path):
    f = write_plan(tmp_path, VALID)
    d = f.parent / "delta.md"
    d.write_text(d.read_text() + "### MODIFIED Requirements\n- req-1: again [outcome-1]\n")
    out = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True).stdout
    assert "PLAN FAIL delta requirement req-1 is listed more than once in delta.md" in out


def test_approved_plan_prose_before_the_block_is_pinned(tmp_path):
    f, sha = committed(tmp_path)
    text = f.read_text()
    f.write_text(text.replace("# Plan\n", "# Plan\n\nOwner decision: unlimited saved searches.\n", 1))
    code, out = approved(f, sha)
    assert code == 1 and f"PLAN FAIL plan.md changed since approved {sha}" in out
    f.write_text(text + "\nOwner decision: changed after the block, a progress note\n")
    assert approved(f, sha)[0] == 0


def run_all(tmp_path, plan):
    f = write_plan(tmp_path, plan)
    p = subprocess.run([sys.executable, str(SCRIPT), str(f), "--all"], capture_output=True, text=True)
    return p.returncode, p.stdout


def test_all_needs_every_milestone_detailed_and_no_hold(tmp_path):
    code, out = run_all(tmp_path / "a", VALID)  # M3 has no tasks
    assert code == 1 and "PLAN FAIL M3 has no tasks" in out and "M1 has no tasks" not in out
    detailed = mutated(lambda p: p["milestones"][2].update(
        covers=[], tasks=[{"id": "T3", "covers": [], "files": ["c.py"], "check": "pytest", "needs": ["T2"]}]))
    code, out = run_all(tmp_path / "b", detailed)
    assert code == 0 and out.startswith("PLAN OK"), out
    code, out = run_all(tmp_path / "c", {**detailed, "hold": "owner restores billing"})
    assert code == 1 and "PLAN FAIL --all cannot run with a hold: M1 stops at the hold" in out
    code, out = run(tmp_path / "d", VALID)  # without --all an open milestone is fine
    assert code == 0


def out_of(f):
    return subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True).stdout


def test_old_forms_are_refused_with_a_rewrite_hint(tmp_path):
    f = write_plan(tmp_path, VALID)
    (f.parent / "delta.md").write_text("### ADDED Requirements\n- guests/R1: old id [I1]\n- req-2: old cite [C1]\n")
    (f.parent / "intent.md").write_text("# intent\n- I1: people save a search\n- C1: guests keep today's search\n")
    out = out_of(f)
    assert "intent.md defines no ids" in out and "old `- I1:` form found" in out
    assert "delta requirement guests/R1 uses the old <spec>/R<n> id" in out
    assert "requirement req-2 in delta.md cites an old [I<n>] or [C<n>] id" in out
    assert out.count("rewrite it as req-<n>, outcome-<n> or constraint-<n> by hand") >= 3


def test_duplicate_requirement_number_fails(tmp_path):
    f = write_plan(tmp_path, VALID)
    d = f.parent / "delta.md"
    d.write_text(d.read_text() + "### REMOVED Requirements\n- req-2: gone [constraint-1]\n")
    assert "delta requirement req-2 is listed more than once in delta.md: requirement numbers are unique" in out_of(f)


def plan_with_prose(tmp_path, prose, intent=None):
    f = write_plan(tmp_path, VALID)
    f.write_text(f.read_text().replace("# Plan\n", "# Plan\n\n" + prose + "\n", 1))
    if intent is not None:
        (f.parent / "intent.md").write_text(intent)
    return f


def test_bare_id_in_plan_prose_fails_and_explainer_passes(tmp_path):
    out = out_of(plan_with_prose(tmp_path / "a", "Covers req-1 and more."))
    assert "PLAN FAIL plan.md:3 bare id req-1" in out and "(req-1)" in out
    out = out_of(plan_with_prose(tmp_path / "b", "Covers req-1."))  # one word before the id is not an explainer
    assert "bare id req-1" in out
    out = out_of(plan_with_prose(tmp_path / "c", "guests see their items (req-1)"))
    assert out.startswith("PLAN OK"), out
    out = out_of(plan_with_prose(tmp_path / "d", "guests see items (req-1, req-2) and mail (req-2) too"))
    assert out.startswith("PLAN OK"), out
    out = out_of(plan_with_prose(tmp_path / "e", "see (req-1) for the rule"))  # only one word before the parenthesis
    assert "bare id req-1" in out


def test_explainer_check_exemptions(tmp_path):
    prose = "## Journey journey-1 heading\n```\nreq-1 in fenced code\n```\n- req-7: defines the id\nitems stay private [outcome-1] here"
    assert out_of(plan_with_prose(tmp_path / "a", prose)).startswith("PLAN OK")
    f = write_plan(tmp_path / "b", VALID)  # the json block and the log after it are not checked
    f.write_text(f.read_text() + "\n- done req-1 and req-2 without explainers\n")
    assert out_of(f).startswith("PLAN OK")


def test_bare_id_in_intent_prose_fails(tmp_path):
    bad = plan_with_prose(tmp_path / "a", "x", intent="# intent\n- outcome-1: people save a search\n- constraint-1: no change\nSee adr-7 for why.\n")
    assert "PLAN FAIL intent.md:4 bare id adr-7" in out_of(bad)
    ok = plan_with_prose(tmp_path / "b", "x", intent="# intent\n- outcome-1: people save a search\n- constraint-1: no change\nWe store rows in one table (adr-7).\n")
    assert out_of(ok).startswith("PLAN OK")


def test_no_block(tmp_path):
    f = tmp_path / "plan.md"
    f.write_text("# no block\n")
    p = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True)
    assert p.returncode == 1 and "PLAN FAIL" in p.stdout


def test_task_model_and_milestone_verifier(tmp_path):
    def ok(p):
        p["milestones"][0]["tasks"][0].update(model="haiku", effort="high")
        p["milestones"][0]["verifier"] = {"model": "sonnet", "effort": "medium"}
    assert run(tmp_path / "a", mutated(ok))[0] == 0
    code, out = run(tmp_path / "b", mutated(lambda p: p["milestones"][0]["tasks"][0].update(model="gpt")))
    assert code == 1 and "M1/T1 model must be haiku, sonnet or opus" in out
    code, out = run(tmp_path / "c", mutated(lambda p: p["milestones"][0].update(verifier={"model": "haiku"})))
    assert code == 1 and "M1 verifier must be" in out
    code, out = run(tmp_path / "d", mutated(lambda p: p["milestones"][0].update(verifier={"effort": "low"})))
    assert code == 1 and "M1 verifier must be" in out


PAT = r"(from|join)\(comments\b"


def guarded(tmp_path, files=None, guards=(PAT,), track=True, **ms):
    """A temp git repo with source files that read the guarded table; returns (exit code, output)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    git(tmp_path, "init", "-q")
    files = files or {"api/leak.py": "db.from(comments)\n"}
    for name, body in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(body)
    (tmp_path / "changes").mkdir()
    def setup(p):
        if "tasks" not in ms:  # the default milestone's own task is its rule test
            p["milestones"][1]["tasks"][0]["ruleTest"] = True
        p["milestones"][1].update(**{"guards": list(guards), "rule": "only members read comments", **ms})
    p = mutated(setup)
    f = write_plan(tmp_path / "changes" / "x", p)
    git(tmp_path, "add", "-A" if track else "changes")
    r = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True)
    return r.returncode, r.stdout


def task(files=(), edits=()):
    return [{"id": "T2", "covers": ["req-2"], "files": ["b.py", *files], "check": "pytest", "needs": ["T1"], "allowTestEdits": list(edits), "ruleTest": True}]


def test_guard_pattern_matches_reads_not_bare_name(tmp_path):
    files = {"api/leak.py": "db.from(comments)\n", "api/other.py": "# comments are nice\n"}
    code, out = guarded(tmp_path, files)
    assert code == 1 and "api/leak.py reads it" in out and "other.py" not in out


def test_guard_uncovered_source_file_fails(tmp_path):
    code, out = guarded(tmp_path)
    assert code == 1
    assert "PLAN FAIL M2 guard (from|join)\\(comments\\b: api/leak.py reads it but no task of M2 or earlier owns it, give it to a task, defer it with a probe, or mark its surface entry `safe` with a reason" in out


def test_guard_invalid_pattern(tmp_path):
    code, out = guarded(tmp_path, guards=["(from"])
    assert code == 1 and "PLAN FAIL M2 guard (from is not a valid pattern" in out


def test_guard_covered_by_task_surface_or_probed_deferral(tmp_path):
    assert guarded(tmp_path / "a", tasks=task(files=["api/leak.py"]))[0] == 0
    assert guarded(tmp_path / "b", tasks=task(files=["api/"]))[0] == 0
    s = [{"exposure": "api/leak.py", "requirement": "req-2", "scenario": "scenario-1 guest sees own", "safe": "already filters by member on base"}]
    assert guarded(tmp_path / "c", risky=True, surface=s)[0] == 0
    s = [{"exposure": "api/leak.py", "requirement": "req-2", "scenario": "scenario-1 guest sees own"}]
    code, out = guarded(tmp_path / "e", risky=True, surface=s)
    assert code == 1 and "api/leak.py reads it but no task of M2 or earlier owns it" in out  # listed in surface only
    s[0]["safe"] = " "
    assert "surface[0] safe needs a non-empty" in guarded(tmp_path / "f", risky=True, surface=s)[1]
    d = [{"item": "api/leak.py", "reason": "dead code", "probe": "rg -n leak shows no caller"}]
    assert guarded(tmp_path / "d", deferred=d)[0] == 0


def test_guard_lookalike_path_not_covered(tmp_path):
    d = [{"item": "api/leak.p", "reason": "dead code", "probe": "rg -n leak shows no caller"}]
    code, out = guarded(tmp_path, deferred=d)
    assert code == 1 and "api/leak.py reads it" in out
    d = [{"item": "api/leak.py", "reason": "dead code", "probe": "rg"}]
    s = [{"exposure": "GET api/leak.py", "requirement": "req-2", "scenario": "s", "safe": "reads only own rows"}]
    assert guarded(tmp_path / "s", risky=True, surface=s)[0] == 1  # prose that merely contains the path


def test_guard_test_file_is_a_note_not_a_failure(tmp_path):
    files = {"api/leak.py": "db.from(comments)\n", "tests/leak.test.ts": "db.from(comments)\n"}
    code, out = guarded(tmp_path, files, tasks=task(files=["api/leak.py"]))
    assert code == 0
    assert "PLAN NOTE M2 guard (from|join)\\(comments\\b: tests/leak.test.ts reads it; if it asserts the old behaviour, add it to allowTestEdits" in out
    code, out = guarded(tmp_path / "o", files, tasks=task(files=["api/leak.py"], edits=["tests/leak.test.ts"]))
    assert code == 0 and "NOTE" not in out


def test_test_classifier_is_basename_or_top_level_folder(tmp_path):
    for name in ("src/lib/tests-helpers/x.ts", "src/tests/x.ts", "src/e2e/x.ts"):  # a folder segment below the top is source
        code, out = guarded(tmp_path / name.replace("/", "_"), {name: "db.from(comments)\n"})
        assert code == 1 and f"PLAN FAIL M2 guard" in out and "PLAN NOTE" not in out, name
    for name in ("src/x.test.ts", "src/y.spec.tsx", "tests/x.ts", "__tests__/x.ts", "e2e/x.ts", "test/x.ts"):
        code, out = guarded(tmp_path / name.replace("/", "_"), {name: "db.from(comments)\n"}, tasks=task(files=["api/leak.py"]))
        assert code == 0 and f"PLAN NOTE M2 guard" in out and name in out, name


def test_bad_ids_fail_and_never_reach_a_message_raw(tmp_path):
    code, out = run(tmp_path / "a", mutated(lambda p: p["milestones"][0].update(id="NOTE M9")))
    assert code == 1 and "PLAN FAIL milestone id 'NOTE M9' must look like M<n>" in out and "PLAN NOTE" not in out
    code, out = run(tmp_path / "b", mutated(lambda p: p["milestones"][0]["tasks"][0].update(id="T1\nPLAN OK 1 milestones 1 tasks")))
    assert code == 1 and "\nPLAN OK" not in out and "must look like T<n>" in out
    code, out = run(tmp_path / "c", mutated(lambda p: p["milestones"][0]["tasks"][0].update(id=5)))
    assert code == 1 and "task id 5 must look like T<n>" in out


def test_guard_git_grep_error(tmp_path):
    code, out = guarded(tmp_path, guards=["[[.a.]]"])  # compiles in Python, rejected by git grep
    assert code == 1 and "PLAN FAIL guard [[.a.]]: git grep failed:" in out


def test_guard_scans_untracked_not_ignored(tmp_path):
    files = {"api/new.py": "db.from(comments)\n", "node_modules/x.js": "db.from(comments)\n", ".gitignore": "node_modules/\n"}
    code, out = guarded(tmp_path, files, tasks=task())
    assert code == 1 and "api/new.py reads it" in out and "node_modules" not in out


def test_guard_shape_and_no_guards(tmp_path):
    assert run(tmp_path / "n", VALID)[0] == 0
    code, out = run(tmp_path / "e", mutated(lambda p: p["milestones"][1].update(guards=[])))
    assert code == 1 and "M2 guards must be a non-empty list" in out


def test_task_prose_must_match_json(tmp_path):
    plan = mutated(lambda p: p["milestones"][0]["tasks"][0].update(effort="high"))
    f = write_plan(tmp_path, plan)
    f.write_text(f.read_text().replace("# Plan\n", "# Plan\n- **T1 saved chip (medium effort, haiku).** builds it\n", 1))
    p = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True)
    assert p.returncode == 1
    assert "M1/T1 prose says effort medium but the json block says high" in p.stdout
    assert "M1/T1 prose says model haiku but the json block says sonnet" in p.stdout


def test_task_prose_default_and_match_pass(tmp_path):
    f = write_plan(tmp_path, VALID)  # no json effort counts as medium
    f.write_text(f.read_text().replace("# Plan\n", "# Plan\n- **T1 saved chip (medium effort).** ok\n- **T2:** says nothing\n", 1))
    p = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout
    f.write_text(f.read_text().replace("(medium effort)", "(high effort)"))
    p = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True)
    assert p.returncode == 1 and "T1 prose says effort high but the json block says medium" in p.stdout


def test_may_touch_shape(tmp_path):
    assert run(tmp_path / "a", mutated(lambda p: p["milestones"][0].update(mayTouch=["src/api/*", "tests/api/"])))[0] == 0
    for i, bad in enumerate(("src", [], [""], ["/etc/*"], ["../x"], ["a b"], ["a,b"], ["**"], ["*/"], [1], ["*.ts"], ["src/**"], ["src/**/x.ts"], ["src/*/"], ["*/x"])):
        code, out = run(tmp_path / f"b{i}", mutated(lambda p: p["milestones"][0].update(mayTouch=bad)))
        assert code == 1 and "M1 mayTouch" in out, bad


def test_milestone_id_may_carry_one_letter_suffix(tmp_path):
    def rename(p):
        p["milestones"][0]["id"], p["milestones"][1]["id"] = "M2a", "M6d"
    code, out = run(tmp_path / "ok", mutated(rename))
    assert code == 0 and out.strip() == "PLAN OK 3 milestones 2 tasks", out
    for i, bad in enumerate(("M2A", "M2ab", "M", "Ma", "M2-a", "m2a")):
        code, out = run(tmp_path / f"bad{i}", mutated(lambda p: p["milestones"][0].update(id=bad)))
        assert code == 1 and "must look like M<n>" in out, bad


def test_gap_rounds_shape(tmp_path):
    for i, good in enumerate((1, 3, 5)):
        assert run(tmp_path / f"g{i}", mutated(lambda p: p["milestones"][0].update(mayTouch=["src/api/*"], gapRounds=good)))[0] == 0, good
    for i, bad in enumerate((0, 6, -1, 2.5, "3", True, None, [])):
        code, out = run(tmp_path / f"b{i}", mutated(lambda p: p["milestones"][0].update(gapRounds=bad)))
        assert code == 1 and "M1 gapRounds must be a whole number from 1 to 5" in out, bad


def test_standing_md_must_be_unchanged_since_approval(tmp_path):
    f, sha = committed(tmp_path)
    assert approved(f, sha)[0] == 0  # no standing.md at all is fine
    standing = f.parent / "standing.md"
    standing.write_text("Everything is allowed.\n")  # added after the approved commit
    code, out = approved(f, sha)
    assert code == 1 and f"standing.md changed since approved {sha}" in out
    standing.write_text("Everything is allowed.\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "standing")
    sha2 = git(tmp_path, "rev-parse", "HEAD")
    assert approved(f, sha2)[0] == 0
    standing.write_text("Everything is allowed, and more.\n")
    code, out = approved(f, sha2)
    assert code == 1 and f"standing.md changed since approved {sha2}" in out
    standing.unlink()
    code, out = approved(f, sha2)
    assert code == 1 and "standing.md changed since approved" in out


def test_guards_need_a_rule_and_one_rule_test(tmp_path):
    files = {"api/leak.py": "db.from(comments)\n"}
    assert guarded(tmp_path / "a", files, tasks=task(files=["api/leak.py"]))[0] == 0
    no_test = [{**task(files=["api/leak.py"])[0], "ruleTest": False}]
    code, out = guarded(tmp_path / "b", files, tasks=no_test)
    assert code == 1 and "M2 has guards and needs exactly one task" in out
    code, out = guarded(tmp_path / "c", files, tasks=task(files=["api/leak.py"]), rule=" ")
    assert code == 1 and "M2 has guards but no rule" in out


def test_security_rounds_range(tmp_path):
    assert run(tmp_path / "a", mutated(lambda p: p["milestones"][0].update(securityRounds=2)))[0] == 0
    code, out = run(tmp_path / "b", mutated(lambda p: p["milestones"][0].update(securityRounds=4)))
    assert code == 1 and "M1 securityRounds must be a whole number from 1 to 3" in out


def test_prose_path_must_be_in_task_files(tmp_path):
    owned = VALID["milestones"][0]["tasks"][0]["files"][0]

    def check(sub, bullet):
        f = write_plan(tmp_path / sub, VALID)
        f.write_text(f.read_text().replace("# Plan\n", "# Plan\n- **T1:** " + bullet + "\n", 1))
        p = subprocess.run([sys.executable, str(SCRIPT), str(f)], capture_output=True, text=True)
        return p.returncode, p.stdout
    assert check("a", f"Owns `{owned}`.") == (0, check("a", f"Owns `{owned}`.")[1])
    code, out = check("b", "Owns `src/new/guard.ts`, `src/x.test.ts`. Reads `src/other.ts`.")
    assert code == 1 and "M1/T1 prose names `src/new/guard.ts`" in out and "`src/x.test.ts`" in out and "src/other.ts" not in out


def test_test_changes(tmp_path):
    ok_rename = {"file": "a.test.ts", "block": "lists", "to": "lists the rows", "why": "req-1 changed the title"}
    ok_remove = {"file": "a.test.ts", "block": "lists", "remove": True, "why": "owner dropped the list view"}

    def with_tc(tc, allow=("a.test.ts",)):
        return mutated(lambda p: p["milestones"][0]["tasks"][0].update(allowTestEdits=list(allow), testChanges=tc))

    code, out = run(tmp_path / "ok", with_tc([ok_rename, ok_remove]))
    assert code == 0, out
    for name, tc, allow, why in [
        ("outside", [{**ok_rename, "file": "b.test.ts"}], ("a.test.ts",), "file 'b.test.ts' is not in the task's allowTestEdits"),
        ("noallow", [ok_rename], (), "file 'a.test.ts' is not in the task's allowTestEdits"),
        ("nowhy", [{**ok_rename, "why": " "}], ("a.test.ts",), "why must be a non-empty string"),
        ("missingwhy", [{k: v for k, v in ok_remove.items() if k != "why"}], ("a.test.ts",), "why must be a non-empty string"),
        ("both", [{**ok_rename, "remove": True}], ("a.test.ts",), "needs exactly one of to and remove"),
        ("neither", [{"file": "a.test.ts", "block": "lists", "why": "x y"}], ("a.test.ts",), "needs exactly one of to and remove"),
        ("removefalse", [{**ok_remove, "remove": False}], ("a.test.ts",), "remove must be true"),
        ("emptyto", [{**ok_rename, "to": ""}], ("a.test.ts",), "to must be a non-empty string"),
        ("same", [{**ok_rename, "to": " lists "}], ("a.test.ts",), "to is the same name as block"),
        ("noblock", [{**ok_remove, "block": ""}], ("a.test.ts",), "block must be a non-empty string"),
        ("unknownkey", [{**ok_rename, "reason": "x"}], ("a.test.ts",), "unknown key reason"),
        ("notobject", ["lists"], ("a.test.ts",), "testChanges[0] must be an object"),
    ]:
        code, out = run(tmp_path / name, with_tc(tc, allow))
        assert code == 1 and why in out, (name, out)
    code, out = run(tmp_path / "list", mutated(lambda p: p["milestones"][0]["tasks"][0].update(testChanges="x")))
    assert code == 1 and "M1/T1 testChanges must be a list" in out


GOOD_TESTS = {"related": "npx vitest related --run {files}", "unit": "pytest {tests}",
              "triggers": [{"paths": ["db/**", "architecture.json"], "run": "npm run arch", "why": "schema coupling"}],
              "suites": [{"name": "unit", "cmd": "npm test"}, {"name": "arch", "cmd": "npm run arch", "lock": True}]}


def test_tests_key_is_optional_and_a_good_one_passes(tmp_path):
    code, out = run(tmp_path, mutated(lambda p: p.update(tests=GOOD_TESTS)))
    assert code == 0 and out.strip() == "PLAN OK 3 milestones 2 tasks", out


def test_trigger_edits_pass(tmp_path):
    t = copy.deepcopy(GOOD_TESTS)
    t["triggers"][0]["edits"] = ["tests/test_migrate.py", "tests/fk.json"]
    code, out = run(tmp_path, mutated(lambda p: p.update(tests=t)))
    assert code == 0, out


def test_tests_shape_errors(tmp_path):
    def bad(fn, msg):
        t = copy.deepcopy(GOOD_TESTS)
        fn(t)
        code, out = run(tmp_path, mutated(lambda p: p.update(tests=t)))
        assert code == 1 and msg in out, (msg, out)
    bad(lambda t: t.update(related="npx vitest related --run"), "tests.related must be a command containing {files}")
    bad(lambda t: t.update(unit="pytest"), "tests.unit must be a command containing {tests}")
    bad(lambda t: t["triggers"][0].pop("why"), "tests.triggers[0] needs a non-empty why")
    bad(lambda t: t["triggers"][0].update(paths=[]), "tests.triggers[0] needs paths")
    bad(lambda t: t["triggers"][0].update(edits=[]), "tests.triggers[0] edits must be a non-empty list of exact test file paths")
    bad(lambda t: t["triggers"][0].update(edits=["tests/*.py"]), "no globs")
    bad(lambda t: t["suites"][0].pop("name"), "tests.suites[0] needs a non-empty name")
    bad(lambda t: t["suites"][1].update(lock="yes"), "lock must be true or false")
    bad(lambda t: t.update(extra=1), "unknown key extra")
    code, out = run(tmp_path, mutated(lambda p: p.update(tests=[])))
    assert code == 1 and "tests must be an object" in out


def test_tests_commands_may_not_switch_parallelism_off(tmp_path):
    for flag in ("--no-file-parallelism", "--fileParallelism=false", "--runInBand", "-p 1", "-j1", "--maxWorkers=1", "--workers=1"):
        for where in ("related", "unit", "trigger", "suite"):
            t = copy.deepcopy(GOOD_TESTS)
            if where in ("related", "unit"):
                t[where] += f" {flag}"
            elif where == "trigger":
                t["triggers"][0]["run"] += f" {flag}"
            else:
                t["suites"][0]["cmd"] += f" {flag}"
            code, out = run(tmp_path, mutated(lambda p: p.update(tests=t)))
            assert code == 1 and "switches parallelism off" in out, (flag, where, out)
    t = copy.deepcopy(GOOD_TESTS)
    t["suites"][0]["cmd"] = "npm test -- -p 10 --maxWorkers=4"
    assert run(tmp_path, mutated(lambda p: p.update(tests=t)))[0] == 0
