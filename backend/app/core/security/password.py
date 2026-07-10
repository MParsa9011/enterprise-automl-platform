"""Password hashing using bcrypt.

bcrypt operates on at most 72 bytes of input and silently truncates anything
longer, which is a subtle security foot-gun. We guard against it explicitly: the
API layer rejects over-long passwords via schema validation, and this module
raises rather than truncating, so a truncation can never happen unnoticed.

A configurable cost factor (``rounds``) governs the work factor; ``needs_rehash``
lets the application transparently upgrade stored hashes when the cost is raised.
"""

from __future__ import annotations

import bcrypt

# bcrypt's hard limit on input length, in bytes.
_MAX_PASSWORD_BYTES = 72

# Work factor. 12 is a sensible modern default (~0.3s/hash on commodity CPUs).
_DEFAULT_ROUNDS = 12


def _validate_length(password: str) -> bytes:
    """Encode ``password`` to UTF-8, rejecting inputs bcrypt cannot fully hash."""
    encoded = password.encode("utf-8")
    if len(encoded) > _MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password exceeds bcrypt's {_MAX_PASSWORD_BYTES}-byte limit "
            f"({len(encoded)} bytes); reject it before hashing."
        )
    return encoded


def hash_password(password: str, *, rounds: int = _DEFAULT_ROUNDS) -> str:
    """Return a salted bcrypt hash of ``password`` as a UTF-8 string."""
    encoded = _validate_length(password)
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(encoded, salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Return whether ``password`` matches the stored ``hashed`` value.

    Returns ``False`` (never raises) for malformed hashes or over-long inputs so
    that authentication failures are uniform and timing-safe from the caller's
    perspective.
    """
    try:
        encoded = _validate_length(password)
    except ValueError:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except ValueError:
        return False


def needs_rehash(hashed: str, *, rounds: int = _DEFAULT_ROUNDS) -> bool:
    """Return whether a stored hash uses a weaker cost than the current target."""
    try:
        cost = int(hashed.split("$")[2])
    except (IndexError, ValueError):
        return True
    return cost < rounds
