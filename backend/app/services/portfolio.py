from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Holding as HoldingModel
from app.models.portfolio import Portfolio
from app.models.state import Holding


class PortfolioService:
    """Database operations for a user's portfolio and holdings."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create_portfolio(self, user_id: str) -> Portfolio:
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.user_id == user_id)
        )
        portfolio = result.scalar_one_or_none()
        if portfolio is None:
            portfolio = Portfolio(user_id=user_id)
            self.db.add(portfolio)
            await self.db.commit()
            await self.db.refresh(portfolio)
        return portfolio

    async def sync_holdings(self, user_id: str, positions: list[dict]) -> None:
        """Replace the portfolio's holdings with fresh Alpaca positions."""
        portfolio = await self.get_or_create_portfolio(user_id)

        await self.db.execute(
            delete(HoldingModel).where(HoldingModel.portfolio_id == portfolio.id)
        )

        for pos in positions:
            self.db.add(
                HoldingModel(
                    portfolio_id=portfolio.id,
                    ticker=pos["ticker"],
                    qty=pos["qty"],
                    avg_entry_price=pos["avg_entry_price"],
                    current_price=pos.get("current_price"),
                    market_value=pos.get("market_value"),
                )
            )

        await self.db.commit()

    async def get_holdings(self, user_id: str) -> list[Holding]:
        portfolio = await self.get_or_create_portfolio(user_id)

        result = await self.db.execute(
            select(HoldingModel).where(HoldingModel.portfolio_id == portfolio.id)
        )
        rows = result.scalars().all()

        return [
            Holding(
                ticker=h.ticker,
                qty=float(h.qty),
                avg_entry_price=float(h.avg_entry_price),
                current_price=float(h.current_price) if h.current_price is not None else 0.0,
                market_value=float(h.market_value) if h.market_value is not None else 0.0,
            )
            for h in rows
        ]
