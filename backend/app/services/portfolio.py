from sqlalchemy import delete, select, text
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

    async def add_holdings(self, user_id: str, rows: list[dict]) -> None:
        """Insert or update individual holdings (manual entry / CSV import).

        Unlike :meth:`sync_holdings`, this merges with the existing holdings
        rather than replacing them; a row whose ticker already exists is updated
        in place so repeated adds don't create duplicates.
        """
        portfolio = await self.get_or_create_portfolio(user_id)

        for row in rows:
            result = await self.db.execute(
                select(HoldingModel).where(
                    HoldingModel.portfolio_id == portfolio.id,
                    HoldingModel.ticker == row["ticker"],
                )
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                existing.qty = row["qty"]
                existing.avg_entry_price = row["avg_entry_price"]
            else:
                self.db.add(
                    HoldingModel(
                        portfolio_id=portfolio.id,
                        ticker=row["ticker"],
                        qty=row["qty"],
                        avg_entry_price=row["avg_entry_price"],
                    )
                )

        await self.db.commit()

    async def update_holding_prices(
        self, user_id: str, prices: dict[str, float]
    ) -> None:
        """Persist fresh live prices for the user's holdings.

        ``market_value`` is recomputed from the holding's quantity so it stays
        consistent with the new ``current_price``.
        """
        if not prices:
            return

        portfolio = await self.get_or_create_portfolio(user_id)
        result = await self.db.execute(
            select(HoldingModel).where(HoldingModel.portfolio_id == portfolio.id)
        )
        for holding in result.scalars().all():
            price = prices.get(holding.ticker)
            if price is not None:
                holding.current_price = price
                holding.market_value = float(holding.qty) * price

        await self.db.commit()

    async def get_holdings(self, user_id: str) -> list[Holding]:
        """Read the user's holdings directly from STK's shared ``holdings`` table.

        Watchman now shares STK's database. STK keys holdings by a varchar(64)
        ``user_id`` and stores ``shares``/``avg_cost`` columns, so we map those
        onto Watchman's ``qty``/``avg_entry_price`` here. STK does not persist a
        live ``current_price`` or ``market_value`` on the row — the fundamentals
        agent fetches fresh prices during the brief pipeline — so both default
        to 0.0.
        """
        result = await self.db.execute(
            text(
                "SELECT ticker, shares, avg_cost FROM holdings "
                "WHERE user_id = :user_id ORDER BY ticker"
            ),
            {"user_id": user_id},
        )

        return [
            Holding(
                ticker=row.ticker,
                qty=float(row.shares),
                avg_entry_price=float(row.avg_cost),
                current_price=0.0,
                market_value=0.0,
            )
            for row in result
        ]

    async def get_all_user_ids(self) -> list[str]:
        """Return every distinct user_id present in STK's shared holdings table.

        Used by the daily scheduler to generate a brief for each user who holds
        positions.
        """
        result = await self.db.execute(
            text("SELECT DISTINCT user_id FROM holdings ORDER BY user_id")
        )
        return [row.user_id for row in result]
