"""Unit tests for the feature-engineering pipeline builder."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.ml.features import (
    FeatureConfig,
    FeatureConfigError,
    ImputationConfig,
    build_preprocessor,
    preview_features,
    split_feature_columns,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "age": [25, 32, 47, np.nan, 51, 29, 40, 33],
            "income": [50000, 64000, 120000, 80000, 95000, 70000, 68000, 72000],
            "gender": ["M", "F", "F", "M", "F", "M", "F", "M"],
            "churned": [0, 1, 0, 0, 1, 0, 1, 0],
        }
    )


class TestColumnSplit:
    def test_excludes_target(self, frame: pd.DataFrame) -> None:
        numeric, categorical = split_feature_columns(frame, target="churned")
        assert "churned" not in numeric
        assert set(numeric) == {"age", "income"}
        assert categorical == ["gender"]


class TestPipeline:
    def test_onehot_expands_categoricals(self, frame: pd.DataFrame) -> None:
        cfg = FeatureConfig(target="churned", encoding="onehot")
        result = preview_features(frame, cfg)
        # age, income + gender_M, gender_F
        assert result["n_features_out"] == 4

    def test_imputation_removes_nans(self, frame: pd.DataFrame) -> None:
        cfg = FeatureConfig(
            target="churned",
            imputation=ImputationConfig(numeric_strategy="median"),
            scaling="none",
        )
        result = preview_features(frame, cfg)
        flat = [v for row in result["sample"] for v in row]
        assert not any(v != v for v in flat)  # no NaN (NaN != NaN)

    def test_pca_reduces_dimensionality(self, frame: pd.DataFrame) -> None:
        cfg = FeatureConfig(target="churned", pca_enabled=True, pca_components=2)
        result = preview_features(frame, cfg)
        assert result["n_features_out"] == 2

    def test_kbest_selection(self, frame: pd.DataFrame) -> None:
        cfg = FeatureConfig(target="churned", selection_method="kbest", selection_k=2)
        result = preview_features(frame, cfg)
        assert result["n_features_out"] == 2

    def test_invalid_scaling_raises(self, frame: pd.DataFrame) -> None:
        cfg = FeatureConfig(scaling="bogus")
        with pytest.raises(FeatureConfigError):
            build_preprocessor(frame, cfg)
