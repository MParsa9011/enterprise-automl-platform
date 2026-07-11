"""Automated exploratory data analysis.

Generates a bundle of Plotly *figure specifications* (plain JSON: ``data`` +
``layout``) for a dataframe — missing-value maps, distributions, box plots,
correlation heatmaps and scatter plots. Returning figure JSON (rather than
server-rendered images) keeps the API stateless and lets the frontend render
interactive charts directly with Plotly.js.

Feature counts are capped so the payload stays bounded on very wide datasets.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import plotly.graph_objects as go

from app.ml.profiling import infer_semantic_type

# Bounds to keep the EDA payload reasonable on wide/large datasets.
MAX_CHARTED_FEATURES = 20
MAX_CATEGORIES = 15
SCATTER_SAMPLE = 2000

# A restrained, colour-blind-safe qualitative palette.
_PALETTE = ["#2563eb", "#16a34a", "#dc2626", "#d97706", "#7c3aed", "#0891b2"]


def _fig_to_dict(figure: go.Figure) -> dict[str, Any]:
    """Convert a Plotly figure to a pure-JSON dict (numpy-safe)."""
    return json.loads(figure.to_json())


def _split_columns(frame: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Return ``(numeric_columns, categorical_columns)`` by semantic type."""
    numeric, categorical = [], []
    for name in frame.columns:
        kind = infer_semantic_type(frame[name])
        if kind == "numeric":
            numeric.append(str(name))
        elif kind in ("categorical", "boolean"):
            categorical.append(str(name))
    return numeric, categorical


def missing_values_figure(frame: pd.DataFrame) -> dict[str, Any]:
    """Bar chart of missing-value counts per column (descending)."""
    missing = frame.isna().sum().sort_values(ascending=False)
    missing = missing[missing > 0]
    figure = go.Figure(
        go.Bar(
            x=missing.index.astype(str).tolist(),
            y=missing.to_numpy().tolist(),
            marker_color=_PALETTE[2],
        )
    )
    figure.update_layout(
        title="Missing values by column",
        xaxis_title="Column",
        yaxis_title="Missing count",
        template="plotly_white",
    )
    return _fig_to_dict(figure)


def histogram_figure(series: pd.Series, name: str) -> dict[str, Any]:
    """Distribution histogram for a numeric column."""
    figure = go.Figure(go.Histogram(x=series.dropna().to_numpy().tolist(), marker_color=_PALETTE[0]))
    figure.update_layout(
        title=f"Distribution — {name}",
        xaxis_title=name,
        yaxis_title="Frequency",
        template="plotly_white",
        bargap=0.05,
    )
    return _fig_to_dict(figure)


def box_figure(series: pd.Series, name: str) -> dict[str, Any]:
    """Box plot for a numeric column (visualises spread and outliers)."""
    figure = go.Figure(go.Box(y=series.dropna().to_numpy().tolist(), name=name, marker_color=_PALETTE[4]))
    figure.update_layout(title=f"Box plot — {name}", template="plotly_white")
    return _fig_to_dict(figure)


def categorical_figure(series: pd.Series, name: str) -> dict[str, Any]:
    """Bar chart of the most frequent categories for a column."""
    counts = series.dropna().astype(str).value_counts().head(MAX_CATEGORIES)
    figure = go.Figure(
        go.Bar(x=counts.index.tolist(), y=counts.to_numpy().tolist(), marker_color=_PALETTE[1])
    )
    figure.update_layout(
        title=f"Top categories — {name}",
        xaxis_title=name,
        yaxis_title="Count",
        template="plotly_white",
    )
    return _fig_to_dict(figure)


def correlation_heatmap(frame: pd.DataFrame, numeric_cols: list[str]) -> dict[str, Any] | None:
    """Pearson correlation heatmap for the numeric columns (or ``None``)."""
    if len(numeric_cols) < 2:
        return None
    matrix = frame[numeric_cols].corr(method="pearson", numeric_only=True)
    figure = go.Figure(
        go.Heatmap(
            z=matrix.to_numpy().tolist(),
            x=numeric_cols,
            y=numeric_cols,
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
        )
    )
    figure.update_layout(title="Correlation heatmap", template="plotly_white")
    return _fig_to_dict(figure)


def scatter_figure(frame: pd.DataFrame, x: str, y: str) -> dict[str, Any]:
    """Scatter plot of two numeric columns (sampled for large frames)."""
    subset = frame[[x, y]].dropna()
    if len(subset) > SCATTER_SAMPLE:
        subset = subset.sample(SCATTER_SAMPLE, random_state=42)
    figure = go.Figure(
        go.Scatter(
            x=subset[x].to_numpy().tolist(),
            y=subset[y].to_numpy().tolist(),
            mode="markers",
            marker={"color": _PALETTE[0], "opacity": 0.6},
        )
    )
    figure.update_layout(
        title=f"{y} vs {x}", xaxis_title=x, yaxis_title=y, template="plotly_white"
    )
    return _fig_to_dict(figure)


def generate_eda(frame: pd.DataFrame) -> dict[str, Any]:
    """Produce the full EDA figure bundle for ``frame``.

    Numeric columns receive a histogram and box plot; categorical columns a
    frequency bar chart; the numeric block also yields a correlation heatmap and
    a scatter plot of the most strongly correlated pair.
    """
    numeric, categorical = _split_columns(frame)
    numeric_charted = numeric[:MAX_CHARTED_FEATURES]
    categorical_charted = categorical[:MAX_CHARTED_FEATURES]

    bundle: dict[str, Any] = {
        "missing_values": missing_values_figure(frame),
        "correlation_heatmap": correlation_heatmap(frame, numeric),
        "histograms": {name: histogram_figure(frame[name], name) for name in numeric_charted},
        "boxplots": {name: box_figure(frame[name], name) for name in numeric_charted},
        "categorical": {
            name: categorical_figure(frame[name], name) for name in categorical_charted
        },
        "scatter": None,
    }

    if len(numeric) >= 2:
        pair = _strongest_pair(frame, numeric)
        if pair is not None:
            bundle["scatter"] = scatter_figure(frame, pair[0], pair[1])

    return bundle


def _strongest_pair(frame: pd.DataFrame, numeric_cols: list[str]) -> tuple[str, str] | None:
    """Return the pair of numeric columns with the largest |correlation|."""
    matrix = frame[numeric_cols].corr(method="pearson", numeric_only=True).abs()
    best: tuple[str, str] | None = None
    best_value = -1.0
    for i, left in enumerate(numeric_cols):
        for right in numeric_cols[i + 1 :]:
            value = matrix.loc[left, right]
            if pd.notna(value) and value > best_value:
                best_value, best = float(value), (left, right)
    return best
