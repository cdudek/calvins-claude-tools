import fcntl
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import heavy


class Heavy(unittest.TestCase):
    def test_lock_excludes_a_second_holder_and_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "heavy.lock"
            with heavy.locked(lock):
                with open(lock, "a") as f, self.assertRaises(BlockingIOError):
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with open(lock, "a") as f:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_cli_runs_the_command_and_returns_its_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "CFACTORY_EVAL_HEAVY_LOCK": str(Path(tmp) / "l")}
            r = subprocess.run([sys.executable, heavy.__file__, sys.executable, "-c", "import sys; sys.exit(3)"], env=env)
            self.assertEqual(r.returncode, 3)


if __name__ == "__main__":
    unittest.main()
