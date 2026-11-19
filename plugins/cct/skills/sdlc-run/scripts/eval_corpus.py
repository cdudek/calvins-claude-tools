"""Usage: python3 eval_corpus.py <repo root> <out dir>

Builds the recall-eval corpus from a repo's own past changes (`changes/*/`, and
`changes/archive/**` when present): every fact (`F1`, `N2`) of a change's facts.md becomes a rule file
`<out>/corpus/specs/<change slug>/rules/R<n>.md`, and every ask of its intent.md becomes a case in
`<out>/fixture.json` whose `relevant` rules are the facts that cite that ask. Real owner words are
the query; each ask is also split into sentences, one case each, with the same labels.

Stdlib only. The labels are the repo's own ask-to-fact traceability, not a reviewer's judgement:
see living-spec.md for what that does and does not prove.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FACT = re.compile(r"^- \[.\] \*\*([FN]\d+)\*\*\s*(?:\(([^)]*)\))?\s*(.*)$")


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


def build(root: Path, out: Path) -> dict:
    rules, cases, n = [], [], 0
    for ch in changes(root):
        facts, intent = ch / "facts.md", ch / "intent.md"
        if not (facts.exists() and intent.exists()):
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
        title = re.search(r"^# Intent: (.*)$", intent.read_text(encoding="utf-8"), re.M)
        (out / "corpus/specs" / cap).mkdir(parents=True, exist_ok=True)
        (out / "corpus/specs" / cap / "manifest.yaml").write_text(
            f"purpose: {title.group(1) if title else cap}\naliases: [{', '.join(cap.split('-'))}]\n"
        )
        for line in intent.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\| (A\d+) \|.*?\| \"(.*)\"[^|]*\|", line)
            if not m or m.group(1) not in by_ask:
                continue
            words = m.group(2).replace('\\"', '"')
            parts = [s.strip() for s in re.split(r"(?<=[.?!])\s+", words) if len(s.split()) >= 4]
            for i, q in enumerate([words] + (parts if len(parts) > 1 else [])):
                cases.append(
                    {
                        "id": f"{cap}/{m.group(1)}" + (f".{i}" if i else ""),
                        "query": q,
                        "relevant": by_ask[m.group(1)],
                    }
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
