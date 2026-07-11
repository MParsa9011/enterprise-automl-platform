"""Unit tests for the algorithm registry and evaluation helpers."""

from __future__ import annotations

import numpy as np
import pytest

from app.core.constants import TaskType
from app.ml.algorithms import available_keys, get_algorithm, list_algorithms
from app.ml.evaluation import (
    DEFAULT_PRIMARY_METRIC,
    evaluate_classification,
    evaluate_regression,
    ranking_score,
)

pytestmark = pytest.mark.unit


class TestRegistry:
    def test_core_sklearn_algorithms_present(self) -> None:
        keys = available_keys(TaskType.CLASSIFICATION)
        for expected in (
            "random_forest",
            "extra_trees",
            "gradient_boosting",
            "logistic_regression",
            "svm",
            "knn",
            "decision_tree",
            "naive_bayes",
        ):
            assert expected in keys

    def test_naive_bayes_is_classification_only(self) -> None:
        assert "naive_bayes" in available_keys(TaskType.CLASSIFICATION)
        assert "naive_bayes" not in available_keys(TaskType.REGRESSION)

    def test_factory_builds_estimator(self) -> None:
        spec = get_algorithm("random_forest")
        estimator = spec.factory(TaskType.CLASSIFICATION, 42, {"n_estimators": 10})
        assert estimator.__class__.__name__ == "RandomForestClassifier"

    def test_unknown_algorithm_raises(self) -> None:
        with pytest.raises(KeyError):
            get_algorithm("does_not_exist")

    def test_list_filters_by_task(self) -> None:
        assert all(s.supports(TaskType.REGRESSION) for s in list_algorithms(TaskType.REGRESSION))


class TestEvaluation:
    def test_ranking_score_orientation(self) -> None:
        # Higher accuracy is better; lower error is better (so negated).
        assert ranking_score({"accuracy": 0.9}, "accuracy") == 0.9
        assert ranking_score({"rmse": 2.0}, "rmse") == -2.0
        assert ranking_score({}, "accuracy") is None

    def test_classification_metrics_and_figures(self) -> None:
        y_true = np.array([0, 1, 0, 1, 1, 0])
        y_pred = np.array([0, 1, 0, 0, 1, 0])
        proba = np.array([[0.8, 0.2], [0.3, 0.7], [0.9, 0.1], [0.6, 0.4], [0.2, 0.8], [0.7, 0.3]])
        metrics, figures = evaluate_classification(y_true, y_pred, proba, [0, 1])
        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert "roc_auc" in metrics
        assert "confusion_matrix" in figures
        assert "roc_curve" in figures

    def test_regression_metrics_and_figures(self) -> None:
        y_true = np.array([1.0, 2.0, 3.0, 4.0])
        y_pred = np.array([1.1, 1.9, 3.2, 3.8])
        metrics, figures = evaluate_regression(y_true, y_pred)
        assert metrics["r2"] > 0.9
        assert "rmse" in metrics
        assert "predicted_vs_actual" in figures

    def test_default_primary_metrics(self) -> None:
        assert DEFAULT_PRIMARY_METRIC[TaskType.CLASSIFICATION] == "f1_weighted"
        assert DEFAULT_PRIMARY_METRIC[TaskType.REGRESSION] == "r2"
