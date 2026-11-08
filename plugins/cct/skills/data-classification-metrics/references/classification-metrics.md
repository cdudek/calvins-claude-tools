# Classification Metrics — Explained

## The Confusion Matrix

A confusion matrix shows what the model predicted vs what actually happened:

```
                    Predicted
                  Positive  Negative
Actual Positive [   TP    |   FN    ]
Actual Negative [   FP    |   TN    ]
```

**Layman terms:**
- **TP (True Positive):** "We said yes, and it WAS yes" — correct catch
- **FP (False Positive):** "We said yes, but it was actually no" — false alarm
- **FN (False Negative):** "We said no, but it was actually yes" — missed catch
- **TN (True Negative):** "We said no, and it WAS no" — correct rejection

**The two types of errors, in real terms:**
- FP (false alarm): "We flagged this customer as churning, but they weren't going to churn" → wasted outreach effort
- FN (missed catch): "We said this customer was fine, but they actually churned" → lost revenue

**Which error matters more depends on the business context.** Always ask: "Is it worse to miss a real case, or to waste effort on a false alarm?"

## Core Metrics

### Accuracy
```
accuracy = (TP + TN) / (TP + TN + FP + FN)
```
**Layman:** "What percentage of all predictions were correct?"
**Watch out:** Misleading with imbalanced data. If 95% of customers don't churn, predicting "no churn" for everyone gives 95% accuracy but catches zero churners.

### Precision
```
precision = TP / (TP + FP)
```
**Layman:** "When the model says 'yes', how often is it actually right?"
**Use when:** False alarms are expensive (e.g., sending a costly retention offer to non-churners)

### Recall (Sensitivity)
```
recall = TP / (TP + FN)
```
**Layman:** "Of all the actual positives, how many did the model catch?"
**Use when:** Missing real cases is expensive (e.g., missing a churning customer who represents €10K/year)

### F1 Score
```
f1 = 2 * (precision * recall) / (precision + recall)
```
**Layman:** "The balance between precision and recall — high F1 means both are good"
**Use when:** You need a single number that captures both types of errors

### Specificity
```
specificity = TN / (TN + FP)
```
**Layman:** "Of all the actual negatives, how many did the model correctly identify as negative?"

## ROC AUC

**ROC Curve:** Plots recall (y-axis) vs false positive rate (x-axis) at every possible threshold.

**AUC (Area Under Curve):**
- 1.0 = perfect model
- 0.5 = random guessing (coin flip)
- < 0.5 = worse than random

**Layman:** "If you picked one positive and one negative example at random, AUC is the probability the model ranks the positive one higher. 0.85 means 85% of the time the model correctly ranks who will churn above who won't."

## When to Use Which Metric

| Scenario | Primary metric | Why |
|----------|---------------|-----|
| Balanced classes (50/50 split) | Accuracy or F1 | All metrics work well |
| Imbalanced (rare events like fraud, churn) | Recall + Precision, F1, AUC | Accuracy is misleading |
| Missing a case is very costly | Recall | Catch as many as possible |
| False alarms are very costly | Precision | Only flag when confident |
| Comparing models overall | ROC AUC | Threshold-independent |
| Need a single summary number | F1 (or AUC) | Balances both error types |

## Presenting to Non-Technical Stakeholders

**Always translate the numbers:**

Bad: "The model has precision 0.78 and recall 0.85"

Good: "When the model flags a customer as likely to churn, it's right 78% of the time (precision). And of all customers who actually churned, the model caught 85% of them (recall). The 15% it missed represent approximately €X in lost revenue."

**Use the confusion matrix visual:**
```
Out of 1,000 customers:
- 823 correctly identified as staying     ✓
- 127 correctly identified as churning    ✓ (we can intervene)
-  22 flagged as churning but weren't     △ (wasted outreach)
-  28 missed — churned without warning    ✗ (lost revenue)
```

**Always connect to business impact:** Multiply each cell by its cost to the business.
