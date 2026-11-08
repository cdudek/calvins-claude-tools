"""No skill, agent, reference or hook in the plugin publishes to claude.ai: no Artifact tool, no Claude Docs, no hosted
canvas. Pages and documents are local markdown or HTML (owner rule). A claude.ai Linear connector is not publishing.
Run: python3 -m unittest discover -s tests"""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent / "plugins/cct"
SCANNED = ("skills", "agents", "references", "hooks", "docs")
FORBIDDEN = re.compile(
    r"artifact-design|artifact-capabilities|Artifact tool|ArtifactData|ArtifactComments|Claude_Docs|Claude Docs"
    r"|claude\.ai/(?:artifact|code/artifact)|publish[a-z]* (?:it |this |the |a )?(?:as|to) (?:an? )?artifact"
    r"|<artifact URL>|\bRepublish\b",
    re.I,
)

# The one thing allowed to name the forbidden tools is the rule that forbids them.
PROHIBITION = re.compile(r"never publish|no Artifact, no Claude Docs", re.I)


class NoClaudeAiPublishing(unittest.TestCase):
    def test_no_publishing_site_in_the_plugin(self):
        hits = []
        for d in SCANNED:
            for f in sorted((PLUGIN / d).rglob("*")):
                if not f.is_file() or f.is_symlink():
                    continue
                try:
                    text = f.read_text()
                except (UnicodeDecodeError, OSError):
                    continue
                for n, line in enumerate(text.splitlines(), 1):
                    if FORBIDDEN.search(line) and not PROHIBITION.search(line):
                        hits.append(f"{f.relative_to(PLUGIN)}:{n}: {line.strip()[:100]}")
        self.assertEqual(hits, [])

    def test_the_decision_page_is_a_local_file(self):
        text = (PLUGIN / "references/decision-page.md").read_text()
        self.assertIn("localStorage", text)
        self.assertIn("answers.json", text)


if __name__ == "__main__":
    unittest.main()
