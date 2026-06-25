import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.portfolio import Base


class Brief(Base):
    __tablename__ = "briefs"
    __table_args__ = (
        # One brief per user per day.
        UniqueConstraint("user_id", "date", name="uq_briefs_user_id_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    # STK's holdings.user_id is varchar(64), so briefs are keyed by the same
    # string user id (see migration 0003) rather than a UUID.
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    headline: Mapped[str] = mapped_column(String, nullable=False)
    portfolio_health: Mapped[int] = mapped_column(Integer, nullable=False)
    sections: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    alerts: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
