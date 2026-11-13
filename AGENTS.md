<!-- prettier-ignore-start -->

## Decision4: how hard is this change to undo?

Every PR says how hard it would be to put right if it turns out to be wrong. Nothing blocks a merge on it. It tells a reviewer the risk at a glance.

Pick one level. `boundary-map.yaml` gives the lowest level for each path; never go below it. Unsure: pick the higher one. A PR takes the level of its riskiest change.

- **🟢 Undo:** a revert fixes it. No decision record.
- **🟡 Repair:** fixing it takes real work, but only from this team. Record what you chose, over what, why, and what it ties us to.
- **🟠 Migrate:** fixing it needs other teams or people to change something. Record at least two real options and what each ties us to (or one, plus the constraint that forces it), and who chose.
- **🔴 Answer:** someone outside the team is affected and it cannot be unmade, such as customer data, money or a public promise. Record the facts, each marked observed, inferred, asked or unknown, and the open questions. Do not recommend; a named person decides.

How to write it:

- Plain words, short sentences. Someone who never saw the work understands it in 30 seconds.
- Write the fact, not a pointer. Never cite a PR, issue or Linear ticket by number alone (not "see other-repo #1931", not "per ABC-1344"); say what it contains.
- Recovery steps are concrete: what to run or change, in order.
- Unattended agents finish only Undo changes. Above Undo, hand back to a person.

Source: Decision4 v1.0.1 by Habitat Thinking (CC BY 4.0).

<!-- prettier-ignore-end -->
