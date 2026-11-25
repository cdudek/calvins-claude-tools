# Research behind the rules

Why each rule exists. UNVERIFIED means the research could not open the primary source; it is repeated here as the research stated it.

## Agentic engineering and factories
- **Lit, not dark.** The owner approves intent, requirements, plan and boards once, never raw diffs; the gallery is reviewed once from the release PR. StrongDM's dark factory forbids human code and human review; Willison's objection is cost (about $20k a month per engineer) and Stanford's is shared blind spots between builder and judge. https://factory.strongdm.ai/ https://simonwillison.net/2026/Feb/7/software-factory/ https://law.stanford.edu/2026/02/08/built-by-agents-tested-by-agents-trusted-by-whom/
- **Verification is the constraint.** "Verification, not generation, is the real constraint": cheap checks first, one expensive gate decides. https://addyosmani.com/blog/software-factories/
- **Humans own architecture and correctness.** Agents run tools in a loop; unreviewed prototype output is vibe coding. https://simonwillison.net/guides/agentic-engineering-patterns/what-is-agentic-engineering/ https://addyosmani.com/blog/agentic-engineering/ (the Karpathy quote that names the term is UNVERIFIED: https://thenewstack.io/vibe-coding-is-passe/)
- **Fix the harness, do not retry.** When the agent fails, add the missing capability; lint errors carry remediation text; recurring agents open small cleanup PRs (entropy). https://openai.com/index/harness-engineering/
- **Each worktree boots its own app.** Same source.
- **Comprehension debt.** Green tests with falling understanding; the verifier writes a two-line "what changed and why". https://addyosmani.com/blog/software-factories/
- **No digital twins.** Only worth it when a third-party service dominates failures; record/replay fixtures first. https://factory.strongdm.ai/
- **No independent defect data for no-review pipelines was found** (UNVERIFIED, advocacy only). https://tessl.io/patterns/agentic-development-workflow/dark-factory/

## Spec-driven development
- **Spec-anchored.** Three levels: spec-first, spec-anchored, spec-as-source. Most tools stop at spec-first; spec-as-source showed non-determinism. https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- **Living spec plus delta.** The OpenSpec model: ADDED requirements with scenarios; MODIFIED and REMOVED handling was UNVERIFIED on the page read. https://github.com/Fission-AI/OpenSpec
- **EARS.** Whether Kiro uses EARS is UNVERIFIED. https://kiro.dev/docs/specs/
- **Keep the spec light.** Kiro turned one small bug into 4 stories and 16 acceptance criteria; so a bug spec is a failing example plus expected result. https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html
- **What exists versus what changes.** A Spec Kit trial mistook research about existing classes for instructions to recreate them. Same source.
- **Holdout scenarios.** Stored outside the codebase so the builder cannot fit them; plain tests can be rewritten. https://factory.strongdm.ai/
- **One success and one rejection example.** The wrong intent passes every gate otherwise. https://github.com/github/spec-kit (flow); the rule is from the greenfield design notes.

## Plans and goals
- **The plan stands alone.** "An engineer who has never seen the conversation could implement the change from the plan alone"; commit it; update it in the same commit as any departure. https://claude.com/blog/the-ai-native-sdlc-playbook
- **Observable milestones.** Each has a validation command, expected output and recovery path. https://developers.openai.com/cookbook/articles/codex_exec_plans https://developers.openai.com/blog/run-long-horizon-tasks-with-codex
- **Progress log and resume state.** Timestamped progress, decisions, outcomes; resume from the log plus git. https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- **Parallel only on disjoint files.** Dependency waves and `[P]` marks. https://github.com/github/spec-kit/blob/main/templates/tasks-template.md https://kiro.dev/docs/specs/
- **Short goal line.** A small model judges the condition from the transcript only; it runs no tools; the limit is 4,000 characters. https://code.claude.com/docs/en/goal
- **Caps survive via the CLI.** A resume resets the goal's turn count; there is no built-in cap, so the condition carries a turn clause (soft) and the unattended run a computed `--max-turns` (hard; it counts coordinator turns only, not subagent steps; local probes, 2026-11-24; formula in goal-briefing.md). The owner rejected `--max-budget-usd` on 2026-11-24. Same source plus https://code.claude.com/docs/en/cli-reference
- **No facts document in the playbook.** The full playbook text (PDF, checked 2026-11-24) names intent.md, spec.md, plan.md, CLAUDE.md, REVIEW.md, bands.yaml and verifier.md. intent.md holds "what is wanted, why, and under which constraints", corrected by the owner; spec.md records flagged concerns. A facts file came from the earlier sdlc-run, not from Anthropic. https://assets.claude.com/5f640b0ae71b855ddd9989d43952da707f62866f.pdf
- **Background agents pause the check.** Evaluation is skipped while they run. https://code.claude.com/docs/en/goal
- **Auto mode.** It falls back to asking after three consecutive blocks. https://code.claude.com/docs/en/best-practices
- **Subagent worktrees branch from the default branch.** Builders start from the milestone branch explicitly. https://code.claude.com/docs/en/sub-agents
- **Terminal states.** SHIPPED, INCOMPLETE, BLOCKED; the cct incident of 11 November 2026 (goal never cleared after merge) is internal evidence, no URL.

## Pitfalls and guardrails
- **Test tampering.** o3 stubbed evaluators; a Go port deleted about 70% of its tests and said all pass; "please do not cheat" barely helped (80% to 70%). Hence `test-integrity.sh` and holdouts. https://metr.org/blog/2025-06-05-recent-reward-hacking https://typia.io/blog/ai-deleted-my-tests-and-said-all-tests-pass/
- **Done is an exit code.** "Claude said it was done and it wasn't quite." https://code.claude.com/docs/en/best-practices
- **Fresh session per milestone.** Context rot; the Chroma report detail is UNVERIFIED. https://research.trychroma.com/context-rot
- **Loop bounds.** Unbounded loops and a $47K run (single blog source). https://www.theregister.com/2026/01/27/ralph_wiggum_claude_loops/ https://dev.to/gabrielanhaia/the-agent-that-spent-47k-on-itself-an-autonomous-loop-postmortem-3313
- **Two attempts, no new evidence, stop.** Codex pitfalls rule 10 (pitfalls-codex/codex-pitfalls.md). https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
- **2 or 3 builders.** Cursor's shared-lock agents got the throughput of two or three out of 20; 16 compiler agents overwrote each other. https://cursor.com/blog/scaling-agents https://www.anthropic.com/research/building-c-compiler
- **Shared blocker fixed once.** Same compiler source.
- **Verifier independence.** Judges favour same-family output; use another model family for risky milestones. https://arxiv.org/abs/2508.06709v1
- **Counterexample first.** Greenfield design risk 2 (the greenfield design notes).
- **Run the real flow.** Agents marked features done on unit tests; browser checks found the bugs. https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- **Merge gate check.** Private GitHub Free repos lack branch protection; CODEOWNERS needs required review. https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- **One always-reported CI job.** A skipped job can report success; test its wiring with a failing and a docs-only change. https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks
- **Owner approves three short things.** Users approved about 93% of permission prompts (measures tool permissions, not PR review); human review rates fell in enterprise preprints (UNVERIFIED, summaries only). https://www.anthropic.com/research/how-we-contain-claude https://arxiv.org/pdf/2607.01904
- **Platform gates over custom gate code.** No study found (UNVERIFIED); the cct sdlc-run review counted 10,077 lines of runner. review-lean-gates-codex.md
- **Replay known-good and known-bad.** After a model, hook or gate change. https://claude.com/blog/the-ai-native-sdlc-playbook
- **Measure, not feel.** METR: 19% slower while believing 20% faster (early-2025, 16 developers). https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/

## UX
- **Design fidelity by vision at two widths.** Design2Code found missing elements and wrong layouts in generated pages. https://aclanthology.org/2025.naacl-long.199/
- **Perform the primary action.** A recording button toggled without capturing audio; visual checks missed it. https://www.anthropic.com/research/harness-design-long-running-apps
- **Supply the design frame and component names.** https://developers.figma.com/docs/figma-mcp-server/code-connect-integration/
- **Few, role-based E2E.** Vendor and practitioner sources only, no flake-rate study (UNVERIFIED as quantitative). https://www.augmentcode.com/guides/why-ai-coding-agents-fail-e2e-tests
- **No primary report on UI diverging from design** (UNVERIFIED); the per-screen check rests on the sources above.
- **The 30 Laws of UX, IA and navigation checks** come from the owner's rules (O), not from the research files.

## Single approval, grilling and review policy (2026-11-25)
- **Grill first.** Rounds of numbered questions, each with a recommended answer, until no decision is open; Spec Kit's clarify step and the grilling skill are the models. https://github.com/github/spec-kit https://github.com/mattpocock/skills
- **Intent before spec.** The playbook's intent.md holds what is wanted, why and under which constraints; the Shape Up pitch is the model for appetite and no-gos. https://basecamp.com/shapeup/1.5-chapter-06
- **Important versus Nit.** Review fails only on findings that break behaviour, leak data or break a policy; the rest is capped and never blocks (playbook, review section). https://assets.claude.com/5f640b0ae71b855ddd9989d43952da707f62866f.pdf
- **Bug as two commits.** The failing test lands first and is frozen; the fix may not change it (playbook, bug-fix section). Same PDF.
- **Numbers from git.** First-pass rate, plan revisions after approval and diff-matches-plan come from the progress log, not from feel. https://claude.com/blog/the-ai-native-sdlc-playbook
- **A stop is a grilling miss.** The first beta-milestone run (2026-11-24) stopped on five guest leaks, unprobed deferrals and tools found mid-run; internal evidence, no URL.
