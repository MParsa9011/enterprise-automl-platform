"""Algorithm registry for the AutoML engine.

Each supported estimator is described by an :class:`AlgorithmSpec` that knows
which task types it supports, how to build the estimator for a given task, and an
Optuna search space for hyper-parameter optimisation. Optional native libraries
(XGBoost, LightGBM, CatBoost) are imported defensively: if a library — or its
runtime dependency such as OpenMP — is unavailable, that algorithm is simply
omitted from the registry instead of breaking it, so the platform degrades
gracefully across environments.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING, Any

from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from app.core.constants import TaskType
from app.core.logging import get_logger

if TYPE_CHECKING:
    import optuna

logger = get_logger(__name__)

CLASSIFICATION = TaskType.CLASSIFICATION
REGRESSION = TaskType.REGRESSION

EstimatorFactory = Callable[[TaskType, int, dict[str, Any]], Any]
SearchSpace = Callable[["optuna.Trial", TaskType], dict[str, Any]]


def _safe_import(module_name: str) -> ModuleType | None:
    """Import an optional module, returning ``None`` on *any* import failure.

    Native ML libraries can fail at import time with errors other than
    ``ImportError`` (e.g. a missing ``libomp`` raises a library-specific error),
    so this catches broadly and logs rather than propagating.
    """
    try:
        return importlib.import_module(module_name)
    except Exception as exc:
        logger.warning("optional_library_unavailable", module=module_name, error=str(exc))
        return None


@dataclass(frozen=True, slots=True)
class AlgorithmSpec:
    """Declarative description of a trainable algorithm."""

    key: str
    display_name: str
    task_types: frozenset[TaskType]
    factory: EstimatorFactory
    search_space: SearchSpace | None = None

    def supports(self, task_type: TaskType) -> bool:
        """Whether this algorithm can be trained for ``task_type``."""
        return task_type in self.task_types


def _build(clf: type, reg: type) -> EstimatorFactory:
    """Create a factory that picks the classifier or regressor by task."""

    def factory(task_type: TaskType, random_state: int, params: dict[str, Any]) -> Any:
        estimator_cls = clf if task_type == CLASSIFICATION else reg
        kwargs = dict(params)
        # Only pass random_state to estimators that accept it.
        if "random_state" in estimator_cls().get_params():
            kwargs.setdefault("random_state", random_state)
        return estimator_cls(**kwargs)

    return factory


# ---------------------------------------------------------------------------
# Search spaces
# ---------------------------------------------------------------------------
def _forest_space(trial: optuna.Trial, _: TaskType) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 20),
        "min_samples_split": trial.suggest_int("min_samples_split", 2, 10),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 5),
        "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", None]),
    }


def _gboost_space(trial: optuna.Trial, _: TaskType) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 400, step=50),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "max_depth": trial.suggest_int("max_depth", 2, 6),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
    }


def _linear_space(trial: optuna.Trial, task_type: TaskType) -> dict[str, Any]:
    if task_type == CLASSIFICATION:
        return {"C": trial.suggest_float("C", 1e-3, 1e2, log=True)}
    return {"alpha": trial.suggest_float("alpha", 1e-3, 1e2, log=True)}


def _svm_space(trial: optuna.Trial, _: TaskType) -> dict[str, Any]:
    return {
        "C": trial.suggest_float("C", 1e-2, 1e2, log=True),
        "kernel": trial.suggest_categorical("kernel", ["rbf", "linear"]),
        "gamma": trial.suggest_categorical("gamma", ["scale", "auto"]),
    }


def _knn_space(trial: optuna.Trial, _: TaskType) -> dict[str, Any]:
    return {
        "n_neighbors": trial.suggest_int("n_neighbors", 3, 30),
        "weights": trial.suggest_categorical("weights", ["uniform", "distance"]),
    }


def _tree_space(trial: optuna.Trial, _: TaskType) -> dict[str, Any]:
    return {
        "max_depth": trial.suggest_int("max_depth", 2, 20),
        "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
    }


def _nb_space(trial: optuna.Trial, _: TaskType) -> dict[str, Any]:
    return {"var_smoothing": trial.suggest_float("var_smoothing", 1e-11, 1e-6, log=True)}


def _boosting_space(trial: optuna.Trial, _: TaskType) -> dict[str, Any]:
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
        "max_depth": trial.suggest_int("max_depth", 2, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
    }


# ---------------------------------------------------------------------------
# Registry assembly
# ---------------------------------------------------------------------------
_BOTH = frozenset({CLASSIFICATION, REGRESSION})
_CLF_ONLY = frozenset({CLASSIFICATION})


def _svc_factory(task_type: TaskType, random_state: int, params: dict[str, Any]) -> Any:
    """SVM factory that enables probability estimates for classification."""
    if task_type == CLASSIFICATION:
        return SVC(probability=True, random_state=random_state, **params)
    return SVR(**params)


def _build_registry() -> dict[str, AlgorithmSpec]:
    """Assemble the registry, including any available optional libraries."""
    specs: list[AlgorithmSpec] = [
        AlgorithmSpec(
            "random_forest",
            "Random Forest",
            _BOTH,
            _build(RandomForestClassifier, RandomForestRegressor),
            _forest_space,
        ),
        AlgorithmSpec(
            "extra_trees",
            "Extra Trees",
            _BOTH,
            _build(ExtraTreesClassifier, ExtraTreesRegressor),
            _forest_space,
        ),
        AlgorithmSpec(
            "gradient_boosting",
            "Gradient Boosting",
            _BOTH,
            _build(GradientBoostingClassifier, GradientBoostingRegressor),
            _gboost_space,
        ),
        AlgorithmSpec(
            "logistic_regression",
            "Logistic / Linear Regression",
            _BOTH,
            _build(LogisticRegression, Ridge),
            _linear_space,
        ),
        AlgorithmSpec("svm", "Support Vector Machine", _BOTH, _svc_factory, _svm_space),
        AlgorithmSpec(
            "knn",
            "K-Nearest Neighbours",
            _BOTH,
            _build(KNeighborsClassifier, KNeighborsRegressor),
            _knn_space,
        ),
        AlgorithmSpec(
            "decision_tree",
            "Decision Tree",
            _BOTH,
            _build(DecisionTreeClassifier, DecisionTreeRegressor),
            _tree_space,
        ),
        AlgorithmSpec(
            "naive_bayes",
            "Gaussian Naive Bayes",
            _CLF_ONLY,
            lambda _t, _r, params: GaussianNB(**params),
            _nb_space,
        ),
    ]
    specs.extend(_optional_boosting_specs())
    return {spec.key: spec for spec in specs}


def _optional_boosting_specs() -> list[AlgorithmSpec]:
    """Build specs for optional gradient-boosting libraries when importable."""
    result: list[AlgorithmSpec] = []

    if (xgb := _safe_import("xgboost")) is not None:
        result.append(
            AlgorithmSpec(
                "xgboost",
                "XGBoost",
                _BOTH,
                _build(xgb.XGBClassifier, xgb.XGBRegressor),
                _boosting_space,
            )
        )
    if (lgb := _safe_import("lightgbm")) is not None:
        result.append(
            AlgorithmSpec(
                "lightgbm",
                "LightGBM",
                _BOTH,
                _lightgbm_factory(lgb),
                _boosting_space,
            )
        )
    if (cat := _safe_import("catboost")) is not None:
        result.append(
            AlgorithmSpec(
                "catboost",
                "CatBoost",
                _BOTH,
                _catboost_factory(cat),
                lambda trial, _t: {
                    "iterations": trial.suggest_int("iterations", 100, 500, step=50),
                    "depth": trial.suggest_int("depth", 3, 10),
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                },
            )
        )
    return result


def _lightgbm_factory(lgb: ModuleType) -> EstimatorFactory:
    def factory(task_type: TaskType, random_state: int, params: dict[str, Any]) -> Any:
        cls = lgb.LGBMClassifier if task_type == CLASSIFICATION else lgb.LGBMRegressor
        return cls(random_state=random_state, verbose=-1, **params)

    return factory


def _catboost_factory(cat: ModuleType) -> EstimatorFactory:
    def factory(task_type: TaskType, random_state: int, params: dict[str, Any]) -> Any:
        cls = cat.CatBoostClassifier if task_type == CLASSIFICATION else cat.CatBoostRegressor
        return cls(random_state=random_state, verbose=0, allow_writing_files=False, **params)

    return factory


_REGISTRY: dict[str, AlgorithmSpec] = _build_registry()


def get_algorithm(key: str) -> AlgorithmSpec:
    """Return the spec for ``key`` or raise ``KeyError`` if unknown/unavailable."""
    if key not in _REGISTRY:
        raise KeyError(f"Unknown or unavailable algorithm: {key!r}")
    return _REGISTRY[key]


def list_algorithms(task_type: TaskType | None = None) -> list[AlgorithmSpec]:
    """List available algorithms, optionally filtered by task type."""
    specs = list(_REGISTRY.values())
    if task_type is None:
        return specs
    return [spec for spec in specs if spec.supports(task_type)]


def available_keys(task_type: TaskType) -> list[str]:
    """Return the keys of algorithms available for ``task_type``."""
    return [spec.key for spec in list_algorithms(task_type)]
