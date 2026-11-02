# Ecosystem: Ruby

## Parameters

```
lockfile: Gemfile.lock
manifest: Gemfile
package_manager: bundler
test_command: make test ARGS="<spec_file>"
lint_command: make lint ARGS="<files>"
lint_fix_command: make lint:fix ARGS="<files>"
import_patterns: ["require", "require_relative"]
config_paths: ["config/initializers/", "Gemfile"]
registry_url: https://rubygems.org/gems/
changelog_search: "github.com/<owner>/<gem>/releases"
```

## Lockfile Parsing

In `Gemfile.lock`, direct dependencies appear under the `DEPENDENCIES` section. Version changes show as diffs in the `specs:` sections under `GEM`.

## Usage Search Patterns

- `require '<gem_name>'` or `require_relative`
- `gem '<gem_name>'` in Gemfile (with version constraints)
- Class/module names from the gem (e.g., `Faraday`, `Redis`, `Sidekiq`)
- Configuration in `config/initializers/<gem_name>.rb`
- Monkey-patches or extensions of library classes
