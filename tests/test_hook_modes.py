"""Claude invokes a registered hook file directly, so git must track it as executable (100755)."""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def modes() -> dict[str, str]:
    out = subprocess.run(["git", "ls-files", "-s"], cwd=ROOT, capture_output=True, text=True).stdout
    return {line.split("\t")[1]: line.split()[0] for line in out.splitlines()}


class HookModes(unittest.TestCase):
    def test_every_registered_hook_file_is_100755_in_git(self):
        settings = json.loads((ROOT / ".claude/settings.json").read_text())
        registered = {
            m[1]
            for groups in settings["hooks"].values()
            for g in groups
            for h in g["hooks"]
            for m in [re.search(r"(\.claude/hooks/[\w.-]+)", h["command"])]
            if m
        }
        tracked = modes()
        self.assertTrue(registered)
        for rel in sorted(registered):
            self.assertEqual(tracked.get(rel), "100755", rel)

    def test_every_hook_script_the_kit_installs_is_100755_in_git(self):
        for rel, mode in modes().items():
            if rel.startswith(".claude/hooks/") and rel.endswith(".sh"):
                self.assertEqual(mode, "100755", rel)


if __name__ == "__main__":
    unittest.main()
