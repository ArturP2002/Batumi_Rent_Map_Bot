from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from geoalchemy2 import Geography
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.enums import AvailabilityKind, LongTermAvailability, PropertyStatus, RentType


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    rent_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=PropertyStatus.DRAFT.value, index=True, nullable=False
    )
    rooms: Mapped[str] = mapped_column(String(16), nullable=False)
    area_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    floor: Mapped[int | None] = mapped_column(Integer)
    floors_total: Mapped[int | None] = mapped_column(Integer)
    sleeping_places: Mapped[int | None] = mapped_column(Integer)
    price_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    district: Mapped[str | None] = mapped_column(String(128), index=True)
    address: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    lat: Mapped[float | None] = mapped_column()
    lon: Mapped[float | None] = mapped_column()
    long_term_availability: Mapped[str] = mapped_column(
        String(32), default=LongTermAvailability.AVAILABLE.value, nullable=False
    )
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    freshness_reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    draft_step: Mapped[str | None] = mapped_column(String(64))
    moderation_comment: Mapped[str | None] = mapped_column(Text)

    photos: Mapped[list[PropertyPhoto]] = relationship(
        back_populates="property", cascade="all, delete-orphan", order_by="PropertyPhoto.sort_order"
    )
    features: Mapped[PropertyFeature | None] = relationship(
        back_populates="property",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    realtor_links: Mapped[list[PropertyRealtor]] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )
    intervals: Mapped[list[AvailabilityInterval]] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )


class PropertyRealtor(Base, TimestampMixin):
    __tablename__ = "property_realtors"
    __table_args__ = (
        UniqueConstraint("property_id", "realtor_id", name="uq_property_realtor"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), index=True
    )
    realtor_id: Mapped[int] = mapped_column(
        ForeignKey("realtor_profiles.id", ondelete="CASCADE"), index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    property: Mapped[Property] = relationship(back_populates="realtor_links")


class PropertyPhoto(Base, TimestampMixin):
    __tablename__ = "property_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), index=True
    )
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    thumb_url: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)

    property: Mapped[Property] = relationship(back_populates="photos")


class PropertyFeature(Base, TimestampMixin):
    __tablename__ = "property_features"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), unique=True
    )
    wifi: Mapped[bool] = mapped_column(Boolean, default=False)
    air_conditioning: Mapped[bool] = mapped_column(Boolean, default=False)
    kitchen: Mapped[bool] = mapped_column(Boolean, default=False)
    oven: Mapped[bool] = mapped_column(Boolean, default=False)
    microwave: Mapped[bool] = mapped_column(Boolean, default=False)
    parking: Mapped[bool] = mapped_column(Boolean, default=False)
    furniture: Mapped[bool] = mapped_column(Boolean, default=False)
    dishwasher: Mapped[bool] = mapped_column(Boolean, default=False)
    sea_view: Mapped[bool] = mapped_column(Boolean, default=False)
    bedrooms_with_windows: Mapped[bool] = mapped_column(Boolean, default=False)
    washing_machine: Mapped[bool] = mapped_column(Boolean, default=False)
    balcony: Mapped[bool] = mapped_column(Boolean, default=False)
    elevator: Mapped[bool] = mapped_column(Boolean, default=False)
    central_heating: Mapped[bool] = mapped_column(Boolean, default=False)
    hot_water: Mapped[bool] = mapped_column(Boolean, default=False)
    pets_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    tv: Mapped[bool] = mapped_column(Boolean, default=False)
    mountain_view: Mapped[bool] = mapped_column(Boolean, default=False)

    property: Mapped[Property] = relationship(back_populates="features")


class AvailabilityInterval(Base, TimestampMixin):
    __tablename__ = "availability_intervals"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)  # exclusive
    kind: Mapped[str] = mapped_column(String(32), default=AvailabilityKind.BOOKED.value)
    note: Mapped[str | None] = mapped_column(String(255))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    property: Mapped[Property] = relationship(back_populates="intervals")


class Favorite(Base, TimestampMixin):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "property_id", name="uq_favorite"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), index=True
    )
