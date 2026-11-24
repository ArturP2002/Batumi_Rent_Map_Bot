from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class MessageOut(BaseModel):
    ok: bool = True
    message: str | None = None


class AuthSessionOut(BaseModel):
    token: str
    telegram_id: int
    roles: list[str]
    expires_hint: datetime | None = None
