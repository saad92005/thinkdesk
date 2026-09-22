from app.auth.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)


def test_hashed_password_is_not_plaintext_and_verifies_correctly():
    hashed = hash_password("correcthorse123")
    assert hashed != "correcthorse123"
    assert verify_password("correcthorse123", hashed) is True


def test_wrong_password_fails_verification():
    hashed = hash_password("correcthorse123")
    assert verify_password("wrongpassword", hashed) is False


def test_session_tokens_are_unique_and_high_entropy():
    tokens = {generate_session_token() for _ in range(50)}
    assert len(tokens) == 50
    assert all(len(t) >= 32 for t in tokens)


def test_session_token_hash_is_deterministic_but_not_reversible():
    token = generate_session_token()
    hash_a = hash_session_token(token)
    hash_b = hash_session_token(token)
    assert hash_a == hash_b
    assert hash_a != token
