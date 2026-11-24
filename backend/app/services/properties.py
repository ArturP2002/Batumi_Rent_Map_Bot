from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from decimal import Decimal

from geoalchemy2.elements import WKTElement
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import PropertyStatus, RentType
from app.db.models import (
    AvailabilityInterval,
    Favorite,
    Property,
    PropertyFeature,
    PropertyPhoto,
    PropertyRealtor,
)
from app.schemas.property import FeaturesIn, PropertyCreateIn, PropertyFilters


def _public_code() -> str:
    return f"BRM-{secrets.token_hex(3).upper()}"


def _point(lat: float, lon: float) -> WKTElement:
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


async def create_property(
    db: AsyncSession,
    data: PropertyCreateIn,
    *,
    created_by_user_id: int | None,
    status: str = PropertyStatus.MODERATION.value,
) -> Property:
    prop = Property(
        public_code=_public_code(),
        rent_type=data.rent_type,
        status=status,
        rooms=data.rooms,
        area_m2=data.area_m2,
        floor=data.floor,
        floors_total=data.floors_total,
        sleeping_places=data.sleeping_places,
        price_usd=data.price_usd,
        district=data.district,
        address=data.address,
        description=data.description,
        lat=data.lat,
        lon=data.lon,
        location=_point(data.lat, data.lon) if data.lat is not None and data.lon is not None else None,
        created_by_user_id=created_by_user_id,
    )
    db.add(prop)
    await db.flush()

    features = data.features or FeaturesIn()
    db.add(PropertyFeature(property_id=prop.id, **features.model_dump()))

    realtor_ids = data.realtor_ids or []
    primary = data.primary_realtor_id
    if primary and primary not in realtor_ids:
        realtor_ids.append(primary)
    for rid in realtor_ids:
        db.add(
            PropertyRealtor(
                property_id=prop.id,
                realtor_id=rid,
                is_primary=(rid == primary) if primary else (rid == realtor_ids[0]),
            )
        )
    await db.commit()
    return await get_property(db, prop.id)


async def get_property(db: AsyncSession, property_id: int) -> Property | None:
    result = await db.execute(
        select(Property)
        .where(Property.id == property_id)
        .options(
            selectinload(Property.photos),
            selectinload(Property.features),
            selectinload(Property.realtor_links),
            selectinload(Property.intervals),
        )
    )
    return result.scalar_one_or_none()


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    parts = [float(x) for x in bbox.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be min_lon,min_lat,max_lon,max_lat")
    return parts[0], parts[1], parts[2], parts[3]


async def _available_for_dates(
    db: AsyncSession, property_ids: list[int], check_in: date, check_out: date
) -> set[int]:
    """Return property ids without overlapping booked/blocked intervals for [check_in, check_out)."""
    if not property_ids:
        return set()
    overlaps = await db.execute(
        select(AvailabilityInterval.property_id).where(
            AvailabilityInterval.property_id.in_(property_ids),
            AvailabilityInterval.start_date < check_out,
            AvailabilityInterval.end_date > check_in,
        )
    )
    busy = set(overlaps.scalars().all())
    return set(property_ids) - busy


async def search_properties(
    db: AsyncSession,
    filters: PropertyFilters,
    *,
    only_active: bool = True,
    user_id: int | None = None,
) -> tuple[list[Property], int]:
    stmt = select(Property).options(
        selectinload(Property.photos),
        selectinload(Property.features),
        selectinload(Property.realtor_links),
    )
    count_stmt = select(func.count(Property.id))
    conditions = []

    if only_active:
        conditions.append(Property.status == PropertyStatus.ACTIVE.value)
    elif filters.status:
        conditions.append(Property.status == filters.status)

    if filters.rent_type:
        conditions.append(Property.rent_type == filters.rent_type)
    if filters.rooms:
        conditions.append(Property.rooms.in_(filters.rooms))
    if filters.price_min is not None:
        conditions.append(Property.price_usd >= filters.price_min)
    if filters.price_max is not None:
        conditions.append(Property.price_usd <= filters.price_max)
    if filters.q:
        q = f"%{filters.q}%"
        conditions.append(or_(Property.address.ilike(q), Property.district.ilike(q), Property.public_code.ilike(q)))
    if filters.bbox:
        min_lon, min_lat, max_lon, max_lat = _parse_bbox(filters.bbox)
        conditions.append(Property.lon >= min_lon)
        conditions.append(Property.lon <= max_lon)
        conditions.append(Property.lat >= min_lat)
        conditions.append(Property.lat <= max_lat)

    if filters.amenities:
        stmt = stmt.join(PropertyFeature)
        count_stmt = count_stmt.join(PropertyFeature)
        for key in filters.amenities:
            if hasattr(PropertyFeature, key):
                conditions.append(getattr(PropertyFeature, key).is_(True))

    if conditions:
        stmt = stmt.where(and_(*conditions))
        count_stmt = count_stmt.where(and_(*conditions))

    if filters.sort == "price_asc":
        stmt = stmt.order_by(Property.price_usd.asc())
    elif filters.sort == "price_desc":
        stmt = stmt.order_by(Property.price_usd.desc())
    else:
        stmt = stmt.order_by(Property.updated_at.desc())

    total = (await db.execute(count_stmt)).scalar_one()
    offset = (filters.page - 1) * filters.page_size
    stmt = stmt.offset(offset).limit(filters.page_size)
    items = list((await db.execute(stmt)).scalars().unique().all())

    if filters.check_in and filters.check_out and filters.rent_type == RentType.DAILY.value:
        ok = await _available_for_dates(db, [p.id for p in items], filters.check_in, filters.check_out)
        items = [p for p in items if p.id in ok]
        # approximate total for filtered page; acceptable for v1
        total = len(items) if filters.page == 1 else total

    return items, total


async def list_markers(
    db: AsyncSession,
    filters: PropertyFilters,
) -> list[Property]:
    filters = filters.model_copy(update={"page": 1, "page_size": 2000})
    items, _ = await search_properties(db, filters, only_active=True)
    return [p for p in items if p.lat is not None and p.lon is not None]


async def toggle_favorite(db: AsyncSession, user_id: int, property_id: int) -> bool:
    existing = (
        await db.execute(
            select(Favorite).where(Favorite.user_id == user_id, Favorite.property_id == property_id)
        )
    ).scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
        return False
    db.add(Favorite(user_id=user_id, property_id=property_id))
    await db.commit()
    return True


async def list_favorites(db: AsyncSession, user_id: int) -> list[Property]:
    result = await db.execute(
        select(Property)
        .join(Favorite, Favorite.property_id == Property.id)
        .where(Favorite.user_id == user_id)
        .options(selectinload(Property.photos), selectinload(Property.features))
        .order_by(Favorite.created_at.desc())
    )
    return list(result.scalars().unique().all())


async def set_status(
    db: AsyncSession,
    prop: Property,
    status: str,
    *,
    comment: str | None = None,
) -> Property:
    prop.status = status
    if comment is not None:
        prop.moderation_comment = comment
    if status == PropertyStatus.ACTIVE.value:
        prop.published_at = datetime.now(timezone.utc)
        prop.last_confirmed_at = datetime.now(timezone.utc)
    await db.commit()
    return prop


def property_to_card(prop: Property, *, is_favorite: bool = False) -> dict:
    cover = prop.photos[0].thumb_url or prop.photos[0].url if prop.photos else None
    return {
        "id": prop.id,
        "public_code": prop.public_code,
        "rent_type": prop.rent_type,
        "status": prop.status,
        "rooms": prop.rooms,
        "area_m2": prop.area_m2,
        "price_usd": prop.price_usd,
        "district": prop.district,
        "address": prop.address,
        "last_confirmed_at": prop.last_confirmed_at,
        "cover_url": cover,
        "is_favorite": is_favorite,
    }


def property_to_detail(prop: Property, *, is_favorite: bool = False) -> dict:
    card = property_to_card(prop, is_favorite=is_favorite)
    primary = next((l.realtor_id for l in prop.realtor_links if l.is_primary), None)
    if primary is None and prop.realtor_links:
        primary = prop.realtor_links[0].realtor_id
    card.update(
        {
            "floor": prop.floor,
            "floors_total": prop.floors_total,
            "sleeping_places": prop.sleeping_places,
            "description": prop.description,
            "lat": prop.lat,
            "lon": prop.lon,
            "long_term_availability": prop.long_term_availability,
            "photos": [
                {
                    "id": p.id,
                    "url": p.url,
                    "thumb_url": p.thumb_url,
                    "sort_order": p.sort_order,
                }
                for p in prop.photos
            ],
            "features": prop.features,
            "realtor_ids": [l.realtor_id for l in prop.realtor_links],
            "primary_realtor_id": primary,
        }
    )
    return card
