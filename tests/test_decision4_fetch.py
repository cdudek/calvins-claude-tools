"""Consumer fetches are checksum checked, cached and fail closed without vendoring code."""

import hashlib
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins/cct/skills/sdlc-run"
SPEC = importlib.util.spec_from_file_location(
    "assets", SKILL / "scripts/decision4_assets.py"
)
ASSETS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ASSETS)


class SharedFetch(unittest.TestCase):
    def test_local_gate_dispatch_and_checksum_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "scripts").mkdir()
            gate = root / "scripts/ci-local"
            gate.write_text('#!/usr/bin/env bash\nprintf "full gate\\n"\n')
            for path, text in ASSETS.asset_changes(root):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            self.assertFalse((root / ".github/workflows/decision4.yml").exists())
            self.assertFalse((root / ".github/scripts/decision4.py").exists())
            self.assertFalse((root / "tests/decision4").exists())
            self.assertIn('"--decision4"', gate.read_text())
            self.assertEqual(ASSETS.asset_changes(root), [])
            helper = root / "scripts/decision4-shared.sh"
            # A tiny stand-in fetched by mocked curl; no shared-check implementation.
            payload = 'print("validated")\n'
            digest = hashlib.sha256(payload.encode()).hexdigest()
            import re

            helper.write_text(
                re.sub(
                    r"checker_sha256=[0-9a-f]+",
                    "checker_sha256=" + digest,
                    helper.read_text(),
                )
            )
            (root / "payload").write_text(payload)
            (root / "bin").mkdir()
            curl = root / "bin/curl"
            curl.write_text(
                '#!/usr/bin/env bash\necho fetch >> "$FETCH_LOG"\ncat "$PAYLOAD"\n'
            )
            curl.chmod(0o755)
            log = root / "fetch.log"
            env = {
                **os.environ,
                "PATH": str(root / "bin") + os.pathsep + os.environ["PATH"],
                "FETCH_LOG": str(log),
                "PAYLOAD": str(root / "payload"),
            }

            def run():
                return subprocess.run(
                    ["bash", str(gate), "--decision4"],
                    cwd=root,
                    env=env,
                    text=True,
                    capture_output=True,
                )

            first = run()
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout.strip(), "validated")
            self.assertEqual(run().returncode, 0)
            self.assertEqual(log.read_text().splitlines(), ["fetch"])
            cached = next((root / ".git/ci-local").glob("decision4-*.py"))
            cached.write_text('raise SystemExit("unverified cache executed")\n')
            self.assertEqual(run().returncode, 0)
            self.assertEqual(len(log.read_text().splitlines()), 2)
            cached.unlink()
            (root / "payload").write_text(
                'raise SystemExit("unverified download executed")\n'
            )
            failed = run()
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("checksum mismatch", failed.stderr)
            self.assertFalse(cached.exists())


if __name__ == "__main__":
    unittest.main()
