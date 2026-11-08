"""Install the per-repository Decision4 contract, map, template and pinned reference.

Checker code and fixtures live only in the shared hosting repository. This module
contains no checker, does not access the network and preserves repository policy.
"""

import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
BUNDLE = TEMPLATES / "decision4"
HEADING = "## How hard is it to undo this PR after merging?"
STARTER_MAP = (BUNDLE / "boundary-map.yaml").read_text()
CONTRACT = (BUNDLE / "AGENTS-section.md").read_text()


def pr_section():
    text = (TEMPLATES / "github/PULL_REQUEST_TEMPLATE.md").read_text()
    start = text.index("<!--\nDecision4 writing rules:")
    end = text.index("</details>", start) + len("</details>")
    return text[start:end] + "\n"


def merge_pr_template(text):
    """Refresh H2/H3 recovery blocks without losing human checklists or records."""
    match = re.search(r"^#{2,3} How hard is it to undo this PR after merging\?\s*$", text, re.M)
    if not match:
        return text.rstrip() + "\n\n" + pr_section()
    start = text.rfind("<!--\nDecision4 writing rules:", 0, match.start())
    if start < 0:
        start = match.start()
    details = text.find("</details>", match.end())
    if details >= 0:
        end = details + len("</details>")
    else:
        following = re.search(r"^#{1,3} ", text[match.end() :], re.M)
        end = match.end() + following.start() if following else len(text)
    prefix, suffix = text[:start].rstrip(), text[end:].lstrip("\n")
    replacement = pr_section()
    # An existing human decision record stays authoritative. Do not duplicate it.
    if re.search(r"^## Decision record\s*$", suffix, re.M):
        replacement = re.sub(r"## Decision record\n.*?(?=<details>)", "", replacement, flags=re.S)
    return (prefix + "\n\n" if prefix else "") + replacement + ("\n" + suffix if suffix else "")


def template_paths(root):
    candidates = []
    for directory in (root, root / ".github", root / "docs"):
        if not directory.is_dir():
            continue
        for path in directory.iterdir():
            if path.is_file() and path.name.lower() in (
                "pull_request_template.md",
                "pull_request_template.txt",
            ):
                candidates.append(path)
            elif path.is_dir() and path.name.lower() == "pull_request_template":
                candidates.extend(
                    p for p in path.iterdir() if p.is_file() and p.suffix.lower() in (".md", ".txt")
                )
    return sorted(candidates) or [root / ".github/PULL_REQUEST_TEMPLATE.md"]


def contract_changes(root):
    """One verbatim upstream contract in AGENTS.md; Claude imports that source."""
    path = root / "AGENTS.md"
    text = path.read_text() if path.exists() else ""
    changes = []
    heading = "## Decision4 handoff contract (v1)"
    if heading not in text:
        changes.append((path, text.rstrip() + ("\n\n" if text else "") + CONTRACT))
    claude = root / "CLAUDE.md"
    if claude.exists():
        old = claude.read_text()
        updated = old
        if heading in old:
            # Move the complete contract section; keep other repo-owned sections.
            updated = re.sub(
                r"^## Decision4 handoff contract \(v1\)\n.*?(?=^## |\Z)",
                "",
                updated,
                flags=re.M | re.S,
            )
        if not re.search(r"^@AGENTS\.md\s*$", updated, re.M):
            updated = updated.rstrip() + "\n\n@AGENTS.md\n"
        if updated != old:
            changes.append((claude, updated))
    return changes


def asset_changes(root):
    """Exactly the consuming-repo set: no checker code or test fixtures."""
    changes = contract_changes(root)
    dest = root / "boundary-map.yaml"
    if not dest.exists():
        changes.append((dest, STARTER_MAP))
    # A local gate gets a fetch fragment, never a parallel Actions check.
    local_gate = (root / "scripts/ci-local").exists()
    relative = "ci-local-decision4.sh" if local_gate else "decision4.yml"
    target = root / (
        "scripts/decision4-shared.sh" if local_gate else ".github/workflows/decision4.yml"
    )
    content = (BUNDLE / relative).read_text()
    if not target.exists() or target.read_text() != content:
        changes.append((target, content))
    if local_gate:
        gate = root / "scripts/ci-local"
        old = gate.read_text()
        marker = "# Decision4 shared dispatch (managed by adoption)"
        if marker not in old and re.match(r"^#!.*(?:bash|/sh)\b", old):
            first, rest = old.split("\n", 1)
            dispatch = "\n".join(
                [
                    marker,
                    'if [ "${1:-}" = "--decision4" ]; then',
                    "  shift",
                    '  exec bash "$(dirname "$0")/decision4-shared.sh" "$@"',
                    "fi",
                    "",
                ]
            )
            changes.append((gate, first + "\n" + dispatch + rest))
    for path in template_paths(root):
        text = (
            path.read_text()
            if path.exists()
            else (TEMPLATES / "github/PULL_REQUEST_TEMPLATE.md").read_text()
        )
        updated = merge_pr_template(text)
        if not path.exists() or text != updated:
            changes.append((path, updated))
    return changes
