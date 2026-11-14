# Verification for copied blueprints

Read the [single local-first contract](../skills/sdlc-run/references/local-first.md).
GitHub Actions required checks are the merge gate; nothing local gates a push or a PR.
Make the copied `ci.yml` a required check in the ruleset of the default branch.
Preserve cloud builds/deploys, eligible previews and scheduled work; do not repeat full CI
after merge. Run the full suite before pushing.
