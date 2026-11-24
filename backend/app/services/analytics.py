from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnalyticsEvent, DailyAggregate, Inquiry, RentalDeal, Review, User
from app.db.enums import DealStatus, ReviewStatus
from app.schemas.admin import AnalyticsEventIn, StatsOut


async def track_event(
    db: AsyncSession,
    data: AnalyticsEventIn,
    *,
    user_id: int | None,
) -> AnalyticsEvent:
    event = AnalyticsEvent(
        event_type=data.event_type,
        occurred_at=datetime.now(timezone.utc),
        user_id=user_id,
        property_id=data.property_id,
        realtor_id=data.realtor_id,
        session_id=data.session_id,
        referrer=data.referrer,
        context_json=json.dumps(data.context) if data.context else None,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def build_stats(
    db: AsyncSession,
    from_date: date | None,
    to_date: date | None,
) -> StatsOut:
    today = datetime.now(timezone.utc).date()
    start = from_date or (today - timedelta(days=30))
    end = to_date or today
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    users = (await db.execute(select(func.count(User.id)))).scalar_one()
    new_users = (
        await db.execute(
            select(func.count(User.id)).where(
                User.created_at >= start_dt, User.created_at < end_dt
            )
        )
    ).scalar_one()

    async def count_events(event_type: str) -> int:
        return (
            await db.execute(
                select(func.count(AnalyticsEvent.id)).where(
                    AnalyticsEvent.event_type == event_type,
                    AnalyticsEvent.occurred_at >= start_dt,
                    AnalyticsEvent.occurred_at < end_dt,
                )
            )
        ).scalar_one()

    property_views = await count_events("property_view")
    contact_clicks = sum(
        [
            await count_events("contact_click_telegram"),
            await count_events("contact_click_whatsapp"),
            await count_events("contact_click_phone"),
        ]
    )
    inquiries = (
        await db.execute(
            select(func.count(Inquiry.id)).where(
                Inquiry.created_at >= start_dt, Inquiry.created_at < end_dt
            )
        )
    ).scalar_one()
    deals_confirmed = (
        await db.execute(
            select(func.count(RentalDeal.id)).where(
                RentalDeal.status == DealStatus.CONFIRMED.value,
                RentalDeal.confirmed_at >= start_dt,
                RentalDeal.confirmed_at < end_dt,
            )
        )
    ).scalar_one()
    reviews_published = (
        await db.execute(
            select(func.count(Review.id)).where(
                Review.status == ReviewStatus.PUBLISHED.value,
                Review.created_at >= start_dt,
                Review.created_at < end_dt,
            )
        )
    ).scalar_one()

    def safe_div(a: int, b: int) -> float:
        return round(a / b, 4) if b else 0.0

    conversions = {
        "view_to_contact": safe_div(contact_clicks, property_views),
        "view_to_inquiry": safe_div(inquiries, property_views),
        "inquiry_to_deal": safe_div(deals_confirmed, inquiries),
        "deal_to_review": safe_div(reviews_published, deals_confirmed),
    }

    top_props = (
        await db.execute(
            select(AnalyticsEvent.property_id, func.count(AnalyticsEvent.id).label("c"))
            .where(
                AnalyticsEvent.event_type == "property_view",
                AnalyticsEvent.property_id.is_not(None),
                AnalyticsEvent.occurred_at >= start_dt,
                AnalyticsEvent.occurred_at < end_dt,
            )
            .group_by(AnalyticsEvent.property_id)
            .order_by(func.count(AnalyticsEvent.id).desc())
            .limit(10)
        )
    ).all()

    top_realtors = (
        await db.execute(
            select(Inquiry.realtor_id, func.count(Inquiry.id).label("c"))
            .where(Inquiry.created_at >= start_dt, Inquiry.created_at < end_dt)
            .group_by(Inquiry.realtor_id)
            .order_by(func.count(Inquiry.id).desc())
            .limit(10)
        )
    ).all()

    series = []
    day = start
    while day <= end:
        day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        views = (
            await db.execute(
                select(func.count(AnalyticsEvent.id)).where(
                    AnalyticsEvent.event_type == "property_view",
                    AnalyticsEvent.occurred_at >= day_start,
                    AnalyticsEvent.occurred_at < day_end,
                )
            )
        ).scalar_one()
        series.append({"day": day.isoformat(), "property_views": views})
        day += timedelta(days=1)

    return StatsOut(
        users=users,
        new_users=new_users,
        property_views=property_views,
        contact_clicks=contact_clicks,
        inquiries=inquiries,
        deals_confirmed=deals_confirmed,
        reviews_published=reviews_published,
        conversions=conversions,
        top_properties=[{"property_id": r[0], "views": r[1]} for r in top_props],
        top_realtors=[{"realtor_id": r[0], "inquiries": r[1]} for r in top_realtors],
        series=series,
    )


async def aggregate_daily(db: AsyncSession, day: date | None = None) -> None:
    target = day or (datetime.now(timezone.utc).date() - timedelta(days=1))
    start_dt = datetime.combine(target, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)
    rows = (
        await db.execute(
            select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
            .where(AnalyticsEvent.occurred_at >= start_dt, AnalyticsEvent.occurred_at < end_dt)
            .group_by(AnalyticsEvent.event_type)
        )
    ).all()
    for metric, value in rows:
        existing = (
            await db.execute(
                select(DailyAggregate).where(
                    DailyAggregate.day == target,
                    DailyAggregate.metric == metric,
                    DailyAggregate.entity_type == "global",
                    DailyAggregate.entity_id.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.value = value
        else:
            db.add(
                DailyAggregate(
                    day=target,
                    metric=metric,
                    entity_type="global",
                    entity_id=None,
                    value=value,
                )
            )
    await db.commit()
