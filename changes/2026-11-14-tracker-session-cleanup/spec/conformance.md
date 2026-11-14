# Conformance

Checked 2026-11-14 by `cct:ux-rules-validate spec`, against `brief.md`, `ia.md`, `interaction.md`, `screens.md` and `sitemap.md` in this folder, and the built code on `milestone/agent-tracker-4` (`plugins/agent-tracker/hooks/tracker/`). Result tags `C1` to `C15` mark the findings; the rest are passes.

**Documents.**

| Document | Status | Effect |
|---|---|---|
| `docs/ux/setup.md` | found | Read for hard rules, audience scenes, safety limits. |
| `docs/ux/interaction-guidelines.md` | found, every rule `unresolved` | No accepted rule exists. Rows cite the rule area (`IG: <area>`) and check the spec's proposed default against `setup.md`, the intent and the built code instead. |
| `docs/ux/glossary-proposal.md` | found, table empty | No glossary. The vocabulary check ran against the spec's own alias table and milestone 1's, and `writing.md`. |
| Design system | missing (`setup.md`: "none") | No token or component rule check. Checked against the built components in `pane/view.tsx` and the tone map in `core/paint.ts`. |
| `docs/ux/exceptions.md` | found, one entry (EX-1, singular page ids) | Not touched: this change adds no page id. |
| Decisions in `docs/designs/INDEX.md` | none of type `ux` | No accepted decision to check. |
| `docs/ux/owner-words.md`, shared `writing.md`, `rule-areas.md` | found | Used. |
| Screen goals file | missing | `setup.md` names `ia.md`'s screen inventory instead; used. |
| `prototype/index.md` and images | missing | Size L in `decisions.json` carries no skip for `prototype`, so the activity is open. See "Screen goals". |

**Visual pass: text-only.** No prototype images and no built page exist, so no screenshot was opened and `visual.json` was not written. `screens.md` already plans the build-time render at 120, 80 and 40 columns. Treat every layout claim below as arithmetic on the strings (cells counted with wide glyphs as 2), not as seen.

**Verdict after the spec fixes (see Resolution).** Clear to build once the owner answers C1 and C5 and the `setup.md` haiku wording (C2 was decided on 2026-11-14); every other finding is fixed in the spec. First check: not clear to build yet. Four need an owner decision (C1, C2, C5, C7) and one wording change in `setup.md` (haiku); the rest are spec fixes (C3, C4, C6, C8 to C15). No rule is broken by an accepted guideline, because none is accepted. C2 was decided by the owner on 2026-11-14 (see Owner decisions).

## Resolution after the first check

The tables below record each finding as the check found it. This section says what the spec did about it (2026-11-14, same day). Findings still open are for the owner and sit in `validation.md`, Decisions Needed.

| Finding | Status | What the spec did |
|---|---|---|
| C1 `setup.md` hard rule and Safety limits | **owner decision** | Recorded under Deliberate inconsistencies. `docs/ux/setup.md` and the guidelines are outside this change's spec folder and are not edited here; a follow-up edits them after the owner accepts. |
| C2 confirm | **closed, decided 2026-11-14** | owner, dialog, 2026-11-14: "Always confirm". Clear opens a confirm every time it would write; the worktree offer keeps its own. See Owner decisions. |
| C3 result lines vs "Nothing to clear" | fixed | The result lines are page-local, survive the re-read, and a fresh visit shows "Nothing to clear" (`interaction.md`, Cleared; `screens.md`, Sections row 9). |
| C4 offer last on a long page | fixed | The offer sits directly under the actions row, above the result lines (`screens.md`, Sections row 8). |
| C5 Tidy leaves the pane | **owner decision** | Listed below; the hand-off mechanism is a Stage 3 fact. |
| C6 "9 tasks closed" | fixed | Dropped from the report. |
| C7 dim text | fixed | The lines that say what to do next are drawn in normal weight; dim stays on facts and the Tidy count (`screens.md`, Words). The contrast of the dim ones is still a render check. |
| C8 widths | fixed | `screens.md`, Layout, now gives error lines at 88 to 117 cells before the reason and what wraps. |
| C9 two wordings | fixed | One string in `ia.md` and `screens.md`. |
| C10 error with no action | fixed | "Check it in a terminal." added. |
| C11 raw `<reason>` | fixed | Passed through `clean()`, one line, cut at 60; dropped when unusable. |
| C12 confirm does not say undo | fixed | "so you can make it again" in the offer and in the tidy option. |
| C13 worktree label | fixed | One label, the Repo page's ("login"), through one helper. |
| C14 idle and ended | fixed | "idle" carries the 30-day test in tidy and on Home; "ended Nd ago" stays in the Session header. |
| C15 "turn" | fixed | "Tidy waits until Claude finishes replying in this session." |
| Tidy as an `inline` item | fixed | Tidy is a `lines` block plus an `actions` block (`screens.md`, Home). |
| `flexWrap`, `Local.date`, `ActionItem`, `AgentRow.pid` | recorded | In `screens.md`, Session, Components, as build notes. |
| Worktree with no session has no page | accepted | `ia.md`, Decisions Taken Here. |
| The owner's 2026-11-14 mockups are not in the repo | **cannot check** | The mockups were local files (milestone 1's brief says the same). No new control could be compared with them; the owner is asked in `validation.md`. |

## Owner decisions, 2026-11-14

Four questions the first check and the validation loop left open were answered in one dialog. Each answer is quoted as selected.

| Question | Owner's answer | Source | Effect on this check |
|---|---|---|---|
| Should Clear ask for a confirm? (C2) | "Always confirm" | owner, dialog, 2026-11-14 | C2 closed. The spec has a Confirming state; no departure from the intent's "a confirm before anything that cannot be undone" remains. |
| `claude rm` also deletes a worktree the session created, if safe. | "Allow, name it (Recommended)" | owner, dialog, 2026-11-14 | Decided; matches the spec. The confirm names it before the press, the result after. |
| Ignored files deleted with a worktree. | "List them in the offer (Recommended)" | owner, dialog, 2026-11-14 | Decided. The offer lists up to 3 names and "and N more"; the list is re-read at the press. |
| The button word. | "Keep "Clear" (Recommended)" | owner, dialog, 2026-11-14 | Decided; matches the spec. The Close and Clear row under Deliberate inconsistencies is closed. |

## Interaction model

| Screen or state | Rule | Result | Change or proposed rule |
|---|---|---|---|
| Session, Clear and Remove worktree (every state) | `setup.md` hard rule "Observe only: the tracker never writes to a session or the agent", and Safety: "Never write to: any Claude Code session ... git, gh or bd state (read only)", "Writes only against" the tracker's own folder, "Allowed outputs: the clipboard and `settings.json`" | **C1 departs.** `claude rm` writes Claude Code's session list; `git worktree remove` writes git state. The built code agrees with `setup.md`: the comment on `act()` in `pane.tsx` calls task Keep and Close "the only writes, both to settings.json". `intent.md` Constraints records the change; `setup.md`, the guidelines and a decision file do not. | The owner accepts a decision (`cct:ux-decision-log`) that replaces the hard rule with: acts only on the owner's press or typed command; never stops a running session; never forces; never deletes a branch. Then edit the four `setup.md` lines and the guideline "Local work and external writes" before build. The owner's 2026-11-13 words were about steering the agent ("remove this intervention rules"); Clear does not steer, but the Safety list is literal. |
| Session, Clear | `IG: confirmation and undo` (unresolved); `intent.md` Constraints: "a confirm before anything that cannot be undone" | **C2 closed (2026-11-14).** The first check found that the spec's own Action Behaviour said the list row "does not come back" and closed tasks "are not reopened", and the pane has no reopen. It then recommended no confirm because the conversation stays resumable. | Decided: owner, dialog, 2026-11-14, "Always confirm". The spec now confirms before every Clear that writes (`interaction.md`, Confirming). Write it into the guideline. |
| Session, after a good Clear | `IG: feedback and notifications` (a result stays beside the affected item) | **C3 gap.** After Clear the session has no process, is not listed and has no open task, so it also meets the entry test of "Nothing to clear". The tables do not say which shows while the owner is still on the page, or whether the 5-second re-read replaces the result lines. | State it: the result lines are page-local and stay until the owner leaves the page; a fresh visit shows "Nothing to clear". Add a build test: the lines survive a re-read. |
| Session, offer after Clear | `IG: feedback and notifications`; `IG: keyboard and focus` | **C4 gap (build check).** The page runs about 20 lines at 120 columns (facts up to 4, milestone 2, tasks and PR, worktree, actions, up to 3 result lines, 4 for the offer), more when lines wrap. The offer is last and holds the one confirm. Neither `pane.tsx` nor `pane/view.tsx` sets a height or scrolls, and the Elements table says "arrows scroll". | Confirm at the render check that the offer is on screen when it appears at the 54-column dock. If the host does not scroll, draw the offer above the result lines. |
| Session, opening ring | `IG: keyboard and focus` | Pass. The ring starts on "Copy resume command", the first item of the first `actions` block (`firstKey`, `core/pane-model.ts:50`), so a double Enter cannot clear. After the offer appears it moves to Keep worktree; the built `ring` and `autoFocus` (`pane/view.tsx:19`) carry it. | none |
| Session, live (running, waiting, interactive done) | `IG: feedback and notifications` | Pass. No inert control: a dim line replaces Clear, and the built page has no disabled Button. | none |
| Home, Tidy button | `IG: navigation and return` | **C5 departs from the pane's own pattern.** Every other Home Button opens a page or acts in place; Tidy alone closes the pane. Its mechanism is also unverified: the built command handler answers `{ text }` or opens a page, and nothing starts a Claude turn (`ia.md`, Open Questions). | Listed under Deliberate inconsistencies. Stage 3 verifies the mechanism; the skill fallback in `ia.md` stands. |
| Transcript, tidy batch question | `IG: dialogs, menus and popovers`; `IG: confirmation and undo` | **C6 inconsistent.** The sessions question says each session "has no task that is not done", and `screens.md` rules send any session with an unfinished ask to "needs a look", never cleared. The report then reads "Cleared 5 sessions (9 tasks closed)". | Drop "(9 tasks closed)" from the tidy report. It matches the rule that tidy never touches unfinished asks. |
| Home, Tidy line (waiting, narrow) | `IG: feedback and notifications` | Pass. Waiting shows a reason, not a dead button; narrow keeps the ring off Tidy. | none |
| Every new move in `ia.md` | `IG: navigation and return` | Pass. No new page; Clear stays on its page; each move names Back target and focus. Longest new journey is J4 (5 moves, two confirms), weekly. No dead end: every result state keeps Copy resume command or Back. | none |
| Elements x interactions, all 13 rows | `IG: lists and selection` | Pass. Every cell is filled; Remove worktree is never first in the ring and sits above the result lines, three rows below where Clear was, with a build check for double clicks. | none |
| Hotkeys, all new controls | `IG: keyboard and focus` | Pass. Owner decision 2026-11-14: no hotkey shown; every key route is "Tab to it, Enter". | none |
| State rule, row with no `pid` is ended | none | Pass for behaviour. Build note: `parseAgents` pins the fields and has no `pid` (`core/states.ts:11`), so `AgentRow` gains one. | none |

## Design system

| Area | Departure | Impact | Fix |
|---|---|---|---|
| Document | No design system. Checked against the built blocks (`lines`, `row`, `inline`, `actions` in `pane/view.tsx`) and `TONE_COLOR` in `core/paint.ts` (red to `error`, yellow to `warning`, green to `success`, cyan to `suggestion`). | No token or component rule can be enforced beyond those two. | Name them in `setup.md` as the tracker's catalogue; it says "Component catalogue: none". |
| Colour meaning | none. ✓ in `success` and ✗ in `error` match `TONE_COLOR`; every glyph sits beside words. | none | Pass |
| Spacing | none. The `actions` row has `gap={2}` (`pane/view.tsx:96`); Clear, Tidy and the offer reuse it. | none | Pass (owner: buttons spaced) |
| Colour weight | **C7.** The lines that explain why a control is absent are dim: the two Clear reason lines, "Worktree ... stays", "Nothing to clear", "Clear waits". Dim text can miss 4.5:1 in some themes; the target is WCAG 2.2 AA (R2). | The owner needs those lines to know what to do next. | Check dim contrast on a light and a dark theme at the render check. If below 4.5:1, draw those lines in normal weight; keep dim for the Tidy count. |
| Layout widths | **C8.** The Layout table says result lines are "up to 72" and "Everything fits one line" at 120. The error strings are 105 cells before `<reason>` (the "changed" error is 92). The other widths check out: first line 56, reason 70, offer line 54, action row 26, offer buttons 30, TIDY 59. | Errors wrap to 2 lines at 120 and 3 or more at a dock. They sit in a `wrap` block, so nothing clips. | Correct the table; test errors at 54 and 36 columns. |
| Density | none. Home gains one dim block, last; the band gains nothing. | none | Pass |

## Component inventory

| Component | Status | Where the spec uses it | Callers today | Implication for other screens | Variant or new spec |
|---|---|---|---|---|---|
| `Button` (plain) | have | Clear, Clear session, Cancel, Remove worktree, Keep worktree, Tidy | `pane/view.tsx` lines 45, 56, 83, 98, 116, 118; `band.tsx`: 6 uses (Pane :108, Board :109, hide :110, Details :124, and the details view) | none; no hotkey prop used | none |
| `actions` block (Box row, `gap` 2) | have, one change | Session actions row; the offer's two buttons | 4 builders: `session-model.ts:99`, `pane-model.ts:145` (Keep and Close on superseded tasks), `pane-model.ts:217` (Mark all seen), `note-model.ts:42` | `flexWrap="wrap"` at `pane/view.tsx:96` reaches all four. They fit today, so nothing moves; include Home and the Note page in the render check. | Prop `flexWrap="wrap"`; states: one line, wrapped |
| `ActionItem.action` | have, seven new values (`clear`, `confirm-clear`, `cancel-clear`, `reopen`, `remove-worktree`, `keep-worktree`, `tidy`) | Clear, Clear session, Cancel, Reopen tasks, Remove worktree, Keep worktree, Tidy | the union at `core/pane-model.ts:33`, handled in `act()` in `pane.tsx` (5 values built today) | `act()` is the one handler, and its "only writes" comment must change (C1). | `'clear'` (sets Confirming), `'confirm-clear'` (sets Clearing), `'cancel-clear'`, `'remove-worktree'`, `'keep-worktree'`, `'tidy'`; each sets its own `Confirming`, `Clearing`, `Removing` or `Done` state |
| `lines` block (Text, wrap) | have | facts, reason, worktree, result and offer lines | every page model: `session-model.ts` (:58, :68, :75), `pane-model.ts`, `repo-model.ts`, `note-model.ts`, `missingModel` | none | none |
| `inline` block | **missing for Tidy** | TIDY block ("have: the REPOS block's component") | 6 builders: `repo-model.ts:139`, `:153`, `:201`, `:232`; `session-model.ts:89`; `pane-model.ts:236` (REPOS) | `Item` has only `to` (page Button), `href` (Link) or plain text (`core/pane-model.ts:34`); no inline item runs an action. So Tidy cannot be an `inline` item as the spec says. | Use a `lines` block (heading and count) followed by an `actions` block with Tidy. No new component, and it matches the narrow case (button on its own line). Props: `items`; states: waiting (no block, a dim line instead) |
| `Local` (day and clock) | have, one change | "started 12 Sep 16:13" | built in `pane.tsx:24`; read by `when` in `pane-model.ts:68` (callers `pane-model.ts:136`, `:143`, `repo-model.ts:68`) | `Local` has `clock` and `day` (weekday) only; the dated forms need a third function, and the weekday alone is already wrong past 7 days. | `Local.date(ms)`; states: today, 2 to 6 days, older, older than a year |
| Worktree label | have, private | worktree line, offer, result, stays, tidy items | 1: inline in `worktreeItems`, `repo-model.ts:103` | The Session and Repo pages must show one label (C13). | Extract one helper used by both pages |
| Command answer `{ text }` | have | tidy answer lines | `pane.tsx` command handler (`PANE_OPENED`, `COMMAND_HELP`), `band.tsx` replies (`BAND_REPLY`) | none | none |
| Command that starts a Claude turn | **new, unverified** | `/tracker tidy`, Home Tidy | none today | `ia.md` Open Question 1 | Props: the prompt text; states: started, busy, list unreadable, nothing to tidy (all in `interaction.md`) |
| Host question dialog | have (host) | tidy batch questions | none in the tracker | The tracker draws nothing; it fixes the words only. | none |

## Words

| String | Where | Result | Proposed word |
|---|---|---|---|
| "Clear is for ended sessions. Close this session in its terminal first." (reworded since: "Close its terminal first.") | `screens.md` Words | **C9 drift.** `ia.md` Decisions Taken Here gives "... Close this session in its terminal, then Clear it here." for the same line. | One string. Keep the `screens.md` one (it becomes the constant in `core/words.ts`) and edit `ia.md`. |
| "✗ The worktree changed since it was checked: it has uncommitted changes. Nothing was removed." | Session, Error, changed | **C10.** Event and consequence, no action (`writing.md`). The Errors table in `interaction.md` gives one. | "... Nothing was removed. Check it in a terminal." |
| `<reason>` in the three error strings | Session, Error rm, save, worktree | **C11.** It is whatever the command printed: system words and possibly a stack trace. | Pass it through `clean()` (`core/format.ts`), one line, cut at 60 cells; with no usable reason, drop the clause. |
| "Remove it? The branch fix-login stays." | Session, Offer line 2 | **C12.** A confirmation must say whether it can be undone (`writing.md`). Same gap in the tidy option "Remove all 3: Branches are kept." | "Remove it? The branch fix-login stays, so you can make it again." and "Remove all 3: Branches are kept, so each can be made again." |
| ".worktrees/login" | Session worktree line, offer, result, stays; tidy items | **C13 two names for one place.** The Repo page's WORKTREES list shows "login" (`repo-model.ts:103` strips `.worktrees/`). | Use the built label everywhere: "Worktree login is clean, pushed and merged." "Never an absolute path" holds either way. |
| "idle for 30 days or more" / "ended 30 days ago or more" / "ended 41d ago" / "idle 52d" | Home TIDY count; tidy question; tidy items | **C14 two words, two clocks.** The Session page shows "ended 63d ago" and "last activity 63d ago"; they are the same number whenever `endedAt` is empty (`endedAt()` falls back to last activity, `core/pane-model.ts:79`). | "idle" and "last activity" carry the 30-day test everywhere in tidy: "Each has been idle 30 days or more", items "idle 41d". "ended Nd ago" stays in the Session header only. |
| "Tidy waits until this session's turn ends." / "Tidy needs this session idle. Try again when its turn ends." | Home; transcript | **C15 (low).** "turn" is in no built word, and "idle" here means "not replying", the third meaning of the word. | "Tidy waits until Claude finishes replying in this session." for both. |
| "Clear", "Tidy" | Session, Home buttons | Pass. The owner's own words (A6); verb-only like the built Keep and Close; "close" stays for tasks and the pane. | none |
| "started" for "since"; "last activity" | Session first line | Pass. Matches the alias table. | none |
| "✓ 2 tasks closed.", "Nothing to clear: it is not in Claude Code's list and has no open tasks." | Session | Pass. Past tense with the number; plain nouns. | none |
| Help and hint strings with `tidy` | `screens.md` Words | Pass. Same order as the built strings (`core/words.ts:56`, `:61`). | none |
| Case, punctuation, public repo | all strings | Pass. Sentence case; no exclamation mark or apology; "TIDY" follows the built capital headings; examples are generic (web-app, api) and no string holds an absolute path (N6). | none |

## Screen goals, audience, taxonomy

| Screen | Goal | Audience scene | Object or control home | Result |
|---|---|---|---|---|
| Pane, Home | Triage: open tasks, then needs you; one dim Tidy line last | S2 triage (J1), S3 review (J5) | Tidy acts on a set, so it lives on the list page; Clear does not (act on one object, on its page) | Pass |
| Pane, Session | One session's real age, tasks, worktree, and the act for an ended one | S3 review (J2 to J4); S2 for a live one (J6) | Clear belongs to Session. Remove worktree belongs to Worktree, which has no page; it sits on the Session page. | Pass with a gap. A worktree with no session has no page, and the Repo list gives its item no link (`repo-model.ts:111`), so it can only be removed in the batch tidy. Accept or add a Repo-page control later. |
| Band | Counts; needs-you drops dead sessions | S1 mid-prompt | unchanged | Pass. The "N sessions run without the tracker" line also follows the state fix (`homeModel`, `lost`). |
| Transcript, tidy pass | Resolve idle items in one pass, ask once per batch | S3 review | A process, not an object; its home is the owner's transcript, drawn by Claude Code | Pass, surface unverified (C5) |
| Board, Session view | Shows the same state | S3 review | no actions (N9) | Pass. The Board computes its own `endedAt` (`board-html.ts:133`) but takes state from the same record, so it follows the fix. |
| All pages, against the owner's mockups of 2026-11-14 | The brief says the approved mockups win over anything new | n/a | The mockups are not in the change's `asks/` folder (only a screenshot of the built page is), so none of this spec's additions could be compared with them. | **Cannot check.** Copy the "Session detail" and Home mockups into `asks/2026-11-14/`, list them in the brief and compare the new controls (Clear, offer, Tidy line). The owner's rule: a departure goes to the owner as a question. |

## Deliberate inconsistencies

| Rule | Where | Why | Owner decision needed |
|---|---|---|---|
| `setup.md` Observe only and Safety limits (C1) | Session: Clear, Remove worktree; tidy | The owner asked for it (A3, A4, A6); acts only on a press or a typed command | Yes. Accept the replacement rule, then edit `setup.md`. |
| Confirm before what cannot be undone (`intent.md`) (C2) | Session: Clear asks one confirm every time; Remove worktree asks its own; tidy asks once per batch | none now: the spec follows the intent | Decided: owner, dialog, 2026-11-14, "Always confirm". No departure remains. |
| Pane buttons stay in the pane (C5) | Home: Tidy closes the pane and runs a command | Tidy runs in the owner's session, where the supervisor can ask questions | Yes, once Stage 3 shows the mechanism works. |
| Focus starts on the primary action | Session: ring starts on Copy resume command, not Clear | A double Enter must not clear | Accept or change. |
| Dim text is secondary (C7) | The Tidy count and "Clearing…" stay dim, as the mockup does | The mockup convention | Only the render check of their contrast. |
| `setup.md` "every model call pins haiku" | Tidy: haiku for the read-only checks, the session's model for the supervisor that acts (brief, Open Questions) | The rule was written for the mod's own calls | Yes. Reword `setup.md` to "every model call the mod makes". |
| One page per object | Worktree has no page; Remove sits on Session | Avoids a page for one button | Accept or add one later. |
| A key shown on every control (the template) | all controls: "Tab to it, Enter" | Owner decision 2026-11-14: no hotkeys | Already decided; none. |
| One word per verb: Close and Clear | Close ends a pane or one task; Clear acts on a session and closes its tasks | The owner chose "Clear" (A6); the alias table keeps the three meanings apart (`ia.md`) | Decided: owner, dialog, 2026-11-14, "Keep "Clear" (Recommended)". |
| Every pointer action has a menu route | Clear has no `/tracker` command of its own; the route is `/tracker session <text>`, then Tab, Enter | The act should be taken with the session's tasks and worktree in view | Accept or add a command. |
| The built page shows "Copy resume command" on every session | The spec restores milestone 1's "ended sessions only" (F005); the Board already does | Resuming a live session starts a second process on it | Accept (recommended) or keep the built behaviour. |
| Milestone 1's no-go N6 ("Closing, removing or archiving anything") | Clear closes tasks and leaves the list; Remove worktree removes a checkout | The owner asked for it (A3, A4, A6); only on a press or a typed command | Yes, with C1. |

## Missing guidelines

| Proposed rule | Home document | Why needed |
|---|---|---|
| The design system and glossary do not exist: record the built blocks and `TONE_COLOR` as the catalogue; add the terms Clear, Remove (a worktree), Tidy, idle, ended, last activity, started, terminal | `docs/ux/setup.md` (catalogue); `docs/ux/glossary-proposal.md` (terms) | Steps 2 and 9 of this check had nothing to run against. |
| The tracker acts only on the owner's press or typed command; it never stops a running session, never forces, never deletes a branch | `docs/ux/interaction-guidelines.md`, "Local work and external writes"; and `docs/ux/setup.md` Hard rules | Replaces observe-only (C1). |
| One confirm before every act that writes outside the tracker (leaving Claude Code's list, closing tasks, removing a checkout), saying what happens and what does not come back; focus lands on the cancelling button; a batch asks once and names what stays | `docs/ux/interaction-guidelines.md`, "Confirmation and undo" | C2, C12. |
| A step in progress shows as a dim line in place of its button; the result stays as lines beside the object until the owner leaves the page; partial success says which steps ran | `docs/ux/interaction-guidelines.md`, "Feedback and notifications" and "Progress and long operations" | C3. |
| The ring starts on the safest action; after an act it goes to the safe choice; no hotkey shown | `docs/ux/interaction-guidelines.md`, "Keyboard and focus" | Ring rules are in the spec only. |
| A control that cannot apply is not drawn; one dim line says what to do instead | `docs/ux/interaction-guidelines.md`, "Feedback and notifications" | Live sessions, unreadable list, nothing to clear. |
| A button that leaves the pane is the last on its page and says so in its neighbouring words | `docs/ux/interaction-guidelines.md`, "Navigation and return" | C5. |
| Derived facts (stale, cleared) are never stored | `docs/ux/interaction-guidelines.md`, "Remembered state" | "Nothing stores it" appears in three places in the spec. |
