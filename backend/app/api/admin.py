from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import require_roles
from app.db.enums import DealStatus, InquiryStatus, PropertyStatus, ReviewStatus, UserRole
from app.db.models import (
    Inquiry,
    Property,
    PropertyRealtor,
    RealtorProfile,
    RentalDeal,
    Review,
    User,
)
from app.db.session import get_db
from app.schemas.admin import (
    DashboardOut,
    ModerationActionIn,
    RealtorCreateIn,
    RealtorOut,
    SettingsOut,
    SettingsUpdateIn,
    StatsOut,
)
from app.schemas.common import MessageOut, Paginated
from app.schemas.deals import DealDecisionIn, DealOut
from app.schemas.property import IntervalIn, IntervalOut, PropertyCardOut, PropertyCreateIn, PropertyDetailOut
from app.services import analytics as analytics_svc
from app.services import calendar as calendar_svc
from app.services import deals as deals_svc
from app.services import properties as properties_svc
from app.services import reviews as reviews_svc
from app.services import settings as settings_svc
from app.services.audit import write_audit
from app.services.users import create_realtor, set_realtor_blocked
from app.schemas.property import PropertyFilters

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(db: AsyncSession = Depends(get_db)):
    async def count(model, *conds):
        stmt = select(func.count()).select_from(model)
        if conds:
            stmt = stmt.where(*conds)
        return (await db.execute(stmt)).scalar_one()

    attention = []
    mod_props = (
        await db.execute(
            select(Property).where(Property.status == PropertyStatus.MODERATION.value).limit(10)
        )
    ).scalars().all()
    for p in mod_props:
        attention.append({"type": "property_moderation", "id": p.id, "title": p.public_code})

    pending_deals = (
        await db.execute(
            select(RentalDeal).where(RentalDeal.status == DealStatus.PENDING.value).limit(10)
        )
    ).scalars().all()
    for d in pending_deals:
        attention.append({"type": "deal_pending", "id": d.id, "title": f"Deal #{d.id}"})

    pending_reviews = (
        await db.execute(
            select(Review).where(Review.status == ReviewStatus.PENDING_MODERATION.value).limit(10)
        )
    ).scalars().all()
    for r in pending_reviews:
        attention.append({"type": "review_moderation", "id": r.id, "title": f"Review #{r.id}"})

    return DashboardOut(
        active_properties=await count(Property, Property.status == PropertyStatus.ACTIVE.value),
        moderation_properties=await count(
            Property, Property.status == PropertyStatus.MODERATION.value
        ),
        active_realtors=await count(
            RealtorProfile, RealtorProfile.is_blocked.is_(False), RealtorProfile.can_publish.is_(True)
        ),
        inquiries_open=await count(
            Inquiry,
            Inquiry.status.in_(
                [InquiryStatus.NEW.value, InquiryStatus.IN_PROGRESS.value, InquiryStatus.AWAITING_CONFIRMATIONS.value]
            ),
        ),
        deals_pending=await count(RentalDeal, RentalDeal.status == DealStatus.PENDING.value),
        reviews_pending=await count(
            Review, Review.status == ReviewStatus.PENDING_MODERATION.value
        ),
        attention=attention,
    )


@router.get("/properties", response_model=Paginated[PropertyCardOut])
async def admin_properties(
    status: str | None = None,
    q: str | None = None,
    rent_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    filters = PropertyFilters(
        status=status, q=q, rent_type=rent_type, page=page, page_size=page_size
    )
    items, total = await properties_svc.search_properties(db, filters, only_active=False)
    return Paginated(
        items=[PropertyCardOut(**properties_svc.property_to_card(p)) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/properties/{property_id}", response_model=PropertyDetailOut)
async def admin_property(property_id: int, db: AsyncSession = Depends(get_db)):
    prop = await properties_svc.get_property(db, property_id)
    if not prop:
        raise HTTPException(404, "Not found")
    return PropertyDetailOut(**properties_svc.property_to_detail(prop))


@router.post("/properties/{property_id}/moderate", response_model=PropertyDetailOut)
async def moderate_property(
    property_id: int,
    data: ModerationActionIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    prop = await properties_svc.get_property(db, property_id)
    if not prop:
        raise HTTPException(404, "Not found")
    mapping = {
        "approve": PropertyStatus.ACTIVE.value,
        "reject": PropertyStatus.BLOCKED.value,
        "needs_fix": PropertyStatus.NEEDS_FIX.value,
        "hide": PropertyStatus.HIDDEN.value,
        "restore": PropertyStatus.ACTIVE.value,
        "block": PropertyStatus.BLOCKED.value,
        "archive": PropertyStatus.ARCHIVED.value,
    }
    if data.action not in mapping:
        raise HTTPException(400, "Unknown action")
    await properties_svc.set_status(db, prop, mapping[data.action], comment=data.comment)
    await write_audit(db, admin.id, f"property.{data.action}", "property", prop.id, {"comment": data.comment})
    prop = await properties_svc.get_property(db, property_id)
    return PropertyDetailOut(**properties_svc.property_to_detail(prop))


@router.patch("/properties/{property_id}", response_model=PropertyDetailOut)
async def edit_property(
    property_id: int,
    data: PropertyCreateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    prop = await properties_svc.get_property(db, property_id)
    if not prop:
        raise HTTPException(404, "Not found")
    for field in (
        "rent_type",
        "rooms",
        "area_m2",
        "floor",
        "floors_total",
        "sleeping_places",
        "price_usd",
        "district",
        "address",
        "description",
        "lat",
        "lon",
    ):
        val = getattr(data, field)
        if val is not None:
            setattr(prop, field, val)
    if data.lat is not None and data.lon is not None:
        from app.services.properties import _point

        prop.location = _point(data.lat, data.lon)
    if data.features and prop.features:
        for k, v in data.features.model_dump().items():
            setattr(prop.features, k, v)
    await db.commit()
    await write_audit(db, admin.id, "property.edit", "property", prop.id)
    prop = await properties_svc.get_property(db, property_id)
    return PropertyDetailOut(**properties_svc.property_to_detail(prop))


@router.get("/properties/{property_id}/calendar", response_model=list[IntervalOut])
async def admin_calendar(property_id: int, db: AsyncSession = Depends(get_db)):
    return await calendar_svc.list_intervals(db, property_id)


@router.post("/properties/{property_id}/calendar", response_model=IntervalOut)
async def admin_add_interval(
    property_id: int,
    data: IntervalIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    return await calendar_svc.add_interval(db, property_id, data, created_by_user_id=admin.id)


@router.delete("/calendar/{interval_id}", response_model=MessageOut)
async def admin_delete_interval(interval_id: int, db: AsyncSession = Depends(get_db)):
    await calendar_svc.delete_interval(db, interval_id)
    return MessageOut(message="deleted")


@router.get("/realtors", response_model=list[RealtorOut])
async def list_realtors(q: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(RealtorProfile).options(selectinload(RealtorProfile.user))
    if q:
        stmt = stmt.where(RealtorProfile.display_name.ilike(f"%{q}%"))
    rows = (await db.execute(stmt)).scalars().all()
    out = []
    for r in rows:
        active = (
            await db.execute(
                select(func.count(PropertyRealtor.id))
                .join(Property, Property.id == PropertyRealtor.property_id)
                .where(
                    PropertyRealtor.realtor_id == r.id,
                    Property.status == PropertyStatus.ACTIVE.value,
                )
            )
        ).scalar_one()
        out.append(
            RealtorOut(
                id=r.id,
                user_id=r.user_id,
                display_name=r.display_name,
                email=r.email,
                bio=r.bio,
                phone=r.phone,
                whatsapp=r.whatsapp,
                telegram_contact=r.telegram_contact,
                photo_url=r.photo_url,
                can_publish=r.can_publish,
                is_blocked=r.is_blocked,
                rating_avg=r.rating_avg,
                rating_count=r.rating_count,
                telegram_id=r.user.telegram_id if r.user else None,
                active_listings=active,
                has_credentials=r.has_credentials,
            )
        )
    return out


@router.post("/realtors", response_model=RealtorOut)
async def add_realtor(
    data: RealtorCreateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    profile = await create_realtor(db, **data.model_dump())
    await write_audit(db, admin.id, "realtor.create", "realtor_profile", profile.id)
    user = await db.get(User, profile.user_id)
    return RealtorOut(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        email=profile.email,
        bio=profile.bio,
        phone=profile.phone,
        whatsapp=profile.whatsapp,
        telegram_contact=profile.telegram_contact,
        photo_url=profile.photo_url,
        can_publish=profile.can_publish,
        is_blocked=profile.is_blocked,
        rating_avg=profile.rating_avg,
        rating_count=profile.rating_count,
        telegram_id=user.telegram_id if user else None,
        active_listings=0,
        has_credentials=profile.has_credentials,
    )


@router.post("/realtors/{realtor_id}/block", response_model=MessageOut)
async def block_realtor(
    realtor_id: int,
    blocked: bool = True,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    realtor = await db.get(RealtorProfile, realtor_id)
    if not realtor:
        raise HTTPException(404, "Not found")
    await set_realtor_blocked(db, realtor, blocked)
    await write_audit(db, admin.id, "realtor.block" if blocked else "realtor.unblock", "realtor_profile", realtor_id)
    return MessageOut(message="blocked" if blocked else "unblocked")


@router.get("/inquiries")
async def list_inquiries(
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Inquiry)
    if status:
        stmt = stmt.where(Inquiry.status == status)
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Inquiry.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/deals", response_model=list[DealOut])
async def list_deals(status: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(RentalDeal).options(selectinload(RentalDeal.confirmations))
    if status:
        stmt = stmt.where(RentalDeal.status == status)
    rows = (await db.execute(stmt.order_by(RentalDeal.created_at.desc()).limit(100))).scalars().all()
    return rows


@router.post("/deals/{deal_id}/decide", response_model=DealOut)
async def decide_deal(
    deal_id: int,
    data: DealDecisionIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    from app.db.enums import ConfirmationSide

    deal = await deals_svc.get_deal(db, deal_id)
    return await deals_svc.decide_confirmation(
        db,
        deal,
        side=ConfirmationSide.ADMIN,
        actor=admin,
        decision=data.decision,
        comment=data.comment,
    )


@router.get("/reviews")
async def list_reviews(status: str | None = "pending_moderation", db: AsyncSession = Depends(get_db)):
    stmt = select(Review)
    if status:
        stmt = stmt.where(Review.status == status)
    return (await db.execute(stmt.order_by(Review.created_at.desc()).limit(100))).scalars().all()


@router.post("/reviews/{review_id}/moderate", response_model=MessageOut)
async def moderate_review(
    review_id: int,
    data: ModerationActionIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(404, "Not found")
    await reviews_svc.moderate_review(
        db, review, action=data.action, actor_id=admin.id, comment=data.comment
    )
    return MessageOut(message=data.action)


@router.get("/stats", response_model=StatsOut)
async def stats(
    from_date: date | None = None,
    to_date: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await analytics_svc.build_stats(db, from_date, to_date)


@router.get("/stats/export")
async def stats_export(
    from_date: date | None = None,
    to_date: date | None = None,
    format: str = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
):
    data = await analytics_svc.build_stats(db, from_date, to_date)
    if format == "xlsx":
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "stats"
        ws.append(["metric", "value"])
        for k, v in data.model_dump().items():
            if isinstance(v, (int, float, str)):
                ws.append([k, v])
        buf = io.BytesIO()
        wb.save(buf)
        return Response(
            buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=stats.xlsx"},
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["metric", "value"])
    for k, v in data.model_dump().items():
        if isinstance(v, (int, float, str)):
            writer.writerow([k, v])
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stats.csv"},
    )


@router.get("/settings", response_model=SettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)):
    return await settings_svc.get_app_settings(db)


@router.put("/settings", response_model=SettingsOut)
async def put_settings(
    data: SettingsUpdateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    result = await settings_svc.update_app_settings(db, data)
    await write_audit(db, admin.id, "settings.update", "system_settings", None, data.model_dump())
    return result
