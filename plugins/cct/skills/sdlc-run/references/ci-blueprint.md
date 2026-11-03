# CI blueprint — a pipeline that does not make the agent wait

## How to set it up in GitHub Actions

1. **Copy the workflow.** `cp templates/ci/github-actions.yml .github/workflows/ci.yml`
   (`adopt` does this for a repo with no CI; a repo with its own CI copies the `changes` and
   `check` jobs and gates its jobs on their flags). It is one complete, runnable file for every stack.
2. **Set `STACK`** at the top of the file (`node`, `python`, `rust`, `ruby-rails`, `kotlin` or `scala`)
   and the version line for it. Set the default branch in `on.push.branches`. Delete the `services:`
   block of `unit` and `e2e` if the repo has no database.
3. **Check `sdlc.json`.** `ciPaths` says which changed files run which step (defaults per stack:
   `templates/ci-paths.json`); `ciCommands` says what each job runs (`install`, `lint`, `unit`,
   `build`, `e2e` with `{shard}` and `{total}`, `e2eTouched` with `{files}`; defaults per stack:
   `templates/ci-commands.json`, from section K). Edit the folder names and commands to the repo's own.
4. **Apply the ruleset** in A6 below, so `milestone/*` and `project/*` need the same status as the default branch.
5. **Make `check` the only required status** (branch protection or the ruleset). Every other job hangs off it.

**What runs.** A changed file that is neither code nor config (Markdown, images, `.claude/`, plans,
`changes/`, notes, docs YAML that nothing reads) runs nothing. Code and config files run the
steps listed for them. The only cost of a PR that changes nothing runnable is the `changes` job
(about 10 seconds), and `check`, because a required status that never reports leaves the PR
unmergeable. The one list a repo edits is `ciPaths`; it is shell globs where `*` also crosses `/`.

| Changed file | Type | Steps |
|---|---|---|
| `README.md`, `docs/*`, `changes/*`, `.claude/*`, `*.txt`, `docs/img/a.png` | not code, not config | nothing |
| `src/*`, `app/*`, `*.ts`, `*.py`, `*.rs`, `*.rb` and the like | code | lint, unit, build, deploy; e2e (touched specs, or the whole suite where the safety net applies) |
| `test/*`, `*.test.*` | code (tests) | lint, unit |
| `e2e/*.spec.*` | code (a spec) | lint, e2e on that spec only |
| `*.css`, `*.scss` | code (styles) | lint, e2e, deploy; not unit, not the separate build |
| `drizzle/*`, `db/migrate/*`, `*.sql` | code (migrations) | unit, e2e, deploy |
| `package.json`, `tsconfig*.json`, `Dockerfile*`, `*.tf` | config | every step |
| `pnpm-lock.yaml`, `.github/workflows/*`, `sdlc.json` | config in `all` | every step |
| anything else with a code or config type that no step lists | code or config | every step: a forgotten path costs minutes, never a missed check |

**Worked example.** `ciPaths` is the TypeScript default (`templates/ci-paths.json`). Four PRs, each
from a feature branch into `milestone/x`, then the same code into the default branch. `●` runs, `–` skipped.

| PR changes | lint | unit | build | e2e | deploy | Why |
|---|---|---|---|---|---|---|
| `README.md`, `docs/guide.md` | – | – | – | – | – | Both match `ciPaths.docs`. Only `changes` and `check` run. |
| `docs/img/diagram.png`, `README.md` | – | – | – | – | – | An image outside the code folders is neither code nor config. Nothing runs. |
| `src/lib/price.ts` | ● | ● | ● | – | ● | Code: every step's include matches. E2E is skipped because no spec changed; the full suite runs on the PR into the default branch. |
| `e2e/login.spec.ts` | ● | – | – | ● (one leg, that spec) | – | `e2e/*` is in lint's and e2e's include and in the excludes of unit, build and deploy. `ciPaths.specs` names it a spec, so one `E2E touched specs` leg runs just that file. |
| `src/lib/price.ts`, into the default branch | ● | ● | ● | ● (4 shards) | ● | The safety net: a PR into the default branch or `project/*`, or from `milestone/*`, that changes any code or config runs every step and the whole suite. |
| any push to the default branch | ● | ● | ● | ● (4 shards) | ● | The same net, after the merge. |

`scripts/test_ci_changes.sh` runs the template's real `changes` script against these cases (and
the CSS, lockfile, config, migration and unknown-file ones) with the shipped defaults.

The `changes` job is the whole mechanism, the rest of the template is gated jobs. An excerpt
of `templates/ci/github-actions.yml` (the template has the rest: the other jobs, the stack setup for six
stacks, the sharded `e2e` job with its database service, the `deploy` hook):

```yaml
  changes:
    name: Changed paths
    runs-on: ubuntu-latest
    timeout-minutes: 5
    outputs:
      lint: ${{ steps.f.outputs.lint }}
      unit: ${{ steps.f.outputs.unit }}
      build: ${{ steps.f.outputs.build }}
      deploy: ${{ steps.f.outputs.deploy }}
      full: ${{ steps.f.outputs.full }}
      matrix: ${{ steps.f.outputs.matrix }}
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
          sparse-checkout: sdlc.json # only the path lists are needed
          sparse-checkout-cone-mode: false
      - id: f
        env:
          GH_TOKEN: ${{ github.token }}
          GH_REPO: ${{ github.repository }}
          PR: ${{ github.event.pull_request.number }}
          BASE: ${{ github.base_ref }}
          HEAD: ${{ github.head_ref }}
          DEFAULT: ${{ github.event.repository.default_branch }}
        run: |
          # >>> changes-script (scripts/test_ci_changes.sh runs exactly these lines)
          set -eu
          set -f # keep the globs literal
          # …
          list() { jq -r "(.ciPaths$1 // []) | join(\" \")" sdlc.json; }
          hit() { for g in $2; do case "$1" in $g) return 0 ;; esac; done; return 1; }
          # …
            while IFS= read -r f; do
              [ -n "$f" ] || continue
              hit "$f" "$IGNORE" && continue
              if hit "$f" "$ALL"; then everything; touched=true; continue; fi
              hit "$f" "$CODE" || continue # neither code nor config: runs nothing
              touched=true
              # …
              for s in $STEPS; do
                eval "inc=\"\$inc_$s\" exc=\"\$exc_$s\""
                # on a step when it matches the include and not the exclude
                if hit "$f" "$inc"; then known=true; hit "$f" "$exc" || eval "$s=true"; fi
              done
              # code or config that no step's include knows is a path you forgot to list: run everything
              $known || everything
            # …
            # safety net: where the full suite runs, any code or config change runs every step
            if [ "$touched" = true ] && [ "$full" = true ]; then everything; fi
          # …

  lint:
    name: Lint and types
    needs: changes
    if: needs.changes.outputs.lint == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      # checkout and the stack setup steps …
      - name: Lint (ciCommands.lint)
        run: |
          cmd=$(jq -r '.ciCommands.lint // empty' sdlc.json)
          if [ -z "$cmd" ]; then echo "::error::sdlc.json has no ciCommands.lint; set it (to true if this repo has no such step)"; exit 1; fi
          echo "+ $cmd"; bash -eo pipefail -c "$cmd"

  # The one required status. It always runs and always reports, so a PR that needed no job is still mergeable.
  check:
    name: check
    if: always()
    needs: [changes, lint, unit, build, e2e, deploy]
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - env:
          RESULTS: ${{ join(needs.*.result, ' ') }}
        run: |
          # skipped is fine: a flag said the step was not needed. failure or cancelled is not.
          case " $RESULTS " in *" failure "*|*" cancelled "*) echo "::error::a job failed: $RESULTS"; exit 1 ;; esac
          echo "all jobs passed or were skipped on purpose: $RESULTS"
```

Measured on one repo in one day (2026-10-31) before this existed: 39 CI runs, 22 red, about 25
minutes each; 13 of 22 PRs were docs-only yet ran the full pipeline and a preview deploy; one
code PR waited 7 hours through 7 red runs that were all E2E timeouts on a dev server. Six rules fix
that. They hold for every stack; only the commands differ, and those are in one table:
`../../e2e-test-run/references/suite-speed-and-reliability.md` section K.

| # | Rule | Where it lives |
|---|---|---|
| A1 | Each step (lint, unit, build, e2e, deploy) runs only when a changed code or config path needs it; a change that is neither runs nothing and the one required status still reports success | this file, A1 |
| A2 | E2E and system tests run against the built artifact, never a dev server that compiles on demand | section K, column "Production target" |
| A3 | The slow suite is sharded over N jobs, each with its own database service | section K, column "Shard" |
| A4 | One retry; a pass on retry is reported, and a committed known-flaky list gets fixed | section K, column "Retry"; list format in section G |
| A5 | Within the `e2e` step: the full suite runs only on PRs into the default branch or `project/*`, on milestone heads and on pushes to the default branch; other PRs run the touched specs | this file, A5 |
| A6 | Interior branches carry the same required status, so auto-merge waits for green | this file, A6 |

## A1 and A5 — one `changes` job sets a flag per step, `check` stays the one required status

Branch protection requires exactly one status, `check`. Every other job hangs off it. Do not
use workflow-level `paths-ignore`: a workflow that never starts leaves the required status
pending forever and the PR unmergeable. A job-level condition plus an aggregating job always
reports. No third-party action: `gh` and `jq` are on every runner.

- **Order of the decision, per changed file:** in `ciPaths.docs` (the never list) → skip; in
  `ciPaths.all` → every step; neither in `ciPaths.code` nor `ciPaths.config` → skip (this is the
  default: *if no code or config was touched, nothing runs*); otherwise each step whose `include`
  matches and whose `exclude` does not; a code or config file no step's include matches → every step.
- **`ciPaths.docs`** is no longer the list of what is documentation. It is the optional "never
  runs anything" list that wins even where a code glob matches (`docs/*.ts` examples, `*.md`).
- **A YAML counts as code or config only if something reads it:** no build, test, deploy or app
  code loads it. A YAML a script or the app does read is config, so list it. Always config, never
  ignored: `.github/workflows/**`, app and framework config, OpenAPI specs the code generates from,
  k8s, helm and terraform YAML, `sdlc.json`, lockfiles. A `docs/` folder that feeds the site and a
  `README.md` embedded in a package are read by the build: take them out of `ciPaths.docs`.
- **The safety net, and its price.** `full` is true for a push to the default branch, a PR into
  the default branch or `project/*`, and a PR whose head is `milestone/*`. Where `full` is true,
  a PR that changes any code or config runs every step and all E2E shards, whatever the
  per-step lists say, so a mis-listed file is caught before it ships; a push to the default
  branch runs everything regardless. A mis-listed file in a PR that changes only that file
  runs nothing until the push after the merge: keep `code` and `config` complete.
- **E2E on other PRs** (feature PRs into `milestone/*`): one `E2E touched specs` leg runs the
  specs in the PR that match `ciPaths.specs` (`ciCommands.e2eTouched`, `{files}`); no changed
  spec, no leg. A deleted spec is skipped.
- **A pass on retry** is reported in the job summary and does not fail a feature PR; on a
  full run (`FULL=true`) it does (`failOnFlakyTests` or the stack's equivalent). Section K.

### `ciPaths` in sdlc.json: the one list per repo

`sdlc.json` (not under `checks`, so a repo edits it without the lock) holds the lists. The
`changes` job reads them with `jq`; the agents read the same lists to pick "touched tests"
(`../../e2e-test-run/references/suite-speed-and-reliability.md` section K).

```json
"ciPaths": {
  "docs": ["changes/*", "docs/*", "plans/*", ".claude/*", "*.md", "*.txt"],
  "all": [".github/workflows/*", "sdlc.json", "package-lock.json", "pnpm-lock.yaml"],
  "code": ["src/*", "app/*", "public/*", "e2e/*", "test/*", "*.ts", "*.tsx", "*.css", "*.sql", "drizzle/*"],
  "config": ["package.json", "tsconfig*.json", "next.config.*", "Dockerfile*", "*.tf", "k8s/*"],
  "specs": ["e2e/*.spec.*"],
  "lint": { "include": ["src/*", "app/*", "e2e/*", "test/*", "*.css"], "exclude": ["public/*", "*.svg", "*/generated/*"] },
  "unit": { "include": ["src/*", "app/*", "test/*", "*.sql"], "exclude": ["e2e/*", "*.css"] },
  "build": { "include": ["src/*", "app/*", "public/*", "Dockerfile"], "exclude": ["e2e/*", "test/*", "*.css"] },
  "e2e": { "include": ["src/*", "app/*", "public/*", "e2e/*", "*.sql"], "exclude": ["test/*", "*.test.*"] },
  "deploy": { "include": ["src/*", "app/*", "public/*", "Dockerfile", "deploy/*", "*.sql"], "exclude": ["e2e/*", "test/*"] }
}
```

- **A step runs** for a code or config file that matches its `include` and not its `exclude`.
- **Defaults per stack** (TypeScript, Python, Rust, Rails, Kotlin, Scala) are in
  `templates/ci-paths.json`; `adopt` copies the stack's block into `sdlc.json` once, adds the keys
  an older block lacks, and never overwrites a value. Edit the folder names to the repo's own.
- **Excludes that are safe:** tests of the other kind (E2E out of unit, unit out of E2E and
  build), assets (`*.css`, images, `public/*`) out of lint and unit, generated code and the
  schema dump out of lint. **Never excluded:** migrations (`db/migrate/*`) trigger unit, e2e
  and deploy; a lockfile or workflow is `all`.

What the defaults encode (a path outside `code` and `config` runs nothing):

| Stack | Changed path | Steps |
|---|---|---|
| TypeScript, JavaScript | `src/**`, `app/**`, `public/**` | lint unit build e2e deploy |
| | `*.test.*`, `__tests__/**` | lint unit |
| | `e2e/**`, `playwright.config.*` | lint e2e |
| | `Dockerfile`, `deploy/**`, `next.config.*` | build e2e deploy |
| Python | `src/**`, `app/**` | lint unit build e2e deploy |
| | `tests/**` | lint unit |
| | `e2e/**` | e2e |
| | `pyproject.toml`, `Dockerfile` | build deploy |
| Rust | `src/**`, `crates/**` | lint unit build e2e deploy |
| | `tests/**`, `benches/**` | lint unit |
| | `Cargo.toml`, `build.rs`, `Dockerfile` | build e2e deploy |
| Ruby, Rails | `app/models/**`, `app/controllers/**`, `app/services/**`, `lib/**` | lint unit build e2e deploy |
| | `app/views/**` | lint e2e |
| | `app/assets/**`, `app/javascript/**` | lint build e2e deploy |
| | `db/migrate/**`, `db/schema.rb` | unit e2e deploy |
| | `spec/**` (not `spec/system/**`) | lint unit |
| | `spec/system/**` | lint e2e |
| Kotlin | `src/main/**` | lint unit build e2e deploy |
| | `src/test/**` | lint unit |
| | `build.gradle*`, `Dockerfile`, `src/main/resources/**` | build e2e deploy |
| Scala | `src/main/**` | lint unit build e2e deploy |
| | `src/test/**` | lint unit |
| | `build.sbt`, `project/*.sbt`, `Dockerfile` | build e2e deploy |

## A6 — interior branches wear the same required status

Auto-merge waits only for the checks that protect the base branch. A feature PR into
`milestone/*` or a milestone PR into `project/*` with no protected base would merge the moment
it is armed, red or not. One ruleset covers them:

```bash
gh api repos/OWNER/REPO/rulesets -X POST --input - <<'JSON'
{
  "name": "interior-branches",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["refs/heads/project/*", "refs/heads/milestone/*"], "exclude": [] } },
  "bypass_actors": [{ "actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always" }],
  "rules": [{ "type": "required_status_checks", "parameters": { "strict_required_status_checks_policy": false, "required_status_checks": [{ "context": "check" }] } }]
}
JSON
```

- OWNER/REPO is the repository. Repo setting "Allow auto-merge" must be on.
- A `non_fast_forward` rule is safe since 3.7.0: the SDLC merges a parent into `milestone/*`
  and `project/*` and never rewrites a pushed one. A required status also blocks the close push,
  so the bypass (actor 5 is the admin role) must cover whoever pushes. Without a bypass, protect
  only `project/*`.
- `delivery: "one-go"` pushes features straight to `milestone/<slug>` and opens one PR from
  it, so nothing merges into it: protect `project/*` only. `delivery: "feature-prs"` protects both.
