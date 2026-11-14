# cct: Calvin's Claude Tools

Calvin's AI-native software development lifecycle as a Claude Code plugin. It holds `sdlc-run` and every skill, agent and hook the SDLC runs, the UX suite included, plus the product skills, the engineering and data skills Calvin runs by hand. It is self-contained: it needs no other plugin.

This repo (`cdudek/calvins-claude-tools`) is a Claude Code marketplace named `cct` with two plugins. `cct`, in `plugins/cct/`, holds the SDLC; `agent-tracker`, in `plugins/agent-tracker/`, is a mod that draws a band above every prompt and a `/tracker` pane (see [its README](plugins/agent-tracker/README.md)). Every `cct` skill is called as `/cct:<name>`, for example `/cct:sdlc-run` or `/cct:ux-assessment-run`.

## Install

```bash
claude plugin marketplace add cdudek/calvins-claude-tools
claude plugin install cct@cct
claude plugin install agent-tracker@cct
```

Inside a session: `/plugin marketplace add cdudek/calvins-claude-tools`, then `/plugin install cct@cct`. Restart Claude Code afterwards so the hooks load.

Update later:

```bash
claude plugin marketplace update cct
claude plugin update cct@cct
```

### Tools the skills call

```bash
brew install gh jq node python uv
npm install -g @openai/codex agent-browser
curl -fsSL https://plannotator.ai/install.sh | bash
```

- `gh`: pull requests, merge state, auto-merge, releases.
- `codex`: the second reviewer in `review-code-run` and the image generation in `design-mockups-create` and `ux-design-run`. Log in with `codex login`.
- `agent-browser`: drives the running app for E2E planning, UX screenshots and responsive checks.
- `plannotator`: plan and annotation review; `sdlc-run adopt` installs its plugin through the repo's `sdlc:tools` script.

## What is inside

Skills are named `<family>-<object>-<verb>` (see [`docs/adr/0001-skill-taxonomy.md`](docs/adr/0001-skill-taxonomy.md) for the rules and the full old-to-new table). Process skills end in `-run`, knowledge skills end in a noun, vendor adapters are `<vendor>-<verb>`. Grouped by prefix:

- **sdlc-** (the lifecycle): `sdlc-run`. Agents: `sdlc-feature-builder`.
- **project-** (new projects and repo setup): `project-kickoff-run`, `project-plan-write`, `project-report-write`, `project-repository-run`.
- **product-** (requirements, discovery, strategy, roadmap): `product-audience-write`, `product-discovery-run`, `product-epic-analyze`, `product-playbook`, `product-prd-write`, `product-priorities-analyze`, `product-problem-write`, `product-roadmap-write`, `product-storymap-create`, `product-strategy-run`, `product-workitem-write`.
- **ux-** (behavior and words: assess, validate, specify): `ux-accessibility-audit`, `ux-ai-heuristics`, `ux-assessment-run`, `ux-brief-write`, `ux-build-validate`, `ux-copy-write`, `ux-decision-log`, `ux-design-run`, `ux-guidelines-write`, `ux-jobs-write`, `ux-journey-create`, `ux-responsive-audit`, `ux-rules-validate`, `ux-run`, `ux-setup`, `ux-sitemap-create`, `ux-spec-validate`, `ux-states-design`, `ux-usability-audit`. Agents: `ux-usability-reviewer`.
- **design-** (visual expression and systems): `design-frontend-write`, `design-mockups-create`, `design-surface-review`, `design-system-write`.
- **arch-** (technical plans and decisions): `arch-decision-log`, `arch-plan-write`.
- **db-** (database work): `db-query-optimize`.
- **review-** (reviewing and fixing authored changes): `review-code-run`, `review-container-audit`, `review-dependency-run`, `review-feedback-analyze`, `review-feedback-run`, `review-fix-run`, `review-security-run`. Agents: `review-code-reviewer`, `review-code-runner`, `review-criteria-auditor`, `review-dimensions-selector`, `review-feedback-runner`, `review-finding-validator`, `review-fix-implementer`, `review-fixset-triager`.
- **test-** (E2E and behavioral tests): `test-e2e-coverage-run`, `test-e2e-policy`, `test-e2e-setup`, `test-flake-fix`, `test-journeys-write`, `test-suite-run`. Agents: `test-behavior-verifier`, `test-behavior-writer`, `test-e2e-generator`, `test-e2e-healer`, `test-e2e-planner`.
- **git-** (commits, PRs, releases): `git-commits-squash`, `git-pr-run`, `git-release-run`.
- **data-** (analysis methods): `data-classification-metrics`, `data-cohorts-analyze`, `data-network-analyze`.
- **tracking-** (product analytics instrumentation): `tracking-apply`, `tracking-audit`, `tracking-library-run`.
- **docs-** (documentation and transcripts): `docs-audit`, `docs-c4-create`, `docs-changelog-write`, `docs-transcript-fix`.
- **vendor and browser adapters** (vendor tools and the browser): `aws-manage`, `browser-automate`, `cloudflare-manage`, `codex-run`, `github-manage`, `linear-manage`, `posthog-manage`.
- **role-*** (internal helpers agents preload): `role-code-analysis`, `role-review-vocabulary`.

- **Hooks:** [Worktrunk-first worktrees with Git fallback](plugins/cct/references/worktree-usage.md), and a lint on every edit.
- **Docs:** `docs/stack.md`, `docs/working-rules.md`, `skills/CLAUDE.md` (the interface contracts the review skills' tests read).
- **Blueprint:** `blueprint/` has the Dockerfile, GitHub Actions, deploy docs and release config for Next.js on Cloud Run, Electron, WXT and a HeroUI design-system kit.
- **Examples:** `examples/heydiff/` has a real context repo, brand guide exports and UX docs.

## How sdlc-run works

- [`docs/sdlc-run.md`](docs/sdlc-run.md): the stages and the two touchpoints, one `/goal` per milestone, branches, commits versus PRs, the verify contract, the CI blueprint with `ciPaths`, and how to adopt. It has diagrams that GitHub renders.

## Renamed in 0.7.0

Every skill and agent got a family-prefixed name and no forwarders exist. Look up an old name in the table in [`docs/adr/0001-skill-taxonomy.md`](docs/adr/0001-skill-taxonomy.md).

## Editing

`plugins/cct/` and `plugins/agent-tracker/` are the source of truth; edit them directly. Naming rules are in [`docs/adr/0001-skill-taxonomy.md`](docs/adr/0001-skill-taxonomy.md) and enforced by `scripts/taxonomy.py`: name pattern, closed verb list, unique trigger phrases, and every reference resolves. A mirrored pair (the PRD template, the requirements grammar) must stay identical, and a description stays at or under 1024 characters.

```bash
python3 -m unittest discover -s tests
```

`scripts/run-plugin-tests.sh` runs the tests that ship inside the plugin's skills and hooks.
