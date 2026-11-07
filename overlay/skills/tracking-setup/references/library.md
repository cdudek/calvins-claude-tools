# The central tracking library

Events are never defined at the call site. Every project has one tracking library, like an i18n catalogue: one registry of every event, one typed helper that call sites use, and the only code allowed to talk to an analytics tool. This file is its shape. The rules it enforces are in `conventions.md`.

## What it owns

| Concern | How |
| --- | --- |
| The registry | every event's name, category, capture side, typed properties, owner, status, question, since-version, replacement |
| The helper | `track(events.x, props)` on the client, `trackServer(events.x, props)` on the server; the only entry points |
| Routing | category to destinations, once; marketing-name mapping and limits in the marketing adapter |
| Consent | no send before consent; per destination; hold in memory or drop, per the tracking doc |
| Privacy | per-event property allowlist; rejects emails, tokens, long strings and values outside a fixed set |
| Context | `app`, `release`, `experiment_variant` added once |
| Identity | `identify` (identify, group, alias in order) and `reset`, for every tool |
| Page views | one router hook fires `page_view` with `page_type`; the tools' automatic pageview is off |
| Tests | a memory adapter for unit and E2E tests |
| Generated files | the tracking plan doc, and optionally a sync of event definitions to product analytics |

Call sites import from the library and nothing else. Analytics SDK imports, `gtag`, `dataLayer.push` and `posthog.capture` outside the library are lint errors.

## Where it lives

| Situation | Place |
| --- | --- |
| One app | in the app: `src/lib/tracking/` (or the stack's equivalent, such as `app/tracking/` or `Sources/Tracking/`) |
| Several apps share events (web, extension, mobile, a marketing site) | one shared package: `packages/tracking` in a monorepo, or a private published package next to the shared `contracts` and `tokens` packages |

Decision rule: if two deployables would fire the same event name, the registry is shared. A shared package exports the core registry (`page_view`, `signup`, `consent_update`, identity, the shared surfaces and page types), `defineEvents` and a `createTracker` factory. Each app adds only its own events in an extension registry and creates its tracker once:

```ts
// apps/shop-web/src/tracking.ts
import { coreEvents, createTracker, defineEvents } from "@acme/tracking";

export const events = { ...coreEvents, ...defineEvents({ /* shop-only events */ }) };
export const { track, identify, reset } = createTracker({ app: "shop-web", events });
```

The registry test runs on the merged registry in every app, so an app event can never reuse a core name.

## Layout (single app)

```
src/lib/tracking/
  define.ts           types, categories, routes, defineEvents
  registry.ts         every event
  track.ts            the client helper
  server.ts           trackServer, server-side capture
  consent.ts          consent state per destination
  privacy.ts          the guard
  context.ts          app, release, experiment_variant
  identity.ts         identify, reset
  page-view.ts        the router hook that fires page_view
  adapters/
    posthog.ts        product analytics
    ga4.ts            marketing analytics, name mapping, limits
    memory.ts         tests
  index.ts            the public API: events, track, identify, reset, consent
  registry.test.ts
scripts/tracking-plan.ts      writes docs/tracking-plan.md from the registry
docs/tracking.md              the project's decisions (written by tracking-setup)
docs/tracking-plan.md         generated, never edited by hand
```

Swap the adapters for the project's tools (Amplitude, Mixpanel, a pixel); the call sites do not change.

## define.ts

```ts
export type Category =
  | "lifecycle" | "acquisition" | "meaningful_action"
  | "engagement" | "retention" | "friction";
export type Dest = "product" | "marketing";

// A property is an ID, a number, a boolean, a short label, or one of a fixed set. There is no free-text kind.
export type PropKind = "id" | "int" | "number" | "bool" | "label" | readonly string[];

export type EventDef = {
  name: string;
  category: Category | readonly Category[]; // a list only for a per-call category (cta_click)
  capture: "client" | "server";
  owner: string;
  status: "proposed" | "live" | "deprecated" | "removed";
  question: string;
  since: string;
  props: Record<string, PropKind>;
  optional?: readonly string[];
  marketingName?: string;
  replacedBy?: string;
  sunset?: string; // YYYY-MM-DD
};

export const ROUTES = {
  lifecycle: ["product", "marketing"],
  acquisition: ["product", "marketing"],
  meaningful_action: ["product", "marketing"],
  engagement: ["product"],
  retention: ["product"],
  friction: ["product"],
} as const satisfies Record<Category, readonly Dest[]>;

export const SURFACES = ["auth", "onboarding", "search", "filter", "nav", "cta", "billing", "checkout", "editor", "profile", "dashboard"] as const;
export type Surface = (typeof SURFACES)[number];

type Value<K> = K extends "int" | "number" ? number : K extends "bool" ? boolean : K extends readonly (infer U)[] ? U : string;
type Opt<E extends EventDef> = E extends { optional: readonly (infer K)[] } ? K : never;
export type PropsOf<E extends EventDef> =
  { [P in Exclude<keyof E["props"], Opt<E>>]: Value<E["props"][P]> } &
  { [P in Extract<keyof E["props"], Opt<E>>]?: Value<E["props"][P]> };

export const destinationsOf = (e: EventDef): Dest[] =>
  [...new Set([e.category].flat().flatMap((c) => ROUTES[c]))];

export const defineEvents = <const T extends Record<string, EventDef>>(events: T) => events;
```

## registry.ts

```ts
import { defineEvents } from "./define";

export const events = defineEvents({
  pageView: {
    name: "page_view", category: "lifecycle", capture: "client", marketingName: "page_view",
    owner: "web", status: "live", since: "1.0.0",
    question: "Which pages draw traffic, by type?",
    props: { page_type: ["home", "product", "category", "checkout", "auth", "other"], product_id: "id", category_id: "id" },
    optional: ["product_id", "category_id"],
  },
  checkoutStart: {
    name: "checkout_start", category: "engagement", capture: "client",
    owner: "checkout", status: "proposed", since: "1.14.0",
    question: "How many carts reach checkout?",
    props: { item_count: "int", cart_value_band: ["0-25", "25-100", "100+"] },
  },
  purchase: {
    name: "purchase", category: "meaningful_action", capture: "server", marketingName: "purchase",
    owner: "checkout", status: "proposed", since: "1.14.0",
    question: "How many checkouts become paid orders, by payment method?",
    props: { order_id: "id", order_value_band: ["0-25", "25-100", "100+"], item_count: "int", payment_method: ["card", "paypal", "invoice"], is_first_order: "bool" },
  },
  ctaClick: {
    name: "cta_click", category: ["meaningful_action", "engagement"], capture: "client",
    owner: "growth", status: "live", since: "1.2.0",
    question: "Which calls to action move people, by position?",
    props: { cta_id: "id", cta_position: ["header", "hero", "inline", "footer"] },
  },
  // A rename: the old entry stays, deprecated, until the sunset; the library dual-fires it.
  orderComplete: {
    name: "order_completed", category: "meaningful_action", capture: "server",
    owner: "checkout", status: "deprecated", since: "1.0.0", replacedBy: "purchase", sunset: "2026-12-31",
    question: "Legacy name of purchase.", props: {},
  },
});
```

The registry is data, so review it like data: one entry per event, sorted by group, and every change to it in the same PR as the call site.

## track.ts

```ts
import { adapters } from "./adapters";
import { consent } from "./consent";
import { context } from "./context";
import { ROUTES, type Category, type EventDef, type PropsOf, type Surface } from "./define";
import { guard } from "./privacy";
import { events } from "./registry";

type PerCall<E extends EventDef> = E["category"] extends readonly Category[] ? [opts: { category: E["category"][number] }] : [];

export function track<E extends EventDef & { capture: "client" }>(
  event: E,
  props: PropsOf<E> & { surface?: Surface },
  ...[opts]: PerCall<E>
): void {
  const category = (Array.isArray(event.category) ? opts?.category : event.category) as Category;
  const payload = { ...context(), ...guard(event, props) };
  for (const dest of ROUTES[category]) {
    consent.run(dest, () => adapters[dest].capture(event.name, payload, event));
    // dual-fire: a deprecated entry whose replacement is this event keeps the old name alive until its sunset
    for (const old of Object.values(events)) {
      if (old.status === "deprecated" && old.replacedBy === event.name) consent.run(dest, () => adapters[dest].capture(old.name, payload, old));
    }
  }
}
```

`trackServer` in `server.ts` has the same shape, accepts only `capture: "server"` entries, takes the `user_id` explicitly, checks the user's stored consent, and sends through the server SDKs (PostHog's node or python client, the GA4 Measurement Protocol). Never import it into client code.

## consent.ts

```ts
import type { Dest } from "./define";

type State = "unknown" | "granted" | "denied";
const state: Record<Dest, State> = { product: "unknown", marketing: "unknown" };
const held: Record<Dest, Array<() => void>> = { product: [], marketing: [] };

export const consent = {
  run(dest: Dest, send: () => void) {
    if (state[dest] === "granted") send();
    // held in memory only, never stored; drop instead if the tracking doc says so
    else if (state[dest] === "unknown" && held[dest].length < 50) held[dest].push(send);
  },
  set(dest: Dest, next: "granted" | "denied") {
    state[dest] = next;
    const pending = held[dest].splice(0);
    if (next === "granted") pending.forEach((send) => send());
  },
};
```

The consent banner calls `consent.set` for each destination its purposes map to (recorded in the tracking doc) and the library fires `consent_update`. The adapters start in their privacy mode: PostHog initialised with `persistence: "memory"` and capturing opted out until granted, GA4 with consent mode defaults set to `denied` before the tag loads. On grant they switch to their normal mode; on deny they stop and clear what they stored.

## privacy.ts

```ts
import type { EventDef } from "./define";

const EMAIL = /[^\s@]+@[^\s@]+\.[^\s@]+/;
const SECRET = /\b(eyJ[\w-]{10,}\.|sk_|phx_|ghp_|xox[abp]-)|[?&](token|code|key|session)=/i;
const CONTEXT = new Set(["surface"]);

export function guard(event: EventDef, props: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(props)) {
    const kind = event.props[key];
    const bad =
      (kind === undefined && !CONTEXT.has(key)) ||
      (Array.isArray(kind) && !kind.includes(value as string)) ||
      (typeof value === "string" && (value.length > 100 || EMAIL.test(value) || SECRET.test(value)));
    if (bad) reject(event.name, key);
    else out[key] = value;
  }
  return out;
}

// Development and tests throw, so the mistake is seen. Production drops the property and logs the event and key, never the value.
function reject(name: string, key: string) {
  if (process.env.NODE_ENV !== "production") throw new Error(`tracking: ${name}.${key} is not allowed`);
  console.warn(`tracking: dropped ${name}.${key}`);
}
```

The type system already stops most of this at compile time; the guard catches what types cannot (an email typed as a string, a value from `any`).

## identity.ts

```ts
import { adapters } from "./adapters";
import { consent } from "./consent";

export type Identity = { userId: string; accountType?: string; companyId?: string; planTier?: string; isFirstLogin?: boolean };

export function identify(user: Identity) {
  consent.run("product", () => adapters.product.identify(user));   // identify, then group, then alias on first login
  consent.run("marketing", () => adapters.marketing.identify(user)); // User-ID plus user properties
}

export function reset() {
  adapters.product.reset();
  adapters.marketing.reset();
}
```

Called once from the auth provider when the session loads, and `reset` on logout. Never from a feature.

## Adapters

```ts
export interface Adapter {
  capture(name: string, props: Record<string, unknown>, event: EventDef): void;
  identify(user: Identity): void;
  reset(): void;
}
```

- **posthog.ts** sends `name` unchanged. It turns off automatic pageview capture (`capture_pageview: false`) because the router hook fires `page_view`.
- **ga4.ts** sends `event.marketingName ?? name`, and in development asserts the GA4 limits (name 40, 25 properties, values 100). It sets `user_id` and user properties on identify.
- **memory.ts** records instead of sending:

```ts
export const sent: Array<{ dest: Dest; name: string; props: Record<string, unknown> }> = [];
export const memory = (dest: Dest): Adapter => ({
  capture: (name, props) => void sent.push({ dest, name, props }),
  identify: () => {},
  reset: () => {},
});
```

`adapters/index.ts` picks the memory adapter when the test runner sets it (for example `NODE_ENV === "test"` or `TRACKING_ADAPTER=memory`). In E2E runs, either expose `sent` on `window` behind the same flag or assert on intercepted requests to the analytics hosts.

## Tests

```ts
import { beforeEach, expect, it } from "vitest";
import { consent, events, track } from "@/lib/tracking";
import { sent } from "@/lib/tracking/adapters/memory";

beforeEach(() => void sent.splice(0));

it("sends nothing before consent, then the held event once granted", () => {
  track(events.checkoutStart, { surface: "checkout", item_count: 2, cart_value_band: "25-100" });
  expect(sent).toHaveLength(0);
  consent.set("product", "granted");
  expect(sent).toEqual([expect.objectContaining({ dest: "product", name: "checkout_start" })]);
});
```

A feature test asserts the helper was called with the right event: render, act, then `expect(sent).toContainEqual(expect.objectContaining({ name: "checkout_start" }))`.

## registry.test.ts

```ts
import { describe, expect, it } from "vitest";
import { destinationsOf } from "./define";
import { events } from "./registry";

const all = Object.values(events);
const NAME = /^[a-z][a-z0-9]*(_[a-z0-9]+)*$/;
const RESERVED_PREFIX = /^(ga_|google_|firebase_|\$)/;
const RESERVED = new Set(["app_remove", "app_update", "error", "first_open", "first_visit", "screen_view", "session_start", "user_engagement"]);
const VALUE_IN_NAME = /_(\d+\w*|v\d+|monthly|yearly|annual|weekly|daily)$/;
const current = all.filter((e) => e.status === "proposed" || e.status === "live"); // legacy names keep their old spelling until removed
const toMarketing = current.filter((e) => destinationsOf(e).includes("marketing"));

describe("tracking registry", () => {
  it.each(current)("$name follows the naming rules", (e) => {
    expect(e.name).toMatch(NAME);
    expect(e.name.length).toBeLessThanOrEqual(40);
    expect(e.name).not.toMatch(RESERVED_PREFIX);
    expect(e.name).not.toMatch(VALUE_IN_NAME);
    expect(RESERVED.has(e.name)).toBe(false);
    for (const p of Object.keys(e.props)) expect(p).toMatch(NAME);
  });

  it.each(all)("$name has an owner, a question and a since-version", (e) => {
    expect(e.owner && e.question && e.since).toBeTruthy();
  });

  it("names are unique in code and in the marketing tool", () => {
    const names = all.map((e) => e.name);
    const marketing = toMarketing.map((e) => e.marketingName ?? e.name);
    expect(new Set(names).size).toBe(names.length);
    expect(new Set(marketing).size).toBe(marketing.length);
  });

  it.each(toMarketing)("$name fits the marketing tool's limits", (e) => {
    expect(Object.keys(e.props).length + 3).toBeLessThanOrEqual(25); // + app, release, surface
    expect((e.marketingName ?? e.name).length).toBeLessThanOrEqual(40);
  });

  it.each(all.filter((e) => e.status === "deprecated"))("$name names a live replacement and a sunset", (e) => {
    const next = all.find((x) => x.name === e.replacedBy);
    expect(next && !["deprecated", "removed"].includes(next.status)).toBe(true);
    expect(e.sunset).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("keeps per-call categories rare", () => {
    expect(all.filter((e) => Array.isArray(e.category)).length).toBeLessThanOrEqual(2);
  });
});
```

## Lint rule

ESLint flat config. If the project already sets `no-restricted-syntax` or `no-restricted-imports`, merge these entries into its lists: a later config object replaces the whole rule, it does not add to it.

```js
// eslint.config.js
const viaLibrary = "Track through @/lib/tracking (see docs/tracking.md).";
export default [
  // ...the project's existing config
  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    ignores: ["src/lib/tracking/**"],
    rules: {
      "no-restricted-imports": ["error", {
        paths: ["posthog-js", "posthog-node", "react-ga4", "@next/third-parties/google"].map((name) => ({ name, message: viaLibrary })),
        patterns: [{ group: ["posthog-js/*"], message: viaLibrary }],
      }],
      "no-restricted-syntax": ["error",
        { selector: "CallExpression[callee.name='gtag']", message: viaLibrary },
        { selector: "CallExpression[callee.property.name='push'][callee.object.name='dataLayer']", message: viaLibrary },
        { selector: "CallExpression[callee.property.name='push'][callee.object.property.name='dataLayer']", message: viaLibrary },
        { selector: "CallExpression[callee.property.name='capture'][callee.object.name=/^posthog$/i]", message: viaLibrary },
        { selector: "CallExpression[callee.name=/^track(Server)?$/][arguments.0.type=/^(Literal|TemplateLiteral)$/]", message: "Pass a registry entry: track(events.x, ...)." },
        { selector: "CallExpression[callee.name=/^track(Server)?$/][arguments.0.type='Identifier']", message: "Pass a registry entry, never a variable: track(events.x, ...)." },
      ],
    },
  },
];
```

A project that prefers typed string names (`track("checkout_start", ...)` with the name typed as a registry key) records that in its tracking doc and keeps only the variable rule: the type check already rejects unknown names.

## The generated tracking plan

```ts
// scripts/tracking-plan.ts, run with: npx tsx scripts/tracking-plan.ts > docs/tracking-plan.md
import { destinationsOf } from "../src/lib/tracking/define";
import { events } from "../src/lib/tracking/registry";

const rows = Object.values(events)
  .sort((a, b) => a.name.localeCompare(b.name))
  .map((e) => `| \`${e.name}\` | ${[e.category].flat().join(", ")} | ${destinationsOf(e).join(", ")} | ${e.capture} | ${e.status}${e.replacedBy ? ` (use \`${e.replacedBy}\`)` : ""} | ${e.owner} | ${e.question} | ${Object.keys(e.props).join(", ")} | ${e.since} |`);

console.log([
  "# Tracking plan", "", "Generated from the registry by scripts/tracking-plan.ts. Do not edit by hand.", "",
  "| Event | Category | Goes to | Captured | Status | Owner | Question | Properties | Since |",
  "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
  ...rows,
].join("\n"));
```

Add a package script (`tracking:plan`) and a CI step that regenerates and fails on a diff (`git diff --exit-code docs/tracking-plan.md`).

Optional: a sync script pushes each entry's question, owner and status to the product-analytics tool's event definitions (description, tags, verified for `live`), through `posthog-manage`. Run it by hand after a release, never from CI with a personal key.

## Other stacks

- **Python:** `tracking/registry.py` with one frozen dataclass or pydantic model per event's properties and an `Event` record per entry; `track(EVENTS.checkout_start, CheckoutStart(item_count=2, ...))`; ruff's `flake8-tidy-imports.banned-api` bans `posthog` outside `tracking/` (allow it there with `per-file-ignores`).
- **Ruby:** a frozen hash registry and `Tracking.track(:checkout_start, ...)` that raises on unknown events or keys; a custom RuboCop cop bans `PostHog::Client` outside `app/lib/tracking`.
- **Swift / Kotlin:** an enum of events with associated values (or a sealed class), one `Tracker` protocol with a real and a memory implementation, and a lint rule (SwiftLint custom rule, detekt `ForbiddenImport`) on the SDK import.
- **Go:** a `tracking` package with one typed struct per event and a `Track(ctx, ev)` that reads the registry; `depguard` bans the SDK elsewhere.
