from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.redis import cache_brief, get_cached_brief
from app.models.state import Brief
from app.services.brief import BriefService
from app.services.pipeline import run_watchman_pipeline
from app.services.portfolio import PortfolioService

router = APIRouter(prefix="/brief", tags=["brief"])


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
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Brief:
    """Runs the full LangGraph pipeline and returns the freshly generated brief."""
    holdings = await PortfolioService(db).get_holdings(user_id)

    brief = await run_watchman_pipeline(user_id, holdings)
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Brief generation failed",
        )

    saved = await BriefService(db).save_brief(brief)
    await cache_brief(user_id, saved)
    return saved
