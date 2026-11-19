"""Rebuild kit-hashes.json: the sha256[:16] of every hook and script the kit ever shipped, by the
path it is installed at. `adopt --migrate` replaces a kit-owned file only when its hash is listed
here; a file that matches no shipped version is the repo's own and stays.

    python3 kit_hashes.py [--write] REPO...     # every commit of each REPO is walked
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

DATA = Path(__file__).with_name("kit-hashes.json")
# <plugin>/skills/<sdlc-run or its old name run-sdlc>/templates/(hooks|scripts)/<file>, at any commit
TEMPLATE = re.compile(r"/(?:sdlc-run|run-sdlc)/templates/(hooks|scripts)/([^/]+)$")
INSTALLED = {"hooks": ".claude/hooks", "scripts": "scripts"}


def walk(repo: Path) -> dict[str, set[str]]:
    git = lambda *a, **k: subprocess.run(["git", *a], cwd=repo, capture_output=True, **k)  # noqa: E731
    commits = git("rev-list", "--all", text=True).stdout.split()
    found: dict[str, str] = {}  # blob -> installed path
    for commit in commits:
        for line in git("ls-tree", "-r", commit, text=True).stdout.splitlines():
            meta, _, path = line.partition("\t")
            if m := TEMPLATE.search("/" + path):
                found[meta.split()[2]] = f"{INSTALLED[m.group(1)]}/{m.group(2)}"
    hashes: dict[str, set[str]] = {}
    for blob, rel in found.items():
        data = git("cat-file", "blob", blob).stdout
        hashes.setdefault(rel, set()).add(hashlib.sha256(data).hexdigest()[:16])
    return hashes


def main() -> None:
    merged: dict[str, set[str]] = {k: set(v) for k, v in json.loads(DATA.read_text()).items()} if DATA.exists() else {}
    for repo in sys.argv[1:]:
        if repo != "--write":
            for rel, hs in walk(Path(repo)).items():
                merged.setdefault(rel, set()).update(hs)
    for kind, installed in INSTALLED.items():  # the templates as they stand now, committed or not
        for f in (Path(__file__).parents[1] / "templates" / kind).glob("*"):
            if f.is_file():
                merged.setdefault(f"{installed}/{f.name}", set()).add(hashlib.sha256(f.read_bytes()).hexdigest()[:16])
    text = json.dumps({k: sorted(v) for k, v in sorted(merged.items())}, indent=1) + "\n"
    if "--write" in sys.argv:
        DATA.write_text(text)
    print(f"{len(merged)} files, {sum(len(v) for v in merged.values())} hashes")


if __name__ == "__main__":
    main()
