# Changelog entry from merged PRs and commits

Generates or updates a CHANGELOG.md file from merged PRs and git history.

## Instructions

### Step 1: Determine the range

Find the previous release tag to scope the changelog:

```bash
git tag --sort=-v:refname | head -5
```

If there's a previous tag, the range is `<previous-tag>..HEAD`. If no tags exist, use all commits on the default branch.

### Step 2: Fetch merged PRs

Use `gh` to list merged PRs in the range:

```bash
gh pr list --state merged --base main --search "merged:>=YYYY-MM-DD" --json number,title,labels,author
```

Or use git log for commit-based changelogs:

```bash
git log <previous-tag>..HEAD --oneline --no-merges
```

### Step 3: Categorize entries

Group by type using PR labels or commit prefixes (feat:, fix:, etc.):

- **Added** — new features (`feat`, `feature`, `enhancement`)
- **Changed** — modifications to existing behavior (`change`, `refactor`)
- **Fixed** — bug fixes (`fix`, `bug`, `bugfix`)
- **Deprecated** — features marked for removal
- **Removed** — features deleted
- **Breaking Changes** — changes requiring migration (`breaking`)

### Step 4: Write each entry

For each PR or commit:
- Lead with what changed from the user's perspective
- Include the PR number as a link: `(#123)`
- Credit the author if it's not the repo owner

### Step 5: Write CHANGELOG.md

If `CHANGELOG.md` exists, prepend the new version section after the header. If it doesn't exist, create it.

Follow [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [v2.4.0] — YYYY-MM-DD

### Added
- Add user authentication via OAuth (#123) — @contributor
- Add rate limiting to public API (#125)

### Changed
- Update dashboard layout for mobile (#127)

### Fixed
- Fix duplicate webhook events in Stripe integration (#130)
- Fix timezone handling in scheduled reports (#132)

### Breaking Changes
- Remove deprecated `/api/v1/users` endpoint — migrate to `/api/v2/users` (#128)
```

### Step 6: Confirm

Show the user:
- Summary: X features, Y fixes, Z changes
- The generated changelog content for review
- Ask if any items should be reworded or recategorized
