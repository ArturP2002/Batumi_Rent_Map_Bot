from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AvailabilityInterval
from app.schemas.property import IntervalIn


async def list_intervals(
    db: AsyncSession, property_id: int, *, month: int | None = None, year: int | None = None
) -> list[AvailabilityInterval]:
    stmt = select(AvailabilityInterval).where(AvailabilityInterval.property_id == property_id)
    if month and year:
        # intervals overlapping the month
        if month == 12:
            start = date(year, 12, 1)
            end = date(year + 1, 1, 1)
        else:
            start = date(year, month, 1)
            end = date(year, month + 1, 1)
        stmt = stmt.where(
            AvailabilityInterval.start_date < end,
            AvailabilityInterval.end_date > start,
        )
    stmt = stmt.order_by(AvailabilityInterval.start_date.asc())
    return list((await db.execute(stmt)).scalars().all())


async def add_interval(
    db: AsyncSession,
    property_id: int,
    data: IntervalIn,
    *,
    created_by_user_id: int | None,
) -> AvailabilityInterval:
    if data.end_date <= data.start_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "end_date must be after start_date")

    overlap = (
        await db.execute(
            select(AvailabilityInterval).where(
                AvailabilityInterval.property_id == property_id,
                AvailabilityInterval.start_date < data.end_date,
                AvailabilityInterval.end_date > data.start_date,
            )
        )
    ).scalar_one_or_none()
    if overlap:
        raise HTTPException(status.HTTP_409_CONFLICT, "Interval overlaps existing availability block")

    # Idempotent: same exact interval returns existing
    same = (
        await db.execute(
            select(AvailabilityInterval).where(
                AvailabilityInterval.property_id == property_id,
                AvailabilityInterval.start_date == data.start_date,
                AvailabilityInterval.end_date == data.end_date,
                AvailabilityInterval.kind == data.kind,
            )
        )
    ).scalar_one_or_none()
    if same:
        return same

    interval = AvailabilityInterval(
        property_id=property_id,
        start_date=data.start_date,
        end_date=data.end_date,
        kind=data.kind,
        note=data.note,
        created_by_user_id=created_by_user_id,
    )
    db.add(interval)
    await db.commit()
    await db.refresh(interval)
    return interval


async def delete_interval(db: AsyncSession, interval_id: int) -> None:
    interval = await db.get(AvailabilityInterval, interval_id)
    if not interval:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interval not found")
    await db.delete(interval)
    await db.commit()


def dates_conflict(existing: list[AvailabilityInterval], start: date, end: date) -> bool:
    return any(i.start_date < end and i.end_date > start for i in existing)
