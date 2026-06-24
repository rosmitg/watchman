import time
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from jose import jwk, jwt

from app.core import security
from app.main import app

TEST_KID = "test-key-1"


def _make_es256_keypair():
    """Generate an EC P-256 keypair and the matching public JWK (with kid)."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_jwk = jwk.construct(public_pem, algorithm=security.ALGORITHM).to_dict()
    public_jwk["kid"] = TEST_KID
    return private_pem, public_jwk


def _sign(private_pem, claims, kid=TEST_KID):
    return jwt.encode(
        claims,
        private_pem,
        algorithm=security.ALGORITHM,
        headers={"kid": kid},
    )


@pytest.fixture
def es256_keys():
    """Provide a keypair and patch the JWKS fetch to serve its public key."""
    private_pem, public_jwk = _make_es256_keypair()
    security._jwks_cache = None
    with patch.object(security, "_fetch_jwks", return_value={"keys": [public_jwk]}):
        yield private_pem
    security._jwks_cache = None


@pytest.mark.asyncio
async def test_auth_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_me_without_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_me_with_invalid_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
    assert response.status_code == 401


def test_verify_valid_es256_token(es256_keys):
    """A token signed with the JWKS key and matching kid verifies successfully."""
    token = _sign(
        es256_keys,
        {"sub": "user-123", "aud": security.AUDIENCE, "exp": int(time.time()) + 3600},
    )
    payload = security.verify_supabase_jwt(token)
    assert payload["sub"] == "user-123"


def test_verify_expired_token_rejected(es256_keys):
    """An expired but correctly-signed token is rejected with 401."""
    token = _sign(
        es256_keys,
        {"sub": "user-123", "aud": security.AUDIENCE, "exp": int(time.time()) - 10},
    )
    with pytest.raises(HTTPException) as exc:
        security.verify_supabase_jwt(token)
    assert exc.value.status_code == 401


def test_verify_unknown_kid_rejected(es256_keys):
    """A token whose kid isn't in the JWKS is rejected with 401."""
    token = _sign(
        es256_keys,
        {"sub": "user-123", "aud": security.AUDIENCE, "exp": int(time.time()) + 3600},
        kid="some-other-kid",
    )
    with pytest.raises(HTTPException) as exc:
        security.verify_supabase_jwt(token)
    assert exc.value.status_code == 401


def test_verify_malformed_token_rejected():
    """A malformed token is rejected with 401 without fetching the JWKS."""
    with patch.object(security, "_fetch_jwks") as mock_fetch:
        with pytest.raises(HTTPException) as exc:
            security.verify_supabase_jwt("not-a-real-token")
    assert exc.value.status_code == 401
    mock_fetch.assert_not_called()


def test_jwks_is_cached(es256_keys):
    """The JWKS is fetched once and reused across verifications."""
    security._jwks_cache = None
    claims = {"sub": "user-123", "aud": security.AUDIENCE, "exp": int(time.time()) + 3600}
    with patch.object(
        security, "_fetch_jwks", wraps=security._fetch_jwks
    ) as spy:
        security.verify_supabase_jwt(_sign(es256_keys, claims))
        security.verify_supabase_jwt(_sign(es256_keys, claims))
    spy.assert_called_once()
