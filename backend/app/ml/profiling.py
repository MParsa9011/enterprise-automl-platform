"""Automated statistical profiling of tabular datasets.

Produces a per-column schema (type inference, missingness, cardinality) and an
aggregate statistics document (numeric summaries, outliers, categorical
frequencies, correlations, duplicate detection). The output is JSON-safe so it
can be persisted on a :class:`DatasetVersion` and served directly to the
frontend for the "dataset statistics" view.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from pandas.api import types as pdt

from app.ml.io import json_safe

# Object columns with a unique-ratio below this are treated as categorical.
_CATEGORICAL_UNIQUE_RATIO = 0.5
_MAX_TOP_VALUES = 10
_MAX_CORRELATION_PAIRS = 15


@dataclass(slots=True)
class DatasetProfile:
    """Result of profiling a dataframe."""

    n_rows: int
    n_columns: int
    columns: list[dict[str, Any]] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)


def infer_semantic_type(series: pd.Series) -> str:
    """Classify a column as boolean, numeric, datetime, categorical or text."""
    if pdt.is_bool_dtype(series):
        return "boolean"
    if pdt.is_numeric_dtype(series):
        return "numeric"
    if pdt.is_datetime64_any_dtype(series):
        return "datetime"
    non_null = series.dropna()
    if non_null.empty:
        return "categorical"
    unique_ratio = non_null.nunique() / len(non_null)
    return "categorical" if unique_ratio <= _CATEGORICAL_UNIQUE_RATIO else "text"


def _column_schema(name: str, series: pd.Series, n_rows: int) -> dict[str, Any]:
    """Build the schema entry for a single column."""
    n_missing = int(series.isna().sum())
    return {
        "name": name,
        "dtype": str(series.dtype),
        "inferred_type": infer_semantic_type(series),
        "n_missing": n_missing,
        "missing_pct": round(100 * n_missing / n_rows, 4) if n_rows else 0.0,
        "n_unique": int(series.nunique(dropna=True)),
    }


def _numeric_summary(series: pd.Series) -> dict[str, Any]:
    """Compute descriptive statistics and IQR-based outlier count."""
    values = series.dropna()
    if values.empty:
        return {"count": 0}

    q1, q3 = (float(values.quantile(0.25)), float(values.quantile(0.75)))
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = int(((values < lower) | (values > upper)).sum())

    return {
        "count": int(values.count()),
        "mean": float(values.mean()),
        "std": float(values.std()) if values.count() > 1 else 0.0,
        "min": float(values.min()),
        "p25": q1,
        "median": float(values.median()),
        "p75": q3,
        "max": float(values.max()),
        "skew": float(values.skew()) if values.count() > 2 else 0.0,
        "kurtosis": float(values.kurt()) if values.count() > 3 else 0.0,
        "n_zeros": int((values == 0).sum()),
        "n_negative": int((values < 0).sum()),
        "n_outliers": outliers,
    }


def _categorical_summary(series: pd.Series) -> dict[str, Any]:
    """Compute the most frequent values for a categorical column."""
    counts = series.dropna().value_counts()
    total = int(counts.sum())
    top = [
        {
            "value": str(value),
            "count": int(count),
            "pct": round(100 * int(count) / total, 4) if total else 0.0,
        }
        for value, count in counts.head(_MAX_TOP_VALUES).items()
    ]
    return {"n_unique": int(counts.shape[0]), "top_values": top}


def _correlations(frame: pd.DataFrame, numeric_cols: list[str]) -> dict[str, Any]:
    """Compute a Pearson correlation matrix and the strongest pairs."""
    if len(numeric_cols) < 2:
        return {"matrix": {}, "top_pairs": []}

    matrix = frame[numeric_cols].corr(method="pearson", numeric_only=True)

    pairs: list[dict[str, Any]] = []
    for i, left in enumerate(numeric_cols):
        for right in numeric_cols[i + 1 :]:
            value = matrix.loc[left, right]
            if pd.notna(value):
                pairs.append({"a": left, "b": right, "correlation": float(value)})
    pairs.sort(key=lambda item: abs(item["correlation"]), reverse=True)

    return {
        "matrix": {col: matrix[col].to_dict() for col in numeric_cols},
        "top_pairs": pairs[:_MAX_CORRELATION_PAIRS],
    }


def profile_dataframe(frame: pd.DataFrame) -> DatasetProfile:
    """Compute a full statistical profile of ``frame``."""
    n_rows, n_columns = int(frame.shape[0]), int(frame.shape[1])

    columns = [_column_schema(str(name), frame[name], n_rows) for name in frame.columns]

    numeric_cols = [c["name"] for c in columns if c["inferred_type"] == "numeric"]
    categorical_cols = [
        c["name"] for c in columns if c["inferred_type"] in ("categorical", "boolean")
    ]

    numeric_stats = {name: _numeric_summary(frame[name]) for name in numeric_cols}
    categorical_stats = {name: _categorical_summary(frame[name]) for name in categorical_cols}

    total_cells = n_rows * n_columns
    missing_cells = int(frame.isna().sum().sum())
    missing_by_column = {
        str(name): int(count)
        for name, count in frame.isna().sum().items()
        if int(count) > 0
    }

    statistics: dict[str, Any] = {
        "overview": {
            "n_rows": n_rows,
            "n_columns": n_columns,
            "n_duplicate_rows": int(frame.duplicated().sum()),
            "memory_bytes": int(frame.memory_usage(deep=True).sum()),
            "missing_cells": missing_cells,
            "missing_cells_pct": round(100 * missing_cells / total_cells, 4)
            if total_cells
            else 0.0,
            "n_numeric": len(numeric_cols),
            "n_categorical": len(categorical_cols),
        },
        "missing_by_column": missing_by_column,
        "numeric": numeric_stats,
        "categorical": categorical_stats,
        "correlations": _correlations(frame, numeric_cols),
    }

    return DatasetProfile(
        n_rows=n_rows,
        n_columns=n_columns,
        columns=json_safe(columns),
        statistics=json_safe(statistics),
    )
