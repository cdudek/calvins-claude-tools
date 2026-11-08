# The stack

What Calvin builds with. A new project starts here unless it has a reason to differ, and that reason is written down in the project's context repo. Never swap a part of the stack (TypeScript for JavaScript, HeroUI for something else) without asking first.

The versions are the ones in use on 2026-10-31. Take the latest stable version when starting something new.

## By product type

| Product | Framework | Reference |
| --- | --- | --- |
| Web app, landing, API, MCP | Next.js 16 (App Router), React 19 | `blueprint/web-nextjs-cloud-run/` |
| Mobile app | React Native | no reference repo yet |
| Desktop app | Electron | `blueprint/desktop-electron/` |
| Chrome extension | WXT | `blueprint/chrome-extension-wxt/` |
| Design system | HeroUI v3 or MUI, on Tailwind CSS 4 | `blueprint/design-system-kit-heroui/` |

## UI and design system

- **Component library:** HeroUI v3 (`@heroui/react`, `@heroui/styles`) or MUI. Pick one per product and keep it everywhere that product appears.
- **Styling:** Tailwind CSS 4. Motion with `motion`.
- **One kit repo per product** (`<product>-kit`) publishes the shared packages to GitHub Packages (`@<owner>/<product>-tokens`, `-ui`, `-contracts`, plus domain packages). Web, extension and desktop all consume the same tokens and UI wrappers, so a brand change lands once.
- **Tokens** come from the brand guide (`tokens.json`, `tokens.css`) and are the only source of colour, type, spacing, radius and motion. No raw hex values in app code.
- **Storybook** in the kit repo shows every component in light and dark.
- Visual direction: calm, native, system colours; the brand colour only on primary actions; no blue focus outlines everywhere.

## Web (Next.js)

- Next.js 16 App Router, React 19, TypeScript 7, `"type": "module"`.
- `next-intl` for German and English.
- Auth: `better-auth` (magic link, Google, GitHub), `@better-auth/mcp` for the MCP endpoint.
- Data: Postgres via `postgres` and `drizzle-orm`; migrations with `drizzle-kit`, bundled with esbuild into their own image and run as a Cloud Run job.
- Validation `zod`, logging `pino`, mail `resend`, images `sharp`, files `@google-cloud/storage`.
- Output `standalone`, served from a distroless Node image.

## Desktop (Electron)

- Electron with TypeScript, built by electron-builder.
- Signed with a Developer ID certificate and notarized in GitHub Actions (`sign-macos-app` skill). Keep the signature stable or macOS asks for Screen Recording again.
- Updates with electron-updater from a generic provider (a public Cloud Storage bucket), pruned to the newest 10 versions.
- Install from a release ZIP, never from a local `--mac dir` build: those carry no `app-update.yml` and never update.
- Global shortcuts use ⌃⇧ combinations, never ⌘ ones.

## Chrome extension (WXT)

- WXT, React 19, Tailwind 4 via `@tailwindcss/vite`.
- Vitest with jsdom and Testing Library for units, Playwright against the built extension for E2E.
- Shares the kit packages with the web app.

## Mobile (React Native)

- React Native, consuming the same tokens package. No HeyDiff reference yet; when the first app starts, add its blueprint here.

## Tooling, in every TypeScript repo

- npm with a committed `package-lock.json`; Node from `.nvmrc`.
- Biome for format and lint; `dependency-cruiser` for layer rules; `tsc --noEmit` for types.
- Vitest for units, Playwright for E2E (`smoke:background` runs it headless).
- Scripts every repo has: `format`, `format:check`, `lint`, `typecheck`, `test`, `build`, `sdlc:tools`. Run format, lint and typecheck before every commit.

## Python

- pyenv for the interpreter, uv for everything else (`uv add`, `uv run`), no `requirements.txt`, no manual venv.
- Flat `src/` layout: `config/`, `domain/` (pure logic, no I/O), `clients/`, feature folders with the provider pattern (`base.py`, `factory.py`, `providers/`).
- ruff (line length 100, rules E F I UP B), mypy strict, pytest.

## Infrastructure and delivery

- **Containers:** multi-stage Dockerfile, bases pinned by digest, runtime on Google distroless (non-root uid 65532, no shell). Secrets enter builds only as BuildKit secrets, never as layers. See `blueprint/web-nextjs-cloud-run/Dockerfile`.
- **CI/CD:** GitHub Actions, every action pinned by commit SHA. CI on each PR (format, lint, typecheck, tests, Trivy on dependencies and images, a Docker smoke run). Preview deployment per PR, deploy to staging then production on merge to `main`, a manual rollback workflow.
- **Cloud:** GCP. Cloud Run (scale to zero), Artifact Registry, Secret Manager, Cloud Storage, BigQuery in the EU. HeyDiff runs in `europe-west1`.
- **Auth from CI:** Workload Identity Federation, no service-account keys.
- **Infrastructure as code:** Terraform in its own `<product>-terraform` repo; secrets as SOPS files encrypted with Cloud KMS and pushed to Secret Manager.
- **Releases:** semantic-release decides the version from the Conventional Commit PR title (`fix` → patch, `feat` → minor, `feat!` → major). Milestone PRs merge with a merge commit, so semantic-release reads every commit in them and builders write Conventional Commit subjects; other PRs squash and their title becomes the commit. Never bump versions by hand.
- **Dependencies:** Dependabot, grouped; adding a dependency is a human decision.

## Agents and their tools

- Claude Code with this plugin; Codex CLI (`codex exec -m gpt-6.1-sol`) as the second reviewer and for image generation.
- plannotator for reviewing plans and annotating documents.
- agent-browser for driving the running app.
- Beads (`bd`) or Linear as the tracker, set in `sdlc.json`.
