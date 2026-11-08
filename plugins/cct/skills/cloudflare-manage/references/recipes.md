# Cloudflare recipes

`cf` below is `bash <skill>/scripts/cf`. `ZONE` is a zone id from `GET /zones`.

## Zones and DNS

```bash
cf GET "/zones?name=example.com" | jq -r '.result[0].id'
cf GET "/zones/ZONE/dns_records?per_page=500" | jq -c '.result[] | {id, type, name, content, proxied, ttl}'
cf GET /zones/ZONE/dns_records/export > zone-before.txt
cf POST /zones/ZONE/dns_records '{"type":"CNAME","name":"www","content":"origin.example.net","proxied":true,"ttl":1}'
cf PATCH /zones/ZONE/dns_records/RECORD '{"proxied":false}'
```

Adding a zone returns the two nameservers the registrar must use. Before the nameserver switch, copy every existing record into the new zone (mail records included) and compare the two record sets name by name:

```bash
cf POST /zones '{"name":"example.com","account":{"id":"ACCOUNT_ID"},"type":"full"}' | jq '.result | {id, name_servers}'
```

## Zone settings

```bash
cf GET /zones/ZONE/settings/ssl | jq -r .result.value        # off | flexible | full | strict
cf PATCH /zones/ZONE/settings/ssl '{"value":"strict"}'
cf PATCH /zones/ZONE/settings/always_use_https '{"value":"on"}'
cf GET /zones/ZONE/settings/ip_geolocation | jq -r .result.value
```

## Rules (one entrypoint ruleset per phase)

```bash
cf GET /zones/ZONE/rulesets/phases/http_request_origin/entrypoint | jq '.result.rules'           # Origin rules
cf GET /zones/ZONE/rulesets/phases/http_request_late_transform/entrypoint | jq '.result.rules'    # request header transforms
cf GET /zones/ZONE/rulesets/phases/http_request_cache_settings/entrypoint | jq '.result.rules'    # cache rules
cf PUT /zones/ZONE/rulesets/phases/http_request_cache_settings/entrypoint @rules.json             # replaces the phase
```

A phase that has never been set answers 404 on `GET`; the first `PUT` creates it.

## Workers

From a folder with a `wrangler.toml` (or `wrangler.jsonc`):

```bash
cf wrangler deploy
cf wrangler tail WORKER_NAME
cf GET "/accounts/{account}/workers/scripts" | jq -r '.result[].id'
```

## The visitor's country

On a proxied hostname, Cloudflare adds `CF-IPCountry` (ISO 3166 alpha-2; `XX` unknown, `T1` Tor) to every request it forwards; IP geolocation is on by default. The origin should trust the header only for requests that came through Cloudflare. An origin that is also reachable directly (a `*.run.app` URL, a load balancer IP) can be sent a forged header, so use it for a display label, not for anything that decides money, access or law.

## Cloud Run behind Cloudflare

Cloud Run answers only for its own `*.run.app` host and for hosts it has a domain mapping for. A proxied record for a custom host therefore does one of two things; say which before proposing the change:

1. **Keep the domain mapping:** the record points at `ghs.googlehosted.com`, Cloudflare passes the original Host, SSL mode `full`. The mapping's Google certificate renews through the same record and can fail while it is proxied; watch the mapping's status after the switch.
2. **Point at `*.run.app`:** the Host header must become the `run.app` host. An Origin rule's host header override is Enterprise only; on other plans a small Worker forwards the request with the new Host.

Either way the app now sits behind one more proxy: any setting that counts proxy hops for the client address (rate limits, `X-Forwarded-For` parsing) goes up by one, and caching stays off for app pages and live streams unless a rule says otherwise.
