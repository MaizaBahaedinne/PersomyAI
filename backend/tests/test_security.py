from app.core.security import (
    constant_time_equals,
    fingerprint,
    generate_token,
    hash_password,
    needs_rehash,
    verify_password,
)


def test_password_hash_is_argon2id_and_verifies():
    h = hash_password("Correct-Horse-42x")
    assert h.startswith("$argon2id$")
    assert "Correct-Horse" not in h
    assert verify_password(h, "Correct-Horse-42x")
    assert not verify_password(h, "wrong")
    assert not needs_rehash(h)


def test_verify_password_handles_garbage_hash():
    assert verify_password("not-a-hash", "x") is False


def test_tokens_are_unique_and_long():
    tokens = {generate_token() for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(t) >= 43 for t in tokens)


def test_fingerprint_is_stable_sha256():
    assert fingerprint("abc") == fingerprint("abc")
    assert len(fingerprint("abc")) == 64
    assert fingerprint("abc") != fingerprint("abd")


def test_constant_time_equals():
    assert constant_time_equals("a", "a")
    assert not constant_time_equals("a", "b")
