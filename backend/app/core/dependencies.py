from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_supabase_jwt

# auto_error=False so a missing header yields 403 (below) rather than the 401
# that newer FastAPI raises by default; an invalid token still yields 401.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> dict:
    """Validate the bearer token and return the decoded JWT payload."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_supabase_jwt(credentials.credentials)


def get_current_user_id(user: dict = Depends(get_current_user)) -> str:
    """Extract the Supabase user ID (the ``sub`` claim) from the payload."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id
