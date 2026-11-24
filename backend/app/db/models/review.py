from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.enums import ReviewStatus


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("deal_id", name="uq_review_deal"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("rental_deals.id"), unique=True)
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    realtor_id: Mapped[int] = mapped_column(ForeignKey("realtor_profiles.id"), index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"))
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=ReviewStatus.PENDING_MODERATION.value, index=True
    )
    moderation_comment: Mapped[str | None] = mapped_column(Text)
