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

**Wired into the gate, hooks and status (group B, plain words).**

- **Gate.** Every check of the milestone gate runs through `heavy.py run --auto`: a heavy one waits for a slot, a light one just runs, a gate already inside a slot passes straight through. The check's own timeout (`checkTimeout` or `timeout`) still kills the process group. A slot that never frees is a handoff (`VERIFY BLOCKED reason=env`) that names who holds it. With `preflight` in `sdlc.json`, the tool and sign-in check runs before the first heavy command.
- **Hooks.** A feature-PR repo with local milestones is refused with the two ways out. A `blocked[]` rule with no message still refuses, and says who owns `sdlc.json` and what to add. `protectedEdit` can name one file and one lock, is spent by the edit it allows, and a ledger the hook cannot read denies. The change comes from the branch; a dispatch pointer (`<git dir>/sdlc-change` or `SDLC_CHANGE`) only fills in when the branch names none, and a pointer that disagrees with the branch refuses. The prototype exemption ends at the lock. A failed stop leaves `sdlc-stop-status.json` in the git dir; `status` prints it, so a stop is never read as a pass.
- **`helper-guard.sh`.** New PreToolUse hook, registered by `adopt`. It refuses only a subagent's heavy command that is not run through `heavy.py`. The owner's session is never refused.
- **Status.** `status` shows a failed stop and who holds or waits for a heavy slot. It runs the plugin's own `heavy.py`, never a copy in the repo.
- **Plan template.** `Done` and the turn caps are rendered for the delivery mode: one go shows the milestone gate and `goal.runTurns`; feature PRs add the feature gate and `goal.featureTurns` and `goal.milestoneTurns`.
- **One list.** A test fails when a preset's milestone checks and its CI `lint` and `unit` commands differ. The python default `unit` now matches the milestone gate.
- **CI example.** `deploy` (the paths changed) and `deploy_ok` (the event: not a fork, not a draft) are separate, and both must be true. A push to the default branch lists its own files, so a merged docs-only PR runs nothing again; an unknown range runs everything. The web-nextjs-cloud-run blueprint has the same `preflight` and `spec` jobs.
- **Two risks from the layout-4 work.** `approve` and the milestone gate hand off an unresolvable parent branch (`BLOCKED reason=env`, with a fix line) instead of failing the change. `marks.py` imports `spec.py` only for a layout-4 change, so a repo with an older layout and no `spec.py` still runs it.
