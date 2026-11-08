---
name: docs-changelog-write
description: "Authors release notes and CHANGELOG.md entries from supplied change history (merged PRs, commits, tickets): grouped by Keep a Changelog categories, user-facing wording, PR links, breaking changes called out. Use when the user says 'write the changelog', 'draft release notes', 'write the CHANGELOG entry', 'what changed since the last release'. Skip for: versioning, tagging and publishing (use cct:git-release-run), listing PRs or CI (use cct:github-manage)."
allowed-tools: "Read Grep Glob Write Bash(gh *) Bash(git log *) Bash(git tag *)"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Write release notes

Writes the changelog entry for one version from change history. It does not choose the version,
tag, push or publish; `cct:git-release-run` owns those and calls this skill for the text.

## Input

A version (or "unreleased") and a change range. If the user supplies the history, use it as is.
Otherwise read it, read-only:

```bash
git tag --sort=-v:refname | head -5
git log <previous-tag>..HEAD --oneline --no-merges
gh pr list --state merged --search "merged:>=YYYY-MM-DD" --json number,title,labels,author
```

No previous tag: the range is every commit on the default branch. No merged PRs in the range:
fall back to commits. The detailed steps are in `references/changelog-command.md`.

## Write

1. **Categorize** with Keep a Changelog: Added, Changed, Fixed, Removed, Security, and Breaking
   Changes (changes needing migration). Optional Infrastructure for CI, dependencies and tooling.
   Use PR labels or Conventional Commit prefixes (`feat`, `fix`, `refactor`, `breaking`) to place
   each item.
2. **Word each entry from the user's side.** Lead with what changed for them. Include the PR
   number as `(#123)`; credit the author when it is not the repo owner. For a breaking change say
   what to migrate to.
3. **Format:**

```markdown
## [x.y.z] - YYYY-MM-DD

### Added
- Add rate limiting to the public API (#125)

### Fixed
- Fix duplicate webhook events in the Stripe integration (#130) @contributor
```

4. **Update `CHANGELOG.md`:** insert the entry after the `# Changelog` header, or after
   `## [Unreleased]` when present (then update its comparison link). If the file does not exist,
   create it with the standard Keep a Changelog header.
5. **Business context (optional).** If PRs reference Linear issues and the Linear tools are
   connected, add a short "Business Context" section tying the changes to their project or
   initiative. Skip it when nothing is referenced or the tools are unavailable.
6. **Show** the user the counts (features, fixes, changes) and the entry, and ask whether any
   item should be reworded or recategorized.

## Changelogs that drive an upgrade

Some repos keep a changelog that tooling reads when upgrading (one entry per version, newest
first, headline lines, then `Mechanical` lines that the tool applies and `Manual` lines printed
for the engineer). When the existing file uses that structure, keep it: a version with no
migration lines needs only a re-run of the tool. Do not convert it to Keep a Changelog.
