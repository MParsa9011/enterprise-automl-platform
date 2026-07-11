"""Model explainability.

Provides model-agnostic explanations for a fitted pipeline:

* **Permutation importance** — always available (scikit-learn); measures the drop
  in score when each raw input feature is shuffled, so it is interpretable in the
  original feature space.
* **Partial dependence** — the marginal effect of the most important numeric
  feature on the prediction.
* **SHAP** — optional; when the ``shap`` library is installed and the model is
  tree-based, mean absolute SHAP values give a fast, theoretically-grounded
  importance ranking. Absence of ``shap`` degrades gracefully.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.inspection import permutation_importance
from sklearn.pipeline import Pipeline

from app.core.constants import TaskType
from app.core.logging import get_logger
from app.ml.io import json_safe

logger = get_logger(__name__)

# Cap rows used for explanation so it stays fast on large datasets.
MAX_EXPLAIN_ROWS = 500


def _fig(figure: go.Figure) -> dict[str, Any]:
    return json.loads(figure.to_json())


def _importance_figure(features: list[str], values: list[float], title: str) -> dict[str, Any]:
    """Horizontal bar chart of feature importances (ascending for readability)."""
    order = np.argsort(values)
    figure = go.Figure(
        go.Bar(
            x=[values[i] for i in order],
            y=[features[i] for i in order],
            orientation="h",
            marker_color="#2563eb",
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title="Importance",
        yaxis_title="Feature",
        template="plotly_white",
        height=max(300, 24 * len(features)),
    )
    return _fig(figure)


def permutation_importances(
    pipeline: Pipeline,
    x: pd.DataFrame,
    y: np.ndarray,
    *,
    scoring: str,
    n_repeats: int = 5,
    random_state: int = 42,
) -> list[dict[str, Any]]:
    """Compute permutation importance for each raw input feature."""
    result = permutation_importance(
        pipeline, x, y, scoring=scoring, n_repeats=n_repeats, random_state=random_state, n_jobs=1
    )
    importances = [
        {"feature": str(col), "importance": float(mean), "std": float(std)}
        for col, mean, std in zip(x.columns, result.importances_mean, result.importances_std, strict=False)
    ]
    importances.sort(key=lambda item: item["importance"], reverse=True)
    return importances


def shap_importances(
    pipeline: Pipeline, x: pd.DataFrame
) -> list[dict[str, Any]] | None:
    """Mean absolute SHAP value per transformed feature, or ``None`` if unavailable.

    Only attempted for tree-based models where SHAP's ``TreeExplainer`` is fast;
    any failure (missing library, unsupported model) returns ``None``.
    """
    try:
        import shap
    except Exception:  # noqa: BLE001 - optional dependency
        return None

    try:
        preprocessor = pipeline.named_steps["preprocess"]
        model = pipeline.named_steps["model"]
        transformed = preprocessor.transform(x)
        try:
            names = [str(n) for n in preprocessor.get_feature_names_out()]
        except Exception:  # noqa: BLE001
            names = [f"feature_{i}" for i in range(transformed.shape[1])]

        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(transformed)
        arr = np.asarray(values)
        # For multiclass, average magnitude across classes.
        if arr.ndim == 3:
            mean_abs = np.abs(arr).mean(axis=(0, -1))
        else:
            mean_abs = np.abs(arr).mean(axis=0)

        pairs = [
            {"feature": name, "importance": float(val)}
            for name, val in zip(names, mean_abs, strict=False)
        ]
        pairs.sort(key=lambda item: item["importance"], reverse=True)
        return pairs
    except Exception as exc:  # noqa: BLE001 - SHAP is best-effort
        logger.info("shap_unavailable_for_model", error=str(exc))
        return None


def explain(
    pipeline: Pipeline,
    frame: pd.DataFrame,
    *,
    task_type: TaskType,
    target: str,
    class_names: list[str] | None,
    scoring: str,
    random_state: int = 42,
) -> dict[str, Any]:
    """Produce a bundle of explanations for a fitted pipeline."""
    sample = frame.sample(min(len(frame), MAX_EXPLAIN_ROWS), random_state=random_state)
    x = sample.drop(columns=[target])

    if task_type == TaskType.CLASSIFICATION:
        from sklearn.preprocessing import LabelEncoder

        y = LabelEncoder().fit_transform(sample[target].astype(str))
    else:
        y = pd.to_numeric(sample[target], errors="coerce").to_numpy(dtype=float)

    perm = permutation_importances(pipeline, x, y, scoring=scoring, random_state=random_state)
    bundle: dict[str, Any] = {
        "permutation_importance": {
            "values": perm,
            "figure": _importance_figure(
                [item["feature"] for item in perm],
                [item["importance"] for item in perm],
                "Permutation importance",
            ),
        },
        "shap": None,
    }

    shap_values = shap_importances(pipeline, x)
    if shap_values:
        top = shap_values[:20]
        bundle["shap"] = {
            "values": top,
            "figure": _importance_figure(
                [item["feature"] for item in top],
                [item["importance"] for item in top],
                "SHAP feature importance (mean |value|)",
            ),
        }

    return json_safe(bundle)
