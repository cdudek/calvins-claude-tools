#!/usr/bin/env python3
"""Usage: goal-brief.py <plan.md> <milestone-id> --approved <sha>
       goal-brief.py <plan.md> --all --approved <sha>
Run inside the milestone worktree (branch milestone/<slug>-<M>, cut from a base that already holds the
merged plan PR). Turns the approved plan into the run briefing for one milestone, or with --all for every
milestone in order (every milestone must already have tasks; refused with a `hold`).
Writes kickoff-<M>.md (kickoff-all.md) next to plan.md, then prints three sections:
  -#-#- KICKOFF FILE -#-#-   path of the kickoff written
  -#-#- GOAL -#-#-           the /goal line (checked against the 4,000-character limit)
  -#-#- RUN -#-#-            the unattended command, and the interactive alternative
Exit 1 with `BRIEF FAIL <reason>` if the plan fails check_plan.validate (which also fails a plan, delta.md or
intent.md that changed since <sha>, the commit the owner approved; with --all it also needs every milestone
detailed and no hold) or the milestone is not detailed.
The kickoff names <sha> and passes it to every test-integrity.sh and check-plan.py call (`--task`/`--milestone`),
with the plan as a repo-relative path (changes/<slug>/plan.md: the coordinator runs the scripts against task
worktrees of the same repo). It records the fetched target SHA of origin/<target> and the INTEGRITY OK commit of
every task: the pre-PR call passes the first as <base-ref> and `--target`, the second as `--checked`.
A bug or small feature is a normal plan with `kind` (one milestone, one task); `kind: bug` adds the two-commit
flow (the first commit holds only the failing test, later integrity calls pass `--pin` for it).

Plan keys read here: `hold` (an owner action known in advance: Ship pushes the milestone branch and opens no PR,
the goal ends HOLD: <hold>), `setup` (run in every new task worktree), `preflight` (commands run first, a failure
is BLOCKED), `merge` ("auto", default, or "owner": never arm auto-merge, end SHIPPED with the merge-ready PR URL),
`integration` (a branch: milestone PRs merge into it on their own; the last milestone opens the one release PR from it
into `base`, auto-merge armed unless a milestone is risky or `deployOnMerge` is true, then the run ends SHIPPED
with the merge-ready release PR URL) and `kind`.
"""
import importlib.util
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("check_plan", HERE / "check-plan.py")
check_plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_plan)

UI_LAYERS = {"components", "layouts", "screens"}
GOAL_LIMIT = 4000
# Hard circuit breaker for `claude -p --max-turns`. It counts the coordinator's own turns only; builder
# (subagent) steps do not count (probe 2026-11-24). Measured on a first beta milestone: 148 coordinator tool
# calls for 15 agent dispatches, about 10 per dispatch (brief, integrity, merge, checks, log).
PASSES = 3          # builder passes allowed per task
STEPS_PER_DISPATCH = 10
SAFETY = 2          # a run that spends every allowed pass still ends at half the cap


def max_turns(m):
    """Worst-case dispatches: every task uses every pass, the verifier runs once per pass, plus the
    security review (risky) and the UX verifier (UI). Times steps per dispatch, times the safety factor."""
    dispatches = len(m["tasks"]) * PASSES + PASSES + bool(m.get("risky")) + (m["layer"] in UI_LAYERS)
    return SAFETY * STEPS_PER_DISPATCH * dispatches


def main_root(start):
    """The main checkout, which holds .worktrees/ even when we run inside a worktree."""
    out = subprocess.run(["git", "-C", str(start), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                         capture_output=True, text=True, check=True).stdout.strip()
    return Path(out).parent


def repo_prefix(plan_path):
    """The plan's folder relative to its worktree root, with a trailing slash ("" at the root): the form every script call gets."""
    return subprocess.run(["git", "-C", str(plan_path.parent), "rev-parse", "--show-prefix"],
                          capture_output=True, text=True, check=True).stdout.strip()


def target(plan):
    """Where milestone PRs go: the integration branch when the plan has one, else the base."""
    return plan.get("integration") or plan["base"]


def needs_human(plan):
    """The release PR waits for the owner when a milestone is risky, the merge deploys, or the plan says merge: owner."""
    return any(x.get("risky") for x in plan["milestones"]) or plan.get("deployOnMerge") is True or plan.get("merge") == "owner"


def merge_action(plan, tgt):
    if plan.get("integration"):
        return (f"merge the PR yourself with `gh pr merge <n> --squash` (no remote CI is required on `{tgt}`; "
                f"the one release PR from `{tgt}` into `{plan['base']}` runs the full CI)")
    if plan.get("merge") == "owner":
        return ("never arm auto-merge: wait for the required CI, then end with SHIPPED, the merge-ready PR URL "
                "(the real URL) and its CI conclusion")
    return "arm auto-merge"


def release_line(plan):
    integ, base = plan["integration"], plan["base"]
    line = (f"Release: once the milestone PR is merged, open the one release PR from `{integ}` into `{base}` "
            f"(`gh pr create --base {base} --head {integ}`), linking the delta revision, every milestone's "
            "evidence/<M>/gallery.md and the reports. Remote CI runs on it. ")
    if needs_human(plan):
        why = ("a milestone is risky" if any(x.get("risky") for x in plan["milestones"])
               else "deployOnMerge is true" if plan.get("deployOnMerge") else "merge is owner")
        return line + (f"Do not arm auto-merge ({why}): wait for its required CI in the foreground (`gh pr checks <n> --watch`), "
                       "then end with SHIPPED, the merge-ready release PR URL and its CI conclusion.")
    return line + ("Arm auto-merge (`gh pr merge <n> --merge --auto`), wait for the required CI in the foreground "
                   "(`gh pr checks <n> --watch`), then print the PR number, merge SHA and CI conclusion.")


def wait_line(plan):
    if plan.get("integration"):
        return "Print the PR number and merge SHA."
    wait = "Wait for the required CI in the foreground (`gh pr checks <n> --watch`), then print the PR number, "
    return wait + ("and CI conclusion." if plan.get("merge") == "owner" else "merge SHA and CI conclusion.")


def task_lines(m, change, root, setup):
    out = []
    for t in m["tasks"]:
        wt = f"{change}-{m['id']}-{t['id']}"
        needs = ", ".join(t.get("needs", [])) or "nothing"
        effort = t.get("effort", "medium")
        out.append(
            f"- {t['id']} covers {', '.join(t['covers'])}. Worktree: `git branch {wt} milestone/{change}-{m['id']}`, then "
            f"`wt switch {wt} --no-cd --yes` (at {root}/.worktrees/{wt}); "
            + (f"run `{setup}` in it; " if setup else "")
            + f"its HEAD must equal the milestone head. Owns only: {', '.join(t['files'])}. Uses {needs}. Its check: `{t['check']}`. Builder effort: {effort}."
            + (f" Builder model: {t['model']}." if "model" in t else ""))
    return out


def verifier_tier(m):
    """The milestone's own verifier model and effort, or nothing for the default (Opus 5.5 high)."""
    v = m.get("verifier")
    return f" (pass model {v.get('model', 'opus')} and effort {v.get('effort', 'high')} to the Agent call)" if v else ""


def section(plan, m, P, root, sha, h, preflight, record=True):
    """One milestone's Build, Verify and Ship, under headings of level h. P is the plan's repo-relative folder prefix;
    record=False when the milestone is cut later in a --all run, whose cut step records the target SHA."""
    change, mid, ui = plan["change"], m["id"], m["layer"] in UI_LAYERS
    branch = f"milestone/{change}-{mid}"
    tgt = target(plan)
    action = merge_action(plan, tgt)
    hold, bug = plan.get("hold"), plan.get("kind") == "bug"
    last = mid == plan["milestones"][-1]["id"]
    pin = " --pin <failing-test SHA>" if bug else ""
    flags = f"--approved {sha}{pin} --target <target SHA>"
    pre_pr = (f"`bash .cfactory/test-integrity.sh <this worktree> <target SHA> {P}plan.md --milestone {mid} {flags} "
              f"--checked <checked SHAs, comma separated>` and `python3 .cfactory/check-plan.py {P}plan.md --approved {sha}`; both must pass")
    lines = [
        f"{h} Build",
        *preflight,
        *([f"Target: run `git fetch origin`, then `git rev-parse origin/{tgt}` and record the output as <target SHA>. Every integrity call "
           f"below passes it, so a local `{tgt}` that lags origin never decides what counts as this milestone's change."] if record else []),
        "One worktree per task, created by you, never by the Agent tool's worktree isolation:",
        *task_lines(m, change, root, plan.get("setup")),
        "Every task runs in a factory:builder subagent (Sonnet 5.5, at the task's builder effort), even a one-line fix; "
        "you only create worktrees, run checks, merge and log. Run 2 or 3 at a time, in the foreground, "
        "each given its worktree path, owned files, requirement ids and check. Never give a builder the scenarios path."
        + (" Pass each task's builder model and effort to its Agent call (a task with no model runs on Sonnet 5.5)."
           if any("model" in t for t in m["tasks"]) else ""),
        "Every agent you start (builders, verifiers, reviews) runs in the foreground, never with run_in_background: a background agent pauses the goal check, and an unattended run exits under it.",
        "Unfinished work stays in its task worktree and the next pass gets the same path. Never patch files "
        "(no `git apply`, no copied diffs). To read a diff: `rtk proxy git diff`.",
        *(["Bug flow (kind: bug): tell the builder its first commit holds only the failing regression test, no fix. When it reports that "
           "commit, run the task's check with the worktree at that commit, paste the failing output, and record the SHA as "
           "<failing-test SHA>. The fix pass goes to the same worktree, and every later integrity call for the task passes "
           "`--pin <failing-test SHA>`."] if bug else []),
        "",
        f"{h} Verify, in this order, pasting each output into the transcript",
        "1. The repo's fast checks: lint, typecheck, unit. No local CI.",
        f"2. Per task, before merging it into `{branch}`: "
        f"`bash .cfactory/test-integrity.sh {root}/.worktrees/<task-worktree> {branch} {P}plan.md --task <task id> {flags}` "
        "must print INTEGRITY OK. "
        f"Then record `git -C {root}/.worktrees/<task-worktree> rev-parse HEAD` as that task's <checked SHA> (every INTEGRITY OK commit, "
        f"also an earlier pass's) and merge exactly that commit into `{branch}`.",
    ]
    if m.get("risky"):
        lines.append("3. This milestone is risky (auth, money, consent or data exposure): also run a security review of the diff and delta, "
                     "by one Opus 5.5 high advisory agent or `codex exec -m gpt-6.2-astra -c model_reasoning_effort=high -s read-only --ephemeral`, "
                     "and fix a confirmed High only inside the task's own files and its allowTestEdits. A fix that needs a new task, other files "
                     "or another test edit ends `BLOCKED: owner approves plan revision for <finding>`.")
    if ui:
        lines.append(f"{4 if m.get('risky') else 3}. factory:ux-verifier against the design boards in `{P}design/`, which the owner approved "
                     f"at the single approval, per the factory ux-checks reference. Screenshots go to {P}evidence/{mid}/. Write the gallery to "
                     f"{P}evidence/{mid}/gallery.md; Ship commits it with the progress entry. It is evidence, not a stop: the milestone merges like any other.")
    lines += [
        "Failures go back to the builder of that task, at most 3 passes. Stop after 2 attempts at the same failure with no new evidence.",
        "",
        f"{h} Ship, in this order",
        "Commit first, verify that final commit, push that same SHA. Nothing is committed after the verifier: a later commit is a different SHA "
        "and needs the verifier again.",
        f"1. Commit on `{branch}`: " + (f"the delta, as your own commit: apply {P}delta.md to the spec files it names (this is the last milestone). "
                                       f"First check that every MODIFIED or REMOVED entry's prior text still matches the spec on `{plan['base']}` and "
                                       "every ADDED id is unused; on a mismatch stop `BLOCKED: delta conflicts with base, owner re-approves`. Then " if last else "")
        + ("the gallery and " if ui else "") + "the progress entry to plan.md (time, milestone, requirement ids, done and remaining, check result, "
        "next action; no PR number or merge SHA, they are not known yet and `gh pr view` has them).",
        f"2. Run {pre_pr}.",
        f"3. factory:verifier{verifier_tier(m)} on the final commit (`git rev-parse HEAD` is the <final SHA>), with the delta, base, diff and the holdout "
        f"scenarios in `~/.cfactory/scenarios/{root.name}/{change}/` for {', '.join(m['covers'])}. Never the builders' reasoning. "
        "A failure goes back to the builder of that task; its new commit goes through Verify step 2 (per-task integrity, a new <checked SHA>, "
        "merge that commit), then repeat Ship from step 1.",
    ]
    if hold:
        lines.append(f"4. Open no PR and merge nothing: the owner action `{hold}` comes first. Then push `{branch}` once, which is the <final SHA>, "
                     "and print the pushed SHA with the verifier PASS for that SHA.")
        return lines
    lines += [
        f"4. Push `{branch}`, which is the <final SHA>, print it with the verifier PASS for that SHA, and open the milestone's one PR into `{tgt}`, "
        "linking the delta revision and the reports. Every push to an open PR runs CI again, so batch fixes into one push.",
        action[0].upper() + action[1:] + ".",
        wait_line(plan),
    ]
    if last and plan.get("integration"):
        lines.append(release_line(plan))
    return lines


def kickoff(plan, ms, plan_path, root, sha, every=False):
    """The kickoff for the milestones in ms (one, or all in order)."""
    change, P, tgt = plan["change"], repo_prefix(plan_path), target(plan)
    hold = plan.get("hold")
    first = f"milestone/{change}-{ms[0]['id']}"
    pre = ([f"First run every preflight command and paste each output: {', '.join(f'`{c}`' for c in plan['preflight'])}. "
            "Any failure ends `BLOCKED: <tool or credential> missing: <exact fix>`."] if plan.get("preflight") else [])
    scope = (f"every milestone in order ({', '.join(x['id'] for x in ms)}), starting from this worktree on branch `{first}`" if every
             else f"milestone {ms[0]['id']} only, from this worktree on branch `{first}`")
    lines = [
        f"# Kickoff: {change}, " + (f"all {len(ms)} milestones" if every else f"milestone {ms[0]['id']} ({ms[0]['layer']})"),
        "",
        f"You coordinate factory change {change}, {scope}. "
        f"The approved plan and delta are on `{tgt}`, or on this branch for milestone 1 in a repo without a plan PR. "
        f"Read {P}plan.md and {P}delta.md first. The owner approved revision `{sha}`; every integrity and plan check below passes it.",
        "Do reversible steps yourself and keep going: create a missing branch, rerun a check, recreate a worktree. Stop only for a decision the plan does not cover or an irreversible step.",
        "Resume rule: read the progress log in plan.md, reconcile it with git and PR state, skip what is already done. "
        "Read a PR's state and merge SHA from `gh pr view <n> --json state,mergeCommit` or git, never from the log. "
        f"A resumed run has lost the recorded <target SHA> and <checked SHA>s: re-record the target as `git merge-base HEAD origin/{tgt}` "
        "after `git fetch origin`, and each merged task's <checked SHA> as the second parent of its merge, after its per-task integrity passes again.",
    ]
    if every:
        lines += [
            f"At the start of each milestone, re-read the pinned plan (`git show {sha}:{P}plan.md`, its json block) and the progress log "
            "in plan.md, and reconcile with git and PR state. Start a milestone only after the previous one is merged. A later milestone "
            f"gets its own worktree: `git fetch origin`, record `git rev-parse origin/{tgt}` as that milestone's <target SHA>, "
            f"`git branch milestone/{change}-<M> <target SHA>`, `wt switch milestone/{change}-<M> --no-cd --yes`.",
            *pre,
        ]
        pre = []
    for i, x in enumerate(ms):
        lines += ["", *([f"## Milestone {x['id']} ({x['layer']}), branch `milestone/{change}-{x['id']}`"] if every else [])]
        lines += section(plan, x, P, root, sha, "###" if every else "##", pre, record=i == 0)
    lines += [
        "",
        "## Stop",
        f"End with exactly one state: {'HOLD' if hold else 'SHIPPED'}, INCOMPLETE or BLOCKED.",
        *([f"HOLD: {hold}. Only once the pushed SHA and the verifier PASS for that SHA are in the transcript."] if hold else []),
        "BLOCKED: an owner decision, credential, approval or destructive migration. Write the exact action needed and stop.",
        "Scope beyond the delta, or a test, CI file or spec that must change: BLOCKED, the owner decides.",
    ]
    return "\n".join(lines) + "\n"


def goal(plan, m, every=False):
    ms = plan["milestones"]
    final = ms[-1] if every else m
    ui = any(x["layer"] in UI_LAYERS for x in (ms if every else [m]))
    extra = ", and the UX verdict" if ui else ""
    ids = ", ".join(map(str, plan["requirements"] if every else m["covers"]))
    # the verifier PASS belongs to the milestone branch's pushed SHA, never to the release PR's head
    ids += " on each milestone branch's pushed SHA" if every else f" on the pushed SHA of branch milestone/{plan['change']}-{m['id']}"
    tgt, base, integ, hold = target(plan), plan["base"], plan.get("integration"), plan.get("hold")
    what = f"all {len(ms)} milestones of {plan['change']}" if every else f"milestone {m['id']} of {plan['change']}"
    be = "are" if every else "is"
    if integ and final["id"] == ms[-1]["id"]:
        rel = f"the release PR from {integ} into {base}"
        if needs_human(plan):
            done = (f"{what} {be} built and {rel} is ready for the owner: the transcript shows the PR number, its required CI conclusion, and "
                    f"verifier evidence for {ids}{extra}, and the last message starts with SHIPPED and gives the merge-ready PR URL")
        else:
            done = (f"{what} {be} built and {rel} is merged into {base}: the transcript shows the PR number, its merge SHA, its required CI "
                    f"conclusion, and verifier evidence for {ids}{extra}")
    elif integ:
        done = f"{what} {be} merged into {tgt}: the transcript shows the PR number, its merge SHA, and verifier evidence for {ids}{extra}"
    elif plan.get("merge") == "owner":
        pr = "the last milestone PR" if every else "its PR"
        done = (f"{what} {be} built and {pr} into {tgt} is ready for the owner: the transcript shows the PR number, its required CI conclusion, "
                f"and verifier evidence for {ids}{extra}, and the last message starts with SHIPPED and gives the merge-ready PR URL")
    else:
        done = (f"{what} {be} merged into {tgt}: the transcript shows the PR number, its merge SHA, its required CI conclusion, "
                f"and verifier evidence for {ids}{extra}")
    # numbered end states, the planned hold before BLOCKED: a Haiku evaluator misread parenthetical and
    # "other than" exceptions about half the time (replays 2026-11-25), so the hold rule is a plain sentence of its own
    states = []
    if hold:
        states.append(f"HOLD: the last message starts with HOLD: and the transcript shows the pushed SHA of branch "
                      f"milestone/{plan['change']}-{m['id']} and a verifier PASS for that same SHA")
    else:
        states.append(f"SHIPPED: {done}")
    # "an exact owner action" failed a BLOCKED that offered the owner a choice (real /goal evaluator, 2026-11-25)
    blocked = ("BLOCKED: the last message starts with BLOCKED: and names the decision or action the owner must take "
               "(one action or a choice of options), whatever the build state")
    if hold:
        blocked += f". In this run, {hold} is not such an action: it is the planned hold, which only 1) can end"
    states.append(blocked)
    turns = plan["goalTurns"] * (len(ms) if every else 1)
    states.append(f"INCOMPLETE: after {turns} turns, the last message starts with INCOMPLETE and names the next step")
    return "/goal Met when any one of these is true. " + " ".join(f"{i}) {s}." for i, s in enumerate(states, 1))


def git_out(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)


def scrub(text):
    """git echoes remote URLs in its errors: drop `user:pass@` from any `scheme://user:pass@host`."""
    return re.sub(r"(\w+://)[^/@\s]+@", r"\1", text.strip())


def valid_ref(cwd, name):
    """A branch name git accepts that cannot be read as an option."""
    return not name.startswith("-") and git_out(cwd, "check-ref-format", "--branch", name).returncode == 0


def preflight_integration(plan_path, plan, sha):
    """Create the plan's integration branch on origin when it is missing. Returns (ok, line).
    Only a branch named integration/... is pushed here; any other name gets the command to run by hand.
    shortcut: a repo with no origin remote skips this, the run's own `git fetch origin` fails loudly then."""
    integ, base, cwd = plan["integration"], plan["base"], plan_path.parent
    for what, name in (("integration", integ), ("base", base)):
        if not valid_ref(cwd, name):
            return False, f"plan {what} {ascii(name)[:60]} is not a valid branch name"
    if not re.fullmatch(r"[0-9a-f]{7,40}", str(sha)):
        return False, f"approved revision {ascii(sha)[:60]} is not a commit hash"
    if git_out(cwd, "remote", "get-url", "origin").returncode:
        return True, ""
    ls = git_out(cwd, "ls-remote", "--heads", "--", "origin", integ)
    if ls.returncode:
        return False, f"could not read origin (git ls-remote --heads origin {integ} failed): {scrub(ls.stderr)}"
    if ls.stdout.strip():
        return True, f"{integ} exists on origin"
    push = f"git push origin {sha}:refs/heads/{integ}"
    if not integ.startswith("integration/"):
        return False, f"{integ} is missing on origin and is not named integration/...: run `{push}` yourself"
    on_base = (git_out(cwd, "fetch", "-q", "--", "origin", base).returncode == 0
               and git_out(cwd, "merge-base", "--is-ancestor", "--", sha, "FETCH_HEAD").returncode == 0)
    if not on_base:
        return False, f"{integ} is missing on origin and the approved {sha} is not on {base}: run `{push}`"
    done = git_out(cwd, "push", "-q", "origin", f"{sha}:refs/heads/{integ}")
    if done.returncode:
        return False, f"could not push {integ} (`{push}` failed): {scrub(done.stderr)}. Run it yourself"
    return True, f"created {integ} on origin from {sha}"


def print_run(out, g, turns):
    print("-#-#- KICKOFF FILE -#-#-")
    print(out)
    print("-#-#- GOAL -#-#-")
    print(g)
    print("-#-#- RUN -#-#-")
    print(f"# unattended, from this milestone worktree; --max-turns {turns} is the hard breaker (coordinator turns only, "
          "2 x 10 x worst-case dispatches), the goal's turn clause the soft one")
    print(f"claude -p --model sonnet --effort medium --permission-mode auto --max-turns {turns} "
          f"--append-system-prompt \"$(cat {shlex.quote(str(out))})\" --output-format stream-json --verbose {shlex.quote(g)}")
    print("# interactive: start claude here, paste the kickoff file, then paste the /goal line")


def main():
    args = sys.argv[1:]
    sha = args[3] if len(args) == 4 and args[2] == "--approved" else None
    if len(args) not in (2, 4) or (len(args) == 4 and sha is None):
        print("usage: goal-brief.py <plan.md> <milestone-id | --all> --approved <sha>", file=sys.stderr)
        return 2
    path, mid = Path(args[0]), args[1]
    if sha is None:
        print("BRIEF FAIL pass --approved <sha>, the commit the owner approved")
        return 1
    try:
        plan = check_plan.load(path)
        root = main_root(path.parent)
    except (OSError, ValueError, subprocess.CalledProcessError) as e:
        print(f"BRIEF FAIL {e}")
        return 1
    every = mid == "--all"
    errs = check_plan.validate(path, sha, every)[0]  # --all: every milestone detailed, no hold
    mss = plan.get("milestones", [])
    pick = mss if every else [x for x in mss if x.get("id") == mid]
    if not pick:
        errs.append(f"no milestone {mid}")
    if not every:
        errs += [f"{x.get('id')} has no tasks: detail it in plan.md and get the plan revision approved first" for x in pick if not x.get("tasks")]
    g =goal(plan, pick[0], every) if not errs else ""
    if len(g) > GOAL_LIMIT:
        errs.append(f"goal is {len(g)} characters, the limit is {GOAL_LIMIT}")
    if errs:
        for e in errs:
            print(f"BRIEF FAIL {e}")
        return 1
    if plan.get("integration"):
        ok, msg = preflight_integration(path, plan, sha)
        if not ok:
            print(f"BRIEF FAIL {msg}")
            return 1
        if msg:
            print(f"-#-#- PREFLIGHT -#-#-\n{msg}")
    out = path.parent / f"kickoff-{'all' if every else mid}.md"
    out.write_text(kickoff(plan, pick, path, root, sha, every), encoding="utf-8")
    print_run(out, g, sum(max_turns(x) for x in pick))
    return 0


if __name__ == "__main__":
    sys.exit(main())
