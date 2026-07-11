"""Model training pipeline.

Trains a single algorithm end-to-end for one :class:`~app.models.experiment.Run`:
compiles the preprocessing + estimator into one scikit-learn ``Pipeline``,
optionally tunes hyper-parameters with Optuna via cross-validation, fits the final
model, evaluates it on a hold-out split and serialises the fitted pipeline.

Everything is pure and synchronous so it can run inside a Celery worker or a test
without any web/database context.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

import joblib
import numpy as np
import optuna
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

from app.core.constants import TaskType
from app.ml.algorithms import AlgorithmSpec
from app.ml.evaluation import (
    ERROR_METRICS,
    evaluate_classification,
    evaluate_regression,
    ranking_score,
)
from app.ml.features import FeatureConfig, build_preprocessor
from app.ml.io import json_safe

optuna.logging.set_verbosity(optuna.logging.WARNING)


class TrainingError(ValueError):
    """Raised when a run cannot be trained (bad target, too little data, ...)."""


@dataclass(slots=True)
class TrainResult:
    """Outcome of training one algorithm."""

    metrics: dict[str, float]
    figures: dict[str, Any]
    params: dict[str, Any]
    primary_score: float | None
    artifact: bytes
    feature_schema: list[dict[str, str]] = field(default_factory=list)
    class_names: list[str] | None = None
    duration_seconds: float = 0.0


_SKLEARN_SCORING = {
    "accuracy": "accuracy",
    "f1_weighted": "f1_weighted",
    "f1_macro": "f1_macro",
    "roc_auc": "roc_auc",
    "r2": "r2",
    "rmse": "neg_root_mean_squared_error",
    "mae": "neg_mean_absolute_error",
}


def sklearn_scoring(primary_metric: str, n_classes: int) -> str:
    """Map a primary metric to an sklearn scoring string for CV/HPO/importance."""
    if primary_metric == "roc_auc" and n_classes > 2:
        return "roc_auc_ovr_weighted"
    return _SKLEARN_SCORING.get(primary_metric, "accuracy")


# Backwards-compatible private alias used within this module.
_scoring_for = sklearn_scoring


def train_algorithm(
    frame: pd.DataFrame,
    *,
    task_type: TaskType,
    target: str,
    feature_config: FeatureConfig,
    algorithm: AlgorithmSpec,
    primary_metric: str,
    optimize: bool = False,
    n_trials: int = 20,
    cv_folds: int = 3,
    test_size: float = 0.2,
    random_state: int = 42,
) -> TrainResult:
    """Train, (optionally) tune and evaluate one algorithm on ``frame``."""
    started = time.perf_counter()
    if target not in frame.columns:
        raise TrainingError(f"Target column {target!r} not found in dataset.")

    feature_config.target = target
    features = frame.drop(columns=[target])
    raw_target = frame[target]

    y, class_names = _prepare_target(raw_target, task_type)
    x_train, x_test, y_train, y_test = _split(features, y, task_type, test_size, random_state)

    effective_cv = _effective_cv(cv_folds, y_train, task_type)
    n_classes = len(class_names) if class_names else 0

    params: dict[str, Any] = {}
    if optimize and algorithm.search_space is not None and effective_cv >= 2:
        params = _optimise(
            algorithm, feature_config, frame, x_train, y_train,
            task_type=task_type, primary_metric=primary_metric,
            n_classes=n_classes, cv=effective_cv, n_trials=n_trials,
            random_state=random_state,
        )

    pipeline = _assemble(frame, feature_config, algorithm, task_type, params, random_state)
    pipeline.fit(x_train, y_train)

    metrics, figures = _evaluate(pipeline, x_test, y_test, task_type, class_names)
    score = ranking_score(metrics, primary_metric)

    result = TrainResult(
        metrics=json_safe(metrics),
        figures=figures,
        params=json_safe(params),
        primary_score=score,
        artifact=_serialise(pipeline),
        feature_schema=_feature_schema(features),
        class_names=class_names,
        duration_seconds=round(time.perf_counter() - started, 3),
    )
    return result


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------
def _prepare_target(
    raw_target: pd.Series, task_type: TaskType
) -> tuple[np.ndarray, list[str] | None]:
    """Encode a classification target; coerce a regression target to float."""
    if task_type == TaskType.CLASSIFICATION:
        encoder = LabelEncoder()
        encoded = encoder.fit_transform(raw_target.astype(str))
        if len(encoder.classes_) < 2:
            raise TrainingError("Classification target must have at least two classes.")
        return encoded, [str(c) for c in encoder.classes_]
    numeric = pd.to_numeric(raw_target, errors="coerce")
    if numeric.isna().all():
        raise TrainingError("Regression target could not be interpreted as numeric.")
    return numeric.to_numpy(dtype=float), None


def _split(
    features: pd.DataFrame,
    y: np.ndarray,
    task_type: TaskType,
    test_size: float,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    """Train/test split, stratifying for classification when feasible."""
    stratify = None
    if task_type == TaskType.CLASSIFICATION:
        _, counts = np.unique(y, return_counts=True)
        if counts.min() >= 2:
            stratify = y
    return train_test_split(features, y, test_size=test_size, random_state=random_state, stratify=stratify)


def _effective_cv(cv_folds: int, y_train: np.ndarray, task_type: TaskType) -> int:
    """Clamp CV folds so no fold is empty (bounded by the rarest class)."""
    if task_type == TaskType.CLASSIFICATION:
        _, counts = np.unique(y_train, return_counts=True)
        return max(2, min(cv_folds, int(counts.min())))
    return max(2, min(cv_folds, len(y_train)))


def _assemble(
    frame: pd.DataFrame,
    feature_config: FeatureConfig,
    algorithm: AlgorithmSpec,
    task_type: TaskType,
    params: dict[str, Any],
    random_state: int,
) -> Pipeline:
    """Compose the preprocessing pipeline with the estimator."""
    preprocessor, _, _ = build_preprocessor(frame, feature_config)
    estimator = algorithm.factory(task_type, random_state, params)
    return Pipeline([("preprocess", preprocessor), ("model", estimator)])


def _optimise(
    algorithm: AlgorithmSpec,
    feature_config: FeatureConfig,
    frame: pd.DataFrame,
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    *,
    task_type: TaskType,
    primary_metric: str,
    n_classes: int,
    cv: int,
    n_trials: int,
    random_state: int,
) -> dict[str, Any]:
    """Run an Optuna study and return the best hyper-parameters found."""
    scoring = _scoring_for(primary_metric, n_classes)
    splitter: Any = (
        StratifiedKFold(n_splits=cv, shuffle=True, random_state=random_state)
        if task_type == TaskType.CLASSIFICATION
        else cv
    )

    def objective(trial: optuna.Trial) -> float:
        assert algorithm.search_space is not None
        trial_params = algorithm.search_space(trial, task_type)
        pipeline = _assemble(frame, feature_config, algorithm, task_type, trial_params, random_state)
        scores = cross_val_score(pipeline, x_train, y_train, cv=splitter, scoring=scoring, n_jobs=1)
        return float(scores.mean())

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=random_state),
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return dict(study.best_params)


def _evaluate(
    pipeline: Pipeline,
    x_test: pd.DataFrame,
    y_test: np.ndarray,
    task_type: TaskType,
    class_names: list[str] | None,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Evaluate the fitted pipeline on the hold-out split."""
    y_pred = pipeline.predict(x_test)
    if task_type == TaskType.CLASSIFICATION:
        proba = pipeline.predict_proba(x_test) if hasattr(pipeline, "predict_proba") else None
        labels = list(range(len(class_names or [])))
        return evaluate_classification(y_test, y_pred, proba, labels)
    return evaluate_regression(y_test, np.asarray(y_pred, dtype=float))


def _serialise(pipeline: Pipeline) -> bytes:
    """Serialise the fitted pipeline to bytes with joblib."""
    buffer = BytesIO()
    joblib.dump(pipeline, buffer)
    return buffer.getvalue()


def _feature_schema(features: pd.DataFrame) -> list[dict[str, str]]:
    """Describe the input feature columns for the prediction contract."""
    return [{"name": str(name), "dtype": str(dtype)} for name, dtype in features.dtypes.items()]


def load_model(artifact: bytes) -> Pipeline:
    """Deserialise a fitted pipeline previously produced by :func:`train_algorithm`."""
    return joblib.load(BytesIO(artifact))  # noqa: S301 - trusted, self-produced artifact


def is_error_metric(metric: str) -> bool:
    """Whether ``metric`` is one where lower is better."""
    return metric in ERROR_METRICS
