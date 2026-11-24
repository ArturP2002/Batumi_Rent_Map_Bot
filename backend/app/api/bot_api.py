from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.deps import require_roles
from app.db.enums import PropertyStatus, UserRole
from app.db.models import Inquiry, Property, PropertyPhoto, PropertyRealtor, RentalDeal, User
from app.db.session import get_db
from app.schemas.common import MessageOut, Paginated
from app.schemas.deals import DealCreateIn, DealDecisionIn, DealOut, InquiryOut
from app.schemas.property import (
    IntervalIn,
    IntervalOut,
    PropertyCardOut,
    PropertyCreateIn,
    PropertyDetailOut,
)
from app.services import calendar as calendar_svc
from app.services import deals as deals_svc
from app.services import properties as properties_svc
from app.storage.s3 import upload_property_photo
from app.db.enums import ConfirmationSide

router = APIRouter(prefix="/api/bot", tags=["bot"])


@router.post("/properties", response_model=PropertyDetailOut)
async def bot_create_property(
    data: PropertyCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REALTOR, UserRole.ADMIN)),
):
    if not user.realtor_profile and not user.has_role(UserRole.ADMIN):
        raise HTTPException(403, "Realtor profile required")
    realtor_ids = data.realtor_ids or (
        [user.realtor_profile.id] if user.realtor_profile else []
    )
    payload = data.model_copy(
        update={
            "realtor_ids": realtor_ids,
            "primary_realtor_id": data.primary_realtor_id
            or (user.realtor_profile.id if user.realtor_profile else None),
        }
    )
    prop = await properties_svc.create_property(
        db,
        payload,
        created_by_user_id=user.id,
        status=PropertyStatus.MODERATION.value,
    )
    return PropertyDetailOut(**properties_svc.property_to_detail(prop))


@router.get("/properties/mine", response_model=list[PropertyCardOut])
async def my_properties(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REALTOR, UserRole.ADMIN)),
):
    if not user.realtor_profile:
        return []
    rows = (
        await db.execute(
            select(Property)
            .join(PropertyRealtor)
            .where(PropertyRealtor.realtor_id == user.realtor_profile.id)
            .options(selectinload(Property.photos))
            .order_by(Property.updated_at.desc())
        )
    ).scalars().unique().all()
    return [PropertyCardOut(**properties_svc.property_to_card(p)) for p in rows]


@router.patch("/properties/{property_id}", response_model=PropertyDetailOut)
async def bot_update_property(
    property_id: int,
    data: PropertyCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REALTOR, UserRole.ADMIN)),
):
    prop = await properties_svc.get_property(db, property_id)
    if not prop:
        raise HTTPException(404, "Not found")
    if user.realtor_profile and not user.has_role(UserRole.ADMIN):
        if user.realtor_profile.id not in [l.realtor_id for l in prop.realtor_links]:
            raise HTTPException(403, "Not your property")
    critical = False
    for field in ("address", "lat", "lon", "rooms", "rent_type"):
        if getattr(data, field) is not None and getattr(data, field) != getattr(prop, field):
            critical = True
        if getattr(data, field) is not None:
            setattr(prop, field, getattr(data, field))
    for field in (
        "area_m2",
        "floor",
        "floors_total",
        "sleeping_places",
        "price_usd",
        "district",
        "description",
    ):
        if getattr(data, field) is not None:
            setattr(prop, field, getattr(data, field))
    if data.lat is not None and data.lon is not None:
        from app.services.properties import _point

        prop.location = _point(data.lat, data.lon)
    if data.features and prop.features:
        for k, v in data.features.model_dump().items():
            if getattr(prop.features, k) != v:
                critical = True
            setattr(prop.features, k, v)
    if critical and prop.status == PropertyStatus.ACTIVE.value:
        prop.status = PropertyStatus.MODERATION.value
    await db.commit()
    prop = await properties_svc.get_property(db, property_id)
    return PropertyDetailOut(**properties_svc.property_to_detail(prop))


@router.post("/properties/{property_id}/photos")
async def upload_photo(
    property_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REALTOR, UserRole.ADMIN)),
):
    prop = await properties_svc.get_property(db, property_id)
    if not prop:
        raise HTTPException(404, "Not found")
    if len(prop.photos) >= get_settings().max_photos_per_property:
        raise HTTPException(400, "Photo limit reached")
    uploaded = await upload_property_photo(file, property_id)
    photo = PropertyPhoto(
        property_id=property_id,
        object_key=uploaded.object_key,
        url=uploaded.url,
        thumb_url=uploaded.thumb_url,
        sort_order=len(prop.photos),
        width=uploaded.width,
        height=uploaded.height,
        size_bytes=uploaded.size_bytes,
    )
    db.add(photo)
    if prop.status == PropertyStatus.ACTIVE.value:
        prop.status = PropertyStatus.MODERATION.value
    await db.commit()
    return {"id": photo.id, "url": photo.url, "thumb_url": photo.thumb_url}


@router.post("/properties/{property_id}/status", response_model=MessageOut)
async def set_my_status(
    property_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REALTOR, UserRole.ADMIN)),
):
    if status not in {
        PropertyStatus.ACTIVE.value,
        PropertyStatus.HIDDEN.value,
        PropertyStatus.ARCHIVED.value,
        PropertyStatus.DRAFT.value,
    }:
        raise HTTPException(400, "Invalid status")
    prop = await properties_svc.get_property(db, property_id)
    if not prop:
        raise HTTPException(404, "Not found")
    # Manual activate only if already approved once
    if status == PropertyStatus.ACTIVE.value and prop.status in {
        PropertyStatus.MODERATION.value,
        PropertyStatus.NEEDS_FIX.value,
        PropertyStatus.BLOCKED.value,
    }:
        raise HTTPException(400, "Await moderation")
    await properties_svc.set_status(db, prop, status)
    return MessageOut(message=status)


@router.post("/properties/{property_id}/confirm-freshness", response_model=MessageOut)
async def confirm_freshness(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REALTOR, UserRole.ADMIN)),
):
    from datetime import datetime, timezone

    prop = await properties_svc.get_property(db, property_id)
    if not prop:
        raise HTTPException(404, "Not found")
    prop.last_confirmed_at = datetime.now(timezone.utc)
    prop.freshness_reminded_at = None
    if prop.status == PropertyStatus.HIDDEN.value:
        prop.status = PropertyStatus.ACTIVE.value
    await db.commit()
    return MessageOut(message="confirmed")


@router.get("/properties/{property_id}/calendar", response_model=list[IntervalOut])
async def bot_calendar(property_id: int, db: AsyncSession = Depends(get_db)):
    return await calendar_svc.list_intervals(db, property_id)


@router.post("/properties/{property_id}/calendar", response_model=IntervalOut)
async def bot_add_interval(
    property_id: int,
    data: IntervalIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REALTOR, UserRole.ADMIN)),
):
    return await calendar_svc.add_interval(db, property_id, data, created_by_user_id=user.id)


@router.get("/inquiries", response_model=list[InquiryOut])
async def bot_inquiries(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REALTOR, UserRole.ADMIN)),
):
    if not user.realtor_profile:
        return []
    rows = (
        await db.execute(
            select(Inquiry)
            .where(Inquiry.realtor_id == user.realtor_profile.id)
            .order_by(Inquiry.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return rows


@router.post("/deals", response_model=DealOut)
async def bot_create_deal(
    data: DealCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REALTOR, UserRole.ADMIN)),
):
    return await deals_svc.create_deal(db, data, actor=user)


@router.post("/deals/{deal_id}/client-decide", response_model=DealOut)
async def client_decide(
    deal_id: int,
    data: DealDecisionIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.TENANT, UserRole.REALTOR, UserRole.ADMIN)),
):
    deal = await deals_svc.get_deal(db, deal_id)
    if deal.client_user_id != user.id and not user.has_role(UserRole.ADMIN):
        raise HTTPException(403, "Not your deal")
    return await deals_svc.decide_confirmation(
        db,
        deal,
        side=ConfirmationSide.CLIENT,
        actor=user,
        decision=data.decision,
        comment=data.comment,
    )


@router.get("/deals/mine", response_model=list[DealOut])
async def my_deals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REALTOR, UserRole.ADMIN)),
):
    if not user.realtor_profile:
        return []
    rows = (
        await db.execute(
            select(RentalDeal)
            .where(RentalDeal.realtor_id == user.realtor_profile.id)
            .options(selectinload(RentalDeal.confirmations))
            .order_by(RentalDeal.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return rows
