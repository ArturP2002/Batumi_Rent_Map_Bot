from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import (
    ConfirmationDecision,
    ConfirmationSide,
    DealStatus,
    InquiryStatus,
    PropertyStatus,
    RentType,
)
from app.db.models import DealConfirmation, Inquiry, Property, RentalDeal, User
from app.schemas.deals import DealCreateIn, InquiryCreateIn
from app.services.calendar import add_interval, list_intervals
from app.schemas.property import IntervalIn
from app.services.audit import write_audit, write_moderation


async def upsert_inquiry(db: AsyncSession, user: User, data: InquiryCreateIn) -> Inquiry:
    existing = (
        await db.execute(
            select(Inquiry).where(
                Inquiry.user_id == user.id,
                Inquiry.property_id == data.property_id,
                Inquiry.realtor_id == data.realtor_id,
                Inquiry.status.in_(
                    [
                        InquiryStatus.NEW.value,
                        InquiryStatus.IN_PROGRESS.value,
                        InquiryStatus.AWAITING_CONFIRMATIONS.value,
                    ]
                ),
            )
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if existing:
        existing.channel = data.channel
        existing.last_event_at = now
        if existing.status == InquiryStatus.NEW.value:
            existing.status = InquiryStatus.IN_PROGRESS.value
        await db.commit()
        await db.refresh(existing)
        return existing

    inquiry = Inquiry(
        user_id=user.id,
        realtor_id=data.realtor_id,
        property_id=data.property_id,
        channel=data.channel,
        status=InquiryStatus.NEW.value,
        last_event_at=now,
    )
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)
    return inquiry


async def create_deal(db: AsyncSession, data: DealCreateIn, *, actor: User) -> RentalDeal:
    deal = RentalDeal(
        inquiry_id=data.inquiry_id,
        property_id=data.property_id,
        realtor_id=data.realtor_id,
        client_user_id=data.client_user_id,
        start_date=data.start_date,
        end_date=data.end_date,
        status=DealStatus.PENDING.value,
    )
    db.add(deal)
    await db.flush()
    for side in (ConfirmationSide.REALTOR, ConfirmationSide.CLIENT, ConfirmationSide.ADMIN):
        decision = ConfirmationDecision.PENDING.value
        actor_id = None
        decided_at = None
        if side == ConfirmationSide.REALTOR:
            decision = ConfirmationDecision.APPROVED.value
            actor_id = actor.id
            decided_at = datetime.now(timezone.utc)
        db.add(
            DealConfirmation(
                deal_id=deal.id,
                side=side.value,
                decision=decision,
                actor_user_id=actor_id,
                decided_at=decided_at,
            )
        )
    if data.inquiry_id:
        inquiry = await db.get(Inquiry, data.inquiry_id)
        if inquiry:
            inquiry.status = InquiryStatus.AWAITING_CONFIRMATIONS.value
    await db.commit()
    await write_audit(db, actor.id, "deal.create", "rental_deal", deal.id)
    return await get_deal(db, deal.id)


async def get_deal(db: AsyncSession, deal_id: int) -> RentalDeal:
    result = await db.execute(
        select(RentalDeal)
        .where(RentalDeal.id == deal_id)
        .options(selectinload(RentalDeal.confirmations))
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found")
    return deal


async def decide_confirmation(
    db: AsyncSession,
    deal: RentalDeal,
    *,
    side: ConfirmationSide,
    actor: User,
    decision: str,
    comment: str | None = None,
) -> RentalDeal:
    if decision not in (ConfirmationDecision.APPROVED.value, ConfirmationDecision.REJECTED.value):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid decision")

    conf = next((c for c in deal.confirmations if c.side == side.value), None)
    if conf is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Confirmation side missing")
    conf.decision = decision
    conf.actor_user_id = actor.id
    conf.decided_at = datetime.now(timezone.utc)
    conf.comment = comment

    if decision == ConfirmationDecision.REJECTED.value:
        deal.status = DealStatus.REJECTED.value
        if deal.inquiry_id:
            inquiry = await db.get(Inquiry, deal.inquiry_id)
            if inquiry:
                inquiry.status = InquiryStatus.REJECTED.value
    else:
        if all(c.decision == ConfirmationDecision.APPROVED.value for c in deal.confirmations):
            deal.status = DealStatus.CONFIRMED.value
            deal.confirmed_at = datetime.now(timezone.utc)
            if deal.inquiry_id:
                inquiry = await db.get(Inquiry, deal.inquiry_id)
                if inquiry:
                    inquiry.status = InquiryStatus.CONFIRMED.value
            # Block calendar for daily rentals
            prop = await db.get(Property, deal.property_id)
            if (
                prop
                and prop.rent_type == RentType.DAILY.value
                and deal.start_date
                and deal.end_date
            ):
                await add_interval(
                    db,
                    prop.id,
                    IntervalIn(start_date=deal.start_date, end_date=deal.end_date, kind="booked"),
                    created_by_user_id=actor.id,
                )

    await db.commit()
    await write_moderation(
        db,
        "rental_deal",
        deal.id,
        f"confirm_{side.value}_{decision}",
        actor.id,
        comment,
    )
    return await get_deal(db, deal.id)
