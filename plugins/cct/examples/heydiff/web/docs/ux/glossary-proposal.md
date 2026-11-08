---
type: glossary-proposal
status: proposed
created: 2026-10-29
updated: 2026-10-29
---

# HeyDiff glossary proposal

Every term the HeyDiff team service shows, and the one word for it. One word per meaning and one meaning per word, in every screen, email, extension string and agent reply (A10, WRD-4).

**A proposal until the owner accepts it.** The terms and the alias table come from the approved information architecture of change 2026-10-27-online-release-1 (`ia.md`, objects and alias table). "Agent" as the label and "Copilot" as an alias that never shows is the owner's decision of 2026-10-28 (A32).

The Mac app keeps its own glossary proposal in `heydiff-desktop/docs/ux/glossary-proposal.md`. The cross-product word map is still to write; see the open question at the end.

**Checks.** `test/docs/glossary.test.ts` fails when a term of the information architecture is missing from "Terms", when "Agent" loses its alias, or when `messages/en.json` uses a product word that this file does not name.

## Terms

| Term           | Meaning                                                                                                                                                                                                                                                 | Aliases and rejected words                                                                       |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Comment        | One remark on one page of the product under review.                                                                                                                                                                                                     | Rejected: Feedback (as a noun on screen), item, issue, ticket, note                              |
| Anchor         | What a comment points at, one per element (A57): selector, DOM path, tag, size, text, region, module, component, `file:line`, parent chain, and the box on the screenshot.                                                                              | Rejected: Target, element binding                                                                |
| Selection      | The elements picked in pick mode before the comment exists.                                                                                                                                                                                             |                                                                                                  |
| Pin            | The comment's mark on the live page: a comment bubble filled with the author's avatar (A41), on the first anchor.                                                                                                                                       | Rejected: Diamond, marker, reference, number                                                     |
| Screenshot     | The image taken when the comment is sent.                                                                                                                                                                                                               |                                                                                                  |
| Drawing        | Marks drawn on the live page with the Mac editor's tools, names and keys (A46, C8): Select (C); Reference, Card (1); Box, Ellipse (2); Arrow (3); Pen (4); Cross, Remove Area (5); Highlighter, Spotlight (6); Cut & Move, Redact (7).                  |                                                                                                  |
| Move           | One suggested change to the page: move an element inside its parent, align it left, centre or right, change its spacing or width (A54).                                                                                                                 | Rejected: Rearrange, drag, edit                                                                  |
| Change list    | The moves of one comment, as structured rows: selector, action, target, values, plus each element's component and `file:line`.                                                                                                                          |                                                                                                  |
| Context        | Where and on what the comment was made: page URL, environment, repo (from the route rules, or the Mac bridge on localhost), worktree path (localhost only, from the Mac bridge), branch, commit, "Uncommitted changes" flag, device, browser, viewport. |                                                                                                  |
| Commit         | The commit the page ran when the comment was made, read from the Mac bridge (localhost) or the environment's deployment.                                                                                                                                |                                                                                                  |
| Environment    | Where the product runs: kind (Local, Preview, Staging, Production), name and address patterns.                                                                                                                                                          | Rejected: Prod, Dev, Stage                                                                       |
| Device         | The screen a comment was made on: Responsive (the window as it is), MacBook Air 13", MacBook Pro 14", MacBook Pro 16", iPad Air, iPhone 16, iPhone 16 Pro Max or Custom, with its size.                                                                 | Rejected: Viewport, screen size, resolution (as a label)                                         |
| Reply          | One entry in a comment's thread: text, optional drawing, optional @mention.                                                                                                                                                                             | Rejected: Respond, Comment (as a verb inside a thread), Answer                                   |
| Decision       | A vote between options about one comment.                                                                                                                                                                                                               | Rejected: Decision request, poll, vote                                                           |
| Option         | One answer in a decision: an uploaded mockup, a Figma link, or a text option.                                                                                                                                                                           | Rejected: Version, alternative, variant, mockup (as a group word)                                |
| Vote           | One person's pick of one option in an open decision.                                                                                                                                                                                                    |                                                                                                  |
| Revision       | What an agent (or a member by hand, A33) reports after changing the code for a comment: number (1, 2, …), commit, summary, files, optional after-screenshot.                                                                                            | Rejected: Version, implementation, fix, iteration                                                |
| Session        | An optional wrapper around one person's review pass (A52): a name, its comments across pages, start and end.                                                                                                                                            | Rejected: Pass, review, folder                                                                   |
| Inbox item     | One thing that needs you: a vote you are asked for, a revision on a comment you wrote or replied to (author and everyone in the thread, guests included; S139), a mention, a reply on a comment you are in, a session shared with you.                  |                                                                                                  |
| Organisation   | Holds seats, members, workspaces and settings.                                                                                                                                                                                                          | Rejected: Org, project, collaborator, staff                                                      |
| Workspace      | One product inside an organisation, e.g.                                                                                                                                                                                                                |                                                                                                  |
| Member         | A person's role in one organisation: owner, admin or member.                                                                                                                                                                                            |                                                                                                  |
| Guest          | A person invited to chosen workspaces only.                                                                                                                                                                                                             |                                                                                                  |
| Invitation     | An email link that adds a person to an organisation with a role (admin sends), or lets a waitlist person create one (operator sends).                                                                                                                   |                                                                                                  |
| Module         | A named part of the product, e.g.                                                                                                                                                                                                                       |                                                                                                  |
| Repo           | A GitHub repository linked to a workspace, entered by hand in release 1.                                                                                                                                                                                |                                                                                                  |
| Route Rule     | Maps an address path to a repo for microfrontends: `/reviews/*` → `reviews-web`.                                                                                                                                                                    |                                                                                                  |
| Device Token   | A client signed in for you: the Chrome extension, the Mac app, or an MCP client such as Claude Code.                                                                                                                                                    |                                                                                                  |
| Agent          | The coding agent acting for a person through MCP (A32).                                                                                                                                                                                                 | Copilot (alias, never on screen); Rejected: Copilot (alias, never on screen), Bot, AI, assistant |
| Waitlist entry | An email asking for early access, confirmed by a link (double opt-in).                                                                                                                                                                                  |                                                                                                  |
| Feature flag   | A switch an operator turns on for everyone or per organisation.                                                                                                                                                                                         |                                                                                                  |
| Audit event    | Append-only record of every status change and operator action.                                                                                                                                                                                          |                                                                                                  |

## One word per meaning

The accepted spelling, the words it replaces, and why. Rejected words never show on screen.

| Canonical                                                      | Rejected                                                  | Reason                                                                                                               |
| -------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Comment                                                        | Feedback (as a noun on screen), item, issue, ticket, note | A42, A43: "each comment sits for itself". `feedback` stays a word for the activity and in the product line           |
| Pin                                                            | Diamond, marker, reference, number                        | A41: "a comment symbol with avatar badge". Numbered diamonds are gone as pins; Reference is only a drawing tool (C8) |
| Anchor                                                         | Target, element binding                                   | Internal word for what a pin points at; on screen the parts are named (Element, Component, File)                     |
| Select / selection (elements)                                  | Inspect, pick (on screen)                                 | "Select" is the owner's verb (A47). "Pick mode" is a spec word only                                                  |
| Draw / drawing                                                 | Annotate, markup, mark                                    | The owner's verb (A4, A46). "Mark" was the earlier word; dropped, except as the Mac's tool group name (C8)           |
| Move                                                           | Rearrange, drag, edit                                     | A54: "moving things around". The switch reads Draw · Move                                                            |
| Suggested change                                               | Edit, patch, diff                                         | The composer says "{n} suggested changes"; the site is never changed                                                 |
| Revision                                                       | Version, implementation, fix, iteration                   | A44: "revision #1". "Version" is dropped                                                                             |
| Option                                                         | Version, alternative, variant, mockup (as a group word)   | A44 and the approved defaults ("Options")                                                                            |
| Decision                                                       | Decision request, poll, vote                              | The journey's word; "Start a Decision", "Decide"                                                                     |
| Decide                                                         | Approve, Accept, Close                                    | One verb for ending a decision                                                                                       |
| Resolve / Resolved                                             | Accept, Accepted, Approve, Done, Close                    | Default 4: Resolved replaces Accepted in words and tokens                                                            |
| Reopen                                                         | Unresolve                                                 | Plain verb for the contra-action                                                                                     |
| Open, Deciding, In Progress, Revised, Resolved (status)        | Implemented, Voting, Needs Decision, In Review, Done      | The brief's five words. The journey's "Implemented" and "Voting" chips are drawing leftovers                         |
| Not Resolved (the set Open, Deciding, In Progress, Revised)    | Open (for the set), Unresolved, Active                    | C6: "Open" names only the one status                                                                                 |
| Joined (invitation status)                                     | Accepted                                                  | C11: the same word as the waitlist                                                                                   |
| Reply                                                          | Respond, Comment (as a verb inside a thread), Answer      | A comment starts a thread; everything after it is a reply                                                            |
| Session                                                        | Pass, review, folder                                      | A52                                                                                                                  |
| End Session                                                    | Stop, Finish, Close Session                               | Image 21                                                                                                             |
| Agent (labels) / "{person} via {client}" (entries)             | Copilot (alias, never on screen), Bot, AI, assistant      | A32                                                                                                                  |
| Device (screen size)                                           | Viewport, screen size, resolution (as a label)            | A50 and image 19: "Each comment records the device it was made on." Viewport stays an engineer's field               |
| Connected App                                                  | Device (for a signed-in client), token, integration       | "Device" now names the screen size; one word per meaning                                                             |
| Environment kind: Local, Preview, Staging, Production          | Prod, Dev, Stage                                          | Design 3                                                                                                             |
| Uncommitted Changes                                            | Dirty, modified, WIP                                      | Image 01: "uncommitted changes"                                                                                      |
| Outdated                                                       | Orphaned, broken, lost                                    | The element is gone from the page                                                                                    |
| Earlier Commits                                                | Older versions, history                                   | Image 04: "Show Earlier Commits"                                                                                     |
| Organisation, Workspace, Member, Guest, Admin, Owner, Operator | Org, project, collaborator, staff                         | Kept from the earlier model                                                                                          |
| Sign In / Sign Out; Email link                                 | Log in; magic link                                        | Kept                                                                                                                 |

**Deliberate inconsistency.** The extension's visibility menu and side panel offer two status sets (Not Resolved, Resolved) while a comment has five statuses. "Not Resolved" is Open, Deciding, In Progress and Revised, and it is the default of the web Status filter too. "Open" always names the one status (C6).

## Named things in sentences

Words that appear capitalised inside sentences, or as part of a button label, in `messages/en.json`. They are product words, so the check wants each one named here.

| Word        | Where it comes from                                                                     |
| ----------- | --------------------------------------------------------------------------------------- |
| Account     | the area of person-level pages: Profile, Sign-In Methods, Connected Apps, Notifications |
| Again       | part of Try Again                                                                       |
| Air         | part of the device name iPad Air                                                        |
| Chrome      | the browser the extension runs in                                                       |
| Claude      | an agent client (shown as "{person} via Claude")                                        |
| Code        | part of Claude Code                                                                     |
| DevTools    | Chrome DevTools, named when a phone size shows the debugging bar                        |
| Docker      | named in a developer message about the localhost bridge                                 |
| Figma       | a link type for a decision option                                                       |
| GitHub      | where repos come from; a sign-in method                                                 |
| Google      | a sign-in method (A85)                                                                  |
| HeyDiff     | the product                                                                             |
| In          | part of Sign In                                                                         |
| Inbox       | the page of things that need you                                                        |
| Invitations | the list of open invitations in organisation settings                                   |
| Join        | the verb for an invitation or the waitlist ("Joined" is the status word)                |
| List        | the waitlist; "Stay on the List"                                                        |
| Mac         | the Mac app, HeyDiff for Mac                                                            |
| MCP         | the protocol an agent uses to reach HeyDiff                                             |
| Mine        | "Only Mine", a status choice in the visibility menu                                     |
| More        | the "…" menu, and "Show {n} More"                                                       |
| Online      | the Mac app's Settings tab for HeyDiff online                                           |
| Option      | one answer in a decision; has a letter                                                  |
| Privacy     | the privacy page                                                                        |
| Production  | an environment kind                                                                     |
| Profile     | the account page of your name and picture                                               |
| Reply       | one entry in a thread; the button Reply in Thread                                       |
| Report      | the verb in the scope "Report Revisions"                                                |
| Revision    | what an agent reports after changing code for a comment                                 |
| Revisions   | the list page of revisions                                                              |
| Settings    | the settings pages of a workspace or organisation, and the Mac app's Settings           |
| Sharing     | Share Session, Stop Sharing                                                             |
| Sign        | part of Sign In, Sign Out                                                               |
| Staging     | an environment kind                                                                     |
| Stop        | part of Stop Sharing                                                                    |
| Threads     | the scope "Reply in Threads"                                                            |
| Workspace   | one product inside an organisation                                                      |

## Writing a new product word

1. Add the term here with its meaning and any rejected words, in the same change as the string that uses it.
2. Add the string to `microcopy.md` and `messages/en.json`.
3. Run `npx vitest run test/docs/glossary.test.ts`. A product word missing here fails it.

## Open questions

- The cross-product word map (HeyDiff for Mac against the team service): Comment, General comment, Note, Mark. Default: the web uses Comment; the Mac app keeps its words until the owner decides. Owner to confirm.
