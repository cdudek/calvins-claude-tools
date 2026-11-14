---
linear: none
type: plan
change: 2026-11-13-agent-tracker
design: docs/designs/agent-tracker.md
author: Calvin Dudek
status: approved
reviewed_by: Calvin Dudek
approved_at: 2026-11-14T00:45
created: 2026-11-13
---

# Plan: Agent tracker, milestone 1

> Add a second plugin, `agent-tracker`, a Claude Code mod that draws a band above every prompt and a `/tracker` pane showing each session's repo, work and state.

A person with no context builds from this file alone. [intent](intent.md) and
[facts](facts.md) are for the gate, not for the build. The UX spec is in [spec/](spec/).

## Approach

- **What changes:** a new plugin `plugins/agent-tracker/` holds a hooks module: a collector, a backfill, a band and a pane.
- **What stays the same:** the `cct` plugin, its skills, agents and naming tests. The mod only observes and never writes to a session, git, gh or bd.
- **Why this way:** one pure TypeScript core and a thin I/O layer match the design file. Milestone 2's web page reuses the core, and no dependency is needed.
- **Prototype images:** none drawn. The UI is not marked risky. The band copies ponytail's built pattern and the pane is lists and buttons. A terminal mod cannot be mocked meaningfully as an image.
- **Check commands, verified on Claude Code 2.1.323:** `claude plugin validate --strict plugins/agent-tracker` reads the manifest. It type-checks the hooks module, its imports and the `*.test.ts` files.
- **Probe result:** an injected type error made `validate --strict` exit 1, in an imported file and in a test file. A clean tree exited 0. `claude plugin test <dir>` runs each `*.test.ts` and does not type-check.
- **Calls:** `arch-plan-write` is this plan. `review-security-run` is not needed: no auth, money or consent, only local reads and one folder written. `review-dependency-run` is not needed: no dependency is added. `tracking-apply` is not needed: the success measure is a by-hand spot check.
- **Scope, owner decision 2026-11-14:** "Keep all four (Recommended)". Milestone 1 keeps the collector, the backfill, the band and the pane. The analyze and challenge findings that asked to cut or split it are accepted on this.
- **Success measure, owner decision 2026-11-14:** "Needs-you spot checks (Recommended)". Five by-hand checks by 2026-12-04 that the band's needs-you count matches the sessions the owner sees waiting. `intent.md` holds the revision.
- **Merge, owner decision 2026-11-14:** "Edit it, you merge". The milestone PR carries the `CLAUDE.md` edit and is not auto-merged. The owner merges it. `decisions.json` records `autoMerge: false`.
- **Rejected, tsc:** `npx -y typescript@5.9.3 -p plugins/agent-tracker` needs the network and the engine's `.claude-plugin/types/`, which a clean checkout lacks. `validate --strict` already type-checks.
- **Rejected, dev dependency:** a `package.json` with typescript would be an Ask-tier dependency change (`sdlc.json` `blocked`) and buys nothing over `validate --strict`.
- **Rejected, install `claude` in CI:** it edits `.github/**`, which `boundary-map.yaml` floors at Repair, and the repo's rule is local-first. The script skips the mod checks when `CI` is set and `claude` is absent.
- **Rejected, one big file for the core:** the design says one shared module. A `core/` folder with an `index.ts` is that module. One file would pass 2,000 lines.
- **Rejected, a server or port for the store:** the design is files only, one per session, so no session waits on another.
- **Rejected, parallel features 3 and 4:** both edit `register.tsx`, the single `/tracker` command handler, `core/format.ts` and `core/words.ts`. They run in order.

## Rules check

The rules in `intent.md` → "Rules that apply", checked twice: before the design (can the approach
obey them?) and again after it (does the design?). `facts.md` names them PUB-1 (`CLAUDE.md#Public repo rule`: no
internal names, people, URLs or local paths) and PUB-2 (`CLAUDE.md#Never publish to claude.ai`).

- Before design: pass. The approach is local files, a local mod and no hosted page.
- After design: pass, with two steps that make it true. Feature 1 extends `tests/test_no_claude_ai_publishing.py`, which scans only `plugins/cct` today, to scan both plugins. Feature 1 also adds a fixture scan for `/Users/`, `/home/` and e-mail addresses to `safety.test.ts`. The repo-wide grep in `tests/test_plugin.py` only knows a fixed list of names.
- `AGENTS.md` Decision4: the `CLAUDE.md` edit makes the milestone PR a Repair change, and unattended work above Undo goes to a person. The run therefore stops with the PR open and the owner merges it. Auto-merge is never armed on it, so the rule is kept and needs no violation row.

### Justified violations

One row per rule the plan breaks. A row with an empty cell blocks the gate; `none` when clean.

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| none | | |

## Design

Arch-plan-write's checklists applied. There are no HTTP endpoints, tables or services. The interfaces are the mod's hooks, one JSON file per session, one settings file and the `/tracker` command.

### Boundaries

- **`core/`:** pure functions on plain data. No `$`, no `claude-code` value import, no file, process or clock access. Time is a parameter.
- **I/O layer:** `hooks/tracker/*.ts(x)` calls `$.process.run`, `$.fs`, `$.clock`, `$.model` and `$.ui`, and hands plain data to `core/`.
- **Dependency direction:** I/O files import `core/`; `core/` imports only itself; no I/O file imports another feature's file except through `store.ts` and the `snapshot` state value. There is no cycle.
- **How band and pane read data:** the collector merges every file into one `snapshot` value in `$.state`. The band and the pane read it, so a change redraws them and neither touches a file.
- **Single points of failure:** `claude agents --json` failing, or an `agents.json` older than 15 s, gives the stale state (F52, F123, F129), never "ended". A file that cannot be written gives a status line (F58). A file that will not parse is skipped and the last good copy stays.
- **Scaling, one poller:** a session's mod takes a lease, `poller.json`, when none is fresh (heartbeat older than 15 s). The holder runs `claude agents --json` every 5 s and writes `agents.json`. Every other session reads `agents.json`. Measured here: one call takes 0.18 s and returns 8 KB, so N open sessions cost one call every 5 seconds.
- **Per session:** each mod lists the sessions folder and re-reads only files whose `mtime` changed.
- **Lease races:** two mods may take a free lease together. The later write wins, and the other sees a fresh lease from another session on its next check and stops polling (F127).

### Hooks and commands the mod uses

| Event or command | Owner file | Facts |
|---|---|---|
| `session.start`, `session.end` | `collector.ts` | F1, F8, F58 |
| `$.clock.every` 5 s: lease check; the holder runs `claude agents --json` and writes `agents.json`; the others read it; file merge | `collector.ts` | F1, F31, F68, F127 to F129 |
| `$.clock.every` 2 min: git and gh scan, own repo only | `scan.ts` | F14, F67 |
| `$.clock.every` 1 min: redraw | `band.tsx`, `pane.tsx` | F126 |
| `prompt.submit`, `turn.complete`, `tool.call` | `asks.ts` | F15 to F21 |
| `ui.render` `AbovePrompt` | `band.tsx` | F22 to F37 |
| `ui.render` `Pane` | `pane.tsx` | F38 to F123 |
| `command.register` `tracker`, `command.run` | `register.tsx` registers; `band.tsx` handles `details`, `compact`, `copy`, `band on`, `band off`; `pane.tsx` handles none, `session`, `repo`, other words | F29, F36, F38, F59, F79, F121, F122 |
| no `classic.*` hook anywhere | none | F18 |

### Store: `~/.claude/agent-tracker/`

The only folder the mod writes (F63). Each mod writes its own `sessions/` file, plus the two lease files while it holds the lease (F130).

| Path | Writer | Content |
|---|---|---|
| `sessions/<sessionId>.json` | that session's own mod, rewritten whole | `SessionRecord` below |
| `transcripts/<sessionId>.json` | any mod, only when no `sessions/` file exists | a `SessionRecord` with `source: "transcript"` |
| `settings.json` | any mod, last write wins | `{ "v": 1, "view": "compact" \| "details", "bandHidden": boolean }` |
| `poller.json` | the mod that holds the lease | `{ "v": 1, "sessionId": string, "heartbeat": number }`, fresh under 15 s (F127) |
| `agents.json` | the mod that holds the lease, temp file then rename where `$.fs` can rename (F128) | `{ "v": 1, "readAt": number, "agents": [...] }`, the parsed list |

A `sessions/` file always wins over a `transcripts/` file for the same id. Keeping backfill in its own folder keeps the rule that one mod writes one `sessions/` file.

```ts
// core/types.ts. v is the shape tag: a reader skips a file whose v it does not know.
export const MODEL = 'haiku'              // the one model constant (F60)
type SessionRecord = {
  v: 1
  sessionId: string
  source: 'mod' | 'transcript'
  writtenAt: number                       // epoch ms
  kind: 'interactive' | 'background'
  title: string | null                    // shown "untitled session" with the folder name
  cwd: string
  repo: { path: string; name: string } | null   // null: shown as "no repo", grouped by folder
  branch: string | null                   // null: shown "detached HEAD"
  startedAt: number
  lastActivityAt: number
  endedAt: number | null
  engine: { status?: string; state?: string; waitingFor?: string | null; since: number }
  state: 'running' | 'needs-you' | 'done' | 'ended'    // derived by core/states.ts
  reason: 'permission' | 'question' | 'waiting' | 'unknown' | null
  questionFlag: { at: number } | null     // set at turn.complete, cleared at prompt.submit
  usage: { tokensIn: number; tokensOut: number; toolErrors: number; retries: number }
  asks: Ask[]                             // at most 200; each text cut at 2,000 characters
  runs: { goalSince: number | null; subagents: { id: string; name: string; status: string }[]
          background: { id: string; name: string; since: number }[] }
  milestone: { slug: string; sentence: string; features: { n: number; name: string; state: string }[] } | null
  scan: { at: number; ghOk: boolean; worktrees: { path: string; branch: string | null }[]
          prs: Pr[] } | null              // own repo only; at feeds F69 and F78
}
type Ask = { n: number; text: string; kind: 'task' | 'question' | 'not-classified'
             status: 'in-progress' | 'needs-you' | 'replied'; at: number }
type Pr = { number: number; title: string; url: string; branch: string; createdAt: string
            checks: 'pass' | 'failing' | 'running'
            review: 'approved' | 'changes' | 'requested' | 'none'
            mergeable: 'mergeable' | 'conflicts' | 'unknown' }
```

- **Size:** a record stays far under the 4 MiB read limit: 200 asks of 2,000 characters is 400 KB at most.
- **Torn reads:** the mod API has no append or atomic rename. A reader that cannot parse a file keeps its last good copy and tries again on the next poll.
- **Merge rule:** the pane takes every `sessions/` file and adds `transcripts/` files with no twin. A record is ended when its session is absent from a good `claude agents --json` read.
- **Repo scan merge:** for a repo, the scan block with the latest `at` among its sessions' files is the repo's PR state (F69, F78).
- **`claude agents --json` parser:** pinned to the 2.1.323 fields `sessionId`, `cwd`, `name`, `startedAt`, `kind`, `status`, `state`, `waitingFor`. An unknown value maps to needs you with the reason "state unknown" (F66).

## Design changes

`docs/designs/agent-tracker.md` is edited in feature 1, in the same commit series, as sections that state what is true now. Then `python3 scripts/design_index.py write`.

- **Checks:** replace `tsc -p plugins/agent-tracker` with `claude plugin validate --strict plugins/agent-tracker`, which type-checks the module and the tests.
- **Store:** name `transcripts/`, `settings.json` and the scan block inside each session file.
- **Code layout:** name `hooks/tracker/core/` as the shared pure module and list the I/O files.
- **Backfill:** remove "`claude -p --model haiku`" from the Decisions bullet on model calls. F12 says the backfill makes no model call; the constant stays for the mod's two calls.
- **Band:** the view is kept in `settings.json`, not `$.store`, so every session follows (spec `ia.md`). The Board button and the you-should-know columns are milestone 2 and 3.
- **Collector:** the design says the collector polls. One poller does it, by lease, and the other sessions read `agents.json` (F127 to F129).
- **bd scan:** removed from Work item 2. Nothing from `bd` shows in milestone 1.
- **Not changed:** no new ADR. A choice worth its reasons in a year is the store layout, and the Store section holds it.

## Where things go

The folder for every new file, so the build cannot invent a place. A file outside these folders
is `scope-growth`.

| New file or kind | Folder |
|---|---|
| Plugin manifest `plugin.json` | `plugins/agent-tracker/.claude-plugin/` |
| Plugin README | `plugins/agent-tracker/` |
| Hooks manifest `tracker-hooks.json` (not the default name `hooks.json`, as the ponytail mod does with `claude-band.json`) | `plugins/agent-tracker/hooks/` |
| Hooks module `register.tsx`, `types.d.ts` (augments `PluginState` with the `snapshot` value, listed as `types` in `plugin.json`) and the I/O files (`store`, `collector`, `asks`, `backfill`, `scan`, `band`, `pane`) | `plugins/agent-tracker/hooks/tracker/` |
| Pane pages (`home`, `session`, `repo`, `chrome`) | `plugins/agent-tracker/hooks/tracker/pane/` |
| Pure core (`types`, `states`, `usage`, `repo`, `milestone`, `transcript`, `git`, `format`, `words`, `rank`, `band-model`, `pane-model`, `match`, `markdown`, `index`) | `plugins/agent-tracker/hooks/tracker/core/` |
| Mod tests `collector`, `asks`, `safety`, `backfill`, `scans`, `band`, `pane` as `*.test.ts` | `plugins/agent-tracker/tests/` |
| Fixtures: agents lists, transcripts, git and gh output, a `milestone.md` | `plugins/agent-tracker/tests/fixtures/` |
| Repo tests (layout, publishing scan, script runner) | `tests/` |
| Open questions and the defaults taken | `changes/2026-11-13-agent-tracker/questions.md` |

## Feature PRs

In order, grouped under `### Milestone <n> — <what a user can do after it>`. One go (the
default): each row is a commit on `milestone/<slug>-<n>` with touched tests and required pre-commit checks between rows; each
milestone gets the checks and validation once, and one PR that releases it. For E2E, run
the full suite once, ×3 only for changed and flaky specs. Use the committed
`e2e/flaky-specs.txt` list per `cct:test-e2e-policy`, `suite-speed-and-reliability.md`
section G (selection and line format). `delivery: "feature-prs"`: each row is one PR into
`milestone/<slug>` (a hotfix: into the default branch), the next starts when it auto-merges.

This repo has no browser E2E. The tests are `*.test.ts` files run by `claude plugin test`, and `e2e/` does not exist. Each fact is owned by one row. Where a fact spans two rows, the row where its named check first fully passes owns it, and the earlier row builds its half.

### Milestone 1 — see every session, what needs me, and dig in, from any session

| # | Feature | Facts | Branch | State |
|---|---|---|---|---|
| 0 | Sync: `git fetch origin && git merge origin/main`, locally; again before the close | none | `milestone/agent-tracker-1` | todo |
| 1 | Collector, asks, safety guards and the repo wiring that lets a second plugin pass the tests | F1-F11, F15-F21, F56-F58, F60-F66, F68, F71-F75, F127-F130, F132 | `agent-tracker/1-collector` | todo |
| 2 | Backfill from transcripts, and the git and gh scans | F12-F14, F55, F67, F69, F70 | `agent-tracker/2-backfill-scans` | todo |
| 3 | Band: compact and details views, Copy and Pane buttons, header, `/tracker` band commands | F22-F37, F52, F76-F87, F125 | `agent-tracker/3-band` | todo |
| 4 | Pane: Home, Session and Repo pages, `/tracker` page commands, stale and loading states | F38-F51, F53, F54, F59, F88-F124, F126, F131 | `agent-tracker/4-pane` | todo |

Counts: 39, 7, 30 and 56 facts, 132 in all. Each of F1 to F132 appears in exactly one row. Shared facts: F53 (loading), F54 (no gh), F124 (word beside every glyph) and F126 (one-minute redraw) cover band and pane, so row 4 owns them. Row 3 builds the band half and tags its tests with the same `@F` ids. F54 has a third half: row 2 builds the gh-missing result (`scans.test.ts`), row 3 the dropped PR segment, row 4 the "PRs not shown" copy.

Row 1 holds F60 to F65 because the model calls live there. Its `safety.test.ts` scans the whole plugin folder. It records every `$.model`, `$.process.run`, `$.fs.write` and listener call a scripted session makes. Rows 2 to 4 are covered without editing it. A later row adds its own calls to the scenarios.

## Files that change

| File | Change |
|------|--------|
| `plugins/agent-tracker/.claude-plugin/plugin.json` | new: name, version, description, `author`, `hooks: ["./hooks/tracker-hooks.json"]`, `types: "./hooks/tracker/types.d.ts"` |
| `plugins/agent-tracker/hooks/tracker-hooks.json` | new: `{"hooks": {}, "modules": ["./tracker/register.tsx"]}` |
| `plugins/agent-tracker/README.md` | new: what it shows, install line, Claude Code 2.1.323 and early-access note, `haiku` is an alias that can move to a newer model, `/tracker band on` brings a hidden band back |
| `plugins/agent-tracker/hooks/tracker/**` | new: hooks module, `types.d.ts`, I/O files, pane pages, `core/` |
| `plugins/agent-tracker/tests/**` | new: seven `*.test.ts` files and fixtures |
| `.claude-plugin/marketplace.json` | add the `agent-tracker` entry, source `./plugins/agent-tracker` |
| `CLAUDE.md` | replace the "One Claude Code plugin" line with two plugins; add the two mod checks under Checks. Keep the `docs/sdlc.md` reference: `tests/test_sdlc.py` asserts it. The owner merges this PR (Repair) |
| `README.md` | lines 3 and 5 say "one Claude Code plugin" and "one plugin": name both; line 71 names `plugins/cct/` as the source of truth: add the tracker; add `claude plugin install agent-tracker@cct` |
| `scripts/run-plugin-tests.sh` | after the `cct` loop, run `claude plugin validate --strict` and `claude plugin test` on `plugins/agent-tracker` |
| `tests/test_plugin_test_runner.py` | add cases for the mod block with a stub `claude` on `PATH` |
| `tests/test_no_claude_ai_publishing.py` | scan `plugins/agent-tracker` whole (skills, agents, hooks, tests and README), not only the folders it scans in `cct` (F65). The decision-page test stays on `cct` |
| `tests/test_agent_tracker_layout.py` | new: `core/` imports no I/O, no file registers a `classic.*` hook |
| `docs/designs/agent-tracker.md` | the Design changes above |
| `docs/ux/setup.md` | one Safety line naming the clipboard and `settings.json` as the allowed outputs (validation r1 R22) |
| `changes/2026-11-13-agent-tracker/{milestone,questions,findings,validation}.md` | records |

`scripts/run-plugin-tests.sh` details, so the existing tests and CI keep passing:

- **Block runs only if `plugins/agent-tracker` exists.** `tests/test_plugin_test_runner.py` copies the script into a temp root without it.
- **A pass prints** `ok   agent-tracker: validate` and `ok   agent-tracker: test`, and nothing else. A failure prints the command output and exits 1.
- **No `claude` on `PATH`:** with `CI` set, print `skip agent-tracker: claude CLI not found` and carry on; otherwise print `FAIL` and exit 1. GitHub's runner sets `CI`, and the local gate has `claude`.
- **`.claude-plugin/marketplace.json`:** also run `claude plugin validate .claude-plugin/marketplace.json` inside the same block.

`tests/test_session_drift_hook.py` mentions the marketplace by name only; the builder reads it once to confirm it assumes no single plugin.

## Order of work

Each step has a proof. The proof is a command, a file, or a fact. After each step the builder
runs `claude plugin validate --strict plugins/agent-tracker`, `claude plugin test plugins/agent-tracker`
and `python3 -m unittest discover -s tests`, then commits with a Conventional Commit subject.

- [x] 0. Sync the milestone branch with `origin/main`. Proof: `git merge-base --is-ancestor origin/main HEAD` exits 0.
- [x] 1. Feature 1, wiring: manifest, `tracker-hooks.json`, empty `register.tsx`, marketplace, READMEs, `CLAUDE.md`, the script block, the three Python tests. Proof: `scripts/run-plugin-tests.sh` prints both `ok   agent-tracker` lines.
- [x] 2. Feature 1, design edits and the `docs/ux/setup.md` line. Proof: `python3 scripts/design_index.py write` leaves `git diff --stat docs/designs/INDEX.md` empty.
- [x] 3. Feature 1, fixtures: a scrubbed `claude agents --json` list. If a session is waiting when the builder runs this step, also record its `waitingFor` value for F4. If none waits, record nothing, test F4 with the documented default ("waiting"; "asks permission" never shows) and log that to `questions.md`. Proof: `git grep -nE '/Users/|/home/' plugins/agent-tracker/tests/fixtures` prints nothing.
- [x] 4. Feature 1, tests first, then `core/` types, states, usage, repo and milestone, then `store.ts` and `collector.ts`. Proof: F1 to F11, F21, F58, F66, F68, F71 and F127 to F129 pass in `collector.test.ts`.
- [x] 5. Feature 1, tests first, then `asks.ts` with the single model helper. Proof: F15 to F20, F56, F57, F72 to F75 and F132 pass in `asks.test.ts`. F21 is proved in `collector.test.ts` (step 4).
- [x] 6. Feature 1, `safety.test.ts` over the whole plugin. Proof: F60 to F63 and F130 pass in `safety.test.ts`. F64 and F65 pass when the extended `tests/test_no_claude_ai_publishing.py` and the fixture scan in `safety.test.ts` both pass.
- [x] 7. Feature 2, tests first, then `core/transcript.ts` and `backfill.ts`. Proof: F12, F13, F55 and F70 pass in `backfill.test.ts`.
- [x] 8. Feature 2, tests first, then `core/git.ts` and `scan.ts`. Proof: F14, F67 and F69 pass in `scans.test.ts`.
- [x] 9. Feature 3, compact band: `core/format.ts`, `words.ts`, `rank.ts`, `band-model.ts`, `band.tsx`. Proof: F22 to F32, F52, F76 to F78 and F125 pass in `band.test.ts`.
- [x] 10. Feature 3, details view, Copy, `/tracker` band commands. Proof: F33 to F37 and F79 to F87 pass.
- [x] 11. Feature 4, pane shell and Home: `pane.tsx`, `pane/home.tsx`, `pane-model.ts`. Proof: F38 to F45, F53, F54, F88 to F102, F123, F124, F126 and F131 pass in `pane.test.ts`.
- [x] 12. Feature 4, Session page. Proof: F46 to F49 and F103 to F113 pass.
- [x] 13. Feature 4, Repo page and `/tracker repo`, `/tracker session`. Proof: F50, F51, F59 and F114 to F122 pass.
- [ ] 14. Sync again, then hand the close to one `Mode: close` builder. Proof: `python3 scripts/verify_gate.py milestone 2026-11-13-agent-tracker` ends `VERIFY PASS milestone`.

## Milestones

One row per milestone, in order; a change small enough for one has one. Each milestone is cut
from the default branch and merges on its own, unless `needs` names one whose code it calls.
Different files do not prove independence: an API and its caller conflict without a merge
conflict.

| Milestone | Features | needs |
|-----------|----------|-------|
| M1 agent-tracker-1: the band and the pane | rows 0 to 4, F1 to F132 | none |

## Risks

Validation findings from `spec/validation.md` are cited by review file and id. Findings the facts already close are listed in the last row of the group.

| Risk | What we do | Where it lands |
|------|------------|----------------|
| Session title may not match its Claude Code tab (r1 R2). The band names a session by `name` from `claude agents --json`, and that may differ from the tab. | The row also shows repo and branch (F40). The facts claim no tab match. Check by hand once in two live sessions. | Step 11, manual check |
| Classic hooks are skipped on managed machines. | The question check runs at `turn.complete` and reads the transcript (F17, F18). Wake-ups are out of scope. A layout test greps for `classic.`. | Step 5, `test_agent_tracker_layout.py` |
| The haiku question check runs only in sessions with the mod. A session without it stays done after a question (F20). | Accepted, the owner's answer. Documented in the README. Home shows how many sessions run without the tracker (F131), so the gap is visible (H6). | Step 11, F131 |
| The question check could cost a model call at every turn end (H7). | The check runs only when the last message's final paragraph holds a "?" (F17, F132). Ask classification at `prompt.submit` stays: the owner asked for it. | Step 5, F132, F61 |
| `waitingFor` content is unverified: a permission prompt against a question (analyze X2, challenge H5). | At step 3 the builder records a `waitingFor` value if any session is waiting then. If none is, F4 is tested with the documented default ("waiting"; "asks permission" never shows) and the build logs it to `questions.md`. F4's check line says both. | Step 3, F4 |
| `claude agents --json` may change shape between Claude Code versions. | Parser pinned to the 2.1.323 fields; an unknown value shows as needs you, "state unknown" (F66), so a changed engine cannot hide a waiting session; a failed or unparseable read is Stale, never "ended" (H5). | Step 4, F66, F52 |
| gh rate limits and gh failure. | One scan per 2 minutes, own repo only (F67). On failure keep the last scan and show Partial (F54). | Step 8, F67 |
| A transcript over 4 MiB cannot be read whole. | Search with `grep` through `$.process.run` and take the prompt, usage and error lines (F13). The test stubs the size and commits no big file. | Step 7, F13 |
| Polling cost: every session running `claude agents --json` every 5 seconds (challenge H4). | One poller by lease (F127 to F129). The holder polls and writes `agents.json`; the others read it. Other sessions re-read only files whose `mtime` changed. A dead holder is replaced after 15 s. | Step 4, F127 to F129 |
| Two sessions write `settings.json` or the same `transcripts/` file at once. | Last write wins, and the content is identical for backfill. A torn read keeps the last good copy. | Step 4, F8, F68 |
| `$.fs` offers no append and may offer no rename, so a reader can see half a file. | `agents.json` is written by temp file and rename where the API has rename (F128). Else, and for other files, a reader skips an unparseable file this poll and keeps its last good copy. The builder checks for rename at step 4 and logs the result in `questions.md`. | Step 4, F68, F128 |
| The mod API is early access and moves between releases. | The README names Claude Code 2.1.323. `validate --strict` runs in the local gate. | Step 1 |
| GitHub CI has no `claude` CLI, so it cannot run the mod checks. | The script prints a skip line when `CI` is set. The local gate, which has `claude`, proves the mod. CI stays confirmation only. | Step 1, runner test |
| The milestone PR changes `CLAUDE.md`, which `boundary-map.yaml` floors at Repair. `AGENTS.md` hands unattended work above Undo to a person (analyze X1). | Owner decision 2026-11-14, "Edit it, you merge": the PR is Repair with a decision record, auto-merge is never armed (`decisions.json` `autoMerge: false`), and the owner merges. `sdlc_status.py goal` reads `DONE` only for a PR that is merged or open with auto-merge armed. Until the owner merges it prints `GOAL <id> OPEN pr-<n>-not-merged-or-armed`. The goal below therefore ends on that line, with nothing else missing. | Step 14, Publish |
| Re-sort under focus, no cap, narrow rows, arrows, ask-text limits, `/tracker` matching, duration format, Copy content (r1 R4, R5, R6, R10, R19, R20; r2 R2-01, R2-08, R2-11; r3 severity 3). | Closed by facts, not risks: F43, F41, F110, F122, F125, F85, F92, F99, F100. | Those facts |
| Hotkeys and the keyboard ring are not visible (r1 R9, r2 R2-13). A non-plain `Button` draws `[ label ]` with no letter. | Spec wording wins. Not added: a hint string, a letter in the label. Deferred to a later change. | Deferred |
| A hidden band leaves no on-screen way back; counts are inert (r1 R8, r3). | Not in the facts. Deferred. The details view is unchanged; `/tracker band on` is in the README. | Deferred |
| Identity fallbacks: untitled session, no repo, detached HEAD (r1 R12). | Show "untitled session" with the folder name, "no repo" grouped by folder, "detached HEAD". Default logged in `questions.md`. | Step 4, F7, F10 |
| `/tracker` with an unknown word (r1 R10). | Show one line: "Try /tracker, details, compact, copy, repo, session, band on, band off." Default logged. | Step 13 |
| Asks are unbounded in the list (r1 R7, r2 R2-16). | Store 200 asks, text cut at 2,000 characters; the page shows all, each cut at 4 lines (F110). No "more" button. | Accepted, F110 |
| Plain buttons look like static rows; dim means six things; two glyph meanings (r2 R2-03, R2-17, r1 R18). | Every glyph has a word or count (F124). No new styles. | Step 11, F124 |
| One state for pending, failed and transcript asks: "not classified" (r2 R2-06, r1 R14). | Accepted: the kind word stays "not classified" (F57). | Accepted, F57 |
| `waitingFor` shown raw and unbounded (r2 R2-19). A session absent from the list is "ended" and enables Copy resume (r2 R2-20). | Only a fixed list of reasons shows (F4). Ended needs a good read of the list. | Step 4, F4, F6 |
| One machine-wide view changes band height in every session; the details view can reach ten rows beside ponytail's (r1 R16, r1 R17, r2 R2-09). | Accepted. The narrow rule folds the columns (F83). | Accepted, F83 |
| Duplicate entries and names: three names, repeated repo and milestone, Back beside Home, Copy resume placement (r2 R2-02, R2-14, R2-15). | The owner kept the names. Accepted. | Accepted |
| Escape may collide with Claude Code's own double Escape (r1 R15). | Close and `ctrl+x x` stay the main routes. Check Escape in a real session. | Step 11, F92 |
| J10 pushed attention rests on an unverified premise: Claude Code notifies itself (r1 R21). | The band is passive. The spot check reads whether it is missed. | Accepted |
| The band counts every open PR of repos with sessions, so a team repo adds other people's PRs (r1 R11). | F78 fixes the scope. Revisit by the outcome. | Accepted, F78 |
| A feature row holds 56 facts (row 4) and 39 (row 1), under a 150-turn cap (analyze X9, challenge H2, H3, H8). | Owner decision 2026-11-14, "Keep all four (Recommended)": accepted. Steps split each row by page and by module; each step is a commit with its own proof. The per-step turn use is not measured. At 150 turns the run reports what is missing and resumes from the branch. | Accepted, steps 4 to 13 |
| The recorded `waitingFor` fixture or any fixture holds a path, name or e-mail address. | Scrub before commit. `safety.test.ts` fails on `/Users/`, `/home/` and `@` addresses. | Step 3, F64 |
| A failed `gh` drops the band's PR segment, so no "1 ✗" reads as healthy (r1 R13, F54). | The pane shows the "PRs not shown" line. The band stays quiet in milestone 1. | Deferred to a later change |
| Errors, retries and tokens have no reference such as a share of tool calls (r2 R2-05). | The page shows the raw numbers (F21, F106). J4 reads as "see the numbers". | Accepted |
| Two waiting sessions can look alike, and the session id that `/tracker session` accepts is shown nowhere (r2 R2-07). | F40 shows the branch and F122 defines the match. The id on the Session page is not added. | Deferred to a later change |
| Copy failed is a toast the owner may miss (r2 R2-18, F86). | Accepted. The toast text names the retry. | Accepted, F86 |
| Design choices to confirm at the gate: Home reopens on Home, the owner finds the terminal by hand, Needs you is flat and Running is grouped (r2 R2-22). | The facts carry them as written. The owner confirms them at the gate. | Gate |
| Store files are never deleted: an ended session's file stays and every poll lists it (challenge M2). | Readers show only the last 7 days and re-read changed files only. Retention is not built. | Deferred to milestone 2 |
| The view and the hidden flag sit in one `settings.json` for every session, last write wins (challenge M3). | The file is tiny and a torn read keeps the last good copy. The spec wants one view for all. | Accepted, F22 |
| A repo's PR count on the band can be old, and a team repo adds others' PRs (challenge M4). | The Repo page shows the age (F69). The band does not. | Accepted, F78 |

## Out of scope

- The web page and the Board button belong to milestone 2.
- "You should know" and "decided without you" items, plan progress, ticket links and superseded tasks belong to milestone 3.
- Anything from `bd` on screen, and any `bd` call. The design's `bd` scan is removed from milestone 1.
- Notifications, sound and toasts when a session waits; scheduled wake-ups.
- Any write to a session, agent, task, worktree, git, gh or repo.
- The project name in the band header, and a milestone view on the Repo page.
- A `tsc` or `package.json` toolchain, and CI changes.

## Done

What must hold, as data in [done.json](done.json) (facts, test tags, pages, states). The goal
below ends on the status line of `sdlc_status.py goal`, which reads the verify gate and the PRs,
so every line here is proven by a check, not by a claim. It ends when the milestone PR is open with `VERIFY PASS` and waits for the owner's merge.

- `python3 scripts/verify_gate.py milestone 2026-11-13-agent-tracker` ends `VERIFY PASS milestone`, once, on the milestone.
- `scripts/run-plugin-tests.sh` prints `ok   agent-tracker: validate` and `ok   agent-tracker: test`.
- F1 to F132 are met by their named checks, and `changes/2026-11-13-agent-tracker/validation.md` records each as met.
- `plugins/agent-tracker/` holds the files in `## Where things go`, and `CLAUDE.md` names two plugins.
- `git grep -nE '/Users/|/home/' plugins/agent-tracker/tests/fixtures` prints nothing.
- One push and one PR from `milestone/agent-tracker-1`, open, not auto-merged: the owner merges it (`decisions.json` `autoMerge: false`). The body is Decision4 Repair with a decision record.
- Nothing outside `## Files that change` is edited.
- Stop and report as soon as a step cannot proceed. Never work around a blocker.
- Stop after 150 turns if not met. Report what is missing.

## How to run

The process of the build. The `/goal` below holds only the end state; everything the run does
lives here, in the skill's stages and in the hooks. Read the [local-first
contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md)
before any check or push: it owns local iteration, failures and the final full gate.

- **Scope:** deliver this change in one go, per this plan and `facts.md`.
- **Milestones:** every row of `## Milestones`, in order. Each one is a local branch
  `milestone/<slug>-<n>`, cut from fresh `origin/<parent>`. `<parent>` is `project/<slug>` when
  the project has a branch, else `<default>`. A milestone with `needs:` is cut from that local
  milestone instead. Building never waits for a merge. Nothing is pushed before its gate passes.
- **Sync:** the first row of a milestone is a local `git fetch origin && git merge
  origin/<default>` (also `git merge origin/project/<slug>` when the project has a branch).
  Repeat it right before each close, and after any earlier milestone merges. It is never a PR.
  The milestone gate fails `check=parent-sync` without it. The merge may run in the supervisor's
  worktree.
- **Features:** write the tests for the feature's facts, build in the folders of `## Where things
  go`, commit. Between features run the touched tests, their directly affected suite and the
  required pre-commit checks, then start the next feature at once.
- **Order here:** rows 1, 2, 3, 4, one builder at a time, each cut from the milestone head with `Base: <sha>`. No parallel builders: rows 3 and 4 share files.
- **Checks here:** `claude plugin validate --strict plugins/agent-tracker`, `claude plugin test plugins/agent-tracker`, then `python3 -m unittest discover -s tests && scripts/run-plugin-tests.sh`. `claude plugin test` runs a whole folder, so a "touched test" means the whole mod suite.
- **Builders:** feature builds and fix parts go to `cct:sdlc-feature-builder` agents. Each prompt
  carries a context pack: the feature's facts, its plan excerpt and the text of the rule IDs
  those facts cite, not whole files. Dispatch with isolation `worktree` and a `Base: <milestone
  head sha>` line after you commit your records. Merge their branches back one at a time. When
  `sdlc.json` `builders` is `codex`, use the kit's `scripts/codex-build.sh` instead; with codex
  the close builder runs checks and the gate only. Either way use `builderModel` and
  `builderEffort`, or the pair this plan's Approach names (`stages.md`).
- **Records:** plans, handover, findings, validation, gate output and every fix or test repair are
  commits on the milestone branch. Open no other PR and push nothing else (`pr-gate.sh` refuses
  it). A record that can only be written after a merge goes in the next milestone's first commit.
- **Questions:** an open question never stops the build. Write it to `questions.md` with the
  default you took, tell the engineer in one line, and carry on.
- **Close:** once a milestone's features are committed, hand its local pipeline to one
  `cct:sdlc-feature-builder` subagent with `Mode: close` and the head it runs on. It spawns no
  agents and nothing merges into the milestone while it runs. It runs the unit tests, the full
  E2E suite once (changed and flaky specs ×3, the committed `e2e/flaky-specs.txt` per
  `cct:test-e2e-policy`, `suite-speed-and-reliability.md` section G), the one fix round on the
  blocking findings, then `python3 scripts/verify_gate.py milestone 2026-11-13-agent-tracker`. Its full output
  is pasted. Here there is no E2E suite: the unit and mod tests are the whole gate.
- **Meanwhile:** dispatch the Stage 6 reviews on the milestone diff in parallel. Validate every
  fact and ask of the milestone against the built app into `validation.md` (expected, observed,
  evidence, verdict). Run the append-only converge pass from `quality-passes.md` into
  `findings.md` (ticked boxes are not evidence; repeat after the fix round until it adds nothing
  and writes `Converged: round <n>`). Write one `findings.md` section for the subagent's fix
  round. Keep building the next milestone where it does not depend on this one.
- **Publish:** only on `VERIFY PASS milestone 2026-11-13-agent-tracker <sha>` with `<sha>` equal to the local
  head: one push, one PR `milestone/<slug>-<n>` to its parent. Do not arm auto-merge on this
  PR: `decisions.json` says `autoMerge: false`, owner, 2026-11-14, "Edit it, you merge". The PR edits `CLAUDE.md`, so its body is Decision4 Repair, with recovery steps and a decision
  record, and the run stops with the PR open for the owner to merge. Ask first when a Critical or High is deferred. A
  milestone that needs another opens its PR after that one merges.
- **Red CI:** CI is the last check, not the test loop. Read the exact failed job or test and its
  reason, reproduce it locally, fix it, then run only the failing tests plus the directly affected
  suite until green, the full local gate once, and one batched push. Never a pipeline retry or a
  speculative push.
- **Scope the owner adds:** it re-locks (`verify_gate.py approve 2026-11-13-agent-tracker`) and gets one more
  close. Log it under `## Revisions`.
- **Blocked:** on `VERIFY BLOCKED`, stop and summarize `verify/report.md` for the engineer. Never
  edit protected paths (`facts.md`, `done.json`, `lock.json`, baselines, allowlists, `sdlc.json`
  `checks`) or accept baselines.
- **Bookkeeping:** tick plan tasks as they land. Log departures under `## Revisions`.
- **Agents:** every build, fix, test, capture, restack or records agent is
  `cct:sdlc-feature-builder` (Sonnet). Review and checks use their typed agents
  (`cct:review-code-reviewer`, `cct:test-behavior-verifier`, `cct:review-criteria-auditor`,
  `cct:ux-usability-reviewer`, `cct:review-finding-validator`). Never launch general-purpose for
  this work: it inherits the session's model. Any other subagent gets `model: sonnet` explicitly.
  The session's own model is only for the gate's visual judgement and for decisions. Dispatch
  builders yourself, never through a closer agent that spawns its own.
- **One milestone** (`/goal` from `templates/goal/milestone.txt`): close it per `milestone.md`.
  Sync first, one fix round, diagnose locally with failing tests and affected suites until green,
  then the full local gate once before the push: unit, E2E (changed and flaky specs ×3) and
  `python3 scripts/verify_gate.py milestone 2026-11-13-agent-tracker`, output pasted. Then one push and PR. Records and
  repairs are commits there, never separate PRs.
- **Feature PRs** (`delivery: "feature-prs"`): not used here; `sdlc.json` says `one-go`.

## Goal handover

Two blocks, committed verbatim, so the handover is not one chat message. The kickoff prompt tells
the run what to do. The `/goal` line holds only the end state. This milestone PR is not auto-merged (the owner merges it), so `sdlc_status.py goal` cannot print `DONE` before that merge. The end state is the PR open with `VERIFY PASS`: the status line `GOAL <ID> OPEN pr-<n>-not-merged-or-armed` with no other missing item. The run also stops on `BLOCKED` and after 150 turns (`goal.runTurns`).

Kickoff prompt:

```
Run change 2026-11-13-agent-tracker: follow `## How to run` in changes/2026-11-13-agent-tracker/plan.md to the end, then
print `python3 scripts/sdlc_status.py goal 2026-11-13-agent-tracker`.
```

The goal:

```
/goal `python3 scripts/sdlc_status.py goal 2026-11-13-agent-tracker` printed `GOAL 2026-11-13-agent-tracker DONE`, or `GOAL 2026-11-13-agent-tracker BLOCKED`, or `GOAL 2026-11-13-agent-tracker OPEN pr-<n>-not-merged-or-armed` with no other item after it, as its last run in this conversation, or stop after 150 turns.
```

## Revisions

Only after approval. One line per change: `YYYY-MM-DD — what changed, and why`.

Verification follows the [local-first contract](https://github.com/cdudek/calvins-claude-tools/blob/main/plugins/cct/skills/sdlc-run/references/local-first.md).
