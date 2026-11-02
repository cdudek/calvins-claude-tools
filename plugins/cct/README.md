# cct: Calvin's Claude Tools

Calvin's AI-native software development lifecycle as one Claude Code plugin. It holds `sdlc-run` and every skill, agent and hook the SDLC runs, the UX suite included, and nothing else. It works without the OMR AI Kit installed.

This repo (`cdudek/calvins-claude-tools`) is a Claude Code marketplace named `cct` with one plugin, also named `cct`, in `plugins/cct/`. Every skill is called as `/cct:<name>`, for example `/cct:sdlc-run` or `/cct:ux-review`.

## Install

```bash
claude plugin marketplace add cdudek/calvins-claude-tools
claude plugin install cct@cct
```

Inside a session: `/plugin marketplace add cdudek/calvins-claude-tools`, then `/plugin install cct@cct`. Restart Claude Code afterwards so the hooks load.

Update later:

```bash
claude plugin marketplace update cct
claude plugin update cct@cct
```

### Turn off what it replaces

`cct` carries its own copy of the omr-dev and omr-ux skills the SDLC uses. If those plugins stay enabled, the skills appear twice and the worktree hooks run twice:

```bash
for p in omr-dev@omr-ai-kit omr-ux@omr-ai-kit calvin@calvin-kit; do claude plugin disable "$p"; done
```

Also remove the `WorktreeCreate` and `WorktreeRemove` entries from `~/.claude/settings.json`; `cct` registers the same hooks.

### Tools the skills call

```bash
brew install gh jq node python uv
npm install -g @openai/codex agent-browser
curl -fsSL https://plannotator.ai/install.sh | bash
```

- `gh`: pull requests, merge state, auto-merge, releases.
- `codex`: the second reviewer in `pr-review` and the image generation in `designs-explore` and `ux-design`. Log in with `codex login`.
- `agent-browser`: drives the running app for E2E planning, UX screenshots and responsive checks.
- `plannotator`: plan and annotation review; `sdlc-run adopt` installs its plugin through the repo's `sdlc:tools` script.

## What is inside

- **The SDLC:** `sdlc-run` (adopt, status, intent → UX plan → facts → tech plan → one /goal build per milestone → milestone PR), `review-fix-loop`, `pr-review`, `address-feedback`, `pr-create`, `squash`, `security-review`, `architecture-review`, `c4-diagram-create`, `plan-design-review`, `ai-ready-issues`, `write-ticket`, `linear-manage`, the E2E skills (`e2e-write`, `e2e-test-run`, `e2e-from-ticket-write`, `flaky-test-fix`), `browser-automate` and the `role-*` helpers, with the agents they dispatch (`builder`, `verifier`, `code-reviewer`, `validate-finding`, `ac-auditor`, `review-runner`, the fix-loop and E2E agents).
- **UX:** `ux-init`, `ux-audit`, `ux-design`, `ux-validate`, `ux-review`, `ux-conformance`, `ux-guidelines`, `ux-decision`, `ux-sitemap-create` and the `ux-reviewer` agent, plus `designs-explore`, `variants-create`, `design-consult`, `design-system-apply`, `microcopy-write`, `accessibility-audit`, `responsive-audit`, `ux-laws-apply`, and the small design skills `ux-design` calls (`ux-writing`, `layout-grid`, `jobs-to-be-done`, `state-machine`, `heuristic-evaluation-ai`, `design-brief`, `frontend-design`).
- **New projects:** `project-kickoff` writes the context, brand guide, design system and UX rules before the first line of app code.
- **Providers:** `aws-manage` (the AWS CLI) and `cloudflare-manage` (the Cloudflare API and wrangler) use your credentials from the environment or `~/.zshrc` without printing them, and ask before any write.
- **Hooks:** worktrees always under `<repo>/.worktrees/<name>`, and a lint on every edit.
- **Docs:** `docs/stack.md`, `docs/working-rules.md`, `docs/skill-map.md` (where each skill came from), `docs/omr-dev-guide.md`.
- **Blueprint:** `blueprint/` has the Dockerfile, GitHub Actions, deploy docs and release config for Next.js on Cloud Run, Electron, WXT and a HeroUI design-system kit, with notes for running it without GCP.
- **Examples:** `examples/heydiff/` has a real context repo, brand guide exports, UX docs and the brand guide PDF.

## How sdlc-run works

- [`docs/sdlc-run.md`](docs/sdlc-run.md): the stages and the two touchpoints, one `/goal` per milestone, branches, commits versus PRs, the verify contract, the CI blueprint with `ciPaths`, and how to adopt. It has diagrams that GitHub renders.
- [`docs/sdlc-run-explained.html`](docs/sdlc-run-explained.html): the same content as one visual page. Download it and open it in a browser.

## Rebuild from the sources

`scripts/build.py` regenerates `plugins/cct/` from the OMR AI Kit (latest `master`), the installed public plugins and the HeyDiff repos, keeps only what `sdlc-run` and `project-kickoff` reach, and lays `overlay/` (the hand-written files) on top. Edit hand-written files in `overlay/`, never in `plugins/cct/`.

```bash
python3 scripts/build.py
```
