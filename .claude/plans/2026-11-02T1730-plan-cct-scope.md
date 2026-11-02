---
type: plan
status: done
created: 2026-11-02T17:30
author: calvindudek
project: calvins-claude-tools
supersedes: none
---

# cct scope: what belongs in Calvin's plugin beyond the SDLC

## The question

cct today is the SDLC and the UX suite: 47 skills, 15 agents, two hooks, built by `scripts/build.py` from the OMR AI Kit and a few public plugins, then pruned to what `sdlc-run` and `project-kickoff` reach. The ask is to add the product (PM) and design skills, and to decide what else from the kit is worth carrying.

## The rule for taking a skill

A skill comes into cct when all three hold:

1. **Portable.** It works on HeyDiff, Snapmark or any next product without OMR's warehouse, brand, voice, Outline, Toggl, Billwerk, Jev, LangSmith, Fastly or OMR AI OS. A skill that reads `omr-data-infra-prod` or inlines OMR tokens is out, or comes in only once it reads the product's own tokens.
2. **Used in the loop.** It is reached from a stage of the SDLC, from `project-kickoff`, or from a job Calvin does weekly (write a PRD, read a cohort, cut a release). A knowledge skill nobody asks for is a description tax.
3. **Pays its description.** Every skill description competes for about one percent of the context window, and eviction drops the least-used first. Each addition should displace nothing Calvin uses more.

What cct is **not**: a mirror of the kit. The kit has 190 skills; cct should land near 70.

## What is already there, by plugin

- **omr-dev:** 44 of 66. Missing: the OMR-only six (`time-log`, `secret-set`, `engineering-metrics-track`, `jev-integrate`, `billing-manage`, `langsmith-analyze`), and 26 that the reachability prune dropped (listed under Engineering).
- **omr-ux:** all 11, as `ux-*`. **Design is done** at the kit level; nothing to add.
- **omr-pm:** 2 of 8 (`ai-ready-issues`, `write-ticket`).
- **omr-core:** none kept (`brand`, `tone-of-voice`, `copy-write` are copied, then dropped as OMR voice).
- **omr-data, omr-content, omr-gtm, omr-reviews, omr-context, omr-ai-os:** nothing, correctly.

## Milestone 1: product (omr-pm, all of it)

Take the six missing omr-pm skills: `develop-prd` (2.0.0 after kit PR #506: page one, decisions log, red team, impact), `product-playbook`, `break-down-epics`, `run-story-mapping`, `plan-roadmap`, `analyze-cohorts`. Together with the two already in, that is the whole PM plugin, and it is the only kit plugin cct takes whole: every one of the eight is a job Calvin does on his own products, none touches an OMR system.

Mechanism in `build.py`:

- copy every `omr-pm/skills/*` instead of the two named ones;
- add a `ROOTS` list to the prune (`sdlc-run`, `project-kickoff`, every omr-pm skill) so they survive the reachability pass;
- `product-playbook` references its siblings by `omr-pm:` name; the existing rewrite turns those into `cct:`.

Check: `develop-prd/template.md` is the mirror of `linear-manage/references/prd-template.md`; both land in cct from the same kit commit, so they match. Add the kit's `check-requirements-grammar.py` pair check to cct's tests so a partial rebuild cannot split them.

Release: `feat(pm): the product skills` → cct 0.3.0.

## Milestone 2: engineering, the generic 11 of the pruned 26

The prune drops anything `sdlc-run` does not reach. These are reached by Calvin, not by the SDLC, so they need to be roots. Take, in this order of use:

| Skill | Why |
|---|---|
| `release-cut` | every milestone becomes a release; today that is done by hand |
| `codex-run` | the second opinion outside pr-review |
| `github-manage` | PR state, rulesets, auto-merge from one place |
| `dependency-review` | Dependabot PRs on four repos |
| `api-design` | HeyDiff's MCP and API surface |
| `data-model-create` | drizzle schemas start from an ERD |
| `docs-audit` | README, deploy docs, AGENTS.md drift |
| `dockerfile-review` | the Cloud Run image |
| `sentry-issues-fix` | if Sentry is wired; else skip |
| `queries-optimize` | Postgres on Cloud Run |
| `tracking-apply` | the success-measure events the plan stage names |

Leave out, with the reason:

- `design-patterns`, `distributed-patterns`: knowledge skills, asked for about never; a description each for nothing.
- `incident-respond`, `iac-security-review`, `k8s-workloads-audit`, `gcp-posture-audit`: OMR's on-call and cluster shape.
- `aws-manage`, `cloudflare-manage`, `fastly-manage`: the stack is GCP Cloud Run.
- `posthog-*` (3), `payments-integrate`, `vectorstore-scaffold`, `gsap-animate`, `scroll-animate`: take the day a product uses PostHog, takes money, embeds, or ships a marketing page with motion. Not before. [NEEDS CLARIFICATION: does HeyDiff use PostHog today?]
- `e2e-audit`, `ticket-validate`, `role-test-fixer`, `role-conventional-commits`: internal to kit flows cct does not run.
- `claude-setup-apply`, `claude-setup-audit`: OMR's Claude setup; cct's own docs are the setup.

Release: `feat(dev): the engineering skills Calvin runs by hand` → 0.4.0.

## Milestone 3: data, the portable half of omr-data

omr-data splits cleanly. Six skills are the OMR warehouse and pipeline (`query-run`, `ask`, `bq-access-grant`, `dag-scaffold`, `model-scaffold`, `model-diff`, `semantic-model-create`, `semantic-layer-audit`): out. Five are method:

- `analyze`: pull, clean, insight, executive summary. Generic. **Take.**
- `model-train`: forecasting, NLP, embeddings, with plain-language metrics. Generic. **Take.**
- `network-analyze`: graphs and communities. Generic, rare. Take, it is one description.
- `chart-create`, `report-create`: generic method, **OMR branding baked in** (matplotlib style, PDF cover). Take only with a style layer that reads the product's `tokens.json` from the context repo the way `project-kickoff` does. That is a small patch in `build.py` (`PATCHES`), not a fork.

Release: `feat(data): analyze, model, network` → 0.5.0; charts and reports in 0.5.x once the token style exists.

## Milestone 4: core, two of eleven

- `presentation-create`, `pdf-create`: decks and PDFs; take if they can run on the product's tokens, same style layer as charts. [NEEDS CLARIFICATION: do they inline OMR tokens today?]
- `transcripts-fix`: generic, cheap. Take.
- Out: `brand`, `tone-of-voice`, `copy-write` (OMR voice; cct's voice lives in the product's context repo and `project-kickoff`), `docs-search` (Outline), `mcp-and-artifacts` (OMR AI OS), `skill-names-fix`, `template-apply`, `pitch-create` (take with Milestone 4 only if a deck is actually needed).

## Build changes that make this safe

1. **`ROOTS` instead of two hard-coded names.** The prune walks from every root; a skill is a root when Calvin calls it directly.
2. **Allowlists, not blocklists.** `OMR_ONLY` says what to leave out of omr-dev; after Milestones 2 to 4 the lists say what to take from omr-pm, omr-data and omr-core. A new kit skill then stays out until someone decides, instead of appearing in cct by default.
3. **A dangling-reference check.** Today an `omr-x:name` that is not in cct is left as written and resolves to nothing at runtime. After the rewrite, fail the build on any remaining `omr-[a-z]+:` token in a kept file, and print the skill that needs it, so the decision is made at build time and not when a skill silently calls nothing.
4. **The mirror check.** Run the kit's `check-requirements-grammar.py` pairs over `plugins/cct` in `scripts/test_build.py`.
5. **A description budget line** in `docs/skill-map.md`: the count and the summed description characters, so growth is a number in the diff.

## Not in this plan

- Any omr-content, omr-gtm, omr-reviews or omr-context skill: marketing and GTM for OMR's units.
- Replacing public plugins (superpowers, ponytail, impeccable): they are vendored as they are.
- A second plugin: one prefix, `cct:`, stays.

## Done

- `python3 scripts/build.py` produces every skill in Milestones 1 to 3 under `plugins/cct/skills/`, `docs/skill-map.md` lists each with its origin, and the dangling-reference check passes.
- `claude plugin update cct@cct` installs it and `/cct:develop-prd` opens the 2.0.0 skill.
- Skill count after Milestone 3: about 68.

## Revisions (2026-11-02, built)

All four milestones and the build changes landed in one PR, as cct 0.3.0: 45 skills became 68, 15 agents unchanged, 32,724 description characters.

- **The open questions are closed.** No product uses PostHog or Sentry (checked the HeyDiff, Snapmark and Samplewerk manifests), so `posthog-*` and `sentry-issues-fix` stay out.
- **Deck, PDF, chart and report stay out.** `presentation-create`, `pdf-create`, `chart-create` and `report-create` ship OMR Sans and the OMR logo as files, not as a token they read. They need a style layer on the product's `tokens.json`, which is its own change, not a build patch.
- **Design was not done.** `ux-run` was the one omr-ux skill nothing reached; it is a root now. `ux-laws-apply` is a root too.
- **A bug the roots fixed.** `aws-manage` and `cloudflare-manage` (PR #12) were copied by the overlay and then deleted by the prune, since nothing rooted them. They are roots now.
- **The dangling check found six calls on its first run,** three of them already on main: `cct:brand`, `cct:tone-of-voice` and `cct:vue-code-write` pointed at skills the build drops. Every call into a skill cct does not carry is now rewritten to say so, with its reason from `NOT_CARRIED`, and an unnamed one fails the build.
- **The mirror check runs in `build.py`,** not a separate test, because the build is the only thing that writes `plugins/cct/`.
- **Not fixed here:** seven tests fail in `plugins/cct` on main and on this branch alike: four in `sdlc-run` (the goal texts pass 1000 characters once cct appends its agents rule) and three contract tests in `pr-review` and `review-fix-loop`. Separate PR.
