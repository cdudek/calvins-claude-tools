"""Usage: python3 eval_corpus.py <repo root> <out dir>

Builds the recall-eval corpus from a repo's own past changes (`changes/*/`, and
`changes/archive/**` when present): every fact (`F1`, `N2`) of a change's facts.md becomes a rule file
`<out>/corpus/specs/<change slug>/rules/R<n>.md`, and every ask of its intent.md becomes a case in
`<out>/fixture.json` whose `relevant` rules are the facts that cite that ask. Where the owner's words live: the ask table of `intent.md`, then any `A<n>` row or `A<n>: "words"`
line in `spec/**/*.md` and `asks/**/*.md`, so a change with no intent.md still yields cases (its
facts file may be `spec.md`). Real owner words are
the query; each ask is also split into sentences, one case each, with the same labels.

Stdlib only. The labels are the repo's own ask-to-fact traceability, not a reviewer's judgement:
see living-spec.md for what that does and does not prove.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FACT = re.compile(r"^- (?:\[.\] )?\*{0,2}([FN]\d+)\*{0,2}:?\s*(?:\(([^)]*)\))?\s*(.*)$")
ASK_ROW = re.compile(r"^\| (A\d+) \|.*?\| \"(.*)\"[^|]*\|")
ASK_LINE = re.compile(r"^[\s|>*-]*\*{0,2}(A\d+)\*{0,2}\b[^\"\n]*?\"([^\"\n]{12,})\"")


def changes(root: Path) -> list[Path]:
    base = root / "changes"
    found = [
        p for p in sorted(base.iterdir()) if p.is_dir() and re.match(r"\d{4}-\d\d-\d\d", p.name)
    ]
    arch = base / "archive"
    if arch.is_dir():
        found += [p.parent for p in sorted(arch.rglob("facts.md"))]
    return found


def cap_of(name: str) -> str:
    return re.sub(r"^\d{4}-\d\d-\d\d-", "", name)


def asks_of(ch: Path) -> dict[str, str]:
    """{A<n>: the owner's words}, from intent.md first, then spec/ and asks/ (first one wins)."""
    files = [
        ch / "intent.md",
        *sorted((ch / "spec").rglob("*.md")),
        *sorted((ch / "asks").rglob("*.md")),
    ]
    found: dict[str, str] = {}
    for f in files:
        if f.is_file():
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                m = ASK_ROW.match(line) or ASK_LINE.match(line)
                if m:
                    found.setdefault(m.group(1), m.group(2).replace('\\"', '"'))
    return found


def build(root: Path, out: Path) -> dict:
    rules, cases, n = [], [], 0
    for ch in changes(root):
        facts = next((f for f in (ch / "facts.md", ch / "spec.md") if f.is_file()), None)
        asks = asks_of(ch)
        if not (facts and asks):
            continue
        cap, by_ask = cap_of(ch.name), {}
        for line in facts.read_text(encoding="utf-8").splitlines():
            m = FACT.match(line)
            if not m or not m.group(3).strip():
                continue
            n += 1
            rid = f"R{n}"
            rules.append((cap, n, m.group(3).strip()))
            for a in re.findall(r"A\d+", m.group(2) or ""):
                by_ask.setdefault(a, []).append(rid)
        intent = ch / "intent.md"
        title = (
            re.search(r"^# Intent: (.*)$", intent.read_text(encoding="utf-8"), re.M)
            if intent.is_file()
            else None
        )
        (out / "corpus/specs" / cap).mkdir(parents=True, exist_ok=True)
        (out / "corpus/specs" / cap / "manifest.yaml").write_text(
            f"purpose: {title.group(1) if title else cap}\naliases: [{', '.join(cap.split('-'))}]\n"
        )
        for a, words in asks.items():
            if a not in by_ask:
                continue
            parts = [s.strip() for s in re.split(r"(?<=[.?!])\s+", words) if len(s.split()) >= 4]
            for i, q in enumerate([words] + (parts if len(parts) > 1 else [])):
                cases.append(
                    {"id": f"{cap}/{a}" + (f".{i}" if i else ""), "query": q, "relevant": by_ask[a]}
                )
    for cap, num, text in rules:
        d = out / "corpus/specs" / cap / "rules"
        d.mkdir(parents=True, exist_ok=True)
        first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0][:120]
        (d / f"R{num}.md").write_text(
            f"---\nid: R{num}\nsummary: {first.replace(chr(10), ' ')}\nstatus: live\nproof: manual\nevidence: derived from the change's facts\n---\n{text}\n"
        )
    (out / "fixture.json").write_text(json.dumps(cases, indent=1) + "\n")
    return {"rules": len(rules), "cases": len(cases)}


if __name__ == "__main__":
    print(build(Path(sys.argv[1]), Path(sys.argv[2])))
