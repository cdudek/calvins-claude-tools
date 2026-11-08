# The decision page: what it must get right

Every point below cost the owner a round trip once. Check them all before handing over the page.

## Content

- **Uncapped.** Every rule, every screen and word choice, every routine fix. Never "the top 100".
- **No codes in the main text.** Finding numbers, rule keys, agent ids, PR numbers, "(main)",
  section numbers and document names go in the folded supporting notes. In the main text say
  "the current app", "the tables draft", "rule 17".
- **Pronouns.** They/them for the owner in anything written about them; "you" when addressing
  them. Never infer he or she from a name.
- **Write "you" directly, do not substitute it.** Replacing "the producer" with "you" by script
  makes "you types", "You who works", "until you moves". Rule text is written in the second
  person; text copied from findings stays third person ("a producer who …").
- **Today and the caption say different things.** The paragraph says what happens; the caption
  says only what the screenshot shows. A caption never repeats the paragraph and never starts
  with "Today".
- **No fake sketches.** For each proposal: a real small sketch when it is visual, the exact
  words before → after when it is about wording or keys, or no before/after at all. A "sketch"
  that repeats the recommendation is worse than none.
- **Quotes must be about the subject.** Show the owner's words only if they are about this
  decision; otherwise "No earlier request found." If the quote argues against the
  recommendation, show it and say so.
- **Behaviour changes are never routine.** Anything that changes what happens (not only how it
  looks or reads) gets its own question: with the rule it belongs to, or in an "Other screen
  decisions" block.
- **Owner comments already given** (Plannotator, chat) are quoted on the card, and the question
  asks the owner to confirm how they were written up, not to decide again.
- **Already decided** items move to an "Already decided" block with the owner's words and no
  answer controls; their questions disappear from the page.

## Mechanics

- Generate the page from the repo's documents with a script; re-parse the documents after every
  change to them, so no cached copy goes stale.
- One self-contained local HTML file in the repo (the path goes in `docs/ux/setup.md`), opened with
  `open`. Everything inline: no server, no upload, no external script. Never publish it to claude.ai
  (no Artifact, no Claude Docs) and never to any hosted page.
- Answers live in the browser's `localStorage` under the answer id, and an Export button downloads
  `answers.json`: one entry per id with `choice`, `text`, `updatedAt`. The owner saves it next to
  the page as `answers.json`, or says where it went.
- Every item: Accept · the alternative (only when there is one) · Defer · My own words, plus a
  note box. Saving on click and when typing stops; no Submit button.
- Check at 1440 and 400 wide: no sideways scroll, every image loads, the title is in the first
  8 KB, answer ids are unique.
- **Read the whole page's visible text before handing it over**, top to bottom, and fix what the
  list above catches. A script check is not a read.
- Write to the same path each time (keep it in `docs/ux/setup.md`). After the first write, open
  the file, answer one item, reload to prove it stays, export, and say what was and was not
  exercised.
