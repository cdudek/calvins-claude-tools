---
name: analyze
description: End-to-end data analysis with narrative — pulls data, cleans it, surfaces insights, and writes executive summaries with compact number formatting. Use when the user wants interpretation, not just rows. Triggers on "analyze data", "data analysis", "run analysis", "insights", "executive summary", "key findings", "what does this data say", "explain these numbers". Skip for a single SQL query / schema lookup with no interpretation — use query-run; graph/network/community/centrality questions — use network-analyze; ML/forecasting/clustering models — use cct:model-train; a dashboard built from the numbers rather than a written narrative — use `ask` (OMR AI Kit only, OMR's BigQuery; not in cct).
allowed-tools: "Bash(bq *) Bash(python3 *)"
user_invocable: true
metadata:
  version: 0.1.0
  author: calvindudek
---

# Analyze Data

Data analysis and storytelling — SQL, cleaning, insights, and executive summaries.

## Prerequisites

| Variable/Dependency | Required | Format | How to obtain |
|---------------------|----------|--------|---------------|
| `bq` CLI | Yes | Installed | `gcloud components install bq` |
| `gcloud` auth | Yes | Authenticated | `gcloud auth login` |
| `pandas` | Yes | Python package | `uv add pandas` |

## Instructions

> **Stub** — this skill will be fully developed in a separate session.

### Planned capabilities
- SQL queries via `query-run` (OMR AI Kit only, OMR's BigQuery; not in cct) — joins, aggregations, window functions
- Compact number formatting (1 decimal: 1.2M, 345.7K, 23.4%)
- Data cleaning and validation
- Storytelling: executive summary, key findings, recommendations
- Proper data formatting (tables, markdown, well-structured output)
- Multi-source data joining and combination
- **Plain-language explanations**: every metric, every number gets a "so what" alongside the value. Translate statistical results into business impact. See `../model-train/references/classification-metrics.md` for the explanation style guide.

### Cross-skill awareness
- Uses `query-run` (OMR AI Kit only, OMR's BigQuery; not in cct) for data
- Uses `chart-create` (OMR AI Kit only, OMR branding baked in; not in cct) for visualizations
- Uses `pdf-create` (OMR AI Kit only, OMR branding baked in; not in cct) for reports

Reference: `~/projects/omr/fastly-logs/report/` analysis patterns

## Teilen: OMR AI OS kann das Ergebnis hosten

Ein fertiges HTML-Artefakt muss nicht als Datei verschickt werden. Der Skill
`overview` (OMR AI Kit only, OMR AI OS; not in cct) publiziert Dashboards, Präsentationen und Reports als interne,
teilbare Seite und vergibt einen `/go/`-Kurzlink. Bei Inhalten auf BigQuery-Basis kann die Seite
live an die Abfrage gebunden bleiben, statt einen Stand einzufrieren.

**Nach dem Erzeugen aktiv anbieten**, statt darauf zu warten, dass jemand danach fragt.
