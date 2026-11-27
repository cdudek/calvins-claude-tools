#!/usr/bin/env python3
"""Usage: check_coupled.py <task dir>... - lists each scored fail_to_pass hidden test whose imports from src/ name a symbol that neither
exists in the start tree (following `export * from` re-exports, relative or through the `@/` alias for src/) nor appears in the change folder's markdown or the ticket. Such a test can
only pass when the builder guesses the reference commit's names: add it to task.json `implementation_coupled`. Exit 1 when any is found.
"""
import json
import posixpath
import re
import sys
import tarfile
from pathlib import Path

IMPORT = re.compile(r"import\s*(?:type\s*)?\{([^}]*)\}\s*from\s*'([^']*src/[^']*)'")
REEXPORT = re.compile(r"export\s*\*\s*from\s*'([^']+)'")


def module_text(src, path, seen=None):
    """The text of module `path` (no extension) plus every module it re-exports with `export * from`."""
    seen = seen if seen is not None else set()
    if path in seen:
        return ""
    seen.add(path)
    text = src.get(path + ".ts") or src.get(path + "/index.ts") or ""
    here = path if (path + "/index.ts") in src else posixpath.dirname(path)  # an index module resolves relative to its own folder
    for rel in REEXPORT.findall(text):
        if rel.startswith("@/"):  # the usual tsconfig alias for src/
            text += module_text(src, "src/" + rel[2:], seen)
        elif rel.startswith("."):
            text += module_text(src, posixpath.normpath(posixpath.join(here, rel)), seen)
    return text


def symbols(spec):
    for name in (x.strip() for x in spec.split(",")):
        if name:
            yield name.replace("type ", "").split(" as ")[0].strip()


def coupled(task_dir):
    """[(hidden file, [missing symbol@module])] for the task's scored fail_to_pass files."""
    task_dir = Path(task_dir)
    t = json.loads((task_dir / "task.json").read_text())
    plan_dir = posixpath.dirname(t["plan"])
    src, spec = {}, ""
    with tarfile.open(task_dir / "start.tar.gz") as tf:
        for m in tf:
            if not m.isfile():
                continue
            if m.name.startswith("src/") and m.name.endswith(".ts"):
                src[m.name] = tf.extractfile(m).read().decode(errors="ignore")
            elif m.name.startswith(plan_dir) and m.name.endswith(".md"):
                spec += tf.extractfile(m).read().decode(errors="ignore")
    ticket = task_dir / "ticket-delta.md"
    spec += ticket.read_text() if ticket.exists() else ""
    skip = set(t.get("implementation_coupled") or []) | set(t.get("out_of_scope") or [])
    out = []
    for f in t.get("fail_to_pass", []):
        if f in skip:
            continue
        missing = []
        for names, mod in IMPORT.findall((task_dir / "hidden-tests" / f).read_text()):
            path = "src/" + mod.split("src/", 1)[1]
            text = module_text(src, path)
            missing += [f"{s}@{path}" for s in symbols(names)
                        if not re.search(r"\b" + re.escape(s) + r"\b", text) and not re.search(r"\b" + re.escape(s) + r"\b", spec)]
        if missing:
            out.append((f, missing))
    return out


if __name__ == "__main__":
    found = False
    for d in sys.argv[1:]:
        for f, missing in coupled(d):
            found = True
            print(f"{Path(d).name}: COUPLED {f} {missing}")
    sys.exit(1 if found else 0)
