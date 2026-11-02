---
name: model-train
description: Applied ML/statistics — predictive modeling, NLP, econometrics, forecasting, simulation, embeddings, and LLM integration with layman-friendly metric explanations. Use when the user wants a model trained, predictions made, or statistical methodology applied. Triggers on "machine learning", "train a model", "classification", "regression", "forecast", "clustering", "sentiment analysis", "embeddings", "confusion matrix", "precision recall", "ROC AUC", "econometrics". Skip for descriptive analysis/exec summary without a model — use cct:analyze; graph/community structure — use network-analyze; raw SQL extraction — use query-run.
allowed-tools: "Bash(python3 *) Bash(uv *)"
user_invocable: true
metadata:
  version: 0.1.0
  author: calvindudek
---

# Apply Data Science

ML, NLP, econometrics, forecasting, simulation, and LLM integration toolkit.

## Prerequisites

| Variable/Dependency | Required | Format | How to obtain |
|---------------------|----------|--------|---------------|
| `GEMINI_API_KEY` | Optional | `AI...` | Google AI Studio |
| `pandas` | Yes | Python package | `uv add pandas` |
| `scikit-learn` | Yes | Python package | `uv add scikit-learn` |
| `statsmodels` | Yes | Python package | `uv add statsmodels` |
| `networkx` | Yes | Python package | `uv add networkx` |

## Instructions

> **Stub** — this skill will be fully developed in a separate session.

### Planned capabilities

**Libraries:**
- scikit-learn — classification, regression, clustering, dimensionality reduction
- nltk + spacy — NLP preprocessing, tokenization, sentiment
- huggingface transformers — pre-trained models, fine-tuning, embeddings
- Google Gemini — LLM inference, multimodal
- statsmodels — econometrics, time series (ARIMA, VAR), hypothesis testing
- scipy — statistical tests, distributions, optimization
- networkx — graph analysis, Markov chains
- prophet / neuralprophet — time series forecasting

**Techniques:**
- Segmentation (K-means, DBSCAN, hierarchical)
- Classification (random forest, XGBoost, logistic regression, neural nets)
- Regression (linear, polynomial, ridge, lasso, econometric models)
- NLP (sentiment, topic modeling, text classification, entity extraction)
- LLM integration (embeddings, RAG, few-shot classification)
- Markov chains and simulation (Monte Carlo, agent-based)
- Econometrics (panel data, instrumental variables, diff-in-diff)
- Model evaluation (cross-validation, confusion matrix, ROC/AUC, RMSE)

### Cross-skill awareness
- Uses `query-run` (OMR AI Kit only, OMR's BigQuery; not in cct) for data
- Uses `chart-create` (OMR AI Kit only, OMR branding baked in; not in cct) for visualizations
- Uses `pdf-create` (OMR AI Kit only, OMR branding baked in; not in cct) for reports
