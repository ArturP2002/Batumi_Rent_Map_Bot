from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.enums import ConfirmationDecision, ConfirmationSide, ContactChannel, DealStatus, InquiryStatus


class Inquiry(Base, TimestampMixin):
    __tablename__ = "inquiries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    realtor_id: Mapped[int] = mapped_column(ForeignKey("realtor_profiles.id"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    channel: Mapped[str] = mapped_column(String(32), default=ContactChannel.TELEGRAM.value)
    status: Mapped[str] = mapped_column(
        String(32), default=InquiryStatus.NEW.value, index=True, nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    deals: Mapped[list[RentalDeal]] = relationship(back_populates="inquiry")


class RentalDeal(Base, TimestampMixin):
    __tablename__ = "rental_deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    inquiry_id: Mapped[int | None] = mapped_column(ForeignKey("inquiries.id"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    realtor_id: Mapped[int] = mapped_column(ForeignKey("realtor_profiles.id"), index=True)
    client_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(
        String(32), default=DealStatus.PENDING.value, index=True, nullable=False
    )
    admin_comment: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    inquiry: Mapped[Inquiry | None] = relationship(back_populates="deals")
    confirmations: Mapped[list[DealConfirmation]] = relationship(
        back_populates="deal", cascade="all, delete-orphan"
    )


class DealConfirmation(Base, TimestampMixin):
    __tablename__ = "deal_confirmations"
    __table_args__ = (UniqueConstraint("deal_id", "side", name="uq_deal_side"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("rental_deals.id", ondelete="CASCADE"), index=True)
    side: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(
        String(32), default=ConfirmationDecision.PENDING.value, nullable=False
    )
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comment: Mapped[str | None] = mapped_column(Text)

    deal: Mapped[RentalDeal] = relationship(back_populates="confirmations")
