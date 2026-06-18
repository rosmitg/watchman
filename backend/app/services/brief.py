from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brief import Brief as BriefModel
from app.models.state import Brief


class BriefService:
    """Database operations for a user's daily portfolio brief."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_today_brief(self, user_id: str) -> Brief | None:
        result = await self.db.execute(
            select(BriefModel).where(
                BriefModel.user_id == user_id,
                BriefModel.date == date.today(),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_pydantic(row)

    async def save_brief(self, brief: Brief) -> Brief:
        """Upsert a brief, keyed on (user_id, date)."""
        sections = [s.model_dump(mode="json") for s in brief.sections]
        alerts = [a.model_dump(mode="json") for a in brief.alerts]

        values = {
            "user_id": brief.user_id,
            "date": brief.date.date()
            if isinstance(brief.date, datetime)
            else brief.date,
            "headline": brief.headline,
            "portfolio_health": brief.portfolio_health,
            "sections": sections,
            "alerts": alerts,
        }

        stmt = insert(BriefModel).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_briefs_user_id_date",
            set_={
                "headline": stmt.excluded.headline,
                "portfolio_health": stmt.excluded.portfolio_health,
                "sections": stmt.excluded.sections,
                "alerts": stmt.excluded.alerts,
            },
        ).returning(BriefModel)

        result = await self.db.execute(stmt)
        await self.db.commit()
        row = result.scalar_one()
        return self._to_pydantic(row)

    @staticmethod
    def _to_pydantic(row: BriefModel) -> Brief:
        return Brief(
            user_id=str(row.user_id),
            date=datetime(row.date.year, row.date.month, row.date.day),
            headline=row.headline,
            portfolio_health=row.portfolio_health,
            sections=row.sections,
            alerts=row.alerts,
        )
