---
type: analyze
change: 2026-11-18-gate-loops
created: 2026-11-18
---

# Analyze: the gate hooks stop looping

## Coverage

| Ask | Facts | Tags | Plan row |
|---|---|---|---|
| A1 record each block in a per-session state file | F9, N1 | @F9, @N1 | 3 |
| A2 second identical block becomes a stop with hook, state, one command, no retry | F10, F11, F13 | @F10, @F11, @F13 | 3 |
| A3 test replays two identical blocks | F12 | @F12 | 3 |
| A4 finished pushes blocked; "/goal clear" had no effect | F1, F2, F5, F10 | @F1, @F2, @F5, @F10 | 1, 3 |
| A5 port gate-fixes: failed goal, clear, off switch, one helper | F1, F2, F3, F4 | @F1, @F2, @F3, @F4 | 1 |
| A5 port gate-fixes: redirects, repo scope, session prExceptions | F6, F7, F8 | @F6, @F7, @F8 | 2 |
| A5 goal text accepts merged PR, 4-hour stop | none (out of scope, true since 3.10.0) | none | none |
| Plan row 4 release (changelog, versions, docs, adopt refresh) | none | none | 4 |

## Findings

| ID | Severity | Pass | Where | Finding | Status |
|---|---|---|---|---|---|
| X1 | HIGH | underspecification | facts F1, F2, F5; plan Risks | No fact states the transcript shape of a failed goal or `/goal clear`. Builders may not see the seed, so tests cannot pin it. | fixed |
| X2 | HIGH | coverage | plan Risks; facts | The plan adds a `gate-bash.sh` block on an agent writing `sdlc-goal-off`. No ask, fact or tag covers it, and `gate-bash.sh` only reads `sdlc.json` `blocked`. | fixed |
| X3 | HIGH | coverage | plan Risks; facts | "Unreadable transcript keeps today's fail-open warning" has no fact. Today the three hooks differ: chain-gate warns, pr-gate says false, verify-on-stop runs verify. | fixed |
| X4 | HIGH | rules alignment | plan Files that change; `adopt.py` lines 1048-1061 | `adopt` writes `*.sh` only and the gitignore fix allows `.claude/hooks/*.sh` only. A global ignore of `.claude/*` would hide the new `.py` helpers in adopted repos. | fixed |
| X5 | MEDIUM | coverage | plan Files that change | The version lives in `SKILL.md` frontmatter (3.15.1) and `sdlc_version.py` reads it. The plan lists the changelog and `plugin.json` but not `SKILL.md`, which also breaks "nothing outside the list". | fixed |
| X6 | MEDIUM | inconsistency | plan Risks | The risk row cites a `test_hook_spawns` limit that exists in no test file in this repo. | fixed |
| X7 | MEDIUM | inconsistency | facts F10 vs F11 | F10 says "repeats a block"; F11 adds "in one session". The repeat scope should read the same in both, and match the per-session file in the assumptions. | fixed |
| X8 | MEDIUM | ambiguity | facts F11 | "the state" it names is vague: the block-state file, the goal state or the transcript. A2 says "the state it read". | fixed |
| X9 | MEDIUM | ambiguity | facts Assumptions | "Other blocks repeat their first command" gives no owner command for the `gate-bash.sh` and `chain-gate.sh` blocks. F13 requires one. | fixed |
| X10 | MEDIUM | underspecification | facts F5 | "Set and not ended" is not tied to a transcript entry. Today it is the last `goal_status` with `met: false`; F1 and F2 do not say how they override it. | fixed |
| X11 | MEDIUM | underspecification | facts F7, F8 | "The session's own repo" and "session's repo" are not defined. `pr-gate.sh` has `SDLC_ROOT` and per-command `Repo`; no fact says which wins. | fixed |
| X12 | MEDIUM | coverage | plan row 4 | The release row (changelog 3.16.0, docs off switch, `adopt` second-run no-diff) has no fact and no tag. It is proven only by the plan's order step. | fixed |
| X13 | MEDIUM | underspecification | facts N1 | N1 has no screen, state or tag line like F1 to F13. Done.json tags it `@N1`, but the fact text omits it. | fixed |
| X14 | LOW | inconsistency | facts F12, F13 | F13 is listed before F12 under "A repeated block says stop". Verification line says `_F9` to `_F13`. Order only. | fixed |
| X15 | LOW | inconsistency | facts F4 vs plan | F4 names three hooks, the plan also edits `gate-bash.sh` for block state only. Wording of "all three hooks" in F9 to F13 is clear, but F4 is easy to misread as covering `gate-bash.sh`. | fixed |
| X16 | LOW | ambiguity | facts Verification | `scripts/run-plugin-tests.sh` is named, but nothing says the new `test_*.py` in `scripts/` are discovered by it. | fixed |
