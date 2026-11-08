---
name: review-security-run
description: "Runs a security-focused differential review of a code change: auth, crypto, external calls, blast radius and adversarial modeling, with methodology, vulnerability patterns and a structured report. It is a complete review workflow of its own, not a pass of the general code review. Use when someone says 'run a security review', 'differential security review', 'security audit of this PR', 'review this change for vulnerabilities', 'adversarial review of this diff'. Skip for: general code correctness review, owned by cct:review-code-run; dependency version updates, owned by cct:review-dependency-run."
allowed-tools: "Read Grep Glob Write Bash(git *) Bash(gh *)"
user_invocable: true
metadata:
  version: 1.0.0
  author: Trail of Bits
context: fork
model: opus
effort: max
background: false
---

# Differential Security Review

Security-focused code review for PRs, commits, and diffs.

Run one review pass; do not start further review rounds or spawn extra reviewers.

## Core Principles

1. **Risk-First**: Focus on auth, crypto, value transfer, external calls
2. **Evidence-Based**: Every finding backed by git history, line numbers, attack scenarios
3. **Adaptive**: Scale to codebase size (SMALL/MEDIUM/LARGE)
4. **Honest**: Explicitly state coverage limits and confidence level
5. **Output-Driven**: Always generate comprehensive markdown report file

## Rationalizations (Do Not Skip)

| Rationalization | Why It's Wrong | Required Action |
|-----------------|----------------|-----------------|
| "Small PR, quick review" | Heartbleed was 2 lines | Classify by RISK, not size |
| "I know this codebase" | Familiarity breeds blind spots | Build explicit baseline context |
| "Git history takes too long" | History reveals regressions | Never skip Phase 1 |
| "Blast radius is obvious" | You'll miss transitive callers | Calculate quantitatively |
| "Just a refactor, no security impact" | Refactors break invariants | Analyze as HIGH until proven LOW |

## Codebase Size Strategy

| Size | Strategy | Approach |
|------|----------|----------|
| SMALL (<20 files) | DEEP | Read all deps, full git blame |
| MEDIUM (20-200) | FOCUSED | 1-hop deps, priority files |
| LARGE (200+) | SURGICAL | Critical paths only |

## Risk Level Triggers

| Risk Level | Triggers |
|------------|----------|
| HIGH | Auth, crypto, external calls, value transfer, validation removal |
| MEDIUM | Business logic, state changes, new public APIs |
| LOW | Comments, tests, UI, logging |

## Workflow

```
Pre-Analysis → Phase 0: Triage → Phase 1: Code Analysis → Phase 2: Test Coverage
    ↓              ↓                    ↓                        ↓
Phase 3: Blast Radius → Phase 4: Deep Context → Phase 5: Adversarial → Phase 6: Report
```

See @references/methodology.md for detailed phase-by-phase workflow.
See @references/adversarial.md for attacker modeling and exploit scenarios.
See @references/reporting.md for report structure and formatting.
See @references/patterns.md for common vulnerability patterns.

## Quality Checklist

- [ ] All changed files analyzed
- [ ] Git blame on removed security code
- [ ] Blast radius calculated for HIGH risk
- [ ] Attack scenarios are concrete (not generic)
- [ ] Findings reference specific line numbers + commits
- [ ] Report file generated

## Red Flags (Stop and Investigate)

- Removed code from "security", "CVE", or "fix" commits
- Access control modifiers removed
- Validation removed without replacement
- External calls added without checks
- High blast radius (50+ callers) + HIGH risk change

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [trailofbits/skills](https://github.com/trailofbits/skills) — `plugins/differential-review` | Trail of Bits | Apache-2.0 |
