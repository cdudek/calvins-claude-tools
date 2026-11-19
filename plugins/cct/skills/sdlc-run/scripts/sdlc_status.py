"""Where a change stands: every milestone, the features of this one, and the stage.

    python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py map [<id>]
    python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py goal <id> [--milestone <n> | --feature <n> | --project]
    python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py ids [<id>]
    python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py readme [<id>]
    python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py record <id> project --sha <sha> [--accepted]

Runs from the plugin and is never copied into a repo: run it with the working directory inside the
adopted repo, which it finds from the cwd. It loads `verify_gate` from the plugin's own
`templates/scripts/`, not from the repo's `scripts/`. stdlib only.

Everything is read from the files; only `readme` writes, and only the change's README.md, only over a README it generated and only when the content changed. The stage (1-7): an archived change → 7,
lock.json → 5 (6 once every feature is merged), plan.md → 4, facts.md → 3, an approved intent → 2,
otherwise 1. Milestone position comes from the design doc's `## Milestones` list (decisions.json
`design`), features from the milestone's `milestone.md` Features table.

`goal` is the check a `/goal` condition names: the evaluator cannot read files or GitHub, so this
prints one line and the evaluator matches it. Exit 0 `GOAL <id> DONE pr=<n> state=<merged|armed>
gate=<sha>`, exit 3 `GOAL <id> BLOCKED reason=<code>` (the last gate said VERIFY BLOCKED), exit 1
`GOAL <id> OPEN <what is missing>`. DONE needs every milestone PR (branch `milestone/<slug>-<n>`,
n from plan.md `## Milestones`) merged or open with auto-merge armed, the last
`VERIFY PASS milestone <id> <sha>` in verify/report.json equal to the head sha of the last PR
(`gh`, never local HEAD: records written after a merge move HEAD), and no open record
(validation.md, findings.md; `verify_gate.milestone_blockers`). `--feature <n>` reads the plan's
`## Feature PRs` row n and a `feature` gate; `--milestone <n>` narrows to one milestone. A `gh`
that is missing or fails is `OPEN gh-unavailable`, never DONE. When the goal is not DONE a second
line `Blocking: <what>, because <why>; <who> runs `<step>`.` says the one thing in the way.

`record <id> project --sha <sha> [--accepted]` persists, for a project with no branch, the default-branch
commit that holds every milestone and the owner's acceptance (state/heads.json); `goal <id> --project`
is DONE only with both. The gates persist each milestone's head and base there, and a hotfix head.

`handoff <id> --cap turns|fix-rounds|retries [--what <words>] [--next <command>]` writes the one HANDOFF
record of a hit cap (state/handoff.json: what, why, the exact next command) and prints it; the retry
cap of the gate writes it itself. While the goal is still open it prints `GOAL <id> HANDOFF cap=<cap>`
(exit 4) and a `Blocking:` line with the next command. A passing gate or `handoff <id> --resume`
clears it.

`ids` prints every id the change defines with its one-line meaning and the file that decides it.
`readme` writes `<change>/README.md`, the reading map (`references/readability.md`).

With sdlc.json `milestones.merge: "local"` and a project branch, a milestone has no PR: it is DONE
when its `VERIFY PASS milestone` head is an ancestor of the local project/<slug> (line `GOAL <id>
DONE merged=project/<slug> gate=<sha>`). Each planned milestone counts by its own receipt
verify/milestone-<n>.json (a pass whose head is in the project branch; the branch need not exist),
or, without a receipt, by its milestone/<slug>-<n> branch being merged. `--project` reads the project's own record (`VERIFY PASS
project <slug>`, written by `verify_gate.py project`) and the PR project/<slug> into the default
branch, merged or armed, as above.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from change_docs import MARKER, ids, readme

# verify_gate and pass_proof live in the plugin's templates (what adopt copies into repos).
for _sub in ("scripts", "hooks"):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates" / _sub))

import spec  # noqa: E402
from pass_proof import bound, change_paths, milestone_of, proves  # noqa: E402

STAGES = ("Intent", "UX plan", "Facts", "Tech plan", "Build", "Milestone", "Outcome")


def git(root: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def repo_root(start: Path) -> Path | None:
    top = git(start, "rev-parse", "--show-toplevel")
    return Path(top) if top and (Path(top) / "sdlc.json").exists() else None


def config(root: Path) -> dict:
    return json.loads((root / "sdlc.json").read_text(encoding="utf-8"))


def slug_of(name: str) -> str:
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)
    return re.sub(r"^[A-Z][A-Z0-9]+-\d+-", "", name)


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def find_change(root: Path, cfg: dict, change_id: str | None) -> Path | None:
    base = root / cfg.get("changesDir", "changes")
    if change_id:
        # a change is a direct child of changesDir, or archive/<year>/<year-month>/<id> once
        # Stage 7 moved it: no "..", no absolute path, never the archive folder itself
        if Path(change_id).name != change_id or change_id in ("..", "archive"):
            return None
        found = change_paths(base, change_id)
        return next((d for d in found if base.resolve() in d.resolve().parents), None)
    if not base.is_dir():
        return None
    folders = [d for d in base.iterdir() if d.is_dir() and d.name != "archive"]
    branch = git(root, "symbolic-ref", "--short", "-q", "HEAD")
    for d in sorted(folders):
        if branch and slug_of(d.name) in branch:
            return d
    return folders[0] if len(folders) == 1 else None


def frontmatter(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    m = re.search(rf"^{key}:\s*(.+)$", path.read_text(encoding="utf-8"), re.M)
    return m.group(1).strip() if m else ""


def section(text: str, heading: str) -> list[str]:
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return [line for line in m.group(1).splitlines() if line.strip()] if m else []


def initiative(change: Path, root: Path, decisions: dict) -> tuple[str, int, int]:
    """(name, milestone position, milestone total); 0/0 without a design doc listing it."""
    named = decisions.get("milestone", {}).get("initiative", "")
    design = root / str(decisions.get("design", ""))
    pos = total = 0
    if decisions.get("design") not in (None, "", "none") and design.is_file():
        text = design.read_text(encoding="utf-8")
        title = re.search(r"^# (?:Design:\s*)?(.+)$", text, re.M)
        named = named or (title.group(1).strip() if title else "")
        items = [li for li in section(text, "Milestones") if re.match(r"\s*(?:[-*]|\d+\.)\s", li)]
        total = len(items)
        pos = next((i for i, li in enumerate(items, 1) if slug_of(change.name) in li), 0)
    if not named:
        plan = change / "plan.md"
        title = (
            re.search(r"^# Plan:\s*(.+)$", plan.read_text(encoding="utf-8"), re.M)
            if plan.exists()
            else None
        )
        named = title.group(1).strip() if title else slug_of(change.name).replace("-", " ")
    return named, pos, total


def features(change: Path, root: Path, cfg: dict, decisions: dict) -> list[dict]:
    """Rows of the milestone's Features table: [{id, feature, state}]. In layout 4 the tasks of
    tasks.md are the rows."""
    if spec.applies(change):
        return [{"id": t, "feature": m, "state": st} for t, st, m in spec.task_states(change)]
    milestone = change / "milestone.md"
    slug = decisions.get("milestone", {}).get("slug", "")
    if not milestone.exists() and slug:
        base = root / cfg.get("changesDir", "changes")
        milestone = next(
            (m for m in base.glob("*/milestone.md") if frontmatter(m, "milestone") == slug),
            milestone,
        )
    if not milestone.exists():
        return []
    rows = []
    for line in section(milestone.read_text(encoding="utf-8"), "Features"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[0] not in ("#", "") and not set(cells[0]) <= {"-", ":"}:
            rows.append({"id": f"F{cells[0]}", "feature": cells[2], "state": cells[4]})
    return rows


def stage_of(change: Path, rows: list[dict]) -> int:
    if "archive" in change.parts:
        return 7
    if spec.state_path(change, "lock.json").exists():
        return 6 if rows and all(r["state"].startswith(("merged", "done")) for r in rows) else 5
    if (change / "plan.md").exists() or (change / "tasks.md").exists():
        return 4
    if frontmatter(change / "spec.md", "status") == "approved":
        return 3
    if (change / "facts.md").exists():
        return 3
    return 2 if frontmatter(change / "intent.md", "status") == "approved" else 1


def state(change: Path, root: Path, cfg: dict) -> dict:
    decisions = read_json(spec.state_path(change, "decisions.json"))
    name, pos, total = initiative(change, root, decisions)
    rows = features(change, root, cfg, decisions)
    return {
        "initiative": name,
        "pos": pos,
        "total": total,
        "stage": stage_of(change, rows),
        "features": rows,
        "merged": sum(1 for r in rows if r["state"].startswith(("merged", "done"))),
    }


def milestone_map(s: dict) -> str:
    head = s["initiative"] + (f"  M{s['pos']} of {s['total']}" if s["pos"] else "")
    marks = {"merged": "✓", "done": "✓", "building": "◐", "blocked": "✗"}
    bar = "".join(
        next((v for k, v in marks.items() if r["state"].startswith(k)), "○") for r in s["features"]
    )
    lines = [head, f"  this milestone  {s['merged']} of {len(s['features'])} merged  {bar}"]
    lines += [f"    {r['id']:<4} {r['feature']:<32} {r['state']}" for r in s["features"]]
    lines.append(f"  stage  {s['stage']}/7 {STAGES[s['stage'] - 1]}")
    return "\n".join(lines)


def side_notes(root: Path) -> list[str]:
    """What the map adds only when there is something to say: a stop whose verification failed (the
    stop hook lets a session end on an unchanged failing tree, which is not a pass) and who holds or
    waits for a heavy slot (the plugin's heavy.py run in the repo, so a waiting helper is visible)."""
    lines = []
    gitdir = git(root, "rev-parse", "--absolute-git-dir")
    try:
        stop = json.loads((Path(gitdir) / "sdlc-stop-status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        stop = {}
    if isinstance(stop, dict) and stop.get("status") == "failed":
        lines.append(f"  last stop  verify FAILED (`{stop.get('verify', '')}`): a stop is not a pass; the uncommitted source was never verified")
    heavy = Path(__file__).resolve().parents[1] / "templates" / "scripts" / "heavy.py"  # the plugin's own copy: status never runs repo code
    if heavy.is_file():
        try:
            out = subprocess.run([sys.executable, str(heavy), "status"], capture_output=True, text=True, timeout=10, cwd=root).stdout
        except (OSError, subprocess.TimeoutExpired):
            out = ""
        queue = [line for line in out.splitlines() if line.strip() and "idle" not in line]
        lines += ["  heavy queue"] + [f"    {line}" for line in queue] if queue else []
    return lines


def gh_json(root: Path, *args: str) -> list | None:
    """Parsed `gh <args>` output; None when gh is missing, fails or prints something else."""
    try:
        out = subprocess.run(["gh", *args], cwd=root, capture_output=True, text=True, timeout=60)
        found = json.loads(out.stdout) if out.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    return found if isinstance(found, list) else None


def contains(root: Path, sha: str, into: str) -> bool:
    """`sha` is `into` or an ancestor of it."""
    return bool(sha and into) and (
        subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", sha, into], capture_output=True
        ).returncode
        == 0
    )


def same_head(root: Path, cfg: dict, gated: str, head: str) -> bool:
    """What the gate passed still holds at `head` (pass_proof.py, the rule pr-gate.sh applies)."""
    return proves(root, str(cfg.get("changesDir", "changes")), gated, head)


def planned(change: Path) -> int:
    """How many milestones plan.md lists (the distinct milestones of tasks.md in layout 4)."""
    if spec.applies(change):
        return len({m for _, _, m in spec.task_states(change) if m})
    plan = (change / "plan.md").read_text(encoding="utf-8") if (change / "plan.md").exists() else ""
    return sum(1 for line in section(plan, "Milestones") if re.match(r"\|\s*M\d+\b", line))


def recorded(change: Path) -> dict:
    """state/heads.json (the old place second): the head and base each gate passed, persisted so a
    resumed goal or a new session reads what the gate saw, not a name derived from the plan."""
    data = read_json(spec.state_path(change, "heads.json"))
    return data if isinstance(data, dict) else {}


def milestone_heads(change: Path, decisions: dict, n: int | None, cfg: dict | None = None) -> list[tuple[int, str]]:
    """(number, head branch) of the milestone PRs that end the goal: the head the gate recorded for
    it, else <prefix><slug>-<n> (feature-PR delivery: the one branch <prefix><slug>)."""
    slug = decisions.get("milestone", {}).get("slug") or slug_of(change.name)
    prefix = ((cfg or {}).get("milestones") or {}).get("branchPrefix", "milestone/")
    kept = recorded(change).get("milestones")
    kept = kept if isinstance(kept, dict) else {}
    feature_prs = (cfg or {}).get("delivery") == "feature-prs"
    rows = [n] if n else [1] if feature_prs else range(1, max(planned(change), 1) + 1)
    return [
        (i, str((kept.get(str(i)) or {}).get("head") or (f"{prefix}{slug}" if feature_prs else f"{prefix}{slug}-{i}")))
        for i in rows
    ]


def branches(
    change: Path, decisions: dict, scope: str, n: int | None, cfg: dict | None = None
) -> list[str]:
    """Head branches whose PRs end the goal: the recorded or derived milestone heads, or the Feature
    PRs row's branch (a hotfix with no row: the head its feature gate recorded)."""
    plan = (change / "plan.md").read_text(encoding="utf-8") if (change / "plan.md").exists() else ""
    if scope == "feature":
        for line in section(plan, "Feature PRs"):
            cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4 and cells[0] == str(n):
                return [cells[3]]
        hotfix = recorded(change).get("hotfix")
        return [str(hotfix["head"])] if n is None and isinstance(hotfix, dict) and hotfix.get("head") else []
    return [head for _, head in milestone_heads(change, decisions, n, cfg)]


def route(change: Path, cfg: dict, scope: str, n: int | None) -> str:
    """The scope a goal reads: a hotfix change (decisions milestone.kind, sdlc.json hotfix on) that
    has a recorded hotfix head is a feature gate and a hotfix PR, not milestone 1."""
    if scope == "milestone" and n is None and cfg.get("hotfix", True):
        kind = read_json(spec.state_path(change, "decisions.json")).get("milestone", {}).get("kind")
        hotfix = recorded(change).get("hotfix")
        if kind == "hotfix" and isinstance(hotfix, dict) and hotfix.get("head"):
            return "feature"
    return scope


def parent_of(change: Path, cfg: dict, scope: str, head: str = "") -> str:
    """The branch the scope's PR must target: a feature goes into its milestone branch (a hotfix
    into the default branch), a milestone into its project branch or else the default branch, a
    project into the default branch."""
    default = cfg.get("defaultBranch") or "main"
    if scope == "project":
        return default
    if scope == "milestone":
        from verify_gate import project_branch

        for row in (recorded(change).get("milestones") or {}).values():  # the base its gate saw
            if isinstance(row, dict) and row.get("head") == head and row.get("base"):
                return str(row["base"])
        return project_branch(change, cfg) or default
    if head.startswith("hotfix/") and cfg.get("hotfix", True):
        return default
    slug = read_json(spec.state_path(change, "decisions.json")).get("milestone", {}).get("slug") or slug_of(change.name)
    return f"{(cfg.get('milestones') or {}).get('branchPrefix', 'milestone/')}{slug}"


def waiting_on(root: Path, cfg: dict, pr: dict, accepted: bool = False) -> str:
    """Why an open PR is not armed: the reader decides an `ask` PR while askGatesMerge is on (until
    the owner accepts: the tier workflow never arms an ask PR, so after the acceptance the agent
    does), the tier workflow arms the others into the default branch, and only a repo without that
    workflow leaves arming to the agent."""
    ask = "ask" in {str(x.get("name")).lower() for x in pr.get("labels") or []}
    if ask and cfg.get("askGatesMerge", True):
        return "not-merged-or-armed" if accepted else "awaits-owner"
    workflow = (root / ".github" / "workflows" / "ship-show-ask.yml").exists()
    if workflow and pr.get("baseRefName") == (cfg.get("defaultBranch") or "main"):
        return "awaits-workflow"
    return "not-merged-or-armed"


FAILED_CHECKS = {"FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE", "ERROR"}


def pr_flag(root: Path, cfg: dict, pr: dict, answer: str = "") -> tuple[str, str]:
    """(phase, flag) of one PR. Phases: merged, awaiting-ci (armed, nothing left for the agent),
    published (open, not armed), awaiting-owner, held, failed (red CI) and closed. The flag is the
    word after `pr-<n>-` in the goal line, empty for the two phases that are done. `answer` is the
    owner's latest answer to `Change <id>, finding PR<n>: ...` (accepted | hold | ""), read only for
    an ask PR."""
    names = {str(x.get("name", "")).lower() for x in pr.get("labels") or []}
    merged = pr.get("state") == "MERGED" or bool(pr.get("mergedAt"))
    armed = pr.get("state") == "OPEN" and bool(pr.get("autoMergeRequest"))
    gating = "ask" in names and cfg.get("askGatesMerge", True)
    accepted = answer == "accepted"
    if answer == "hold" or "hold" in names:
        return "held", "held"
    if pr.get("state") == "CLOSED":
        return "closed", "closed"
    if gating and not accepted:  # a merge that outran the owner is still unsigned
        return "awaiting-owner", "awaits-owner"
    if merged:
        return "merged", ""
    if "awaiting-owner" in names:
        return ("published", "label-awaiting-owner") if accepted else ("awaiting-owner", "awaits-owner")
    if any(str(c.get("conclusion", "")).upper() in FAILED_CHECKS for c in pr.get("statusCheckRollup") or [] if isinstance(c, dict)):
        return "failed", "ci-failed"
    if armed:
        return "awaiting-ci", ""
    tiered = (
        pr.get("baseRefName") == (cfg.get("defaultBranch") or "main")
        and cfg.get("tiers") is not False
        and (root / ".github" / "workflows" / "ship-show-ask.yml").exists()  # it sets the label
    )
    if tiered and not names & {"ask", "show", "ship"}:
        return "published", "awaits-tier"
    return "published", waiting_on(root, cfg, pr, accepted)


def integrated(root: Path, sha: str, default: str) -> bool:
    """`sha` is in the default branch, local or as origin has it."""
    return any(contains(root, sha, ref) for ref in (default, f"origin/{default}"))


def owner_accepted(root: Path, change: Path, slug: str) -> bool:
    """The owner answered `Change <id>, finding PROJECT-<slug>: ...` with Accept milestone in a dialog (the
    reader of marks.py, as for an ask PR); a flag the agent writes is never the owner."""
    from marks import owner_decisions

    return owner_decisions(root, change.name).get(f"PROJECT-{slug}", ("",))[0] == "accepted"


def branchless_project(root: Path, change: Path, cfg: dict) -> tuple[int, str] | None:
    """A project with no branch is done by the record `record <id> project` wrote: the default-branch
    commit that holds every milestone, and the owner's acceptance. None when nothing was recorded."""
    rec = recorded(change).get("project")
    if not isinstance(rec, dict) or not rec.get("sha"):
        return None
    name, sha = f"GOAL {change.name}", str(rec["sha"])
    if not integrated(root, sha, cfg.get("defaultBranch") or "main"):
        return 1, f"{name} OPEN project-not-integrated"
    slug = (read_json(spec.state_path(change, "decisions.json")).get("project") or {}).get("slug", "")
    if not (rec.get("accepted") and owner_accepted(root, change, slug)):
        return 1, f"{name} OPEN project-not-accepted"
    return 0, f"{name} DONE project={slug} integrated={sha}"


def record_project(root: Path, change: Path, cfg: dict, sha: str, accepted: bool) -> tuple[int, str]:
    """Persist the integrated default-branch commit of a branchless project and the owner's acceptance."""
    from verify_gate import record_head

    default = cfg.get("defaultBranch") or "main"
    if not integrated(root, sha, default):
        return 1, f"{sha or 'no sha'} is not in {default}: merge every milestone into {default} first"
    slug = (read_json(spec.state_path(change, "decisions.json")).get("project") or {}).get("slug", "")
    if accepted and not owner_accepted(root, change, slug):
        return 1, f"the owner has not accepted PROJECT-{slug}: ask `Change {change.name}, finding PROJECT-{slug}: ...` (Accept milestone | Hold) first"
    record_head(change, "project", None, {"sha": sha, "accepted": accepted})
    return 0, f"recorded project sha={sha} accepted={'yes' if accepted else 'no'}"


def handoff_of(change: Path) -> dict:
    """state/handoff.json: the record a hit cap left (verify_gate.write_handoff)."""
    data = read_json(spec.state_path(change, "handoff.json"))
    return data if isinstance(data, dict) and data.get("cap") else {}


def handoff_sentence(change: Path) -> str:
    rec = handoff_of(change)
    return (
        f"Blocking: {rec.get('what', 'a cap was reached')}, because {rec.get('why', 'the cap was reached')}; "
        f"you run `{rec.get('next', '')}`."
    )


def goal(
    root: Path, change: Path, scope: str = "milestone", n: int | None = None, gh=gh_json
) -> tuple[int, str]:
    """`goal_state` plus the handoff: a goal still OPEN when a cap stopped the run reads HANDOFF."""
    code, line = goal_state(root, change, scope, n, gh)
    cap = handoff_of(change).get("cap")
    return (4, f"GOAL {change.name} HANDOFF cap={cap}") if code == 1 and cap else (code, line)


def goal_state(
    root: Path, change: Path, scope: str = "milestone", n: int | None = None, gh=gh_json
) -> tuple[int, str]:
    """(exit code, the one line) for the change's goal; `gh(root, *args)` is injectable. The gate's
    report.json in the checkout says whether the scope passed; a local milestone is also done by
    its own receipt (verify/milestone-<n>.json) or its merged branch."""
    from verify_gate import merges_locally, milestone_blockers, project_branch, project_record

    name = f"GOAL {change.name}"
    cfg = config(root) if (root / "sdlc.json").exists() else {}
    scope = route(change, cfg, scope, n)
    project = project_branch(change, cfg)
    if scope == "project" and not project and (done := branchless_project(root, change, cfg)):
        return done
    subject = change.name
    folder = change
    if scope == "project":
        subject = (read_json(spec.state_path(change, "decisions.json")).get("project") or {}).get("slug", "")
        folder = project_record(subject, root) if project else change
    report = read_json(folder / "verify" / "report.json")
    if scope == "milestone" and n:  # report.json is the last run only: milestone n keeps its own receipt
        receipt = read_json(folder / "verify" / f"milestone-{n}.json")
        if receipt and not bound(report, scope, subject, n, project):
            report = receipt
    result = str(report.get("result", "")) if report.get("scope") == scope else ""
    blocked = re.fullmatch(r"VERIFY BLOCKED reason=([\w-]+)", result)
    if blocked:
        return 3, f"{name} BLOCKED reason={blocked.group(1)}"
    passed = re.fullmatch(rf"VERIFY PASS {scope} {re.escape(subject)} (\w+)", result)
    # a pass counts for the milestone it was gated as (the goal's last one without --milestone) and
    # the project the change belongs to: M1's pass never finishes M2, nor another project's
    number = (n or (1 if cfg.get("delivery") == "feature-prs" else max(planned(change), 1))) if scope == "milestone" else None
    if passed and scope != "project" and not bound(report, scope, subject, number, project):
        passed = None
    if scope == "milestone" and n and planned(change) and n > planned(change):
        return 1, f"{name} OPEN no-such-milestone:{n}"  # an unlisted row: no branch or PR is invented for it
    missing = [] if passed else [f"{scope}-gate-pass"]
    local = scope == "milestone" and project and merges_locally(cfg)
    if local:  # no PR: the gated head must be merged into the local project branch
        names = []
        into = git(root, "rev-parse", "--verify", "--quiet", f"{project}^{{commit}}")
        if passed and not contains(root, passed.group(1), into):
            missing.append(f"gate-not-merged-into-{project}")
        # report.json holds the last gate run only: each planned milestone is done by its own
        # receipt (verify/milestone-<n>.json), whose gated head is in the project branch; the
        # branch merge is the fallback for a change gated before receipts existed
        merged_in: list[str] | None = None  # the project history, listed once per poll

        def brought_in(gated: str) -> str:
            """The second parent of the oldest first-parent merge on the project branch that holds `gated`."""
            nonlocal merged_in
            if merged_in is None:
                log = git(root, "log", "--first-parent", "--merges", "--reverse", "--format=%P", into)
                merged_in = [p[1] for p in (line.split() for line in log.splitlines()) if len(p) > 1]
            return next((p for p in merged_in if contains(root, gated, p)), "")

        if planned(change):
            for i, b in milestone_heads(change, read_json(spec.state_path(change, "decisions.json")), n, cfg):
                receipt = read_json(change / "verify" / f"milestone-{i}.json")
                i = str(i)
                tip = git(root, "rev-parse", "--verify", "--quiet", f"{b}^{{commit}}")
                if receipt:
                    # a receipt counts only for its own milestone and change, never a copy
                    ok = bound(receipt, "milestone", change.name, int(i), project)
                    if not (ok and contains(root, str(receipt.get("sha", "")), into)):
                        missing.append(f"receipt-not-merged:{i}")
                        continue
                    if not tip:  # the branch is gone: the merge that brought it in stands in for it
                        sha = str(receipt.get("sha", ""))
                        second = brought_in(sha)
                        if not second:  # a fast-forward leaves no merge commit to prove against
                            missing.append(f"receipt-not-merged:{i}")
                        elif not same_head(root, cfg, sha, second):
                            missing.append(f"gate-sha-not-tip:{b}")  # the merge carried more than records
                        continue
                if not contains(root, tip, into):  # no receipt, or the branch is still there
                    missing.append(f"merge-missing:{b}")
                elif receipt and not same_head(root, cfg, str(receipt.get("sha", "")), tip):
                    missing.append(f"gate-sha-not-tip:{b}")  # code, criteria or evidence moved after the gate
    elif scope == "project":
        names = [project] if project else []
        if not names:
            missing.append("no-project-branch")
    else:
        names = branches(change, read_json(spec.state_path(change, "decisions.json")), scope, n, cfg)
    if not names and not local and scope != "project":
        missing.append(f"no-branch-for-{scope}-{n}")
    prs = []
    for branch in names:
        found = gh(
            root,
            *("pr", "list", "--head", branch, "--state", "all", "--limit", "1"),
            *("--json", "number,headRefOid,state,autoMergeRequest,mergedAt,baseRefName,labels,statusCheckRollup"),
        )
        if found is None:
            return 1, f"{name} OPEN gh-unavailable"
        if not found:
            missing.append(f"no-pr:{branch}")
            continue
        pr = found[0]
        merged = pr.get("state") == "MERGED" or bool(pr.get("mergedAt"))
        answer = ""
        if pr.get("state") == "OPEN":
            # the owner's answer to `Change <id>, finding PR<n>: ...` (Accept milestone | Hold), for
            # every open PR: a Hold blocks at any tier. Parsed once per process, from sessions newer
            # than the change (marks.answers)
            from marks import owner_decisions

            answer = owner_decisions(root, change.name).get(f"PR{pr['number']}", ("",))[0]
        _, flag = pr_flag(root, cfg, pr, answer)
        if pr.get("baseRefName") != parent_of(change, cfg, scope, branch):
            missing.append(f"pr-{pr['number']}-wrong-base")  # first: arming it would merge elsewhere
        if flag:
            missing.append(f"pr-{pr['number']}-{flag}")
        prs.append((pr, "merged" if merged else "armed"))
    if prs and passed and not same_head(root, cfg, passed.group(1), prs[-1][0].get("headRefOid", "")):
        missing.append(f"gate-sha-not-pr-{prs[-1][0]['number']}-head")
    if scope == "milestone":
        if blocker := milestone_blockers(change, number):  # the gate's own record rules, one definition
            missing.append(blocker[0])
    if missing:
        return 1, f"{name} OPEN " + ",".join(missing)
    if local:
        return 0, f"{name} DONE merged={project} gate={passed.group(1)}"
    pr, state = prs[-1]
    return 0, f"{name} DONE pr={pr['number']} state={state} gate={passed.group(1)}"


def goal_removed(root: Path, change_id: str, scope: str, n: int | None, gh=gh_json) -> tuple[int, str] | None:
    """The folder is gone: the owner's rule removes it after merge, so that is the normal end state.
    A merged PR from the change's milestone branch is the proof; None when there is none."""
    cfg = config(root) if (root / "sdlc.json").exists() else {}
    if scope != "milestone" or Path(change_id).name != change_id or change_id in ("", "..", "archive"):
        return None
    prefix, slug = (cfg.get("milestones") or {}).get("branchPrefix", "milestone/"), slug_of(change_id)
    found = gh(root, "pr", "list", "--state", "merged", "--limit", "200", "--json", "number,headRefName,state")
    if not found:  # gh failed or nothing merged: no proof, so the id is still unknown
        return None
    merged = [  # the one rule of the gate and the hook: <prefix><slug>-<n> is n, <prefix><slug> is 1
        p for p in found
        if (num := milestone_of(str(p.get("headRefName", "")), prefix, slug)) and (n is None or num == n)
    ]
    if not merged:
        return None
    return 0, f"GOAL {change_id} DONE pr={merged[-1]['number']} state=merged folder=removed"


# what is in the way, by the first missing item: (what, why, who acts, the exact step)
BLOCKS = {
    "gate-pass": (
        "the {scope} gate has not passed",
        "no VERIFY PASS is recorded for it",
        "the agent",
        "python3 scripts/verify_gate.py {scope} {id}",
    ),
    "gate-sha-not-pr-": (
        "the gate passed on a different commit than PR {n} holds",
        "the PR head moved after the gate ran",
        "the agent",
        "python3 scripts/verify_gate.py {scope} {id}",
    ),
    "no-pr:": (
        "there is no PR for {n}",
        "the branch was never pushed and opened",
        "the agent",
        "gh pr create --head {n} --base {base} --fill",
    ),
    "gh-unavailable": (
        "GitHub cannot be reached",
        "gh is missing, logged out or offline",
        "you",
        "gh auth status",
    ),
    "findings-open": (
        "review findings are still open",
        "findings.md has an unchecked item",
        "the agent",
        "fix each open item in findings.md, tick it, commit",
    ),
    "findings-blocked": (
        "a review finding is blocked",
        "findings.md has an item whose disposition says blocked",
        "you",
        "decide: a scope change with a new approval, or fix the named blocker",
    ),
    "validation-not-met": (
        "a fact has no proof",
        "validation.md has a row that is not met or partly met",
        "the agent",
        "build the missing proof, then update validation.md",
    ),
    "not-converged": (
        "the review has not converged",
        "findings.md has a Converge section without a Converged line",
        "the agent",
        "run the converge pass and add the Converged line",
    ),
    "project-gate-pass": (
        "the project gate has not passed",
        "no VERIFY PASS project is recorded for it",
        "the agent",
        "python3 scripts/verify_gate.py project {id}",
    ),
    "gate-not-merged-into-": (
        "the milestone gate head is not merged into its local project branch",
        "the milestone was never merged there, or moved after the gate",
        "the agent",
        "git switch <project branch> && git merge --no-ff <milestone branch>",
    ),
    "merge-missing:": (
        "the milestone branch {n} is not merged into its local project branch",
        "the milestone has no gate receipt, so its branch is checked, and it is not in the project branch",
        "the agent",
        "on {n}: python3 scripts/verify_gate.py milestone {id} (writes its receipt); then git switch <project branch> && git merge --no-ff {n}",
    ),
    "receipt-not-merged:": (
        "milestone {n} has no passing gate receipt merged into its local project branch",
        "its verify/milestone-{n}.json is missing, failed, or its head is not in the project branch",
        "the agent",
        "on branch milestone/<slug>-{n}: python3 scripts/verify_gate.py milestone {id}, then merge it",
    ),
    "gate-sha-not-tip:": (
        "the milestone branch {n} moved past its gate in more than records",
        "code, facts.md, done.json or evidence changed after its gate receipt",
        "the agent",
        "on {n}: python3 scripts/verify_gate.py milestone {id} (writes a new receipt)",
    ),
    "no-such-milestone:": (
        "the plan has no milestone {n}",
        "plan.md ## Milestones lists fewer rows",
        "the agent",
        "grep -n '^| M' changes/{id}/plan.md, then ask for a listed number",
    ),
    "no-branch-for-": (
        "the plan names no branch for {n}",
        "plan.md has no matching row",
        "you",
        "add the row to plan.md ## Feature PRs",
    ),
    "no-project-branch": (
        "the project has no branch and nothing records it integrated",
        "no default-branch commit that holds every milestone is recorded",
        "the agent",
        "python3 ${{CLAUDE_SKILL_DIR}}/scripts/sdlc_status.py record {id} project --sha <default-branch commit that holds every milestone>",
    ),
    "project-not-integrated": (
        "the recorded project commit is not in the default branch",
        "the commit was recorded before the milestones merged, or it left the default branch",
        "the agent",
        "merge every milestone into the default branch, then `python3 ${{CLAUDE_SKILL_DIR}}/scripts/sdlc_status.py record {id} project --sha <sha>`",
    ),
    "project-not-accepted": (
        "the owner has not accepted the project",
        "the integrated project is recorded without the owner's acceptance",
        "you",
        "ask `Change {id}, finding PROJECT-<slug>: ...` with Accept milestone and Hold, then `python3 ${{CLAUDE_SKILL_DIR}}/scripts/sdlc_status.py record {id} project --sha <sha> --accepted`",
    ),
    "no-change-folder": (
        "there is no change folder",
        "the id matches no folder under changes/",
        "you",
        "python3 ${{CLAUDE_SKILL_DIR}}/scripts/sdlc_status.py map",
    ),
    "not-approved": (
        "the plan was never approved",
        "lock.json is missing",
        "you",
        "python3 scripts/verify_gate.py approve {id}",
    ),
    "protected-path": (
        "the approved criteria changed",
        "facts.md, done.json or checks moved after approval",
        "you",
        "decide whether the change stands; never re-lock without a decision",
    ),
    "no-progress": (
        "the same failure came back three times",
        "the fix did not change the result",
        "you",
        "read verify/report.md, then delete verify/state.json to start over",
    ),
    "flaky": (
        "a check failed once and passed on a re-run",
        "a flaky check cannot prove the change",
        "you",
        "reproduce it locally three times and fix the check's flakiness in its own change",
    ),
    "unknown-verdict": (
        "a check ended without a verdict the gate understands",
        "its last line was neither pass nor a known blocked reason",
        "the agent",
        "read verify/report.md, then fix the check's output",
    ),
    "needs-baseline": (
        "a check needs a baseline that does not exist",
        "nothing recorded the passing state to compare with",
        "you",
        "decide whether to record the baseline, then rerun `python3 scripts/verify_gate.py {scope} {id}`",
    ),
    "allowlist-request": (
        "a check asks for a wider allowlist",
        "the change needs something its limits do not permit",
        "you",
        "decide whether to widen the allowlist; never widen it silently",
    ),
    "scope-growth": (
        "the change grew past its plan",
        "files outside the plan's Files that change were edited",
        "you",
        "decide whether the plan or the edit moves",
    ),
    "spec-conflict": (
        "the build contradicts the approved spec",
        "a check found a state the spec forbids",
        "you",
        "decide whether the spec or the build changes",
    ),
    "env": (
        "the gate cannot run here",
        "no checks are configured, the change folder is missing or the environment is broken",
        "you",
        "fix the environment named in the gate output, then rerun `python3 scripts/verify_gate.py {scope} {id}`",
    ),
    "test-proves-nothing": (
        "a test passes without the code it guards",
        "the test also passes on the old code",
        "the agent",
        "rewrite the test so it fails without the change",
    ),
    "attempts": (
        "three gate runs failed",
        "the breaker stops a loop",
        "you",
        "read verify/report.md, then delete verify/state.json to start over",
    ),
}


def blocker(subject: str, line: str, scope: str = "milestone", base: str = "") -> str:
    """The one thing in the way, as a sentence, from the goal line; empty when the goal is DONE.
    `subject` is the change id the goal was asked about, `scope` the gate it reads, `base` the
    branch the scope's PR must target. Built from the first missing item (the line lists them in
    the order the goal checks them)."""
    m = re.search(r"OPEN (\S+)|BLOCKED reason=([\w-]+)", line)
    if not m:
        return ""
    first = (m.group(1) or m.group(2)).split(",")[0]
    key_of = "gate-pass" if first.endswith("-gate-pass") else first
    for key, (what, why, who, step) in BLOCKS.items():
        if key_of == key or (key.endswith(("-", ":")) and first.startswith(key)):
            n = re.sub(
                r"^no-pr:|^no-such-milestone:|^no-branch-for-|^merge-missing:|^receipt-not-merged:|^gate-sha-not-tip:|^gate-sha-not-pr-|-head$",
                "",
                first,
            )
            fill = {"scope": scope, "id": subject, "n": n, "base": base or "<parent branch>"}
            return f"Blocking: {what.format(**fill)}, because {why}; {who} runs `{step.format(**fill)}`."
    waits = re.fullmatch(
        r"pr-(\d+)-(closed|held|awaits-tier|awaits-owner|awaits-workflow|wrong-base|ci-failed|label-awaiting-owner)", first
    )
    if waits and waits[2] == "awaits-owner":
        return (
            f"Blocking: PR {waits[1]} waits for its owner's acceptance, because it is labelled ask "
            f"(or awaiting-owner) and askGatesMerge is on; the agent asks the owner "
            f"`AskUserQuestion` \"Change {subject}, finding PR{waits[1]}: ...\" with the options "
            f"Accept milestone and Hold, and arms nothing before the answer."
        )
    if waits and waits[2] == "label-awaiting-owner":
        return (
            f"Blocking: PR {waits[1]} is accepted but still carries the awaiting-owner label, which "
            f"stops the tier workflow; the agent runs `gh pr edit {waits[1]} --remove-label awaiting-owner`."
        )
    if waits and waits[2] == "ci-failed":
        return (
            f"Blocking: a check of PR {waits[1]} failed, so arming it would never merge; the agent "
            f"runs `gh pr checks {waits[1]}`, fixes the failure on the branch and pushes."
        )
    if waits and waits[2] == "awaits-workflow":
        return (
            f"Blocking: PR {waits[1]} is open without auto-merge, because the tier workflow arms ship "
            f"and show PRs into the default branch; the agent runs "
            f"`gh pr view {waits[1]} --json labels,autoMergeRequest` to see whether it ran."
        )
    if waits and waits[2] == "wrong-base":
        return (
            f"Blocking: PR {waits[1]} targets the wrong branch, because the {scope} PR goes into "
            f"{base or 'its parent'}; the agent runs `gh pr edit {waits[1]} --base {base or '<parent branch>'}`."
        )
    if waits:
        what, step = {
            "closed": (
                "closed without merging, so there is nothing to arm",
                f"the agent runs `gh pr create --base {base or '<parent branch>'} --fill` for the gated head",
            ),
            "held": (
                "on Hold, so nothing arms it",
                f"you decide: `gh pr edit {waits[1]} --remove-label hold` for a label, or answer "
                f"the dialog \"Change {subject}, finding PR{waits[1]}: ...\" with Accept milestone",
            ),
            "awaits-tier": (
                "waiting for its tier label, so nothing arms it",
                f"the agent runs `gh pr view {waits[1]} --json labels` until the workflow has set it",
            ),
        }[waits[2]]
        return f"Blocking: PR {waits[1]} is {what}; {step}."
    pr = re.fullmatch(r"pr-(\d+)-not-merged-or-armed", first)
    if pr:
        flag = "--merge" if scope in ("milestone", "project") else "--squash"  # as the tier workflow
        return (
            f"Blocking: PR {pr[1]} is open without auto-merge, because nothing armed it; "
            f"the agent runs `gh pr merge {pr[1]} {flag} --auto`."
        )
    return f"Blocking: {first}, because the goal check lists it; the agent reads `sdlc_status.py goal {subject}`."


def security_base(change: Path) -> str:
    """The commit the goal started from: the `sha` approval recorded in lock.json ("" if none)."""
    return str(read_json(spec.state_path(change, "lock.json")).get("sha") or "")


def subject_of(change: Path, scope: str) -> str:
    """What the goal's recovery step names: the change id, or for a project the project slug."""
    slug = (read_json(spec.state_path(change, "decisions.json")).get("project") or {}).get("slug") if scope == "project" else ""
    return slug or change.name


def goal_main(args: list[str]) -> int:
    pos, flag, value = (
        list(args),
        next((a for a in args if a in ("--milestone", "--feature")), None),
        "",
    )
    project = "--project" in pos and not flag
    if project:
        pos.remove("--project")
    if flag:
        at = pos.index(flag)
        value = pos[at + 1] if at + 1 < len(pos) else ""
        del pos[at : at + 2]
    if len(pos) != 1 or (flag and not value.isdigit()) or pos[0].startswith("--"):
        print(__doc__)
        return 2
    root = repo_root(Path.cwd())
    scope = "project" if project else flag[2:] if flag else "milestone"
    change = find_change(root, config(root), pos[0]) if root else None
    if root and not change and (done := goal_removed(root, pos[0], scope, int(value) if flag else None)):
        print(done[1])
        if done[0]:
            print(blocker(pos[0], done[1], scope))
        return done[0]
    if not root or not change:
        line = f"GOAL {pos[0]} OPEN no-change-folder"
        print(line)
        print(blocker(pos[0], line, scope))
        return 1
    code, line = goal(root, change, scope, int(value) if flag else None)
    print(line)
    if code == 4:
        print(handoff_sentence(change))
        return code
    head = re.search(r"no-pr:([^,\s]+)", line)
    # a feature's base depends on its branch (a hotfix goes to the default branch): the no-pr one,
    # or else the plan's row
    row = branches(change, read_json(spec.state_path(change, "decisions.json")), scope, int(value) if flag else None)
    base = parent_of(change, config(root), scope, head[1] if head else row[0] if scope == "feature" and row else "")
    if code and (sentence := blocker(subject_of(change, scope), line, scope, base)):
        print(sentence)
    return code


def write_readme(change: Path, text: str) -> int:
    """Write the reading map: only over a README this tool generated, and only when it differs,
    so a stage commit carries it and a plain `status` never dirties the tree."""
    path = change / "README.md"
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old is not None and MARKER not in old:
        print(f"{path} is not generated (no {MARKER}); move or delete it first")
        return 2
    if old == text:
        print(f"unchanged {path}")
        return 0
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("map", "goal", "ids", "readme", "base", "record", "handoff"):
        print(__doc__)
        return 2
    if argv[1] == "goal":
        return goal_main(argv[2:])
    root = repo_root(Path.cwd())
    if not root:
        print("no sdlc.json in this repo: run `sdlc-run adopt`")
        return 2
    cfg = config(root)
    change = find_change(root, cfg, argv[2] if len(argv) > 2 else None)
    if not change:
        print("no change folder for this branch: pass its id")
        return 2
    if argv[1] == "record":  # record <id> project --sha <sha> [--accepted]
        rest = argv[3:]
        sha = rest[rest.index("--sha") + 1] if "--sha" in rest and rest.index("--sha") + 1 < len(rest) else ""
        if rest[:1] != ["project"]:
            print(__doc__)
            return 2
        code, said = record_project(root, change, cfg, sha, "--accepted" in rest)
        print(said)
        return code
    if argv[1] == "handoff":  # handoff <id> --cap turns|fix-rounds|retries [--what W] [--next C] | --resume
        from verify_gate import CAPS, write_handoff

        rest, path = argv[3:], change / "state" / "handoff.json"
        opt = lambda flag: rest[rest.index(flag) + 1] if flag in rest and rest.index(flag) + 1 < len(rest) else ""  # noqa: E731
        if "--resume" in rest:
            path.unlink(missing_ok=True)
            print(f"resumed {change.name}: the handoff is cleared")
            return 0
        if opt("--cap") not in CAPS:
            print(__doc__)
            return 2
        resume = f"python3 ${{CLAUDE_SKILL_DIR}}/scripts/sdlc_status.py handoff {change.name} --resume"
        nxt = opt("--next") or resume
        write_handoff(
            change, opt("--cap"), "milestone", opt("--what") or "the run stopped with the goal still open",
            f"the {opt('--cap')} cap was reached", nxt,
        )
        print(f"HANDOFF {change.name} cap={opt('--cap')} next={nxt}")
        return 0
    if argv[1] == "base":
        sha = security_base(change)
        print(sha or "no recorded start: approve the plan first")
        return 0 if sha else 1
    s = state(change, root, cfg)
    if argv[1] == "ids":
        print("\n".join(ids(change)))
    elif argv[1] == "readme":
        stage = f"{s['stage']}/7 {STAGES[s['stage'] - 1]}"
        return write_readme(change, readme(change, stage))
    else:
        print("\n".join([milestone_map(s), *side_notes(root)]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
