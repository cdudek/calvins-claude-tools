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
        """@F76 @2026-11-14-tracker-session-cleanup The mod starts nothing of its own: no note, prompt, tool call or registered tool, agent, command, request or MCP call, and nothing is armed."""
        # Its two writes run through `$.process.run` after the owner's press, and the cleanup skill's script acts only on the owner's answer (F66).
        forbidden = r"\$\.(session\.(append|send)|prompt\.submit|tool\.(call|register)|command\.run|agent\.spawn|http\.|process\.spawn|mcp\.)"
        # One exception, the owner's (2026-11-14): the band's Board button runs the mod's own `/tracker web` command.
        own = "$.command.run({ command: 'tracker', args: 'web' })"
        bad = [f"{f.name}:{n}" for f in SOURCES for n, line in enumerate(f.read_text().splitlines(), 1) if re.search(forbidden, line) and own not in line]
        self.assertEqual(bad, [])

    def test_every_process_the_mod_runs_is_an_allowed_source(self):
        """@F69 @2026-11-14-tracker-session-cleanup every `$.process.run` call under hooks/tracker starts claude, git, gh, bd or tail; the few others are named with their reason."""
        sources = {"claude", "git", "gh", "bd", "tail"}
        # Beyond F69's list, each with its reason: grep reads the transcripts F69 allows; uname and the opener belong to the Board button.
        named = {"grep": "reads transcripts", "uname": "Board: picks the opener", "opener": "Board: opens the page"}
        call = re.compile(r"(?:\$\.process\.run|\bout)\(\s*(?:\$,\s*)?(\[\s*'([^']+)'|gitArgv\(|argv\b|\[opener\b)")
        every = re.compile(r"\$\.process\.run\(|\bout\(\$,")
        found, bad = set(), []
        for f in SOURCES:
            text = f.read_text()
            self.assertEqual(len(every.findall(text)), len(call.findall(text)), f"{f.name}: a process call this scan cannot read")
            for m in call.finditer(text):
                head = m.group(2) or ("git" if m.group(1).startswith("gitArgv") else "opener" if m.group(1).startswith("[opener") else None)
                if head is None:  # `argv`: the helper's own parameter, fed by the `out($, ...)` calls scanned here
                    continue
                found.add(head)
                if head not in sources | named.keys():
                    bad.append(f"{f.name}: {head}")
        self.assertEqual(bad, [])
        self.assertTrue({"claude", "git", "gh", "tail"} <= found, found)

    def test_no_file_registers_a_classic_hook(self):
        bad = [f"{f.name}:{n}" for f in SOURCES for n, line in enumerate(f.read_text().splitlines(), 1) if "classic." in line]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
