# Finding the routes, by stack

Read by `cct:ux-sitemap-create` before `as-built` and `diff`. Detect the stack from the repo;
never assume one. When the repo matches none of these, find the place where an address becomes
a screen and read that, then say in the report which source was used.

## 1. Detect

| Signal | Stack |
|---|---|
| `next` in the package manifest, an `app/` or `src/app/` folder with `page.*` files | Next.js App Router |
| `next`, a `pages/` or `src/pages/` folder | Next.js Pages Router (both can coexist: list both) |
| `react-router` 7 with `app/routes.ts`, or `@remix-run/*` | React Router framework mode or Remix |
| `react-router-dom` / `react-router` with `createBrowserRouter`, `useRoutes` or `<Route path>` | React Router library mode |
| `@tanstack/react-router`, a `routeTree.gen.ts` | TanStack Router |
| `vue-router` with `createRouter({ routes })` | Vue Router |
| `nuxt`, a `pages/` folder of `.vue` files | Nuxt |
| `@sveltejs/kit`, `src/routes/**/+page.svelte` | SvelteKit |
| `astro`, `src/pages/` | Astro |
| `@angular/router`, `Routes` arrays | Angular |
| `config/routes.rb` | Rails |
| `urls.py` with `urlpatterns` | Django |
| `routes/web.php` | Laravel |
| `electron` or a native shell with no URL bar | Desktop: the screens are the navigation stack or state machine; the "route" is the screen id the code uses |

## 2. Per stack

**Next.js App Router.** A page is a `page.tsx|jsx|ts|js` file; its address is the folder path.
`(group)` folders do not appear in the address but often mark an area (console, portal,
public). `[id]` is a path param, `[...slug]` a catch-all, `[[...slug]]` an optional catch-all.
`@slot` folders are parallel routes and `(.)x` folders intercepting routes: they render inside
another page, so list them as a panel of that page, with the address they also answer on.
`route.ts` is an API or file endpoint, not a page, unless a mail links to it (then it is an
inbound target, listed with its type). `not-found`, `error` and `global-error` files are the
error pages of their segment. Redirects: `next.config.*` `redirects()` and `rewrites()`,
`middleware.ts` or `proxy.ts`, and `redirect()` / `permanentRedirect()` in pages and layouts.
Locale: a `[locale]` segment, with the list in the i18n config (for example next-intl's
`routing.ts`: `locales`, `defaultLocale`, `localePrefix`).

**Next.js Pages Router.** Every file under `pages/` except `_app`, `_document`, `_error` and
`api/` is a page; `[id].tsx` and `[...slug].tsx` as above. Locales from `i18n` in
`next.config.*`.

**React Router and Remix.** Library mode: route objects or `<Route>` JSX, nested `children`
joined to the parent's path, `index` routes, `lazy` imports (follow them to the component).
Framework mode: `app/routes.ts` (`route()`, `index()`, `layout()`, `prefix()`), or file routes
in `app/routes/` where a dot is a slash, `$id` is a param, `_` prefixed segments are pathless
layouts and `_index` is the index. `redirect()` in loaders and actions are redirects.

**TanStack Router.** `routeTree.gen.ts` is the generated full list; the source files are in
`src/routes/`. `$id` is a param; `validateSearch` declares the query params, with types.

**Vue Router and Nuxt.** `routes` arrays with `path`, `name`, `children`, `redirect`, `alias`
(an alias is a second address: check SM-4). Nuxt: `pages/` files, `[id].vue`, `[...slug].vue`,
`index.vue`; `definePageMeta` for middleware, layout and aliases; `@nuxtjs/i18n` for locales and
its `strategy` for the prefix.

**SvelteKit and Astro.** SvelteKit: `+page.svelte` per page, `(group)` folders as in Next.js,
`[id]`, `[...rest]`, `[[optional]]`; `+page.server.ts` `redirect()` calls. Astro: every file in
`src/pages/`, `[id].astro`, `[...slug].astro`, `getStaticPaths` for generated pages.

**Angular.** `Routes` arrays (`path`, `component`, `loadComponent`, `loadChildren`,
`redirectTo`, `canActivate` guards for access). Follow lazy children to their own arrays.

**Rails.** `config/routes.rb`. `resources :items` gives index, new, show and edit pages (GET),
plus create, update and destroy, which are not pages. `only:` and `except:` narrow it;
`namespace` and `scope` add a prefix; `scope "(:locale)"` is an optional locale. `bin/rails
routes` lists the result when the app boots; it only reads, so it may run. Access from
`before_action` filters and the policy classes (Pundit, CanCanCan).

**Django and Laravel.** Django: `urlpatterns` with `path()` and `include()`, joined in order;
`i18n_patterns` adds the locale. Laravel: `Route::get`, `Route::resource`, `Route::prefix`,
`->middleware()` for access; `php artisan route:list` reads the result.

## 3. Around the router

| What | Where to look |
|---|---|
| Labels | the message catalogue (`messages/*.json`, `locales/**`, `config/locales/*.yml`, `.po` files); the key the page title, the navigation item and the breadcrumb use |
| Navigation | a nav config file, or the sidebar, rail, tab bar, settings menu and command menu components |
| Ways in | links (`href`, `<Link>`, `link_to`, `routerLink`, `:to`), `router.push`, route helpers, form actions, server redirects; search for the literal address and for its helper name |
| Query params | `searchParams`, `useSearchParams`, `useSearch`, `route.query`, `params` in controllers; the list toolbar's filter, sort and view components |
| Access | middleware, layouts that check a session or role, route guards, controller filters, policies |
| Hosts | middleware that refuses paths by host, deployment config, environment variables naming base URLs |
| Inbound links | mail templates, notification payloads, embed snippets, public docs, and any absolute URL built with the base URL |
| Error pages | the framework's not-found and error files, and every place that calls the not-found helper |

A link built from a variable (`href={item.url}`) is followed to where the variable is set. If
it cannot be resolved, the entry says so; it is not dropped.
