## What

<one or two sentences: what changes for the user or the system>

Fixes <LINEAR-ID>

## Which requirements this satisfies

> One row per requirement from `changes/<id>/facts.md`, or from the issue when there is no change
> folder. A requirement with no proof is not done, and a proof with no requirement is scope creep.

| Requirement | Proof                          |
| ----------- | ------------------------------ |
| F1          | `<test file> › <test name>`    |
| F2          | manual: <who checked, and how> |

## Verification

- [ ] `<verify command>` exits 0
- [ ] Every `F`/`N` above has a proof in the table
- [ ] No `[NEEDS CLARIFICATION]` marker is left in the change folder or the issue

## Out of scope

- <what this PR deliberately does not do>
