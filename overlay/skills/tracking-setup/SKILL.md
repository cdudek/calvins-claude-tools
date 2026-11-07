---
name: tracking-setup
description: One-time analytics setup for a project or shared-packages repo - finds existing tracking calls, decides where the central tracking library lives, scaffolds a typed event registry, a track helper, destination adapters, consent and privacy guards, a test adapter, a lint rule and a registry test, writes the project's tracking doc and generated plan, and migrates old calls with a rename map. Use for "set up tracking", "tracking library", "event registry", "clean up our analytics", "centralise tracking". Skip when a registry already exists (tracking-apply) or for a read-only check (tracking-audit).
allowed-tools: "Read Grep Glob Edit Write AskUserQuestion Bash(git *) Bash(gh *) Bash(pnpm *) Bash(npm *) Bash(npx *) Bash(yarn *) Bash(bun *) Bash(uv *) Bash(python3 *)"
user_invocable: true
metadata:
  version: 1.0.0
---

# Tracking setup

Events are never defined at the call site. A project gets one central tracking library, like an i18n catalogue: a typed registry of every event, one helper that call sites use, and the only code allowed to talk to an analytics tool. This skill builds that library once, writes down the decisions the conventions leave open, and moves the existing calls onto it.

Read both references before the first step:

- `references/conventions.md`: naming, categories and routing, properties, identity, consent and privacy, lifecycle, limits. The rules.
- `references/library.md`: the registry, the helper, adapters, consent, privacy guard, identity, test adapter, lint rule, registry test and plan generator, with code. The shape.

Run it once per app repo, or once per shared-packages repo when several apps share events. After that, every feature uses `cct:tracking-apply`, and `cct:tracking-audit` checks the result.

## 1. Find what exists

Search the whole repo, generated and vendored folders excluded:

```bash
git grep -nE "posthog\.(capture|identify|group|alias|reset)|\bgtag\(|dataLayer\.push|\btrack(Event)?\(|analytics\.(track|page|identify)|mixpanel\.|amplitude\.|sendGAEvent|usePostHog|logEvent\(" -- ':!*.lock' ':!*.min.js'
git grep -nE "from ['\"](posthog-js|posthog-node|react-ga4|@next/third-parties/google|@segment/|mixpanel|@amplitude/)" -- ':!*.lock'
```

Also read the package manifests for analytics SDKs, the root layout or app entry for tag scripts and `init` calls, the consent banner, and the auth provider (where identify should happen).

Write an inventory in the scratchpad: every event name, file:line, properties sent, destination, consent check (yes or no), and whether it carries private data. Note duplicate inits (two `posthog.init`, a tag manager next to a direct tag).

## 2. Decide where the library lives

Apply the rule in `library.md`, "Where it lives":

- One deployable fires these events: inside the app, `src/lib/tracking/` or the stack's equivalent.
- Two or more deployables would fire the same event name: a shared package (`packages/tracking` in a monorepo, or a private published package next to shared `contracts` and `tokens` packages), with each app adding only its own events in an extension registry.

When the answer is a shared package in another repo, ask the owner which repo, then run this skill there first and come back to wire each app.

## 3. Record the open decisions

Write `docs/tracking.md` (or where the repo keeps docs). It holds what the conventions leave to the project. Infer what the code already shows; ask the owner, in one question round, only for the rest, offering the recommended default from `conventions.md` for each.

```markdown
# Tracking

The rules: <link or copy of the conventions>. The events: docs/tracking-plan.md (generated).

## Tools and routing
Product analytics: <tool, region, host>. Marketing analytics: <tool or none>. Routing: by category (conventions).
Marketing names: mapped in the library | in the tool's admin UI.

## Where the library lives
<path or package>, and why (one app | shared by <apps>).

## Values
app: <list>. surface: <list>. page_type: <list>. account_type: <list>. plan_tier: <list or none>.

## Identity
identify at <where>, group by <company or none>, reset at logout in <where>.

## Consent
Mechanism: <banner or framework>. Purposes to destinations: <map>. Before consent: drop | hold in memory.

## Server-side events
<which events, and why>.

## Data handling
Product analytics region: <>. Marketing retention: <>. Product retention: <>. Google Signals: <on or off, why>. Erasure: <how a deletion reaches each tool>.

## Owners
Product owner: <>. Registry owner: <>. Library owner: <>. Conventions owner: <>.

## Decisions
- YYYY-MM-DD: <decision>, chosen over <alternative>, because <reason>.
```

Never put keys, project IDs that are secret, or personal data in this file. The public product-analytics project key (`phc_...`) is not secret, but it belongs in the app's environment, not the doc.

## 4. Scaffold the library

Build the files in `library.md` "Layout", adapted to the stack (TypeScript is the main example; the last section names the Python, Ruby, mobile and Go equivalents). In order:

1. `define.ts` and `registry.ts`. Seed the registry with the core events every product needs (`page_view`, `consent_update`, `signup` if there is sign-up, `login_fail`) and with the canonical form of every event in the inventory.
2. `consent.ts`, `privacy.ts`, `context.ts`, `identity.ts`.
3. The adapters for the recorded tools, plus `memory.ts`. Move the SDK `init` calls into the adapters, in their privacy mode until consent. Remove every other init.
4. `track.ts`, `server.ts` if server events were recorded, `page-view.ts` hooked into the router once, `index.ts`.
5. Wire the auth provider to `identify` and logout to `reset`, and the consent banner to `consent.set`.

Keep the public key and host in the app's environment (`NEXT_PUBLIC_POSTHOG_KEY` or the framework's equivalent). Never a personal API key (`phx_...`) in the app.

## 5. Guard rails

1. The lint rule from `library.md`, merged into the project's existing lint config.
2. `registry.test.ts` from `library.md`, in the project's test runner.
3. One consent test with the memory adapter: nothing sent before consent, the right event after.
4. `scripts/tracking-plan.ts`, a `tracking:plan` script, and a CI step that regenerates `docs/tracking-plan.md` and fails on a diff.

## 6. Migrate the existing calls

Write the rename map into `docs/tracking.md` under `## Migration`, one row per inventory event:

| Old name | New name | Old properties | New properties | Dashboards, insights, models to repoint | Sunset |
| --- | --- | --- | --- | --- | --- |
| `Signup Completed` | `signup` | `method` | `signup_method` | <list> | YYYY-MM-DD |
| `apply_filter` | `filter_apply` | `group` | `filter_group` | <list> | YYYY-MM-DD |

Then:

1. Add each old name to the registry as `deprecated`, with `replacedBy` and a sunset at least 30 days out, so the library dual-fires it while dashboards are repointed. An old event nobody reads can go straight to `removed` once the owner confirms that.
2. Rewrite each call site to `track(events.x, props)`, fixing names, properties and private data on the way. Delete direct SDK calls.
3. Events that were firing before consent now wait for it; say so in the PR, since counts will drop.
4. Pull the "to repoint" column from the tool if credentials exist: `cct:posthog-manage` lists insights and cohorts using an event.

Large repos: migrate one surface per commit, each commit green.

## 7. Verify

Run, and show the output:

1. The project's typecheck, lint (zero restricted-syntax hits outside the library) and tests, the registry and consent tests included.
2. `tracking:plan`, then `git diff --exit-code docs/tracking-plan.md`.
3. Run the app with consent denied: the network panel or the E2E network log shows no requests to the analytics hosts. Grant consent: `page_view` arrives once per navigation, not twice.
4. With credentials, `cct:posthog-manage` confirms the events arrive in the product tool; for the marketing tool, its debug view.
5. `cct:tracking-audit` on the repo: no Critical or High finding left.

## Output

- The library in its folder, the lint rule, the registry and consent tests, the plan generator and its CI step.
- `docs/tracking.md` with the decisions and the migration map, `docs/tracking-plan.md` generated.
- A short report: events registered, call sites migrated, decisions still open with their owner.
