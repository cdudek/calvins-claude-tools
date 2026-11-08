# Lint Commands by Language

Detection and lint commands for common project types. Always check for a `Makefile` lint target or `package.json` lint script first — those represent the project's preferred way to lint.

## Detection Priority

1. **Makefile** — `grep -q '^lint:' Makefile 2>/dev/null` → run `make lint`
2. **package.json lint script** — `jq -e '.scripts.lint' package.json 2>/dev/null` → run with detected package manager
3. **Language-specific config files** — see table below
4. **File extension scan** — `ls *.rb 2>/dev/null`, etc.

## Package Manager Detection (JavaScript/TypeScript)

```bash
# Detect which package manager the project uses
if [ -f "pnpm-lock.yaml" ]; then PM="pnpm"
elif [ -f "yarn.lock" ]; then PM="yarn"
elif [ -f "bun.lockb" ]; then PM="bun"
else PM="npm"; fi

# Run the lint script
$PM run lint
```

## Language Table

| Language | Config Files | Lint Command | Auto-fix Command |
|----------|-------------|-------------|-----------------|
| **JavaScript/TypeScript** | `.eslintrc*`, `eslint.config.*`, `biome.json` | `npx eslint .` or `npx biome check .` | `npx eslint --fix .` or `npx biome check --fix .` |
| **TypeScript (types)** | `tsconfig.json` | `npx tsc --noEmit` | — (manual fix required) |
| **Ruby** | `.rubocop.yml`, `Gemfile` | `bundle exec rubocop` | `bundle exec rubocop -a` |
| **Python** | `pyproject.toml`, `ruff.toml`, `.flake8` | `uv run ruff check .` or `ruff check .` | `uv run ruff check --fix .` |
| **Python (types)** | `pyproject.toml` (mypy section) | `uv run mypy src` | — |
| **Rust** | `Cargo.toml` | `cargo clippy` | `cargo clippy --fix` |
| **Go** | `go.mod` | `go vet ./...` | — |
| **Go (lint)** | `go.mod` + `.golangci.yml` | `golangci-lint run` | `golangci-lint run --fix` |
| **Elixir** | `mix.exs` | `mix credo` | — |
| **Swift** | `Package.swift`, `.swiftlint.yml` | `swiftlint` | `swiftlint --fix` |
| **Kotlin** | `build.gradle*`, `.editorconfig` | `./gradlew ktlintCheck` | `./gradlew ktlintFormat` |
| **Java** | `pom.xml`, `build.gradle*` | `./mvnw checkstyle:check` or `./gradlew checkstyleMain` | — |

## Notes

- When both a linter (ESLint, RuboCop) and a type checker (tsc, mypy) are available, run both — they catch different classes of errors
- Only run linters on staged/changed files when the project is large and full-project linting is slow. Use `git diff --name-only --cached` to get the list
- If linting produces only warnings (no errors), proceed with the commit — warn the user but don't block
- If no linter is detected at all, tell the user and proceed. Not every project has linting configured
