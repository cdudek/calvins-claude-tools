#!/usr/bin/env python3
"""Usage: discover-tests.py <repo>

Read-only. Proposes the plan's `tests` block from the repo's manifests (package.json, pyproject.toml,
pytest.ini/setup.cfg/tox.ini, requirements*.txt, go.mod, Cargo.toml, Makefile) and shows CI test commands as evidence.
Rules: `references/test-strategy.md`. The block is checked with check-plan.py's tests_errs before it prints.

Output sections:
  the `tests` JSON block
  -#-#- NOTES -#-#-   one `- ` line per fact the owner should confirm
Exit 0 on a valid block, 1 when the proposal is invalid, 2 on bad usage.
"""
import importlib.util
import json
import os
import re
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("check_plan", HERE / "check-plan.py")
check_plan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_plan)

SKIP = {".git", "node_modules", ".venv", "venv", "vendor", "dist", "build", "target", ".next", "__pycache__", ".factory", ".worktrees", "coverage", ".tox"}
LOCKED = re.compile(r"e2e|playwright|cypress", re.I)
TESTFILE = re.compile(r"(^test_.*\.py$|_test\.(py|go)$|\.(test|spec)\.[cm]?[jt]sx?$)")
MUTATING = re.compile(r"watch|update|fix|format|write|ui|debug|dev|gen|record|headed|snapshot", re.I)
SRC_EXT = (".py", ".go", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")
CI_CMD = re.compile(r"\b(npm (run )?test|(pnpm|yarn|bun) (run )?test\S*|vitest|jest|pytest|go test|cargo (nextest|test)|playwright|mocha|make test\S*|tox|nx |turbo )", re.I)


def read(p):
    try:
        return Path(p).read_text(errors="replace")
    except OSError:
        return ""


def serial(text):
    m = check_plan.SERIAL.search(text)
    return m.group(0) if m else None


def walk(repo, depth=4):
    for root, dirs, files in os.walk(repo):
        rel = Path(root).relative_to(repo)
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith("."))
        if len(rel.parts) >= depth:
            dirs[:] = []
        yield rel, files


def is_test_path(rel):
    return any(x in ("test", "tests", "__tests__", "e2e", "spec") for x in rel.parts) or bool(TESTFILE.search(rel.name))


class Proposal:
    def __init__(self):
        self.suites, self.triggers, self.notes, self.related = [], [], [], None

    def suite(self, name, cmd, lock=False):
        if any(s["name"] == name or s["cmd"] == cmd for s in self.suites):
            return
        self.suites.append({"name": name, "cmd": cmd, **({"lock": True} if lock else {})})

    def has(self, name):
        return any(s["name"] == name for s in self.suites)

    def block(self):
        return {**({"related": self.related} if self.related else {}), "triggers": self.triggers, "suites": self.suites}


def node(repo, pr):
    pkg = repo / "package.json"
    if not pkg.is_file():
        return None
    try:
        j = json.loads(read(pkg))
    except ValueError:
        pr.notes.append("package.json is not valid JSON; skipped")
        return None
    scripts, deps = j.get("scripts") or {}, {**(j.get("dependencies") or {}), **(j.get("devDependencies") or {})}
    lock = {"pnpm-lock.yaml": ("pnpm run", "pnpm exec"), "yarn.lock": ("yarn", "yarn"), "bun.lockb": ("bun run", "bunx"), "bun.lock": ("bun run", "bunx")}
    run, exe = next((v for f, v in lock.items() if (repo / f).exists()), ("npm run", "npx"))
    stack = "vitest" if "vitest" in deps else "jest" if "jest" in deps else None
    if stack == "vitest":
        pr.related = f"{exe} vitest related --run {{files}}"
    elif stack == "jest":
        pr.related = f"{exe} jest --findRelatedTests {{files}}"
    bodies = " ".join(str(v) for v in scripts.values())
    if "test" in scripts:
        pr.suite("unit", f"{run} test")
    elif stack == "vitest":
        pr.suite("unit", f"{exe} vitest run")
    elif stack == "jest":
        pr.suite("unit", f"{exe} jest")
    elif "mocha" in deps:
        pr.suite("unit", f"{exe} mocha")
    for name in sorted(scripts):
        body = str(scripts[name])
        if name == "test" or MUTATING.search(name):
            continue
        if re.fullmatch(r"test[:-].+|e2e(:.*)?|arch(:.*)?", name):
            pr.suite(name.replace(":", "-"), f"{run} {name}", lock=bool(LOCKED.search(name) or LOCKED.search(body)))
        elif re.fullmatch(r"lint(:.*)?", name) and (name == "lint" or "lint" not in scripts):
            pr.suite(name.replace(":", "-"), f"{run} {name}")
        elif re.fullmatch(r"typecheck|type-check|tsc|check-types", name):
            pr.suite("typecheck", f"{run} {name}")
    for f in sorted(repo.glob("vitest.*.config.*")) + sorted(repo.glob("jest.*.config.*")):
        tool = f.name.split(".")[0]
        if f.name in bodies:
            continue
        pr.suite(f"{tool}-{f.name.split('.')[1]}", f"{exe} {tool} {'run ' if tool == 'vitest' else ''}--config {f.name}", lock=bool(LOCKED.search(f.name)))
    if ("@playwright/test" in deps or list(repo.glob("playwright.config.*"))) and not any(s.get("lock") for s in pr.suites):
        pr.suite("e2e", f"{exe} playwright test", lock=True)
    if any(s.get("lock") for s in pr.suites):
        pr.notes.append("E2E suites are lock: true (shared app server or port); drop it only if each worker gets its own")
    if serial(bodies):
        pr.notes.append(f"a package.json script switches parallelism off ({serial(bodies)}); the plan checker only sees the command, fix the script")
    return stack or ("mocha" if "mocha" in deps else None)


def python(repo, pr):
    files = ("pyproject.toml", "setup.cfg", "pytest.ini", "tox.ini", "requirements.txt", "requirements-dev.txt", "requirements-test.txt")
    text = "\n".join(read(repo / n) for n in files)
    if not text.strip():
        if any(f.startswith("test_") and f.endswith(".py") for _, fs in walk(repo, 6) for f in fs):
            pr.suite("unit", "pytest")
            pr.notes.append("test_*.py files found but no Python manifest: `pytest` from the repo root is a guess, compare with CI")
            return "pytest"
        return None
    if "pytest" not in text:
        pr.notes.append("Python manifests without pytest; no Python suite proposed, ask the owner")
        return None
    py = "uv run " if (repo / "uv.lock").exists() else ""
    xdist = "xdist" in text
    pr.suite("unit", f"{py}pytest -n auto" if xdist else f"{py}pytest")
    pr.notes.append("pytest: `related` is not set (pytest-testmon takes no file list); finish relies on triggers")
    if not xdist:
        pr.notes.append("pytest-xdist is not declared, so the suite runs in one process; consider adding it")
    try:
        tool = tomllib.loads(read(repo / "pyproject.toml")).get("tool", {})
    except tomllib.TOMLDecodeError:
        tool = {}
    if "ruff" in tool or "ruff" in text:
        pr.suite("lint", f"{py}ruff check .")
    if "mypy" in tool or "mypy" in text:
        pr.suite("typecheck", f"{py}mypy .")
    return "pytest"


def golang(repo, pr):
    if not (repo / "go.mod").is_file():
        return None
    pr.suite("unit", "go test ./...")
    pr.suite("vet", "go vet ./...")
    pr.notes.append("go: `related` is not set (go test takes packages, not files); finish relies on triggers")
    return "go"


def rust(repo, pr):
    if not (repo / "Cargo.toml").is_file():
        return None
    pr.suite("unit", "cargo nextest run" if (repo / ".config" / "nextest.toml").exists() else "cargo test")
    pr.suite("clippy", "cargo clippy --all-targets")
    pr.notes.append("cargo: `related` is not set; finish relies on triggers")
    return "cargo"


def make(repo, pr):
    targets = set(re.findall(r"^([A-Za-z][\w-]*)\s*:(?!=)", read(repo / "Makefile"), re.M))
    for kind, names in (("unit", ("test",)), ("lint", ("lint",)), ("typecheck", ("typecheck", "types")), ("e2e", ("e2e", "test-e2e"))):
        n = next((x for x in names if x in targets), None)
        if n and not pr.has(kind):
            pr.suite(kind, f"make {n}", lock=kind == "e2e")


def ci(repo, pr):
    seen = []
    for f in sorted((repo / ".github" / "workflows").glob("*.y*ml")):
        for line in read(f).splitlines():
            c = re.sub(r"^\s*(-\s*)?(run:\s*)?[|>]?-?\s*", "", line).strip()
            if CI_CMD.search(c) and not c.startswith(("#", "name:", "uses:", "if:")) and c not in seen:
                seen.append(c)
    if seen:
        pr.notes.append("CI runs: " + "; ".join(seen[:8]) + (" ..." if len(seen) > 8 else "") + " (compare with the suites above)")


def reader_cmd(stack, hits):
    if not hits:
        return None
    if stack in ("vitest", "jest", "pytest"):
        shown = hits if len(hits) <= 5 else [Path(os.path.commonpath([h.parent for h in hits]))]
        return {"vitest": "npx vitest run ", "jest": "npx jest ", "pytest": "pytest "}[stack] + " ".join(h.as_posix() for h in shown)
    if stack == "go":
        return "go test " + " ".join(sorted({"./" + h.parent.as_posix() if h.parent.parts else "." for h in hits}))
    return None


def triggers(repo, stack, pr):
    cands, tests = {}, []
    for rel, files in walk(repo):
        tests += [rel / f for f in files if is_test_path(rel / f) and f.endswith(SRC_EXT)]
        if is_test_path(rel / "x"):
            continue
        if rel.name in ("migrations", "migrate", "schema", "schemas"):
            cands[f"{rel.as_posix()}/**"] = rel.name
        elif rel == Path("config"):
            cands["config/**"] = "config"
        for f in files:
            if re.fullmatch(r"schema\.(prisma|sql|rb|graphql|json)", f):
                cands[(rel / f).as_posix()] = f
            elif f.endswith(".sql") and rel.name not in ("migrations", "migrate") and rel.parts:
                cands[f"{rel.as_posix()}/*.sql"] = rel.name
    asks = []
    for path, key in sorted(cands.items()):
        base = Path(path.split("*")[0].rstrip("/"))
        needle = "/".join(base.parts[-2:]) if len(base.parts) > 1 else key + "/"
        ext = {"pytest": (".py",), "go": (".go",)}.get(stack, SRC_EXT[2:])
        hits = [t for t in tests if t.suffix in ext and needle in read(repo / t)]
        run = reader_cmd(stack, hits) if len(hits) <= 15 else None
        if run:
            pr.triggers.append({"paths": [path], "run": run, "why": f"{len(hits)} test file(s) mention {needle}"})
        else:
            asks.append(path + (f" ({len(hits)} test files mention it, too many to name)" if hits else ""))
    if asks:
        pr.notes.append("ask the owner: these paths may couple tests through files, but no single reader was detected: " + ", ".join(asks[:6]) + (f" and {len(asks) - 6} more" if len(asks) > 6 else ""))


def discover(repo):
    pr = Proposal()
    stacks = [s for s in (node(repo, pr), python(repo, pr), golang(repo, pr), rust(repo, pr)) if s]
    make(repo, pr)
    ci(repo, pr)
    if not pr.suites:
        pr.notes.append("no test setup detected: ask the owner for the test, lint and typecheck commands")
        subs = [(r / m).as_posix() for r, fs in walk(repo, 2) for m in fs if m in ("package.json", "pyproject.toml", "go.mod", "Cargo.toml") and r.parts]
        if subs:
            pr.notes.append("manifests in subdirectories, run discovery per package: " + ", ".join(subs[:8]))
    if len(stacks) > 1:
        pr.notes.append("more than one stack found (" + ", ".join(stacks) + "): check every suite")
    triggers(repo, stacks[0] if stacks else None, pr)
    return pr


def main(argv):
    if len(argv) != 2 or not Path(argv[1]).is_dir():
        print("usage: discover-tests.py <repo>", file=sys.stderr)
        return 2
    pr = discover(Path(argv[1]).resolve())
    block = pr.block()
    errs = check_plan.tests_errs(block)
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 1
    print(json.dumps(block, indent=2))
    print("-#-#- NOTES -#-#-")
    for n in pr.notes:
        print(f"- {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
