# Next Task

## ▶ M5 — EDA & Feature Engineering pipeline

**Goal:** Turn an uploaded dataset version into (a) automated EDA artifacts the
frontend can render, and (b) a reproducible, configurable feature-engineering
pipeline that later feeds the AutoML trainer.

### Scope
1. **EDA generation** (`app/ml/eda.py`)
   - Missing-value summary, feature distributions/histograms, box plots,
     scatter plots, correlation heatmap — emitted as Plotly-compatible figure
     JSON (no server-side image rendering).
2. **Feature engineering** (`app/ml/features.py`)
   - scikit-learn `Pipeline` / `ColumnTransformer` builder from a declarative
     config: imputation, encoding (one-hot / ordinal), scaling (standard /
     minmax / robust), variance-threshold + top-k feature selection, optional PCA.
3. **DTOs & config schemas** (`app/schemas/eda.py`, `app/schemas/features.py`).
4. **Service** (`app/services/eda.py`) — load a dataset version, run EDA /
   preview a feature pipeline; authorize via the dataset service.
5. **Endpoints**
   - `GET  /datasets/{id}/versions/{v}/eda` — EDA figures.
   - `POST /datasets/{id}/versions/{v}/feature-preview` — apply a pipeline config
     and return the transformed schema + a sample.
6. **Tests** — unit tests for EDA/feature builders; integration tests for endpoints.

### Definition of done
- New endpoints wired, permission-guarded (`dataset:read`).
- Unit + integration tests green; full suite still passing.
- Atomic Conventional Commits per sub-feature.
- `PROJECT_STATUS.md` and this file updated; roadmap row flipped to ✅.
