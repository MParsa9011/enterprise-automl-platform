"""Tabular data loading and JSON-safe coercion helpers."""

from __future__ import annotations

import math
from io import BytesIO
from typing import Any

import numpy as np
import pandas as pd

from app.core.constants import DatasetFileType

# Cap on rows parsed for profiling to bound memory/latency on huge uploads.
MAX_PROFILE_ROWS = 1_000_000


class DataLoadError(ValueError):
    """Raised when an uploaded file cannot be parsed into a table."""


def read_tabular(data: bytes, file_type: DatasetFileType) -> pd.DataFrame:
    """Parse raw bytes into a :class:`pandas.DataFrame`.

    Raises :class:`DataLoadError` with a user-safe message on any parse failure
    so the API can surface a clean 422 rather than an opaque stack trace.
    """
    buffer = BytesIO(data)
    try:
        if file_type == DatasetFileType.CSV:
            frame = pd.read_csv(buffer)
        elif file_type == DatasetFileType.EXCEL:
            frame = pd.read_excel(buffer, engine="openpyxl")
        elif file_type == DatasetFileType.PARQUET:
            frame = pd.read_parquet(buffer)
        else:  # pragma: no cover - guarded by enum
            raise DataLoadError(f"Unsupported file type: {file_type}")
    except DataLoadError:
        raise
    except Exception as exc:
        raise DataLoadError(f"Could not parse file as {file_type.value}: {exc}") from exc

    if frame.empty:
        raise DataLoadError("The uploaded file contains no rows.")
    if frame.shape[1] == 0:
        raise DataLoadError("The uploaded file contains no columns.")
    return frame


def detect_file_type(filename: str) -> DatasetFileType:
    """Infer the dataset file type from a filename extension."""
    lowered = filename.lower()
    if lowered.endswith(".csv") or lowered.endswith(".txt"):
        return DatasetFileType.CSV
    if lowered.endswith((".xlsx", ".xls")):
        return DatasetFileType.EXCEL
    if lowered.endswith(".parquet"):
        return DatasetFileType.PARQUET
    raise DataLoadError(
        f"Unsupported file extension for {filename!r}; expected .csv, .xlsx or .parquet."
    )


def json_safe(value: Any) -> Any:
    """Recursively convert numpy/pandas scalars and NaN/inf into JSON-safe types.

    JSON has no representation for NaN/Infinity, and numpy scalar types are not
    natively serialisable; this normalises both so profiles can be stored in a
    JSON column and returned over the API without custom encoders.
    """
    if value is None:
        return None
    if isinstance(value, float | np.floating):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return [json_safe(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): json_safe(val) for key, val in value.items()}
    if isinstance(value, list | tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value
