# Trackers: Linear, GitHub, Beads — what is what, and how to set each up

`sdlc.json` `tracker.kind` names the one tool that holds the plan's status: `linear`, `github`,
`beads` or `none`. The old `linear` key with a `team` still means `linear`. Content always lives
in the repo; the tracker holds status and links. A change never waits for a tracker.

## Choose: detect, then one dialog

Run `python3 ${CLAUDE_SKILL_DIR}/scripts/tracker.py detect --linear-mcp yes|no` at `adopt` and at
Stage 1.0 when `sdlc.json` names no tracker. Pass `yes` when the Linear MCP tools are in your tool
list. Then one `AskUserQuestion`: the four kinds, the script's `recommend` first as
`(Recommended)` with its `reason`, each option's description naming what is missing from
`SETUP`. Write the answer and its ids into `sdlc.json` `tracker`, then run the setup guide below.

| Situation | Recommend | Because |
|---|---|---|
| `sdlc.json` names one | that one | it is already decided |
| the repo already uses one (`.beads/`, open GitHub milestones, a `linear` key) | that one | switching splits the history |
| `gh` works | GitHub | no extra tool |
| `bd` installed | Beads | local, with epics |
| nothing works | none | the repo files are the plan until a tracker is set up |

## The ladder: four levels, the same words everywhere

| Level | What it is | In the repo |
|---|---|---|
| **Initiative** | an outcome over a quarter or so; several projects | the design docs that name it |
| **Project** | one deliverable with one design | `docs/designs/<slug>.md` |
| **Milestone** | one shippable slice, checked once, one PR to the default branch | a change folder + `milestone/<slug>` |
| **Issue** | one feature PR into the milestone | a row in `milestone.md` `## Features` |

Each tool organises these differently. Use its own concepts; do not force one onto another.

## Linear — the richest

| Level | Linear object | Notes |
|---|---|---|
| Initiative | Initiative | holds several projects and their health updates |
| Project | Project, under the initiative | description links the design doc permalink |
| Milestone | Project milestone, plus one issue for the change | the change's issue holds the folder key and closes with the milestone PR |
| Issue | Sub-issue of the change's issue, in the project and milestone | one per feature PR, created at the plan gate (4.3); blocking via relations |

**Setup:** connect the MCP (`/mcp` → claude.ai Linear). Pick the team. Create or attach the initiative, then
the project. Write `tracker: {"kind": "linear", "team", "initiative", "project"}`. Create minimal,
then update (the connector is flaky on large writes); retry twice.

**Status:** the change's issue goes `In Progress` at 1.2 and `Done` (or `Ready To Deploy` where
the repo deploys separately) only when the milestone PR merges to the default branch. Each
sub-issue goes `In Progress` when its builder starts, `In Review` when its PR opens, and `Done`
when it merges into the milestone branch. Never backwards.

**Which merge closes what.** Linear's GitHub integration closes every issue whose key is in a
merged PR's branch name or title, whatever branch the PR merged into. One issue per change
therefore went `Done` at its first feature merge, while the rest was unbuilt and nothing was on
the default branch (seen with three issues in one repo). So:

- A feature branch and its PR title carry the **sub-issue** key, never the change's key.
- The milestone branch `milestone/<slug>` carries no key.
- The milestone PR title and body name the change's key with `Closes <KEY>`; its merge is the
  only one that closes the change.
- Do not reopen an issue at the milestone checks to correct an early `Done`; split it instead. Text goes through `scripts/linear-safe.py`.

## Beads — local, epics and dependencies

| Level | Beads object | Command |
|---|---|---|
| Initiative | epic, label `initiative` | `bd create "<name>" -t epic -l initiative` |
| Project | epic under it, label `project` | `bd create "<name>" -t epic -l project --parent <initiative-id>` |
| Milestone | epic under the project, label `milestone` | `bd create "<slug>" -t epic -l milestone --parent <project-id>` |
| Issue | feature, bug or task under the milestone | `bd create "<feature>" -t feature --parent <milestone-id>` |

Order the features with `bd dep add <later> --depends-on <earlier>`; `bd ready` then shows what may start.
`bd children <id>` lists a level. **Setup:** `brew install beads`, then `bd init` in the repo
(commit `.beads/`). Write `tracker: {"kind": "beads", "initiative", "project"}`. **Status:**
`bd update <id> --status in_progress` at 1.2, `bd close <id>` on merge.

## GitHub — issues, sub-issues, milestones and a board

| Level | GitHub object | Command |
|---|---|---|
| Initiative | issue labelled `initiative`; its sub-issues are the projects' tracking issues | `gh issue create -l initiative` |
| Project | a Project (v2) board, plus a tracking issue that is a sub-issue of the initiative | `gh project create --owner <org> --title "<name>"` |
| Milestone | a repo Milestone | `gh api repos/<repo>/milestones -f title=<slug>` |
| Issue | issue of type Feature, Bug or Task, in the milestone, on the board, a sub-issue of the project's tracking issue | `gh issue create -m <slug> -p "<board>"` |

Sub-issues are linked with the GraphQL `addSubIssue` mutation (`gh api graphql`); issue types are
the org's own (commonly Task, Bug, Feature; check what the org has). **Setup:** `gh auth login`, then
`gh auth refresh -s project` (boards need the `project` scope). Create the board and the
initiative issue. Write `tracker: {"kind": "github", "owner", "project", "initiative"}`.
**Status:** the board's Status field; a merged PR with `Fixes #<n>` closes the issue; the
milestone closes when its PR merges.

## none — the repo is the plan

No tracker calls. Initiatives and projects are the design docs, milestones the change folders,
issues the `milestone.md` rows. Say once that the change has no tracker; never ask twice.

## Ids, wherever the tracker

A Linear key goes into the folder name (`changes/<date>-<KEY>-<slug>/`) and `linear:` frontmatter.
A GitHub or Beads id goes into `decisions.json` `ticket`; the folder keeps `<date>-<slug>` and
`linear: none`. Nothing that crosses into any tracker carries a local path.
