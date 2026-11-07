---
name: posthog-manage
description: Runs the PostHog API with your personal API key from the shell (POSTHOG_API_KEY, POSTHOG_HOST) without ever printing it - HogQL queries, event and property definitions, insights, feature flags, annotations, cohorts, and checking that a tracking plan's events arrive. Also covers secure key setup and reviewing what the PostHog setup wizard changed. Use when the user mentions PostHog, HogQL, "is the event arriving", feature flags, annotations or cohorts in PostHog. Skip for designing events (tracking-apply) and for numbers that live in another warehouse.
allowed-tools: "Bash(bash */posthog-manage/scripts/*) Bash(jq *)"
user_invocable: true
metadata:
  version: 1.0.0
---

# PostHog

Every call goes through the wrapper in this skill's folder, never bare `curl` with a key:

```bash
bash <skill>/scripts/ph check                                   # which variables are set, never their values
bash <skill>/scripts/ph query "SELECT event, count() FROM events WHERE timestamp > now() - INTERVAL 1 DAY GROUP BY event"
bash <skill>/scripts/ph GET "/api/projects/{project}/event_definitions/?limit=100"   # {project} becomes POSTHOG_PROJECT_ID
bash <skill>/scripts/ph POST "/api/projects/{project}/annotations/" '{"content":"Release 1.14.0","date_marker":"2026-01-15T10:00:00Z","scope":"project"}'
```

The wrapper takes `POSTHOG_API_KEY`, `POSTHOG_HOST` and `POSTHOG_PROJECT_ID` from the environment (or the user's zsh profile), sends the key as a header from stdin so it is never on a command line, prints the raw JSON and redacts anything shaped like `phx_...`. Pipe to `jq`.

## Key setup (the user does this once, in their own terminal)

Never paste a key into the chat. If one is pasted, say so, treat it as leaked, and ask the user to revoke it in PostHog and create a new one.

**Two kinds of key, never mixed up:**

| Key | Looks like | Secret? | Where it goes |
| --- | --- | --- | --- |
| Personal API key | `phx_...` | **Yes.** Acts as the user | the shell, for this skill and server scripts. Never in an app, a repo or CI logs |
| Project API key | `phc_...` | No, public | the client app's environment (`NEXT_PUBLIC_POSTHOG_KEY` or similar), for sending events |

**Create the personal key:** PostHog, Settings, Account, Personal API keys, Create. Label it after the machine. Give it access to only the projects it needs, and only the scopes it needs: `query:read`, `event_definition:read`, `property_definition:read`, `insight:read`, `cohort:read`, `feature_flag:read`, `annotation:read`, `project:read`; add `annotation:write`, `feature_flag:write` or `event_definition:write` only when the user wants those writes.

**Store it in the OS keychain and read it at shell start** (preferred). macOS, once; `-w` last makes it prompt, so the key never lands in shell history:

```bash
security add-generic-password -a "$USER" -s posthog-api-key -w
```

Then in `~/.zshrc`:

```bash
export POSTHOG_API_KEY="$(security find-generic-password -a "$USER" -s posthog-api-key -w 2>/dev/null)"
export POSTHOG_HOST="https://eu.posthog.com"
export POSTHOG_PROJECT_ID="12345"
```

- **Linux:** `secret-tool store --label="PostHog API key" service posthog-api-key` once, then `export POSTHOG_API_KEY="$(secret-tool lookup service posthog-api-key)"`; or with `pass`: `pass insert posthog/api-key`, then `export POSTHOG_API_KEY="$(pass show posthog/api-key)"`.
- **bash:** the same lines in `~/.bashrc`. **fish:** `set -gx POSTHOG_API_KEY (security find-generic-password -a $USER -s posthog-api-key -w 2>/dev/null)` in `~/.config/fish/config.fish`.
- **A plaintext export instead:** only if no keychain is available, then `chmod 600 ~/.zshrc`, and never commit or sync that file to a public dotfiles repo.

**Hosts.** The API host is the app host: `https://eu.posthog.com` (EU cloud) or `https://us.posthog.com` (US cloud), or the self-hosted URL. The ingestion hosts (`eu.i.posthog.com`, `us.i.posthog.com`) are for sending events from the app and refuse API calls; the wrapper stops on them. The project ID is in the URL of any project page (`/project/12345/...`) and in project settings; it is not secret.

**Rotate** the key in PostHog settings the moment it may have leaked (pasted, logged, committed), then update the keychain entry (`security add-generic-password -U ...`).

## Start of every session

```bash
bash <skill>/scripts/ph check
bash <skill>/scripts/ph GET "/api/projects/{project}/" | jq '{id, name, timezone}'
```

`check` prints `set` or `missing` for each variable. Any `missing`: tell the user which, point to Key setup, and stop. A 401 or 403 means the key is wrong or lacks a scope: name the scope from the endpoint (for example `query:read` for `/query/`), never look for another key.

## Rules

- **Never print or read the key:** no `cat`, `grep` or `source` of `~/.zshrc` or other profiles, no `env`, `printenv`, `echo $POSTHOG_API_KEY`, `set -x`, no key in a URL or a file. To test presence by hand: `zsh -ic '[ -n "$POSTHOG_API_KEY" ] && echo set || echo missing'`. Redact `phx_` in anything shown to the user.
- **Read freely:** every `GET` and every HogQL `SELECT`.
- **Keep personal data out of the output:** select named properties and aggregates; never `SELECT *`, never person properties like email or name, never raw `properties` blobs. Show counts, not people.
- **Ask before any write:** creating or changing a feature flag (it changes what real users see), an annotation, a cohort, an event definition, an insight. State the exact call, the value before and after, and the effect, then wait for a yes.
- **Never delete** a flag, cohort, insight, dashboard or definition unless the user named that exact one in the same turn. Turning a flag off is a write that affects production, too.
- **Batch queries:** the API is rate limited per key. One HogQL query with `GROUP BY` beats one call per event.

## What it covers

Recipes for each: `references/recipes.md`. Read the section before the first call.

- **HogQL** through `/api/projects/{project}/query/`: event counts, funnels, success measures, property coverage.
- **Events and properties:** event definitions, property definitions per event, last seen.
- **Tracking plan check:** do the registry's events arrive, with the expected properties, once? For a full conformance check with ranked findings, use `cct:tracking-audit`; this skill supplies its live data.
- **Insights and dashboards:** list, find the ones using an event (to repoint after a rename).
- **Feature flags:** list, read rollout, create or change on a yes.
- **Annotations:** mark releases and incidents.
- **Cohorts:** list and read definitions.

## The PostHog setup wizard

`npx -y @posthog/wizard@latest` (with subcommands such as `ai-observability`, `error-tracking`, `feature-flags`) installs and wires PostHog into a codebase. Claude cannot run it: it needs Node 22.22 or newer and an interactive terminal, and its `--ci` mode is not available in published builds.

1. Ask the user to run it in their own terminal, in a fresh branch or worktree with a clean tree, so its changes are one diff.
2. Afterwards, review the diff (`git diff`, `git status` for new files) against the project's tracking library (`cct:tracking-setup`):
   - a second `posthog.init` or provider next to the library's adapter: move the options into the adapter and delete the wizard's init;
   - `posthog.capture` calls the wizard added outside the library: move them into the registry and call `track(events.x, ...)` (`cct:tracking-apply`);
   - init without consent gating (persistence not memory, capturing not opted out until consent): fix per the library's consent rules;
   - automatic pageview turned on next to the library's `page_view`: turn it off;
   - keys: the project key (`phc_`) belongs in the app's environment, not hard-coded; any personal key (`phx_`) or `.env` file it wrote must be gitignored or removed;
   - any MCP or editor config it added: keep only what the user wants.
3. Run the project's typecheck, lint and tests, then `cct:tracking-audit` on the branch.

## In scripts

A script calls the wrapper (`subprocess`, `execFile`) so the key stays inside it. Never copy the personal key into a `.env`, a CI secret shared with forks, or code.
