# Verification for copied blueprints

Read the [single local-first contract](../skills/sdlc-run/references/local-first.md).
Implement the repo's `scripts/ci-local`, pre-push hook and real Decision4 validation;
require `local-ci` and `decision4` on the exact pushed head, never posted by hand.
The copied workflows are legacy examples: migrate their verification to the local gate
before enabling them in a new repository. Preserve cloud builds/deploys, eligible previews
and scheduled work; do not repeat full CI after merge. Run the full local suite before
pushing while adopting, and keep any existing required checks until replacements are applied.
