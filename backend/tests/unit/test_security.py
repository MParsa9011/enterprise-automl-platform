"""Unit tests for password hashing and JWT token helpers."""

from __future__ import annotations

import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import (
    TokenType,
    create_token_pair,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)

pytestmark = pytest.mark.unit


class TestPasswordHashing:
    def test_hash_is_salted_and_verifies(self) -> None:
        hashed = hash_password("Sup3r-secret")
        assert hashed != "Sup3r-secret"
        assert verify_password("Sup3r-secret", hashed)

    def test_two_hashes_of_same_password_differ(self) -> None:
        assert hash_password("Sup3r-secret") != hash_password("Sup3r-secret")

    def test_wrong_password_is_rejected(self) -> None:
        hashed = hash_password("Sup3r-secret")
        assert not verify_password("wrong", hashed)

    def test_overlong_password_is_rejected_not_truncated(self) -> None:
        with pytest.raises(ValueError):
            hash_password("a" * 100)

    def test_verify_returns_false_for_malformed_hash(self) -> None:
        assert not verify_password("whatever", "not-a-bcrypt-hash")

    def test_needs_rehash_detects_low_cost(self) -> None:
        low_cost = hash_password("password1", rounds=4)
        assert needs_rehash(low_cost, rounds=12)
        assert not needs_rehash(hash_password("password1", rounds=12), rounds=12)


class TestTokens:
    def test_token_pair_roundtrip(self) -> None:
        pair, jti = create_token_pair("user-123", roles=["admin"])
        access = decode_token(pair.access_token, expected_type=TokenType.ACCESS)
        refresh = decode_token(pair.refresh_token, expected_type=TokenType.REFRESH)
        assert access.sub == "user-123"
        assert access.roles == ["admin"]
        assert refresh.jti == jti

    def test_wrong_token_type_is_rejected(self) -> None:
        pair, _ = create_token_pair("user-123")
        with pytest.raises(AuthenticationError) as exc:
            decode_token(pair.access_token, expected_type=TokenType.REFRESH)
        assert exc.value.code == "token_wrong_type"

    def test_tampered_token_is_rejected(self) -> None:
        pair, _ = create_token_pair("user-123")
        tampered = pair.access_token[:-2] + ("aa" if pair.access_token[-2:] != "aa" else "bb")
        with pytest.raises(AuthenticationError):
            decode_token(tampered)
