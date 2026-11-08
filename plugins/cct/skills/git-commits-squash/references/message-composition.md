# Message Composition

Synthesis rules for composing **one** conventional commit message from **many** source commits — used by both `references/commands/branch.md` (local) and `references/commands/pr.md` (GitHub PR).

For the canonical type table, header/body/footer format, and examples, see `../../role-conventional-commits/references/format.md`. This file layers synthesis rules on top of that format.

## Inputs

- **Branch mode**: N local commits between `merge-base` and `HEAD`, plus enriched Linear/GitHub ticket context.
- **PR mode**: N PR commits, the PR title and body, linked Linear/GitHub issues, and existing reviews.

## Output

One conventional commit message that becomes:
- **Branch mode**: the message of the single commit created by `git reset --soft` + `git commit`.
- **PR mode**: the `<subject>` arg and stdin `<body>` passed to `gh pr merge --squash -t <subject> -F -`.

## Synthesis Rules

### Type Selection

Priority order:

1. **From ticket type/labels** if a Linear ticket has a type (feature, bug, etc.) or a GitHub label like `bug`/`enhancement`.
2. **From dominant change pattern** across the diff: if most files are new functionality → `feat`; most are bug fixes → `fix`; etc.
3. **Present a choice to the user** if ambiguous between two types — don't silently pick.

### Scope

Infer from the primary module, directory, or area affected:
- Single module (`src/auth/*`) → use that module name as scope.
- Multiple modules under one parent → use the parent directory.
- Project-wide → omit scope.
- Keep scope 1–2 words, lowercase, no slashes.

### Header

Follows the format in `../../role-conventional-commits/references/format.md`. The PR title (in PR mode) is a strong candidate but is rewritten if it doesn't fit the format or no longer matches the diff.

### Body

- **Synthesize, don't list.** Write a coherent narrative — not a bullet list of individual commits. The body explains **what** and **why**, not a per-commit changelog.
- Pull *why* from the ticket description and acceptance criteria when available.
- If the ticket has acceptance criteria, optionally mention which ones this work satisfies.
- Wrap at 72 characters.

### Footer

- **Linear refs** → `Refs: ENG-123` (one per line if multiple tickets).
- **GitHub issues closed by this change** → `Fixes #42` or `Closes #42`.
- **GitHub references that are not closed** → `Refs: #42`.
- **Co-authors** → preserve every `Co-authored-by:` line found in source commits, deduplicated.
- **Breaking changes** → `BREAKING CHANGE: <what breaks>`, or `!` after type in the header per format reference.

## Mode-specific notes

### Branch mode

Source commits are local — the agent inspects them directly via `git log`. The synthesized message replaces all of them in one commit.

### PR mode

Source material includes the PR body, which is often already a narrative. Two checks before composing:

1. **Is the PR body already a coherent narrative that matches the format?** If yes, lift it as the body of the squash message with minimal edits.
2. **Does the PR body describe scope that no longer exists in the diff** (e.g., scope was cut during review)? Strip those parts and synthesize from what's actually shipping.

After composing, compute divergence from current PR title/body:
- Levenshtein distance > 25% on title OR different conventional-commit type → flag as "significant divergence" and offer to update the PR record via `gh pr edit` before merging.
- Below threshold → skip the offer; the squash message lands on `main` via `--subject`/`--body` regardless.

## Examples

See `../../role-conventional-commits/references/format.md` for canonical examples. Synthesis-specific example:

### Synthesis from 5 messy commits + ticket

Source commits (verbose, WIP-style):
```
WIP: try oauth provider
add google support
hook up github too
fix tests broken by middleware change
lint
```

Ticket: `ENG-123 — Add SSO with Google and GitHub (feature)`.

Synthesized:
```
feat(auth): add OAuth2 SSO with Google and GitHub providers

Implement PKCE-based OAuth2 flow for Google and GitHub identity
providers. Token refresh runs automatically via middleware on each
request when the access token is within 5 minutes of expiry.
Session data persists in encrypted cookies.

Refs: ENG-123
```

The synthesis combines: type (`feat` from ticket label), scope (`auth` from directory), narrative body (from ticket description, not commit list), and ticket footer.
