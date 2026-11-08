# Playwright Setup & Tools Reference

Complete installation, configuration, and tool documentation for Playwright testing infrastructure.

---

## Contents

- 1. Playwright Test Framework
- 2. Playwright MCP Server (`@playwright/mcp`)
- 3. Playwright CLI Tool (`@playwright/cli`)
- 4. Playwright Test Agents (v1.56+)
- 5. Authentication
- 6. Configuration, CI and debugging
- 7. Useful Resources

---

## 1. Playwright Test Framework

### Installation

```bash
npm init playwright@latest
# or add to existing project:
npm install -D @playwright/test
npx playwright install
```

Install specific browsers only:

```bash
npx playwright install chromium
npx playwright install chromium --with-deps    # Include OS dependencies (for CI)
```

### Project Structure

The layout. `install-lint.sh` writes the files marked *installed*.

```
project/
  playwright.config.ts
  e2e/
    journeys.md                 # the journey inventory (installed template)
    personas.md                 # who signs in, with which helper (installed template)
    plans/                      # Markdown plans from the planner, one per surface
    fixtures/                   # persona sign-in, data factories, readiness checks
    i18n.ts                     # t(): copy resolved from the app's catalogue (installed)
    tokens.ts                   # resolveToken(): design tokens, not hex (installed)
    eslint.config.e2e.mjs       # the lint preset (installed)
    <journey>.spec.ts           # one spec file per journey
  test-results/                 # run output, gitignored
  playwright-report/            # HTML report, gitignored
```

### Configuration Reference

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // Test discovery
  testDir: './tests',
  testMatch: '**/*.spec.ts',
  testIgnore: '**/node_modules/**',

  // Execution
  fullyParallel: true,
  workers: process.env.CI ? 1 : undefined,          // only until each worker has its own data (strategy.md section 6)
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,                 // one retry; a pass on retry is flaky, not green
  timeout: 30000,

  // Reporting
  reporter: 'html',
  outputDir: 'test-results',

  // Lifecycle
  globalSetup: require.resolve('./global-setup'),
  globalTeardown: require.resolve('./global-teardown'),

  // Assertions
  expect: {
    timeout: 5000,
    toHaveScreenshot: { maxDiffPixels: 10 },
    toMatchSnapshot: { maxDiffPixelRatio: 0.1 },
  },

  // Shared settings
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },

  // Browser projects
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/user.json' },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'], storageState: 'playwright/.auth/user.json' },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'], storageState: 'playwright/.auth/user.json' },
      dependencies: ['setup'],
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'], storageState: 'playwright/.auth/user.json' },
      dependencies: ['setup'],
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 13'], storageState: 'playwright/.auth/user.json' },
      dependencies: ['setup'],
    },
  ],

  // Auto-start dev server
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
```

### CLI Commands

```bash
# Running tests
npx playwright test                              # All tests
npx playwright test --headed                     # Visible browser
npx playwright test --debug                      # With Inspector
npx playwright test --ui                         # Interactive UI mode
npx playwright test -g "login"                   # Filter by title
npx playwright test --project=chromium           # Specific project
npx playwright test -j 4                         # Set workers
npx playwright test --trace on                   # Record traces
npx playwright test --retries 1                  # Set retries
npx playwright test --shard=1/3                  # Shard for CI
npx playwright test --list                       # List without running
npx playwright test example.spec.ts:9 --debug    # Debug specific line

# Reports and traces
npx playwright show-report
npx playwright show-trace [trace-file]

# Code generation
npx playwright codegen [url]
npx playwright codegen -o tests/gen.spec.ts      # Output to file

# Browser management
npx playwright install                           # All browsers
npx playwright install chromium --with-deps      # With OS deps
npx playwright uninstall                         # Remove browsers
npx playwright clear-cache                       # Clear caches
```

---

## 2. Playwright MCP Server (`@playwright/mcp`)

General-purpose browser automation MCP server. Uses accessible tree snapshots (not vision). Fast, lightweight, LLM-friendly.

- **Repo:** https://github.com/microsoft/playwright-mcp
- **NPM:** `@playwright/mcp`
- **Requires:** Node.js 18+

### Installation

For Claude Code:

```bash
claude mcp add playwright npx @playwright/mcp@latest
```

For VS Code / other MCP clients:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

With headless mode (recommended for multitasking):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless"]
    }
  }
}
```

Docker deployment:

```bash
docker run -d --init -p 8931:8931 \
  mcr.microsoft.com/playwright/mcp \
  node cli.js --headless --browser chromium --port 8931 --host 0.0.0.0
```

### Available Tools

**Navigation:** `browser_navigate`, `browser_navigate_back`, `browser_snapshot`, `browser_take_screenshot`

**Forms:** `browser_type`, `browser_fill_form`, `browser_press_key`, `browser_select_option`

**Elements:** `browser_click`, `browser_hover`, `browser_drag`, `browser_file_upload`

**Inspection:** `browser_console_messages`, `browser_network_requests`, `browser_evaluate`

**Browser:** `browser_close`, `browser_tabs`, `browser_resize`, `browser_install`, `browser_handle_dialog`

**Optional capabilities** (enable with `--caps` flag):

| Flag | Tools Added |
|------|------------|
| `--caps=vision` | Mouse click/move/drag/wheel at pixel coordinates |
| `--caps=pdf` | `browser_pdf_save` |
| `--caps=testing` | `browser_generate_locator`, verify element/text/list/value |

### Key CLI Flags

| Flag | Description |
|------|-------------|
| `--browser` | chromium, firefox, webkit, msedge |
| `--headless` | No visible browser window |
| `--viewport-size` | e.g., "1280x720" |
| `--user-data-dir` | Persistent profile location |
| `--isolated` | Ephemeral session |
| `--storage-state` | Load auth state from file |
| `--save-trace` | Record Playwright trace |
| `--save-video` | Capture video |
| `--allowed-origins` | Whitelist URLs (semicolon-separated) |
| `--blocked-origins` | Blacklist URLs (semicolon-separated) |
| `--config` | Load JSON config file |

Environment variables: all flags support `PLAYWRIGHT_MCP_` prefix (e.g., `PLAYWRIGHT_MCP_HEADLESS=true`).

### Configuration File

```json
{
  "browser": {
    "browserName": "chromium",
    "isolated": false,
    "launchOptions": { "channel": "chrome", "headless": true },
    "contextOptions": { "viewport": { "width": 1280, "height": 720 } }
  },
  "security": {
    "allowedOrigins": "https://example.com;https://app.example.com",
    "blockedOrigins": "https://ads.example.com"
  }
}
```

---

## 3. Playwright CLI Tool (`@playwright/cli`)

Standalone shell-based browser automation for AI coding agents. Uses plain commands instead of MCP protocol. ~4x more token-efficient than MCP.

- **Repo:** https://github.com/microsoft/playwright-cli
- **NPM:** `@playwright/cli`
- **Requires:** Node.js 18+

### Installation

```bash
npm install -g @playwright/cli@latest
playwright-cli install --skills    # Install agent integration
```

### Key Commands

```bash
# Navigation
playwright-cli open [url]
playwright-cli goto <url>
playwright-cli go-back / go-forward
playwright-cli reload
playwright-cli close

# Interaction
playwright-cli click <ref>
playwright-cli type <text>
playwright-cli fill <ref> <text>
playwright-cli select <ref> <value>
playwright-cli hover <ref>
playwright-cli check / uncheck <ref>

# Screenshots & output
playwright-cli snapshot                    # Accessibility tree snapshot
playwright-cli screenshot [ref]
playwright-cli pdf

# Tabs
playwright-cli tab-list / tab-new / tab-close / tab-select

# Storage
playwright-cli state-save / state-load
playwright-cli cookie-list / cookie-get / cookie-set / cookie-clear

# Debugging
playwright-cli console
playwright-cli network
playwright-cli run-code <js>
playwright-cli tracing-start / tracing-stop

# Session management
playwright-cli list                        # List sessions
playwright-cli -s=name open <url>          # Named session
playwright-cli show                        # Monitoring dashboard
```

### MCP vs CLI Comparison

| Aspect | MCP Server | CLI Tool |
|--------|-----------|----------|
| Token usage | ~114K tokens/task | ~27K tokens/task |
| Protocol | MCP (JSON-RPC) | Shell commands |
| State | Persistent browser context | Named sessions |
| Best for | Autonomous systems, exploratory | High-throughput coding agents |
| Setup | JSON config in MCP client | `npm install -g` |

---

## 4. Playwright Test Agents (v1.56+)

**Not used here.** Documented so you recognise them; `SKILL.md` ("Two upstream tools this setup
does not use") says why. Their healer may mark a test `fixme`, which our healer must never
do. Use `cct:test-e2e-coverage-run` instead.

### Setup

```bash
npx playwright init-agents --loop=claude     # Claude Code
npx playwright init-agents --loop=vscode     # VS Code (requires v1.105+)
npx playwright init-agents --loop=opencode   # OpenCode
```

Regenerate agent definitions whenever Playwright updates.

### Generated Structure

```
project/
  .github/agents/          # Agent definitions (VS Code) or agents/ (Claude)
  specs/                   # Markdown test plans from planner
  tests/
    seed.spec.ts           # Seed file — your control point
    feature/
      scenario.spec.ts     # Generated tests
```

### Agent Pipeline

1. **Planner** — explores app via accessible tree, outputs markdown specs
2. **Generator** — converts specs to tests, verifies locators live
3. **Healer** — runs tests, debugs failures, adds FIXME for app bugs

Each agent can run independently or be chained.

### REPL Loops (Experimental)

A bash loop that chains plan -> generate -> heal without human intervention. Currently experimental — the Playwright team plans to build loops directly into agents.

---

## 5. Authentication

A spec signs in as a declared persona (`e2e/personas.md`, locator policy section 6). Where
the project has no persona helper yet, this is the upstream pattern:

1. A **setup project** signs in once and saves the browser state.
2. **Test projects** depend on it and reuse the saved state; nothing logs in twice.
3. Credentials stay in environment variables. The agent never reads them.

```
playwright.config.ts
  projects:
    - name: 'setup', testMatch: '*.setup.ts'
    - name: 'chromium', dependencies: ['setup'], use: { storageState: 'playwright/.auth/user.json' }

.gitignore
  playwright/.auth/
```

- **Several roles:** one state file per role (`admin.json`, `viewer.json`), chosen per test
  with `test.use({ storageState: 'playwright/.auth/admin.json' })`.
- **Signed out:** `test.use({ storageState: { cookies: [], origins: [] } })`.
- **Faster:** sign in through the API with `APIRequestContext`, or write the session row
  directly when the real login (OAuth, magic link) cannot be driven, and say so in
  `e2e/personas.md`.

---

## 6. Configuration, CI and debugging

```typescript
defineConfig({
  fullyParallel: true,
  forbidOnly: !!process.env.CI,       // a stray .only fails CI
  retries: process.env.CI ? 1 : 0,    // one retry; a pass on retry is reported flaky, not green
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {                        // the production build, never the dev server
    command: 'npm run build && npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

- Run on Linux and install only what runs: `npx playwright install chromium --with-deps`.
- Shard with `--shard=1/3` once each worker has its own data (strategy.md section 6); a
  shared database makes sharding a source of flakes.
- Lint specs with `@typescript-eslint/no-floating-promises` and run `tsc --noEmit`: a
  missing `await` is the most common silent race.
- Upload the HTML report and traces as CI artifacts.

| Debugging | Command |
|---|---|
| Step through | `npx playwright test path/to.spec.ts:12 --debug` |
| Interactive tree, watch mode | `npx playwright test --ui` |
| Trace of a CI failure | `npx playwright show-trace trace.zip` or `npx playwright show-report` |
| Ask a model | the **Copy prompt** button in the HTML report or trace viewer copies the accessibility tree, the source and the error |

---

## 7. Useful Resources

| Resource | URL |
|----------|-----|
| Playwright Docs | https://playwright.dev |
| Playwright GitHub | https://github.com/microsoft/playwright |
| Playwright MCP GitHub | https://github.com/microsoft/playwright-mcp |
| Playwright CLI GitHub | https://github.com/microsoft/playwright-cli |
| Playwright YouTube | https://youtube.com/@playwright |
| Best Practices | https://playwright.dev/docs/best-practices |
| Test Agents Docs | https://playwright.dev/docs/test-agents |
| Auth Docs | https://playwright.dev/docs/auth |
| Debbie O'Brien | https://deb.codes |
