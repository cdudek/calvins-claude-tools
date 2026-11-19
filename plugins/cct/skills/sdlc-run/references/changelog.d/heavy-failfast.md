# Heavy work and fail-fast (notes for the release entry)

**New scripts, installed by `adopt` into `scripts/`** (stdlib only, so they run in CI and in `/goal`):

- `heavy.py`: the heavy-job queue. One heavy job at a time per machine by default (`heavy.slots`).
  First come, first served, a dead process never blocks the line, a waiter is told who holds the
  slot, waits and runs have deadlines, ports come from the slot, `submit` and `wait` let a helper
  hand in a job and stop. `guard-main` refuses helper commands in the main working folder.
- `db.py`: `test` keeps one local Postgres container with a migrated template and gives each job a
  private copy in under a second; `dev` connects a developer to their own cloud database through the
  auth proxy with their own identity, creates it once if missing, and runs migrations. Provider
  neutral: every command comes from `sdlc.json` `db`.
- `evidence.py`: one evidence file per screen; "changed since capture" is checked per text key.
- `preflight.py`: checks tools, sign-in and Docker once and prints one fix line per failure; also
  refuses feature PRs with local milestones and a `blocked[]` rule that has no message.

**Docs and process.**

- New `references/heavy-work.md`; one new `docs-sdlc.md` key row (`heavy`, `db`, `preflight`).
- Stage 3 runs the lint before the checklist reviewer (the numbering said the opposite). The
  feature PR body is linted before `git-pr-run`.
- The full test suite has one owner, the milestone gate. Nothing starts it early or runs it again
  before the gate. Read-only review still starts while the last feature builds.
- Stage 6 runs offline checks (preflight, lint, marks shape, validation and findings shape, stale
  screen evidence) before any browser or suite starts.
- Dispatch passes `Repo`, `Worktree`, `Change` and `Base`; the builder checks them before any edit
  and stops in the main working folder. The change is never chosen from a branch name.
- Builders: at most 4 at once, inside about 6 helpers; heavy slots are counted separately.
  Builders no longer wait in the foreground: heavy jobs go through the queue or are submitted.
- Codex builders run light checks only (the sandbox cannot write the queue); the supervisor runs
  their heavy checks outside it.
- The builder agent may run `heavy.py`, `db.py`, `evidence.py` and `preflight.py`.

**Contradictions fixed.** `local-first.md` and `SKILL.md` said nothing local blocks a push while
`pr-gate.sh` requires `VERIFY PASS milestone` (now: it enforces branch order, not quality). `SKILL.md`
said "never re-lock" while stages said owner-added scope re-locks (now: re-lock only added scope).
The machine-wide E2E lock in `test-e2e-policy` is this queue. Feature PR step 9 no longer says the
next feature starts only on merge (independent rows start at step 8).

**CI example (`templates/ci/github-actions.yml`).** A `preflight` job gates every expensive job; lint
and build failures skip the E2E shards; one failing shard cancels the rest; with
`ciCommands.buildOutput` set the production build runs once and the shards download it. Executable
hooks (`.claude/hooks/*`, `.claude/settings.json`) are code: `all` is checked before `docs`, so a
hook-only PR runs every step. Fixtures for hook-only changes are in `test_ci_changes.sh`.

**Ship / Show / Ask (S9).** A bot PR is labelled `ship` but never armed. The tier job now adds a
`needs-merge` label and prints a notice, and `tiers.md` says who merges it.

**Manual for a repo.** Optional: set `heavy`, `db` and `preflight` in `sdlc.json`; set
`ciCommands.buildOutput` to share one build with the E2E shards; add `needs-merge` handling to the
repo's own bot-merge automation. Nothing is required.

**For the release.** Recompute `kitTemplates` (`adopt.py --templates-hash`) after the three streams
merge. What the gate, hooks and status code must still do is in `docs/designs/heavy-integration.md`.
Process-map items: D4 and S4 (preflight plus the existing adopt refusal; runtime halves in the
integration note), S9 (done), L1 (queue deadlines done; gate retry counters in the note), F3
(dispatch identity done; hook binding in the note), F5 (in the note).
