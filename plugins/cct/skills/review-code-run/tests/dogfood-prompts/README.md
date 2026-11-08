# Dogfood smoke prompts — reference-file structural checks

The `references/*.md` files are consulted instructions, not directly unit-testable. The check below is structural: confirm the file still carries its required keys/rows. Run it by hand after editing the referenced file.

## dimensions.md — core + scored-pool tables

- `grep -E '^\| (security|correctness|performance) \|' dimensions.md` — confirm the **Core** table carries the 3 always-on axes.
- `grep -E '^\| (complexity|design-structure|test-quality|documentation|completeness|auth|authz|db-access|graphql|patterns-compat) \|' dimensions.md` — confirm the **Scored pool** table carries the secondary + domain axes.
