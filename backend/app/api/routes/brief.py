import hmac
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import bearer_scheme, get_current_user_id
from app.core.redis import get_cached_brief
from app.core.security import verify_supabase_jwt
from app.models.state import Brief
from app.services.brief import BriefService
from app.services.pipeline import generate_brief_for_user

router = APIRouter(prefix="/brief", tags=["brief"])


class GenerateBriefRequest(BaseModel):
    """Optional body for /generate. ``user_id`` is honoured only for trusted
    internal service calls (valid X-Internal-Secret); JWT callers are ignored."""

    user_id: Optional[str] = None


def _resolve_generate_user_id(
    internal_secret: Optional[str],
    body_user_id: Optional[str],
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str:
    """Authenticate a /generate request via either a trusted internal secret or
    a Supabase JWT, and return the user_id to generate a brief for.

    A trusted caller (e.g. STK's backend) presents the shared secret in the
    X-Internal-Secret header and the target user in the request body. Everyone
    else must present a valid Supabase bearer token, as before.
    """
    configured = settings.INTERNAL_SERVICE_SECRET
    if (
        configured
        and internal_secret is not None
        and hmac.compare_digest(internal_secret, configured)
    ):
        if not body_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required for internal service calls",
            )
        return body_user_id

    # Fall back to Supabase JWT auth (Watchman's own authenticated users).
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_supabase_jwt(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )
    return user_id


@router.get("/today", response_model=Brief)
async def get_today_brief(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Brief:
    # Redis cache first — avoids re-querying the DB for repeat reads.
    cached = await get_cached_brief(user_id)
    if cached is not None:
        return cached

    service = BriefService(db)
    brief = await service.get_today_brief(user_id)
    if brief is not None:
        return brief

    # No brief generated yet today; return a placeholder until one is generated.
    return Brief(
        user_id=user_id,
        date=datetime.utcnow(),
        headline="Your portfolio brief is being prepared",
        portfolio_health=50,
        sections=[],
        alerts=[],
    )


@router.post("/generate", response_model=Brief)
async def generate_brief(
    body: Optional[GenerateBriefRequest] = None,
    x_internal_secret: Annotated[Optional[str], Header()] = None,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Security(bearer_scheme)
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> Brief:
    """Runs the full LangGraph pipeline and returns the freshly generated brief.

    Accepts either a Supabase JWT (Watchman's own users) or a trusted internal
    service call (STK's backend) carrying the shared secret and target user_id.
    """
    user_id = _resolve_generate_user_id(
        x_internal_secret, body.user_id if body else None, credentials
    )

    saved = await generate_brief_for_user(user_id, db)
    if saved is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Brief generation failed",
        )
    return saved
