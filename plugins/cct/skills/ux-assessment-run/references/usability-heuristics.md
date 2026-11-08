# Usability heuristics, severity and dark patterns

Phase 4 of the audit judges **behaviour**: whether a person can finish the job. The ten
categories in Phase 3 judge the **rendered result**. A screen can score A on every visual
category and still fail here.

Read this file when you run Phase 4. Everything in it produces findings on the kit's one
scale, the five levels of `finding-format.md` in the plugin's `references/` (Critical, High,
Medium, Low, Design choice). There is no second scale.

## How to run the pass

1. Walk each key flow as a first-time user, then again as a returning one.
2. For every stumble, name the heuristic it breaks. A finding without a named heuristic is
   an opinion.
3. Rate it with the table in **Severity**, then write it as
   `{heuristic} — {what happens} → {fix}`.
4. Run the **Dark patterns** checklist over any flow that takes money, consent or data.
5. Where two heuristics, laws or rules disagree, settle it with **When heuristics collide**
   below, which hands the decision to `conflicts.md`.

---

## The ten heuristics

Each one: what it means, a failure you will actually see, the fix, and where it usually lands
on the severity scale.

### 1. Visibility of system status

The interface says what it is doing, while it does it.

| | |
|---|---|
| **Failure** | "Pay 249 EUR" submits and nothing changes for four seconds. The person clicks again and is charged twice. |
| **Fix** | Disable the button on click, swap the label to `Processing…`, and show the result. |
| **Severity** | Critical when the silent action can produce a wrong outcome in money, consent, access or mail (the double charge). High when it costs data or time. Low when it is only a missing "Saved" tick. |

Watch for: no loading state, a silent failure that looks like success, feedback that arrives
after the person has already re-clicked, progress that exists but is drawn somewhere nobody
is looking.

### 2. Match between the system and the real world

The words on screen are the words the person would use.

| | |
|---|---|
| **Failure** | A settings page offers `Terminate instance`, `Purge cache`, `Revoke principal`. The user wanted to cancel a subscription. |
| **Fix** | Write the user's verb: `Cancel subscription`. Keep the internal term for logs, never for labels. |
| **Severity** | Medium normally, High when the wrong reading triggers something destructive. |

Watch for: internal service names in the UI, one concept with two names on two pages, icons
with no label, and a step order that matches the database rather than the task.

### 3. User control and freedom

Every state has a marked exit.

| | |
|---|---|
| **Failure** | A six-step onboarding wizard with no back button and no skip. A wrong answer in step 2 means starting over. |
| **Fix** | Let people move backwards and leave. Keep what they typed when they return. |
| **Severity** | High for anything a person cannot escape or undo. |

**Undo beats confirmation.** People click through "Are you sure?" without reading it, so the
dialogue buys nothing and costs a step. An undo that lasts ten seconds is worth more than
three confirmations. Reserve a confirmation for what genuinely cannot be undone, with one
exception: money, consent, access and outgoing mail get a review step that names the
consequence even when they can be undone (`conflicts.md` C11, `laws-of-ux.md` B5).

Watch for: modal traps, a hijacked browser back button, deletion with no recovery, a flow
that cannot be abandoned halfway.

### 4. Consistency and standards

The same thing looks and behaves the same way everywhere, and follows the platform.

| | |
|---|---|
| **Failure** | The primary action is bottom-right on one form, top-left on the next, and a text link on the third. |
| **Fix** | One button hierarchy, one position, applied everywhere. Take it from the design system, not from the page. |
| **Severity** | Medium each, High in aggregate — inconsistency compounds. |

Conventions people already hold: logo top-left and it goes home, search top-right, the primary
action to the right of or below the form, cancel as the weaker neighbour, a hamburger only on
small screens.

If the repo declares a design system, it decides this. A consistency finding that contradicts
the design system is a finding against the page, not against the system.

### 5. Error prevention

The best error message is the one that never fires.

| | |
|---|---|
| **Failure** | A free-text date field that rejects `03.09.2026` after submit, with the rest of the form cleared. |
| **Fix** | A date picker. Constrain the input instead of validating the mistake afterwards. |
| **Severity** | Medium, High when the prevented error loses work. |

Two different failures need two different fixes. A **slip** is the right intention performed
wrongly — bigger targets, undo, confirmation on the destructive one. A **mistake** is the
wrong intention — clearer labels, better defaults, a preview of what will happen.

Watch for: free text where a list would do, no warning before leaving unsaved work, destructive
actions sitting next to routine ones, validation that only runs on submit.

### 6. Recognition rather than recall

Show the options. Do not make people remember them.

| | |
|---|---|
| **Failure** | "Enter your country code" against an empty field. The person leaves to search for it. |
| **Fix** | A dropdown of country names. The code is your problem, not theirs. |
| **Severity** | Medium. High when the forgotten thing blocks the task. |

Watch for: empty fields with no format hint, actions hidden behind a hover or a long-press,
no breadcrumb in a deep hierarchy, raw codes where the decoded value would fit, a second step
that asks again for what the first step already collected.

### 7. Flexibility and efficiency of use

Fast paths for people who are here every day, invisible to people who are here once.

| | |
|---|---|
| **Failure** | An operator archives 300 records one at a time because there is no multi-select. |
| **Fix** | Select-all plus a bulk action. Add a keyboard shortcut for the action they repeat most. |
| **Severity** | Medium for the daily user, Low for the occasional one. Weigh it by how often the task runs. |

Watch for: no bulk operations, no shortcuts on a high-frequency screen, an unskippable tutorial,
no recent or saved items where the same query is run daily.

### 8. Aesthetic and minimalist design

Everything on screen competes with everything else on screen.

| | |
|---|---|
| **Failure** | A dashboard where nine cards all use the same weight, size and colour. Nothing is first. |
| **Fix** | Pick the one number that matters, make it larger than the rest, and demote the other eight. |
| **Severity** | Medium. It rarely blocks a task, it reliably slows every task. |

This is the same judgement as Phase 3's visual hierarchy, applied to content rather than form:
if a thing is rarely needed, it belongs behind a disclosure, not on the first screen.

### 9. Error recovery

When it does fail, say what happened and what to do next.

| | |
|---|---|
| **Failure** | `Error 422: unprocessable entity`, with the form emptied. |
| **Fix** | "That email address is already registered. Sign in instead, or use another address." Keep every field they filled. |
| **Severity** | High when the person cannot get out of the error. Medium when they can, slowly. |

A usable error message has three parts: what happened, in plain words; why, when the why helps;
and the specific next action. Never blame the person, never clear their input, never print a
code as the whole message. Where the copy itself needs writing, that is `ux-copy-write` —
this audit says the message fails, that skill writes the replacement.

### 10. Help and documentation

Help is a fallback, not a substitute for a self-evident interface.

| | |
|---|---|
| **Failure** | A field labelled `Cost centre reference` with a link to a 40-page PDF. |
| **Fix** | A one-line hint next to the field with an example value. Keep the PDF for the rare deep question. |
| **Severity** | Low, unless the task is impossible without the document, which makes it High. |

Watch for: help that cannot be searched, help written per feature rather than per task, and
help that is only reachable by leaving the page.

---

## Severity

The kit has one scale, defined in `finding-format.md`, which also maps it to Nielsen's 0-4,
the accessibility skill's levels and the build QA's P0-P3. Map every heuristic finding onto it.

| Severity | Use it when | Example |
|---|---|---|
| **Critical** | The person loses work, data or money, cannot finish a core job, or gets a wrong outcome in money, consent, access or mail; or a legal requirement fails | Silent double charge; an error that clears the form; pre-ticked consent |
| **High** | A core job is broken, misleading or needlessly hard for most users | A wizard with no exit; a destructive action labelled like a routine one |
| **Medium** | The task completes, but costs time, a retry or a support message | Jargon labels; no bulk action on a daily job; validation only on submit |
| **Low** | Noticed, survivable, worth fixing when nearby | Missing "Saved" confirmation; a hint that would save one hover |
| **Design choice** | No demonstrated problem; a direction to decide | A preference for a different layout |

The B2B escalation rule applies: a finding on a money, consent, access or mail action is raised
one level, never above Critical.

Three factors decide where a finding sits. Judge all three before writing it down.

- **Frequency** — is this on the path everyone walks, or one rare branch?
- **Impact** — when it bites, does it cost a second, a retry, or the work?
- **Persistence** — does it trip people once and then get learned, or every single time?

A small annoyance on the main flow outranks a serious problem in a corner nobody visits. Say
which factor drove the rating when it is not obvious — "Medium, not High: it only affects the
first session" is a reviewable claim, "Medium" alone is not.

Per Phase 6, each Critical or High drops a category a full letter and each Medium half a
letter, so inflating severity inflates the grade downward. Rate honestly.

---

## When heuristics collide

Two heuristics will disagree on most real screens. That is not a defect in the framework: it is
the actual design decision, and the kit settles it one way. Use `conflicts.md` in the plugin's
`references/`:

1. Look the pair up in its conflict table (C, W, G and P rows) and apply the resolution rule.
2. If the pair is not there, climb its precedence ladder: the highest rung with an opinion
   decides, and a lower rung only decides how that rung is met.
3. Write down which side lost: in the finding, a `Rung:` line in the supporting notes; for a
   deliberate departure, an `EX-<n>` entry in the product's `docs/ux/exceptions.md`.

There is no second method. Money, consent, access and outgoing mail always keep their review
step (R3).

---

## Dark patterns

A dark pattern is an interface that works against the person using it — usually by making the
profitable choice easy and the honest one hard. Some of them are illegal in the EU. Every one is
at least a **High** finding, and **Critical** when it touches consent, money or a legal
requirement (pre-ticked consent, withdrawal harder than granting), as `laws-of-ux.md` L4 rates
them. Unlike the rest of this file they are not a usability defect to be weighed against
effort: they are a design decision to reverse.

| Pattern | What it looks like | What to write instead |
|---|---|---|
| **Forced continuity** | A free trial that needs a card and charges silently on day 31 | Tell people before it charges, and let them cancel in the same number of clicks it took to subscribe |
| **Roach motel** | Signing up takes one form, cancelling takes a phone call | Same route in and out |
| **Privacy zuckering** | Consent pre-ticked, sharing on by default, granular controls three levels deep | Off by default, one screen, plain wording |
| **Bait and switch** | The advertised action does something else — `X` that opens a purchase | The control does what its label says |
| **Confirmshaming** | The decline link reads "No thanks, I don't want to save money" | A neutral decline: "Not now" |
| **Hidden costs** | Fees appear only at the final step | Full price at the first step |
| **Misdirection** | The upsell is a big coloured button, "continue without" is grey 11px text | Equal visual weight for both real choices |
| **Trick questions** | "Untick if you do not want to not receive emails" | One clause, one meaning, positively worded |
| **Sneak into basket** | An extra lands in the cart on its own | Nothing enters the basket unless the person put it there |
| **False urgency** | "3 people are viewing this" and a timer that resets on reload | Real stock and real deadlines, or no counter at all |

### The checks

Run these over any flow that takes money, consent or personal data.

- Is the cheapest, most private, least committal choice as easy to pick as the profitable one?
- Does every control do what its label promises?
- Is the full price visible before the last step?
- Can the person leave, cancel or delete by the same route they arrived?
- Is every countdown, stock level and social proof number real?
- Would the copy on the decline option embarrass you if it were read aloud in a meeting?

### The mirror test

Show the flow to the person it targets and describe what it is doing. If you would soften the
description, it is a dark pattern. That is the whole test, and it is more reliable than the
catalogue above, which will never be complete.

### The legal edge

This is a judgement aid, not legal advice — flag it and let legal rule.

For EU and German products these are the rules to name. First decide the surface's
scope: consumer-facing, or business customers only. The consumer rules below do not bind a pure
B2B surface, where the same patterns are still failures under the honesty rule.

- **GDPR consent** must be freely given, specific, informed and unambiguous (Art. 4(11), 7).
  Pre-ticked boxes are not consent (CJEU Planet49, C-673/17); refusal is as easy and as
  prominent as acceptance on the same layer (EDPB Guidelines 05/2020,
  https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-052020-consent-under-regulation-2016679_en;
  EDPB Cookie Banner Taskforce report 2023,
  https://www.edpb.europa.eu/our-work-tools/our-documents/other/report-work-undertaken-cookie-banner-taskforce_en).
- **Withdrawal** is as easy as giving consent (GDPR Art. 7(3)); for consumer subscriptions the
  cancellation button of BGB 312k applies (https://www.gesetze-im-internet.de/bgb/__312k.html).
- **Transparency:** a layered notice is allowed, but its first layer carries the controller,
  the purposes, the right to withdraw and the consequences (GDPR Art. 12-13; Art. 29 WP
  Transparency Guidelines WP260 rev.01, https://ec.europa.eu/newsroom/article29/items/622227).
- **Privacy by default:** personal data off by default in exports and shares (GDPR Art. 25(2),
  https://eur-lex.europa.eu/eli/reg/2016/679/oj).
- **Unfair commercial practices** on consumer surfaces: misleading actions and omissions and
  false limited-time offers (UCPD Art. 6-7 and Annex I no. 7,
  https://eur-lex.europa.eu/eli/dir/2005/29/oj; in Germany the UWG and its annex).
- **Marketing mail** needs double opt-in (UWG 7(2),
  https://www.gesetze-im-internet.de/uwg_2004/__7.html).
- **DSA Art. 25** binds providers of online platforms only
  (https://eur-lex.europa.eu/eli/reg/2022/2065/oj). Do not cite it for a console or a
  company's own website.

Treat a consent finding on an EU surface as Critical by default.

---

## Fast diagnostic

Fifteen failures that account for most of what this pass finds. Use it to sweep a screen in a
minute before walking the flows properly.

| Symptom | Why it costs | Fix |
|---|---|---|
| Icons with no labels | People guess, and guess wrong | Label the icon |
| Options not ordered or not searchable | Scanning an unordered list costs time with every item | Order by use or alphabet, group under headings, add search for long lists |
| No "you are here" | People lose the hierarchy | Mark the current section, add breadcrumbs |
| Validation only on submit | Fill, fail, scroll, repeat | Validate on blur, message next to the field |
| Required fields marked, optional not | Everything looks compulsory | Mark the optional ones instead |
| A wall of text | Nobody reads it | Headings, lists, whitespace |
| Internal jargon in labels | Your language, not theirs | Use the user's word |
| No loading indicator | Looks broken, gets re-clicked | Show progress, disable the trigger |
| Targets under 24x24 CSS px without spacing | Mis-taps and missed clicks; fails WCAG 2.5.8 (AA) | At least 24x24, or a 24 px circle on each that touches no other target; 44x44 on phone primary targets is a recommendation (`laws-of-ux.md` L7.2) |
| Information only on hover | Invisible on touch and keyboard | Never hide anything necessary behind hover |
| No undo | People stop taking actions | Undo on everything reversible |
| `Invalid input` | Says nothing | Name the field and the rule |
| Low contrast text | Unreadable for many | `ux-accessibility-audit` owns the thresholds |
| Navigation that moves between pages | Re-learned every page | Same place, every page |
| A broken back button | Breaks the oldest contract on the web | Never hijack history |

And the four questions that decide whether a screen is self-evident at all:

1. Can I tell what this page is, without reading the body?
2. Is the main action obvious within a second?
3. Do I know where I am in the structure?
4. If I do the wrong thing, can I get back?

A `no` to any of them is at least Medium, and a `no` to the fourth is High.
