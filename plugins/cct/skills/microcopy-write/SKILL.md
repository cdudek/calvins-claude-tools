---
name: microcopy-write
description: 'Writes and reworks product UI copy — button labels, error messages, empty states, toasts, confirmation dialogs, onboarding, CTAs — in OMR voice with de/en i18n discipline. Use when the user says "write the microcopy", "better error message", "label for this button", "empty state copy", "toast text", "UI copy", "what should this say", or a review flagged a ux-microcopy finding to fix. Skip for: emails/memos/Slack/reports — use copy-write; reviewing existing copy tone — use tone-of-voice.'
allowed-tools: "Read Grep Glob Edit Write Skill"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Write Microcopy (product UI copy)

Write UI copy that helps users accomplish tasks, understand status, and feel confident.
Core patterns adapted from MC Dean's MIT-licensed `cct:ux-writing`
(github.com/Owl-Listener/designer-skills), extended with OMR voice and i18n rules.

## Before writing

1. Read the project's design/voice contract if present (`PRODUCT.md` register + brand
   personality, tone docs). For OMR products, the `tone-of-voice` (OMR AI Kit only, OMR's voice; not in cct) skill is the
   voice authority — consult it for anything user-facing.
2. Find the project's terminology glossary (CLAUDE.md, docs) and reuse its exact terms —
   never introduce a synonym for an established concept (e.g. OMR Reviews: "Partner",
   never "Anbieter"/"vendor"; "Merkliste", never "Watchlist" in DE).
3. Locate where copy lives (message catalogs like `messages/de.json` + `en.json`, inline
   component copy, email builders) and follow that mechanism — no hardcoded strings where
   the project uses keys.

## Category patterns

### Buttons & CTAs
- Verb + object, outcome-specific: "Lead kaufen", "Save changes" — never "OK", "Submit",
  "Click here". Cancel clarifies what cancel means ("Keep editing").
- Destructive actions name the destruction and the count ("Delete 5 leads").
- Match user intent, not business intent; the primary CTA is the most common action.
- Loading keeps the label (spinner carries the signal) — no "Saving…" label swaps that
  change button width.

### Error messages
Formula, always: what happened → why (only if it helps) → what to do next.
- Specific over generic: name the offending value ("Invalid addresses: foo@gmail.com"),
  never a bare "Invalid input".
- Human, never blaming ("This field is required", not "You made an error"). No humor in
  errors.
- Pair with the mechanism: inline field errors for input problems (persist next to the
  field, `role="alert"` wiring); toasts only for transient action results — and a failed
  action ALWAYS gets feedback (a silently reverting optimistic toggle is a bug).
- End actionable server-error copy with the next step ("Bitte erneut versuchen.").

### Empty states
Onboarding moments, never dead ends: what will appear here → why it's worth filling →
one clear CTA. On-voice wit is allowed where the design contract assigns it.

### Confirmations & toasts
- Confirm what happened, brief and positive ("Demo-Einstellungen gespeichert.").
- Destructive confirms name the action + consequence ("Alle Demo-Leads zurücksetzen?
  Nicht umkehrbar.") with specific button labels, never Yes/No.
- Prefer undo over confirmation for reversible actions.
- Success toasts must be TRUE: never toast success when the operation may have no-oped.

### Onboarding
Welcome without overwhelming; one concept at a time; action-oriented; always skippable.

## Voice and tone
- **Voice** is constant (brand personality, vocabulary, perspective — for OMR: confident,
  credible, direct, du-form in DE).
- **Tone** adapts: celebratory-brief on success, empathetic-helpful on error, serious-clear
  on destructive confirms.
- Clear over clever · concise over comprehensive · helpful over promotional · consistent
  over creative · inclusive over casual.

## i18n discipline (non-negotiable for OMR repos)
- Every key lands in ALL locale catalogs in the same change (de/en parity — run the
  project's parity check if one exists).
- German: real Umlaute, du-form, gender with * where the project does; expect +30% length
  vs English — check the layout survives it (labels must not truncate into "ZEITHO…").
- Translation-friendly: full sentences per key (word order varies), no concatenation from
  fragments, no abbreviations, numbers/units kept with their words (an amount must never
  wrap away from its unit).
- Relationships in words, not symbols a screen reader skips ("saved at 201 € — now 190 €",
  not "201 € → 190 €").

## Best practices
- Content-first: write the copy before (or while) designing the UI, not after.
- Keep/extend the project's terminology dictionary; consistency beats variety.
- Avoid jargon, internal names, abbreviations, and idioms.
- After changing copy, check every consuming surface (a subject line may also render in a
  feed, a preview, and a test snapshot).
