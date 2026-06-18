from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.models.state import Brief
from app.services.brief import BriefService

router = APIRouter(prefix="/brief", tags=["brief"])


@router.get("/today", response_model=Brief)
async def get_today_brief(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Brief:
    service = BriefService(db)
    brief = await service.get_today_brief(user_id)
    if brief is not None:
        return brief

    # No brief generated yet today; return a placeholder until Sprint 2 agents
    # populate the real thing.
    return Brief(
        user_id=user_id,
        date=datetime.utcnow(),
        headline="Your portfolio brief is being prepared",
        portfolio_health=50,
        sections=[],
        alerts=[],
    )


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_brief(
    user_id: str = Depends(get_current_user_id),
) -> dict:
    # Stub: brief-generation agents will be wired in during Sprint 2.
    return {"message": "Brief generation queued"}
