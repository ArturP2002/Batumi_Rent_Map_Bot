from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import DealStatus, ReviewStatus
from app.db.models import RealtorProfile, RentalDeal, Review, User
from app.schemas.deals import ReviewCreateIn
from app.services.audit import write_moderation


async def create_review(db: AsyncSession, author: User, data: ReviewCreateIn) -> Review:
    deal = await db.get(RentalDeal, data.deal_id)
    if not deal or deal.status != DealStatus.CONFIRMED.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Confirmed deal required")
    if deal.client_user_id != author.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only deal client can review")
    existing = (
        await db.execute(select(Review).where(Review.deal_id == deal.id))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Review already exists for deal")

    review = Review(
        deal_id=deal.id,
        author_user_id=author.id,
        realtor_id=deal.realtor_id,
        property_id=deal.property_id,
        rating=data.rating,
        text=data.text.strip(),
        status=ReviewStatus.PENDING_MODERATION.value,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def moderate_review(
    db: AsyncSession,
    review: Review,
    *,
    action: str,
    actor_id: int,
    comment: str | None = None,
) -> Review:
    if action == "publish":
        review.status = ReviewStatus.PUBLISHED.value
    elif action == "reject":
        review.status = ReviewStatus.REJECTED.value
        review.moderation_comment = comment
    elif action == "hide":
        review.status = ReviewStatus.HIDDEN.value
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown action")
    await db.commit()
    await recalculate_realtor_rating(db, review.realtor_id)
    await write_moderation(db, "review", review.id, action, actor_id, comment)
    return review


async def recalculate_realtor_rating(db: AsyncSession, realtor_id: int) -> None:
    result = await db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(
            Review.realtor_id == realtor_id,
            Review.status == ReviewStatus.PUBLISHED.value,
        )
    )
    avg, count = result.one()
    realtor = await db.get(RealtorProfile, realtor_id)
    if realtor:
        realtor.rating_avg = round(float(avg or 0), 1)
        realtor.rating_count = int(count or 0)
        await db.commit()


async def list_published_reviews(db: AsyncSession, realtor_id: int) -> list[Review]:
    result = await db.execute(
        select(Review)
        .where(
            Review.realtor_id == realtor_id,
            Review.status == ReviewStatus.PUBLISHED.value,
        )
        .order_by(Review.created_at.desc())
    )
    return list(result.scalars().all())
