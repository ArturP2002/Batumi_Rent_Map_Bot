from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DashboardOut(BaseModel):
    active_properties: int
    moderation_properties: int
    active_realtors: int
    inquiries_open: int
    deals_pending: int
    reviews_pending: int
    attention: list[dict]


class RealtorCreateIn(BaseModel):
    telegram_id: int
    display_name: str
    bio: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    telegram_contact: str | None = None


class RealtorOut(ORMModel):
    id: int
    user_id: int
    display_name: str
    email: str | None = None
    bio: str | None
    phone: str | None
    whatsapp: str | None
    telegram_contact: str | None
    photo_url: str | None
    can_publish: bool
    is_blocked: bool
    rating_avg: float
    rating_count: int
    telegram_id: int | None = None
    active_listings: int = 0
    has_credentials: bool = False


class ModerationActionIn(BaseModel):
    action: str
    comment: str | None = None


class SettingsOut(BaseModel):
    freshness_days: int = 14
    freshness_remind_days: int = 3
    freshness_hide_days: int = 4
    districts: list[str] = []


class SettingsUpdateIn(BaseModel):
    freshness_days: int | None = None
    freshness_remind_days: int | None = None
    freshness_hide_days: int | None = None
    districts: list[str] | None = None


class StatsQuery(BaseModel):
    from_date: date | None = None
    to_date: date | None = None


class StatsOut(BaseModel):
    users: int
    new_users: int
    property_views: int
    contact_clicks: int
    inquiries: int
    deals_confirmed: int
    reviews_published: int
    conversions: dict[str, float]
    top_properties: list[dict]
    top_realtors: list[dict]
    series: list[dict]


class AnalyticsEventIn(BaseModel):
    event_type: str
    property_id: int | None = None
    realtor_id: int | None = None
    session_id: str | None = None
    referrer: str | None = None
    context: dict | None = None
