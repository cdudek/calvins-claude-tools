# Ecosystem: Pytest

## Test Commands

| Action | Command |
|---|---|
| Run single test | `pytest <file>::<test_name>` |
| Run without randomization | `pytest <file>::<test_name> -p no:randomly` |
| Run with seed | `pytest <file> --randomly-seed=<seed>` |
| Run full file | `pytest <file>` |
| Run full suite | `pytest` or `make test` |

Use `uv run pytest` if the project uses uv (check for `pyproject.toml` with `[tool.uv]` or `uv.lock`).

## Seed Handling

Requires the `pytest-randomly` plugin. Without it, pytest has no randomization or seed support.

- **Seed output regex:** `--randomly-seed=(\d+)`
- **Seed displayed by default:** Yes, when pytest-randomly is installed
- If pytest-randomly is not installed, note this in the report and skip seed-based reproduction

## Bisect

**Third-party** — no built-in support. Two options:

### Option A: pytest-bisect-tests
```
pip install pytest-bisect-tests
pytest-bisect-tests --failing-test "<file>::<test_name>" --run-options "--some-flag"
```
Finds the minimal set of tests that cause a specific test to fail.

### Option B: detect-test-pollution
```
pip install detect-test-pollution
detect-test-pollution --tests ./tests --failing-test "<file>::<test_name>"
```
Bisects to find the single polluting test. Supports `--testids-file` for a pre-collected list.

### When to use
The test passes in isolation (`pytest <file>::<test>`) but fails in the full suite.

### Setup note
Check if either plugin is already installed. If not, install in the worktree:
- uv-based projects: `uv pip install pytest-bisect-tests` or `uv pip install detect-test-pollution`
- pip-based projects: `pip install pytest-bisect-tests` or `pip install detect-test-pollution`

These are dev tools — do not add them to project dependencies.

### After bisect
Read the identified polluting test to find shared state (module-level variables, fixtures with `session` scope, monkeypatch not restored).

## Common Flaky Patterns

- `session`-scoped fixtures with mutable state
- `monkeypatch` in `conftest.py` not properly scoped
- Module-level variables modified in tests
- `tmp_path` collisions in parallel runs
- Missing `autouse` fixture for database cleanup
