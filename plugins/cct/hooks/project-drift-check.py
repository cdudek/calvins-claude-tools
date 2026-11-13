#!/usr/bin/env python3
"""SessionStart: one line when this repo's .claude/settings.json drifts from the plugins it declares.

Silent unless the repo declares cct (a key `cct@...` in enabledPlugins, or a `cct` marketplace). Runs the
project-repository-run script's read-only --check on the settings only. Never blocks: any failure exits 0
with no output. Prints Claude Code's `systemMessage` JSON so the owner sees the line."""
import contextlib
import io
import json
import os
import sys
from pathlib import Path

try:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    declared = json.loads((root / ".claude/settings.json").read_text())
    if not (any(str(k).startswith("cct@") for k in declared.get("enabledPlugins", {}))
            or "cct" in declared.get("extraKnownMarketplaces", {})):
        sys.exit(0)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills/project-repository-run/scripts"))
    import project_setup

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = project_setup.main(["--root", str(root), "--check"])
    items = [line[4:] for line in out.getvalue().splitlines() if line.startswith("  - ")]
    if code and items:
        more = f" (+{len(items) - 1} more)" if len(items) > 1 else ""
        print(json.dumps({"systemMessage": f"cct: .claude/settings.json drifts from the declared plugins: {items[0]}{more}. "
                                           "Run /cct:project-repository-run."}))
except SystemExit:
    pass
except Exception:  # a notice must never stop a session
    pass
