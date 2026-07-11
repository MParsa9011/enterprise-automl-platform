"""Prediction request/response DTOs."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.base import Schema


class PredictionRequest(Schema):
    """A batch of records to predict on.

    Each record is a mapping of feature name to value; the model validates the
    records against its stored feature schema before predicting.
    """

    records: list[dict[str, Any]] = Field(min_length=1, max_length=1000)


class PredictionItem(Schema):
    """A single prediction, with class probabilities for classifiers."""

    prediction: Any
    probabilities: dict[str, float] | None = None


class PredictionResponse(Schema):
    """Predictions for a batch of records."""

    model_id: str
    model_version: int
    task_type: str
    predictions: list[PredictionItem]
