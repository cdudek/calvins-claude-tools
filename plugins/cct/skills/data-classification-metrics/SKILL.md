---
name: data-classification-metrics
description: "Reference for reading a classifier's results: the confusion matrix, accuracy, precision, recall, F1, specificity, ROC AUC, which metric fits which cost of error, and how to explain each to a non-technical reader. Grounds other work (reviewing a model, a report or a moderation rule) and writes nothing. Use when asked what a confusion matrix, 'precision versus recall', 'F1 score' or 'ROC AUC' means, or which metric to report for a classifier. Skip for graph and network metrics: cct:data-network-analyze."
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Classification metrics

A reference. It explains the numbers a classification model produces and how to say what they mean; it trains nothing and runs nothing.

## When to read it

- You are given a confusion matrix or a metric table and have to interpret it.
- You must choose which metric to report, or defend that choice, for a given cost of error.
- You must explain a result to someone who does not read statistics.

## What it holds

`references/classification-metrics.md` covers, in this order:

1. The confusion matrix: true and false positives and negatives, read as plain sentences.
2. Core metrics: accuracy, precision, recall (sensitivity), F1, specificity, each with a one-line meaning, the formula and when it misleads.
3. ROC AUC: what the curve shows and what a given value means.
4. When to use which metric: pick by the cost of a false positive against a false negative, and by class balance.
5. Presenting to non-technical stakeholders: lead with the consequence ("of 100 flagged, 82 are real"), then the number.

Read the whole file before explaining a result; the section on choosing a metric is the part people skip and regret.

## Rules

- Every metric you quote gets a "so what" in the same sentence: what it means for the decision, not only its value.
- State class balance before quoting accuracy. Accuracy on an imbalanced set hides the failure.
- Never present one metric alone when the costs of the two error types differ; give precision and recall together.
- Model training, forecasting and statistics beyond this reference are not part of cct. Say so instead of improvising a procedure.
