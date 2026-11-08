# Ecosystem: Python

## Parameters

```
lockfile: requirements.txt | poetry.lock | Pipfile.lock
manifest: pyproject.toml | setup.py | setup.cfg | Pipfile
package_manager: pip | poetry | pipenv
test_command: pytest <test_file>
lint_command: ruff check <files>
lint_fix_command: ruff check --fix <files>
import_patterns: ["import", "from"]
config_paths: ["pyproject.toml", "setup.py", "setup.cfg", "conftest.py"]
registry_url: https://pypi.org/project/
changelog_search: "github.com/<owner>/<package>/releases"
```

## Lockfile Parsing

In `requirements.txt`, versions appear as `package==x.y.z`. Changes show as version diffs.

In `poetry.lock`, packages are `[[package]]` blocks with `name` and `version` fields.

In `Pipfile.lock`, deps are in `default` and `develop` keys with version strings.

## Usage Search Patterns

- `import <package>` or `from <package> import ...`
- `from <package>.<module> import ...`
- Configuration in `pyproject.toml` (e.g., `[tool.pytest]`, `[tool.ruff]`)
- Plugin registrations in `conftest.py`
- Entry points in `setup.py` or `pyproject.toml`
