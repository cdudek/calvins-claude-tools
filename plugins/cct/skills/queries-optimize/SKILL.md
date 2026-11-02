---
name: queries-optimize
description: Optimizes PostgreSQL queries and database performance. Use when user says "Postgres", "PostgreSQL", "slow query", "query optimization", "indexing", "explain analyze", "database performance", or asks about SQL performance tuning.
allowed-tools: "Read Grep Glob Edit Write Bash(psql *)"
user_invocable: true
metadata:
  version: 1.0.0
  author: Supabase
---

# Supabase Postgres Best Practices

Comprehensive performance optimization guide for Postgres, maintained by Supabase. Contains rules across 8 categories, prioritized by impact to guide automated query optimization and schema design.

## When to Apply

Reference these guidelines when:
- Writing SQL queries or designing schemas
- Implementing indexes or query optimization
- Reviewing database performance issues
- Configuring connection pooling or scaling
- Optimizing for Postgres-specific features
- Working with Row-Level Security (RLS)

## Rule Categories by Priority

| Priority | Category | Impact | Prefix |
|----------|----------|--------|--------|
| 1 | Query Performance | CRITICAL | `query-` |
| 2 | Connection Management | CRITICAL | `conn-` |
| 3 | Security & RLS | CRITICAL | `security-` |
| 4 | Schema Design | HIGH | `schema-` |
| 5 | Concurrency & Locking | MEDIUM-HIGH | `lock-` |
| 6 | Data Access Patterns | MEDIUM | `data-` |
| 7 | Monitoring & Diagnostics | LOW-MEDIUM | `monitor-` |
| 8 | Advanced Features | LOW | `advanced-` |

## How to Use

Read individual rule files for detailed explanations and SQL examples:

```
@references/query-missing-indexes.md
@references/query-partial-indexes.md
@references/schema-primary-keys.md
@references/conn-pooling.md
@references/monitor-explain-analyze.md
```

Each rule file contains:
- Brief explanation of why it matters
- Incorrect SQL example with explanation
- Correct SQL example with explanation
- Optional EXPLAIN output or metrics
- Additional context and references

## References

- https://www.postgresql.org/docs/current/
- https://supabase.com/docs
- https://wiki.postgresql.org/wiki/Performance_Optimization

## Sources

| Origin | Author | License |
|--------|--------|---------|
| [supabase/agent-skills](https://github.com/supabase/agent-skills) — `skills/supabase-postgres-best-practices` | Supabase | MIT |
