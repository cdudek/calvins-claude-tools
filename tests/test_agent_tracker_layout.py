"""The agent-tracker mod keeps its layout: core/ is pure and no file hooks a classic event.
The mod's own tests (`claude plugin test`) cannot read the disk, so the source scans live here.
Run: python3 -m unittest discover -s tests"""
import re
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "plugins/agent-tracker/hooks/tracker"
CORE = HOOKS / "core"
SOURCES = sorted(p for p in HOOKS.rglob("*") if p.suffix in {".ts", ".tsx"})


class AgentTrackerLayout(unittest.TestCase):
    def test_core_exists(self):
        self.assertTrue(list(CORE.glob("*.ts")), "hooks/tracker/core/ holds the shared pure module")

    def test_core_imports_only_itself_and_types(self):
        bad = []
        for f in CORE.rglob("*.ts"):
            for n, line in enumerate(f.read_text().splitlines(), 1):
                m = re.match(r"\s*(?:import|export)\b.*?\bfrom\s+['\"]([^'\"]+)['\"]", line)
                if not m:
                    continue
                target, is_type = m.group(1), re.match(r"\s*(?:import|export) type\b", line)
                if not (target.startswith("./") or (is_type and target in {"claude-code", "../types"})):
                    bad.append(f"{f.name}:{n}: {line.strip()}")
        self.assertEqual(bad, [])

    def test_core_touches_no_engine_file_process_or_clock(self):
        bad = []
        for f in CORE.rglob("*.ts"):
            for n, line in enumerate(f.read_text().splitlines(), 1):
                if re.search(r"\$\.|\$:|Date\.now|new Date\(|Math\.random|performance\.now|setTimeout|setInterval", line):
                    bad.append(f"{f.name}:{n}: {line.strip()}")
        self.assertEqual(bad, [])

    def test_the_mod_never_writes_to_a_session_or_opens_a_port(self):
        # The mod only observes (F62, F65): no note, prompt, tool call, agent, command, request or spawned process of its own.
        forbidden = r"\$\.(session\.(append|send)|prompt\.submit|tool\.call|command\.run|agent\.spawn|http\.|process\.spawn|mcp\.)"
        # One exception, the owner's (2026-11-14): the band's Board button runs the mod's own `/tracker web` command.
        own = "$.command.run({ command: 'tracker', args: 'web' })"
        bad = [f"{f.name}:{n}" for f in SOURCES for n, line in enumerate(f.read_text().splitlines(), 1) if re.search(forbidden, line) and own not in line]
        self.assertEqual(bad, [])

    def test_no_file_registers_a_classic_hook(self):
        bad = [f"{f.name}:{n}" for f in SOURCES for n, line in enumerate(f.read_text().splitlines(), 1) if "classic." in line]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
