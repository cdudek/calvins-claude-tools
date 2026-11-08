---
name: cloudflare-manage
description: Runs the Cloudflare API and wrangler with the token from your shell (CLOUDFLARE_API_TOKEN), without ever printing it. Zones and nameservers, DNS records, SSL modes, zone settings, Origin, Transform and cache rules, Workers and wrangler deploys, Pages, R2, and the CF-IPCountry country header. Use when the user mentions "Cloudflare", "wrangler", "Workers", "orange cloud", "proxied record", "CF-IPCountry", "Cloudflare DNS", "nameservers to Cloudflare", or asks to list, inspect, create or change anything in Cloudflare. Skip for AWS Route53 or CloudFront (aws-manage), Vercel and Google Cloud.
allowed-tools: "Bash(bash */cloudflare-manage/scripts/*) Bash(jq *)"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Cloudflare

Every call goes through the wrapper in this skill's folder, never bare `curl` with a token and never bare `wrangler`:

```bash
bash <skill>/scripts/cf GET /zones                                 # v4 API: METHOD /path [json-body | @file.json]
bash <skill>/scripts/cf GET "/accounts/{account}/workers/scripts"  # {account} becomes the account id
bash <skill>/scripts/cf wrangler deploy                            # wrangler with the token and account set
```

The wrapper takes `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` from the environment (or the user's zsh profile), sends the token as a header from stdin, and prints the raw JSON. Pipe to `jq`: every response has `.success`, `.errors` and `.result`.

## Prerequisites

| Needs | How |
| --- | --- |
| `CLOUDFLARE_API_TOKEN` | A scoped API token (Cloudflare dashboard → My Profile → API Tokens), exported in the shell profile. Never pasted into the chat. |
| `CLOUDFLARE_ACCOUNT_ID` | The account id from any zone's Overview page; not a secret. |
| `curl`, `jq` | Preinstalled on macOS / `brew install jq`. |
| `node` (`npx`) | Only for `cf wrangler`. |

## Start of every session

```bash
bash <skill>/scripts/cf GET "/accounts/{account}/tokens/verify" | jq '{ok:.success, status:.result.status}'
bash <skill>/scripts/cf GET /zones | jq -c '[.result[] | {name, id, status, plan:.plan.name}]'
```

A failed call with code 10000 or "Authentication error" means the token lacks that permission: name the permission the user must add, do not look for another token.

## Rules

- **Never print the token** and never read the shell profile to find it: no `cat`, `grep`, `env`, `printenv`, `echo $CLOUDFLARE_*` or `set -x` around the wrapper. Account and zone ids are not secret.
- **Read freely:** every `GET`, `wrangler whoami`, `wrangler deployments list`, `wrangler tail`.
- **Ask before any write:** `POST`, `PUT`, `PATCH`, `DELETE`, `wrangler deploy`, `wrangler secret put`, a nameserver change, an SSL mode, a rule. State the exact call, the value before and after, and the effect, then wait for a yes. DNS and SSL changes can take a site or its mail offline.
- **Never delete** a zone, record, Worker or bucket unless the user named that exact resource in the same turn. Never touch MX, SPF, DKIM, DMARC or mail-verification records as a side effect of other work.
- **Before a DNS change, export the zone** (`GET /zones/ZONE/dns_records/export`) so every record can be put back.
- **A rulesets `PUT` replaces the whole phase:** read the phase first and send it back with the change.

## Recipes

Zones, DNS, settings, rules, Workers, the country header and Cloud Run behind Cloudflare: `references/recipes.md`. Read the section you need before the first write.

## In scripts

A script calls the wrapper (`subprocess`, `execFile`) so the token stays inside it. Never copy the token into a `.env`, a `wrangler.toml` or code; Worker secrets go in with `cf wrangler secret put NAME`, which reads the value from stdin.
