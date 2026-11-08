# Inconsistency Categories

Seven generalized detection categories. Apply each to the gathered branch data. These are ecosystem-agnostic — describe patterns, not specific files.

## 1. Contradictory Changes

**What:** Files or symbols added in one commit then removed in another within the same branch. Code paths introduced then deleted.

**How to detect:**
- Check the "Files Added Then Deleted" section from file operations output
- Check "Net-Zero Files" — files touched but with no net change
- In the full diff: look for functions/classes/variables that are defined and then have their definition removed

**Classify as:**
- **Question** if the commit messages don't explain the removal (e.g., "added auth.py" then later "removed auth.py" with no context)
- **Info** if commit messages explain it (e.g., "spike: try approach A" then "revert: approach A, go with B instead")

## 2. Incomplete Operations

**What:** A rename, move, or refactoring where not all references were updated. An import added but the imported symbol is never used. An export removed but downstream files still import it.

**How to detect:**
- From file operations: look for `R` (rename) entries — then grep the diff for the old filename/path
- In the full diff: look for new imports/requires — check if the imported name appears in the file's changed lines
- Look for deleted files — grep the remaining codebase for references to those filenames

**Classify as:**
- **Concern** if stale references are found in the codebase
- **Info** if all references appear updated

## 3. Missing Companion Changes

**What:** A new piece of functionality without its expected companions — tests, documentation, configuration, examples.

**How to detect:**
- New source files (from file operations `A` entries) — are there corresponding new test files?
- New public interfaces (functions, classes, endpoints visible in the diff) — are they documented or exported?
- New dependencies added — are they version-constrained?
- New configuration keys — is there a corresponding example/default in env templates or config samples?

**Classify as:**
- **Concern** for missing tests or missing config examples
- **Info** for missing docs (unless the project has strict doc requirements)

## 4. Version Coherence

**What:** The nature of changes implies a version bump that hasn't happened.

**How to detect:**
- Cross-reference the ticket type/branch prefix with version files from ecosystem output
- If changes are a new feature (`feat` type, branch starts with `feat/`, ticket is a feature) — check if any version file shows a minor/major bump in the diff
- If changes are a fix — check for patch bump
- If dependencies were added/updated — check if lockfile and version file are consistent

**Classify as:**
- **Concern** if a feature or breaking change has no version bump
- **Info** for fixes without patch bumps (some projects don't bump for every fix)

## 5. Scope Drift

**What:** Changes that don't relate to the branch name, ticket description, or stated purpose. Unrelated formatting, refactoring, or cleanup mixed with feature work.

**How to detect:**
- Compare the semantic intent of the branch name and ticket (if available) against the full diff
- Look for files changed that are in completely different modules/directories than the primary change
- Look for formatting-only changes (whitespace, import ordering) in files not otherwise modified by the feature
- Check if the diff touches test files for unrelated modules

**Classify as:**
- **Question** if significant unrelated changes are present — ask if they should be in a separate branch
- **Info** for minor incidental cleanup (e.g., fixing a typo noticed while editing a file)

## 6. Dead Artifacts

**What:** After the branch's deletions/removals, some references to the removed things still exist.

**How to detect:**
- From deleted files/symbols in the diff: grep the codebase for references
- Look for config entries, environment variables, feature flags that reference removed functionality
- Check import statements across the project for removed modules
- Look for documentation references to removed features

**Classify as:**
- **Concern** if code references remain (will cause runtime errors)
- **Info** if only documentation references remain

## 7. Symmetry Violations

**What:** Paired constructs where only one side was changed. Most codebases have paired operations that should stay in sync.

**How to detect:**
- In the diff: look for one-sided changes to pairs like:
  - setup / teardown
  - open / close
  - subscribe / unsubscribe
  - create / delete (API endpoints)
  - serialize / deserialize
  - encode / decode
  - migration up / down
  - mount / unmount
  - register / deregister
- Check if a new resource acquisition (file handle, connection, lock) has a corresponding release

**Classify as:**
- **Concern** for missing migration down, missing resource cleanup
- **Info** for intentionally one-sided changes (e.g., adding a new endpoint without a delete endpoint is often fine)

## Classification Summary

| Level | Meaning | Action |
|-------|---------|--------|
| **Question** | Needs user clarification before squashing | Present and wait for answer |
| **Concern** | Likely issue, recommend addressing | Present and recommend fix |
| **Info** | Worth noting, probably fine | Include in output for awareness |
