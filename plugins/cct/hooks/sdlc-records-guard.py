#!/usr/bin/env python3
"""PreToolUse: agents neither read nor write the run records (~/.sdlc/runs/ or $SDLC_HOME/runs/). Only the runner does.

This hook is the barrier: receipts and checkpoints carry no signature, so nothing but this guard keeps an agent from
writing a pass. It stops a careless or confused agent, not a hostile process of the same user (design 3.2).

Rule for Bash: a command that mentions the sdlc folder in any form is denied unless the WHOLE command is exactly one
invocation of this plugin's own runner, or of the same runner shipped by a sibling kit the owner named in
`<claude config dir>/sdlc-sibling-kits.json` ({"plugins": ["<plugin name>"]}, default: none). A sibling runner counts only at the exact
path `<plugin>/skills/sdlc-run/runner/sdlc.py` of an installed copy: a directory under the plugin cache
(`<config dir>/plugins/cache/<marketplace>/<plugin>/<version>`) or an install path listed in
`<config dir>/plugins/installed_plugins.json`, with symlinks resolved. Deny on a match, stay silent otherwise.
"""
import fnmatch
import json
import os
import re
import shlex
import sys

RUNNER = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "sdlc-run", "runner", "sdlc.py"))
RUNNER_DIR = os.path.dirname(RUNNER)
OPERATORS = set(";&|<>()")
MODULES = ("contract", "store", "engine", "verify", "discover", "release", "clean", "deps", "board", "graph", "sdlc", "ci")


SUFFIX = os.path.join("skills", "sdlc-run", "runner", "sdlc.py")


def claude_home() -> str:
    return os.path.realpath(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"))


def sibling_runners() -> set[str]:
    """Real paths of the runner of each named sibling plugin, taken from where Claude Code installed it, never from a pattern the
    command could match."""
    base = claude_home()
    try:
        with open(os.path.join(base, "sdlc-sibling-kits.json"), encoding="utf-8") as f:
            names = {n for n in (json.load(f).get("plugins") or []) if isinstance(n, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", n)}
    except (OSError, ValueError, AttributeError):
        return set()
    roots: list[tuple[str, str]] = []  # (plugin name, installed plugin directory)
    cache = os.path.join(base, "plugins", "cache")
    for n in names:
        for mkt in glob_dirs(cache):
            for ver in glob_dirs(os.path.join(mkt, n)):
                roots.append((n, ver))
    try:
        with open(os.path.join(base, "plugins", "installed_plugins.json"), encoding="utf-8") as f:
            for key, installs in (json.load(f).get("plugins") or {}).items():
                for i in installs if isinstance(installs, list) else []:
                    if key.split("@")[0] in names and isinstance(i, dict) and isinstance(i.get("installPath"), str):
                        roots.append((key.split("@")[0], i["installPath"]))
    except (OSError, ValueError, AttributeError):
        pass
    out = set()
    for n, root in roots:
        real = os.path.realpath(os.path.join(root, SUFFIX))
        # the file must really live in that plugin's own installed directory: a symlink leading elsewhere is not the plugin
        if real == os.path.join(os.path.realpath(root), SUFFIX) and os.path.isfile(real):
            out.add(real)
    return out


def glob_dirs(path: str) -> list[str]:
    try:
        return [os.path.join(path, d) for d in sorted(os.listdir(path)) if os.path.isdir(os.path.join(path, d))]
    except OSError:
        return []


def roots() -> tuple[str, str, str]:
    home = os.environ.get("SDLC_HOME") or os.path.expanduser("~/.sdlc")
    return home, os.path.join(home, "runs"), os.path.realpath(os.path.join(home, "runs"))


def deny(why: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": why}}))


def under(path: str, root: str) -> bool:
    p = os.path.realpath(os.path.expanduser(os.path.expandvars(path))) if path else ""
    return bool(p) and (p == root or p.startswith(root + os.sep))


def glob_reaches(pattern: str, home: str) -> bool:
    """The glob can name the records folder, its runs folder or anything below them: each component of the pattern is
    matched against the same component of <home>/runs (`~/.s?lc/runs/*/contract.json` included)."""
    pat = pattern.split("/")
    for h in {home, os.path.realpath(home), os.path.expanduser("~/.sdlc")}:
        target = (h.rstrip("/") + "/runs").split("/")
        if len(pat) < len(h.rstrip("/").split("/")):  # shorter than the folder itself: an ancestor glob such as `/Users/*`
            continue
        if all(k >= len(target) or fnmatch.fnmatchcase(target[k], comp) for k, comp in enumerate(pat)):
            return True
    return False


def mentions(cmd: str, words: list[str], home: str, runs: str, real: str) -> bool:
    if ".sdlc" in cmd or "SDLC_HOME" in cmd or home in cmd or runs in cmd or real in cmd:
        return True
    for w in words:
        if ".sdlc" in w or home in w:
            return True
        if re.search(r"[*?\[]", w):  # a glob that could name the folder: every path component is tested
            g = os.path.expanduser(os.path.expandvars(w))
            base = g.rsplit("/", 1)[-1]
            if base.startswith(".") and fnmatch.fnmatchcase(".sdlc", base):
                return True
            if glob_reaches(g, home):
                return True
    return False


def exec_target(words: list[str]) -> str:
    """The program a simple command really runs, looking through VAR=value prefixes, `env` and `python [flags]`."""
    ws = [w for w in words]
    while ws and (re.match(r"[A-Za-z_]\w*=", ws[0]) or os.path.basename(ws[0]) == "env" or ws[0].startswith("-")):
        ws.pop(0)
    if ws and os.path.basename(ws[0]).startswith("python"):
        ws.pop(0)
        while ws and ws[0].startswith("-"):
            ws.pop(0)
    return ws[0] if ws else ""


def touches_runner(cmd: str, words: list[str]) -> bool:
    """The command runs the runner (sdlc.py, ./sdlc, any copy of it), or is a python program that names its folder or
    imports one of its modules. Prose that merely contains these words is not a touch."""
    if os.path.basename(exec_target(words)) in ("sdlc", "sdlc.py"):
        return True
    program = re.search(r"\bpython[0-9.]*\b|<<| -c\b", cmd)
    if not program:
        return False
    mods = "|".join(MODULES)
    return bool(RUNNER_DIR in cmd or "skills/sdlc-run/runner" in cmd or re.search(r"\bsdlc\.py\b", cmd)
                or re.search(rf"\b(import|from)\s+({mods})\b", cmd)
                or (re.search(r"\b(sys\.path|__import__|importlib|runpy)\b", cmd) and re.search(rf"\b({mods})\b", cmd)))


def is_exact_runner(cmd: str, words: list[str]) -> bool:
    """One simple command, no chaining, no expansion, and argv resolves to this plugin's own runner or an installed sibling kit's."""
    if "\n" in cmd or "\r" in cmd or "`" in cmd or "$" in cmd:
        return False
    if any(set(w) <= OPERATORS for w in words) or not words:
        return False
    argv = words
    if os.path.basename(argv[0]).startswith("python") and len(argv) > 1:
        argv = argv[1:]
    first = os.path.expanduser(argv[0])
    # a relative `./sdlc.py` is not the plugin's runner; a sibling kit's runner counts at its installed path only
    return os.path.isabs(first) and (os.path.realpath(first) == RUNNER or os.path.realpath(first) in sibling_runners())


def main() -> None:
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return
    home, runs, real = roots()
    ti, tool = ev.get("tool_input") or {}, ev.get("tool_name")
    cwd = ev.get("cwd") or os.getcwd()
    msg = f"The run records under {runs} belong to the sdlc runner; use `sdlc.py` instead of reading or editing them."
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit", "Read"):
        if under(ti.get("file_path") or ti.get("notebook_path") or "", real):
            deny(msg)
    elif tool in ("Grep", "Glob"):
        p = ti.get("path") or ""
        pat = ti.get("pattern") or ""
        rp = os.path.realpath(os.path.expanduser(p)) if p else ""
        ancestor = bool(rp) and real.startswith(rp.rstrip(os.sep) + os.sep)  # a recursive search from above reaches the records
        if under(p, real) or ancestor or ".sdlc" in pat or under(pat, real):
            deny(msg)
    elif tool == "Bash":
        cmd = ti.get("command") or ""
        try:
            lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
            lex.whitespace_split = True
            words = list(lex)
            parsed = True
        except ValueError:
            words, parsed = [], False
        if "SDLC_GATE_CMD" in cmd:  # the owner's approval program is not an agent's to set
            return deny("SDLC_GATE_CMD may not be set: the approval gate is a fixed command.")
        inside = under(cwd, real)
        runner = touches_runner(cmd, words) if parsed else bool(re.search(r"\bpython", cmd) and ("sdlc.py" in cmd or RUNNER_DIR in cmd))
        if not (mentions(cmd, words, home, runs, real) or inside or runner):
            return
        if parsed and is_exact_runner(cmd, words):
            if "boards" in words and mentions(cmd, words, home, runs, real):  # boards writes files: never into the records
                return deny("`sdlc boards` may not name the run records folder (index, rows and --out write files).")
            return
        if runner and not (mentions(cmd, words, home, runs, real) or inside):
            return deny("The sdlc runner or its modules are only run as exactly one plain call of the plugin's own runner by its absolute path: "
                        "no env prefix (HOME=, PATH=, PYTHONPATH=, env), no python -c or heredoc importing it, no relative ./sdlc.")
        deny(msg + (" (the command could not be parsed)" if not parsed else " (only one plain runner call may touch them)"))


main()
