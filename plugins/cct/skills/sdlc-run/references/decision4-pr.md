# Decision4 PR writing and validation

The rule is [Habitat Thinking Decision4 v1.0.1](https://github.com/Habitat-Thinking/decision4/blob/4429f821780655f253a954b2659bf38e7b9d5517/DECISION4.md).
The verbatim handoff block lives in AGENTS.md; CLAUDE.md imports it. Read the boundary map and the PR template HTML comment before writing a body.

- **Undo:** A revert puts it right. Return the result; omit Decision record.
- **Repair:** Real work, contained to this team. Return the result and Chose / Over / Because / Commits us to under `## Decision record`.
- **Migrate:** Coordinated change involving other people. Use `**Options**` and at least two real numbered options, or one `Forced` option with its `Constraint`; the accountable owner chooses.
- **Answer:** The wrong outcome reached someone outside the team with standing to ask, and nothing unmakes it. Use `**Evidence**` with each item labelled observed / inferred / asked / unknown, then `**Challenges**`. No recommendation; name a person or @handle responsible for recovery.

Use the highest decision and at least the map floor; unmapped or unsure means the higher class and a logged map gap. Escalate freely; never lower silently. A lowering records from -> to, who and why. Unattended runs close only Undo unless the owner explicitly authorized a higher ceiling.

Copy the exact H2 `## How hard is it to undo this PR after merging?` section, one bold class with its one colour circle, and a concrete recovery sentence. Repair and above need a standalone `**Recovery steps**` and a top-level numbered list, then Responsible for recovery and Classification change. Keep the legend collapsed. Work preserved is optional and needs evidence.

The shared check accepts H2/H3, legacy Decision-Class / Put-right / Answerer / Class-Change, and indented recovery lists. New bodies use the template format. Placeholder fields are empty. Effective class remains max(declared, floor), even with a recorded lowering.

Validate a proposed body before pushing and the actual body after creation or editing. Use `gh pr create --body-file` or `gh pr edit --body-file`. Actions callers pin the shared workflow; local gates dispatch `scripts/ci-local --decision4` through the checksum-verified fetch helper. No consuming repository carries checker code or fixtures. Shared-host fixtures test the check, while the actual PR uses the repository's map and entire diff (including rename sources).

The check proves minimum fields and floors; reviewers assess viable options, truthful recovery claims and the owner's recorded authorization. See [scannable PR layout](pr-body.md) and [local-first verification](local-first.md).
