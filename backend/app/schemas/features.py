"""Feature-engineering configuration and preview DTOs.

These pydantic DTOs are the validated API surface; they map to the plain
:mod:`app.ml.features` dataclasses so the ML layer stays free of web dependencies.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.ml.features import FeatureConfig, ImputationConfig
from app.schemas.base import Schema


class ImputationConfigIn(Schema):
    """Missing-value imputation configuration."""

    numeric_strategy: Literal["mean", "median", "most_frequent", "constant"] = "median"
    categorical_strategy: Literal["most_frequent", "constant"] = "most_frequent"
    numeric_fill_value: float = 0.0
    categorical_fill_value: str = "missing"

    def to_dataclass(self) -> ImputationConfig:
        """Map to the ML-layer dataclass."""
        return ImputationConfig(
            numeric_strategy=self.numeric_strategy,
            categorical_strategy=self.categorical_strategy,
            numeric_fill_value=self.numeric_fill_value,
            categorical_fill_value=self.categorical_fill_value,
        )


class FeatureConfigIn(Schema):
    """Declarative feature-engineering configuration."""

    target: str | None = Field(default=None, description="Target column to exclude from features.")
    imputation: ImputationConfigIn = Field(default_factory=ImputationConfigIn)
    encoding: Literal["onehot", "ordinal"] = "onehot"
    scaling: Literal["standard", "minmax", "robust", "none"] = "standard"
    selection_method: Literal["none", "variance", "kbest"] = "none"
    selection_k: int = Field(default=10, ge=1, le=1000)
    variance_threshold: float = Field(default=0.0, ge=0.0)
    pca_enabled: bool = False
    pca_components: float | int | None = Field(default=None, ge=0)

    def to_config(self) -> FeatureConfig:
        """Map to the ML-layer :class:`FeatureConfig` dataclass."""
        return FeatureConfig(
            target=self.target,
            imputation=self.imputation.to_dataclass(),
            encoding=self.encoding,
            scaling=self.scaling,
            selection_method=self.selection_method,
            selection_k=self.selection_k,
            variance_threshold=self.variance_threshold,
            pca_enabled=self.pca_enabled,
            pca_components=self.pca_components,
        )


class FeaturePreviewResponse(Schema):
    """Summary of a fitted feature pipeline's output."""

    n_features_in: int
    n_features_out: int
    numeric_columns: list[str]
    categorical_columns: list[str]
    output_features: list[str]
    sample: list[list[Any]]
