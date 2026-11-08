"""Shared, offline Decision4 scaffolding for project setup and SDLC adoption.

The checker and good/bad cases come from cdudek/blueprints PR #20. Repo policy
and check invocation remain repo-owned; the fixture map describes synthetic paths.
"""
from pathlib import Path
import re

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
BUNDLE = TEMPLATES / "decision4"
HEADING = "### How hard is it to undo this PR after merging?"
STARTER_MAP = (BUNDLE / "boundary-map.yaml").read_text()


def pr_section():
    text = (TEMPLATES / "github/PULL_REQUEST_TEMPLATE.md").read_text()
    return text[text.index("<!--\nDecision4 writing rules:"):]


def merge_pr_template(text):
    """Refresh only the Decision4 block, retaining the repo's other content."""
    start = text.find("<!--\nDecision4 writing rules:")
    heading = text.find(HEADING)
    if heading < 0:
        return text.rstrip() + "\n\n" + pr_section()
    if start < 0 or start > heading:
        start = heading
    # The shipped block ends at </details>; older blocks end at the next heading.
    details = text.find("</details>", heading)
    next_heading = re.search(r"^#{1,3} ", text[heading + len(HEADING):], re.M)
    end = heading + len(HEADING) + next_heading.start() if next_heading else len(text)
    if details >= 0 and details < end:
        end = details + len("</details>")
    prefix, suffix = text[:start].rstrip(), text[end:].lstrip("\n")
    return (prefix + "\n\n" if prefix else "") + pr_section() + ("\n" + suffix if suffix else "")


def template_paths(root):
    candidates = []
    for directory in (root, root / ".github", root / "docs"):
        if directory.is_dir():
            for path in directory.iterdir():
                if path.is_file() and path.name.lower() in ("pull_request_template.md", "pull_request_template.txt"):
                    candidates.append(path)
                elif path.is_dir() and path.name.lower() == "pull_request_template":
                    candidates.extend(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in (".md", ".txt"))
    return sorted(candidates) or [root / ".github/PULL_REQUEST_TEMPLATE.md"]


def asset_changes(root):
    """Return (path, text) edits, leaving boundary maps and existing runners alone."""
    changes = []
    for source in sorted(BUNDLE.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(BUNDLE)
        dest = root / relative
        if dest.exists() and relative.as_posix() in ("boundary-map.yaml", "tests/decision4/run.sh"):
            continue
        text = source.read_text()
        if not dest.exists() or dest.read_text() != text:
            changes.append((dest, text))
    for path in template_paths(root):
        text = path.read_text() if path.exists() else (TEMPLATES / "github/PULL_REQUEST_TEMPLATE.md").read_text()
        updated = merge_pr_template(text)
        if not path.exists() or text != updated:
            changes.append((path, updated))
    return changes
