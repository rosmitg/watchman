import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

# Supabase signs access tokens with ES256 (asymmetric). We verify against the
# project's published public keys (JWKS) rather than a shared secret.
ALGORITHM = "ES256"
AUDIENCE = "authenticated"
JWKS_PATH = "/auth/v1/.well-known/jwks.json"

# In-memory cache of the fetched JWKS so we don't hit Supabase on every request.
_jwks_cache: dict | None = None


def _jwks_url() -> str:
    return f"{settings.SUPABASE_URL.rstrip('/')}{JWKS_PATH}"


def _fetch_jwks() -> dict:
    """Fetch the JWKS document from Supabase."""
    response = httpx.get(_jwks_url(), timeout=10.0)
    response.raise_for_status()
    return response.json()


def _get_jwks(force_refresh: bool = False) -> dict:
    """Return the cached JWKS, fetching (and caching) it on first use.

    Pass ``force_refresh=True`` to bypass the cache, e.g. after a key rotation
    leaves the cached set without a matching ``kid``.
    """
    global _jwks_cache
    if _jwks_cache is None or force_refresh:
        _jwks_cache = _fetch_jwks()
    return _jwks_cache


def _find_key(jwks: dict, kid: str) -> dict | None:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def _get_signing_key(kid: str) -> dict | None:
    """Find the JWK matching ``kid``, refreshing the cache once on a miss."""
    key = _find_key(_get_jwks(), kid)
    if key is None:
        # The cache may be stale after a key rotation; refresh once and retry.
        key = _find_key(_get_jwks(force_refresh=True), kid)
    return key


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_supabase_jwt(token: str) -> dict:
    """Decode and validate a Supabase JWT.

    Resolves the signing key from Supabase's JWKS by the token's ``kid`` header,
    then verifies the ES256 signature. Returns the decoded payload on success.
    Raises HTTPException 401 if the token is malformed, references an unknown
    key, has an invalid signature, or has expired.
    """
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except JWTError as exc:
        raise _unauthorized("Invalid or expired token") from exc

    if not kid:
        raise _unauthorized("Invalid or expired token")

    try:
        key = _get_signing_key(kid)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch signing keys",
        ) from exc

    if key is None:
        raise _unauthorized("Invalid or expired token")

    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
        )
    except JWTError as exc:
        raise _unauthorized("Invalid or expired token") from exc

    return payload
