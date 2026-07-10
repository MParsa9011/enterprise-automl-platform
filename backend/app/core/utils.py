"""Small, dependency-free utility helpers."""

from __future__ import annotations

import re
import unicodedata

_SLUG_STRIP = re.compile(r"[^\w\s-]")
_SLUG_HYPHENATE = re.compile(r"[-\s]+")


def slugify(value: str, *, max_length: int = 160) -> str:
    """Return a URL-safe slug derived from ``value``.

    Normalises unicode to ASCII, lowercases, replaces runs of whitespace and
    punctuation with single hyphens and trims to ``max_length``. Deterministic
    and idempotent, so re-slugifying a slug yields the same slug.
    """
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = _SLUG_STRIP.sub("", ascii_only).strip().lower()
    slug = _SLUG_HYPHENATE.sub("-", cleaned).strip("-")
    return slug[:max_length].rstrip("-") or "item"
