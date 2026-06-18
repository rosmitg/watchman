from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.models.state import Holding
from app.services.alpaca import AlpacaService
from app.services.portfolio import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/holdings", response_model=list[Holding])
async def get_holdings(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[Holding]:
    service = PortfolioService(db)
    return await service.get_holdings(user_id)


@router.post("/sync", response_model=list[Holding])
async def sync_portfolio(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[Holding]:
    alpaca = AlpacaService(settings.ALPACA_API_KEY, settings.ALPACA_SECRET_KEY)
    positions = alpaca.get_positions()

    service = PortfolioService(db)
    await service.sync_holdings(user_id, positions)
    return await service.get_holdings(user_id)


@router.get("/summary")
async def get_summary(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = PortfolioService(db)
    holdings = await service.get_holdings(user_id)

    return {
        "total_market_value": sum(h.market_value for h in holdings),
        "num_holdings": len(holdings),
        "tickers": [h.ticker for h in holdings],
    }
