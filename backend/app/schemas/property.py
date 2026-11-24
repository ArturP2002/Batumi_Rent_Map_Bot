from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class FeaturesIn(BaseModel):
    wifi: bool = False
    air_conditioning: bool = False
    kitchen: bool = False
    oven: bool = False
    microwave: bool = False
    parking: bool = False
    furniture: bool = False
    dishwasher: bool = False
    sea_view: bool = False
    bedrooms_with_windows: bool = False
    washing_machine: bool = False
    balcony: bool = False
    elevator: bool = False
    central_heating: bool = False
    hot_water: bool = False
    pets_allowed: bool = False
    tv: bool = False
    mountain_view: bool = False


class FeaturesOut(FeaturesIn, ORMModel):
    pass


class PhotoOut(ORMModel):
    id: int
    url: str
    thumb_url: str | None = None
    sort_order: int


class PropertyMarkerOut(BaseModel):
    id: int
    public_code: str
    price_usd: Decimal
    rent_type: str
    rooms: str
    lat: float
    lon: float
    district: str | None = None
    area_m2: Decimal | None = None
    cover_url: str | None = None


class PropertyCardOut(ORMModel):
    id: int
    public_code: str
    rent_type: str
    status: str
    rooms: str
    area_m2: Decimal | None = None
    price_usd: Decimal
    district: str | None = None
    address: str | None = None
    last_confirmed_at: datetime | None = None
    cover_url: str | None = None
    is_favorite: bool = False


class PropertyDetailOut(PropertyCardOut):
    floor: int | None = None
    floors_total: int | None = None
    sleeping_places: int | None = None
    description: str | None = None
    lat: float | None = None
    lon: float | None = None
    long_term_availability: str
    photos: list[PhotoOut] = []
    features: FeaturesOut | None = None
    realtor_ids: list[int] = []
    primary_realtor_id: int | None = None


class PropertyFilters(BaseModel):
    rent_type: str | None = None
    rooms: list[str] | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    amenities: list[str] | None = None
    check_in: date | None = None
    check_out: date | None = None
    bbox: str | None = Field(
        default=None, description="min_lon,min_lat,max_lon,max_lat"
    )
    q: str | None = None
    status: str | None = None
    sort: str = "newest"  # newest|price_asc|price_desc
    page: int = 1
    page_size: int = 20


class IntervalIn(BaseModel):
    start_date: date
    end_date: date
    kind: str = "booked"
    note: str | None = None


class IntervalOut(ORMModel):
    id: int
    start_date: date
    end_date: date
    kind: str
    note: str | None = None


class PropertyCreateIn(BaseModel):
    rent_type: str
    rooms: str
    area_m2: Decimal | None = None
    floor: int | None = None
    floors_total: int | None = None
    sleeping_places: int | None = None
    price_usd: Decimal
    district: str | None = None
    address: str | None = None
    description: str | None = None
    lat: float | None = None
    lon: float | None = None
    features: FeaturesIn | None = None
    realtor_ids: list[int] = []
    primary_realtor_id: int | None = None
