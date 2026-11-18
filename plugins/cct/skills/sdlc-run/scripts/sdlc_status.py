"""Where a change stands: every milestone, the features of this one, and the stage.

    python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py map [<id>]
    python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py goal <id> [--milestone <n> | --feature <n> | --project]
    python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py ids [<id>]
    python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py readme [<id>]

Runs from the plugin and is never copied into a repo: run it with the working directory inside the
adopted repo, which it finds from the cwd. It loads `verify_gate` from the plugin's own
`templates/scripts/`, not from the repo's `scripts/`. stdlib only.

Everything is read from the files; only `readme` writes, and only the change's README.md. The stage (1-7): an archived change → 7,
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

from change_docs import ids, readme

# verify_gate lives in the plugin's templates (it is also what adopt copies into repos).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates" / "scripts"))

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
        # archive/<year>/<year-month>/<id> once Stage 7 moved it
        found = [base / change_id, *base.glob(f"archive/**/{change_id}")]
        return next((d for d in found if d.is_dir()), None)
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
    """Rows of the milestone's Features table: [{id, feature, state}]."""
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
    if (change / "lock.json").exists():
        return 6 if rows and all(r["state"].startswith(("merged", "done")) for r in rows) else 5
    if (change / "plan.md").exists():
        return 4
    if (change / "facts.md").exists():
        return 3
    return 2 if frontmatter(change / "intent.md", "status") == "approved" else 1


def state(change: Path, root: Path, cfg: dict) -> dict:
    decisions = read_json(change / "decisions.json")
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
    """The head the gate passed, or a descendant that only added records (pr-gate.sh's rule)."""
    if gated == head:
        return True
    rel = str(cfg.get("changesDir", "changes")).rstrip("/") + "/"
    changed = git(root, "diff", "--name-only", gated, head).splitlines()
    return contains(root, gated, head) and bool(changed) and all(p.startswith(rel) for p in changed)


def planned(change: Path) -> int:
    """How many milestones plan.md lists."""
    plan = (change / "plan.md").read_text(encoding="utf-8") if (change / "plan.md").exists() else ""
    return sum(1 for line in section(plan, "Milestones") if re.match(r"\|\s*M\d+\b", line))


def branches(change: Path, decisions: dict, scope: str, n: int | None) -> list[str]:
    """Head branches whose PRs end the goal: milestone/<slug>-<n>, or the Feature PRs row's branch."""
    plan = (change / "plan.md").read_text(encoding="utf-8") if (change / "plan.md").exists() else ""
    if scope == "feature":
        for line in section(plan, "Feature PRs"):
            cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4 and cells[0] == str(n):
                return [cells[3]]
        return []
    slug = decisions.get("milestone", {}).get("slug") or slug_of(change.name)
    count = planned(change)
    return [f"milestone/{slug}-{i}" for i in ([n] if n else range(1, max(count, 1) + 1))]


def goal(
    root: Path, change: Path, scope: str = "milestone", n: int | None = None, gh=gh_json
) -> tuple[int, str]:
    """(exit code, the one line) for the change's goal; `gh(root, *args)` is injectable."""
    from verify_gate import merges_locally, project_branch, project_record

    name = f"GOAL {change.name}"
    cfg = config(root) if (root / "sdlc.json").exists() else {}
    project = project_branch(change, cfg)
    subject = change.name
    folder = change
    if scope == "project":
        subject = (read_json(change / "decisions.json").get("project") or {}).get("slug", "")
        folder = project_record(subject, root) if project else change
    report = read_json(folder / "verify" / "report.json")
    result = str(report.get("result", "")) if report.get("scope") == scope else ""
    blocked = re.fullmatch(r"VERIFY BLOCKED reason=([\w-]+)", result)
    if blocked:
        return 3, f"{name} BLOCKED reason={blocked.group(1)}"
    passed = re.fullmatch(rf"VERIFY PASS {scope} {re.escape(subject)} (\w+)", result)
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
        if planned(change):
            for b in branches(change, read_json(change / "decisions.json"), scope, n):
                i = b.rsplit("-", 1)[1]
                receipt = read_json(change / "verify" / f"milestone-{i}.json")
                if receipt:
                    ok = str(receipt.get("result", "")).startswith("VERIFY PASS milestone ")
                    if not (ok and contains(root, str(receipt.get("sha", "")), into)):
                        missing.append(f"receipt-not-merged:{i}")
                    continue
                tip = git(root, "rev-parse", "--verify", "--quiet", f"{b}^{{commit}}")
                if not contains(root, tip, into):
                    missing.append(f"merge-missing:{b}")
    elif scope == "project":
        names = [project] if project else []
        if not names:
            missing.append("no-project-branch")
    else:
        names = branches(change, read_json(change / "decisions.json"), scope, n)
    if not names and not local and scope != "project":
        missing.append(f"no-branch-for-{scope}-{n}")
    prs = []
    for branch in names:
        found = gh(
            root,
            *("pr", "list", "--head", branch, "--state", "all", "--limit", "1"),
            *("--json", "number,headRefOid,state,autoMergeRequest,mergedAt,baseRefName"),
        )
        if found is None:
            return 1, f"{name} OPEN gh-unavailable"
        if not found:
            missing.append(f"no-pr:{branch}")
            continue
        pr = found[0]
        merged = pr.get("state") == "MERGED" or bool(pr.get("mergedAt"))
        armed = pr.get("state") == "OPEN" and bool(pr.get("autoMergeRequest"))
        if not (merged or armed):
            missing.append(f"pr-{pr['number']}-not-merged-or-armed")
        if scope == "project" and pr.get("baseRefName") != (cfg.get("defaultBranch") or "main"):
            missing.append(f"pr-{pr['number']}-wrong-base")
        prs.append((pr, "merged" if merged else "armed"))
    if (
        prs
        and passed
        and not same_head(root, cfg, passed.group(1), prs[-1][0].get("headRefOid", ""))
    ):
        missing.append(f"gate-sha-not-pr-{prs[-1][0]['number']}-head")
    if scope == "milestone":
        from verify_gate import milestone_blockers  # the gate's own record rules, one definition

        if blocker := milestone_blockers(change):
            missing.append(blocker[0])
    if missing:
        return 1, f"{name} OPEN " + ",".join(missing)
    if local:
        return 0, f"{name} DONE merged={project} gate={passed.group(1)}"
    pr, state = prs[-1]
    return 0, f"{name} DONE pr={pr['number']} state={state} gate={passed.group(1)}"


# what is in the way, by the first missing item: (what, why, who acts, the exact step)
BLOCKS = {
    "milestone-gate-pass": (
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
        "gh pr create --head {n} --fill",
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
    "no-branch-for-": (
        "the plan names no branch for {n}",
        "plan.md has no matching row",
        "you",
        "add the row to plan.md ## Feature PRs",
    ),
    "no-change-folder": (
        "there is no change folder",
        "the id matches no folder under changes/",
        "you",
        "python3 scripts/sdlc_status.py map",
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
    "attempts": (
        "three gate runs failed",
        "the breaker stops a loop",
        "you",
        "read verify/report.md, then delete verify/state.json to start over",
    ),
}


def blocker(change: Path, line: str, scope: str = "milestone") -> str:
    """The one thing in the way, as a sentence, from the goal line; empty when the goal is DONE.
    Built from the first missing item (the line lists them in the order the goal checks them)."""
    m = re.search(r"OPEN (\S+)|BLOCKED reason=([\w-]+)", line)
    if not m:
        return ""
    first = (m.group(1) or m.group(2)).split(",")[0]
    for key, (what, why, who, step) in BLOCKS.items():
        if first == key or (key.endswith(("-", ":")) and first.startswith(key)):
            n = re.sub(
                r"^no-pr:|^no-branch-for-|^merge-missing:|^receipt-not-merged:|^gate-sha-not-pr-|-head$", "", first
            )
            fill = {"scope": scope, "id": change.name, "n": n}
            return f"Blocking: {what.format(**fill)}, because {why}; {who} runs `{step.format(**fill)}`."
    pr = re.fullmatch(r"pr-(\d+)-not-merged-or-armed", first)
    if pr:
        flag = "--merge" if scope == "milestone" else "--squash"
        return (
            f"Blocking: PR {pr[1]} is open without auto-merge, because nothing armed it; "
            f"the agent runs `gh pr merge {pr[1]} {flag} --auto`."
        )
    return f"Blocking: {first}, because the goal check lists it; the agent reads `sdlc_status.py goal {change.name}`."


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
    change = find_change(root, config(root), pos[0]) if root else None
    if not root or not change:
        print(f"GOAL {pos[0]} OPEN no-change-folder")
        return 1
    scope = "project" if project else flag[2:] if flag else "milestone"
    code, line = goal(root, change, scope, int(value) if flag else None)
    print(line)
    if code and (sentence := blocker(change, line, flag[2:] if flag else "milestone")):
        print(sentence)
    return code


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("map", "goal", "ids", "readme"):
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
    s = state(change, root, cfg)
    if argv[1] == "ids":
        print("\n".join(ids(change)))
    elif argv[1] == "readme":
        stage = f"{s['stage']}/7 {STAGES[s['stage'] - 1]}"
        (change / "README.md").write_text(readme(change, stage), encoding="utf-8")
        print(f"wrote {change / 'README.md'}")
    else:
        print(milestone_map(s))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
