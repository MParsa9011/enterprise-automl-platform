"""Unit tests for the dataset profiling engine."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.core.constants import DatasetFileType
from app.ml.io import detect_file_type, read_tabular
from app.ml.profiling import infer_semantic_type, profile_dataframe

pytestmark = pytest.mark.unit


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "age": [25, 32, 47, np.nan, 51, 200],  # includes a missing + an outlier
            "income": [50000, 64000, 120000, 80000, 95000, 70000],
            "gender": ["M", "F", "F", "M", "F", "M"],
            "flag": [True, False, True, True, False, True],
        }
    )


class TestTypeInference:
    def test_numeric(self, frame: pd.DataFrame) -> None:
        assert infer_semantic_type(frame["income"]) == "numeric"

    def test_categorical(self, frame: pd.DataFrame) -> None:
        assert infer_semantic_type(frame["gender"]) == "categorical"

    def test_boolean(self, frame: pd.DataFrame) -> None:
        assert infer_semantic_type(frame["flag"]) == "boolean"

    def test_high_cardinality_text(self) -> None:
        series = pd.Series([f"id-{i}" for i in range(100)])
        assert infer_semantic_type(series) == "text"


class TestProfile:
    def test_shape(self, frame: pd.DataFrame) -> None:
        profile = profile_dataframe(frame)
        assert profile.n_rows == 6
        assert profile.n_columns == 4

    def test_missing_detection(self, frame: pd.DataFrame) -> None:
        profile = profile_dataframe(frame)
        age = next(c for c in profile.columns if c["name"] == "age")
        assert age["n_missing"] == 1
        assert profile.statistics["overview"]["missing_cells"] == 1

    def test_outlier_detection(self, frame: pd.DataFrame) -> None:
        profile = profile_dataframe(frame)
        assert profile.statistics["numeric"]["age"]["n_outliers"] == 1

    def test_correlations_present(self, frame: pd.DataFrame) -> None:
        profile = profile_dataframe(frame)
        assert "matrix" in profile.statistics["correlations"]
        assert profile.statistics["overview"]["n_numeric"] == 2

    def test_profile_is_json_serialisable(self, frame: pd.DataFrame) -> None:
        profile = profile_dataframe(frame)
        # Must not raise — NaN/inf/numpy types are coerced away.
        json.dumps(profile.statistics)
        json.dumps(profile.columns)


class TestDataLoading:
    def test_csv_roundtrip(self, frame: pd.DataFrame) -> None:
        data = frame.to_csv(index=False).encode()
        loaded = read_tabular(data, detect_file_type("f.csv"))
        assert loaded.shape == frame.shape

    def test_detect_file_type(self) -> None:
        assert detect_file_type("a.csv") == DatasetFileType.CSV
        assert detect_file_type("a.xlsx") == DatasetFileType.EXCEL
