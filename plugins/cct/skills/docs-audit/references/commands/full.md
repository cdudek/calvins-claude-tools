---
description: Full audit of every documentation file in the repository against the current code and tooling. Slow but exhaustive.
---

The user input is: $ARGUMENTS

Parse `$ARGUMENTS` as an optional path:

- empty → audit every doc in the repo
- a path → restrict to docs under that path (e.g. `docs/`, `app/`)

This is **full mode** — no `git diff`, no merge-base, no change set. Every documentation file is read and verified against the current code, filesystem, and tooling. Use this for periodic health checks, post-refactor sweeps, onboarding prep, or when a CLAUDE.md / README feels out of sync but you can't point to a specific change.

For PR-prep / per-change audits, use `/cct:docs-audit diff` instead (much faster — only reads docs affected by the diff). Diff mode also runs automatically as a step of `cct:git-pr-run`, so most pre-PR audits happen without you invoking anything manually.

## Step 1: Enumerate every doc

Collect all documentation files in the repo:

```sh
git ls-files '*.md' 'CLAUDE.md' 'AGENTS.md' 'README.md'
```

`git ls-files` only returns tracked files, so it already excludes `node_modules/`, `dist/`, etc. — no extra filter is needed in the common case. If a particular repo tracks generated docs (rare), filter them out in Step 1b below.

If a path argument was provided, restrict to it (e.g. `docs/` or `app/services/`).

Step 1a: **Resolve symlinks** — if `CLAUDE.md` is a symlink to `AGENTS.md` (or vice versa), audit the resolved file once and note the alias in the report. Likewise for any other symlinked docs.

Step 1b: **Skip generated docs** — drop any file whose first 20 lines contain `<!-- generated -->`, `<!-- DO NOT EDIT -->`, or `auto-generated`. List each as Info ("generated file — regenerate if stale, do not edit by hand") and move on.

Step 1c: **Cost guardrail** — count the candidate docs remaining after 1a/1b (post-symlink-dedup, post-generated-skip). Call this *N*.

- *N* ≤ 50 candidates → proceed with the full audit.
- *N* > 50 and **no path argument was given** → **STOP**. Print: "This repo has *N* candidate docs (post-symlink-dedup, post-generated-skip) — a no-filter full audit would exceed the safe context budget (rough rule of thumb: each doc consumes ~800 tokens to read plus 2–5× for verification reads). Re-run with a path argument, e.g. `/cct:docs-audit full docs/` or `/cct:docs-audit full app/services/`." Do not partially audit; require the user to make the scoping choice.
- *N* > 50 and a path argument was given → proceed (the user explicitly scoped the audit).

The 50-doc threshold is calibrated against measured repo sizes: a repo with ~27 docs (~22k tokens) passes; repos with 50 to 100 docs require scoping. The threshold is a heuristic — if a repo's docs are unusually small, full mode may still be safe above 50; if they're unusually large, even 50 may be too many. When unsure, scope to a subdirectory.

## Step 2: Build the source-of-truth index

Before reading docs, gather the facts each claim will be verified against. Read these in parallel (one tool call each, all in one message):

- `package.json` (or `Gemfile`, `pyproject.toml`, `Cargo.toml` — whichever exists)
- `Makefile` (top-level targets via `grep -E '^[a-zA-Z_][a-zA-Z0-9_-]*:' Makefile`)
- `docker-compose*.yml` (service names, ports)
- `Dockerfile` (base image, exposed ports, key ENV)
- `.env.example` (variable names, no values)
- `.krane/**` (if present — deployment manifests)
- `config/routes.rb` (Rails) or `nuxt.config.ts` / `app.config.ts` (Nuxt) or `pages/**` / `app/**` (Next/Nuxt route files)
- The repo's root-level dotfiles relevant to tooling (`.nvmrc`, `.ruby-version`, `.tool-versions`)

Treat these reads as the source-of-truth snapshot for the rest of the audit. Don't re-read the same file twice — when later steps need to verify a claim against (say) `Makefile`, work from the version already in your context. If the conversation has been compacted and you no longer see the read, re-read it once and note that you did.

## Step 3: Audit each doc

For each doc, read it once, then verify every concrete claim. Verification methods and severity assignments live in **`../references/workflow.md`** — that's the canonical table. Apply those rules; do not invent local variants.

Full-mode specifics on top of the canonical rules:

- For claims that involve symbols (class names, function names, GraphQL types, route names), grep the relevant directories. Don't fabricate claims-not-made; only verify what the doc actually says.
- The "missing entirely" definition for architecture claims (see `workflow.md` § *Architecture claims*) is operational: `git grep -li '<entity>' --` over tracked source. Apply it as written; do not weaken to "I couldn't think of where to look".
- Full mode is reading every doc, so the **Confirmed up-to-date** section will be long. That's the value — it tells the user which docs were audited and passed, not just which are broken.

## Step 4: Cross-doc consistency

After auditing each doc in isolation, also check for **drift between docs**:

- Two docs that describe the same checklist, command list, or architecture diagram should agree. If they don't, **flag both** as Warning with the divergence, and note which was edited more recently (`git log -1 --format=%aI <file>`) so the user has a starting point. Do not auto-pick a winner — "most recent" doesn't mean "correct".
- A pointer like `see docs/X.md for details` should match what `docs/X.md` actually covers.

## Step 5: Report

Emit the report format defined in `../SKILL.md` under "Output format" — same severity buckets (Critical / Warning / Info / Confirmed up-to-date). For full mode, the **Confirmed up-to-date** section will be long and is important: it tells the user which docs *were* audited and passed.

Add a top-line summary:

```
Audited <N> doc files (<M> read, <K> skipped as generated/excluded).
Findings: <c> Critical · <w> Warning · <i> Info · <ok> Confirmed up-to-date.
```

## Step 6: Offer to fix

After the report, ask:

> "Want me to fix any of these? Reply with the finding numbers (e.g. `1,3`), `all critical`, `all`, or `no`."

Same rule as the diff command: only edit docs after explicit user direction; never modify source code; surgical edits per the repo's engineering principles.

## Constraints

- **Do not modify source code.** This skill audits docs only.
- **Do not run lints, tests, or builds.** The audit is read-only against git and the filesystem.
- **Do not fetch external URLs.** Out of scope.
- **Stay within the repo.** Do not cross worktree or repo boundaries.
- **Cap is implicit via Step 1c** — repos with > 50 candidate docs require a path argument; the audit otherwise refuses to proceed rather than partially audit and silently skip files.
- **Read each doc once.** Don't re-read the same file; if a claim needs cross-reference, read the *other* doc.
