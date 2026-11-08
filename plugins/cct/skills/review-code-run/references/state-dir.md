# State dir

Two dirs hold a review's state:

| Dir | Holds | Lifetime |
|---|---|---|
| `$STATE_BASE` | cross-run files: `discuss.json` | one review target (a PR, a branch, a file set) |
| `$STATE_DIR` = `$STATE_BASE/rev-<revid>` | every artifact of one run: `INPUT.md`, the diff, `findings.json`, `verdicts.json`, `verdict-<id>.json`, `codex-findings.json`, `dimensions*.json`, `dim-*.json` | one reviewed revision |

A new commit or a changed file set gives a new `$STATE_DIR`. A `skip-if-exists` check therefore only ever resumes the same revision.

`codex-findings.json` is absent when Codex was `off`, unavailable or failed. It is **present with an empty list** when Codex ran and found nothing.

A resume keeps the reviewer output but not always the merge: each lane runs `state-codex-check.sh` first, which removes `findings.json` and the verdicts when they disagree with the current `$CODEX` (Codex findings cached but `--no-codex` now; Claude-only cached but `--codex` now).

## 1. Sync with the remote — `changes` mode only

`pr` mode already fetched and entered the branch. `files` mode has no remote. Skip this step for both.

Run `git rev-parse --abbrev-ref --symbolic-full-name @{u}`. No upstream → skip.

Set `U` = that upstream, `B` = `git branch --show-current`, `R` = `git config --get branch."$B".remote`.
Continue only if `U` equals `$R/$B` — the branch's own remote copy. A shared base like `origin/main` cannot make the review stale, so skip.

`git fetch`, then compare `HEAD` with `@{u}`:

| State | Do |
|---|---|
| upstream ahead | `git merge --ff-only @{u}` |
| diverged | **Stop.** Tell the user to reconcile first. |
| equal or local ahead | nothing |

## 2. Create the dirs

```sh
bash "${CLAUDE_SKILL_DIR}/scripts/state-dir.sh" <mode> <lane> <key> [files-list]
```

| Mode | `<key>` | `[files-list]` |
|---|---|---|
| `pr` | `$PR_NUMBER` | — |
| `changes` | the branch name | — |
| `files` | anything | path to a file with `$FILES`, one path per line |

Read `- state_base:` as `$STATE_BASE` and `- state_dir:` as `$STATE_DIR`. The script makes the dirs and keeps one prior `rev-*` dir for the fix loop's repeat check.

Never `mkdir` these dirs by hand. To force a fresh review of the same revision, delete its `rev-<revid>` dir.
