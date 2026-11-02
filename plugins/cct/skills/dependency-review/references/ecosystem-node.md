# Ecosystem: Node.js

## Parameters

```
lockfile: package-lock.json | yarn.lock | pnpm-lock.yaml
manifest: package.json
package_manager: npm | yarn | pnpm
test_command: npm test
lint_command: npx eslint <files>
lint_fix_command: npx eslint --fix <files>
import_patterns: ["import", "require"]
config_paths: ["package.json", ".eslintrc*", "tsconfig.json", "next.config.*", "vite.config.*"]
registry_url: https://www.npmjs.com/package/
changelog_search: "github.com/<owner>/<package>/releases"
```

## Lockfile Parsing

In `package-lock.json`, direct deps are in `packages[""].dependencies`. Version changes show as diffs in `packages["node_modules/<name>"]`.

For `yarn.lock`, deps are listed as `"<name>@<range>":` blocks with `version:` fields.

## Usage Search Patterns

- `import ... from '<package>'` or `import '<package>'`
- `require('<package>')`
- `const { ... } = require('<package>')`
- Configuration in `package.json` (e.g., `"jest"`, `"eslint"`, `"babel"` keys)
- Framework-specific config files (next.config.js, vite.config.ts, etc.)
