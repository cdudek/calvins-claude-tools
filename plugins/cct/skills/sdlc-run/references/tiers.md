# Ship / Show / Ask by blast radius

Rouan Wilsenach's Ship/Show/Ask (<https://martinfowler.com/articles/ship-show-ask.html>),
decided by path, not by feel. `.github/tiers.json` is the one source; a PR is as risky
as its riskiest file. A repo with one owner sets `sdlc.json` `tiers: false` and turns all of
this off: every PR auto-merges on green.

## Only the PR into the default branch is tiered

The tiers answer **"who must look before this reaches the trunk"**. A feature PR into
`milestone/*`, and a milestone PR into `project/*`, reach nothing — they are interior merges
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
| **ask** | migrations / schema, integrations that write to real systems, `k8s/**`, `.github/**`, dependency manifests + lockfiles, `REVIEW.md`, `sdlc.json`, `.claude/settings.json`, `.claude/hooks/**` | writes to a CRM, mailbox or billing account; cluster or secret wiring; supply chain; the rules the agents run under | a code owner **before** merge; with no co-owner, a human merges by hand |
| **show** | `src/**`, `tests/**`, `e2e/**`, `scripts/**` | a bug ships behind CI, e2e and the milestone review | the co-owner **after** merge (`vars.SDLC_COOWNER` is requested; optional Slack notice) |
| **ship** | docs, changes, designs, skills, `CLAUDE.md` | nothing runs differently | nobody |

Milestone and project PRs merge with a merge commit, everything else squashes.
`show` and `ship` auto-merge on green, armed with the **App token**, never
`GITHUB_TOKEN` — a push by `GITHUB_TOKEN` triggers no workflows, so master would land
with no CI run and no deploy (omr-automations #168, #170). The arm job has no checkout:
the App token is a bypass identity and must never be minted where PR-authored code has
run. `ask` never auto-merges. Bot PRs are `ship`.

## CODEOWNERS

`require_code_owner_review` is the only GitHub rule that is path-scoped, so it is the
native enforcement for `ask`. It only helps with two people: the author cannot approve
their own PR, so a single owner turns every `ask` PR into a logged admin bypass. Hence:
`adopt` generates `CODEOWNERS` from `sdlc.json` `codeowners` × the `ask` globs, only when
at least one login is named, and the guardrail test keeps the two in step. One list of
logins to maintain; the file is output.

## Ruleset settings — learned on the first ship PR

| Setting | Value | Why |
|---|---|---|
| `required_status_checks` | CI | `merge-gate` went with the CI review in 3.7.0; drop it from an older ruleset |
| `strict_required_status_checks_policy` | false | every merge is followed by an image-bump PR; strict makes every other open PR `BEHIND`, and auto-merge never rebases |
| `required_review_thread_resolution` | false | a human's nits are advisory; blocking findings are fixed before the push |
| `require_code_owner_review` | only with codeowners | see above |
| bypass actor | the App, `pull_request` mode | the image-bump PR touches `k8s/**` (ask) and must merge unattended; a human editing the same file still needs an owner |

What replaces strict: deploy triggers on `workflow_run` after CI succeeds on master, so a
PR green on a stale base never ships an image.
