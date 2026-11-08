# Writing for the interface

Read the project's own voice rules first (named in `docs/ux/setup.md`: a DESIGN.md voice section,
a glossary, a writing-style file). They win over anything here. This file is what to check.

## Writing for the audience

Read every word on screen as the person in the project's audience file would read it.

- **Their nouns:** the words they use for their own things, not the system's. A producer has
  one-shots and kits, not assets and items.
- **Their level:** no jargon they would not use; no hand-holding they do not need.
- **Their tone:** the same voice on every screen, dialog, toast and error.
- **No system words:** no IDs, codes, status enums, stack traces, internal names.

## One vocabulary

- One word per meaning, one meaning per word, everywhere: screens, dialogs, toasts, menus,
  settings, tooltips, documents.
- Build a **term × place table** for every object, action and state. Every row that uses a
  different word, or the same word for a different thing, is a finding.
- Flag misspellings and outdated text (words for features that changed or no longer exist).

## Voice checks, one finding per string that fails

- Sentence case, unless the project says otherwise.
- Buttons name the action and its object ("Delete kit", not "OK").
- Outcomes in past tense with the number ("3 kits deleted").
- Errors read **event · consequence · action** ("The Digitakt disconnected. The copy to slot 5
  stopped. Plug it back in to try again.").
- No exclamation marks, no celebration, no apology filler, unless the project's voice allows it.
- Placeholders never carry the label.
- Every confirmation says exactly what will happen and whether it can be undone.
- A disappearing message never carries the only copy of something the user needs.

## How a wording finding is shown

Always the exact text before and after, and where it appears:

| Where | Before | After |
|---|---|---|
| Footer | "Digitakt II detected" | "Digitakt II · connected" |
