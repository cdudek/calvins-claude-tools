"""The verify contract of the SDLC chain: one command, one last line.

    python3 scripts/verify_gate.py approve <id>              # lock the criteria at approval
    python3 scripts/verify_gate.py lint <id> [--pr-body FILE|-]  # plain language: short sentences, ids only in brackets; the PR body you publish
    python3 scripts/verify_gate.py feature|milestone <id> [--keep-going]   # run sdlc.json checks.<scope>
    python3 scripts/verify_gate.py project <slug>            # local milestones: checks.milestone on project/<slug>
    python3 scripts/verify_gate.py audit [--no-evidence]     # read-only: is every gate enforced?
    # After UX review, also require each visual run:
    # ... --visual-check <ux visual-check.py> --visual-run <run> [--visual-run <run> ...]

Written by `sdlc-run adopt` from the kit; edit the kit, not this copy. stdlib only.

`audit` changes nothing. For every sdlc.json check and every installed hook it reports four
states apart: installed (the checker or script exists), configured (which gate scope, CI job or
hook event invokes it), executed (the newest verify/report.json that ran it) and passed. For a
check run by a CI job it also reports whether that job is a required status on the default
branch (read with `gh api`; `unknown` when gh or the API is unavailable, `local` when no CI job
runs it). Last line `AUDIT PASS|FAIL problems=<n> unknown=<m>`, exit 1 on a problem: a missing
checker, a check that never ran (`--no-evidence` skips that test, for a CI runner without reports), a CI-run check that is not required, a hook file that is not
registered or a registered one that is missing.

`approve` writes <changesDir>/<id>/lock.json: the hash of facts.md, done.json and
sdlc.json `checks`, taken when the engineer approved the plan. `feature`/`milestone` refuse to
run against criteria that moved since. `approve` refuses (APPROVE FAIL) an unchecked
`checklist.md` item, an open CRITICAL in `analyze.md` or `challenge.md` and a plan violation without a justification.
`milestone` blocks on a `not met` or `partly` row in `validation.md`
(validation-not-met), an unchecked item in `findings.md` outside `## Advisory` (findings-open) and
a `## Converge` section without a `Converged:` line (not-converged). `milestone` also fails with check=parent-sync while
origin's default branch, or project/<slug> in a project, has commits HEAD lacks: merge them in
locally first. With `milestones.merge: "local"` the local project/<slug> must also be an ancestor
of HEAD, so a milestone cannot skip an earlier one merged locally. Then it runs the checks cheapest first and the first
failure stops the run (`--keep-going` runs them all and reports the first failure's verdict), and
writes <changesDir>/<id>/verify/report.json + report.md (a milestone on branch milestone/<slug>-<n> also milestone-<n>.json, never overwritten by another scope).

Cheapest first: a check that passed takes its seconds into verify/durations.json (keyed by command)
and the next run sorts by them; a check with no record yet sorts by a static guess from its
command (lint, format, typecheck, secrets and docs first, a build, e2e or docker run last, the
rest between). Equal costs keep their order in sdlc.json. A check that depends on an earlier
one's output sets `"serial": true`: it never moves, and nothing moves across it, or
`"after": ["<check name>"]`: it runs behind the named checks and moves freely otherwise. An approval
made before 3.18.0 (its lock.json has no `"order": "cost"`) keeps the declared order.

`project <slug>` (local milestones, stage 6p) runs `checks.milestone` on the checked-out
project/<slug>, which must contain origin's default branch, and records `VERIFY PASS project
<slug> <sha>`. It has no lock or change folder: the report lives in the common git dir
(`sdlc/projects/<slug>/verify/`), so every worktree sees it and `pr-gate.sh` reads it before the
one push of project/<slug>. `{id}` in a check is the slug.

Stdout is capped. The last line is exactly one of:
    VERIFY PASS <scope> <id> <sha>         exit 0
    VERIFY FAIL <scope> <id> check=<name>  exit 1   -- fix and run again
    VERIFY BLOCKED reason=<code>           exit 3   -- stop and ask the engineer

A repo whose `sdlcVersion` is missing or differs from the kit's gets one `WARN` line first;
it never changes the verdict.

A check may block on its own: when its output ends `VERIFY BLOCKED reason=<code>`, that line is
passed through. The same failure three runs in a row blocks with reason=no-progress, and any
three failed runs of one scope block with reason=attempts (delete verify/state.json to start
over; a PASS resets the count).

A check that passed on this exact tree, command and lock is not run again: verify/cache.json
holds the passes and the report says `ok (cached)`. A failing E2E check (command contains
`playwright` or `test:e2e`) is re-run once with `--last-failed` to say whether its failures
reproduce (real) or not (flaky). The check still counts as failed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import functools
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True  # imports of marks and sdlc_version must not leave __pycache__
import spec  # noqa: E402  (layout 4: the three documents, the rules, the id families)
from sdlc_version import kit_version, message  # noqa: E402

REASONS = {
    "not-approved",  # no lock.json: the plan gate has not run
    "protected-path",  # facts.md, done.json or checks changed since approval
    "no-progress",
    "attempts",  # three failed runs of one scope, whatever the failures were
    "flaky",
    "unknown-verdict",
    "needs-baseline",
    "allowlist-request",
    "scope-growth",
    "spec-conflict",
    "env",
    "test-proves-nothing",
    "validation-not-met",  # a `not met` or `partly` row in validation.md
    "findings-open",  # an unchecked item in findings.md outside ## Advisory
    "findings-blocked",  # an open item whose ## Dispositions row says blocked: terminal
    "not-converged",  # findings.md ## Converge has no `Converged:` line
}
LOCKED = ("facts.md", "done.json")
REPORT_FORMAT = 2  # a report of this format names its change, owner and milestone; hooks/pass_proof.py requires them
LOCK_FORMAT = 3  # written by `approve` into lock.json; strict records apply to locks of this version or later
ROUTING = ("size", "visualSource")  # decisions.json fields that route the gate, locked at approval
TAIL = 60  # stdout lines of a failing check
BREAKER = 3
ATTEMPTS = 3
SENTENCE_WORDS = 25
# What the owner reads. Facts, analyze, findings and the like are data tables of ids, not prose.
OWNER_FILES = ("intent.md", "plan.md", "milestone.md", "questions.md", "pr-body.md")
# The id families the chain defines: asks, bugs, facts, challenge findings, job stories,
# non-functional facts, questions, review findings, analyze findings (`references/readability.md`).
LEGACY_LETTERS = "ABFHJNQRX"


@functools.lru_cache(maxsize=None)
def id_patterns(letters: str = LEGACY_LETTERS) -> tuple[re.Pattern, re.Pattern, re.Pattern, re.Pattern]:
    """(bare id, definition label, table-row id, ids-only cell) for one set of family letters. The
    letter R is a review finding before layout 4 and a rule in it, where a finding is V."""
    token = rf"[{letters}]\d+"
    return (
        re.compile(rf"(?<![\w@/.#-]){token}\b"),
        # A definition label opens a line: `**F3**`, `**F3:**`, `**Q1 (date) the question?**`. The id
        # then stands alone; `**B19 blocks the build.**` is a sentence, not a label.
        re.compile(
            rf"^\s*(?:>\s*)?(?:(?:[-*]|\d+\.)\s+(?:\[[ x]\]\s+)?)?\*\*({token})(?=\*\*|:|\s*\(|\s*$)"
        ),
        re.compile(rf"^\s*\|\s*({token})\s*\|"),
        re.compile(rf"[\s,;/&+-]*(?:{token}[\s,;/&+-]*)*"),
    )


def letters_of(change: Path) -> str:
    return "".join(sorted(spec.id_families(change)))


PLACEHOLDER = re.compile(r"\[NEEDS CLARIFICATION: (?:<question>|\.\.\.)\]")  # the template's own words, no other
BRACKETS = re.compile(r"\([^()]*\)|\[[^\[\]]*\]")  # may span a line wrap, never a blank line


def sh(*cmd: str) -> str:
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def root() -> Path:
    return Path(sh("git", "rev-parse", "--show-toplevel") or ".").resolve()


def criteria_hash(change: Path, checks: object, plan: bool = True) -> dict[str, str]:
    """Hashes of what approval locks: facts.md, done.json, the checks and (from 3.21.0) the plan's
    `## Milestones` section, which decides which facts each milestone must prove. `plan=False`
    reads an older lock, which lacks that key."""
    v4 = spec.applies(change)
    hashes = {
        name: hashlib.sha256(spec.state_path(change, name).read_bytes()).hexdigest()
        for name in (("done.json",) if v4 else LOCKED)
        if spec.state_path(change, name).exists()
    }
    if v4:  # the spec, the design and the task rows replace facts.md and the plan's milestones
        hashes.update(
            {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in spec.lock_inputs(change).items()}
        )
    hashes["checks"] = hashlib.sha256(
        json.dumps(checks, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if plan and not v4:
        hashes["plan.milestones"] = hashlib.sha256(
            section(read(change / "plan.md"), "Milestones").encode("utf-8")
        ).hexdigest()
    if plan:  # every layout locks the routing fields
        hashes["decisions.routing"] = hashlib.sha256(
            json.dumps(routing(change), sort_keys=True).encode("utf-8")
        ).hexdigest()
    return hashes


def routing(change: Path) -> dict:
    """The routing fields of decisions.json (an unreadable file locks as itself, so editing it moves the hash)."""
    path = spec.state_path(change, "decisions.json")
    if not path.exists():
        return {"missing": True}
    try:
        data = json.loads(read(path))
    except (OSError, ValueError):
        return {"unreadable": True}
    return {k: data.get(k) for k in ROUTING} if isinstance(data, dict) else {"unreadable": True}


def merges_locally(cfg: dict) -> bool:
    """`milestones.merge: "local"`: milestones merge into project/<slug> on this machine."""
    return (cfg.get("milestones") or {}).get("merge") == "local"


def project_record(slug: str, repo: Path | None = None) -> Path:
    """Where `project <slug>` writes its report: the common git dir, shared by all worktrees."""
    common = sh(
        "git", "-C", str(repo or "."), "rev-parse", "--path-format=absolute", "--git-common-dir"
    )
    return Path(common or ".git") / "sdlc" / "projects" / slug


def has_bundle_inputs(change: Path) -> bool:
    """A design bundle under asks/ (an index.html, or the folder decisions.json names as
    visualSource.path). Read without marks.py, so an old copy of it cannot hide one."""
    if next((change / "asks").rglob("index.html"), None):
        return True
    try:
        declared = json.loads(spec.state_path(change, "decisions.json").read_text(encoding="utf-8"))
        path = (change / declared["visualSource"]["path"]).resolve()
        return path.is_dir() and path.is_relative_to((change / "asks").resolve())
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def milestone_number(change: Path, cfg: dict, branch: str) -> int | None:
    """The milestone `branch` is (`<prefix><slug>-<n>` is n, `<prefix><slug>` is 1), else None; the
    rule of hooks/pass_proof.py `milestone_of`, kept equal by test_contract."""
    prefix = (cfg.get("milestones") or {}).get("branchPrefix", "milestone/")
    try:
        slug = (json.loads(spec.state_path(change, "decisions.json").read_text(encoding="utf-8")).get("milestone") or {}).get("slug")
    except (OSError, ValueError, AttributeError):
        slug = None
    slug = slug or re.sub(r"^[A-Z][A-Z0-9]+-\d+-", "", re.sub(r"^\d{4}-\d{2}-\d{2}-", "", change.name))
    name = branch[len(prefix) :] if branch.startswith(prefix) else ""
    if not name:
        return None
    if name == slug:
        return 1
    found = re.fullmatch(re.escape(slug) + r"-(\d+)", name)
    return int(found[1]) if found else None


def project_branch(change: Path, cfg: dict) -> str:
    """project/<slug> of the change's project when it has a branch, else "". A project without
    `branch: true` is planning only (3.7.0), but one written before 3.7.0 has no `branch` key
    and keeps its branch."""
    try:
        project = json.loads(spec.state_path(change, "decisions.json").read_text(encoding="utf-8")).get("project")
    except (OSError, ValueError, AttributeError):
        project = None
    if isinstance(project, dict) and project.get("slug") and project.get("branch", True):
        return f"{(cfg.get('projects') or {}).get('branchPrefix', 'project/')}{project['slug']}"
    return ""


def parent_tips(change: Path, cfg: dict) -> list[tuple[str, str]]:
    """(branch, sha) on origin of every branch a milestone must contain: the default branch,
    and project/<slug> too when the change's project has a branch. A branch origin lacks
    (no remote, offline, project not created yet, or never pushed in local mode) is left out."""
    names = [cfg.get("defaultBranch") or "main"]
    if branch := project_branch(change, cfg):
        names.insert(0, branch)
    tips = []
    for name in names:
        sh("git", "fetch", "--quiet", "origin", name)  # offline: the last fetched tip still counts
        tip = sh("git", "rev-parse", "--verify", "--quiet", f"origin/{name}^{{commit}}")
        if tip:
            tips.append((name, tip))
    return tips


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def table_rows(text: str) -> list[list[str]]:
    """Cells of every markdown table row, separator rows dropped; the header is the first row."""
    return [
        [c.strip() for c in line.strip().strip("|").split("|")]
        for line in text.splitlines()
        if line.lstrip().startswith("|") and not re.fullmatch(r"\s*\|[\s:|-]+\|\s*", line)
    ]


def section(text: str, heading: str) -> str:
    m = re.search(rf"^#{{2,3}} {re.escape(heading)}\s*$(.*?)(?=^#{{1,3}} |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def open_criticals(change: Path, name: str) -> list[str]:
    """CRITICAL rows still `open` in analyze.md or challenge.md; an absent file has none."""
    return [
        f"{name}: open CRITICAL: {row[0]} {' '.join(row[3:5])[:80]}"
        for row in table_rows(read(change / name))
        if "CRITICAL" in row and row[-1].lower() == "open"
    ]


def approval_blockers(change: Path) -> list[str]:
    """What stops the plan gate: the checklist, the analyze and challenge passes and the plan's unjustified rule
    violations. A file that does not exist blocks nothing."""
    out = []
    open_items = re.findall(r"^\s*[-*] \[ \] (.*)$", read(change / "checklist.md"), re.M)
    out += [f"checklist.md: unchecked: {i[:80]}" for i in open_items]
    out += open_criticals(change, "analyze.md") + open_criticals(change, "challenge.md")
    for row in table_rows(section(read(change / "plan.md"), "Justified violations"))[1:]:
        if row[0].lower() != "none" and (len(row) < 3 or any(not c or c[0] == "<" for c in row)):
            out.append(f"plan.md: unjustified violation: {row[0][:80]}")
    return out


E2E_ENTRY = re.compile(r"playwright|test:e2e|\be2e\b|cypress")
E2E_SCOPED = re.compile(
    r"--grep|--only-changed|--last-failed|--repeat-each|\bseq\b|\bfor\b|\brelated\b"
    r"|\.(?:spec|test)\.\w+|test_\w+\.py|\$specs"
)


E2E_REPEAT = re.compile(r"--repeat-each|\bseq\s+3\b|\bin\s+1\s+2\s+3\b|--count[= ]3")


def has_e2e_config(repo: Path) -> bool:
    """The repo has an E2E suite of its own: a playwright config or an e2e/ folder."""
    return (repo / "e2e").is_dir() or any(repo.glob("playwright.config.*"))


def full_e2e_gap(checks: list, repo: Path) -> str:
    """"" when `checks.milestone` names a full E2E entry (or the repo has no E2E suite), else why
    not: the gate is the only runner of the full suite, so a list without it never runs it."""
    if not has_e2e_config(repo):
        return ""
    cmds = [c["run"] if isinstance(c, dict) else c for c in checks]
    full = any(E2E_ENTRY.search(c) and not E2E_SCOPED.search(c) for c in cmds)
    repeat = any(E2E_ENTRY.search(c) and E2E_REPEAT.search(c) for c in cmds)
    if full and repeat:
        return ""
    return (
        "sdlc.json checks.milestone has no full E2E entry and a repeat (x3) of the changed and flaky specs "
        "although the repo has an E2E suite: add the full E2E command (the stack's, run once) and the repeat"
        if not full
        else "sdlc.json checks.milestone has a full E2E entry but no repeat (x3) of the changed and flaky specs "
        "although the repo has an E2E suite: add the repeat"
    )


PLAIN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")  # one path component, never a flag
PLAIN_BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")


def plain_id(name: str) -> bool:
    return bool(PLAIN_ID.fullmatch(name)) and ".." not in name


def plain_branch(name: str) -> bool:
    return bool(PLAIN_BRANCH.fullmatch(name)) and all(p not in ("", "..") for p in name.split("/"))


def unsafe_substitutions(change_id: str, cfg: dict) -> str:
    """Why `{id}` or `{base}` may not be put into a shell command line, or "" when both are plain."""
    if not plain_id(change_id):
        return (
            f"the change id {change_id!r} is not a plain name "
            "(start with a letter or digit; then letters, digits, . _ -; no ..)"
        )
    branch = cfg.get("defaultBranch") or "main"
    if not plain_branch(branch):
        return (
            f"sdlc.json defaultBranch {branch!r} is not a plain branch name "
            "(start with a letter or digit; no leading -, no .. or empty component)"
        )
    return ""


def parent_ref(change: Path, cfg: dict, repo: Path) -> str:
    """The ref a milestone's diff base is: the project branch it merges into (origin's, or the
    local one in local mode) when the change has a project branch that exists, else the default
    branch on origin."""
    if (pb := project_branch(change, cfg)) and plain_branch(pb):
        local = merges_locally(cfg) and sh("git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{pb}^{{commit}}")
        if local:
            return pb
        if sh("git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"origin/{pb}^{{commit}}"):
            return f"origin/{pb}"
    return f"origin/{cfg.get('defaultBranch') or 'main'}"


def parent_gap(repo: Path, base: str) -> list[str]:
    """Layout 4 compares the change with its parent branch. When no parent resolves (a fresh clone
    with no `origin`, a renamed default branch) that is the environment's gap, not a failed change:
    the message and the fix line, or nothing."""
    if spec.resolve_base(repo, base):
        return []
    default = base.removeprefix("origin/")
    return [
        f"the parent branch ({base}) cannot be resolved: the living-spec diff has nothing to compare with.",
        f"Fix: `git fetch origin {default}` (or create the branch), or set sdlc.json `defaultBranch` to its real name; then run again.",
    ]


def expand(cmd: str, change_id: str, cfg: dict, base: str = "") -> str:
    """`{id}` is the change, `{base}` the diff base of a repeat run: `base` (the real parent ref,
    see parent_ref) or else the default branch on origin. Both go into a command run by a shell,
    so only plain names are substituted."""
    if why := unsafe_substitutions(change_id, cfg):
        raise ValueError(why)
    base = base or f"origin/{cfg.get('defaultBranch') or 'main'}"
    if not plain_branch(base):
        raise ValueError(f"the diff base {base!r} is not a plain ref")
    return cmd.replace("{id}", shlex.quote(change_id)).replace("{base}", shlex.quote(base))


SETTLED = ("accepted", "deferred")  # `fixed` is the ticked box; `blocked` is terminal


def item_id(item: str) -> str:
    """The id of a findings.md item: its explicit bold label (**B2**, **C1**) when it follows the
    finding-id grammar shared with the producers, else "" (an item without one can never be
    settled by an owner answer)."""
    from marks import FINDING_ID  # lazy: an old marks.py never breaks approve, audit or lint

    m = re.match(rf"\*\*({FINDING_ID})\*\*", item.strip())
    return m.group(1) if m else ""


NO_EVIDENCE = {"", "-", "--", "n/a", "na", "none", "tbd", "todo", "?"}


def lock_format(change: Path) -> int:
    """The format version `approve` wrote into lock.json: 0 for a lock from before it existed or no
    lock. An unreadable lock reads as the newest format (fail closed)."""
    if not spec.state_path(change, "lock.json").exists():
        return 0
    try:
        return int(json.loads(read(spec.state_path(change, "lock.json"))).get("format", 0))
    except (ValueError, AttributeError, TypeError):
        return LOCK_FORMAT


def current_format(change: Path) -> bool:
    """Approved under lock format 3 or later: its records may not be missing and its validation rows
    are strict. An older lock (including one that merely holds done.json) keeps the old behaviour and
    gets an upgrade-gap note."""
    return lock_format(change) >= LOCK_FORMAT


def approved_facts(change: Path) -> tuple[list[str], list[str]]:
    """(fact ids of the approved `done.json`, problems). A missing or unparsable file is a problem
    on a current-format change; a legacy change without one has no facts to derive."""
    problem = "validation.md: done.json is missing or unreadable, so the approved facts are unknown"
    if not spec.state_path(change, "done.json").exists():
        return [], [problem] if current_format(change) else []
    try:
        listed = json.loads(read(spec.state_path(change, "done.json"))).get("facts")
        if not isinstance(listed, list):
            raise ValueError("facts is not a list")
        return [str(f["id"] if isinstance(f, dict) else f) for f in listed if f], []
    except (ValueError, AttributeError, KeyError, TypeError):
        return [], [problem]


FACT_RANGE = re.compile(r"\b([A-Z])(\d+)\s*(?:to|\.\.|[-\u2013\u2014])\s*(?:[A-Z])?(\d+)\b")


def cell_ids(cell: str, universe: list[str]) -> list[str]:
    """The ids of `universe` a plan cell names: `F1`, `F1 to F132`, `F1-F7`, `F8\u2013F20`; its order."""
    named: set[str] = set()
    for m in FACT_RANGE.finditer(cell):
        lo, hi = int(m[2]), int(m[3])
        named.update(f"{m[1]}{k}" for k in range(lo, min(hi, lo + 5000) + 1))
    named.update(re.findall(r"\b[A-Z]\d+\b", FACT_RANGE.sub(" ", cell)))
    return [f for f in universe if f in named]


def row_facts(plan: str, number: int, facts: list[str]) -> list[str]:
    """The approved `facts` the `## Milestones` row of milestone `number` lists (`M1 ...` or a bare `1`).
    A plan with one row whose cell names no id (`rows 0 to 5, 74 facts`) gives that row every fact."""
    rows = table_rows(section(plan, "Milestones"))[1:]
    row = next((r for r in rows if len(r) > 1 and re.match(rf"M?{number}\b", r[0])), None)
    mine = cell_ids(row[1], facts) if row else []
    if not mine and row and len(rows) == 1 and row[1].strip().lower() not in ("", "none", "-") and not re.search(r"\b[A-Z]\d+\b", row[1]):
        return list(facts)
    return mine


def milestone_facts(change: Path, number: int | None = None) -> tuple[list[str], list[str]]:
    """(the approved facts this milestone must prove, problems). Under lock format 3 and for a known
    milestone `number`, the `## Milestones` row of `plan.md` selects them and a missing or empty row is
    a problem; an older lock uses every approved fact (its plan rows were never locked)."""
    facts, problems = approved_facts(change)
    if number and facts and spec.applies(change):  # layout 4: the rules of this milestone's tasks
        tasks = spec.table(read(change / "tasks.md"), "Tasks")
        if not tasks:  # a scope S change has no task table: one milestone, every rule
            return facts, problems
        mine = {
            f"R{n}"
            for t in tasks
            if re.match(rf"M?{number}\b", spec._cell(t, "milestone"))
            for n in re.findall(r"R(\d+)", spec._cell(t, "rules", "satisf"))
        }
        if not mine & set(facts):
            return [], problems + [f"validation.md: tasks.md has no task for M{number} that lists approved rules"]
        return [f for f in facts if f in mine], problems
    if number and facts and current_format(change):
        mine = row_facts(read(change / "plan.md"), number, facts)
        if not mine:
            return [], problems + [
                f"validation.md: plan.md ## Milestones has no row for M{number} that lists approved facts"
            ]
        return mine, problems
    return facts, problems


def validation_gaps(change: Path, number: int | None = None) -> list[str]:
    """What validation.md lacks: for every approved fact of this milestone one row with the verdict
    `met` and evidence (a test, a file, an observed artefact: not empty, not a placeholder). Only a
    change approved under lock format 3 is held to it; an older one gets an upgrade-gap note instead."""
    if not current_format(change):
        return []
    rows = table_rows(read(change / "validation.md"))
    head = [c.lower() for c in rows[0]] if rows else []
    at = head.index("evidence") if "evidence" in head else 3
    facts, gaps = milestone_facts(change, number)
    for fact in facts:
        mine = [r for r in rows if fact in cell_ids(r[0] if r else "", [fact])]
        if not mine:
            gaps.append(f"validation.md: {fact} has no row")
        for row in mine:
            # the verdict is the last cell and never doubles as the evidence cell
            evidence = row[at].strip(" `") if len(row) > at and at < len(row) - 1 else ""
            if row[-1].strip().lower() != "met":
                gaps.append(f"validation.md: {fact} is not marked met")
            elif evidence.lower() in NO_EVIDENCE or evidence[:1] == "<":
                gaps.append(f"validation.md: {fact} is met without evidence")
    return gaps


def read_decisions(change: Path) -> dict | None:
    """decisions.json as a dict ({} when unparsable or not an object), None when the file is missing."""
    path = spec.state_path(change, "decisions.json")
    if not path.exists():
        return None
    try:
        data = json.loads(read(path))
    except (OSError, ValueError, AttributeError):
        return {}
    return data if isinstance(data, dict) else {}


def sources_present(change: Path) -> bool:
    """The change holds visual inputs: marks.json, owner sessions, a bundle, a loose reference
    image or a capture manifest (any one makes `marks.py check` mandatory)."""
    if (change / "marks.json").exists() or (change / "verify/shots/manifest.json").exists():
        return True
    try:
        from marks import inventory  # absent in an older marks.py: no loose-image check then

        return bool(inventory(change))
    except ImportError:
        return False
    except (OSError, ValueError):
        return True  # an inventory that cannot be read is itself a marks failure


def visual_run_required(change: Path, cfg: dict, repo: Path) -> bool:
    """A milestone needs a current UX visual run when the UX plan is on, the decision says the
    change has an interface (`size` is not `none`) and a visual source or reference exists, unless
    `decisions.json` `skips.visual` is a `skip -- <reason>` that the owner attested. decisions.json
    is not part of the approval lock, so the attestation is the owner's answer to the dialog
    `Change <id>, finding visual-skip: ...` (options Skip visual evidence, Run visual evidence)."""
    decisions = read_decisions(change) or {}
    if cfg.get("ux") == "off":
        return False
    skip = str((decisions.get("skips") or {}).get("visual", ""))
    if re.match(r"skip -- \S", skip):
        from marks import owner_decisions

        if owner_decisions(repo, change.name).get("visual-skip", ("",))[0] == "skip":
            return False
    # `size: none` only waives loose sources: an explicit visual source always needs its run
    return bool(decisions.get("visualSource")) or (decisions.get("size") != "none" and sources_present(change))


def refusal(name: str, message: str) -> dict:
    """An evidence check that fails with `message`: the gate says why before any suite runs."""
    return {
        "name": name,
        "cache": False,
        "run": shlex.join([sys.executable, "-c", f"import sys; print({message!r}); sys.exit(1)"]),
    }


def milestone_blockers(change: Path, number: int | None = None) -> tuple[str, list[str]] | None:
    """The records a milestone must close before it passes: (reason, offending lines) or None.
    A residual finding is settled only by the owner's answer to a dialog `Change <id>, finding
    <finding id>: ...` (`marks.owner_decisions`, the one reader gate and status share)."""
    rows = table_rows(read(change / "validation.md"))
    bad = [r for r in rows if any(c.lower() in ("not met", "partly") for c in r)]
    if bad:
        return "validation-not-met", [f"validation.md: {r[0]} {r[-1]}" for r in bad]
    findings = read(change / "findings.md")
    advisory = section(findings, "Advisory")
    items = re.findall(r"^\s*[-*] \[([ x])\] (.*)$", findings.replace(advisory, ""), re.M)
    ids = [item_id(text) for _, text in items]
    decided = {}
    if any(ids):
        repo = Path(sh("git", "-C", str(change), "rev-parse", "--show-toplevel") or ".")
        from marks import owner_decisions

        decided = owner_decisions(repo, change.name, change / "findings.md", "**{}**", with_time=True)
    # a terminal `Block the close` answer counts against every finding, ticked or not: a ticked
    # box is no evidence against the owner's block; a later answer from the owner resolves it
    blocked = [
        f"findings.md: blocked: {text[:80]}" + (" (ticked, contradicts the owner's block)" if mark == "x" else "")
        for (mark, text), k in zip(items, ids)
        if k and decided.get(k, ("",))[0] == "blocked"
    ]
    if blocked:
        return "findings-blocked", blocked
    open_ids = [k for (mark, _), k in zip(items, ids) if mark == " "]

    def ticked_after_fix(k: str) -> bool:
        """`Fix it now` is an instruction: a ticked box counts only if it was ticked after it."""
        from marks import first_seen

        stamp = decided[k][2]
        began = first_seen(repo, change / "findings.md", f"[x] **{k}**")
        return bool(began and began > stamp)

    # an answer binds to exactly one open item: an id shared by two open items settles neither
    open_items = [
        text
        for (mark, text), k in zip(items, ids)
        if (mark == " " and not (k and open_ids.count(k) == 1 and decided.get(k, ("",))[0] in SETTLED))
        or (mark == "x" and k and decided.get(k, ("",))[0] == "fix" and not ticked_after_fix(k))
    ]
    if open_items:
        return "findings-open", [f"findings.md: open: {i[:80]}" for i in open_items]
    if (section(findings, "Converge") or current_format(change)) and "Converged:" not in findings:
        return "not-converged", ["findings.md: ## Converge has no `Converged: round <n>` line"]
    if gaps := validation_gaps(change, number):
        return "validation-not-met", gaps
    return None


def legacy_marks() -> bool:
    """scripts/marks.py from before design bundles: a kept copy (sdlc.json `keep`) can stay old."""
    import marks

    return not callable(getattr(marks, "bundles", None))


def has_owner_marks(change: Path) -> bool:
    """Owner notes or a design bundle to check. marks.py is imported here and nowhere else, so an
    older copy of it beside a newer gate never breaks approve, audit or lint."""
    import marks

    return bool(
        (change / "marks.json").exists()
        or marks.sessions(change)
        or (callable(getattr(marks, "bundles", None)) and marks.bundles(change))  # an old marks.py has no `bundles`
        or sources_present(change)
    )


def end(line: str, code: int) -> int:
    print(line)
    return code


def graph_problems(plan: str) -> list[str]:
    """The plan's `## Milestones` graph must be buildable: unique ids, every `needs` defined, no
    milestone needing itself and no cycle (two milestones waiting on each other's merge)."""
    rows = [r for r in table_rows(section(plan, "Milestones"))[1:] if r and re.match(r"M\d+\b", r[0])]
    ids = [re.match(r"M\d+", r[0])[0] for r in rows]
    problems = [f"plan.md: {i} is defined twice" for i in dict.fromkeys(ids) if ids.count(i) > 1]
    needs: dict[str, list[str]] = {}
    for r in rows:
        mine = re.match(r"M\d+", r[0])[0]
        listed = re.findall(r"M\d+", r[2]) if len(r) > 2 else []
        needs[mine] = listed
        problems += [f"plan.md: {mine} needs itself" for _ in listed if _ == mine]
        problems += [f"plan.md: {mine} needs {n}, which the plan does not define (unknown milestone)" for n in listed if n not in ids]
    done: set[str] = set()
    for start in needs:  # depth-first, one report per cycle
        stack, on = [(start, iter(needs[start]))], {start}
        while stack:
            node, it = stack[-1]
            nxt = next((n for n in it if n in needs and n != node), None)
            if nxt is None:
                stack.pop()
                on.discard(node)
                done.add(node)
            elif nxt in on:
                problems.append(f"plan.md: circular milestones: {node} and {nxt} wait on each other")
                break
            elif nxt not in done:
                on.add(nxt)
                stack.append((nxt, iter(needs[nxt])))
    return list(dict.fromkeys(problems))


def branch_mode_problems(change: Path, cfg: dict) -> list[str]:
    """Delivery and merge modes that cannot both be served: feature PRs publish a milestone branch
    that local milestones, once the change has a project branch, never push (checked at approval,
    before any branch or goal exists)."""
    if cfg.get("delivery") == "feature-prs" and merges_locally(cfg) and project_branch(change, cfg):
        return [
            'sdlc.json: delivery "feature-prs" needs a remote milestone branch, which milestones.merge '
            '"local" never pushes for a change with a project branch; choose delivery "one-go" with '
            'local milestones, or milestones.merge "pr" with feature PRs'
        ]
    return []


def v4_done(change: Path) -> dict:
    """done.json of a layout-4 change, derived from the spec: one fact per rule the change adds or
    changes (id R<n>, tag @R<n>), with the screens and states its UX table names."""
    ux = spec.table(read(change / "spec.md"), "UX")
    facts = []
    for n, rule in sorted(spec.change_rules(change).items()):
        if rule["change"] == "removed":
            continue
        rows = [r for r in ux if re.search(rf"\bR{n}\b", spec._cell(r, "rule"))]
        facts.append(
            {
                "id": f"R{n}",
                "tag": f"@R{n}",
                "screens": sorted({spec._cell(r, "screen") for r in rows}),
                "states": sorted({spec._cell(r, "state") for r in rows}),
            }
        )
    return {"facts": facts}


def approve(change: Path, cfg: dict) -> int:
    v4 = spec.applies(change)
    problems = lint_problems(change) + approval_blockers(change)  # the cheap pure check first
    if v4:  # the spec, its rule files and the diff against the parent agree before anyone locks it
        base = parent_ref(change, cfg, root())
        if gap := parent_gap(root(), base):
            print("\n".join(gap))
            return end("APPROVE BLOCKED reason=env", 3)
        problems += spec.consistency(change, "approve", root(), base) + spec.check(root(), base)
    else:
        problems += [f"{name} is missing: approval locks it" for name in ("facts.md", "plan.md") if not (change / name).is_file()]
        problems += graph_problems(read(change / "plan.md"))
    problems += branch_mode_problems(change, cfg)
    if gap := full_e2e_gap((cfg.get("checks") or {}).get("milestone") or [], root()):
        problems.append(gap)
    if not v4 and not spec.state_path(change, "done.json").exists():  # approval requires its artifacts
        problems.append("done.json is missing: the approved facts cannot be locked without it")
    elif not v4 and approved_facts(change)[1]:
        problems.append("done.json is unreadable or has no `facts` list")
    if problems:
        print("\n".join(problems[:TAIL]))
        return end(f"APPROVE FAIL {change.name} problems={len(problems)}", 1)
    if v4:
        spec.state_path(change, "done.json").write_text(json.dumps(v4_done(change), indent=2) + "\n", encoding="utf-8")
    lock = {
        "approved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),  # noqa: UP017 -- runs on macOS python3 3.9
        "sha": sh("git", "rev-parse", "HEAD"),
        "criteria": criteria_hash(change, cfg.get("checks", {})),
        "order": "cost",  # a lock without this key keeps the declared order (before 3.18.0)
        "manifest": "required",  # from 3.21.0 visual work needs verify/shots/manifest.json
        "format": LOCK_FORMAT,  # strict validation rows and records apply to this lock and later ones
        "layout": 4 if v4 else 3,  # the hooks read the layout here, not from files an edit can change
    }
    spec.state_path(change, "lock.json").write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"locked {', '.join(lock['criteria'])} in {change.name}/lock.json -- commit it")
    return 0


def prose(text: str) -> list[str]:
    """Sentences outside frontmatter, code fences, tables, headings and HTML comments."""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"```.*?```|<!--.*?-->", "", text, flags=re.S)
    lines = [
        re.sub(r"^\s*(?:[-*]|\d+\.)\s+(?:\[[ x]\]\s+)?", "", line)
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("|", "#", ">"))
    ]
    return [s for line in lines for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]


def defined_ids(change: Path) -> set[str]:
    """The ids this change defines: a table row that opens with the id, or a definition label.
    An id defined nowhere ("Press F5", "before Q4") is ordinary text and never flagged."""
    _, label, table_id, _ = id_patterns(letters_of(change))
    found = set()
    for path in change.rglob("*.md"):
        if path.name == "README.md" or {"asks", "verify"} & set(path.relative_to(change).parts):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if m := table_id.match(line) or label.match(line):
                found.add(m.group(1))
    return found


def bare_ids(text: str, defined: set[str], letters: str = LEGACY_LETTERS) -> list[tuple[str, str]]:
    """(id, context) for every defined id in running text that is not inside brackets: "plain words
    first, the id in brackets after". Headings, code, the first cell of a table row, a cell that
    holds only ids, a definition label and the verbatim Words column of the intent's Asks table are
    structure; every other table cell is prose."""
    bare, label, _, ids_only = id_patterns(letters)
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"```.*?```|<!--.*?-->", "", text, flags=re.S)
    found: list[tuple[str, str]] = []
    para: list[str] = []
    heading, header = "", []  # the last heading, and the header row of the table being read

    def flush() -> None:
        body = "\n".join(para)
        para.clear()
        for _ in range(3):  # nested brackets: (A1; see [F2])
            body = BRACKETS.sub("", body)
        for m in bare.finditer(body):
            if m.group(0) in defined:
                around = " ".join(body[max(0, m.start() - 30) : m.end() + 30].split())
                found.append((m.group(0), around))

    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            header = []
        if not s or s.startswith("#"):
            flush()
            heading = s.lstrip("# ").lower() if s else heading
        elif s.startswith("|"):
            flush()
            cells = [c.strip() for c in s.strip("|").split("|")]
            header = header or [c.lower() for c in cells]
            for i, cell in enumerate(cells[1:], 1):
                verbatim = heading == "asks" and header[i : i + 1] == ["words"]
                if not verbatim and not ids_only.fullmatch(cell):
                    para.append(cell)
                    flush()
        else:
            if re.match(r"(?:[-*]|\d+\.)\s", s):
                flush()  # a new list item never shares a bracket with the one before
            para.append(re.sub(r"`[^`]*`", "", label.sub("", line)))
    flush()
    return found


def lint_problems(change: Path, body: str | None = None) -> list[str]:
    """Plain language: no sentence over SENTENCE_WORDS words, no leftover template prompts, and
    in the files the owner reads no id outside brackets. With `body`, only that text (the PR body
    about to be published) is checked, for ids. Pure file reads."""
    defined, letters = defined_ids(change), letters_of(change)
    if body is not None:
        return [
            f"pr-body: id {bare} outside brackets, words first: {ctx}"
            for bare, ctx in bare_ids(body, defined, letters)
        ]
    problems = []
    v4 = spec.applies(change)
    docs = spec.documents(change)  # the three documents in layout 4, intent/facts/plan before
    for name in (*docs, "questions.md", "pr-body.md") if v4 else OWNER_FILES:
        path = change / name
        if path.exists():
            for bare, ctx in bare_ids(path.read_text(encoding="utf-8"), defined, letters):
                problems.append(f"{name}: id {bare} outside brackets, words first: {ctx}")
    for name in docs if v4 else ("intent.md", "facts.md", "plan.md"):
        path = change / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for s in prose(text):
            if len(s.split()) > SENTENCE_WORDS:
                problems.append(f"{name}: {len(s.split())} words: {s[:90]}...")
        # an open question is a marker in running text; the same words in code explain the syntax
        # a fenced Gherkin step is running requirements text: only the template's own placeholder
        # marker (`<question>`, `...`) is skipped there
        unfenced = re.sub(r"```(.*?)```", lambda m: PLACEHOLDER.sub("", m[1]), text, flags=re.S)
        if "[NEEDS CLARIFICATION" in re.sub(r"`[^`\n]*`|<!--.*?-->", "", unfenced, flags=re.S):
            problems.append(f"{name}: an open [NEEDS CLARIFICATION] remains")
    return problems


def lint(change: Path, body: str | None = None) -> int:
    problems = lint_problems(change, body)
    for p in problems[:TAIL]:
        print(p)
    print(f"LINT {'FAIL' if problems else 'PASS'} {change.name} problems={len(problems)}")
    return 1 if problems else 0


def signature(name: str, output: str) -> str:
    tail = "\n".join(output.strip().splitlines()[-20:])
    tail = re.sub(r"\d+(\.\d+)?m?s\b|\b[0-9a-f]{7,40}\b", "#", tail)  # timings and shas drift
    return hashlib.sha256(f"{name}\n{tail}".encode()).hexdigest()[:16]


def cache_key(tree: str, cmd: str, criteria: dict[str, str]) -> str:
    return hashlib.sha256(
        "\n".join([tree, cmd, json.dumps(criteria, sort_keys=True)]).encode()
    ).hexdigest()


def is_e2e(cmd: str) -> bool:
    return "playwright" in cmd or "test:e2e" in cmd


def classify_e2e(cmd: str, repo: Path) -> str:
    """Re-run only the failures of an E2E check: they reproduce (real) or they do not (flaky)."""
    last = repo / "test-results" / ".last-run.json"
    if last.exists() and not json.loads(last.read_text(encoding="utf-8")).get("failedTests"):
        return ""  # nothing recorded as failed: --last-failed would run the whole suite
    again = subprocess.run(
        f"{cmd} --last-failed",
        shell=True,
        cwd=repo,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    return "reproduced (real)" if again.returncode else "did not reproduce (flaky)"


def metrics(change: Path, report: dict, retries: int, started: float) -> dict:
    """The operational numbers of one gate run, for the report: what ran and how it ended,
    how many earlier runs of this scope failed, review rounds, seconds, findings still open."""
    checks = report["checks"]
    findings = read(change / "findings.md")
    advisory = section(findings, "Advisory")
    open_findings = re.findall(r"^\s*[-*] \[ \] ", findings.replace(advisory, ""), re.M)
    rounds = [int(n) for n in re.findall(r"Converged: round (\d+)", findings)]
    return {
        "checks_run": sum(1 for c in checks if not c.get("cached")),
        "checks_cached": sum(1 for c in checks if c.get("cached")),
        "checks_passed": sum(1 for c in checks if c["status"] == "pass"),
        "checks_failed": sum(1 for c in checks if c["status"] != "pass"),
        "retries": retries,
        "review_rounds": max(rounds, default=0),
        "elapsed_s": round(time.monotonic() - started, 1),
        "open_findings": len(open_findings)
        + len(open_criticals(change, "analyze.md"))
        + len(open_criticals(change, "challenge.md")),
    }


# What a check with no recorded duration probably costs, by its name and command: first match wins.
COST_HINTS = (
    (
        re.compile(
            r"format|fmt|lint|ruff|eslint|prettier|biome|oxlint|stylelint|typecheck|tsc|mypy"
            r"|secret|gitleaks|actionlint|shellcheck|docs"
        ),
        5.0,
    ),
    (re.compile(r"e2e|playwright|cypress|smoke|docker|build|integration|migrat"), 600.0),
)
DEFAULT_COST = 60.0  # unit tests and anything unrecognised


def order_checks(
    checks: list[dict], durations: dict[str, float], change_id: str, cfg: dict | None = None
) -> list[dict]:
    """Cheapest first: recorded seconds when there are any, else a guess from the command. Stable,
    so ties keep their sdlc.json order; a `serial` check is a wall that nothing moves across, and
    `"after": [<check name>]` keeps a check behind the ones it needs (codegen before tsc)."""

    def cost(check: dict) -> float:
        cmd = expand(check["run"], change_id, cfg or {})
        if cmd in durations:
            return durations[cmd]
        text = f"{check['name']} {cmd}".lower()
        return next((c for rx, c in COST_HINTS if rx.search(text)), DEFAULT_COST)

    ordered: list[dict] = []
    segment: list[dict] = []
    for check in checks:
        if check.get("serial"):
            ordered += sorted(segment, key=cost) + [check]
            segment = []
        else:
            segment.append(check)
    ordered += sorted(segment, key=cost)
    done: set[str] = set()
    names = {c["name"] for c in ordered}
    result: list[dict] = []
    while ordered:
        # the first check whose named predecessors have run; a cycle or unknown name never blocks
        nxt = next(
            (c for c in ordered if all(a in done or a not in names for a in c.get("after") or [])),
            ordered[0],
        )
        ordered.remove(nxt)
        done.add(nxt["name"])
        result.append(nxt)
    return result


CHECK_TIMEOUT = 1800  # seconds a single check may run (sdlc.json `checkTimeout`, or `timeout` on the check)


def run_check(cmd: str, cwd: Path, limit: int) -> subprocess.CompletedProcess[str]:
    """Run a shell check in its own process group; past `limit` seconds kill the group and report 124."""
    import signal

    proc = subprocess.Popen(
        cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        stdin=subprocess.DEVNULL, start_new_session=True,
    )  # fmt: skip
    try:
        out, err = proc.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
        return subprocess.CompletedProcess(cmd, 124, out or "", (err or "") + f"\ntimed out after {limit}s\n")
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def run(
    scope: str,
    change: Path,
    cfg: dict,
    repo: Path,
    visual_check: str | None = None,
    visual_runs: list[str] | None = None,
    keep_going: bool = False,
) -> int:
    if why := unsafe_substitutions(change.name, cfg):
        print(f"refused before any check runs: {why}.")  # the id and branch reach a shell line
        return end("VERIFY BLOCKED reason=env", 3)
    out_dir = change / "verify"
    out_dir.mkdir(exist_ok=True)
    report: dict = {"scope": scope, "id": change.name, "checks": []}
    started_run = time.monotonic()
    try:
        retries = json.loads((out_dir / "state.json").read_text()).get("attempts", {}).get(scope, 0)
    except (OSError, ValueError):
        retries = 0
    kit, changelog = kit_version()
    notice = message(cfg.get("sdlcVersion"), kit, changelog)
    if notice:
        print(f"WARN {notice}")  # never blocks; the last line stays the verdict

    number = milestone_number(change, cfg, sh("git", "symbolic-ref", "--short", "-q", "HEAD")) if scope == "milestone" else None

    def finish(line: str, code: int) -> int:
        report["result"] = line
        report["format"] = REPORT_FORMAT
        report["sha"] = sh("git", "rev-parse", "HEAD")
        if scope != "project":  # what the hook and the goal check bind a pass to
            report["change"], report["owner"] = change.name, project_branch(change, cfg)
        if scope == "milestone":
            report["milestone"] = number
        report["metrics"] = metrics(change, report, retries, started_run)
        text = json.dumps(report, indent=2) + "\n"
        (out_dir / "report.json").write_text(text, encoding="utf-8")
        # report.json holds the last scope run only: a milestone also keeps its own receipt, which
        # `sdlc_status.py goal` reads, so a deleted merged branch does not undo a finished milestone
        if scope == "milestone" and number:
            (out_dir / f"milestone-{number}.json").write_text(text, encoding="utf-8")
        rows = "\n".join(
            f"| {c['name']} | {c['status']} | {c['seconds']} |" for c in report["checks"]
        )
        failed = next((c for c in report["checks"] if c["status"] != "pass"), None)
        detail = f"\n\n## {failed['name']}\n\n```\n{failed['tail']}\n```\n" if failed else ""
        stats = "\n".join(f"- {k.replace('_', ' ')}: {v}" for k, v in report["metrics"].items())
        (out_dir / "report.md").write_text(
            f"# verify {scope} {change.name}\n\n| check | status | s |\n|---|---|---|\n{rows}\n"
            f"{detail}\n## Metrics\n\n{stats}\n\n`{line}`\n",
            encoding="utf-8",
        )
        if code == 0:
            (out_dir / "state.json").unlink(missing_ok=True)
        return end(line, code)

    declared = False  # an approval from before 3.18.0 keeps the order its checks were written in
    now: dict[str, str] = {}  # a project has no lock: its checks are the milestones' locked ones
    if scope == "project":
        branch = f"{(cfg.get('projects') or {}).get('branchPrefix', 'project/')}{change.name}"
        if sh("git", "rev-parse", "--abbrev-ref", "HEAD") != branch:
            print(f"check out {branch} (the project head) and run the gate there.")
            return finish("VERIFY BLOCKED reason=env", 3)
    else:
        lock_path = spec.state_path(change, "lock.json")
        if not lock_path.exists():
            print(f"{change.name}/lock.json is missing: run `verify_gate.py approve {change.name}`")
            print("at the plan gate, when the engineer approves.")
            return finish("VERIFY BLOCKED reason=not-approved", 3)
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        locked = lock["criteria"]
        declared = lock.get("order") != "cost"
        old_plan = lock.get("format", 0) < LOCK_FORMAT or ("plan.milestones" not in locked and not spec.applies(change))
        now = criteria_hash(change, cfg.get("checks", {}))
        for key in ("plan.milestones", "decisions.routing"):
            if key not in locked:
                now.pop(key, None)  # an older lock never hashed it: reported below, not a move
        if old_plan and scope == "milestone":
            gap = (
                f"lock.json predates lock format {LOCK_FORMAT}: every approved fact is expected, validation "
                "rows, plan.milestones and decisions.routing are not enforced; the engineer approves "
                "again to lock them"
            )
            print(f"upgrade gap: {gap}")
            report.setdefault("upgrade_gaps", []).append(gap)
        moved = sorted(k for k in set(locked) | set(now) if locked.get(k) != now.get(k))
        if moved:
            print(
                f"changed since approval: {', '.join(moved)}. The engineer decides; never re-lock."
            )
            report["moved"] = moved
            return finish("VERIFY BLOCKED reason=protected-path", 3)

    dirty = [
        line
        for line in sh("git", "status", "--porcelain").splitlines()
        if f"{change.name}/verify/" not in line
    ]
    if dirty:
        print("uncommitted changes: a PASS must name a commit. Commit, then run again.")
        print("\n".join(dirty[:TAIL]))
        return finish(f"VERIFY FAIL {scope} {change.name} check=uncommitted", 1)

    if scope in ("milestone", "project"):
        tips = [(f"origin/{name}", tip) for name, tip in parent_tips(change, cfg)]
        local = project_branch(change, cfg) if merges_locally(cfg) else ""
        if local and (tip := sh("git", "rev-parse", "--verify", "--quiet", f"{local}^{{commit}}")):
            tips.append((local, tip))
        default = cfg.get("defaultBranch") or "main"
        if sh("git", "remote", "get-url", "origin") and not any(n == f"origin/{default}" for n, _ in tips):
            print(f"origin/{default} cannot be resolved (offline, or the fetch failed): the gate cannot tell whether")
            print(f"this {scope} contains its parent. Fix the connection, then run `git fetch origin {default}` and the gate again.")
            return finish("VERIFY BLOCKED reason=env", 3)
        behind = [
            name
            for name, tip in tips
            if subprocess.run(
                ["git", "merge-base", "--is-ancestor", tip, "HEAD"], capture_output=True
            ).returncode
        ]
        if behind:
            print(f"{', '.join(behind)} has commits this {scope} lacks.")
            print("Merge in locally, then run the gate again (a commit here, never a PR):")
            print("  git fetch origin && " + " && ".join(f"git merge {b}" for b in behind))
            return finish(f"VERIFY FAIL {scope} {change.name} check=parent-sync", 1)

    if scope == "milestone" and spec.applies(change):  # the living spec: rules, tags and the diff
        if gap := parent_gap(repo, parent_ref(change, cfg, repo)):
            print("\n".join(gap))
            return finish("VERIFY BLOCKED reason=env", 3)
        if drift := spec.check(repo, parent_ref(change, cfg, repo)):
            print("\n".join(drift[:TAIL]))
            return finish(f"VERIFY FAIL {scope} {change.name} check=spec", 1)
    if scope == "milestone" and (blocker := milestone_blockers(change, number)):
        print("\n".join(blocker[1][:TAIL]))
        return finish(f"VERIFY BLOCKED reason={blocker[0]}", 3)
    if scope == "milestone" and legacy_marks() and has_bundle_inputs(change):
        print("scripts/marks.py is older than this gate (it has no `bundles`): it cannot inventory")
        print("this milestone's design bundles, and an empty inventory would pass an unrendered one.")
        print("If sdlc.json `keep` lists scripts/marks.py, remove it from `keep` first, then run")
        print("`adopt --upgrade --replace scripts/marks.py --apply` (or restore the kit's marks.py).")
        return finish("VERIFY BLOCKED reason=env", 3)

    suite = "milestone" if scope == "project" else scope
    checks = cfg.get("checks", {}).get(suite, [])
    if suite == "milestone" and (gap := full_e2e_gap(checks, repo)):
        if current_format(change) and scope == "milestone":
            # a suite added after approval: the locked checks cannot prove it, the engineer approves again
            print(gap)
            return finish("VERIFY BLOCKED reason=env", 3)
        # an approval made before this rule keeps working: report, never fail
        print(f"upgrade gap: {gap}")
        report.setdefault("upgrade_gaps", []).append(gap)
    if not checks:
        print(f"sdlc.json checks.{suite} is empty: nothing would prove this change.")
        return finish("VERIFY BLOCKED reason=env", 3)

    # Runtime evidence is additional to the locked checks; never weaken or re-lock them.
    # It depends on more than the tree (sessions, visual runs), so it is never cached.
    checks = [c if isinstance(c, dict) else {"run": c} for c in checks]
    for i, check in enumerate(checks, 1):  # default names count from sdlc.json, not from the sort
        check["name"] = check.get("name") or f"check-{i}"
    durations_path = out_dir / "durations.json"
    try:
        durations = json.loads(durations_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        durations = {}
    if not declared:
        checks = order_checks(checks, durations, change.name, cfg)
    # Evidence checks are offline and cheap: they run before the suites, so a missing screenshot,
    # checker or tag never costs a full E2E run (3.21.0).
    evidence: list[dict] = []
    if scope == "milestone" and has_owner_marks(change):
        evidence.append(
            {
                "name": "owner-marks",
                "cache": False,
                "run": shlex.join(
                    [
                        sys.executable,
                        str(Path(__file__).with_name("marks.py")),
                        "check",
                        change.name,
                    ]
                ),
            }
        )
    if scope == "milestone" and read_decisions(change) is None and current_format(change):
        evidence.append(
            refusal("decisions-json", "decisions.json is missing: it records the size, the visual source and the skips this gate reads")
        )
    elif (
        scope == "milestone"
        and not (visual_check and visual_runs)
        and visual_run_required(change, cfg, repo)
    ):
        evidence.append(
            refusal(
                "ux-visual-required",
                "this milestone has a UX decision and a visual source, but no --visual-check and "
                "--visual-run were given: run cct:ux-assessment-run and pass its run, or have the "
                "owner attest a skip (decisions.json skips.visual `skip -- <reason>` plus the "
                "dialog `Change <id>, finding visual-skip: ...` answered Skip visual evidence)",
            )
        )
    if visual_check and (
        Path(visual_check).name != "visual-check.py"
        or any(not Path(r).is_dir() for r in visual_runs or [])
    ):  # the shipped checker over a real run folder, not any command that exits 0
        evidence.append(
            refusal(
                "ux-visual-binding",
                "--visual-check must be the shipped visual-check.py and every --visual-run an existing run folder",
            )
        )
    for k, visual_run in enumerate(visual_runs or [], 1):  # not `number`: finish() reads the milestone number
        evidence.append(
            {
                "name": f"ux-visual-{k}",
                "cache": False,
                "run": shlex.join(
                    [
                        sys.executable,
                        str(visual_check),
                        visual_run,
                        "--repo",
                        str(repo),
                    ]
                ),
            }
        )
    checks = evidence + checks

    diff_base = parent_ref(change, cfg, repo) if scope == "milestone" else ""
    cache_path = out_dir / "cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    tree = sh("git", "rev-parse", "HEAD^{tree}")
    head = sh("git", "rev-parse", "HEAD")

    def failed(name: str, output: str) -> int:
        """The breaker and the attempt count, for the run's first failing check."""
        state_path = out_dir / "state.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        sig = signature(name, output)
        count = state.get("count", 0) + 1 if state.get("signature") == sig else 1
        attempts = {**state.get("attempts", {}), scope: state.get("attempts", {}).get(scope, 0) + 1}
        state_path.write_text(
            json.dumps({"signature": sig, "count": count, "attempts": attempts}) + "\n"
        )
        if count >= BREAKER:
            print(f"the same failure {count} runs in a row: the loop is not making progress.")
            return finish("VERIFY BLOCKED reason=no-progress", 3)
        if attempts[scope] >= ATTEMPTS:
            print(
                f"{attempts[scope]} failed {scope} runs of {change.name}: "
                "stop and ask the engineer."
            )
            return finish("VERIFY BLOCKED reason=attempts", 3)
        return finish(f"VERIFY FAIL {scope} {change.name} check={name}", 1)

    first_failure: tuple[str, str, str] | None = None  # --keep-going: the verdict names the first
    for check in checks:
        name = check["name"]
        cmd = expand(check["run"], change.name, cfg, diff_base)
        key = cache_key(tree, cmd, now) if check.get("cache", True) and tree else ""
        if key in cache:
            report["checks"].append(
                {"name": name, "run": cmd, "status": "pass", "exit": 0, "seconds": 0,
                 "tail": "cached", "cached": True}
            )  # fmt: skip
            print(f"ok (cached) {name}: {cmd}")
            continue
        started = time.monotonic()
        limit = int(check.get("timeout") or cfg.get("checkTimeout") or CHECK_TIMEOUT)
        proc = run_check(cmd, repo, limit)
        output = proc.stdout + proc.stderr
        tail = "\n".join(output.strip().splitlines()[-TAIL:])
        status = "pass" if proc.returncode == 0 else "fail"
        report["checks"].append(
            {
                "name": name,
                "run": cmd,
                "status": status,
                "exit": proc.returncode,
                "seconds": round(time.monotonic() - started, 1),
                "tail": tail,
            }
        )
        print(f"{'ok  ' if status == 'pass' else 'FAIL'} {name}: {cmd}")
        if status == "pass":
            # staged: a check that ran while the tree moved proves nothing about the starting tree
            if key and sh("git", "rev-parse", "HEAD^{tree}") == tree and not [
                line for line in sh("git", "status", "--porcelain").splitlines() if f"{change.name}/verify/" not in line
            ]:
                cache[key] = name
                cache_path.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
            durations[cmd] = report["checks"][-1]["seconds"]
            durations_path.write_text(json.dumps(durations, indent=2) + "\n", encoding="utf-8")
            continue
        print(tail)
        blocked = re.search(r"VERIFY BLOCKED reason=([\w-]+)\s*\Z", output.strip())
        if blocked:
            reason = blocked.group(1) if blocked.group(1) in REASONS else "unknown-verdict"
            if keep_going:  # the rest still runs; the first verdict, blocked or failed, stands
                first_failure = first_failure or (name, output, reason)
                continue
            return finish(f"VERIFY BLOCKED reason={reason}", 3)
        if is_e2e(cmd):
            verdict = classify_e2e(cmd, repo)
            if verdict:
                print(f"--last-failed re-run: the failures {verdict}")
                report["checks"][-1]["rerun"] = verdict
                report["checks"][-1]["tail"] += f"\n--last-failed re-run: the failures {verdict}"
        if keep_going:
            first_failure = first_failure or (name, output, "")
            continue
        return failed(name, output)
    if first_failure:
        names = ", ".join(c["name"] for c in report["checks"] if c["status"] != "pass")
        print(f"failed: {names}")
        if first_failure[2]:
            return finish(f"VERIFY BLOCKED reason={first_failure[2]}", 3)
        return failed(*first_failure[:2])

    # A PASS names one frozen head: a merge or an edit during the checks means they tested
    # something other than the commit the line would name.
    still_dirty = [
        line
        for line in sh("git", "status", "--porcelain").splitlines()
        if f"{change.name}/verify/" not in line
    ]
    if sh("git", "rev-parse", "HEAD") != head or still_dirty:
        print(
            "HEAD or the tree changed while the checks ran: nothing may merge or edit during a gate."
        )
        return finish(f"VERIFY FAIL {scope} {change.name} check=moved", 1)
    return finish(f"VERIFY PASS {scope} {change.name} {head}", 0)


def checker_exists(cmd: str, repo: Path) -> bool:
    """The program a check runs exists. shortcut: reads only the first command of a `a && b`
    line, so a broken second command is not seen; split it into two checks to audit both."""
    cmd = re.sub(r"^(?:\s*\w+=\$\(\s*(?:\{\s*)?)+", "", cmd)  # `specs=$( { git diff ...`: a shell fragment
    try:
        words = shlex.split(cmd)
    except ValueError:
        return False
    while words and re.fullmatch(r"\w+=\S*", words[0]):  # leading VAR=value
        words.pop(0)
    if not words:
        return False
    if words[0] in ("python3", "python", "bash", "sh") and len(words) > 1:
        return (repo / words[1]).exists() or words[1].startswith("-")
    return (repo / words[0]).exists() if "/" in words[0] else shutil.which(words[0]) is not None


def ci_jobs(repo: Path) -> list[dict]:
    """Jobs of .github/workflows/*.yml as {key, name, needs, body}. shortcut: a line scan for the
    two-space `jobs:` layout (no YAML parser, stdlib only); an anchored or flow-style file shows
    up as no jobs, so the check reads `local`, never a false `yes`."""
    jobs: list[dict] = []
    for path in sorted((repo / ".github" / "workflows").glob("*.y*ml")):
        in_jobs = in_needs = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"^jobs:\s*$", line):
                in_jobs = True
            elif in_jobs and (m := re.match(r"^  ([\w-]+):\s*$", line)):
                jobs.append({"key": m[1], "name": m[1], "needs": [], "body": "", "file": path.name})
            elif in_jobs and line and not line.startswith(" "):
                in_jobs = False
            elif in_jobs and jobs:
                jobs[-1]["body"] += line + "\n"
                if m := re.match(r"^    name:\s*(.+?)\s*$", line):
                    jobs[-1]["name"] = m[1].strip("'\"")
                if m := re.match(r"^    needs:\s*(.*)$", line):
                    jobs[-1]["needs"] += re.findall(r"[\w-]+", m[1])
                    in_needs = not m[1]
                elif in_needs and (m := re.match(r"^\s+- ([\w-]+)\s*$", line)):
                    jobs[-1]["needs"].append(m[1])
                elif re.match(r"^    \S", line):
                    in_needs = False
    return jobs


def required_contexts(branch: str) -> set[str] | None:
    """Required status checks of the default branch via `gh api` (rulesets first, then classic
    branch protection); None when gh or the API cannot say."""
    for path in (
        f"repos/{{owner}}/{{repo}}/rules/branches/{branch}",
        f"repos/{{owner}}/{{repo}}/branches/{branch}/protection/required_status_checks",
    ):
        try:
            data = json.loads(sh("gh", "api", path))
        except ValueError:
            continue
        if isinstance(data, list):
            return {
                c["context"]
                for rule in data
                if rule.get("type") == "required_status_checks"
                for c in rule.get("parameters", {}).get("required_status_checks", [])
            }
        if isinstance(data, dict):
            return set(data.get("contexts", [])) | {c["context"] for c in data.get("checks", [])}
    return None


def required_job_keys(jobs: list[dict], contexts: set[str]) -> set[str]:
    """Jobs whose name is a required context, plus everything they `needs`, transitively."""
    wanted = {c.rsplit(" / ", 1)[-1] for c in contexts}
    keys = {j["key"] for j in jobs if {j["key"], j["name"]} & wanted}
    while extra := {n for j in jobs if j["key"] in keys for n in j["needs"]} - keys:
        keys |= extra
    return keys


def last_runs(repo: Path, cfg: dict) -> dict[str, tuple[float, str, str]]:
    """run command -> (mtime, status, sha) from the newest verify/report.json that ran it."""
    found: dict[str, tuple[float, str, str]] = {}
    for path in (repo / cfg.get("changesDir", "changes")).rglob("verify/report.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for c in data.get("checks", []):
            if path.stat().st_mtime > found.get(c["run"], (0.0, "", ""))[0]:
                found[c["run"]] = (path.stat().st_mtime, c["status"], str(data.get("sha", ""))[:7])
    return found


def audit(cfg: dict, repo: Path, evidence: bool = True) -> int:
    """Read-only: installed, configured, executed and passed are four separate answers."""
    problems, unknown = [], 0
    jobs = ci_jobs(repo)
    branch = cfg.get("defaultBranch") or "main"
    contexts = required_contexts(branch)
    needed = required_job_keys(jobs, contexts) if contexts is not None else set()
    runs = last_runs(repo, cfg)
    print(
        f"default branch {branch}: required statuses "
        + (
            ", ".join(sorted(contexts)) or "none"
            if contexts is not None
            else "unknown (gh api failed)"
        )
    )
    for scope, checks in (cfg.get("checks") or {}).items():
        for i, check in enumerate(checks, 1):
            check = check if isinstance(check, dict) else {"run": check}
            cmd, name = check["run"], check.get("name") or f"check-{i}"
            prefix = cmd.split("{id}")[0].split("{base}")[0].strip()  # receipts hold the expanded line
            mine = [j for j in jobs if prefix and prefix in j["body"]]
            when = next((v for k, v in sorted(runs.items()) if k.startswith(prefix)), None)
            if not mine:
                required = "local"
            elif contexts is None:
                required = "unknown"
            else:
                required = "yes" if any(j["key"] in needed for j in mine) else "no"
            unknown += required == "unknown"
            invoked = ", ".join([f"gate {scope}"] + [f"ci {j['file']}:{j['key']}" for j in mine])
            ran = (
                "never" if not when else
                f"{when[1]} @{when[2]} {dt.datetime.fromtimestamp(when[0]):%Y-%m-%d}"
            )  # fmt: skip
            installed = checker_exists(cmd, repo)
            print(
                f"check {scope}/{name}: installed={'yes' if installed else 'NO'} "
                f"invoked by [{invoked}] required={required} last run: {ran}"
            )
            if not installed:
                problems.append(f"{scope}/{name}: the checker `{cmd.split()[0]}` does not exist")
            if evidence and not when:
                problems.append(f"{scope}/{name}: never ran (no verify/report.json has it)")
            if required == "no":
                problems.append(f"{scope}/{name}: a CI job runs it but it is not a required status")
    settings = repo / ".claude" / "settings.json"
    registered: dict[str, str] = {}
    if settings.exists():
        for event, groups in (
            json.loads(settings.read_text(encoding="utf-8")).get("hooks", {}).items()
        ):
            for g in groups:
                for h in g.get("hooks", []):
                    if m := re.search(r"\.claude/hooks/([\w.-]+\.sh)", h.get("command", "")):
                        registered[m[1]] = f"{event} {g.get('matcher', '*')}"
    on_disk = {
        p.name: p for p in (repo / ".claude" / "hooks").glob("*.sh") if p.name != "sdlc-config.sh"
    }  # sdlc-config.sh is sourced by the others, never registered
    for hook in sorted(set(registered) | set(on_disk)):
        path = on_disk.get(hook)
        installed = path is not None and os.access(path, os.X_OK)
        print(
            f"hook {hook}: installed={'yes' if installed else 'NO'} "
            f"invoked by [{registered.get(hook, 'NOT REGISTERED')}] "
            "last run: no record (a hook leaves no log)"
        )
        if not installed:
            problems.append(f"{hook}: registered but missing or not executable")
        if hook not in registered:
            problems.append(f"{hook}: installed but not registered in .claude/settings.json")
    print("\n".join(f"PROBLEM {p}" for p in problems[:TAIL]))
    verdict = "FAIL" if problems else "PASS"
    return end(f"AUDIT {verdict} problems={len(problems)} unknown={unknown}", 1 if problems else 0)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scope", choices=("approve", "lint", "feature", "milestone", "project", "audit")
    )
    parser.add_argument("id", nargs="?")
    parser.add_argument("--no-evidence", action="store_true", help="audit: skip the never-ran test")
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="run every check, not only up to the first failure",
    )
    parser.add_argument("--pr-body", metavar="FILE", help="lint: check this PR body ('-' = stdin)")
    parser.add_argument("--visual-check")
    parser.add_argument("--visual-run", action="append", default=[])
    args = parser.parse_args(argv[1:])
    if bool(args.visual_check) != bool(args.visual_run):
        parser.error("--visual-check and at least one --visual-run must be supplied together")
    if args.visual_run and args.scope not in ("feature", "milestone"):
        parser.error("visual checks apply only to feature and milestone gates")
    if args.scope != "audit" and not args.id:
        parser.error(f"{args.scope} needs a change id")
    repo = root()
    cfg = json.loads((repo / "sdlc.json").read_text(encoding="utf-8"))
    if args.scope == "audit":
        return audit(cfg, repo, not args.no_evidence)
    if args.scope == "project":
        change = project_record(args.id, repo)
        change.mkdir(parents=True, exist_ok=True)
        return run(args.scope, change, cfg, repo, keep_going=args.keep_going)
    changes = (repo / cfg.get("changesDir", "changes")).resolve()
    change = repo / cfg.get("changesDir", "changes") / args.id
    if not change.resolve().is_relative_to(changes) or change.resolve() == changes:
        print(f"the change id {args.id!r} does not name a folder inside {changes.name}/.")
        return end("VERIFY BLOCKED reason=env", 3)
    if not change.is_dir():
        print(f"no change folder {change.relative_to(repo)}")
        return end("VERIFY BLOCKED reason=env", 3)
    if args.scope == "approve":
        return approve(change, cfg)
    if args.scope == "lint":
        body = None
        if args.pr_body:
            body = (
                sys.stdin.read() if args.pr_body == "-" else Path(args.pr_body).read_text("utf-8")
            )
        return lint(change, body)
    return run(args.scope, change, cfg, repo, args.visual_check, args.visual_run, args.keep_going)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
