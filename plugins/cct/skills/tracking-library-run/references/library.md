# The central tracking library

Events are never defined at the call site. Every project has one tracking library, like an i18n catalogue: one registry of every event, one typed helper that call sites use, and the only code allowed to talk to an analytics tool. This file is its shape, in TypeScript; the rules it enforces are in `conventions.md`. Every code block below compiles under `tsc --strict` and its tests pass as written; copy them, then change the project's values.

## What it guarantees, and how

| Guarantee | Enforced by |
| --- | --- |
| Only registry events are sent | `track` takes a registry key and reads the definition from its own registry, so a forged or foreign definition cannot be passed; only `proposed` and `live` keys type-check; a runtime check refuses anything else (a value from `any`); the lint rule bans SDK calls, SDK imports (static, dynamic, `require`) and non-key first arguments outside the library |
| No private data | the privacy guard checks every property's kind (ID, number, boolean, short label, fixed value, items), rejects objects, arrays, `null`, emails, tokens and unknown keys, and requires the required ones; identity and context values go through the same checks |
| Nothing leaves the browser before consent | no SDK is initialised and no tag is loaded until its destination is granted (`start`); before that, events are held in memory or dropped; deny or withdrawal calls `stop` |
| Logout ends the person | `reset` forgets the current identity and drops every held event, so nothing queued before logout is sent as anyone |
| A rename keeps dashboards and does not double-count | the old name is re-sent to product analytics only, in its own validated shape, until its sunset; the marketing tool only ever gets the new name |
| GA4 accepts what is sent | the registry test validates each marketing event as GA4 receives it (name, reserved names, parameter count and names, value lengths, user properties, the custom-dimension budget); the GA4 adapter re-checks in development |
| Server events stitch and count once | `trackServer` takes the user ID, the stored consent, the GA4 client and session IDs and an idempotency key |

Call sites import from the library's `index.ts` and nothing else.

## Where it lives

| Situation | Place |
| --- | --- |
| One app | in the app: `src/lib/tracking/` (or the stack's equivalent) |
| Several apps share events (web, extension, mobile, a marketing site) | one shared package: `packages/tracking` in a monorepo, or a private published package |

Decision rule: if two deployables would fire the same event name, the registry is shared. The package exports the core registry (`page_view`, `consent_update`, `signup`, the shared values), `defineEvents`, `extendEvents` and `createTracker`. Each app adds its own events with `extendEvents`, which throws on a reused key or name before merging, and creates its tracker once:

```ts
// apps/shop-web/src/tracking.ts (sketch: the package's index.ts, below, with the merged registry)
import { coreEvents, createTracker, defineEvents, extendEvents } from "@acme/tracking";

const registry = extendEvents(coreEvents, defineEvents({ /* shop-only events */ }));
export const { events, track, identify, reset, consent } = createTracker({ app: "shop-web", registry, /* ... */ });
```

The registry test and the plan generator run on the merged registry in every app. The lint rule's `ignores` path points at the package, and the deep-import ban names the package (`@acme/tracking/*`).

## Layout

```
src/lib/tracking/
  define.ts            types, routes, the project's values, defineEvents, extendEvents
  registry.ts          every event
  privacy.ts           the guard
  tracker.ts           createTracker: consent, identity, routing, renames
  server.ts            createServerTracker and the server adapters (server code only)
  adapters/
    ga4-rules.ts       GA4's names, reserved words and limits, as data
    posthog.ts         product analytics in the browser
    ga4.ts             marketing analytics in the browser
    memory.ts          tests
    index.ts           picks the real or the memory adapters
  index.ts             the public API: events, track, identify, reset, consent, setExperiment
  tracker.test.ts      consent, identity, privacy, renames
  types.test.ts        what must not compile
  registry.test.ts     names, fields, GA4 limits, lifecycle
scripts/tracking-plan.ts       writes or checks docs/tracking-plan.md
docs/tracking.md               the project's decisions (written by tracking-library-run)
docs/tracking-plan.md          generated, never edited by hand
```

Other tools (Amplitude, Mixpanel, a pixel) are one more adapter; call sites do not change.

## define.ts

```ts
// src/lib/tracking/define.ts
export type Category = "lifecycle" | "acquisition" | "meaningful_action" | "engagement" | "retention" | "friction";
export type Dest = "product" | "marketing";
export type Status = "proposed" | "live" | "deprecated" | "removed";
export type Item = { item_id: string; price: number; quantity: number };

// An ID, a number, a boolean, a short label, one of a fixed set, or purchased items. There is no free-text kind.
export type PropKind = "id" | "int" | "number" | "bool" | "label" | "items" | readonly string[];
type Props = Readonly<Record<string, unknown>>;

export type EventDef = {
  name: string;
  category: Category | readonly Category[]; // a list only for the one per-call-category event (cta_click)
  capture: "client" | "server";
  owner: string;
  status: Status;
  question: string;          // the plain-language question it answers
  firedWhen: string;         // the trigger, in words: "the payment webhook confirms the charge"
  apps?: readonly string[];  // the apps that fire it; omitted means every app on this registry
  since: string;
  props: Readonly<Record<string, PropKind>>;
  optional?: readonly string[];
  needs?: { by: string; ids: Readonly<Record<string, readonly string[]>> }; // IDs required per value (page_view)
  marketingName?: string;
  marketingParams?: (props: Props) => Record<string, unknown>; // GA4 recommended parameters (purchase)
  replacedBy?: string;       // deprecated only: the new event's name
  deprecatedOn?: string;     // YYYY-MM-DD
  sunset?: string;           // YYYY-MM-DD, 30 days or more after deprecatedOn
  toLegacy?: (props: Props) => Record<string, unknown>; // deprecated only: the new props in the old shape
};

export const ROUTES = {
  lifecycle: ["product", "marketing"],
  acquisition: ["product", "marketing"],
  meaningful_action: ["product", "marketing"],
  engagement: ["product"],
  retention: ["product"],
  friction: ["product"],
} as const satisfies Record<Category, readonly Dest[]>;

// The project's values. A new one is a one-line change here, in the PR that first uses it.
export const SURFACES = ["auth", "onboarding", "search", "filter", "nav", "cta", "billing", "checkout", "editor", "profile", "dashboard"] as const;
export const ACCOUNT_TYPES = ["buyer", "seller", "admin"] as const;
export const PLAN_TIERS = ["free", "pro", "team"] as const;
export type Surface = (typeof SURFACES)[number];
export type Identity = { userId: string; accountType?: (typeof ACCOUNT_TYPES)[number]; companyId?: string; planTier?: (typeof PLAN_TIERS)[number] };

type Value<K> = K extends "int" | "number" ? number : K extends "bool" ? boolean : K extends "items" ? readonly Item[]
  : K extends readonly (infer U)[] ? U : string;
type Opt<E> = E extends { optional: readonly (infer K)[] } ? K : never;
type By<E> = E extends { needs: { by: infer B } } ? B : never;
type Needed<E> = E extends { needs: { ids: infer M } } ? { [V in keyof M]: M[V] extends readonly (infer X)[] ? X : never }[keyof M] : never;
type Cat<E extends EventDef> = E["category"] extends readonly (infer C)[] ? C : E["category"];
type Disc<E extends EventDef> = E extends { needs: { by: infer B extends string; ids: infer M } }
  ? { [V in Value<E["props"][B]> & string]: { [P in B]: V } & {
      [K in V extends keyof M ? (M[V] extends readonly (infer X extends string)[] ? X : never) : never]: Value<E["props"][K]> } }[Value<E["props"][B]> & string]
  : unknown;
type SurfaceArg<E extends EventDef> = E["capture"] extends "server" ? unknown
  : Cat<E> extends "lifecycle" ? { surface?: Surface } : { surface: Surface };

export type PropsOf<E extends EventDef> =
  { [P in Exclude<keyof E["props"], Opt<E> | By<E> | Needed<E>>]: Value<E["props"][P]> } &
  { [P in Extract<keyof E["props"], Opt<E>>]?: Value<E["props"][P]> } &
  Disc<E> & SurfaceArg<E>;

export type Registry = Readonly<Record<string, EventDef>>;
// Only current entries can be called: deprecated ones are re-sent by the library, removed ones are tombstones.
export type Callable<R extends Registry, C extends EventDef["capture"]> =
  { [K in keyof R]: R[K] extends { status: "proposed" | "live"; capture: C } ? K : never }[keyof R] & string;
export type PerCall<E extends EventDef> = E["category"] extends readonly Category[] ? [opts: { category: E["category"][number] }] : [];

export const destinationsOf = (e: EventDef): Dest[] => [...new Set([e.category].flat().flatMap((c) => ROUTES[c]))];
export const defineEvents = <const T extends Record<string, EventDef>>(events: T) => events;

// A shared core plus an app's own events. Throws before merging, so an app can never overwrite a core entry.
export function extendEvents<const A extends Registry, const B extends Registry>(core: A, own: B): A & B {
  const names = new Set(Object.values(core).map((e) => e.name));
  for (const [key, e] of Object.entries(own)) {
    if (key in core || names.has(e.name)) throw new Error(`tracking: ${key} (${e.name}) is already registered`);
    names.add(e.name);
  }
  return { ...core, ...own };
}
```

## registry.ts

```ts
// src/lib/tracking/registry.ts
import { defineEvents } from "./define";

const BANDS = ["0-25", "25-100", "100+"] as const;

export const registry = defineEvents({
  pageView: {
    name: "page_view", category: "lifecycle", capture: "client", marketingName: "page_view",
    owner: "web", status: "live", since: "1.0.0",
    question: "Which pages draw traffic, by type?", firedWhen: "the router finishes a navigation (library hook)",
    props: { page_type: ["home", "product", "category", "checkout", "auth", "other"], product_id: "id", category_id: "id" },
    needs: { by: "page_type", ids: { product: ["product_id"], category: ["category_id"] } },
  },
  consentUpdate: {
    name: "consent_update", category: "lifecycle", capture: "client",
    owner: "web", status: "live", since: "1.0.0",
    question: "How many visitors grant or deny each kind of tracking?", firedWhen: "the consent banner saves a choice (library)",
    props: { destination: ["product", "marketing"], consent_state: ["granted", "denied"] },
  },
  checkoutStart: {
    name: "checkout_start", category: "engagement", capture: "client",
    owner: "checkout", status: "proposed", since: "1.14.0",
    question: "How many carts reach checkout?", firedWhen: "the checkout page opens with at least one item",
    props: { item_count: "int", cart_value_band: BANDS },
  },
  purchase: {
    name: "purchase", category: "meaningful_action", capture: "server",
    owner: "checkout", status: "proposed", since: "1.14.0",
    question: "How many checkouts become paid orders, and how much revenue, by payment method?",
    firedWhen: "the payment webhook confirms the charge",
    props: { order_id: "id", value: "number", currency: ["EUR", "USD"], items: "items", payment_method: ["card", "paypal", "invoice"], is_first_order: "bool" },
    marketingName: "purchase",
    marketingParams: (p) => ({ transaction_id: p.order_id, value: p.value, currency: p.currency, items: p.items }),
  },
  ctaClick: {
    name: "cta_click", category: ["meaningful_action", "engagement"], capture: "client",
    owner: "growth", status: "live", since: "1.2.0",
    question: "Which calls to action move people, by position?", firedWhen: "a tracked call to action is clicked",
    props: { cta_id: "id", cta_position: ["header", "hero", "inline", "footer"] },
  },
  // A rename: the old entry stays until its sunset; the library re-sends it to product analytics only, in its own shape.
  orderComplete: {
    name: "order_completed", category: "meaningful_action", capture: "server",
    owner: "checkout", status: "deprecated", since: "1.0.0",
    replacedBy: "purchase", deprecatedOn: "2026-11-01", sunset: "2026-12-31",
    question: "Legacy name of purchase.", firedWhen: "with purchase, until the sunset",
    props: { order_id: "id", order_total_band: BANDS },
    toLegacy: (p) => ({ order_id: p.order_id, order_total_band: Number(p.value) < 25 ? "0-25" : Number(p.value) < 100 ? "25-100" : "100+" }),
  },
});
```

The registry is data: one entry per event, grouped by area, changed in the same PR as its call site. A removed entry stays as a tombstone (`status: "removed"`) so the name is never reused.

## privacy.ts

```ts
// src/lib/tracking/privacy.ts
import { ACCOUNT_TYPES, PLAN_TIERS, SURFACES, type EventDef, type Identity, type PropKind } from "./define";

export class TrackingError extends Error {
  constructor(event: string, key: string) {
    super(`tracking: ${event}.${key} is not allowed`); // names the key, never the value
  }
}

const EMAIL = /[^\s@]+@[^\s@]+\.[^\s@]+/;
const SECRET = /\b(eyJ[\w-]{10,}\.|sk_|phx_|ghp_|xox[abp]-)|[?&#](token|code|key|session|access_token)=/i;
const ID = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;
const has = (o: object, k: string) => Object.prototype.hasOwnProperty.call(o, k);

export const isLabel = (v: unknown): v is string =>
  typeof v === "string" && v.length > 0 && v.length <= 100 && !EMAIL.test(v) && !SECRET.test(v);
const isId = (v: unknown) => (typeof v === "string" && ID.test(v) && !SECRET.test(v)) || Number.isSafeInteger(v);
const isItem = (v: unknown) => {
  if (v === null || typeof v !== "object" || Array.isArray(v)) return false;
  const i = v as Record<string, unknown>;
  return Object.keys(i).every((k) => ["item_id", "price", "quantity"].includes(k)) && typeof i.item_id === "string" && isId(i.item_id)
    && typeof i.price === "number" && Number.isFinite(i.price) && Number.isSafeInteger(i.quantity) && (i.quantity as number) > 0;
};

export function valid(kind: PropKind, v: unknown): boolean {
  if (typeof kind !== "string") return typeof v === "string" && kind.includes(v);
  switch (kind) {
    case "id": return isId(v);
    case "int": return Number.isSafeInteger(v);
    case "number": return typeof v === "number" && Number.isFinite(v);
    case "bool": return typeof v === "boolean";
    case "label": return isLabel(v);
    case "items": return Array.isArray(v) && v.length > 0 && v.length <= 200 && v.every(isItem);
  }
}

// A fresh, checked copy of the props: every key known, every value of its kind, every required key present.
export function guard(e: EventDef, props: unknown, surface: "required" | "optional" | "none"): Record<string, unknown> {
  if (props === null || typeof props !== "object" || Array.isArray(props)) throw new TrackingError(e.name, "(props)");
  const p = props as Record<string, unknown>;
  const needed = e.needs ? Object.values(e.needs.ids).flat() : [];
  const forThis = e.needs ? (e.needs.ids[String(p[e.needs.by])] ?? []) : [];
  const allowed = (k: string) => !needed.includes(k) || forThis.includes(k);
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(p)) {
    const ok = key === "surface"
      ? surface !== "none" && SURFACES.some((s) => s === value)
      : has(e.props, key) && allowed(key) && valid(e.props[key]!, value);
    if (!ok) throw new TrackingError(e.name, key);
    out[key] = Array.isArray(value) ? value.map((i: object) => ({ ...i })) : value;
  }
  for (const key of Object.keys(e.props)) {
    if (!e.optional?.includes(key) && allowed(key) && !has(out, key)) throw new TrackingError(e.name, key);
  }
  if (surface === "required" && !has(out, "surface")) throw new TrackingError(e.name, "surface");
  return out;
}

export function guardIdentity(u: unknown): Identity {
  if (u === null || typeof u !== "object") throw new TrackingError("identify", "(identity)");
  const i = u as Record<string, unknown>;
  const checks: Record<string, (v: unknown) => boolean> = {
    userId: (v) => typeof v === "string" && isId(v),
    accountType: (v) => v === undefined || ACCOUNT_TYPES.some((t) => t === v),
    companyId: (v) => v === undefined || (typeof v === "string" && isId(v)),
    planTier: (v) => v === undefined || PLAN_TIERS.some((t) => t === v),
  };
  for (const key of new Set([...Object.keys(i), ...Object.keys(checks)])) {
    if (!checks[key]?.(i[key])) throw new TrackingError("identify", key);
  }
  return { ...(i as Identity) };
}
```

An ID may not contain `@`, so an email never passes as one. Development and tests throw (`strict`); production drops the whole event and logs the event name and key, never the value.

## tracker.ts

```ts
// src/lib/tracking/tracker.ts
import { ROUTES, type Callable, type Category, type Dest, type EventDef, type Identity, type PerCall, type PropsOf, type Registry } from "./define";
import { guard, guardIdentity, isLabel, TrackingError } from "./privacy";

export interface Adapter {
  start(): void;   // load and initialise the SDK; called on each grant, never before the first one
  stop(): void;    // opt out and clear what the SDK stored; called on deny or withdrawal
  capture(event: EventDef, props: Record<string, unknown>, at: Date): void;
  identify(user: Identity): void; // the current person and group; absent fields are cleared
  reset(): void;   // forget the person
}
export type Send = { dest: Dest; event: EventDef; props: Record<string, unknown> };
const DESTS = ["product", "marketing"] as const;

// Shared by the client and the server tracker: checks, routes and adds the legacy name of a renamed event.
export function prepare(registry: Registry, key: string, capture: EventDef["capture"], props: unknown,
  category: Category | undefined, context: Record<string, unknown>, today: string): Send[] {
  const e = Object.prototype.hasOwnProperty.call(registry, key) ? registry[key] : undefined;
  if (!e || e.capture !== capture || (e.status !== "proposed" && e.status !== "live")) throw new TrackingError(String(key), "(not a callable registry key)");
  const cat = Array.isArray(e.category) ? category : (e.category as Category);
  if (!cat || (Array.isArray(e.category) && !e.category.includes(cat))) throw new TrackingError(e.name, "(category)");
  const surface = capture === "server" ? "optional" : cat === "lifecycle" ? "optional" : "required";
  const checked = guard(e, props, surface);
  const sends: Send[] = ROUTES[cat].map((dest) => ({ dest, event: e, props: { ...checked, ...context } }));
  for (const old of Object.values(registry)) {
    if (old.status !== "deprecated" || old.replacedBy !== e.name || (old.sunset ?? "") < today) continue;
    // product analytics only: the marketing tool gets the new name alone, so no conversion is counted twice
    sends.push({ dest: "product", event: old, props: { ...guard(old, old.toLegacy?.(checked) ?? {}, "none"), ...context } });
  }
  return sends;
}

type Options<R extends Registry> = {
  app: string; release?: string; registry: R; adapters: Record<Dest, Adapter>;
  beforeConsent: "hold" | "drop"; // the tracking doc's choice
  strict: boolean;                 // true in development and tests: a rejected event throws
  now?: () => Date;
};

export function createTracker<const R extends Registry>(o: Options<R>) {
  if (!isLabel(o.app) || (o.release !== undefined && !isLabel(o.release))) throw new TrackingError("context", "app");
  const now = o.now ?? (() => new Date());
  const state: Record<Dest, "unknown" | "granted" | "denied"> = { product: "unknown", marketing: "unknown" };
  let held: Array<{ dest: Dest; run: () => void }> = [];
  let user: Identity | undefined;
  let variant: string | undefined;

  const reject = (err: unknown) => {
    if (o.strict || !(err instanceof TrackingError)) throw err;
    console.warn(err.message);
  };
  const deliver = (sends: Send[]) => {
    const at = now();
    for (const { dest, event, props } of sends) {
      const p = dest === "product" && variant ? { ...props, experiment_variant: variant } : props;
      const run = () => o.adapters[dest].capture(event, p, at);
      if (state[dest] === "granted") run();
      else if (state[dest] === "unknown" && o.beforeConsent === "hold" && held.filter((h) => h.dest === dest).length < 50) held.push({ dest, run });
    }
  };
  const emit = (key: string, props: unknown, category?: Category) => {
    const context = { app: o.app, ...(o.release ? { release: o.release } : {}) };
    deliver(prepare(o.registry, key, "client", props, category, context, now().toISOString().slice(0, 10)));
  };

  function track<K extends Callable<R, "client">>(key: K, props: PropsOf<R[K]>, ...[opts]: PerCall<R[K]>): void {
    try { emit(key, props, opts?.category); } catch (err) { reject(err); }
  }

  function identify(next: Identity): void {
    try {
      const u = guardIdentity(next);
      if (user && user.userId !== u.userId) reset(); // account switch: nothing of the old account carries over
      user = u;
      for (const d of DESTS) if (state[d] === "granted") o.adapters[d].identify(u);
    } catch (err) { reject(err); }
  }

  function reset(): void {
    user = undefined;
    held = []; // held events belong to the person who just left
    for (const d of DESTS) if (state[d] === "granted") o.adapters[d].reset();
  }

  const consent = {
    get: (dest: Dest) => state[dest],
    set(dest: Dest, next: "granted" | "denied"): void {
      const was = state[dest];
      if (was === next) return;
      state[dest] = next;
      const mine = held.filter((h) => h.dest === dest);
      held = held.filter((h) => h.dest !== dest);
      if (next === "granted") {
        o.adapters[dest].start();
        if (user) o.adapters[dest].identify(user);
        for (const h of mine) if (state[dest] === "granted") h.run();
      } else if (was === "granted") o.adapters[dest].stop();
      const entry = Object.keys(o.registry).find((k) => o.registry[k]!.name === "consent_update");
      if (entry) try { emit(entry, { destination: dest, consent_state: next }); } catch (err) { reject(err); }
    },
  };

  function setExperiment(v: string | undefined): void {
    if (v !== undefined && !isLabel(v)) return reject(new TrackingError("context", "experiment_variant"));
    variant = v;
  }

  const events = Object.fromEntries(Object.keys(o.registry).map((k) => [k, k])) as { readonly [K in keyof R & string]: K };
  return { events, track, identify, reset, consent, setExperiment };
}
```

`identify` is the "current identity" call: run it when the session loads, right after login, and again whenever the role, plan or company changes; it clears fields that are now absent. A different user ID resets first. Identity properties describe the person or group now; when an analysis needs the value at the time of an event (the plan when they bought), that event carries it as its own property.

## Adapters

The SDKs load only inside `start`. This is the strict reading of "nothing before consent", which Google calls basic consent mode: no tag and no request before the visitor answers. Both vendors offer a looser mode (PostHog loaded with `opt_out_capturing_by_default: true`, GA4 advanced consent mode with cookieless pings while denied); a project that wants it records that choice in its tracking doc, and then "nothing leaves the browser" no longer holds.

```ts
// src/lib/tracking/adapters/posthog.ts
import posthog from "posthog-js";
import type { Adapter } from "../tracker";

export function posthogAdapter(cfg: { key: string; host: string; groupType: string }): Adapter {
  let loaded = false;
  return {
    start() {
      if (loaded) return void posthog.opt_in_capturing();
      posthog.init(cfg.key, {
        api_host: cfg.host,
        capture_pageview: false,             // the router hook sends page_view
        capture_pageleave: false,
        person_profiles: "identified_only",  // anonymous visitors create no person profile
      });
      loaded = true;
    },
    stop() {
      if (!loaded) return;
      posthog.opt_out_capturing();
      posthog.reset();
    },
    capture: (event, props, at) => void posthog.capture(event.name, props, { timestamp: at }),
    identify(u) {
      posthog.identify(u.userId, u.accountType ? { account_type: u.accountType } : {});
      if (u.companyId) posthog.group(cfg.groupType, u.companyId, u.planTier ? { plan_tier: u.planTier } : {});
      else posthog.resetGroups();
    },
    reset: () => posthog.reset(),
  };
}
```

```ts
// src/lib/tracking/adapters/ga4.ts
import type { Adapter } from "../tracker";
import { TrackingError } from "../privacy";
import { ga4Payload, ga4Problems, ga4UserProblems } from "./ga4-rules";

declare global { interface Window { dataLayer: unknown[] } }
type Grant = "analytics_storage" | "ad_storage" | "ad_user_data" | "ad_personalization";
const ALL: readonly Grant[] = ["analytics_storage", "ad_storage", "ad_user_data", "ad_personalization"];

// grants: the Google consent types the marketing destination stands for, per the tracking doc's purpose map
export function ga4Adapter(cfg: { measurementId: string; grants: readonly Grant[]; dev: boolean }): Adapter {
  let loaded = false;
  function gtag(..._args: unknown[]) { window.dataLayer.push(arguments); } // gtag needs the arguments object
  const consent = (granted: readonly Grant[]) => Object.fromEntries(ALL.map((g) => [g, granted.includes(g) ? "granted" : "denied"]));
  return {
    start() {
      (window as unknown as Record<string, boolean>)[`ga-disable-${cfg.measurementId}`] = false;
      if (loaded) return gtag("consent", "update", consent(cfg.grants));
      window.dataLayer = window.dataLayer || [];
      gtag("consent", "default", consent([]));
      gtag("consent", "update", consent(cfg.grants));
      gtag("js", new Date());
      gtag("config", cfg.measurementId, { send_page_view: false }); // the router hook sends page_view
      const s = document.createElement("script");
      s.async = true;
      s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(cfg.measurementId)}`;
      document.head.appendChild(s);
      loaded = true;
    },
    stop() {
      if (!loaded) return;
      gtag("consent", "update", consent([]));
      (window as unknown as Record<string, boolean>)[`ga-disable-${cfg.measurementId}`] = true;
    },
    capture(event, props) {
      const { name, params } = ga4Payload(event, props);
      if (cfg.dev && ga4Problems(name, params).length) throw new TrackingError(name, ga4Problems(name, params).join("; "));
      gtag("event", name, params);
    },
    identify(u) {
      const user = { account_type: u.accountType ?? null, company_id: u.companyId ?? null, plan_tier: u.planTier ?? null };
      if (ga4UserProblems(user).length) throw new TrackingError("identify", ga4UserProblems(user).join("; "));
      gtag("set", { user_id: u.userId });
      gtag("set", "user_properties", user);
    },
    reset() {
      gtag("set", { user_id: null }); // GA4 wants null on logout, never "" or "null"
      gtag("set", "user_properties", { account_type: null, company_id: null, plan_tier: null });
    },
  };
}
```

```ts
// src/lib/tracking/adapters/ga4-rules.ts
import type { EventDef } from "../define";

// GA4's collection limits and reserved names (see the sources in conventions.md, Hard limits).
const NAME = /^[A-Za-z][A-Za-z0-9_]{0,39}$/;
const RESERVED_PREFIX = /^(_|firebase_|ga_|google_|gtag\.)/;
const RESERVED_EVENTS = new Set(["ad_activeview", "ad_click", "ad_exposure", "ad_impression", "ad_query", "ad_reward", "adunit_exposure",
  "app_clear_data", "app_exception", "app_install", "app_remove", "app_store_refund", "app_store_subscription_cancel",
  "app_store_subscription_renew", "app_update", "app_upgrade", "click", "dynamic_link_app_open", "dynamic_link_app_update",
  "dynamic_link_first_open", "error", "file_download", "firebase_campaign", "first_open", "first_visit", "form_start", "form_submit",
  "in_app_purchase", "notification_dismiss", "notification_foreground", "notification_open", "notification_receive",
  "notification_send", "os_update", "page_view", "scroll", "session_start", "user_engagement", "video_progress", "video_start",
  "view_complete", "view_search_results"]); // Google's list as published; it says the list may grow
const MANUAL = new Set(["page_view"]); // reserved, but sent by hand with automatic page views off
const RESERVED_PARAMS = new Set(["cid", "currency", "customer_id", "customerid", "dclid", "gclid", "session_id", "sessionid",
  "sfmc_id", "sid", "srsltid", "uid", "user_id", "userid"]);
const WITH_CURRENCY = new Set(["add_payment_info", "add_shipping_info", "add_to_cart", "add_to_wishlist", "begin_checkout",
  "generate_lead", "purchase", "refund", "remove_from_cart", "view_cart", "view_item"]);
const RESERVED_USER = new Set(["cid", "customer_id", "customerid", "first_open_after_install", "first_open_time", "first_visit_time",
  "google_allow_ad_personalization_signals", "last_advertising_id_reset", "last_deep_link_referrer", "last_gclid",
  "lifetime_user_engagement", "non_personalized_ads", "session_id", "session_number", "sessionid", "sfmc_id", "sid", "uid", "user_id", "userid"]);
const LONG: Record<string, number> = { page_title: 300, page_referrer: 420, page_location: 1000 };
// Predefined parameters need no custom dimension.
export const PREDEFINED = new Set(["page_location", "page_referrer", "page_title", "currency", "value", "transaction_id", "items", "method", "search_term", "content_type"]);

export function ga4Payload(e: EventDef, props: Record<string, unknown>) {
  return { name: e.marketingName ?? e.name, params: { ...props, ...e.marketingParams?.(props) } };
}

export function ga4Problems(name: string, params: Record<string, unknown>): string[] {
  const out: string[] = [];
  if (!NAME.test(name) || RESERVED_PREFIX.test(name) || (RESERVED_EVENTS.has(name) && !MANUAL.has(name))) out.push(`event name ${name}`);
  const keys = Object.keys(params);
  if (keys.length > 25) out.push(`${keys.length} parameters`);
  for (const k of keys) {
    if (!NAME.test(k) || RESERVED_PREFIX.test(k) || (RESERVED_PARAMS.has(k) && !(k === "currency" && WITH_CURRENCY.has(name)))) out.push(`parameter ${k}`);
    const v = params[k];
    if (typeof v === "string" && v.length > (LONG[k] ?? 100)) out.push(`${k} longer than ${LONG[k] ?? 100}`);
  }
  return out;
}

export function ga4UserProblems(user: Record<string, unknown>): string[] {
  const out: string[] = [];
  if (Object.keys(user).length > 25) out.push("more than 25 user properties");
  for (const [k, v] of Object.entries(user)) {
    if (k.length > 24 || !NAME.test(k) || /^(_|firebase_|ga_|google_)/.test(k) || RESERVED_USER.has(k)) out.push(`user property ${k}`);
    if (typeof v === "string" && v.length > 36) out.push(`${k} longer than 36`);
  }
  return out;
}
```

```ts
// src/lib/tracking/adapters/memory.ts
import type { Dest, Identity } from "../define";
import type { Adapter } from "../tracker";
import { ga4Payload } from "./ga4-rules";

export type Op = { dest: Dest; op: "start" | "stop" | "capture" | "identify" | "reset"; name?: string; props?: Record<string, unknown>; user?: Identity };

// Records every operation, with a copy of the payload as the tool would receive it.
export const memory = (dest: Dest, log: Op[]): Adapter => ({
  start: () => void log.push({ dest, op: "start" }),
  stop: () => void log.push({ dest, op: "stop" }),
  capture(event, props) {
    const sent = dest === "marketing" ? ga4Payload(event, props) : { name: event.name, params: props };
    log.push({ dest, op: "capture", name: sent.name, props: structuredClone(sent.params) });
  },
  identify: (user) => void log.push({ dest, op: "identify", user: { ...user } }),
  reset: () => void log.push({ dest, op: "reset" }),
});
```

```ts
// src/lib/tracking/adapters/index.ts
import { ga4Adapter } from "./ga4";
import { memory, type Op } from "./memory";
import { posthogAdapter } from "./posthog";

export const inTest = process.env.NODE_ENV === "test" || process.env.TRACKING_ADAPTER === "memory";
export const testLog: Op[] = []; // E2E runs expose it on window behind the same flag
export const adapters = inTest
  ? { product: memory("product", testLog), marketing: memory("marketing", testLog) }
  : {
      product: posthogAdapter({ key: process.env.NEXT_PUBLIC_POSTHOG_KEY ?? "", host: process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "", groupType: "company" }),
      marketing: ga4Adapter({ measurementId: process.env.NEXT_PUBLIC_GA4_MEASUREMENT_ID ?? "", grants: ["analytics_storage", "ad_storage", "ad_user_data", "ad_personalization"], dev: process.env.NODE_ENV !== "production" }),
    };
```

## index.ts

```ts
// src/lib/tracking/index.ts
import { adapters, inTest, testLog } from "./adapters";
import { registry } from "./registry";
import { createTracker } from "./tracker";

export const { events, track, identify, reset, consent, setExperiment } = createTracker({
  app: "shop-web",
  release: process.env.NEXT_PUBLIC_RELEASE || undefined,
  registry,
  adapters,
  beforeConsent: "hold",
  strict: process.env.NODE_ENV !== "production",
});

// Feature tests run with consent granted, set here once and never changed by them; consent itself is tested on fresh trackers.
if (inTest) {
  consent.set("product", "granted");
  consent.set("marketing", "granted");
  testLog.length = 0;
}
export { testLog };
```

Wire it once: the auth provider calls `identify` when the session loads and after login, logout calls `reset`, the consent banner calls `consent.set` for each destination its purposes map to, and one router hook calls `track(events.pageView, ...)` after each navigation (Next.js: a client component in the root layout using `usePathname` and `useEffect`; React Router: `useLocation`; Vue Router: `router.afterEach`). Nothing else calls `identify`, `reset` or `consent`.

## server.ts

A server event (revenue, a webhook, a job) goes through `trackServer`. Keep this file out of client bundles (Next.js: `import "server-only"` at its top).

```ts
// src/lib/tracking/server.ts
import { createHash } from "node:crypto";
import type { PostHog } from "posthog-node";
import type { Callable, Dest, EventDef, PerCall, PropsOf, Registry } from "./define";
import { ga4Payload, ga4Problems } from "./adapters/ga4-rules";
import { guardIdentity, isLabel, TrackingError } from "./privacy";
import { prepare } from "./tracker";

export type ServerContext = {
  userId: string;                                 // the same opaque ID identify uses
  consent: Record<Dest, boolean>;                 // the browser's choice, stored with the user or the order
  ga?: { clientId: string; sessionId?: string };  // from the _ga and _ga_<id> cookies of the request that started it, stored with the order
  occurredAt: Date;                               // when it happened, not when it is sent; also the retry-safe timestamp
  idempotencyKey: string;                         // stable per business event, such as `purchase:<order_id>`
};
export interface ServerAdapter { send(event: EventDef, props: Record<string, unknown>, ctx: ServerContext): Promise<void> }

export function createServerTracker<const R extends Registry>(o: { app: string; release?: string; registry: R; adapters: Record<Dest, ServerAdapter>; strict: boolean }) {
  async function trackServer<K extends Callable<R, "server">>(ctx: ServerContext, key: K, props: PropsOf<R[K]>, ...[opts]: PerCall<R[K]>): Promise<void> {
    try {
      guardIdentity({ userId: ctx.userId });
      if (!isLabel(ctx.idempotencyKey)) throw new TrackingError(key, "idempotencyKey");
      const context = { app: o.app, ...(o.release ? { release: o.release } : {}) };
      const sends = prepare(o.registry, key, "server", props, opts?.category, context, ctx.occurredAt.toISOString().slice(0, 10));
      await Promise.all(sends.filter((s) => ctx.consent[s.dest]).map((s) => o.adapters[s.dest].send(s.event, s.props, ctx)));
    } catch (err) {
      if (o.strict || !(err instanceof TrackingError)) throw err;
      console.warn(err.message);
    }
  }
  return { events: Object.fromEntries(Object.keys(o.registry).map((k) => [k, k])) as { readonly [K in keyof R & string]: K }, trackServer };
}

// The same key always gives the same UUID, so PostHog can drop a retried event.
const uuidOf = (key: string) => {
  const h = createHash("sha256").update(key).digest("hex");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-8${h.slice(13, 16)}-${((parseInt(h[16]!, 16) & 3) | 8).toString(16)}${h.slice(17, 20)}-${h.slice(20, 32)}`;
};

export const posthogServer = (client: PostHog): ServerAdapter => ({
  async send(event, props, ctx) {
    client.capture({ distinctId: ctx.userId, event: event.name, properties: props, timestamp: ctx.occurredAt, uuid: uuidOf(`${event.name}:${ctx.idempotencyKey}`) });
  },
});

export const ga4Server = (cfg: { measurementId: string; apiSecret: string }): ServerAdapter => ({
  async send(event, props, ctx) {
    if (!ctx.ga) return console.warn(`tracking: ${event.name} not sent to GA4, no client_id was stored with it`);
    if (Date.now() - ctx.occurredAt.getTime() > 72 * 3600e3) return console.warn(`tracking: ${event.name} is older than GA4's 72 hours`);
    const { name, params } = ga4Payload(event, props);
    const problems = ga4Problems(name, params);
    if (problems.length) throw new TrackingError(name, problems.join("; "));
    const url = `https://www.google-analytics.com/mp/collect?measurement_id=${encodeURIComponent(cfg.measurementId)}&api_secret=${encodeURIComponent(cfg.apiSecret)}`;
    const session = ctx.ga.sessionId ? { session_id: ctx.ga.sessionId, engagement_time_msec: 1 } : {};
    const res = await fetch(url, { method: "POST", body: JSON.stringify({
      client_id: ctx.ga.clientId, user_id: ctx.userId, timestamp_micros: ctx.occurredAt.getTime() * 1000,
      events: [{ name, params: { ...params, ...session } }],
    }) });
    if (!res.ok) throw new Error(`GA4 Measurement Protocol answered ${res.status}`);
  },
});
```

The caller owns "once": record the idempotency key in the same database transaction as the state change (an outbox row), and send only when the row is new; a retried webhook finds the row and sends nothing. The deterministic UUID with the original `occurredAt` lets PostHog drop a duplicate that slips through, and GA4 drops a second `purchase` with the same `transaction_id` from the same user on web streams. A mobile app stream uses `app_instance_id` (from the Firebase SDK) instead of `client_id`.

## Tests

Each test builds a fresh tracker with memory adapters and sets consent itself, so no test depends on another.

```ts
// src/lib/tracking/tracker.test.ts
import { describe, expect, it } from "vitest";
import { memory, type Op } from "./adapters/memory";
import { defineEvents, extendEvents, type Dest, type EventDef } from "./define";
import { registry } from "./registry";
import { createServerTracker, type ServerContext } from "./server";
import { createTracker } from "./tracker";

function setup(beforeConsent: "hold" | "drop" = "hold") {
  const log: Op[] = [];
  const t = createTracker({ app: "shop-web", registry, beforeConsent, strict: true, now: () => new Date("2026-11-07T10:00:00Z"),
    adapters: { product: memory("product", log), marketing: memory("marketing", log) } });
  return { t, log, ops: (op: Op["op"]) => log.filter((o) => o.op === op) };
}
const checkout = { surface: "checkout", item_count: 2, cart_value_band: "25-100" } as const;

describe("consent", () => {
  it("starts no SDK and sends nothing before consent, then the held event once", () => {
    const { t, log, ops } = setup();
    t.track(t.events.checkoutStart, checkout);
    expect(log).toEqual([]);
    t.consent.set("product", "granted");
    expect(ops("start")).toEqual([{ dest: "product", op: "start" }]);
    expect(ops("capture").map((o) => o.name)).toEqual(["checkout_start", "consent_update"]);
  });

  it("drops held events on deny and stops the SDK on withdrawal", () => {
    const { t, ops } = setup();
    t.track(t.events.checkoutStart, checkout);
    t.consent.set("product", "denied");
    expect(ops("capture")).toEqual([]);
    t.consent.set("product", "granted");
    t.consent.set("product", "denied");
    expect(ops("stop")).toEqual([{ dest: "product", op: "stop" }]);
    t.track(t.events.checkoutStart, checkout);
    expect(ops("capture").filter((o) => o.name === "checkout_start")).toEqual([]);
  });

  it("drops instead of holding when the tracking doc says so", () => {
    const { t, ops } = setup("drop");
    t.track(t.events.checkoutStart, checkout);
    t.consent.set("product", "granted");
    expect(ops("capture").map((o) => o.name)).toEqual(["consent_update"]);
  });
});

describe("identity", () => {
  it("logout cancels what was held for the old person", () => {
    const { t, ops } = setup();
    t.identify({ userId: "u_a" });
    t.track(t.events.checkoutStart, checkout);
    t.reset();
    t.consent.set("product", "granted");
    expect(ops("identify")).toEqual([]);
    expect(ops("capture").map((o) => o.name)).toEqual(["consent_update"]);
  });

  it("applies the current identity on grant, and resets on an account switch", () => {
    const { t, log } = setup();
    t.identify({ userId: "u_a", companyId: "c_1" });
    t.consent.set("product", "granted");
    t.identify({ userId: "u_b" });
    expect(log.filter((o) => o.op !== "capture")).toEqual([
      { dest: "product", op: "start" },
      { dest: "product", op: "identify", user: { userId: "u_a", companyId: "c_1" } },
      { dest: "product", op: "reset" },
      { dest: "product", op: "identify", user: { userId: "u_b" } },
    ]);
  });
});

describe("privacy guard", () => {
  it.each([
    ["a nested object", { ...checkout, item_count: { email: "ana@example.com" } }, /item_count/],
    ["an unknown key", { ...checkout, note: "x" }, /note/],
    ["a missing required key", { surface: "checkout", item_count: 2 }, /cart_value_band/],
    ["a value outside the set", { ...checkout, cart_value_band: "huge" }, /cart_value_band/],
    ["null", null, /props/],
  ])("rejects %s", (_, props, error) => {
    const { t } = setup();
    expect(() => t.track(t.events.checkoutStart, props as never)).toThrow(error);
  });

  it("rejects an email as an ID, in identity too", () => {
    const { t } = setup();
    expect(() => t.track(t.events.ctaClick, { surface: "cta", cta_id: "ana@example.com", cta_position: "hero" }, { category: "engagement" })).toThrow(/cta_id/);
    expect(() => t.identify({ userId: "ana@example.com" })).toThrow(/userId/);
    expect(() => t.identify({ userId: "u_1", name: "Ana" } as never)).toThrow(/name/);
  });

  it("needs the IDs a page type requires, and no others", () => {
    const { t } = setup();
    expect(() => t.track(t.events.pageView, { page_type: "product" } as never)).toThrow(/product_id/);
    expect(() => t.track(t.events.pageView, { page_type: "home", product_id: "p1" } as never)).toThrow(/product_id/);
  });

  it("drops instead of throwing in production, and logs no value", () => {
    const log: Op[] = [];
    const t = createTracker({ app: "web", registry, beforeConsent: "hold", strict: false, adapters: { product: memory("product", log), marketing: memory("marketing", log) } });
    t.consent.set("product", "granted");
    expect(() => t.track(t.events.checkoutStart, { ...checkout, item_count: "ana@example.com" } as never)).not.toThrow();
    expect(log.filter((o) => o.name === "checkout_start")).toEqual([]);
  });
});

describe("registry binding", () => {
  it("refuses at runtime what the types refuse", () => {
    const { t } = setup();
    const untyped = t.track as unknown as (key: string, props: object) => void; // what a call through `any` does
    expect(() => untyped("nope", {})).toThrow(/not a callable/);
    expect(() => untyped("orderComplete", {})).toThrow(/not a callable/);
    expect(() => untyped("purchase", {})).toThrow(/not a callable/);
    expect(() => untyped("toString", {})).toThrow(/not a callable/);
  });

  it("routes the per-call category", () => {
    const { t, ops } = setup();
    t.consent.set("product", "granted");
    t.consent.set("marketing", "granted");
    t.track(t.events.ctaClick, { surface: "cta", cta_id: "pricing_hero", cta_position: "hero" }, { category: "engagement" });
    expect(ops("capture").filter((o) => o.name === "cta_click").map((o) => o.dest)).toEqual(["product"]);
  });

  it("extendEvents refuses a reused key or name", () => {
    const extra = (name: string) => defineEvents({ x: { ...registry.checkoutStart, name } as EventDef });
    expect(() => extendEvents(registry, { checkoutStart: registry.checkoutStart })).toThrow(/already registered/);
    expect(() => extendEvents(registry, extra("checkout_start"))).toThrow(/already registered/);
    expect(Object.keys(extendEvents(registry, extra("checkout_resume")))).toContain("x");
  });
});

describe("server and renames", () => {
  const order = { order_id: "o_1", value: 59.9, currency: "EUR", items: [{ item_id: "sku_1", price: 59.9, quantity: 1 }], payment_method: "card", is_first_order: true } as const;
  const ctx = (at: string, consent: Record<Dest, boolean>): ServerContext => ({ userId: "u_1", consent, ga: { clientId: "123.456" }, occurredAt: new Date(at), idempotencyKey: "purchase:o_1" });

  function serverSetup() {
    const sent: Array<{ dest: Dest; name: string; props: Record<string, unknown> }> = [];
    const mem = (dest: Dest) => ({ send: async (e: EventDef, props: Record<string, unknown>) => void sent.push({ dest, name: e.name, props: structuredClone(props) }) });
    const s = createServerTracker({ app: "shop-api", registry, strict: true, adapters: { product: mem("product"), marketing: mem("marketing") } });
    return { s, sent };
  }

  it("sends the old name to product analytics only, in its own shape, until the sunset", async () => {
    const { s, sent } = serverSetup();
    await s.trackServer(ctx("2026-11-07T10:00:00Z", { product: true, marketing: true }), s.events.purchase, order);
    expect(sent.map((x) => `${x.dest}:${x.name}`)).toEqual(["product:purchase", "marketing:purchase", "product:order_completed"]);
    expect(sent[2]!.props).toEqual({ order_id: "o_1", order_total_band: "25-100", app: "shop-api" });
    sent.length = 0;
    await s.trackServer(ctx("2027-01-05T10:00:00Z", { product: true, marketing: true }), s.events.purchase, order);
    expect(sent.map((x) => x.name)).toEqual(["purchase", "purchase"]);
  });

  it("respects the stored consent", async () => {
    const { s, sent } = serverSetup();
    await s.trackServer(ctx("2026-11-07T10:00:00Z", { product: true, marketing: false }), s.events.purchase, order);
    expect(sent.map((x) => x.dest)).toEqual(["product", "product"]);
  });
});
```

```ts
// src/lib/tracking/types.test.ts
// Each line under @ts-expect-error must fail to compile; if one compiles, tsc fails on the unused directive.
import { it } from "vitest";
import { events, track } from "./index";
import { registry } from "./registry";

it("refuses at compile time", () => {
  const never = () => {
    // @ts-expect-error a forged definition is not a registry key
    track({ ...registry.checkoutStart, name: "unregistered_event" }, { surface: "checkout", item_count: 1, cart_value_band: "25-100" });
    // @ts-expect-error a name that is not in the registry
    track("unregistered_event", {});
    // @ts-expect-error deprecated entries are re-sent by the library, never called
    track(events.orderComplete, { order_id: "o_1", order_total_band: "0-25" });
    // @ts-expect-error a server event cannot be sent from the client
    track(events.purchase, {});
    // @ts-expect-error a product page needs product_id
    track(events.pageView, { page_type: "product" });
    // @ts-expect-error surface is required outside lifecycle
    track(events.checkoutStart, { item_count: 1, cart_value_band: "25-100" });
    // @ts-expect-error cta_click needs its per-call category
    track(events.ctaClick, { surface: "cta", cta_id: "x", cta_position: "hero" });
    // @ts-expect-error not one of the fixed values
    track(events.checkoutStart, { surface: "checkout", item_count: 1, cart_value_band: "huge" });
  };
  void never;
});
```

A feature test uses the module the app uses: render, act, then `expect(testLog).toContainEqual(expect.objectContaining({ op: "capture", name: "checkout_start" }))`, clearing `testLog` in `beforeEach`. In E2E runs, assert on `window.__tracking` (the `testLog`, exposed behind `TRACKING_ADAPTER=memory`) or on intercepted requests to the analytics hosts.

## registry.test.ts

```ts
// src/lib/tracking/registry.test.ts
import { describe, expect, it } from "vitest";
import { ga4Payload, ga4Problems, ga4UserProblems, PREDEFINED } from "./adapters/ga4-rules";
import { destinationsOf, type EventDef, type PropKind } from "./define";
import { registry } from "./registry";

const all: readonly EventDef[] = Object.values(registry); // widened, so optional fields read without casts
const current = all.filter((e) => e.status === "proposed" || e.status === "live");
const toMarketing = current.filter((e) => destinationsOf(e).includes("marketing"));
const NAME = /^[a-z][a-z0-9]*(_[a-z0-9]+)*$/;
const VALUE_IN_NAME = /_(\d+\w*|v\d+|monthly|yearly|annual|weekly|daily)$/;
const DAY = 864e5;
const sample = (k: PropKind): unknown =>
  typeof k !== "string" ? k[0] : k === "items" ? [{ item_id: "sku_1", price: 1, quantity: 1 }] : k === "bool" ? true : k === "int" || k === "number" ? 1 : "x";
// the largest payload an event can carry, as the adapters build it
const fullPayload = (e: EventDef) => ({ ...Object.fromEntries(Object.entries(e.props).map(([p, k]) => [p, sample(k)])), app: "x", release: "x", surface: "x" });

describe("tracking registry", () => {
  it.each(current)("$name follows the naming rules", (e) => {
    expect(e.name).toMatch(NAME);
    expect(e.name).not.toMatch(VALUE_IN_NAME);
    expect(ga4Problems(e.name, {})).toEqual([]); // product-only events too, so they can move to marketing later
    for (const p of Object.keys(e.props)) expect(p).toMatch(NAME);
  });

  it.each(all)("$name has an owner, a question, a trigger and a since-version", (e) => {
    expect(e.owner && e.question && e.firedWhen && e.since).toBeTruthy();
  });

  it("names are unique, in code and in the marketing tool", () => {
    const names = all.map((e) => e.name);
    const marketing = toMarketing.map((e) => e.marketingName ?? e.name);
    expect(new Set(names).size).toBe(names.length);
    expect(new Set(marketing).size).toBe(marketing.length);
  });

  it.each(toMarketing)("$name is accepted by GA4 as sent", (e) => {
    const { name, params } = ga4Payload(e, fullPayload(e));
    expect(ga4Problems(name, params)).toEqual([]);
  });

  it("custom parameters fit GA4's 50 event-scoped custom dimensions", () => {
    const custom = new Set(toMarketing.flatMap((e) => Object.keys(ga4Payload(e, fullPayload(e)).params)).filter((p) => !PREDEFINED.has(p)));
    expect(custom.size).toBeLessThanOrEqual(50);
  });

  it("identity fits GA4's user-property rules", () => {
    expect(ga4UserProblems({ account_type: "x", company_id: "x", plan_tier: "x" })).toEqual([]);
  });

  it.each(all.filter((e) => e.status === "deprecated"))("$name has a live replacement, a 30-day window and a sunset ahead", (e) => {
    const next = current.find((x) => x.name === e.replacedBy);
    expect(next?.capture).toBe(e.capture);
    expect(e.toLegacy).toBeTypeOf("function");
    const from = Date.parse(e.deprecatedOn ?? ""), to = Date.parse(e.sunset ?? "");
    expect(to - from).toBeGreaterThanOrEqual(30 * DAY);
    expect(to, `${e.name}: sunset passed, set status "removed"`).toBeGreaterThanOrEqual(Date.now() - DAY);
  });

  it("keeps the per-call category to one event", () => {
    expect(all.filter((e) => Array.isArray(e.category)).length).toBeLessThanOrEqual(1);
  });
});
```

## Lint rule

ESLint flat config. If the project already sets `no-restricted-syntax` or `no-restricted-imports`, merge these entries into its lists: a later config object replaces the whole rule, it does not add to it.

```js
// eslint.config.js (merge into the project's config)
const via = "Track through @/lib/tracking (see docs/tracking.md).";
const SDK = "^(posthog-js|posthog-node|posthog-react-native|@posthog/|react-ga4|ga-gtag|@next/third-parties/google|@segment/|mixpanel|@amplitude/)";
const SDK_Q = "/^(posthog|@posthog|react-ga4|ga-gtag|@next.third-parties.google|@segment|mixpanel|@amplitude)/";

export const tracking = {
  files: ["**/*.{js,jsx,ts,tsx,mjs,cjs}"],
  ignores: ["src/lib/tracking/**"],
  rules: {
    "no-restricted-imports": ["error", { patterns: [
      { regex: SDK, message: via },
      { group: ["@/lib/tracking/*", "!@/lib/tracking/server"], message: "Import from @/lib/tracking (or @/lib/tracking/server on the server)." },
    ] }],
    "no-restricted-syntax": ["error",
      { selector: `ImportExpression[source.value=${SDK_Q}]`, message: via },
      { selector: `CallExpression[callee.name='require'][arguments.0.value=${SDK_Q}]`, message: via },
      { selector: "CallExpression[callee.name='gtag'], CallExpression[callee.property.name='gtag']", message: via },
      { selector: "CallExpression[callee.property.name='push'][callee.object.name='dataLayer']", message: via },
      { selector: "CallExpression[callee.property.name='push'][callee.object.property.name='dataLayer']", message: via },
      { selector: "CallExpression[callee.object.name=/posthog/i][callee.property.name=/^(capture|identify|group|alias|reset|register)$/]", message: via },
      { selector: "CallExpression[callee.object.property.name=/posthog/i][callee.property.name=/^(capture|identify|group|alias|reset|register)$/]", message: via },
      { selector: "CallExpression[callee.name='track'][arguments.0.type!='MemberExpression']", message: "Pass a registry key: track(events.x, ...)." },
      { selector: "CallExpression[callee.name='trackServer'][arguments.1.type!='MemberExpression']", message: "Pass a registry key: trackServer(ctx, events.x, ...)." },
    ],
  },
};
// export default [...projectConfig, tracking];
```

Prove it: a fixture file outside the library with one of each banned pattern must give one error per line (see `tracking-library-run`, guard rails).

## The generated tracking plan

The plan is for people who never open the registry: a PM checking what is already measured, a marketer checking what reaches the ad tools, an analyst checking an event is live in the app they query.

```ts
// scripts/tracking-plan.ts: npx tsx scripts/tracking-plan.ts [--check]
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { destinationsOf, type EventDef, type PropKind } from "../src/lib/tracking/define";
import { registry } from "../src/lib/tracking/registry";

const FILE = "docs/tracking-plan.md";
const all: readonly EventDef[] = Object.values(registry).sort((a, b) => a.name.localeCompare(b.name));
const TOOL = { product: "product analytics", marketing: "marketing analytics" } as const;
const kind = (k: PropKind) => (typeof k === "string" ? k : k.join(" / "));
const props = (e: EventDef) => Object.entries(e.props).map(([p, k]) => `\`${p}\`${e.optional?.includes(p) ? " (optional)" : ""}: ${kind(k)}`).join("<br>") || "none";
const goesTo = (e: EventDef) => e.status === "deprecated" ? "product analytics only (old name, kept for old dashboards)"
  : Array.isArray(e.category)
  ? `chosen per call: ${e.category.map((c) => `${c} (${destinationsOf({ ...e, category: c }).map((d) => TOOL[d]).join(" + ")})`).join(" or ")}`
  : `${e.category}: ${destinationsOf(e).map((d) => TOOL[d]).join(" + ")}${e.marketingName && e.marketingName !== e.name ? ` (as \`${e.marketingName}\`)` : ""}`;
const status = (e: EventDef) => e.status === "deprecated" ? `deprecated: use \`${e.replacedBy}\`, gone after ${e.sunset}` : e.status;
const apps = [...new Set(all.flatMap((e) => e.apps ?? ["every app"]))];

const plan = [
  "# Tracking plan", "",
  "Generated from the tracking registry by scripts/tracking-plan.ts. Do not edit by hand; change the registry.", "",
  "Each event answers one question. `proposed` means defined but not seen in production yet; it becomes `live` the first time it is.",
  "`deprecated` events still fire until their date, so old dashboards keep working; build new ones on the replacement.", "",
  "## Coverage per app", "",
  ...apps.flatMap((app) => [`- **${app}:** ${all.filter((e) => e.status !== "removed" && (e.apps ?? ["every app"]).includes(app)).map((e) => `\`${e.name}\` (${e.status})`).join(", ")}`]),
  "", "## Events", "",
  "| Event | Question it answers | Fires when | Goes to | Side | Status | Owner | Properties | Since |",
  "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
  ...all.map((e) => `| \`${e.name}\` | ${e.question} | ${e.firedWhen} | ${goesTo(e)} | ${e.capture} | ${status(e)} | ${e.owner} | ${props(e)} | ${e.since} |`),
  "",
].join("\n");

if (process.argv.includes("--check")) {
  if (!existsSync(FILE) || readFileSync(FILE, "utf8") !== plan) {
    console.error(`${FILE} is missing or stale: run npx tsx scripts/tracking-plan.ts`);
    process.exit(1);
  }
} else writeFileSync(FILE, plan);
```

Add a package script (`tracking:plan`) and a CI step running it with `--check`; that fails on a stale plan and on a missing one.

Optional: a sync script pushes each entry's question, owner and status to the product-analytics tool's event definitions (description, tags, verified for `live`, hidden for `proposed`), through `posthog-manage`. Run it by hand after a release, never from CI with a personal key.

## Other stacks

The registry must stay one list across languages. When a second language fires events (a Python API next to a TypeScript web app), make the registry data: `tracking/registry.json` with the fields of `EventDef` (no functions; `marketingParams` and `toLegacy` become field maps), validated by the TypeScript test and by each language's test, and generate each language's typed bindings from it in CI.

- **Python (server):** `tracking/registry.py` generated from the JSON: one frozen pydantic model per event's properties (`extra="forbid"`, `Literal` for fixed values, `constr` for IDs and labels), `track_server(ctx, EVENTS.purchase, Purchase(...))` with the `ServerContext` fields above; `posthog` sends with `uuid` and `timestamp`; ruff's `flake8-tidy-imports.banned-api` bans `posthog` outside `tracking/`.
- **Ruby (server):** a frozen registry hash generated from the JSON and `Tracking.track_server(ctx, :purchase, props)` that raises on an unknown event, key or value kind; a RuboCop cop bans `PostHog::Client` outside `app/lib/tracking`.
- **Go (server):** a `tracking` package with one struct per event generated from the JSON and `TrackServer(ctx, ev)`; `depguard` bans the SDK elsewhere.
- **Swift / Kotlin (mobile):** an enum (or sealed class) of events with associated values generated from the JSON; one `Tracker` with the same `start`, `stop`, `capture`, `identify`, `reset` adapters and a memory implementation; a lint rule (SwiftLint custom rule, detekt `ForbiddenImport`) on the SDK imports. Mobile specifics are in `tracking-library-run`, step 4.
