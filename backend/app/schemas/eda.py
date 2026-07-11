"""EDA response DTOs.

Figures are Plotly figure specifications (``data`` + ``layout`` dicts) rendered
client-side, so they are typed loosely as JSON objects rather than modelled field
by field.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field

from app.schemas.base import Schema

Figure = dict[str, Any]


class EdaResponse(Schema):
    """Bundle of EDA figures for a dataset version."""

    dataset_id: uuid.UUID
    version: int
    missing_values: Figure
    correlation_heatmap: Figure | None = None
    histograms: dict[str, Figure] = Field(default_factory=dict)
    boxplots: dict[str, Figure] = Field(default_factory=dict)
    categorical: dict[str, Figure] = Field(default_factory=dict)
    scatter: Figure | None = None
