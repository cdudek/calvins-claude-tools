---
type: ux-rules-validate
mode: sdlc
change: 2026-11-13-agent-tracker
spec: brief, ia, interaction, screens (no prototype images)
created: 2026-11-13
---

# Conformance

Text-only check. No prototype images exist (the screenshot recipes in `docs/ux/setup.md` are BLOCKED until the mod is built), so no visual pass ran and nothing here is "seen on screen". Every row is read from the four spec files and the repo.

**Documents.** Found: `docs/ux/setup.md`; `docs/ux/interaction-guidelines.md` (every rule `unresolved` or not applicable, none accepted); `docs/ux/exceptions.md` (empty); `docs/ux/glossary-proposal.md` (empty table); `docs/ux/sitemap.md` and the change's `spec/sitemap.md`; `docs/designs/agent-tracker.md` (the owner's recorded decisions); the shared `writing.md`; the owner's words in `docs/ux/owner-words.md`. Missing: a glossary (the alias table in `ia.md` is a proposal), a design system (setup.md says none), `PRODUCT.md`, any accepted `ux` ADR (`docs/designs/INDEX.md` lists none), a component catalogue, a screen-goals file (`ia.md` stands in).

**What that stops.** No rule check can come back "conforms to rule X": there is no accepted rule, so every row below is "no accepted rule" plus the spec's proposed default, or a departure from the spec's own text, `setup.md`'s hard rules, or `writing.md`. No glossary check ran against accepted terms; the alias table was checked for consistency only. No token check ran: there are no tokens, only Claude Code's theme colour names.

## Interaction model

Rule column: the area from `rule-areas.md`. Result "no accepted rule" means the spec's proposed default stands until the owner accepts a rule.

| Screen or state | Rule | Result | Change or proposed rule |
|---|---|---|---|
| Band compact and details, view button | Remembered state | No accepted rule. Scope unspecified: `ia.md` says "per machine", `interaction.md` says "across sessions", the store's real scope is unverified. Whether a toggle in one session redraws every other open band is not said. | Proposed rule: the view is one value per machine and every open band follows it within one refresh. Check `$.store` scope at build (F013). |
| Band, view button, double-click | Lists and selection | Differs from Pane button, which is idempotent: a double-click on Details ends where it started. | Listed under Deliberate inconsistencies. |
| Band, hotkeys `d` `p` `c` and pane hotkeys `b` `h` `x` | Keyboard and focus | Departure: the spec says digit hotkeys are avoided because "a bare digit in an empty prompt would press them", which says hotkeys fire from the prompt. Letters would then fire on the first letter typed. If hotkeys fire only with the band focused, the digit reason is moot. | F001. Proposed rule: hotkeys act only while the band or pane holds the keyboard; say so in the spec. |
| Band and pane, Escape | Keyboard and focus | Escape means "hand the keyboard back" in the band and "close the pane" at an empty prompt. Order is not stated when the ring is focused inside an open pane. | F012. Proposed rule: Escape goes one step up: ring to prompt, then pane closed. |
| Band compact, oldest waiting session | Lists and selection, Navigation and return | The most frequent job (J1) ends with a name and no route to that session; the sitemap's "Copy resume command" has no control in screens or the CTA inventory. | F005. |
| Band, this session counted in its own band | Feedback and notifications | No rule: the band in the session that itself waits may name that session as the oldest waiting one. | F008. |
| Band, Pane button, pane opens | Side panels and detail pages | Move Table and sitemap: always `home`. Action Behaviour and Open Question 2: reopens on the page it was closed on. | F006. Owner decides. |
| Band error vs pane error | Connection to external systems | Departure: band drops its counts on error, pane keeps the last good list dim. `interaction.md` Errors says the band "shows the last read and its age". | F007. |
| Pane Home, session row, repo heading | Lists and selection | Conforms to the proposed default: one focused row, Enter opens, Tab and arrows move. Repo pages are not reachable from Home for every repo. | F009. |
| Pane Back, Home, Close | Navigation and return | Conforms: history-based Back, row and scroll restored, Close keeps place. The breadcrumb is text while a repo button beside it does the work. | F004. |
| Pane Repo, PR number link | Navigation and return | No accepted rule for leaving the app to the browser. Spec states Enter opens it. | Proposed rule: a link that leaves the tracker is a `Link`, says "opens GitHub" in its label when width allows. Low; fold into guidelines. |
| Copy, toast | Feedback and notifications, Copy and paste | Conforms to the proposed default: toast carries nothing needed later; failure toast names the reason. | none |
| Store write failure | Feedback and notifications | Status line text has no consequence and no action. | F014. |
| All actions | Confirmation and undo | Conforms: nothing is written outside the tracker's own folder, so nothing needs confirming or undoing. Observe-only holds in every row; no control writes to a session. | none |
| All screens | Drag and drop, Media, Forms | Not applicable, per the guidelines. | none |

## Design system

No design system exists, so there are no tokens or shared components to check against (setup.md: "none"). Checked against what exists: Claude Code's theme colour names and its mod components.

| Area | Departure | Impact | Fix |
|---|---|---|---|
| Colour | None. Only `success`, `warning`, `error`, `suggestion`, `inactive` and dim are used; no literal values. Colour never carries meaning alone: each glyph sits beside a word or a count. | none | none |
| Components | `Link` is used for the PR number (Pane Repo, Session) but `setup.md` lists only `Box`, `Text`, `Button`, `Svg`, and no installed public mod calls a `Link`. It is not shown to exist. | Medium if it does not exist: PRs cannot open from the pane. | Confirm against the mod types at build; if absent, use a `Button` that runs `open`. Add `Link` to `setup.md`'s component list (F015). |
| Components | `Button` with `hotkey` exists in a public official mod (digits and one letter), and `plain`, `label`, `variant`, `onPress` exist in the ponytail band. Whether letter hotkeys fire only under focus is not shown anywhere. | See F001. | Read the mod types before the first build step. |
| Type and spacing | Terminal cells only; no type scale to depart from. Widths in the spec do not add up at 100 % (see F002). | Medium | Compute the budget; apply the drop order at every width. |
| Density | The compact band packs five segments and two buttons in one row. | see F002 | as above |
| Dim style | The needs-you column's dim line holds the oldest waiting session, the one fact J1 exists for, in the lowest-emphasis style. Contrast is not measured; WCAG scope is proposed R2, not accepted. | Low | Give it the normal colour (F010). |

## Component inventory

Callers searched in this repo (`$.ui`, `bodyColumns`, `Button`, `Box` over the tree, excluding `changes/` and `.git`): the only hits are two design documents. `plugins/agent-tracker/` does not exist, so every tracker component has **0 callers** and nothing on another screen changes. External reference callers were read in the installed public plugins: the ponytail band (`hooks/band/register.tsx`, `metrics.ts`) and the official `code-modernization` mod (`hooks/views/deck.tsx`, `pane.tsx`, `register.ts`).

| Component | Status | Where the spec uses it | Callers today | Implication for other screens | Variant or new spec |
|---|---|---|---|---|---|
| `Box` | have | every screen | 0 in repo; ponytail `register.tsx` (row, column, `flexGrow`, `gap`, `width`) | none | none |
| `Text` | have | every screen (bold, dim, colour, `wrap="truncate-end"`) | 0 in repo; ponytail `register.tsx` | none | none |
| `Button`, `plain`, `label`, `onPress` | have | band, pane controls | 0 in repo; ponytail `register.tsx` (`plain`, `label`, `variant`) | none | none |
| `Button` with `hotkey` | have (prop seen), behaviour unverified | band and pane hotkeys | 0 in repo; `code-modernization/hooks/views/deck.tsx` (digits), `pane.tsx` (`m`) | If hotkeys fire from the prompt, every letter key in this spec is unusable (F001). | none, but verify |
| `Link` | unverified | Pane Repo and Session (PR number) | 0 in repo; none found in any installed public mod | If absent, J11's "open the PR" has no control. | check types; else Button |
| `Svg` with `alt` | have | band details on desktop | 0 in repo; ponytail `register.tsx` via `metricsSvg` (`metrics.ts`) | none | new variant (columns) |
| Columns, terminal | new variant | band details | 0; ponytail builds the same four-column Box inline | A second copy of ponytail's column code; the two cannot share it (a plugin cannot read another plugin's files). | Props: `label`, `value`, `sub`, `tone`. States: normal, empty (0, no sub line), narrow (no sub line), fold to two rows. |
| Columns, desktop | new variant | band details, desktop | 0; ponytail `metricsSvg` | as above | Props: columns array, width. States: as above; `alt` lists every label and value. |
| Session row (`Button` with `Text` children) | new variant | Home, Repo | 0 | Home and Repo must stay identical | Props: state glyph, title, meta (repo or branch, time, tokens, errors, retries), `onPress`. States: default, focused, one line, two lines (narrow), needs-you with reason, ended (dim). |
| Repo heading (`Button` with `Text` children) | new variant | Home | 0 | none | Props: label, PR count, failing count, `onPress`. States: default, focused, without PR counts (gh missing). |
| PR row (`Box` with `Link` and `Text`) | new variant | Repo | 0 | none | Props: number, title, checks, review, mergeable, session. States: one line, two lines, no gh, running checks. |
| Ask row (`Box` with `Text`) | new variant | Session | 0 | none | Props: number, kind, status, text, time. States: task, question, not classified, waiting on you, replied; one line, wrapped. Not focusable. |
| Feature row (`Box` with `Text`) | new variant | Session | 0 | none | Props: number, name, state. States: done, in progress, not started. |
| Band stack slot (`ui.render` on `AbovePrompt`, `next(e)` below) | have (pattern seen) | band | 0; ponytail `register.tsx` renders `next(e)` below its own row | Two bands stack when ponytail is on, each with Details or Compact and Copy; hotkeys can collide. Spec is silent (F011). | Props and states for the stacked case missing. |

## Words

No glossary exists. Checked the alias table in `ia.md` for consistency, then every string against `writing.md` and setup.md's voice (plain words, sentence case, no exclamation marks).

| String | Where | Result | Proposed word |
|---|---|---|---|
| "● 2 need you · web-app: fix login, 6m" vs "… fix login 6m" | interaction.md vs screens.md, Band compact | Two spellings of the same line. | One form: "● 2 need you · web-app: fix login · 6m" (F003). |
| "tracker · reading sessions…" vs "reading sessions…" | interaction.md vs screens.md | Prefix differs. | "reading sessions…" |
| "tracker · sessions unavailable: claude agents failed. Retrying every 5s." vs "sessions unavailable · retrying" | interaction.md vs screens.md | Two wordings; the long one has event and action, the short one has no reason. | The long form where it fits; else "sessions unavailable · retrying". |
| "agent-tracker-1 2/4" vs "feature 2 of 4" | screens.md compact Work vs details header | Two ways to say progress. | "feature 2 of 4" in both when it fits; "2/4" only as the width fallback, stated in the spec. |
| "kind not known: this session ran without the tracker" vs "Kinds not known: …" | interaction.md vs screens.md | Two wordings. | "Kinds not known: this session ran without the tracker." |
| "Tracker › web-app" vs "Home > {repo}" | screens.md vs sitemap.md | Root name and separator differ. | F004. |
| "done" | session state (turn ended) and feature state (finished) | One word, two meanings. The engine's own `done` means ended. | Feature state "complete"; keep "done" for sessions (F009 note in findings). |
| "Copy" | band button | Names the action, not the object. Toast says "Tracker state copied as Markdown". | Deliberate (ponytail's label, A6); see Deliberate inconsistencies. |
| "Pane" | band button | A word from the mod API, not the owner's. `ia.md` says it is "ponytail's pattern, A6"; ponytail's buttons are Review, Audit, Board, Details and Compact, and A6 asks for a Board-like button that opens a page. | Owner decides (F011 note). Candidates: "Tracker", "List". |
| "Needs you" / "need you" / "0 need you" | band, pane | One concept, consistent. Plural handled. | none |
| "PRs not shown: gh is not installed or not signed in." | Pane Home | Event and consequence, no action; the Repo version adds "Run gh auth login to see them." | Same sentence on both (F014). |
| "tracker: could not save this session's file: <reason>" | status line | Names a "file" (system word), no consequence, no action. | "Asks from this session are not being kept: the tracker folder is not writable. Check `.claude/agent-tracker`." (F014) |
| "asks permission" | Home needs-you row | Depends on `waitingFor`, whose values the spec says are read at build time. | Verify the values before the string is fixed (F007). |
| Exclamation marks, headline case, apology filler | all screens | None found. Sentence case holds. | none |
| Outcomes in past tense: "Tracker state copied as Markdown" | Copy toast | Conforms; carries no count (none exists). | none |

## Screen goals, audience, taxonomy

| Screen | Goal | Audience scene | Object or control home | Result |
|---|---|---|---|---|
| Band, compact | Count what needs the owner; name the oldest waiting session (J1, J5, J10) | S1 mid-prompt | Needs-you item lives in Session state; control home is the band | Goal met in text. Reading order puts Work first, left of the count that `ia.md` ranks 1 (F016, a design choice). Sample strings do not fit 115 columns (F002). |
| Band, details | Columns with one line each; what runs here (J5, J6, J7, J11) | S1, S2 | Same | Header words differ between files (F003). The oldest waiting line is dim (F010). |
| Pane, Home | Triage queue: needs you, running, done by repo (J1, J4, J9, J10) | S2 triage | Session rows; repo headings | Needs you is a flat list with repo on each row; Running and Done sit under repo headings, so a repo with only waiting or only ended sessions has no heading (F009). |
| Pane, Repo | One repo: worktrees, PRs, ended (J9, J11) | S3 review | Repo object | Reachable by a heading only when the repo has a running or done session; otherwise by the session's repo line or `/tracker repo <name>` (F009). |
| Pane, Session | One session: running now, asks, features, numbers (J2, J3, J4, J7) | S3 review | Ask, Run, Feature, numbers | Goal met. Breadcrumb is text; a repo button repeats it (F004). No hand-off to switch to the session (F005). |

## Deliberate inconsistencies

All undecided. The owner decides at the gate.

| Rule | Where | Why | Owner decision needed |
|---|---|---|---|
| Double-click on Details toggles twice (Pane is idempotent) | Band view button | Toggle copied from ponytail's band (A6) | Keep the toggle, or make Details and Compact two named states. |
| Needs you is a flat list; Running and Done are grouped by repo | Pane Home | Triage wants the longest wait first, whatever the repo | Keep, and add a repo route for repos that never get a heading (F009). |
| Buttons named by noun or bare verb ("Pane", "Details", "Copy"), where `writing.md` asks for action and object | Band | Width; ponytail's labels (A6) | Keep ponytail's labels, or rename for the action ("Copy state"). |
| The band's labels "compact" and "details" follow ponytail, not the glossary | Band | A6 | Accept as the glossary entry. |
| Singular page ids (`repo/<repo>`, `session/<sessionId>`) against route conventions RC-1 and RC-2 | Pane routes | Match the alias table and milestone 2's `#/repo/…` | Already recorded in `ia.md` and `spec/sitemap.md`; accept or choose `repos/<repo>`. |
| Three names for one entry: `/tracker`, "Pane", "Home", title "Tracker" | Band, pane | Ponytail pattern for the button | Choose one name for the place (SM-4, still open). |

## Missing guidelines

| Proposed rule | Home document | Why needed |
|---|---|---|
| Hotkeys act only while the band or pane holds the keyboard; the first letter typed in an empty prompt is never a hotkey. | `docs/ux/interaction-guidelines.md`, Keyboard and focus | F001; every prompt in every session depends on it. |
| Escape goes one step up: ring to prompt, then pane closed. | same, Keyboard and focus | F012. |
| What a read error does to the band and the pane: both keep the last good data, dimmed, with its age and the reason. | same, Connection to external systems | F007. |
| A session's own state is shown in its own band as "this session"; it is not counted as the "oldest waiting" one a second time. | same, Feedback and notifications | F008. |
| When another mod fills the same slot (ponytail's band), the tracker renders below it, uses no hotkey a sibling band may use, and says in its hint how to hide itself. | same, Platform conventions | F011. |
| The pane opens on Home when opened from the band, and on the last page when reopened by `/tracker`, or always Home. | same, Navigation and return | F006. |
| A link that leaves the tracker is marked and opens the browser. | same, Navigation and return | Pane Repo and Session PR links. |
| The band view is one value per machine; every open band follows it. | same, Remembered state | F013. |
| One error shape: event, consequence, action, in one place per surface. | same, Feedback and notifications; `docs/ux/glossary-proposal.md` for words | F014. |
| Glossary entries for session, needs you, running, done, ended, ask, task, question, PR, goal, subagent, repo, compact, details. | `docs/ux/glossary-proposal.md` | The alias table is the only vocabulary and holds one meaning clash ("done"). |
| Design system: Claude Code's mod components and theme colours as the system, with the component list including `Link`. | `docs/ux/setup.md` | The spec cites "have" and "new variant" against nothing the owner accepted. |

### Findings behind the F-codes above

One entry per departure, in the form of `finding-format.md`. Verified is stated honestly: nothing is "seen on screen".

### F001: Letter hotkeys may fire while typing a prompt
- **Impact:** High · if hotkeys act from an empty prompt, pressing `p`, `d`, `c`, `b`, `h` or `x` as the first letter of a prompt opens the pane or toggles the band, in every session.
- **Current experience:** `interaction.md` avoids digit hotkeys because "a bare digit in an empty prompt would press them". The same spec binds letters `d`, `p`, `c`, `b`, `h`, `x`, which have the same problem, worse.
- **Recommendation:** State when hotkeys act. If only while the band or pane has the keyboard, delete the digit reason; if from the prompt, drop letter hotkeys and keep Tab and Enter.
- **Tradeoff:** Without hotkeys the keyboard route is slower (ring, Tab, Enter).
- **Decision needed:** Routine fix once the mod types say how `hotkey` fires; until then a decision.
- **Verified:** assumption, not checked. `hotkey` exists as a prop in a public mod; its firing rule is not shown in any file read.
- **Owner's words:** no earlier request found.
- Where: `interaction.md` "Band keys", "Pane keys"; every Controls table. Broken: proposed rule Keyboard and focus (none accepted). Rung R6.

### F002: The spec's own sample strings do not fit its widths
- **Impact:** Medium · the compact band wraps or cuts at the default width, so the one line the owner reads at every prompt breaks.
- **Current experience:** The sample compact band with a goal ("calvins-claude-tools · agent-tracker-1 2/4 · goal 14m", "● 2 need you · web-app: fix login 6m", "◐ 3 running", "4 PRs · 1 ✗", "Pane  Details") counts 136 cells with separators; `bodyColumns` at 120 columns is 115. Home's Running example row ("◐ migrate users   feat/users · 22m · 41k tokens · 2 errors · 1 retry") is 68 cells in a dock of 40 to 54; two-line rows start only below 50. The sdlc-run details header ("… · milestone/agent-tracker-1") is 83 cells plus buttons, about 104, against 75 at 150 %.
- **Recommendation:** Apply the drop order at every width, set the Home two-line threshold from the longest sample (70), and say what the details header cuts first when it has no session title (branch, then milestone name).
- **Tradeoff:** More states to build and test.
- **Decision needed:** Routine fix: no individual decision needed.
- **Verified:** measured, on the spec's own strings.
- **Owner's words:** no earlier request found.
- Where: `screens.md` Band compact Layout, Pane Home Layout, Band details Layout. Broken: proposed rule none; density check in `spec.md` step 4.

### F003: Two spec files give two wordings for the same screen
- **Impact:** Medium · whoever builds picks one at random, and the tests and screens drift.
- **Current experience:** See the Words table: needs-you comma, "tracker ·" prefix, error wording, "2/4" against "feature 2 of 4", the details header with and without the branch, "kind not known" against "Kinds not known".
- **Recommendation:** Make `screens.md` the only home for strings; `interaction.md` points to it.
- **Tradeoff:** none.
- **Decision needed:** Routine fix: no individual decision needed.
- **Verified:** read in the files (`interaction.md` lines 92 to 103 and 125; `screens.md` lines 63 to 73, 135 to 137, 302).
- **Owner's words:** no earlier request found.
- Broken: `writing.md` "One vocabulary".

### F004: The breadcrumb differs between files and is not a control
- **Impact:** Low · the root is "Tracker ›" in `screens.md` and "Home >" in `sitemap.md`; the repo button beside the breadcrumb does what clicking the breadcrumb would.
- **Current experience:** "Tracker › web-app › fix login redirect" is text; the repo is a separate button; "Home" is a button elsewhere.
- **Recommendation:** One root name, one separator, and make the breadcrumb segments the controls (drop the repo button) or say it is text only.
- **Tradeoff:** Segments as buttons cost width.
- **Decision needed:** Which root name (SM-4 is open): "Tracker" or "Home"?
- **Verified:** read in the files.
- **Owner's words:** no earlier request found.

### F005: J1 ends at a name; no route to the session, and a control named in the sitemap has no screen
- **Impact:** Medium · the most frequent job (answer the blocked session first) is read-only with no hand-off; the owner has to find the session by hand.
- **Current experience:** `interaction.md` says switching is "Claude Code's own move". `sitemap.md` lists "Copy resume command (secondary)" on the Session page; `screens.md` and the CTA inventory have no such control.
- **Recommendation:** Add a Copy button on the Session page that copies the session's resume command to the clipboard. It writes nothing to a session, so it keeps observe-only.
- **Tradeoff:** One more control on the page; the command is for a terminal the owner may not be in.
- **Decision needed:** Add Copy resume command to Session (recommended), or remove it from the sitemap?
- **Verified:** read in the files.
- **Owner's words:** "which agent needs attention" (2026-11-13, owner-words, "What the tracker is for").
- Broken: Navigation and return (proposed), job J1.

### F006: The pane's entry page is stated two ways
- **Impact:** Medium · triage (S2) wants Home every time; a pane that reopens on a stale Session page hides the queue.
- **Current experience:** Move Table and sitemap: the Pane button and `/tracker` open Home. Action Behaviour: `/tracker` reopens on the same page. Open Question 2 recommends "Yes".
- **Recommendation:** Open Home from the band's Pane button; reopen the last page only for `/tracker` with no argument, or always Home.
- **Tradeoff:** Reopening on the last page saves a move for people reading one session.
- **Decision needed:** Home always, or last page on reopen?
- **Verified:** read in the files.
- **Owner's words:** no earlier request found.

### F007: On a read error the band drops its counts; the pane keeps them
- **Impact:** Medium · when `claude agents --json` fails, the band that is the only signal for J10 shows no count, while the pane shows the last list dimmed.
- **Current experience:** Band error state: header plus one dim line "sessions unavailable". `interaction.md` Errors: "the band shows the last read and its age." Pane error: "Showing what was read 2m ago."
- **Recommendation:** Both keep the last good counts, dimmed, with "read 2m ago" and the reason. Also confirm `waitingFor` values before "asks permission" is final.
- **Tradeoff:** A stale count can mislead; the age and dimming mark it.
- **Decision needed:** Routine fix: no individual decision needed.
- **Verified:** read in the files.
- **Owner's words:** no earlier request found.

### F008: The current session may name itself as the oldest waiting one
- **Impact:** Medium · the band in a session that waits for a permission tells the owner, in that session, that this session needs them.
- **Current experience:** `ia.md` answers "Yes, the same band in every session" and states nothing about counting or naming self.
- **Recommendation:** Count it, but name it "this session"; name the oldest other session next to it.
- **Tradeoff:** Another variant of one line.
- **Decision needed:** Count itself or not?
- **Verified:** assumption, not checked.
- **Owner's words:** no earlier request found.

### F009: Some repos have no way in from Home
- **Impact:** Medium · J11 (open PRs) is reachable only through a repo heading, and headings exist only under Running and Done.
- **Current experience:** A repo with only waiting sessions, or only ended sessions, has no heading. `/tracker repo <name>` is the only direct route; the Session page's repo line is the other.
- **Recommendation:** Show the repo name on each Needs you row as a second control, or add a "Repos" line listing every repo.
- **Tradeoff:** A row with two controls is harder to focus.
- **Decision needed:** Which route?
- **Verified:** read in the files.
- **Owner's words:** "I want to understand which repository is what" (2026-11-13).
- Also: "done" names a session whose turn ended and a feature that is finished; use "complete" for features.

### F010: Needed information sits in the dim style
- **Impact:** Low · the needs-you column's dim line carries which session has waited longest.
- **Recommendation:** Normal colour for that line.
- **Tradeoff:** Less contrast between the columns' label and sub-line.
- **Decision needed:** Routine fix.
- **Verified:** read in the files; contrast not measured.

### F011: The tracker band stacks under ponytail's with no stated behaviour
- **Impact:** Medium · the owner runs ponytail (the two screenshots in `asks/`). Two bands appear, each with Details or Compact and Copy, and any shared hotkey collides.
- **Current experience:** The design file says it stacks by rendering `next(e)` below its own row; the screens do not show or size the stacked case. `ia.md` calls the "Pane" button "ponytail's pattern", which is not ponytail's button set.
- **Recommendation:** Add a stacked state, no hotkeys shared with a sibling, and a way to hide the tracker band.
- **Tradeoff:** Two rows of band at every prompt.
- **Decision needed:** Show both bands, or let the owner hide one?
- **Verified:** read in the code (`register.tsx` renders `next(e)` below its own) and in the files.
- **Owner's words:** "ponytail also has this little menu … we could have something similar for us." (2026-11-13)

### F012: Escape has two meanings
- **Impact:** Low · "hand the keyboard back" in the band, "close the pane" at an empty prompt; order is not stated when both apply.
- **Recommendation:** Escape goes one step up. **Decision needed:** Routine fix. **Verified:** read in the files.

### F013: The remembered band view has no stated scope
- **Impact:** Low · "per machine" and "across sessions" are not the same, and a store under the mod API is outside `~/.claude/agent-tracker/`, the one folder `setup.md` allows writes in.
- **Recommendation:** Say where it is stored and whether other bands follow at once; add the store to `setup.md`'s Safety list. **Decision needed:** Routine fix. **Verified:** assumption, not checked.

### F014: Error lines miss the consequence or the action
- **Impact:** Low · store write failure, Home "PRs not shown", the compact band error.
- **Recommendation:** Event, consequence, action on each; no word "file" on screen. See the Words table for the before and after. **Decision needed:** Routine fix. **Verified:** read in the files.

### F015: `Link` is not shown to exist
- **Impact:** Medium · see Component inventory. **Verified:** none found in any installed public mod and not in `setup.md`'s list. **Decision needed:** Routine fix once the types are read.

### F016: The count the band exists for is not first
- **Impact:** Design choice · `ia.md` ranks the needs-you count 1; `screens.md` puts Work first on the left.
- **Recommendation:** Keep Work first and rely on the warning colour, or put the count first. **Decision needed:** which. **Verified:** read in the files; preference.

### Checked and clean

- **Observe only:** no control or flow writes to a session, agent, git, gh or bd.
- **Keyboard parity:** every pointer action has a keyboard route and a `/tracker <argument>` route (Action Behaviour).
- **No drag, drop, right-click or media:** stated per element in the matrix.
- **Colour:** no literal values; every glyph sits beside a word or a count.
- **States:** loading, empty, error, partial and not-found exist for the band and each page.
- **Feedback:** the only toast is Copy, and its failure names the reason; no essential message is toast-only.
- **Public repo:** no local path or internal name in the spec files (grep for `/Users/` and `file://` found none).
- **Back:** history-based, restores row and scroll.

### Not run

- **Visual pass:** no images; the screenshot recipes are BLOCKED until the mod is built. `visual-check.py` did not run; result is text-only.
- **Accepted-rule check:** none accepted.
- **Glossary and token checks:** no glossary, no tokens.
- **WCAG:** scope proposed R2, not accepted; no contrast or target measured.

## Resolution, 2026-11-13

What the spec did with each finding. Decisions marked "taken" are the agent's recommended answers, recorded in `ia.md` under Decisions Taken Here; the owner confirms or changes them at the plan gate.

- **F001:** resolved by the engine types: a letter `hotkey` fires only while the band or pane has the keyboard; only a bare digit fires from an empty prompt. Letters kept, digits unused; `interaction.md` says so.
- **F002:** fixed. Widths measured on the Words samples (compact 112 of 115 cells; Home row 68; details header 72 + 21); drop orders at every width in `screens.md`.
- **F003:** fixed. `screens.md` Words tables are the only home for strings; `interaction.md` state tables name the Words row.
- **F004:** taken: root "Home" as in the sitemap; the pane's title row says "Tracker"; the breadcrumb is text, the repo button is the control.
- **F005:** taken: "Copy resume command" on an ended session's page only; a live session is named by its tab title. Sitemap updated.
- **F006:** taken: the Pane button and `/tracker` always open Home.
- **F007:** fixed: band and pane both keep the last good counts, dimmed, with their age (state "Stale").
- **F008:** taken: this session counts and is named "this session".
- **F009:** taken: a Repos line ends Home; feature states use "complete", not "done".
- **F010:** fixed: the needs-you line is in normal colour.
- **F011:** taken: the tracker's row draws above other mods' rows, shares no hotkey, and `/tracker band off|on` hides and shows it.
- **F012:** fixed: Escape goes one step at a time (keyboard to the prompt, then close at an empty prompt).
- **F013:** fixed: band view and hidden flag in `~/.claude/agent-tracker/settings.json`; `setup.md` Safety lists it.
- **F014:** fixed: every error line reads event, consequence, action; no "file" on screen.
- **F015:** resolved by the engine types: `Link` exists on the terminal; `setup.md` lists it.
- **F016:** taken: the needs-you count goes first, as in the owner's sketch in the design file.
- **Still open for the owner:** singular page ids (`repo/<repo>`) against route conventions RC-1 and RC-2 (sitemap).
