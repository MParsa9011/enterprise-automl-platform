"""Declarative feature-engineering pipelines.

A :class:`FeatureConfig` is compiled into a scikit-learn ``Pipeline`` composed of
a ``ColumnTransformer`` (per-dtype imputation, encoding and scaling) optionally
followed by feature selection and PCA. Expressing preprocessing as a single
fitted estimator means the exact same transformation is applied at train time and
at prediction time — eliminating training/serving skew — and it can be persisted
alongside the model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.feature_selection import (
    SelectKBest,
    VarianceThreshold,
    f_classif,
    f_regression,
)
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    MinMaxScaler,
    OneHotEncoder,
    OrdinalEncoder,
    RobustScaler,
    StandardScaler,
)

_NUMERIC_IMPUTERS = {"mean", "median", "most_frequent", "constant"}
_CATEGORICAL_IMPUTERS = {"most_frequent", "constant"}
_SCALERS = {"standard", "minmax", "robust", "none"}
_ENCODERS = {"onehot", "ordinal"}
_SELECTORS = {"none", "variance", "kbest"}


class FeatureConfigError(ValueError):
    """Raised when a feature configuration is invalid."""


@dataclass(slots=True)
class ImputationConfig:
    """Missing-value imputation strategy per dtype family."""

    numeric_strategy: str = "median"
    categorical_strategy: str = "most_frequent"
    numeric_fill_value: float = 0.0
    categorical_fill_value: str = "missing"


@dataclass(slots=True)
class FeatureConfig:
    """Declarative preprocessing configuration."""

    target: str | None = None
    imputation: ImputationConfig = field(default_factory=ImputationConfig)
    encoding: str = "onehot"
    scaling: str = "standard"
    selection_method: str = "none"
    selection_k: int = 10
    variance_threshold: float = 0.0
    pca_enabled: bool = False
    pca_components: float | int | None = None

    def validate(self) -> None:
        """Validate enum-like fields, raising :class:`FeatureConfigError`."""
        if self.imputation.numeric_strategy not in _NUMERIC_IMPUTERS:
            raise FeatureConfigError(f"Invalid numeric imputer: {self.imputation.numeric_strategy}")
        if self.imputation.categorical_strategy not in _CATEGORICAL_IMPUTERS:
            raise FeatureConfigError(
                f"Invalid categorical imputer: {self.imputation.categorical_strategy}"
            )
        if self.scaling not in _SCALERS:
            raise FeatureConfigError(f"Invalid scaling: {self.scaling}")
        if self.encoding not in _ENCODERS:
            raise FeatureConfigError(f"Invalid encoding: {self.encoding}")
        if self.selection_method not in _SELECTORS:
            raise FeatureConfigError(f"Invalid selection method: {self.selection_method}")


def split_feature_columns(frame: pd.DataFrame, target: str | None) -> tuple[list[str], list[str]]:
    """Return ``(numeric, categorical)`` feature columns, excluding the target."""
    features = frame.drop(columns=[target]) if target and target in frame.columns else frame
    numeric = features.select_dtypes(include=["number"]).columns.astype(str).tolist()
    # Include "string" for forward-compatibility with the pandas 3 string dtype.
    categorical = (
        features.select_dtypes(include=["object", "string", "category", "bool"])
        .columns.astype(str)
        .tolist()
    )
    return numeric, categorical


def _make_scaler(name: str) -> Any:
    """Instantiate the configured scaler, or ``None`` when disabled."""
    return {
        "standard": StandardScaler(),
        "minmax": MinMaxScaler(),
        "robust": RobustScaler(),
        "none": None,
    }[name]


def _numeric_pipeline(config: FeatureConfig) -> Pipeline:
    """Build the numeric-column sub-pipeline (impute → optional scale)."""
    steps: list[tuple[str, Any]] = [
        (
            "impute",
            SimpleImputer(
                strategy=config.imputation.numeric_strategy,
                fill_value=config.imputation.numeric_fill_value,
            ),
        )
    ]
    scaler = _make_scaler(config.scaling)
    if scaler is not None:
        steps.append(("scale", scaler))
    return Pipeline(steps)


def _categorical_pipeline(config: FeatureConfig) -> Pipeline:
    """Build the categorical-column sub-pipeline (impute → encode)."""
    if config.encoding == "onehot":
        encoder: Any = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    else:
        encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    return Pipeline(
        [
            (
                "impute",
                SimpleImputer(
                    strategy=config.imputation.categorical_strategy,
                    fill_value=config.imputation.categorical_fill_value,
                ),
            ),
            ("encode", encoder),
        ]
    )


def build_preprocessor(
    frame: pd.DataFrame, config: FeatureConfig
) -> tuple[Pipeline, list[str], list[str]]:
    """Compile ``config`` into a fitted-able preprocessing ``Pipeline``.

    Returns the pipeline together with the numeric and categorical feature
    columns it operates on, for transparency to callers.
    """
    config.validate()
    numeric, categorical = split_feature_columns(frame, config.target)
    if not numeric and not categorical:
        raise FeatureConfigError("No feature columns available after excluding the target.")

    transformers: list[tuple[str, Any, list[str]]] = []
    if numeric:
        transformers.append(("numeric", _numeric_pipeline(config), numeric))
    if categorical:
        transformers.append(("categorical", _categorical_pipeline(config), categorical))

    column_transformer = ColumnTransformer(transformers, remainder="drop")

    steps: list[tuple[str, Any]] = [("columns", column_transformer)]
    steps.extend(_selection_steps(config))
    if config.pca_enabled:
        steps.append(("pca", PCA(n_components=config.pca_components)))

    return Pipeline(steps), numeric, categorical


def _selection_steps(config: FeatureConfig) -> list[tuple[str, Any]]:
    """Build optional feature-selection steps for the pipeline."""
    if config.selection_method == "variance":
        return [("select", VarianceThreshold(threshold=config.variance_threshold))]
    if config.selection_method == "kbest":
        # f_classif vs f_regression is resolved at fit time in ``preview``/trainer,
        # where the target's nature is known; default to classification here.
        return [("select", SelectKBest(score_func=f_classif, k=config.selection_k))]
    return []


def preview_features(frame: pd.DataFrame, config: FeatureConfig) -> dict[str, Any]:
    """Fit the pipeline on ``frame`` and summarise the transformed output.

    Returns the output feature count/names, a small sample of transformed rows
    and the resolved input column split. Supervised selectors use the target.
    """
    pipeline, numeric, categorical = build_preprocessor(frame, config)

    target = config.target
    y = None
    features = frame
    if target and target in frame.columns:
        features = frame.drop(columns=[target])
        y = frame[target]
        _resolve_kbest_score_func(pipeline, y)

    transformed = pipeline.fit_transform(features, y)
    transformed = np.asarray(transformed)

    try:
        names = [str(n) for n in pipeline.get_feature_names_out()]
    except Exception:
        names = [f"feature_{i}" for i in range(transformed.shape[1])]

    sample = transformed[:10].tolist()
    return {
        "n_features_in": len(numeric) + len(categorical),
        "n_features_out": int(transformed.shape[1]),
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "output_features": names,
        "sample": [[_round(v) for v in row] for row in sample],
    }


def _resolve_kbest_score_func(pipeline: Pipeline, y: pd.Series) -> None:
    """Pick f_regression for continuous targets, f_classif otherwise."""
    if "select" not in pipeline.named_steps:
        return
    selector = pipeline.named_steps["select"]
    if isinstance(selector, SelectKBest):
        is_continuous = pd.api.types.is_float_dtype(y) and y.nunique() > 20
        selector.set_params(score_func=f_regression if is_continuous else f_classif)


def _round(value: Any) -> Any:
    """Round floats for a compact preview payload."""
    if isinstance(value, float | np.floating):
        return round(float(value), 6)
    if isinstance(value, np.integer):
        return int(value)
    return value
