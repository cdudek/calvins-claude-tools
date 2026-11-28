"""The test strategy end to end on real toolchains: discover-tests.py proposes the `tests` block, task-step.py finish/gate run it.
No fake commands: pytest and cargo run for real (each case skips when its tool is missing)."""
import copy
import json
import os
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


def task_repo(tmp_path, files, block, task_files):
    plan = copy.deepcopy(T.PLAN)
    plan["tests"] = block
    plan["milestones"][0]["tasks"] = [{"id": "T1", "covers": ["req-1"], "files": task_files, "check": "true"}]
    tmp_path.mkdir(parents=True, exist_ok=True)
    repo, sha = T.milestone_repo(tmp_path, plan, extra=files)
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
    assert code == 0 and "FINISH tests" not in out and "FINISH OK T1" in out, out  # discover proposes no hand-back command for cargo
    code, out = T.ok(repo, sha, "gate")
    assert code == 0 and "GATE tests OK unit" in out and lines(marks / "unit") == ["x"], out


def test_rust_breaking_change_is_caught_at_the_gate_with_discovers_block(tmp_path, rs_block):
    repo, sha, wt = task_repo(tmp_path, RS, rs_block, ["src/mul.rs"])
    T.build(wt, "src/mul.rs", BROKEN_MUL)
    assert T.ok(repo, sha, "finish", "T1")[0] == 0  # gap: nothing ran at hand-back
    code, out = T.ok(repo, sha, "gate")
    assert code == 1 and "GATE tests FAIL unit" in out and "muls" in out, out


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
