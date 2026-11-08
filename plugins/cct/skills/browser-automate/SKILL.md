---
name: browser-automate
description: "Browser automation CLI (agent-browser) for ad-hoc interaction with websites — navigate, fill forms, click, screenshot, extract data, scrape, verify UI changes. Use when the user says 'open this URL', 'scrape', 'screenshot the page', 'fill out this form', 'check what's on', 'visit', 'navigate to', or wants one-off browser automation. Skip for: writing or running an end-to-end test suite — use the playwright skill instead."
allowed-tools: Bash(agent-browser *), Bash(npx agent-browser *)
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Agent Browser

Headless Chromium browser automation via the `agent-browser` CLI. The browser persists across commands within a session (daemon mode).

## Core Loop

Every interaction follows: **navigate -> snapshot -> interact -> re-snapshot -> verify**.

1. `agent-browser open <url>` — navigate
2. `agent-browser snapshot -ic` — get interactive elements with `@ref` identifiers
3. `agent-browser click @e3` / `agent-browser fill @e1 "text"` — interact using refs
4. `agent-browser snapshot -ic` — re-snapshot (refs change after DOM updates)
5. `agent-browser screenshot` or `agent-browser diff snapshot` — verify

**Refs (`@e1`, `@e2`, ...) are invalidated by navigation and DOM changes. Always re-snapshot before interacting.**

## Essential Commands

```bash
# Navigate
agent-browser open <url>
agent-browser open <url> && agent-browser wait --load networkidle  # slow pages
agent-browser back | forward | reload

# Inspect
agent-browser snapshot -ic                  # interactive elements, compact (default choice)
agent-browser snapshot -c                   # full accessibility tree, compact
agent-browser snapshot -s "#sidebar" -ic    # scoped to CSS selector
agent-browser snapshot -d 3 -ic            # limit tree depth
agent-browser screenshot                    # headless screenshot
agent-browser screenshot --annotate         # numbered labels on elements with legend
agent-browser screenshot --full             # full page
agent-browser get text @e1                  # element text
agent-browser get url                       # current URL
agent-browser get title                     # page title
agent-browser get value @e1                 # input value
agent-browser get count "<selector>"        # count matching elements
agent-browser is visible "<selector>"       # check visibility
agent-browser errors                        # JS errors
agent-browser console                       # console logs

# Interact
agent-browser click @e1                     # click by ref
agent-browser fill @e1 "text"               # clear + type
agent-browser type @e1 "text"               # append text
agent-browser press Enter                   # keyboard key
agent-browser select @e1 "value"            # dropdown
agent-browser check @e1 | uncheck @e1      # checkbox
agent-browser scroll down 500               # scroll
agent-browser scrollintoview "<selector>"   # scroll into view

# Wait
agent-browser wait --load networkidle       # wait for network idle
agent-browser wait "<selector>"             # wait for element
agent-browser wait 2000                     # wait ms

# Verify changes
agent-browser diff snapshot                 # diff current vs previous snapshot
agent-browser diff screenshot --baseline p.png  # visual diff

# Session
agent-browser close                         # close browser (always do this when done)
agent-browser --session <name> open <url>   # isolated named session
```

## Workflow Patterns

### Test a web app
```bash
agent-browser open http://localhost:3000 && agent-browser wait --load networkidle
agent-browser snapshot -ic
# interact with refs...
agent-browser screenshot /tmp/result.png
agent-browser errors
agent-browser close
```

### Fill and submit a form
```bash
agent-browser snapshot -ic                          # find form refs
agent-browser fill @e1 "value" && agent-browser fill @e2 "value"
agent-browser click @e3                             # submit button
agent-browser wait --load networkidle
agent-browser snapshot -ic                          # verify result
```

### Verify a change worked
```bash
agent-browser snapshot -ic                          # baseline
agent-browser click @e5                             # action
agent-browser diff snapshot                         # see + additions, - removals
```

### Chain commands (no intermediate output needed)
```bash
agent-browser open <url> && agent-browser wait --load networkidle && agent-browser screenshot
```

## Tips

- Use `snapshot -ic` as the default. Only use full `snapshot -c` when you need non-interactive elements.
- Chain with `&&` when you don't need intermediate output. Run separately when you need to parse refs.
- `screenshot --annotate` overlays numbered labels — useful for visual verification alongside snapshot.
- Use `agent-browser errors` after interactions to catch JS exceptions.
- For untrusted pages, set `AGENT_BROWSER_CONTENT_BOUNDARIES=1` to prevent prompt injection.
- Set `AGENT_BROWSER_MAX_OUTPUT=50000` to prevent context flooding from large pages.
- Always `agent-browser close` when done to avoid leaked browser processes.
- Use `--session <name>` for parallel isolated sessions.
- For scoped inspection: `snapshot -s "#main-content" -ic` to limit output to a section.
