---
name: api-design
description: >
  API design — REST and GraphQL endpoint design, OpenAPI spec generation, versioning strategy,
  and error contract design. Use when user says "API design", "design API", "REST endpoints",
  "GraphQL schema", "OpenAPI spec", "API contract", "endpoint design", "versioning strategy",
  or asks to design an API for a feature or service.
  Skip for: database/ER schema design — use data-model-create.
  Skip for: API gateway, BFF, or service mesh patterns — use distributed-patterns.
allowed-tools: "Read Grep Glob Write"
user_invocable: true
metadata:
  version: 0.1.0
  author: calvindudek
effort: high
---

# Design API

Design consistent, well-structured APIs with proper contracts, versioning, and error handling.

> **Stub** — this skill will be fully developed in a separate session.

### Planned capabilities
- Requirements analysis → resource identification → endpoint design
- REST endpoint design with proper HTTP methods, status codes, and URL patterns
- GraphQL schema design with types, queries, mutations, and subscriptions
- OpenAPI 3.1 spec generation
- Versioning strategy (URL path vs. header vs. content negotiation)
- Error contract design (consistent error shapes, error codes)
- Pagination, filtering, and sorting patterns
- Authentication/authorization patterns per endpoint
- Cross-skill: works with `cct:data-model-create` for data-informed API design
