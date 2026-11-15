# Round 3 re-check

Checked 2026-11-14 against all seven spec files and `plugins/agent-tracker/hooks/tracker/core/states.ts`. Text only. Severity: 4 Critical, 3 High, 2 Medium, 1 Low. Medium and low items go to the plan.

## 1. Round-2 findings

| Finding | Status | Evidence |
|---|---|---|
| N1 batch disclosures | **fixed** | `screens.md` Words "Question, sessions" ends "Claude Code also removes a worktree it made for a session, when that is safe."; "Question, worktrees" says "Ignored files in them, such as .env, are deleted too."; "Option details": "Remove all 3: ... Ignored files in them are deleted." |
| R2-01 / R3-24 no-pid rule | **partly fixed** (residual named, listed for Stage 3) | Rule limited to blocked/done rows and to reads where some row has `pid`; self never ended; "Pid not reported" string at `screens.md` Words. The residual (a live background row with no `pid` while others have one reads ended) is named in `ia.md` Objects "Ended session" and as a Stage 3 fixture. Still wrong: `ia.md` Open Questions says the guard "stands either way" (contradicts Objects). See M1. |
| N2 live-reason wording | **fixed** | `ia.md` Decisions "Live sessions get a line" now equals `screens.md` ("Close its terminal first."; "This one is still running. Resume comes back when it ends."). Only `conformance.md` C9 still quotes the old `ia.md` string as history (Low). |
| N3 ring on Clear | **fixed** | `screens.md` Controls: "When Copy resume command is not drawn ... the ring starts on the Home crumb. The ring never starts on Clear or Remove worktree." One gap after Clear (M2). |
| N4 Before Clear | **fixed** | `screens.md` Words "Before Clear": "built from the parts that apply", with the no-`claude rm`, no-tasks and worktree-only variants. |
| N5 re-read fails | **fixed** (string drift, M3) | `interaction.md` state row "Refused, unreadable"; Clearing exits list it. |
| N6 Reopen tasks wiring | **partly fixed** | Done: state "Reopened", Action Behaviour row, Feedback row, Controls row, Elements row, `ActionItem.action` "five" values (`screens.md` Components), `sitemap.md` Move row 2. Left: `conformance.md` Component inventory still "four new values" without `reopen`; `sitemap.md` and `sitemap.json` state lists have no refused, reopened or pid-not-reported; Reopened row offers only Copy resume command though open tasks are back (see M4). |
| N7 "arrows scroll" | **fixed** | `interaction.md` Elements rows now say "↑↓ move the ring; no scroll". |
| N8 tidy entry wording | **partly fixed** | Fixed: Home Words "Count" ("counts only what tidy can act on"), "Answer, nothing" ("Nothing idle for 30 days is ready to clear."), supervisor line ("one agent each to describe it"). Left: "only when something is idle 30 days or more" in `screens.md` Home Sections row 6, `ia.md` CTA Inventory and Move Table, `sitemap.md` row 3, `sitemap.json` line 49 (Low: the Count words govern). |
| N9 offer lines | **fixed** | `interaction.md` Offer "three lines"; Layout line 2 is 62. Stale "line 2 64" in the docked row (Low). |
| N10 drift | **partly fixed** | `ia.md` Decisions uses `·` between started and last activity where `screens.md` uses two spaces; `ia.md` still says "0 to 2" batches. Low. |
| N11 tidy option resume | **fixed** | Option detail now says only "Conversations are kept." and the sessions question discloses worktree removal. |
| R1-01 confirm on Clear | **listed for the owner** | `brief.md` Open Questions row 1; `conformance.md` C2. |
| R1-02 `claude rm` removes a worktree | **listed for the owner** | `brief.md` Open Questions row 2; disclosed before and after in Words. |

## 2. New findings (all Medium or Low)

| # | Sev | Finding | Where |
|---|---|---|---|
| M1 | 2 | False claim: the Stage 3 question says the pid guard "stands either way", while `ia.md` Objects says a live background row without `pid` still reads ended. Clear on such a row would run `claude rm` on live work. Fix: say the fixture is a build gate (no Clear for background rows until it passes), drop "either way". | `ia.md` Open Questions row 4 vs Objects |
| M2 | 2 | After a good Clear with no Copy resume command, "focus goes to the first action", which is Reopen tasks; a stray Enter undoes the Clear. Start focus on the Home crumb in that case. | `interaction.md` Cleared row; `screens.md` Controls |
| M3 | 2 | State "Refused, unreadable" shows "Clear waits: Claude Code's session list could not be read. Nothing was changed." which is not a Words row; Words "List unreadable" differs (ends "Retrying every 5 seconds."). Also "Pid not reported" has a Words row but no state row, no Controls reason and no Errors row. | `interaction.md` State Tables; `screens.md` Words |
| M4 | 2 | Reopened lists only Copy resume command, but open tasks exist again so Controls draws Clear; Action Behaviour says undo is "Clear again". Exit says "Done"; diagram is `Reopened --> Done`. | `interaction.md`; `ia.md` diagram |
| M5 | 2 | Tidy rule "any item that failed a check ... is never removed by tidy, whatever the owner answers" is not true for a session batch whose `claude rm` may remove its worktree on Claude Code's own test. Disclosed in the question, but the rule should say so. | `screens.md` Transcript rules, "Batches" |
| L1 | 1 | `conformance.md` C9 and the ring "Pass" row are stale (ring now starts on the Home crumb when Copy resume is absent); Words index prose omits the Reopen tasks label. | `conformance.md`; `screens.md` Words index |

No false claim against the built code: `parseAgents` still has no `pid` field; `deriveState` maps `blocked` to needs-you and `done` to ended; `resolveState` keeps the `isSelf` branch for a session absent from the list.

## 3. New severity 3-4 findings

None.

## Verdict

**ready.** Every round-2 High is fixed or sits in the owner decisions (confirm on Clear, `claude rm` removing a worktree); the one residual safety risk (live background row without `pid`) is named and tied to a Stage 3 fixture. Take M1 to M5 into the plan, and make the fixture a gate for Clear on background rows.
