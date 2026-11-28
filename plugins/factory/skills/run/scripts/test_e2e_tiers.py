"""The test strategy end to end on real toolchains: discover-tests.py proposes the `tests` block, task-step.py finish/gate run it.
No fake commands: pytest and cargo run for real (each case skips when its tool is missing)."""
import copy
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import test_task_step as T  # noqa: E402  (the plan/repo fixture helpers)

DISCOVER = Path(__file__).parent / "discover-tests.py"


@pytest.fixture(autouse=True)
def marks(tmp_path, monkeypatch):
    d = tmp_path / "marks"
    d.mkdir()
    monkeypatch.setenv("MARK_DIR", str(d))
    monkeypatch.setenv("CARGO_TARGET_DIR", str(Path(os.environ.get("TMPDIR") or "/tmp") / "factory-e2e-tiers-cargo"))
    return d


def lines(path):
    return path.read_text().splitlines() if path.exists() else []


def discover(tmp_path, files):
    """Run the real discover-tests.py on a scratch copy of the project; returns its `tests` block."""
    proj = tmp_path / "proj"
    for name, text in files.items():
        f = proj / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    p = subprocess.run([sys.executable, str(DISCOVER), str(proj)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.split("-#-#- NOTES -#-#-")[0])


def mark_suites(block):
    """Each suite appends one line to $MARK_DIR/<name> before the real command, so a test can count its runs."""
    for s in block["suites"]:
        s["cmd"] = f'echo x >> "$MARK_DIR/{s["name"]}" && {s["cmd"]}'
    return block


def task_repo(tmp_path, files, block, task_files, node_modules=None):
    """node_modules: a toolchain cache dir linked into the repo and (through the plan's `setup`) into every worktree."""
    plan = copy.deepcopy(T.PLAN)
    plan["tests"] = block
    if node_modules:
        plan["setup"] = f"ln -s {shlex.quote(str(node_modules))} node_modules"
    plan["milestones"][0]["tasks"] = [{"id": "T1", "covers": ["req-1"], "files": task_files, "check": "true"}]
    tmp_path.mkdir(parents=True, exist_ok=True)
    repo, sha = T.milestone_repo(tmp_path, plan, extra=files)
    if node_modules:
        (repo / "node_modules").symlink_to(node_modules)  # the gate runs in the repo itself, where `setup` does not
    assert T.ok(repo, sha, "target")[0] == 0
    assert T.ok(repo, sha, "start", "T1")[0] == 0
    return repo, sha, repo / ".worktrees" / f"{T.SLUG}-M1-T1"


# ---------- Python / pytest ----------

IGNORE = "__pycache__/\n.pytest_cache/\n*.pyc\ntarget/\nCargo.lock\n"
MARKED = "import os\n\n\ndef _mark(name):\n    d = os.environ.get('MARK_DIR')\n    if d:\n        open(os.path.join(d, name), 'a').write('x\\n')\n\n\n"
OLD = "from pathlib import Path\n\n\ndef test_tables():\n    lines = (Path(__file__).parent.parent / 'schema/tables.txt').read_text().split()\n    assert len(lines) == {n}\n"
PY = {
    ".gitignore": IGNORE,
    "pyproject.toml": '[project]\nname = "calc"\nversion = "0.1.0"\ndependencies = []\n[dependency-groups]\ndev = ["pytest"]\n'
                      '[tool.pytest.ini_options]\npythonpath = ["src"]\ntestpaths = ["tests"]\n',
    "src/calc/__init__.py": "",
    "src/calc/add.py": "def add(a, b):\n    return a + b\n",
    "src/calc/mul.py": "def mul(a, b):\n    return a * b\n",
    "tests/test_add.py": MARKED + "from calc.add import add\n\n\ndef test_add():\n    _mark('add-ran')\n    assert add(2, 3) == 5\n",
    "tests/test_mul.py": MARKED + "from calc.mul import mul\n\n\ndef test_mul():\n    _mark('mul-ran')\n    assert mul(2, 3) == 6\n",
    "tests/test_old.py": OLD.format(n=2),
    "schema/tables.txt": "users\norders\n",
}
LEGACY = {"src/calc/legacy.py": "VALUE = 1\n", "tests/test_legacy.py": "def test_legacy_broken():\n    assert False, 'red since before the task'\n"}


@pytest.fixture
def py_block(tmp_path):
    if not shutil.which("pytest"):
        pytest.skip("pytest is not installed")
    block = discover(tmp_path, PY)
    assert block["unit"] == "pytest {tests}" and [s["name"] for s in block["suites"]] == ["unit"]
    trig = [t for t in block["triggers"] if t["paths"] == ["schema/**"]]  # discovery sees test_old.py reading schema/
    if not trig:
        block["triggers"].append({"paths": ["schema/**"], "run": "pytest tests/test_old.py", "why": "test_old.py counts the lines"})
        trig = block["triggers"][-1:]
    assert trig[0]["run"] == "pytest tests/test_old.py"
    trig[0]["edits"] = ["tests/test_old.py"]
    return block


def test_python_task_runs_only_the_nearby_tests_and_merges(tmp_path, marks, py_block):
    repo, sha, wt = task_repo(tmp_path, PY, mark_suites(py_block), ["src/calc/add.py"])
    T.build(wt, "src/calc/add.py", "def add(a, b):\n    return sum((a, b))\n")
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests OK 1 commands (nearby tests)" in out and "FINISH OK T1 INTEGRITY OK" in out, out
    assert lines(marks / "add-ran") == ["x"] and not (marks / "mul-ran").exists()  # test_mul.py never ran
    assert (repo / "src/calc/add.py").read_text().count("sum") == 1  # merged


def test_python_task_that_breaks_mul_is_blocked(tmp_path, py_block):
    repo, sha, wt = task_repo(tmp_path, PY, mark_suites(py_block), ["src/calc/mul.py"])
    T.build(wt, "src/calc/mul.py", "def mul(a, b):\n    return a + b\n")
    before = T.git(repo, "rev-parse", "HEAD")
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 1 and "FINISH FAIL T1 tests: pytest tests/test_mul.py" in out and "test_mul" in out, out
    assert T.git(repo, "rev-parse", "HEAD") == before


def test_python_schema_trigger_blocks_until_the_counting_test_grows(tmp_path, py_block):
    repo, sha, wt = task_repo(tmp_path / "a", PY, mark_suites(copy.deepcopy(py_block)), ["schema/tables.txt"])
    T.build(wt, "schema/tables.txt", "users\norders\ninvoices\n")
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 1 and "FINISH FAIL T1 tests: pytest tests/test_old.py" in out and "assert 3 == 2" in out, out
    repo, sha, wt = task_repo(tmp_path / "b", PY, mark_suites(copy.deepcopy(py_block)), ["schema/tables.txt"])
    T.build(wt, "schema/tables.txt", "users\norders\ninvoices\n")
    T.build(wt, "tests/test_old.py", OLD.format(n=3))  # allowed by the trigger's `edits`, not by the task's files
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests OK" in out and "INTEGRITY OK" in out, out


def test_python_preexisting_red_test_is_excused_at_finish_and_at_gate(tmp_path, py_block):
    files = {**PY, **LEGACY}
    repo, sha, wt = task_repo(tmp_path, files, mark_suites(py_block), ["src/calc/legacy.py"])
    T.build(wt, "src/calc/legacy.py", "VALUE = 2\n")  # nearby rule picks tests/test_legacy.py, red on the base too
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests PRE-EXISTING pytest tests/test_legacy.py" in out and "FINISH OK T1" in out, out
    code, out = T.ok(repo, sha, "gate")
    assert code == 0 and "GATE tests PRE-EXISTING unit" in out and "GATE tests FAIL" not in out, out


def test_python_gate_runs_each_suite_once_and_reports_ok(tmp_path, marks, py_block):
    block = mark_suites(py_block)
    block["suites"].append({"name": "again", "cmd": 'echo x >> "$MARK_DIR/again" && pytest -q tests/test_add.py'})
    repo, sha, wt = task_repo(tmp_path, PY, block, ["src/calc/add.py"])
    T.build(wt, "src/calc/add.py", "def add(a, b):\n    return sum((a, b))\n")
    assert T.ok(repo, sha, "finish", "T1")[0] == 0
    code, out = T.ok(repo, sha, "gate")
    assert code == 0 and "GATE tests OK unit" in out and "GATE tests OK again" in out, out
    assert lines(marks / "unit") == ["x"] and lines(marks / "again") == ["x"]


# ---------- Rust / cargo ----------

RS = {
    ".gitignore": IGNORE,
    "Cargo.toml": '[package]\nname = "calc"\nversion = "0.1.0"\nedition = "2021"\n',
    "src/lib.rs": "pub mod add;\npub mod mul;\n",
    "src/add.rs": "pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n\n#[cfg(test)]\nmod tests {\n    use super::*;\n    #[test]\n    fn adds() {\n        assert_eq!(add(2, 3), 5);\n    }\n}\n",
    "src/mul.rs": "pub fn mul(a: i32, b: i32) -> i32 {\n    a * b\n}\n\n#[cfg(test)]\nmod tests {\n    use super::*;\n    #[test]\n    fn muls() {\n        assert_eq!(mul(2, 3), 6);\n    }\n}\n",
    "tests/integration.rs": "use calc::{add::add, mul::mul};\n\n#[test]\nfn both() {\n    assert_eq!(add(1, 2) + mul(2, 3), 9);\n}\n",
}
BROKEN_MUL = RS["src/mul.rs"].replace("a * b", "a + b")


@pytest.fixture
def rs_block(tmp_path):
    if not shutil.which("cargo"):
        pytest.skip("cargo is not installed")
    block = discover(tmp_path, RS)
    assert "unit" not in block and "related" not in block  # tests are not files: finish has nothing to select
    block["suites"] = [s for s in block["suites"] if s["name"] == "unit"]  # clippy is a lint suite, not what is under test
    assert block["suites"][0]["cmd"] == "cargo test"
    return mark_suites(block)


def test_rust_change_passes_finish_and_gate(tmp_path, marks, rs_block):
    repo, sha, wt = task_repo(tmp_path, RS, rs_block, ["src/add.rs"])
    T.build(wt, "src/add.rs", RS["src/add.rs"].replace("a + b", "b + a"))
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests OK 1 commands (triggers)" in out and "FINISH OK T1" in out, out  # discover's catch-all crate trigger
    code, out = T.ok(repo, sha, "gate")
    assert code == 0 and "GATE tests OK unit" in out and lines(marks / "unit") == ["x"], out


def test_rust_breaking_change_is_caught_at_finish_with_discovers_block(tmp_path, rs_block):
    repo, sha, wt = task_repo(tmp_path, RS, rs_block, ["src/mul.rs"])
    T.build(wt, "src/mul.rs", BROKEN_MUL)
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 1 and "FINISH FAIL T1 tests: cargo test" in out and "muls" in out, out


def test_rust_breaking_change_is_caught_at_finish_with_a_src_trigger(tmp_path, rs_block):
    rs_block["triggers"].append({"paths": ["src/**"], "run": "cargo test", "why": "no related-tests tool for cargo"})
    repo, sha, wt = task_repo(tmp_path, RS, rs_block, ["src/mul.rs"])
    T.build(wt, "src/mul.rs", BROKEN_MUL)
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 1 and "FINISH FAIL T1 tests: cargo test" in out and "muls" in out, out


# ---------- Go (skips when go is missing; written against discover's proposal, never run on this machine) ----------

GO = {
    "go.mod": "module calc\n\ngo 1.21\n",
    "add.go": "package calc\n\nfunc Add(a, b int) int { return a + b }\n",
    "add_test.go": "package calc\n\nimport \"testing\"\n\nfunc TestAdd(t *testing.T) {\n\tif Add(2, 3) != 5 {\n\t\tt.Fatal(\"add\")\n\t}\n}\n",
    "mul.go": "package calc\n\nfunc Mul(a, b int) int { return a * b }\n",
    "mul_test.go": "package calc\n\nimport \"testing\"\n\nfunc TestMul(t *testing.T) {\n\tif Mul(2, 3) != 6 {\n\t\tt.Fatal(\"mul\")\n\t}\n}\n",
}


def test_go_change_runs_the_package_and_merges(tmp_path):
    if not shutil.which("go"):
        pytest.skip("go is not installed")
    block = discover(tmp_path, GO)
    assert block["unit"] == "go test {tests}"
    repo, sha, wt = task_repo(tmp_path, GO, mark_suites(block), ["add.go"])
    T.build(wt, "add.go", "package calc\n\nfunc Add(a, b int) int { return b + a }\n")
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests OK" in out, out
    assert T.ok(repo, sha, "gate")[0] == 0


# ---------- TypeScript: vitest and jest (real npm toolchain, cached outside the repo; skips offline or when the install takes > 120 s) ----------

NODE_PINS = {"vitest": "5.1.2", "jest": "30.5.2", "ts-jest": "29.4.15", "typescript": "5.9.3", "@types/jest": "30.0.0", "@types/node": "24.0.0"}


@pytest.fixture(scope="session")
def node_modules():
    if not shutil.which("npm"):
        pytest.skip("npm is not installed")
    key = hashlib.sha256(json.dumps(NODE_PINS, sort_keys=True).encode()).hexdigest()[:12]
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "factory-e2e-node" / key
    if (cache / "node_modules/.bin/vitest").exists() and (cache / "node_modules/.bin/jest").exists():
        return cache / "node_modules"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "package.json").write_text(json.dumps({"name": "factory-e2e-node", "private": True, "devDependencies": NODE_PINS}))
    try:
        p = subprocess.run(["npm", "install", "--no-audit", "--no-fund", "--prefer-offline"], cwd=cache, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        pytest.skip("npm install took longer than 120 s")
    if p.returncode != 0:
        pytest.skip(f"npm install failed (offline?): {p.stderr[-200:]}")
    return cache / "node_modules"


MARK_TS = "import { appendFileSync } from 'node:fs';\n\nexport const mark = (name: string) => process.env.MARK_DIR && appendFileSync(`${process.env.MARK_DIR}/${name}`, 'x\\n');\n"
TS_IGNORE = "node_modules\n.vite/\n"
TSCONFIG = json.dumps({"compilerOptions": {"strict": True, "target": "es2022", "module": "esnext", "moduleResolution": "bundler", "noEmit": True,
                                           "types": ["node"], "skipLibCheck": True}, "include": ["src", "test"]})
VT = {
    ".gitignore": TS_IGNORE,
    "package.json": json.dumps({"name": "calc", "private": True, "type": "module", "scripts": {"test": "vitest run", "typecheck": "tsc --noEmit"},
                                "devDependencies": {"vitest": NODE_PINS["vitest"], "typescript": NODE_PINS["typescript"]}}),
    "tsconfig.json": TSCONFIG,
    "src/add.ts": "export const add = (a: number, b: number): number => a + b;\n",
    "src/util/format.ts": "export const format = (n: number): string => `${n}`;\n",
    "src/mul.ts": "import { format } from './util/format';\n\nexport const mul = (a: number, b: number): number => Number(format(a * b));\n",
    "test/mark.ts": MARK_TS,
    "test/add.test.ts": "import { expect, test } from 'vitest';\nimport { add } from '../src/add';\nimport { mark } from './mark';\n\n"
                        "test('add', () => {\n  mark('add-ran');\n  expect(add(2, 3)).toBe(5);\n});\n",
    "test/mul.test.ts": "import { expect, test } from 'vitest';\nimport { mul } from '../src/mul';\nimport { mark } from './mark';\n\n"
                        "test('mul', () => {\n  mark('mul-ran');\n  expect(mul(2, 3)).toBe(6);\n});\n",
    "test/schema.test.ts": "import { readFileSync } from 'node:fs';\nimport { expect, test } from 'vitest';\nimport { mark } from './mark';\n\n"
                           "test('tables', () => {\n  mark('schema-ran');\n  const n = readFileSync(new URL('../schema/tables.txt', import.meta.url), 'utf8').split('\\n').filter(Boolean).length;\n  expect(n).toBe({n});\n});\n",
    "schema/tables.txt": "users\norders\n",
}
SCHEMA_TEST = "test/schema.test.ts"


def vt_files(n=2):
    return {**VT, SCHEMA_TEST: VT[SCHEMA_TEST].replace("{n}", str(n))}


@pytest.fixture
def vt_block(tmp_path):
    block = discover(tmp_path, vt_files())
    assert block["related"] == "npx vitest related --run --passWithNoTests {files}"
    assert {s["name"] for s in block["suites"]} == {"unit", "typecheck"}
    trig = [t for t in block["triggers"] if t["paths"] == ["schema/**"]]
    if not trig:  # discovery cannot see a test reading schema/ through a URL
        block["triggers"].append({"paths": ["schema/**"], "run": f"npx vitest run {SCHEMA_TEST}", "why": "schema.test.ts counts the lines"})
        trig = block["triggers"][-1:]
    trig[0]["edits"] = [SCHEMA_TEST]
    return mark_suites(block)


def test_vitest_change_runs_only_the_related_test_and_merges(tmp_path, marks, node_modules, vt_block):
    repo, sha, wt = task_repo(tmp_path, vt_files(), vt_block, ["src/add.ts"], node_modules)
    T.build(wt, "src/add.ts", "export const add = (a: number, b: number): number => b + a;\n")
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests OK 1 commands (related)" in out and "FINISH OK T1 INTEGRITY OK" in out, out
    assert lines(marks / "add-ran") == ["x"] and not (marks / "mul-ran").exists() and not (marks / "schema-ran").exists()
    assert "b + a" in (repo / "src/add.ts").read_text()  # merged


def test_vitest_change_to_a_file_no_test_imports_merges(tmp_path, marks, node_modules, vt_block):
    # vitest related exits 1 when it finds no test; --passWithNoTests in discover's template keeps finish from blocking
    repo, sha, wt = task_repo(tmp_path, vt_files(), vt_block, ["src/orphan.ts"], node_modules)
    T.build(wt, "src/orphan.ts", "export const orphan = 1;\n")
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH OK T1" in out, out


def test_vitest_break_in_a_transitive_import_is_blocked(tmp_path, marks, node_modules, vt_block):
    repo, sha, wt = task_repo(tmp_path, vt_files(), vt_block, ["src/util/format.ts"], node_modules)  # mul.test.ts reaches format.ts only through mul.ts
    T.build(wt, "src/util/format.ts", "export const format = (n: number): string => `${n + 1}`;\n")
    before = T.git(repo, "rev-parse", "HEAD")
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 1 and "FINISH FAIL T1 tests: npx vitest related --run --passWithNoTests src/util/format.ts" in out and "mul" in out, out
    assert "x" in lines(marks / "mul-ran") and T.git(repo, "rev-parse", "HEAD") == before


def test_vitest_schema_trigger_blocks_until_the_counting_test_grows(tmp_path, node_modules, vt_block):
    repo, sha, wt = task_repo(tmp_path / "a", vt_files(), copy.deepcopy(vt_block), ["schema/tables.txt"], node_modules)
    T.build(wt, "schema/tables.txt", "users\norders\ninvoices\n")
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 1 and f"FINISH FAIL T1 tests: npx vitest run {SCHEMA_TEST}" in out, out
    repo, sha, wt = task_repo(tmp_path / "b", vt_files(), copy.deepcopy(vt_block), ["schema/tables.txt"], node_modules)
    T.build(wt, "schema/tables.txt", "users\norders\ninvoices\n")
    T.build(wt, SCHEMA_TEST, vt_files(3)[SCHEMA_TEST])  # allowed by the trigger's `edits`
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests OK" in out and "INTEGRITY OK" in out, out


def test_vitest_type_error_passes_finish_by_design_and_fails_the_gates_typecheck(tmp_path, node_modules, vt_block):
    """Finish runs tests only; types are checked once, at the gate (the `typecheck` suite). Both halves are the design."""
    repo, sha, wt = task_repo(tmp_path, vt_files(), vt_block, ["src/add.ts"], node_modules)
    T.build(wt, "src/add.ts", "export const add = (a: number, b: number): number => {\n  const unused: string = 0;\n  return a + b;\n};\n")  # runtime-correct, TS2322
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests OK 1 commands (related)" in out and "FINISH OK T1" in out, out
    code, out = T.ok(repo, sha, "gate")
    assert code == 1 and "GATE tests OK unit" in out and "GATE tests FAIL typecheck" in out and "TS2322" in out, out


# ---------- jest + ts-jest ----------

JEST = {
    ".gitignore": TS_IGNORE,
    "package.json": json.dumps({"name": "calc", "private": True, "scripts": {"test": "jest"},
                                "devDependencies": {"jest": NODE_PINS["jest"], "ts-jest": NODE_PINS["ts-jest"], "typescript": NODE_PINS["typescript"]}}),
    "jest.config.cjs": "module.exports = { preset: 'ts-jest', testEnvironment: 'node' };\n",
    "tsconfig.json": json.dumps({"compilerOptions": {"strict": True, "target": "es2022", "module": "commonjs", "esModuleInterop": True,
                                                      "types": ["node", "jest"], "skipLibCheck": True}, "include": ["src", "test"]}),
    "src/add.ts": VT["src/add.ts"],
    "src/mul.ts": "export const mul = (a: number, b: number): number => a * b;\n",
    "test/mark.ts": MARK_TS,
    "test/add.test.ts": "import { add } from '../src/add';\nimport { mark } from './mark';\n\ntest('add', () => {\n  mark('add-ran');\n  expect(add(2, 3)).toBe(5);\n});\n",
    "test/mul.test.ts": "import { mul } from '../src/mul';\nimport { mark } from './mark';\n\ntest('mul', () => {\n  mark('mul-ran');\n  expect(mul(2, 3)).toBe(6);\n});\n",
}


@pytest.fixture
def jest_block(tmp_path):
    block = discover(tmp_path, JEST)
    assert block["related"] == "npx jest --passWithNoTests --findRelatedTests {files}"
    return mark_suites(block)


def test_jest_change_runs_only_its_related_test_and_merges(tmp_path, marks, node_modules, jest_block):
    repo, sha, wt = task_repo(tmp_path, JEST, jest_block, ["src/add.ts"], node_modules)
    T.build(wt, "src/add.ts", "export const add = (a: number, b: number): number => b + a;\n")
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 0 and "FINISH tests OK 1 commands (related)" in out and "FINISH OK T1" in out, out
    assert lines(marks / "add-ran") == ["x"] and not (marks / "mul-ran").exists()
    assert "b + a" in (repo / "src/add.ts").read_text()


def test_jest_break_is_blocked(tmp_path, node_modules, jest_block):
    repo, sha, wt = task_repo(tmp_path, JEST, jest_block, ["src/mul.ts"], node_modules)
    T.build(wt, "src/mul.ts", "export const mul = (a: number, b: number): number => a + b;\n")
    before = T.git(repo, "rev-parse", "HEAD")
    code, out = T.ok(repo, sha, "finish", "T1")
    assert code == 1 and "FINISH FAIL T1 tests: npx jest --passWithNoTests --findRelatedTests src/mul.ts" in out, out
    assert T.git(repo, "rev-parse", "HEAD") == before
