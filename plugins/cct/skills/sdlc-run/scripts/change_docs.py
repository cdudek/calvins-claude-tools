"""The two reading aids of a change folder, built from its files: the id glossary and the reading map.

Called by `sdlc_status.py ids` and `sdlc_status.py readme` (see `references/readability.md`).
Nothing here touches git or the network; `readme` is the only thing that writes, and only README.md.
"""

from __future__ import annotations

import re
from pathlib import Path

# family letter -> (what it is, the file that decides it); the same letters verify_gate.py lints
FAMILIES = {
    "A": ("ask", "intent.md"),
    "J": ("job story", "intent.md"),
    "F": ("fact", "facts.md"),
    "N": ("non-functional fact", "facts.md"),
    "X": ("analysis finding", "analyze.md"),
    "H": ("challenge finding", "challenge.md"),
    "Q": ("question asked during the build", "questions.md"),
    "R": ("review finding", "findings.md"),
    "B": ("numbered item", ""),
}
USED = re.compile(r"(?<![\w@/.#-])([ABFHJNQRX])(\d{1,3})\b")
MEANING = 100


def _md_files(change: Path) -> list[Path]:
    return [p for p in sorted(change.rglob("*.md")) if p.name != "README.md"]


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _first_sentence(text: str) -> str:
    text = re.sub(r"\*\*|`", "", text).strip(" :-—")
    first = re.split(r"(?<=[.?!])\s", text, maxsplit=1)[0].strip()
    if len(first) > MEANING:
        first = first[:MEANING].rsplit(" ", 1)[0] + "..."
    return first


def meaning(ident: str, line: str) -> str | None:
    """The one-line meaning when `line` defines `ident`, else None. A definition is a table row
    whose first cell is the id, or a list item that opens with the id (bold or not)."""
    if line.lstrip().startswith("|"):
        cells = _cells(line)
        if cells[0] != ident or len(cells) < 2:
            return None
        if ident[0] == "A" and len(cells) > 3:
            return _first_sentence(cells[3])
        if ident[0] == "J" and len(cells) > 3:
            return _first_sentence(f"When {cells[1]}, I want {cells[2]}, so I can {cells[3]}")
        return _first_sentence(max(cells[1:], key=len))
    m = re.match(rf"^\s*(?:[-*]|\d+\.)\s+(?:\[[ x]\]\s+)?\**{ident}\b(.*)$", line)
    if not m:
        return None
    rest = re.sub(r"^\**\s*(?:\([^)]*\)\s*)*", "", m.group(1))  # drop "** (A1; rules x)" lead
    return _first_sentence(rest) or None


def ids(change: Path) -> list[str]:
    """One line per id the change defines, `F1  <meaning>  (facts.md)`, then the ids it only uses."""
    files = _md_files(change)
    used = {
        m.group(0)
        for p in files
        for m in USED.finditer(re.sub(r"```.*?```", "", p.read_text(encoding="utf-8"), flags=re.S))
    }
    found: dict[str, tuple[str, str]] = {}
    for ident in sorted(used, key=lambda i: (list(FAMILIES).index(i[0]), int(i[1:]))):
        home = FAMILIES[ident[0]][1]
        order = [p for p in files if p.name == home] + [p for p in files if p.name != home]
        for p in order:
            hit = next(
                (
                    t
                    for line in p.read_text(encoding="utf-8").splitlines()
                    if (t := meaning(ident, line))
                ),
                None,
            )
            if hit:
                found[ident] = (hit, str(p.relative_to(change)))
                break
    out = [f"{i:<5}{text}  ({where})" for i, (text, where) in found.items()]
    missing = sorted((i for i in used if i not in found), key=lambda i: (i[0], int(i[1:])))
    if missing:
        out.append(f"no definition found for: {', '.join(missing)}")
    return out or ["no ids in this change yet"]


# file or folder -> (question it answers, who writes it, stage, does a newcomer need it)
DOCS = (
    (
        "intent.md",
        "What are we building, and why?",
        "agent drafts, engineer confirms",
        "1 Intent",
        "yes",
    ),
    (
        "spec/screens.md",
        "What does each screen show and do?",
        "agent (ux-design-run)",
        "2 UX plan",
        "yes",
    ),
    (
        "facts.md",
        "What must be true when it is done?",
        "agent drafts, engineer approves",
        "3 Facts",
        "yes",
    ),
    (
        "plan.md",
        "How is it built, and in what order?",
        "agent drafts, engineer approves",
        "4 Tech plan",
        "yes",
    ),
    (
        "milestone.md",
        "Which features ship together, and where do they stand?",
        "builder",
        "5 Build",
        "yes",
    ),
    (
        "questions.md",
        "What came up while building, and what default was taken?",
        "builder",
        "5 Build",
        "yes",
    ),
    ("handover.md", "Where did the last session stop?", "agent", "any", "yes"),
)
FOR_AGENTS = (
    ("decisions.json", "Size, kind, milestone and skipped steps.", "agent", "1 Intent"),
    ("spec/readiness.md", "Is the design ready to build?", "review agents", "2 UX plan"),
    ("checklist.md", "Which gaps did the facts and plan still have?", "agent", "4 Tech plan"),
    ("analyze.md", "Do facts and plan cover every ask?", "agent", "4 Tech plan"),
    ("challenge.md", "What could be wrong with the plan?", "agent", "4 Tech plan"),
    ("done.json", "The approved criteria as data.", "approve step", "4 Tech plan"),
    ("lock.json", "Proof the criteria did not move after approval.", "approve step", "4 Tech plan"),
    ("verify/", "What each gate run checked and how it ended.", "gate script", "5 Build"),
    ("validation.md", "Does each fact have proof?", "builder", "6 Milestone"),
    ("findings.md", "What did review find, and was it fixed?", "review agents", "6 Milestone"),
    ("asks/", "The requests exactly as they were given.", "agent", "1 Intent"),
)


def _name(change: Path, rel: str) -> str:
    return f"[{rel}]({rel})" if (change / rel).exists() else f"{rel} (not written yet)"


def readme(change: Path, stage: str) -> str:
    """The reading map of one change folder; regenerated, never edited by hand."""
    latest = sorted(change.glob("handover*.md"))
    pick = f"[{latest[-1].name}]({latest[-1].name})" if latest else "no handover yet"
    out = [
        f"# {change.name}",
        "",
        "GENERATED by `sdlc_status.py readme`; do not edit by hand. Ids such as F1 or Q3 are "
        f"explained by `sdlc_status.py ids {change.name}`.",
        "",
        "## Start here",
        "",
        f"- **Understand the change:** read {_name(change, 'intent.md')}.",
        f"- **Review it:** read {_name(change, 'facts.md')}, then {_name(change, 'plan.md')}.",
        f"- **Pick up the work:** the change is at stage {stage}; read {pick}.",
        "",
        "## What each document answers",
        "",
        "| Document | Question it answers | Who writes it | Stage | A newcomer needs it |",
        "|---|---|---|---|---|",
    ]
    out += [f"| {_name(change, f)} | {q} | {w} | {s} | {n} |" for f, q, w, s, n in DOCS]
    out += [
        "",
        "## For agents",
        "",
        "Working files. A newcomer can skip all of them.",
        "",
        "| Document | Question it answers | Who writes it | Stage |",
        "|---|---|---|---|",
    ]
    out += [f"| {_name(change, f)} | {q} | {w} | {s} |" for f, q, w, s in FOR_AGENTS]
    return "\n".join(out) + "\n"
