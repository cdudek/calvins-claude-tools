# The playbook, and where each play lives here

Verification and every push follow the [local-first contract](local-first.md); read it before running checks or preparing a push.

Anthropic, *The AI-Native SDLC Playbook* — <https://academy.claude.com/courses/ai-native-sdlc-playbook>
(blog: <https://claude.com/blog/the-ai-native-sdlc-playbook>). Six stages, twelve plays; each
stage ends by committing an artifact, the commit starts the next stage, humans sit at gates.

| Stage | Play | What implements it now | Gate | Leading metric | Lagging metric |
|---|---|---|---|---|---|
| Plan | Capture as intent.md | `intent.md` with `## Asks`, plus `decisions.json` for ticket, intent, design, size and kind | originator or named reviewer | conversation → committed intent | asks dropped after commit |
| Design | Requirements and design | `spec/` via `cct:ux-design-run`, `cct:ux-rules-validate spec`, `facts.md` citing asks and screens, `cct:ux-spec-validate spec` | owner reads `spec/validation.md`; facts and validation approved together | intent commit → approved spec | rework because screen/state was missing |
| Build | Plan mode default | `plan.md` visible slices, proof per slice, `planGate` owner or allowed self-check | plan gate | share merged first pass | merged diff matches plan |
| Build | CLAUDE.md | generated `CLAUDE.md` section plus repo rules | reviewed like code | repeated mistakes recorded | time to first merged PR for a new joiner |
| Build | Skills | this kit, especially `cct:sdlc-run` and the cct UX skills | policy owner | policy change → merged skill | review findings citing policy → 0 |
| Build | Hooks as guardrails · parallel sessions | `.claude/hooks/*`, worktrees, `prototypeDirs` allowance | deterministic hooks | concurrent sessions while quality holds | merged changes per engineer vs rework |
| Build | Build subagents | `cct:test-behavior-verifier` for M/L: changed behaviour plus two nearest flows, report only | PR evidence, no approval power | verifier pass on first run | escaped neighbouring-flow regressions |
| Test | Feedback loop | `verifyStop`, `cct:ux-spec-validate build`, locked bug tests, full `verify` before PR | hook and PR checks | stop checks stay fast | CI success and change failure rate |
| Test | Continuous evals in CI | not yet — needs 20+ collected tasks | pass-rate threshold | eval pass rate | regressions caught in CI vs prod |
| Deploy | AI in PR review | `review-code-run` (Claude and Codex, reading `REVIEW.md`) once per milestone, locally, before the push; no CI review since 3.7.0 | the milestone gate | time to first review | defects caught at merge vs escaped |
| Deploy | Hooks as approval gates · CI/CD | `gate-bash.sh`, `chain-gate.sh`, Ship / Show / Ask, CI triage | tiers and ruleset | pipeline failures triaged without paging | DORA |
| Maintain | Closing the loop | `sdlc.json.feedback` files become Stage 1.3 asks in the next change | owner triage | feedback → ask table | findings that become merged fixes |

Rules worth quoting at the gates:

- "Requirements and design collapse into one session ... guided by the organization's skills for
  brand, security, compliance, and UX."
- Areas of concern are flagged "especially where you cannot satisfy contradicting policies."
- For front-end work Claude "mocks the design up ... iterates on the mock."
- "The product owner reviews that spec, but doesn't write it."
- "Screenshot matches the attached mock ... two or three rounds."
- "Write the failing test first; confirm it fails for the expected reason; commit the test; ask
  Claude to make it pass without editing the test."
- Hooks are "fast and scoped to the file that changed. Heavier checks such as the full test suite
  belong at the commit or the PR."
- Review: Important vs Nit, at most five nits, nothing CI already enforces; "the agent has no
  approval power."

Every artifact here carries `created:` and lands in git, so metrics are computable from
timestamps, PR history and CI later.

## Where the milestone process (2026-10-09) departs from the playbook

- The product owner still reviews and does not write: the engineer confirms the drafted intent,
  then the UX plan, facts and plan in one gate. There is no separate design gate.
- "Two or three rounds" against the mock becomes one validation pass in the UX plan and one fix
  round per milestone, because a review after every change looped without end.
- Hooks stay fast and file-scoped. The feature checks run on what the feature touched; the full
  suite and the heavy checks run once per milestone, on the milestone diff.
