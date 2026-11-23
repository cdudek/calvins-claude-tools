# A project across several repos

One project can touch several repositories (an app, a design-system package, an API). The goal
binds to its start repo, and `pr-gate.sh` blocks pushes and PRs in any other repo while a goal is
active. Every repo also needs its own runner records. A project that ignored this invented
hand-offs and ran `/goal clear`. Use this pattern instead; it never needs a `/goal clear`.

## The pattern

1. **One start repo owns the goal.** Run the whole change from it: intent, plan, the one approval,
   the one `/goal`. The other repos are worked on from that session, never from a second goal.
2. **A dependency repo is milestone M-first.** A repo the others consume (a design-system
   package, a shared client) is the first milestone of the plan. Build it in its own project
   worktree (`wt switch -c <slug>` inside that repo, never `--path` or `--base`), on its own
   `milestone/<slug>-<n>` branch. Nothing in it is pushed while the goal runs.
3. **Consumers build against a packed tarball of a frozen commit.** When the dependency milestone
   passes its gate, freeze its head sha, pack it (`npm pack` or `pnpm pack`, `uv build`) and give the
   consumer that file. The consumer's builders never see the other repo's source and never need its
   registry. The tarball path and the frozen sha go into the plan's "Dependency changes (owner paste
   blocks)" section, because builders never edit a manifest or lockfile.
4. **Every release PR in another repo happens at the project end.** Only the start repo pushes
   while the goal is active. When the goal prints `GOAL <id> DONE`, the goal is finished and
   `pr-gate.sh` no longer binds the session: push and open each other repo's one PR then, one repo
   at a time, dependency repo first. The consumer then swaps the tarball for the published version
   (below) in the consumer's own last commit.
5. **One command writes the per-repo records.** Each repo's gate needs its own change folder and
   lock. Under the approved plan, run from the start repo:

   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/sdlc_status.py repo-records <id> --repo <path-to-other-repo>
   ```

   It copies `decisions.json`, `facts.md`, `plan.md` and `done.json` into that repo's change
   folder of the same id, then runs the plugin's own gate (`python3 -E -s`, that repo as the working
   directory; no script of that repo is ever executed) with `approve`, which writes `state/lock.json`. It refuses an unapproved source, an unadopted target, a different existing
   record and a folder that is already locked. Never write those files or a lock by hand.
6. **Each repo's project gate runs before its push.** In every repo, `verify_gate.py milestone <id>`
   (and the project gate when the project has a branch) must print `VERIFY PASS` on the head that
   is pushed. Run it from that repo's own worktree, then push and open its PR. A repo whose gate has
   not passed is not pushed.

## Dependency changes are owner steps

`codex-build.sh` rejects any edit of a manifest or lockfile, and repos say a human adds packages.
So a plan never gives an install to a builder. It lists the commands in "Dependency changes (owner
paste blocks)"; the owner pastes them and commits the manifest and lockfile before the feature
row starts. `verify_gate.py lint` flags a feature row that adds a package without that section.

## The packed tarball, and the swap to the published version

Local dependency repo, the consumer's owner block:

```bash
# in the dependency repo, at the frozen commit <sha>
pnpm pack --pack-destination ../tarballs
# in the consumer
pnpm add ../tarballs/<name>-<version>.tgz
```

Commit the manifest and lockfile with the tarball reference. The tarball itself is not committed
to the consumer; the owner keeps it next to the repos, and the plan names its sha.

After the dependency repo's PR merges and the package is published, the last block swaps it:

```bash
pnpm add <name>@<published version>
```

Commit the manifest and lockfile, then rerun the consumer's gate before its push. A published
version that differs from the frozen commit is a new milestone, not a quiet swap.
