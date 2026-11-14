"""The Decision4 files a repo gets: boundary map, AGENTS.md section, PR-template section.

Decision4 is advisory: no workflow, no status check. Existing files are
never overwritten; a repo that already has the heading keeps its own text.
"""

from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
BUNDLE = TEMPLATES / "decision4"
HEADING = "## Decision4: how hard is this change to undo?"
PR_HEADING = "## How hard is it to undo this PR after merging?"
PR_MARKER = "<!-- Decision4 is advisory"
STARTER_MAP = (BUNDLE / "boundary-map.yaml").read_text()
CONTRACT = (BUNDLE / "AGENTS-section.md").read_text()


def pr_section():
    text = (TEMPLATES / "github/PULL_REQUEST_TEMPLATE.md").read_text()
    return text[text.index(PR_MARKER) :]


def template_paths(root):
    names = ("pull_request_template.md", "pull_request_template.txt")
    found = [
        p
        for d in (root, root / ".github", root / "docs")
        if d.is_dir()
        for p in d.iterdir()
        if p.is_file() and p.name.lower() in names
    ]
    return sorted(found) or [root / ".github/PULL_REQUEST_TEMPLATE.md"]


def asset_changes(root):
    """(path, new text) for each missing piece; nothing present is rewritten."""
    changes = []
    agents = root / "AGENTS.md"
    text = agents.read_text() if agents.exists() else ""
    if HEADING not in text:
        changes.append((agents, text.rstrip() + ("\n\n" if text else "") + CONTRACT))
    claude = root / "CLAUDE.md"
    if claude.exists():
        old = claude.read_text()
        if not any(line.strip() == "@AGENTS.md" for line in old.splitlines()):
            changes.append((claude, old.rstrip() + "\n\n@AGENTS.md\n"))
    boundary = root / "boundary-map.yaml"
    if not boundary.exists():
        changes.append((boundary, STARTER_MAP))
    for path in template_paths(root):
        if not path.exists():
            changes.append((path, (TEMPLATES / "github/PULL_REQUEST_TEMPLATE.md").read_text()))
        elif PR_HEADING not in (old := path.read_text()):
            changes.append((path, old.rstrip() + "\n\n" + pr_section()))
    return changes
