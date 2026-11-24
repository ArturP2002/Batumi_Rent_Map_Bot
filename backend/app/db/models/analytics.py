from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), index=True)
    realtor_id: Mapped[int | None] = mapped_column(ForeignKey("realtor_profiles.id"))
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    referrer: Mapped[str | None] = mapped_column(String(255))
    context_json: Mapped[str | None] = mapped_column(Text)


class DailyAggregate(Base, TimestampMixin):
    __tablename__ = "daily_aggregates"
    __table_args__ = (
        UniqueConstraint("day", "metric", "entity_type", "entity_id", name="uq_daily_agg"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), default="global")
    entity_id: Mapped[int | None] = mapped_column(BigInteger)
    value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
