"""Hand the close's visual and convergence findings to the fix round the triager runs.

Usage: python3 close_findings.py <review state dir> <findings.md> --change <change id>

`cct:review-fixset-triager` reads only `findings.json` and `verdicts.json` of the code review's
state directory, so a clean code review plus a blocking visual or convergence finding would give
an empty fix set. This appends every open, non-advisory item of `findings.md` (id kept: B2, V1,
C1) to `findings.json` as a high-severity finding and to `verdicts.json` as confirmed, skipping
ids already there and items the owner already settled (`Accept as is`, `Defer to milestone <n>`).
Prints how many it added. stdlib only; reads marks.py from the plugin's templates.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "templates" / "scripts"))
from marks import FINDING_ID, owner_decisions  # noqa: E402

ITEM = re.compile(rf"^\s*[-*] \[ \] \*\*({FINDING_ID})\*\*\s*(.*)$", re.M)
LOCATION = re.compile(r"([\w./-]+\.\w+):(\d+)")


def advisory(text: str) -> str:
    m = re.search(r"^#{2,3} Advisory\s*$(.*?)(?=^#{1,3} |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def main(argv: list[str]) -> int:
    if len(argv) != 5 or argv[3] != "--change":
        print(__doc__)
        return 2
    state, md, change = Path(argv[1]), Path(argv[2]), argv[4]
    text = md.read_text(encoding="utf-8")
    items = ITEM.findall(text.replace(advisory(text), ""))
    settled = {
        k for k, (kind, _) in owner_decisions(Path.cwd(), change, md, "**{}**").items()
        if kind in ("accepted", "deferred")
    }  # fmt: skip
    findings = json.loads((state / "findings.json").read_text(encoding="utf-8"))
    verdicts = json.loads((state / "verdicts.json").read_text(encoding="utf-8"))
    have = {str(f.get("id")) for f in findings.get("findings", [])}
    added = 0
    for fid, body in items:
        if fid in have or fid in settled:
            continue
        place = LOCATION.search(body)
        findings.setdefault("findings", []).append(
            {
                "id": fid,
                "file": place[1] if place else "",
                "line": place[2] if place else "",
                "severity": "high",
                "dimension": "close",
                "source": "close",
                "body": body,
                "reversibility": "cheap",
            }
        )
        verdicts.append({"id": fid, "verdict": "confirmed"})
        added += 1
    (state / "findings.json").write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
    (state / "verdicts.json").write_text(json.dumps(verdicts, indent=2) + "\n", encoding="utf-8")
    print(f"close findings added to the fix set: {added}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
