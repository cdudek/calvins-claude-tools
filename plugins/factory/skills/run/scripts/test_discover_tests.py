import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SCRIPT = HERE / "discover-tests.py"
SERIALS = ("--runInBand", "--maxWorkers=1", "-j1", "-p 1", "--workers=1", "--no-file-parallelism", "--fileParallelism=false")


def put(root, rel, text=""):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def discover(repo):
    r = subprocess.run([sys.executable, str(SCRIPT), str(repo)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    body, _, notes = r.stdout.partition("-#-#- NOTES -#-#-")
    return json.loads(body), notes


def no_serial(block):
    text = json.dumps(block)
    assert not any(s in text for s in SERIALS)


def test_vitest_repo_with_arch_config_and_playwright(tmp_path):
    put(tmp_path, "package.json", json.dumps({
        "scripts": {"test": "vitest run", "lint": "eslint .", "typecheck": "tsc --noEmit", "e2e": "playwright test"},
        "devDependencies": {"vitest": "^2", "@playwright/test": "^1"},
    }))
    put(tmp_path, "vitest.arch.config.ts")
    put(tmp_path, "db/migrations/001.sql")
    put(tmp_path, "tests/migrate.test.ts", "import x from 'y'\n// reads db/migrations\nconst d = 'migrations'\n")
    block, notes = discover(tmp_path)
    by = {s["name"]: s for s in block["suites"]}
    assert block["related"] == "npx vitest related --run {files}"
    assert by["unit"]["cmd"] == "npm run test"
    assert by["e2e"]["lock"] is True
    assert by["vitest-arch"]["cmd"] == "npx vitest run --config vitest.arch.config.ts"
    assert {"lint", "typecheck"} <= set(by)
    trig = block["triggers"][0]
    assert trig["paths"] == ["db/migrations/**"] and "tests/migrate.test.ts" in trig["run"] and trig["why"]
    assert "lock: true" in notes
    no_serial(block)


def test_pytest_repo_with_xdist(tmp_path):
    put(tmp_path, "pyproject.toml", '[project]\nname="x"\n[dependency-groups]\ndev=["pytest","pytest-xdist","ruff","mypy"]\n[tool.ruff]\nline-length=100\n')
    put(tmp_path, "uv.lock")
    block, notes = discover(tmp_path)
    cmds = {s["name"]: s["cmd"] for s in block["suites"]}
    assert cmds == {"unit": "uv run pytest -n auto", "lint": "uv run ruff check .", "typecheck": "uv run mypy ."}
    assert "related" not in block
    no_serial(block)


def test_pytest_without_xdist_notes_it(tmp_path):
    put(tmp_path, "requirements.txt", "pytest\n")
    block, notes = discover(tmp_path)
    assert block["suites"] == [{"name": "unit", "cmd": "pytest"}]
    assert "xdist" in notes


def test_go_module(tmp_path):
    put(tmp_path, "go.mod", "module x\n")
    put(tmp_path, "Makefile", "test:\n\tgo test ./...\ne2e:\n\t./e2e.sh\n")
    block, _ = discover(tmp_path)
    by = {s["name"]: s for s in block["suites"]}
    assert by["unit"]["cmd"] == "go test ./..."
    assert by["e2e"] == {"name": "e2e", "cmd": "make e2e", "lock": True}
    assert "related" not in block
    no_serial(block)


def test_empty_repo(tmp_path):
    block, notes = discover(tmp_path)
    assert block == {"triggers": [], "suites": []}
    assert "ask the owner" in notes


def test_trigger_without_reader_is_a_note(tmp_path):
    put(tmp_path, "package.json", json.dumps({"scripts": {"test": "jest"}, "devDependencies": {"jest": "^29"}}))
    put(tmp_path, "db/migrations/001.sql")
    block, notes = discover(tmp_path)
    assert block["triggers"] == []
    assert "db/migrations/**" in notes and "ask the owner" in notes


def test_serial_script_is_flagged_not_emitted(tmp_path):
    put(tmp_path, "package.json", json.dumps({"scripts": {"test": "jest --runInBand"}, "devDependencies": {"jest": "^29"}}))
    block, notes = discover(tmp_path)
    no_serial(block)
    assert "parallelism" in notes


def test_ci_commands_are_evidence(tmp_path):
    put(tmp_path, ".github/workflows/ci.yml", "jobs:\n  t:\n    steps:\n      - run: npx vitest run\n      - uses: actions/checkout@v4\n")
    _, notes = discover(tmp_path)
    assert "CI runs: npx vitest run" in notes


def test_bad_usage_exits_2(tmp_path):
    assert subprocess.run([sys.executable, str(SCRIPT)], capture_output=True).returncode == 2
    assert subprocess.run([sys.executable, str(SCRIPT), str(tmp_path / "nope")], capture_output=True).returncode == 2


def test_pytest_files_without_manifest(tmp_path):
    put(tmp_path, "tools/test_x.py")
    block, notes = discover(tmp_path)
    assert block["suites"] == [{"name": "unit", "cmd": "pytest"}]
    assert "no Python manifest" in notes
