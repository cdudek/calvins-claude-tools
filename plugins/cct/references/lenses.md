# The lenses

Every audit and every review looks through all of these. A finding names the lens it rests on in
its supporting notes. Translate each lens into the project's own world: its users, its objects,
its devices. The project's `docs/ux/setup.md` says what that world is.

## Nielsen's ten usability heuristics

Every finding is tagged with the one it breaks.

1. **Visibility of system status:** the user always knows what is going on, through timely feedback.
2. **Match between the system and the real world:** the user's words, concepts and order, not the system's.
3. **User control and freedom:** a clearly marked way out of every unwanted state; undo and redo.
4. **Consistency and standards:** one word, one look, one behaviour per meaning; platform conventions followed.
5. **Error prevention:** remove error-prone conditions, or confirm before the user commits.
6. **Recognition rather than recall:** options visible; nothing to remember from one screen to the next.
7. **Flexibility and efficiency of use:** accelerators (keys, shortcuts, defaults) for the frequent user.
8. **Aesthetic and minimalist design:** nothing that competes with what matters.
9. **Help users recognise, diagnose and recover from errors:** plain words, the exact problem, a way forward.
10. **Help and documentation:** easy to find, focused on the task, short.

Heuristic evaluation complements research; it does not replace it. The standard is three to five
evaluators working independently on the same interface, merged afterwards (see `cct:ux-assessment-run`).

## Shneiderman's rules

- **Consistency:** similar patterns, identical terms in prompts, homogeneous menus and screens,
  the same commands throughout.
- **Shortcuts for frequent users:** keys for everything done often.
- **Informative feedback:** modest for frequent and minor actions, substantial for infrequent and
  major ones.
- **Dialogs that yield closure:** a beginning, a middle and an end, with a visible result at the end.
- **Error prevention:** grey out what cannot be done now; refuse bad input at the field.
- **Easy reversal:** undo relieves anxiety and invites exploration.

## Six plain questions, answered per screen

1. Does it solve the user's problem?
2. Is it intuitive without a manual?
3. Is the interface well designed?
4. Is it easy to navigate?
5. Does it work for everyone?
6. Is the user confident about what will happen?

## Maze's three extra lenses

- **Design-system and visual inconsistencies:** fonts, colours, patterns, spacing, components.
- **Outdated or misspelled content.**
- **Limitations in the user's journey:** jobs that are clumsy, broken or impossible.

## The Laws of UX (Jon Yablonski, lawsofux.com), all thirty

This table is the index. The checks live in `laws-of-ux.md`: numbered, observable checks per law
with thresholds, the evidence each needs, severity and when a law does not apply. An audit or a
review marks every law pass, fail or not applicable there; reading this table alone is not a
Laws of UX pass.

| Law | What it says | What to look for |
|---|---|---|
| Aesthetic-usability effect | Pleasing design is perceived as more usable | Polish hiding a real problem; roughness making a working screen feel broken |
| Choice overload | Many options overwhelm | Menus, pickers, filters and settings with more options than the task needs |
| Chunking | Information is grasped in meaningful groups | Long lists and forms not broken into scannable groups |
| Cognitive bias | Systematic errors in judgment | Defaults and wording that steer a choice, especially a destructive one |
| Cognitive load | Mental resources needed to use the interface | State the user must hold in their head: where am I, what is selected, is it saved |
| Doherty threshold | Fast response keeps people productive | Every action measured against the response-time bands of `laws-of-ux.md` B1 (0.1 s feedback, INP at most 200 ms, progress from 1 s); 400 ms is not a pass mark |
| Fitts's law | Time to a target depends on its size and distance | Small or far targets, especially frequent or primary ones |
| Flow | Full, energised immersion in a task | Anything that interrupts the core activity: dialogs, waits, lost place |
| Goal-gradient effect | Effort rises near the goal | Progress made visible on long jobs |
| Hick's law | Decision time grows with number and complexity of choices | Crowded decision points |
| Jakob's law | Users expect your product to work like the others they use | Breaks with the platform and with the tools the audience already knows |
| Law of common region | Shared boundaries group elements | Related controls without a boundary; unrelated ones inside one |
| Law of proximity | Near things read as related | Spacing that groups the wrong things |
| Law of Prägnanz | Complex images are read in their simplest form | Screens that look busier than they are |
| Law of similarity | Similar-looking things read as one group | Look-alikes that behave differently; act-alikes that look different |
| Law of uniform connectedness | Visually connected things read as related | Missing or false visual links between related parts |
| Mental model | Users act on what they think they know | Where the product's model differs from the user's |
| Miller's law | Working memory holds only a few chunks (about 4, Cowan 2001) | Items the user must remember without seeing them; never the number of visible items |
| Occam's razor | Prefer the fewest assumptions | Features, controls or steps that add nothing |
| Paradox of the active user | Users never read manuals | Anything that only works after reading a hint or document |
| Pareto principle | 80% of effects come from 20% of causes | Whether the most-used actions are the easiest to reach |
| Parkinson's law | Tasks expand to fill the time | Long flows without a clear end |
| Peak-end rule | Experiences are judged by their peak and their end | How the key flows end: success, failure, partial success |
| Postel's law | Liberal in what you accept, conservative in what you send | What the product accepts: odd files, names, formats, devices, versions |
| Selective attention | Attention goes to goal-related stimuli | Status and warnings placed where the user is not looking |
| Serial position effect | First and last items are remembered best | Order of navigation, menu items and dialog buttons |
| Tesler's law | Some complexity cannot be removed, only moved | Complexity the product should carry instead of the user |
| Von Restorff effect | The item that differs is remembered | Whether the one thing that should stand out does, and only that |
| Working memory | Temporary store for the task at hand | Anything carried in memory from one screen to another |
| Zeigarnik effect | Unfinished tasks are remembered | Unfinished work made visible: unsaved edits, interrupted jobs |

## The UX-reviewer lenses

Visual hierarchy, contrast, accessibility, friction, motion, microcopy, and a design review
against the project's own design system. Run through the `cct:ux-usability-reviewer` agent
(prompt starts with `MODE: review`) when it is available.

## Accessibility

WCAG 2.2 AA, through the `cct:ux-accessibility-audit` skill when it is available, and the
accessibility block of `checklist.md` point by point.

## Writing

`writing.md`: writing for the audience, one vocabulary, the project's voice rules.

## Pattern research

For every finding that needs a decision: how the products the audience already uses solve the
same problem. The project's `docs/ux/setup.md` names them. One line per product, in the
supporting notes. "Another product does it" is evidence, never the reason on its own.
