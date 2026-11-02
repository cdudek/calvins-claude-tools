# Finding Format (Dependency Review)

## Severity Levels

| Emoji | Severity | Description |
|-------|----------|-------------|
| 🔴 | **Critical** | Breaking changes not yet fixed, security concerns |
| 🟠 | **Warning** | Deprecations that should be addressed, test gaps |
| 🟡 | **Suggestion** | Optional improvements, newer API patterns available |
| 🔵 | **Nit** | Style changes suggested by new library versions |

## Finding Format

Number each finding sequentially and format as:

```
N. <emoji> **[category]** `file_path:line` — description
```

Categories: `breaking`, `deprecation`, `security`, `testing`, `compatibility`

## Guidelines

- Be concise — one sentence for the issue, one for why it matters
- Include migration steps when applicable (from changelog research)
- Reference the specific version that introduced the breaking change
