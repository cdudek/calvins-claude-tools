---
name: posthog-manage
description: Runs PostHog from the shell with your personal API key, never printing it - feature flags and rollouts, experiments and their results, dashboards, insights, trend, funnel and retention reports, HogQL, session recordings and console logs, persons, cohorts, surveys, annotations, error tracking, event definitions. Every write is a dry run with an approval code until confirmed. Use when the user names PostHog or HogQL, or asks to read or change a PostHog flag, experiment, dashboard, insight, recording or cohort. Skip for other analytics tools and for app tracking code (tracking-apply).
allowed-tools: "Bash(bash */posthog-manage/scripts/*) Bash(jq *)"
user_invocable: true
metadata:
  version: 2.1.0
---

# PostHog

Every call goes through `bash <skill>/scripts/ph`, never bare `curl` with a key. It reads `POSTHOG_API_KEY`, `POSTHOG_HOST` and `POSTHOG_PROJECT_ID` from the environment (or the user's zsh profile), keeps the key out of child processes, sends it to curl on stdin so it is never on a command line, runs curl with `-q` (no `~/.curlrc`), `https` only and no redirects, and redacts anything shaped like `phx_...` in the output, curl's errors and dry runs included.

Output is one compact JSON object per line (no output means no rows); add `--table` to read it or `--csv` to hand it on. The exceptions: `check` and dry runs print plain lines, `dashboards url` and `insights url` print a link, `use` prints an `export` line, `recordings export` prints a summary of the file it wrote. Notes go to stderr, and **a line starting `posthog-manage: partial` means the list or query is incomplete**: say so, and raise `--limit` or narrow the query before drawing a conclusion. `ph help` lists every command and `ph <area> --help` one area; neither needs credentials.

## First run

1. The user creates a personal API key (Key setup below) and exports it, preferably from the OS keychain; a plain `export` in `~/.zshrc` works too, then `chmod 600 ~/.zshrc`.
2. Run:

   ```bash
   bash <skill>/scripts/ph check     # set or missing per variable, never values
   bash <skill>/scripts/ph whoami    # organizations, every project with its id; finds the region if POSTHOG_HOST is unset
   ```

   Success: `check` says `set` for the key, and `whoami` lists at least one project. A 401 or 403 there means the key is wrong or lacks `user:read`.

3. The user adds the two lines `whoami` and `use` print to their profile:

   ```bash
   export POSTHOG_HOST=https://eu.posthog.com     # or https://us.posthog.com, or the self-hosted URL
   export POSTHOG_PROJECT_ID=<id>                 # bash <skill>/scripts/ph use <id> checks it and prints this line
   ```

4. Success check: `bash <skill>/scripts/ph events top --days 7 --table` prints the project's events.

Without `POSTHOG_HOST` the wrapper tries EU, then US, on every run and says which one worked. Without `POSTHOG_PROJECT_ID` it uses the only project, or stops and lists them when there are several or when an organization could not be listed. A 401 or 403 names the call; the key is wrong or lacks that scope. Never look for another key.

## Commands

| Area | Commands (`ph ...`) |
| --- | --- |
| Setup | `check`, `whoami`, `projects`, `use <id>` |
| Feature flags | `flags list [--active] [--search S] [--limit N]`, `flags get <key\|id>`, `flags evaluate <flag> <distinct-id>`, `flags create <key> [--name N] [--rollout PCT] [--prop k=v\|k~v]... [--variants a:50,b:50] [--active]`, `flags rollout <flag> <PCT> [--condition N]`, `flags enable\|disable\|delete <flag>` |
| Experiments | `experiments list [--status S]`, `experiments get <id>`, `experiments results <id>`, `experiments create <name> --flag <key> [--variants control:50,test:50] [--event E \| --funnel e1,e2] [--allow-unknown-events]` (an existing flag is reused as it is), `experiments launch <id>`, `experiments stop <id> [--conclusion won\|lost\|inconclusive\|stopped_early\|invalid] [--comment C]`, `experiments archive <id> [--disable-flag]`, `experiments delete <id>` |
| Dashboards | `dashboards list`, `dashboards get <id>` (tiles), `dashboards url <id>`, `dashboards create <name>`, `dashboards add <dashboard-id> <insight-id>`, `dashboards delete <id>` |
| Insights | `insights list [--search S]`, `insights get <id\|short-id>` (computed result), `insights url <id>`, `insights create trend <event> \| funnel <e1> <e2>... \| hogql 'SQL' --name N [--dashboard ID]`, `insights delete <id>` |
| Reports | `trend <event> [--days N \| --from DATE --to DATE] [--interval hour\|day\|week\|month] [--breakdown PROP] [--math total\|dau\|weekly_active\|monthly_active]`, `funnel <e1> <e2>... [--days N \| --from DATE --to DATE] [--window DAYS] [--breakdown PROP]`, `retention <event> [--return-event E] [--period Day\|Week\|Month] [--intervals N]`, `events top [--days N]`, `query 'HogQL'` |
| Recordings | `recordings list [--days N] [--person ID\|EMAIL] [--min-duration SEC] [--errors] [--url TEXT] [--limit N]`, `recordings get <session-id>`, `recordings console <session-id> [--level error]`, `recordings events <session-id>`, `recordings export <session-id> <file>`, `playlists list`, `playlists add <short-id> <session-id>` |
| People | `persons find <distinct-id\|email>`, `persons events <distinct-id\|email> [--days N]`, `cohorts list`, `cohorts create-static <name> <distinct-id>... \| @ids.txt` |
| Other | `annotations list\|create <text> [--date ISO]\|delete <id>`, `surveys list\|get <id>\|results <id> [--days N]`, `errors list [--status S]`, `events list [--search S]`, `events describe <name>`, `events verify <name>`, `properties list [--event NAME]`, `actions list` |
| Raw | `ph METHOD /path [json\|@file.json]`; `{project}` in the path becomes the project id; a raw read prints the API's answer unfiltered |
| Global | `--yes CODE`, `--table`, `--csv`, `--personal`, `--` (everything after it is a plain argument) |

Recipes and output shapes for each area: `references/recipes.md`. Read the section before the first call in that area.

## Safety rules

- **Writes are dry runs.** Every command that changes something (`create`, `rollout`, `enable`, `disable`, `launch`, `stop`, `archive`, `delete`, `add`, `verify`, and a raw `POST`, `PATCH`, `PUT` or `DELETE` other than a query) prints what it will change, the exact request and an approval code, then stops. The code hashes the request and the current state of the object it changes (a flag's conditions and version, an experiment's dates and metrics, an `@file`'s bytes). The same command with `--yes CODE` sends it only if nothing changed; otherwise it refuses (exit 3) and the dry run must be shown again. Show the user the dry run, then send with its code.
- **Ask before anything that reaches real users:** enabling a flag, raising a rollout, changing a flag's conditions or variants, launching or stopping an experiment, archiving with `--disable-flag`. Show the before and after from the dry run and wait for a yes in this turn. A flag change is live for real users at once.
- **Ask before every other write too** (dashboards, insights, annotations, cohorts, definitions), unless the user asked for exactly that change in the same turn.
- **Deletes** only for the object the user named. Flags, experiments, dashboards, insights and annotations are soft-deleted (PostHog marks them `deleted`); deleting an experiment leaves its flag, which needs its own `flags delete`.
- **Never print or read the key:** no `cat`, `grep` or `source` of a profile, no `env`, `printenv`, `echo $POSTHOG_API_KEY`, `set -x`, no key in a URL or a file. Never paste a key into the chat; if the user pastes one, say it is leaked and must be revoked.
- **Personal data stays out of the chat:** by default the wrapper prints no emails or distinct IDs (`whoami`, `persons find`, `recordings`), replaces emails in console messages, errors and flag conditions with `[email]`, drops URL query strings and fragments, and leaves person properties out of `flags evaluate`. `--personal` shows them; use it only when the user asks for that person's data in this turn. Show counts and ids; never `SELECT *` or raw `properties` blobs; raw reads (`ph GET`) are unfiltered, so project them with `jq`.
- **Recording exports hold personal data** (what people typed and saw). `recordings export` writes only to a new file at a path the user gives: it refuses an existing name or a symlink, any folder inside a git repository, and any folder other users can write to; creates the file exclusively, readable by the user only (mode 600); and removes a partial file when a download fails. Never write one into a repo, a shared folder or the chat.
- **Batch:** the API is rate limited per key. One HogQL query with `GROUP BY` beats one call per event.

## Typical requests

- **"Roll out new-checkout to 20 %."** `flags get new-checkout` (state, conditions, rollout now), then `flags rollout new-checkout 20` (dry run). Tell the user: active or not, which condition, 5 % -> 20 %, who that reaches. On a yes, rerun with `--yes <code>`, then `flags get` to confirm. A flag with several conditions: name the one with `--condition N`.
- **"How is experiment Y doing?"** `experiments list --table` to find it, `experiments get <id>`, then `experiments results <id>`: per variant the exposures, the estimate (a conversion rate, a mean per exposure or a ratio, as `estimate_is` says), chance to win (Bayesian) or p-value (frequentist), significant or not, the interval, and PostHog's `validation_failures`. Say plainly whether there is a winner; any validation failure or a small exposure count means wait, not a result. Stopping or shipping is the user's call.
- **"Weekly report."** `events top --days 7 --table` for volume, `trend <key event> --days 28 --interval week --table` for each event the user cares about, `funnel` for the main conversion, `retention <signup event> --period Week --intervals 8`. Report numbers with their week-over-week change; add `annotations list` so steps have causes. To keep it in PostHog, `insights create ... --dashboard ID` (asks first).
- **"Show me recordings with errors from today."** `recordings list --days 1 --errors --table`; then for the ones worth a look `recordings get <id>` (duration, active time, clicks, error count, start URL, replay link) and `recordings console <id> --level error`. Give the user the replay links.
- **"Why did this user struggle?"** `recordings list --person <email> --days 7`, then for one session `recordings events <id>` and `recordings console <id>`. An empty console with a `capture is off` or `expired` note means nothing was captured, not that nothing went wrong.
- **"Mark the deploy."** `annotations create "Release 1.14.0: new checkout"` (now, or `--date`), then `--yes <code>` on a yes.

## Recordings: what Claude can and cannot see

Claude cannot watch a replay; it is a video-like rrweb stream. It answers from what the API gives as data:

- **Metadata** (`recordings get`): duration, active and inactive seconds, click, keypress and mouse counts, console log, warning and error counts, start URL, person, and the replay link (`<host>/project/<id>/replay/<session-id>`) for the user to watch.
- **Console logs** (`recordings console`): the browser console messages, oldest first.
- **Events of the session** (`recordings events`): HogQL over `events` where `$session_id` is that session: pageviews, autocaptured clicks, exceptions, custom events, in order. This shows the path, where it stopped and what failed.
- **Raw snapshots** (`recordings export`): the rrweb stream as JSON lines, each `[window_id, event]` (DOM snapshots and mutations, mouse, scroll and input events). Useful for a tool that replays or searches it; still not something to read by eye.

Rage clicks, dead clicks and "stuck" moments show up as many clicks or errors in a short time in the session's events; say what the data shows and send the user the link for the rest.

## The official PostHog MCP connector

If the user has PostHog's MCP connector (its tools appear as PostHog tools in the session), prefer it for interactive exploration: it signs in with OAuth, so no personal key sits in a profile. Use this wrapper when the connector is missing, for output to pipe or save (`--csv`, recording exports), and when a dry run before a write matters. Never use both for the same write.

## Key setup (the user does this once, in their own terminal)

**Two kinds of key, never mixed up:**

| Key | Looks like | Secret? | Where it goes |
| --- | --- | --- | --- |
| Personal API key | `phx_...` | **Yes.** Acts as the user | the shell, for this skill and server scripts. Never in an app, a repo or CI logs |
| Project API key | `phc_...` | No, public | the client app's environment (`NEXT_PUBLIC_POSTHOG_KEY` or similar), for sending events |

**Create the personal key:** PostHog, Settings, Account, Personal API keys, Create. Label it after the machine; give it only the projects it needs. Read scopes for the whole skill: `user:read`, `organization:read`, `project:read`, `query:read`, `feature_flag:read`, `experiment:read`, `dashboard:read`, `insight:read`, `session_recording:read`, `session_recording_playlist:read`, `person:read`, `cohort:read`, `annotation:read`, `survey:read`, `error_tracking:read`, `event_definition:read`, `property_definition:read`, `action:read`. Add the matching `:write` scope only for what the user wants to change (`feature_flag:write`, `experiment:write`, `dashboard:write`, `insight:write`, `annotation:write`, `cohort:write`, `session_recording_playlist:write`, `event_definition:write`).

**Store it in the OS keychain and read it at shell start** (preferred). macOS, once; `-w` last makes it prompt, so the key never lands in shell history:

```bash
security add-generic-password -a "$USER" -s posthog-api-key -w
```

Then in `~/.zshrc`:

```bash
export POSTHOG_API_KEY="$(security find-generic-password -a "$USER" -s posthog-api-key -w 2>/dev/null)"
```

- **Linux:** `secret-tool store --label="PostHog API key" service posthog-api-key` once, then `export POSTHOG_API_KEY="$(secret-tool lookup service posthog-api-key)"`; or `pass insert posthog/api-key` and `export POSTHOG_API_KEY="$(pass show posthog/api-key)"`.
- **bash:** the same lines in `~/.bashrc`. **fish:** `set -gx POSTHOG_API_KEY (security find-generic-password -a $USER -s posthog-api-key -w 2>/dev/null)`.
- **Plain export:** only without a keychain; then `chmod 600 ~/.zshrc`, and never commit or sync that file to a public dotfiles repo.

**Hosts.** The API host is the app host: `https://eu.posthog.com`, `https://us.posthog.com` or the self-hosted URL. The ingestion hosts (`eu.i.posthog.com`, `us.i.posthog.com`) refuse API calls; the wrapper stops on them. In a zsh one-liner of your own, quote curl's `--proto '=https'`: unquoted, zsh treats `=https` as a command lookup.

**Rotate** the key in PostHog the moment it may have leaked, then update the keychain entry (`security add-generic-password -U ...`).

## The PostHog setup wizard

`npx -y @posthog/wizard@latest` (subcommands such as `feature-flags`, `error-tracking`, `ai-observability`) installs and wires PostHog into a codebase. Claude cannot run it: it needs Node 22.22 or newer, an interactive terminal the user runs themselves, and a browser sign-in; its `--ci` mode is not available in published builds.

1. Ask the user to run it in their own terminal, in a fresh branch or worktree with a clean tree, so its changes are one diff.
2. Review the diff (`git diff`, `git status` for new files) against the project's tracking library (`cct:tracking-setup`):
   - a second `posthog.init` or provider next to the library's adapter: move the options into the adapter and delete the wizard's init;
   - `posthog.capture` calls outside the library: move them into the registry and call `track(events.x, ...)` (`cct:tracking-apply`);
   - init without consent gating: fix per the library's consent rules;
   - automatic pageview on next to the library's `page_view`: turn it off;
   - keys: the project key (`phc_`) belongs in the app's environment, not hard-coded; any personal key (`phx_`) or `.env` it wrote must be gitignored or removed;
   - any MCP or editor config it added: keep only what the user wants.
3. Run the project's typecheck, lint and tests, then `cct:tracking-audit` on the branch.

## In scripts and tests

A script calls the wrapper (`subprocess`, `execFile`) so the key stays inside it. Never copy the personal key into a `.env`, a CI secret shared with forks, or code. `scripts/test_ph.sh` checks the wrapper's guards and command contracts offline with a stub `curl` (approval codes, redaction, partial results, personal data, experiments, export): run it after any change to `ph`, also under `/bin/bash` (`PH_BASH=/bin/bash bash scripts/test_ph.sh`) since macOS ships bash 3.2.
