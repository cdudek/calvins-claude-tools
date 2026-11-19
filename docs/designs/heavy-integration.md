---
title: Heavy-job queue and fail-fast: what the core stream wires in
type: design
status: active
created: 2026-11-19
tags: [sdlc-run, heavy, integration]
read_when: when you wire the gate, the hooks or the status code to the heavy-job queue
---

# Heavy-job queue and fail-fast: what the core stream wires in

**Status (3.21.0):** every item below is wired. Gate: `queued()` and the `preflight` evidence check in `verify_gate.py`; hooks: `pr-gate.sh`, `gate-bash.sh`, `chain-gate.sh`, `verify-on-stop.sh`, `helper-guard.sh`; status: `sdlc_status.py` and `status.sh`. The sections keep the reasoning.

The queue, the database helpers, the evidence ledger and the preflight are new scripts
(`templates/scripts/heavy.py`, `db.py`, `evidence.py`, `preflight.py`) with docs in
`references/heavy-work.md`. This note lists what needs a change in a file the heavy stream did
not touch. Line numbers are those of the branch this was written on; search for the quoted code.

## Gate and hooks

1. **Done (aee5cec).** **`verify_gate.py` takes a slot for the milestone run.** Call site: the check loop, the
   `proc = subprocess.run(cmd, shell=True, ...)` in `run()` (about line 697). Wrap each configured
   check command with `python3 scripts/heavy.py run --auto --` (it takes a slot only for a heavy
   command and passes light ones straight through), or take one slot around the whole milestone
   run. Either is safe: a command started under a held slot passes through (`SDLC_HEAVY_HOLDER`),
   so a gate run by the close builder inside `heavy.py run -- verify_gate.py milestone` does not
   queue behind itself.
2. **Done (aee5cec for the heavy slot deadline, ef08aae for `checkTimeout` and the process-group kill).** **The same loop has no deadline (process map L1).** `subprocess.run` there has no `timeout`.
   Use `heavy.runTimeout` from `sdlc.json` (default 3600 s) as the check timeout, kill the process
   group, and report `check=<name> timeout` as a handoff with the log. `heavy.py run` already
   enforces it for anything run through the queue.
3. **Done (aee5cec: offline preflight first; 0074aa4: evidence checks before the suites).** **Evidence shape before suites.** `owner-marks` and `ux-visual-N` are appended after the cost
   sort (`ordered`, about line 479), so they run behind full E2E. Run the offline checks first
   (marks shape, visual-run presence, `preflight.py`) before the first heavy command. The stage text
   already tells the supervisor this order; the gate should enforce it.
4. **Done (b69de86).** **`pr-gate.sh` (D4, runtime half).** `adopt` and `preflight.py` already reject feature-PR
   delivery with local milestones. The hook still forbids the publication that feature PRs need;
   if the pair is ever allowed, the hook is where the two policies would disagree.
5. **Done (b69de86).** **`gate-bash.sh` (S4, runtime half).** A `blocked[]` rule with an empty `message` prints an empty
   owner action (`gate-bash.sh` lines 23-26 and `block_state.py` lines 62-68). `preflight.py` now
   flags new ones; the hook should refuse to apply a rule with no message and name the config owner.
6. **Done (b69de86).** **`chain-gate.sh` (F3).** Dispatch now passes `Repo`, `Worktree`, `Change`, `Base` and the builder
   verifies them (agent definition and stages.md "Dispatch names the workspace"). The hook still
   picks the change by the first slug found in the branch name (lines 202-216, 338-345) and treats
   any truthy `protectedEdit` as permission (lines 248-256). Bind the authorization to
   change, path and revision and consume it; read the change id from the dispatch when given.
7. **Done (b69de86 writes the failed status, cfdf803 reads it in status).** **`verify-on-stop.sh` (F5).** The second stop on an unchanged failing tree exits 0 (lines 64-87).
   Keep that anti-recursion, and write a durable `failed` status next to it that `sdlc_status.py`
   reads, so "stopped" is never read as "verified".
8. **Done (cfdf803).** **`sdlc_status.py` (heavy).** Optional: print `heavy.py status` (who holds a slot) in the status
   output, so a waiting helper is visible.

## Helper-in-the-main-folder guard (hook wiring)

**Done (b590fc7):** `helper-guard.sh` and its registration in `adopt.py`; the `agent_id` field is read as documented.

`heavy.py guard-main --hook` reads a PreToolUse payload on stdin and exits 2 only for a subagent's
call (`agent_id` present) in the main working folder. Register it as a second `PreToolUse` `Bash`
command beside `gate-bash.sh`. The kit's registration list is in `adopt.py` (about line 1048,
`("PreToolUse", "Bash", "gate-bash.sh", 5)`) and takes script names under `.claude/hooks/`, so the
clean wiring is a one-line wrapper `templates/hooks/helper-guard.sh`
(`exec python3 "$(dirname "$0")/../../scripts/heavy.py" guard-main --hook`) plus one list entry.
It was not added here because a new hook file changes the `audit` hook inventory and the adopt
hook tests, which the core stream owns. The `agent_id` payload field is the Claude Code field for
subagent calls; confirm it on the installed version before enabling.

## After the three streams merge

- **Done at release.** `kitTemplates` in `sdlc.json` is the hash of every file under `templates/`; it changes with this
  stream and with the others. Recompute it once after the merge: `python3 plugins/cct/skills/sdlc-run/scripts/adopt.py --templates-hash`.
- **Done (e8b0466, 0ec0083).** `scripts/heavy.py`, `db.py`, `evidence.py` and `preflight.py` in the repo root are byte copies of
  the templates (`cmp` them after any edit).
- **Done at release.** `docs/designs/INDEX.md` is generated: run `python3 scripts/design_index.py write` after merging.
