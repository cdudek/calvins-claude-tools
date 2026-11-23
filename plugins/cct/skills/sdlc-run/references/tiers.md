# Ship / Show / Ask by blast radius

Rouan Wilsenach's Ship/Show/Ask (<https://martinfowler.com/articles/ship-show-ask.html>),
decided by path, not by feel. `.github/tiers.json` is the one source; a PR is as risky
as its riskiest file. A repo with one owner sets `sdlc.json` `tiers: false` and turns all of
this off: every PR auto-merges on green.

## Only the PR into the default branch is tiered

The tiers answer **"who must look before this reaches the trunk"**. A milestone PR
into `project/*` reaches nothing — they are interior merges
inside one change, and they auto-merge on their checks alone. Tiering them would ask a code
owner to approve the same code two or three times on its way up, and the `ask` paths
(`k8s/**`, `.github/**`, migrations) are exactly the ones a multi-milestone project touches
early and often.

The workflow enforces this itself rather than trusting the chain to drive it:
`ship-show-ask.yml`'s `tier` job requires
`github.event.pull_request.base.ref == github.event.repository.default_branch`. So a PR
opened by hand into `milestone/*` is untiered too, and the rule cannot be bypassed by not
using the skill. Nothing reviews code in CI (3.7.0): the review runs once, locally, at the
milestone close.

| Tier | Typical paths | Worst case if wrong | Who looks |
|---|---|---|---|
| **ask** | migrations / schema, integrations that write to real systems, `k8s/**`, `.github/**`, dependency manifests + lockfiles, `REVIEW.md`, `sdlc.json`, `.claude/settings.json`, `.claude/hooks/**` | writes to a CRM, mailbox or billing account; cluster or secret wiring; supply chain; the rules the agents run under | never auto-merged; a human looks **before** merge |
| **show** | `src/**`, `tests/**`, `e2e/**`, `scripts/**` | a bug ships behind CI, e2e and the milestone review | the co-owner **after** merge (optional Slack notice; nothing requests them) |
| **ship** | docs, changes, designs, skills, `CLAUDE.md` | nothing runs differently | nobody |

Milestone and project PRs merge with a merge commit, everything else squashes.
`show` and `ship` auto-merge on green, armed with the **App token**, never
`GITHUB_TOKEN` — a push by `GITHUB_TOKEN` triggers no workflows, so master would land
with no CI run and no deploy. The arm job has no checkout:
the App token is a bypass identity and must never be minted where PR-authored code has
run. `ask` never auto-merges. Bot PRs are `ship`.

**A bot PR has no merger in this workflow.** It is labelled `ship`, but the arm job serves human PRs
only (the App token is a bypass identity and a bot PR's workflow run cannot read the App secrets), so
green checks alone merge nothing. The `tier` job therefore adds the `needs-merge` label and prints a
notice. Name the merger once per repo: a person merges `needs-merge` PRs on green, or the repo runs its
own bot-merge automation (for example the bot's native auto-merge, enabled on its own PRs). A repo that
has neither has bot PRs that wait forever; say which one it is in `docs/sdlc.md`, "Repo-specific".

## Reviewers

The kit has no code-owner step: adopt writes no CODEOWNERS file, and neither the workflow nor
the classifier requests a review or reads one. The tier labels are the whole mechanism; who must
look at an `ask` PR is the repo's own ruleset.

## Ruleset settings — learned on the first ship PR

| Setting | Value | Why |
|---|---|---|
| `required_status_checks` | CI | `merge-gate` went with the CI review in 3.7.0; drop it from an older ruleset |
| `strict_required_status_checks_policy` | false | every merge is followed by an image-bump PR; strict makes every other open PR `BEHIND`, and auto-merge never rebases |
| `required_review_thread_resolution` | false | a human's nits are advisory; blocking findings are fixed before the push |
| bypass actor | the App, `pull_request` mode | the image-bump PR touches `k8s/**` (ask) and must merge unattended; a human editing the same file still needs an owner |

What replaces strict: deploy triggers on `workflow_run` after CI succeeds on master, so a
PR green on a stale base never ships an image.
