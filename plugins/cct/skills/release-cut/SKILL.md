---
name: release-cut
description: Manages releases — semantic versioning, changelog generation from merged PRs, GitHub releases, and optional Linear context enrichment. Use when user says "create release", "cut a release", "release", "changelog", "version bump", "tag release", "draft release notes", "what changed since last release", or asks to prepare, publish, or document a release.
allowed-tools: "Bash(gh *) Bash(git *)"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Release Manager

Manages releases with semantic versioning, changelog generation, and GitHub releases. Can enrich release notes with Linear project/initiative context when available.

## Instructions

### Step 1: Determine Release Type

Ask the user or infer from changes:

| Type | When | Version bump |
|------|------|-------------|
| **Major** (X.0.0) | Breaking changes, API removals, incompatible migrations | `v1.0.0 -> v2.0.0` |
| **Minor** (x.Y.0) | New features, non-breaking additions | `v1.0.0 -> v1.1.0` |
| **Patch** (x.y.Z) | Bug fixes, dependency updates, docs | `v1.0.0 -> v1.0.1` |

### Step 2: Gather Changes

```bash
# Get the latest release tag
LATEST_TAG=$(gh release list --limit 1 --json tagName -q '.[0].tagName')

# If no releases exist yet
if [ -z "$LATEST_TAG" ]; then
  echo "No previous releases found. This will be the first release."
  LATEST_TAG=$(git rev-list --max-parents=0 HEAD)
fi

# List merged PRs since last release
gh pr list --state merged --search "merged:>$(gh release view $LATEST_TAG --json publishedAt -q .publishedAt 2>/dev/null || echo '2020-01-01')" --json number,title,author,labels,mergedAt --jq '.[] | "#\(.number) \(.title) (@\(.author.login))"'

# Or use git log for commit-based changelog
git log ${LATEST_TAG}..HEAD --oneline --no-merges
```

### Step 3: Categorize Changes

Group changes using Keep a Changelog categories:

| Category | What belongs here |
|----------|------------------|
| **Added** | New features, new endpoints, new commands |
| **Changed** | Changes to existing functionality |
| **Fixed** | Bug fixes |
| **Removed** | Removed features or deprecated items |
| **Security** | Security patches or vulnerability fixes |
| **Infrastructure** | CI/CD, dependencies, tooling (optional) |

### Step 4: Enrich with Linear Context (Optional)

If the repo uses Linear and the MCP is connected, pull project/initiative context to frame changes in business terms:

1. Check PR descriptions for Linear issue references (e.g., `DAT-83`, `REV-42`)
2. Look up the referenced issues to find their parent project and initiative
3. Add a "Business Context" section to the release notes that connects changes to strategic goals

Example enrichment:
```
## Business Context
This release advances the **AI-Native Enablement** initiative:
- Automated changelog generation (Quality Assurance & Testing project)
- PR review improvements (Developer Experience project)
```

Skip this step if Linear MCP is not available or no issues are referenced.

### Step 5: Generate Changelog Entry

Format the changelog entry following Keep a Changelog:

```markdown
## [x.y.z] - YYYY-MM-DD

### Added
- Add feature X for Y (#123) @author

### Fixed
- Fix bug in Z when A happens (#456) @author

### Changed
- Update dependency B to v2.0 (#789) @author
```

### Step 6: Update CHANGELOG.md

If the repo has a `CHANGELOG.md`:
1. Read the existing file
2. Insert the new entry after the `# Changelog` header (or after `## [Unreleased]` if present)
3. Update the `[Unreleased]` comparison link if present

If no `CHANGELOG.md` exists, create one:
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [x.y.z] - YYYY-MM-DD

### Added
- ...
```

### Step 7: Create the Release

```bash
# Create a git tag
git tag -a v{version} -m "Release v{version}"

# Push the tag
git push origin v{version}

# Create GitHub release with generated notes
gh release create v{version} --title "v{version}" --notes "$(cat <<'EOF'
{changelog entry from Step 5}
EOF
)"
```

For draft releases (review before publishing):
```bash
gh release create v{version} --draft --title "v{version}" --notes "..."
```

### Step 8: Confirm

Show the user:
- Release URL
- Version number
- Changelog entry
- Any CHANGELOG.md changes made

## Examples

### Example 1: Standard release
User says: "cut a release"
Actions:
1. Find latest tag, list merged PRs since then
2. Suggest version bump based on changes
3. Generate categorized changelog
4. Update CHANGELOG.md, tag, create GitHub release
Result: Release published with changelog

### Example 2: Changelog only
User says: "what changed since last release?"
Actions:
1. Find latest tag, list merged PRs
2. Categorize and format changes
3. Present to user without creating a release
Result: Formatted changelog displayed

### Example 3: Linear-enriched release
User says: "create a release with business context"
Actions:
1. Gather changes, extract Linear issue references from PRs
2. Look up issues, projects, initiatives via Linear MCP
3. Add Business Context section to release notes
4. Create release
Result: Release notes with both technical changes and business framing

## Error Handling

### No previous releases
Solution: Use the initial commit as the baseline. All commits become the first changelog.

### No merged PRs found
Cause: PRs were merged before the date filter or commits were pushed directly.
Solution: Fall back to `git log` for commit-based changelog.

### Linear MCP not available
Solution: Skip the enrichment step. Generate standard changelog without business context.
