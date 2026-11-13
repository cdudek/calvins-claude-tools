# Decision4 in a PR (advisory)

Decision4 says how hard a change is to undo. It is guidance for the reviewer. No workflow, no
`ci-local` step and no status check reads it, and it never blocks a merge.

Where things live in an adopted repo:

- `boundary-map.yaml`: the lowest level for each path. A PR never goes below it.
- `AGENTS.md`, section "Decision4: how hard is this change to undo?": the four levels and how to write them.
- The PR template: the section "How hard is it to undo this PR after merging?" and the Decision record.

## Writing the section

1. Find the lowest level `boundary-map.yaml` gives the changed paths. Pick that level or a higher one. Unsure: the higher.
2. Start with the level in bold and one sentence: what goes wrong if this is wrong, and who fixes it.
3. Under Repair and above, give **Recovery steps**: concrete things to run or change, in order, and who is responsible. At Answer that is a named person.
4. Under Undo, delete the Decision record. Otherwise fill it as `AGENTS.md` says: Repair, four bullets (Chose, Over, Because, Commits us to); Migrate, at least two options with what each commits us to, and who chose; Answer, facts marked observed, inferred, asked or unknown plus open questions, with no recommendation.
5. Plain words. Write the fact, never only a PR, issue or ticket number.

Unattended agents finish only Undo changes. Above Undo they hand back to a person.
