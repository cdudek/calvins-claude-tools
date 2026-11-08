# 0001. Skill taxonomy: family-prefixed names, a closed verb list, one owner per job

- Status: accepted (2026-11-08, Calvin Dudek)
- Replaces: the unprefixed names cct inherited from its sources
- Enforced by: `scripts/taxonomy.py` (rules and checks), run by `tests/test_plugin.py` against `plugins/cct/`; rule tests in `tests/test_taxonomy.py`

## Context

cct grew from many sources. Each named its skills its own way, so it carried 72 skills and 15 agents with no shared grammar: `squash` beside `pr-review`, `ux-audit` beside `accessibility-audit`, `ai-ready-issues` beside `write-ticket`. Overlapping descriptions made the wrong skill fire.

The fix is an object-verb convention, a closed verb list and a checker. cct is a single plugin, so the discipline prefix inside each skill name does the work a plugin name would.

## Decision

Adopt the twelve rules below and checks that fail on any violation. The rules, as approved:

1. Keep one plugin, `cct`; the discipline prefix inside each skill name supplies the owner/object context.
2. Preserve the approved families: `sdlc`, `project`, `product`, `ux`, `design`, `arch`, `db`, `review`, `test`, `git`, `data`, `tracking`, `docs`. UX owns behavior and words; design owns visual expression and systems.
3. Action names are `<family>-<object>-<verb>`; omit the object when the family already supplies it, as in `ux-audit`.
4. Use the closed `VERBS` list. The last segment is the verb; reject synonyms rather than expanding the vocabulary.
5. Preserve distinctions: `write` authors language; `create` produces a finished non-language artifact; `scaffold` produces incomplete boilerplate; `design` specifies something subsequently built.
6. `audit` judges an artifact against a standard; `review` examines an authored change; `analyze` returns insight without writing back; `validate` returns a binary verdict.
7. A process is an action subtype named `…-run`: it executes a defined workflow, delegates overlapping jobs to their owners, and keeps private methods in references/scripts.
8. Product adapters use `<vendor>-<verb>`: `aws-manage`, `cloudflare-manage`, `github-manage`, `linear-manage`, `posthog-manage`, `codex-run`. Keep `browser-automate`; artifact-producing skills retain their discipline.
9. Knowledge names end in nouns and require reasoned `NOUN_TAILS` entries. They ground other work; their descriptions must not dispatch artifact creation.
10. Internal role skills use `role-<subject>` and `user_invocable: false`; all other skills explicitly use `true`. Inline missing `role-test-fixer` material into its three consuming agents; do not carry that skill.
11. Names are lowercase kebab-case, 1–64 characters, with no repeated hyphen-delimited word; skill folder/frontmatter names match. Agents use family-prefixed noun forms; `role-` is a skill-only rule.
12. Migrate atomically; rewrite consumers and record the complete migration in an ADR. Add no forwarding skills.

### What the checks do

- `scripts/taxonomy.py` holds the rules and `NOUN_TAILS`, and reads the plugin folder.
- Checks that fail the test run: the name pattern, the closed verb list (a synonym is rejected with its replacement), a `NOUN_TAILS` reason for each knowledge skill, processes end in `run`, an explicit boolean `user_invocable` equal to `role-` membership, descriptions of at most 1024 characters, unique trigger phrases, and every `cct:` call, plugin path and agent preload resolving.

## The classes

**A** action, **K** knowledge, **R** role, **P** process. Every `@` row below is an agent role. A dagger removes the current standalone entry. A plus identifies a skill extracted from existing content.

## Old to new: all 72 skills and 15 agents

The first column is the name in cct 0.6.x, `@` marks an agent. Where two rows share a final name, the sources were merged into it. `analyze` is dropped.

| Current | Final name | Class | Exclusive job |
|---|---|---|---|
| accessibility-audit | ux-accessibility-audit | A | Own WCAG verdicts, including overlapping reflow/target-size criteria. |
| address-feedback | review-feedback-run | P | Coordinate diagnosis, test-first remediation, and verification. |
| ai-ready-issues † | product-workitem-write | A | Merge agent-ready requirements into the canonical work-item writer. |
| analyze † | — | A | Drop the unimplemented general-analysis entry. |
| analyze-cohorts | data-cohorts-analyze | A | Return retention/adoption insights from supplied cohort data. |
| api-design † | arch-plan-write | A | Retain the API checklist within technical planning. |
| architecture-review † | arch-plan-write | A | Retain structural-risk planning questions; remove the audit promise. |
| aws-manage | aws-manage | A | Operate AWS through its supported interface. |
| break-down-epics | product-epic-analyze | A | Return vertical slice boundaries; delegate work-item authoring. |
| browser-automate | browser-automate | A | Perform ad hoc browser interactions. |
| c4-diagram-create | docs-c4-create | A | Produce C4 architecture diagrams. |
| cloudflare-manage | cloudflare-manage | A | Operate Cloudflare through its supported interfaces. |
| codex-run | codex-run | A | Execute one supplied headless Codex task. |
| data-model-create † | arch-plan-write | A | Retain the schema-design checklist within technical planning. |
| dependency-review | review-dependency-run | P | Execute the authored dependency-update review workflow. |
| design-brief | ux-brief-write | A | Write change-specific goals, constraints, and success criteria. |
| design-consult | design-system-write | A | Author visual tokens and component conventions. |
| design-system-apply | — (removed later) | K | Carried a private design system; cct no longer ships one. |
| designs-explore | design-mockups-create | A | Produce image mockups from supplied specifications and visual contracts. |
| develop-prd | product-prd-write | A | Maintain the stakeholder PRD, linking canonical requirements. |
| dockerfile-review | review-container-audit | A | Audit container-build hardening against explicit criteria. |
| docs-audit | docs-audit | A | Audit documentation against implementation. |
| e2e-from-ticket-write † | test-e2e-coverage-run | P | Merge ticket input as a coverage-workflow mode. |
| e2e-test-run | test-e2e-policy | K | Supply E2E strategy, locator, waiting, and test-integrity rules. |
| e2e-write | test-e2e-coverage-run | P | Coordinate E2E planning, generation, execution, and healing. |
| flaky-test-fix | test-flake-fix | A | Diagnose and repair nondeterministic test failures. |
| frontend-design | design-frontend-write | A | Implement supplied visual specifications, including alternative versions. |
| github-manage | github-manage | A | Persist and inspect supplied GitHub resources; delegate domain authoring. |
| heuristic-evaluation-ai | ux-ai-heuristics | K | Supply AI-specific usability criteria to the usability auditor. |
| jobs-to-be-done | ux-jobs-write | A | Author job stories and desired user outcomes. |
| layout-grid † | design-system-write | A | Merge grid and breakpoint-token definition into system authoring. |
| linear-manage | linear-manage | A | Persist supplied Linear records; delegate their authored content. |
| microcopy-write | ux-copy-write | A | Author localized interface wording and terminology. |
| model-train † | data-classification-metrics | K | Preserve the real metrics reference; remove unsupported training claims. |
| network-analyze | data-network-analyze | A | Return graph/community/centrality insights from supplied data. |
| plan-design-review | design-surface-review | A | Critique an authored visual plan or changed surface. |
| plan-roadmap | product-roadmap-write | A | Write release sequencing from supplied priorities and initiative boundaries. |
| posthog-manage | posthog-manage | A | Operate PostHog resources and queries; delegate interpretation/instrumentation. |
| pr-create | git-pr-run | P | Coordinate documentation checks, commits, draft publication, and CI. |
| pr-review | review-code-run | P | Coordinate independent code-review evidence and finding validation. |
| product-playbook | product-playbook | K | Index product methods and supply their shared guidance. |
| project-kickoff | project-kickoff-run | P | Coordinate product inception, context, brand, and specialist outputs. |
| project-setup | project-repository-run | P | Coordinate repository adoption and workflow configuration. |
| queries-optimize | db-query-optimize | A | Improve measured SQL execution on an existing schema. |
| release-cut | git-release-run | P | Coordinate changelog authoring, versioning, tagging, and publication. |
| responsive-audit | ux-responsive-audit | A | Audit viewport adaptation outside WCAG-owned criteria. |
| review-fix-loop | review-fix-run | P | Iterate review, finding validation, remediation, and commits. |
| role-code-analysis | role-code-analysis | R | Supply shared investigation methods to agents. |
| role-review-vocabulary | role-review-vocabulary | R | Supply canonical finding identities, severity, and triage vocabulary. |
| run-story-mapping | product-storymap-create | A | Arrange supplied stories into narrative release slices. |
| sdlc-run | sdlc-run | P | Coordinate explicit lifecycle execution, resumption, and gates. |
| security-review | review-security-run | P | Execute the differential security-review workflow. |
| squash | git-commits-squash | A | Consolidate local branch commits; delegate GitHub merge operations. |
| state-machine | ux-states-design | A | Specify UI states, events, and transitions. |
| tracking-apply | tracking-apply | A | Register events and instrument call sites through an existing library. |
| tracking-audit | tracking-audit | A | Audit instrumentation and event conventions without repairing them. |
| tracking-setup | tracking-library-run | P | Coordinate library construction, call-site migration, and audit. |
| transcripts-fix | docs-transcript-fix | A | Correct speech-recognition errors in transcripts. |
| ux-audit | ux-assessment-run | P | Coordinate specialist assessments with `scope=app\|change`. |
| ux-conformance | ux-rules-validate | A | Return conformance verdicts against accepted product rules. |
| ux-decision | ux-decision-log | A | Record owner interaction decisions; delegate technical ADRs. |
| ux-design | ux-design-run | P | Coordinate a change’s interaction specification and assessment loop. |
| ux-guidelines | ux-guidelines-write | A | Author accepted interaction guidelines from recorded decisions. |
| ux-init | ux-setup | A | Configure UX inputs and artifact locations for one repository. |
| ux-laws-apply | ux-usability-audit | A | Own heuristic usability verdicts, including selected AI criteria. |
| ux-review † | ux-assessment-run | P | Merge change scope into the shared assessment process. |
| ux-run | ux-run | P | Coordinate assessment, owner decisions, and approved delivery. |
| ux-sitemap-create | ux-sitemap-create | A | Produce route maps and their planned/as-built differences. |
| ux-validate | ux-spec-validate | A | Return spec-readiness verdicts from completed specialist evidence. |
| ux-writing † | ux-copy-write | A | Merge writing guidance and execution into one copy owner. |
| variants-create † | design-frontend-write | A | Merge alternatives as an implementation parameter. |
| write-ticket | product-workitem-write | A | Author one canonical work item with business/agent renderings. |
| @ac-auditor | @review-criteria-auditor | R | Grade acceptance criteria against supplied implementation evidence. |
| @address-feedback-runner | @review-feedback-runner | R | Execute feedback remediation in isolated context. |
| @behavior-test-writer | @test-behavior-writer | R | Write a defect-proving behavioral test. |
| @builder | @sdlc-feature-builder | R | Implement an approved feature or milestone. |
| @code-reviewer | @review-code-reviewer | R | Review an assigned code axis outside reserved specialist domains. |
| @dimension-selector | @review-dimensions-selector | R | Select disjoint review axes. |
| @e2e-generator | @test-e2e-generator | R | Generate live-verified, defect-proven E2E specifications. |
| @e2e-healer | @test-e2e-healer | R | Repair deterministic E2E drift without weakening expectations. |
| @e2e-planner | @test-e2e-planner | R | Plan coverage for an assigned journey. |
| @extra-validation-runner | @review-fixset-triager | R | Classify validated findings into fix/discuss/drop dispositions. |
| @fix-implementer | @review-fix-implementer | R | Implement a diagnosed production fix after the failing test. |
| @review-runner | @review-code-runner | R | Execute the code-review process in isolated context. |
| @ux-reviewer | @ux-usability-reviewer | R | Evaluate one assigned usability lens. |
| @validate-finding | @review-finding-validator | R | Independently validate one finding. |
| @verifier | @test-behavior-verifier | R | Exercise changed and neighboring behavior. |
| + S/sdlc-run technical plan; Linear RFC; three architecture stubs | arch-plan-write | A | Author technical proposals/plans using API, schema, and structural checklists. |
| + Linear ADR; technical portion of UX decisions | arch-decision-log | A | Record an accepted technical decision as an ADR. |
| + Linear project/initiative templates | project-plan-write | A | Author execution milestones, ownership, and dependencies. |
| + Linear status/research templates | project-report-write | A | Author status or investigation reports from supplied evidence. |
| + S/address-feedback investigation | review-feedback-analyze | A | Return feedback diagnoses and dispositions without writing back. |
| + S/e2e-test-run installation | test-e2e-setup | A | Configure the named E2E harness and its guards. |
| + S/e2e-write journey inventory | test-journeys-write | A | Author the canonical journey coverage inventory. |
| + S/e2e-write suite execution | test-suite-run | A | Execute a supplied test suite and return its results. |
| + GitHub changelog command; release workflow | docs-changelog-write | A | Author release notes from supplied change history. |
| + S/ux-validate build mode | ux-build-validate | A | Return built-versus-approved-spec verdicts from state/visual evidence. |
| + PP/run-strategy-session | product-strategy-run | P | Coordinate strategy development using shared specialists and private methods. |
| + PP/run-discovery-process | product-discovery-run | P | Coordinate research, synthesis, experimentation, and evidence decisions. |
| + PP/frame-problem + reframe-problem | product-problem-write | A | Author the problem statement reused by briefs and PRDs. |
| + PP/define-ideal-customer; kickoff audience authoring | product-audience-write | A | Author canonical audience and persona definitions. |
| + PP/advise-prioritization + triage-feature-requests | product-priorities-analyze | A | Return comparative priorities for roadmap and strategy decisions. |
| + PP/map-customer-journey + run-journey-workshop | ux-journey-create | A | Produce the shared experience/touchpoint map. |
| + S/model-train/references/classification-metrics.md | data-classification-metrics | K | Explain confusion matrices and classification metrics. |

Counts: 72 skills before, 78 after. Of the 72: 46 renamed, 16 keep their name, 9 folded into another skill (`ai-ready-issues`, `api-design`, `architecture-review`, `data-model-create`, `e2e-from-ticket-write`, `layout-grid`, `ux-review`, `ux-writing`, `variants-create`), 1 dropped (`analyze`). 16 new skills are written from existing content. 15 agents, all renamed.

### The five stubs

| Stub and evidence | What exists today | Incoming references | Recommendation |
|---|---|---|---|
| analyze | **50 lines**; explicit stub at 25; prerequisites and planned capabilities, no analysis procedure or assets. | `network-analyze:173` actually delegates preparation; model/network descriptions redirect; build `DATA` roots it. | **Drop**. Remove preparation delegation and redirects; preserve useful presentation guidance as references. |
| api-design | **33 lines**; explicit stub at 22; planned endpoint/OpenAPI/versioning checklist only; no assets. | SDLC Stage 4; `data-model-create:10` redirects; explicitly rooted by build. | **Merge** checklist into `arch-plan-write`; no standalone contract-design capability is implemented. |
| architecture-review | **34 lines**; explicit stub at 24; planned coupling/boundary/scaling checklist only; no assets. | SDLC Stage 4; schema stub’s cross-skill note; C4 description redirects. | **Merge** planning questions into `arch-plan-write`; remove whole-system audit claims. |
| data-model-create | **31 lines**; explicit stub at 23; planned normalization/ERD/SQL checklist only; no assets. | SDLC Stage 4; API cross-skill note/redirect; C4 description redirect; explicitly rooted. | **Merge** checklist into `arch-plan-write`; schema engineering would require a real implementation. |
| model-train | **54 lines**; explicit stub at 27; library/technique wishlist; one substantive **101-line** metrics reference. | Analyze/network descriptions redirect; `analyze:34` reads the metrics file; build `DATA` roots it. | **Merge** the real reference into `data-classification-metrics`; drop unimplemented ML/statistics promises. |

## Product playbook

Only the four overlapping methods become skills (`product-problem-write`, `product-audience-write`, `product-priorities-analyze`, `ux-journey-create`) plus the two processes (`product-strategy-run`, `product-discovery-run`). Interviews, competition, positioning, finance, pricing, stakeholder work and the other methods stay references of `product-playbook`, used by the two process skills.

## Consequences

- Every command a user typed before this change is gone. The old to new table above is the migration guide. Update custom prompts, settings, hooks and agent dispatches that name an old skill or agent, for example `/cct:pr-review` is now `/cct:review-code-run`, and `subagent_type: cct:builder` is now `cct:sdlc-feature-builder`.
- Descriptions are exclusive: a trigger phrase belongs to one skill, so the right skill fires and the wrong one stays quiet. The cost is that a new skill must pick its own phrases.
- A new skill must pass the name rules and the reference check, or the tests fail.
- External adopters (settings, copied hooks, prompts, agent dispatches) must be inventoried before release; this ADR replaces forwarding skills.

## No forwarders

No skill under an old name is kept, no alias, no stub that redirects. A forwarder is a second description competing for the same trigger phrases and a second name to keep working; the old to new table is the single record. An unmigrated call fails loudly (the skill is not found) rather than silently running a stale copy.

## Open questions, with the recommendation taken

1. Which stub capabilities return? None during the rename. Add dedicated API, schema, architecture-audit, general-analysis or ML skills only with working procedures and resolved dependencies.
2. Which design and voice contract should generic skills select? Repository-configured contracts; product-specific assets live in references.
3. External adopters: inventory their settings, copied hooks, prompts and agent dispatches before release.
