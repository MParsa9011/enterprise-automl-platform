"""Model evaluation: metrics and diagnostic figures.

Computes task-appropriate metrics (classification / regression) plus
Plotly-compatible diagnostic figures (confusion matrix, ROC curve, predicted-vs-
actual, residuals, learning curve). A single :func:`ranking_score` orients any
primary metric so that "higher is better", which the AutoML engine uses to select
the best run regardless of whether the metric is an accuracy or an error.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import plotly.graph_objects as go
from sklearn import metrics as skm
from sklearn.model_selection import learning_curve

from app.core.constants import TaskType

# Metrics where a *lower* value is better; ranking negates these.
ERROR_METRICS = frozenset({"mae", "mse", "rmse", "mape"})

PRIMARY_METRICS: dict[TaskType, list[str]] = {
    TaskType.CLASSIFICATION: ["accuracy", "f1_weighted", "f1_macro", "roc_auc"],
    TaskType.REGRESSION: ["r2", "rmse", "mae"],
}

DEFAULT_PRIMARY_METRIC: dict[TaskType, str] = {
    TaskType.CLASSIFICATION: "f1_weighted",
    TaskType.REGRESSION: "r2",
}


def _fig(figure: go.Figure) -> dict[str, Any]:
    """Convert a Plotly figure to a pure-JSON dict."""
    return json.loads(figure.to_json())


def ranking_score(metrics: dict[str, float], primary: str) -> float | None:
    """Return a "higher-is-better" score for the primary metric, or ``None``."""
    if primary not in metrics or metrics[primary] is None:
        return None
    value = float(metrics[primary])
    return -value if primary in ERROR_METRICS else value


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def evaluate_classification(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None,
    labels: list[Any],
) -> tuple[dict[str, float], dict[str, Any]]:
    """Compute classification metrics and diagnostic figures."""
    metrics: dict[str, float] = {
        "accuracy": float(skm.accuracy_score(y_true, y_pred)),
        "precision_weighted": float(
            skm.precision_score(y_true, y_pred, average="weighted", zero_division=0)
        ),
        "recall_weighted": float(
            skm.recall_score(y_true, y_pred, average="weighted", zero_division=0)
        ),
        "f1_weighted": float(skm.f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "f1_macro": float(skm.f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }

    auc = _roc_auc(y_true, y_proba, labels)
    if auc is not None:
        metrics["roc_auc"] = auc

    figures: dict[str, Any] = {
        "confusion_matrix": _confusion_matrix_figure(y_true, y_pred, labels),
    }
    if y_proba is not None and len(labels) == 2:
        figures["roc_curve"] = _roc_curve_figure(y_true, y_proba[:, 1])

    return metrics, figures


def _roc_auc(y_true: np.ndarray, y_proba: np.ndarray | None, labels: list[Any]) -> float | None:
    """Compute ROC AUC for binary or multiclass (OvR), or ``None`` if not possible."""
    if y_proba is None:
        return None
    try:
        if len(labels) == 2:
            return float(skm.roc_auc_score(y_true, y_proba[:, 1]))
        return float(skm.roc_auc_score(y_true, y_proba, multi_class="ovr", average="weighted"))
    except ValueError:
        return None


def _confusion_matrix_figure(
    y_true: np.ndarray, y_pred: np.ndarray, labels: list[Any]
) -> dict[str, Any]:
    """Build a confusion-matrix heatmap figure."""
    matrix = skm.confusion_matrix(y_true, y_pred, labels=labels)
    text = [[str(v) for v in row] for row in matrix]
    figure = go.Figure(
        go.Heatmap(
            z=matrix.tolist(),
            x=[str(label) for label in labels],
            y=[str(label) for label in labels],
            colorscale="Blues",
            text=text,
            texttemplate="%{text}",
            showscale=True,
        )
    )
    figure.update_layout(
        title="Confusion matrix",
        xaxis_title="Predicted",
        yaxis_title="Actual",
        template="plotly_white",
    )
    return _fig(figure)


def _roc_curve_figure(y_true: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    """Build a binary ROC-curve figure with the diagonal baseline."""
    fpr, tpr, _ = skm.roc_curve(y_true, scores)
    auc = skm.auc(fpr, tpr)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(x=fpr.tolist(), y=tpr.tolist(), mode="lines", name=f"ROC (AUC={auc:.3f})")
    )
    figure.add_trace(
        go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Chance", line={"dash": "dash"})
    )
    figure.update_layout(
        title="ROC curve",
        xaxis_title="False positive rate",
        yaxis_title="True positive rate",
        template="plotly_white",
    )
    return _fig(figure)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------
def evaluate_regression(
    y_true: np.ndarray, y_pred: np.ndarray
) -> tuple[dict[str, float], dict[str, Any]]:
    """Compute regression metrics and diagnostic figures."""
    mse = float(skm.mean_squared_error(y_true, y_pred))
    metrics: dict[str, float] = {
        "r2": float(skm.r2_score(y_true, y_pred)),
        "mae": float(skm.mean_absolute_error(y_true, y_pred)),
        "mse": mse,
        "rmse": float(np.sqrt(mse)),
        "explained_variance": float(skm.explained_variance_score(y_true, y_pred)),
    }
    mape = _safe_mape(y_true, y_pred)
    if mape is not None:
        metrics["mape"] = mape

    figures = {
        "predicted_vs_actual": _predicted_vs_actual_figure(y_true, y_pred),
        "residuals": _residuals_figure(y_true, y_pred),
    }
    return metrics, figures


def _safe_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float | None:
    """MAPE, guarding against division by zero when targets contain zeros."""
    if np.any(y_true == 0):
        return None
    return float(skm.mean_absolute_percentage_error(y_true, y_pred))


def _predicted_vs_actual_figure(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Scatter of predicted vs actual with the ideal y=x reference line."""
    lo, hi = float(min(y_true.min(), y_pred.min())), float(max(y_true.max(), y_pred.max()))
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=y_true.tolist(),
            y=y_pred.tolist(),
            mode="markers",
            name="Predictions",
            marker={"opacity": 0.6},
        )
    )
    figure.add_trace(
        go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="Ideal", line={"dash": "dash"})
    )
    figure.update_layout(
        title="Predicted vs actual",
        xaxis_title="Actual",
        yaxis_title="Predicted",
        template="plotly_white",
    )
    return _fig(figure)


def _residuals_figure(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Residuals-vs-predicted scatter with a zero reference line."""
    residuals = (y_true - y_pred).tolist()
    figure = go.Figure(
        go.Scatter(x=y_pred.tolist(), y=residuals, mode="markers", marker={"opacity": 0.6})
    )
    figure.add_hline(y=0, line_dash="dash")
    figure.update_layout(
        title="Residuals",
        xaxis_title="Predicted",
        yaxis_title="Residual",
        template="plotly_white",
    )
    return _fig(figure)


# ---------------------------------------------------------------------------
# Learning curve (task-agnostic)
# ---------------------------------------------------------------------------
def learning_curve_figure(
    estimator: Any, x: Any, y: Any, *, cv: int, scoring: str, random_state: int
) -> dict[str, Any]:
    """Build a learning-curve figure (train/validation score vs training size)."""
    sizes, train_scores, val_scores = learning_curve(
        estimator,
        x,
        y,
        cv=cv,
        scoring=scoring,
        train_sizes=np.linspace(0.2, 1.0, 5),
        random_state=random_state,
        n_jobs=1,
    )
    train_mean = train_scores.mean(axis=1)
    val_mean = val_scores.mean(axis=1)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(x=sizes.tolist(), y=train_mean.tolist(), mode="lines+markers", name="Train")
    )
    figure.add_trace(
        go.Scatter(x=sizes.tolist(), y=val_mean.tolist(), mode="lines+markers", name="Validation")
    )
    figure.update_layout(
        title="Learning curve",
        xaxis_title="Training examples",
        yaxis_title=f"Score ({scoring})",
        template="plotly_white",
    )
    return _fig(figure)
