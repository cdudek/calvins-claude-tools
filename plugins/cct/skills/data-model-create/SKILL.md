---
name: data-model-create
description: >
  Normalized data models — ERDs, entity relationships, 3NF/BCNF analysis, and migration plans.
  Outputs Mermaid ER diagrams. Use when user says "data model", "ERD", "entity relationship diagram",
  "database schema", "normalize tables", "3NF", "BCNF", "schema design", or asks to model a domain
  into tables.
  Skip for: dbt models or warehouse marts — use model-scaffold.
  Skip for: C4/system architecture diagrams — use c4-diagram-create.
  Skip for: API request/response shape design — use api-design.
allowed-tools: "Read Grep Glob Write"
user_invocable: true
metadata:
  version: 0.1.0
  author: calvindudek
effort: high
---

# Create Normalized Data Model

Design relational data models with proper normalization, clear entity relationships, and migration-ready output.

> **Stub** — this skill will be fully developed in a separate session.

### Planned capabilities
- Domain analysis → entity extraction → relationship mapping
- Normalization analysis (1NF → 2NF → 3NF/BCNF) with trade-off discussion
- Mermaid ER diagram output
- Migration SQL generation (CREATE TABLE statements)
- Index recommendations based on query patterns
- Cross-skill: works with `cct:architecture-review` for full system design
