# Next Task

## ▶ M6 — AutoML Training Engine

**Goal:** Train, tune and evaluate many models asynchronously from a dataset
version + feature config, tracking everything for reproducibility.

### Scope (delivered as vertical slices)
1. **Domain models** — `Experiment`, `Run`, `Model` (+ statuses already in
   `constants.py`). An experiment fans out into one run per algorithm; the best
   run is registered as a `Model`.
2. **Algorithm registry** (`app/ml/algorithms.py`) — a registry of estimators
   with default hyper-parameters and Optuna search spaces:
   Random Forest, XGBoost, CatBoost, LightGBM, Logistic Regression, SVM, KNN,
   Naive Bayes, Decision Tree, Extra Trees, Gradient Boosting.
3. **Evaluation** (`app/ml/evaluation.py`) — classification & regression metrics,
   ROC/confusion-matrix/learning-curve figure data.
4. **Training pipeline** (`app/ml/training.py`) — assemble preprocessing +
   estimator, cross-validate, optional Optuna HPO, fit final model, persist
   artifact + metrics.
5. **Async execution** — Celery app + training task; experiment/run status
   transitions; graceful eager-mode fallback for tests.
6. **Service + endpoints** — create experiment, list/get experiments & runs,
   fetch metrics/evaluation figures.
7. **Tests** — algorithm registry, evaluation math, and an end-to-end training
   run executed synchronously (Celery eager) on a small dataset.

### Definition of done
- Experiments can be created and (in eager mode) trained end-to-end.
- Metrics + evaluation figures retrievable via API.
- Unit + integration tests green; full suite passing.
- Atomic Conventional Commits; `PROJECT_STATUS.md` + this file updated.

> MLflow tracking and SHAP explainability are integrated in this milestone where
> feasible; heavier boosting libraries (XGBoost/LightGBM/CatBoost) are optional
> extras and the registry degrades gracefully if one is unavailable.
