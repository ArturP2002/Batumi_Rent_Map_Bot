from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_optional_user
from app.core.security import make_session_token, validate_init_data
from app.db.enums import ConfirmationSide, DealStatus, ReviewStatus, UserRole
from app.db.models import Favorite, Property, RealtorProfile, Review, User
from app.db.session import get_db
from app.schemas.admin import AnalyticsEventIn
from app.schemas.common import AuthSessionOut, MessageOut, Paginated
from app.schemas.deals import (
    DealDecisionIn,
    DealOut,
    InquiryCreateIn,
    InquiryOut,
    ReviewCreateIn,
    ReviewOut,
)
from app.schemas.property import (
    IntervalOut,
    PropertyCardOut,
    PropertyDetailOut,
    PropertyFilters,
    PropertyMarkerOut,
)
from app.services import analytics as analytics_svc
from app.services import calendar as calendar_svc
from app.services import deals as deals_svc
from app.services import properties as properties_svc
from app.services import reviews as reviews_svc
from app.services.users import ensure_user_from_telegram

router = APIRouter(prefix="/api/public", tags=["public"])


@router.post("/auth/session", response_model=AuthSessionOut)
async def create_session(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    init_data = payload.get("initData") or payload.get("init_data") or ""
    parsed = validate_init_data(init_data)
    user = await ensure_user_from_telegram(db, parsed["_user"])
    token = make_session_token(user.telegram_id)
    return AuthSessionOut(
        token=token,
        telegram_id=user.telegram_id,
        roles=[r.role for r in user.roles if r.is_active],
    )


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "roles": [r.role for r in user.roles if r.is_active],
        "realtor_id": user.realtor_profile.id if user.realtor_profile else None,
    }


@router.get("/map/markers", response_model=list[PropertyMarkerOut])
async def map_markers(
    rent_type: str | None = None,
    rooms: list[str] | None = Query(default=None),
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    amenities: list[str] | None = Query(default=None),
    check_in: date | None = None,
    check_out: date | None = None,
    bbox: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    filters = PropertyFilters(
        rent_type=rent_type,
        rooms=rooms,
        price_min=price_min,
        price_max=price_max,
        amenities=amenities,
        check_in=check_in,
        check_out=check_out,
        bbox=bbox,
    )
    items = await properties_svc.list_markers(db, filters)
    return [
        PropertyMarkerOut(
            id=p.id,
            public_code=p.public_code,
            price_usd=p.price_usd,
            rent_type=p.rent_type,
            rooms=p.rooms,
            lat=p.lat or 0,
            lon=p.lon or 0,
            district=p.district,
            area_m2=p.area_m2,
            cover_url=(p.photos[0].thumb_url or p.photos[0].url) if p.photos else None,
        )
        for p in items
    ]


@router.get("/properties", response_model=Paginated[PropertyCardOut])
async def list_properties(
    rent_type: str | None = None,
    rooms: list[str] | None = Query(default=None),
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    amenities: list[str] | None = Query(default=None),
    check_in: date | None = None,
    check_out: date | None = None,
    q: str | None = None,
    sort: str = "newest",
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    filters = PropertyFilters(
        rent_type=rent_type,
        rooms=rooms,
        price_min=price_min,
        price_max=price_max,
        amenities=amenities,
        check_in=check_in,
        check_out=check_out,
        q=q,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    items, total = await properties_svc.search_properties(db, filters, only_active=True)
    fav_ids: set[int] = set()
    if user:
        fav_ids = set(
            (
                await db.execute(select(Favorite.property_id).where(Favorite.user_id == user.id))
            ).scalars().all()
        )
    return Paginated(
        items=[
            PropertyCardOut(**properties_svc.property_to_card(p, is_favorite=p.id in fav_ids))
            for p in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/properties/{property_id}", response_model=PropertyDetailOut)
async def property_detail(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    prop = await properties_svc.get_property(db, property_id)
    if not prop:
        from fastapi import HTTPException

        raise HTTPException(404, "Not found")
    is_fav = False
    if user:
        is_fav = (
            await db.execute(
                select(Favorite).where(
                    Favorite.user_id == user.id, Favorite.property_id == property_id
                )
            )
        ).scalar_one_or_none() is not None
        await analytics_svc.track_event(
            db,
            AnalyticsEventIn(event_type="property_view", property_id=property_id),
            user_id=user.id,
        )
    return PropertyDetailOut(**properties_svc.property_to_detail(prop, is_favorite=is_fav))


@router.get("/properties/{property_id}/calendar", response_model=list[IntervalOut])
async def property_calendar(
    property_id: int,
    month: int | None = None,
    year: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await calendar_svc.list_intervals(db, property_id, month=month, year=year)


@router.post("/favorites/{property_id}", response_model=MessageOut)
async def favorite_toggle(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    added = await properties_svc.toggle_favorite(db, user.id, property_id)
    await analytics_svc.track_event(
        db,
        AnalyticsEventIn(event_type="favorite_add" if added else "favorite_remove", property_id=property_id),
        user_id=user.id,
    )
    return MessageOut(message="added" if added else "removed")


@router.get("/favorites", response_model=list[PropertyCardOut])
async def favorites(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    items = await properties_svc.list_favorites(db, user.id)
    return [PropertyCardOut(**properties_svc.property_to_card(p, is_favorite=True)) for p in items]


@router.post("/inquiries", response_model=InquiryOut)
async def create_inquiry(
    data: InquiryCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inquiry = await deals_svc.upsert_inquiry(db, user, data)
    event = f"contact_click_{data.channel}"
    await analytics_svc.track_event(
        db,
        AnalyticsEventIn(
            event_type=event,
            property_id=data.property_id,
            realtor_id=data.realtor_id,
        ),
        user_id=user.id,
    )
    await analytics_svc.track_event(
        db,
        AnalyticsEventIn(
            event_type="inquiry_created",
            property_id=data.property_id,
            realtor_id=data.realtor_id,
        ),
        user_id=user.id,
    )
    return inquiry


@router.get("/realtors/{realtor_id}")
async def realtor_profile(realtor_id: int, db: AsyncSession = Depends(get_db)):
    realtor = await db.get(RealtorProfile, realtor_id)
    if not realtor or realtor.is_blocked:
        from fastapi import HTTPException

        raise HTTPException(404, "Realtor not found")
    from app.db.models import PropertyRealtor

    linked = (
        await db.execute(
            select(Property)
            .join(PropertyRealtor)
            .where(
                PropertyRealtor.realtor_id == realtor_id,
                Property.status == "active",
            )
            .options(selectinload(Property.photos))
        )
    ).scalars().unique().all()
    reviews = await reviews_svc.list_published_reviews(db, realtor_id)
    return {
        "id": realtor.id,
        "display_name": realtor.display_name,
        "bio": realtor.bio,
        "photo_url": realtor.photo_url,
        "phone": realtor.phone,
        "whatsapp": realtor.whatsapp,
        "telegram_contact": realtor.telegram_contact,
        "rating_avg": realtor.rating_avg,
        "rating_count": realtor.rating_count,
        "active_listings": len(linked),
        "properties": [
            PropertyCardOut(**properties_svc.property_to_card(p)) for p in linked
        ],
        "reviews": [ReviewOut.model_validate(r) for r in reviews],
    }


@router.get("/deals/{deal_id}", response_model=DealOut)
async def get_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deal = await deals_svc.get_deal(db, deal_id)
    if deal.client_user_id != user.id and not user.has_role(UserRole.ADMIN):
        raise HTTPException(403, "Недостаточно прав")
    return deal


@router.post("/deals/{deal_id}/decide", response_model=DealOut)
async def client_decide_deal(
    deal_id: int,
    data: DealDecisionIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deal = await deals_svc.get_deal(db, deal_id)
    if deal.client_user_id != user.id and not user.has_role(UserRole.ADMIN):
        raise HTTPException(403, "Недостаточно прав")
    if deal.status != DealStatus.PENDING.value:
        raise HTTPException(400, "Сделка уже обработана")
    return await deals_svc.decide_confirmation(
        db,
        deal,
        side=ConfirmationSide.CLIENT,
        actor=user,
        decision=data.decision,
        comment=data.comment,
    )


@router.post("/reviews", response_model=ReviewOut)
async def create_review(
    data: ReviewCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await reviews_svc.create_review(db, user, data)


@router.post("/analytics/events", response_model=MessageOut)
async def post_event(
    data: AnalyticsEventIn,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    await analytics_svc.track_event(db, data, user_id=user.id if user else None)
    return MessageOut()
