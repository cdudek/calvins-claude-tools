---
name: ux-copy-write
description: "Writes and reworks localized interface wording and owns the product's terminology: button labels, CTAs, error, empty-state, toast and confirmation copy, onboarding, tooltips and placeholders, in the repo's voice with locale parity. Use when the user says 'write the microcopy', 'better error message', 'label for this button', 'empty state copy', 'toast text', 'what should this interface say'. Skip for: emails, memos, Slack and reports (use a writing skill); judging the wording of a built screen (cct:ux-usability-audit)."
allowed-tools: "Read Grep Glob Edit Write Skill"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Write interface copy (microcopy, terminology, i18n)

Write interface copy that helps users accomplish tasks, understand status and feel confident.
This skill is the single owner of interface wording, the terminology dictionary and de/en
discipline. Core patterns adapted from the MIT-licensed UX-writing skill in
github.com/Owl-Listener/designer-skills, extended with voice and i18n rules.

## Before writing

1. Read the project's design/voice contract if present (`PRODUCT.md` register and brand
   personality, tone docs). The repo's voice guide, if any, is the voice authority for anything user-facing.
2. Find the project's terminology glossary (CLAUDE.md, docs, the UX glossary) and reuse its exact
   terms. Never introduce a synonym for an established concept (e.g. one name for a user role, never its synonyms).
3. Locate where copy lives (message catalogs like `messages/de.json` and `en.json`, inline
   component copy, email builders) and follow that mechanism. No hardcoded strings where the
   project uses keys.
4. A new concept gets one term, added to the glossary in the same change. Keep and extend the
   terminology dictionary; consistency beats variety. An action keeps one name through the whole
   flow: the button "Publish" produces a toast "Published".

## Category patterns

### Buttons, CTAs and labels
- Verb + object, outcome-specific: "Lead kaufen", "Save changes". Never "OK", "Submit", "Click
  here". Cancel clarifies what cancel means ("Keep editing").
- Destructive actions name the destruction and the count ("Delete 5 leads").
- Match user intent, not business intent; the primary CTA is the most common action.
- Loading keeps the label (the spinner carries the signal); no "Saving..." swap that changes the
  button width.
- Form labels: clear, concise, no jargon. Tooltips: brief explanation of a complex feature.
  Placeholders: an example format, never instructions.

### Error messages
Formula, always: what happened, why (only if it helps), what to do next.
- Specific over generic: name the offending value ("Invalid addresses: foo@gmail.com"), never a
  bare "Invalid input".
- Human, never blaming ("This field is required", not "You made an error"). No humor in errors,
  and errors do not apologize.
- Pair with the mechanism: inline field errors for input problems (persist next to the field,
  `role="alert"` wiring); toasts only for transient action results. A failed action ALWAYS gets
  feedback (a silently reverting optimistic toggle is a bug).
- End actionable server-error copy with the next step ("Bitte erneut versuchen.").

### Empty states
Onboarding moments, never dead ends: what will appear here, why it is worth filling, one clear
CTA. On-voice wit is allowed where the design contract assigns it.

### Confirmations and toasts
- Confirm what happened, brief and positive ("Demo-Einstellungen gespeichert.").
- Destructive confirms name the action and consequence ("Alle Demo-Leads zurücksetzen? Nicht
  umkehrbar.") with specific button labels, never Yes/No.
- Prefer undo over confirmation for reversible actions.
- Success toasts must be TRUE: never toast success when the operation may have no-oped.

### Onboarding
Welcome without overwhelming; one concept at a time; action-oriented; always skippable.

## Voice and tone
- **Voice** is constant (brand personality, vocabulary, perspective; e.g. confident,
  credible, direct).
- **Tone** adapts: celebratory-brief on success, empathetic-helpful on error, serious-clear on
  destructive confirms.
- Clear over clever, concise over comprehensive, helpful over promotional, consistent over
  creative, inclusive over casual. Plain verbs, sentence case, no filler, no jargon, internal
  names, abbreviations or idioms. Name things by what users understand, not by how the system is
  built. Each written element does exactly one job.

## i18n discipline (non-negotiable where the repo is localized)
- Every key lands in ALL locale catalogs in the same change (de/en parity; run the project's
  parity check if one exists).
- German: real Umlaute, du-form, gender with * where the project does; expect +30% length vs
  English and check the layout survives it (labels must not truncate into "ZEITHO...").
- Translation-friendly: full sentences per key (word order varies), no concatenation from
  fragments, no abbreviations, numbers and units kept together (an amount must never wrap away
  from its unit).
- Relationships in words, not symbols a screen reader skips ("saved at 201 €, now 190 €", not
  "201 € → 190 €").

## Working rules
- Content first: write the copy before or while designing the UI, not after.
- After changing copy, check every consuming surface (a subject line may also render in a feed, a
  preview and a test snapshot).
- Test copy with real users when the chance exists.
- Wording on a built screen that needs judging, not authoring, goes to `cct:ux-usability-audit`.
