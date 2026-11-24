from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class InquiryCreateIn(BaseModel):
    property_id: int
    realtor_id: int
    channel: str


class InquiryOut(ORMModel):
    id: int
    user_id: int
    realtor_id: int
    property_id: int
    channel: str
    status: str
    note: str | None = None
    created_at: datetime
    last_event_at: datetime | None = None


class DealCreateIn(BaseModel):
    inquiry_id: int | None = None
    property_id: int
    realtor_id: int
    client_user_id: int
    start_date: date | None = None
    end_date: date | None = None


class ConfirmationOut(ORMModel):
    side: str
    decision: str
    decided_at: datetime | None = None
    comment: str | None = None


class DealOut(ORMModel):
    id: int
    inquiry_id: int | None
    property_id: int
    realtor_id: int
    client_user_id: int
    start_date: date | None
    end_date: date | None
    status: str
    admin_comment: str | None = None
    confirmed_at: datetime | None = None
    confirmations: list[ConfirmationOut] = []


class DealDecisionIn(BaseModel):
    decision: str = Field(description="approved|rejected")
    comment: str | None = None


class ReviewCreateIn(BaseModel):
    deal_id: int
    rating: int = Field(ge=1, le=5)
    text: str = Field(max_length=1000)


class ReviewOut(ORMModel):
    id: int
    deal_id: int
    author_user_id: int
    realtor_id: int
    property_id: int | None
    rating: int
    text: str
    status: str
    created_at: datetime
