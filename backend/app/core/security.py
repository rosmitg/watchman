from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

# Supabase signs access tokens with HS256 using the project's JWT secret.
ALGORITHM = "HS256"
AUDIENCE = "authenticated"


def verify_supabase_jwt(token: str) -> dict:
    """Decode and validate a Supabase JWT.

    Returns the decoded payload on success. Raises HTTPException 401 if the
    token is malformed, has an invalid signature, or has expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return payload
