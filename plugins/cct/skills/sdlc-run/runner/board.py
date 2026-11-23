"""Board extraction and real-surface UI checks (design 3.5). Step 6 fills this in; browser_available is used by verify."""
from __future__ import annotations

import os
import shutil


def browser_available(executable: str | None = None) -> tuple[bool, str]:
    if executable:
        return (os.access(executable, os.X_OK), f"{executable} is not executable")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, "python playwright is not installed"
    try:
        with sync_playwright() as p:
            path = p.chromium.executable_path
        return (os.path.exists(path), "chromium is not downloaded (playwright install chromium)")
    except Exception as e:  # noqa: BLE001 - any failure to locate the browser is an env problem
        return False, str(e)[:100]
