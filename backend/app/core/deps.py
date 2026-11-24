from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import parse_session_token, validate_init_data
from app.db.enums import UserRole
from app.db.models import User
from app.db.session import get_db
from app.services.users import ensure_user_from_telegram


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> User:
    telegram_id: int | None = None
    tg_user = None

    bearer = (
        authorization.split(" ", 1)[1].strip()
        if authorization and authorization.lower().startswith("bearer ")
        else None
    )

    if bearer:
        try:
            telegram_id = parse_session_token(bearer)
        except HTTPException:
            # Expired/invalid session: fall back to live Telegram initData
            telegram_id = None

    if telegram_id is None:
        if not x_telegram_init_data:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
        parsed = validate_init_data(x_telegram_init_data)
        tg_user = parsed["_user"]
        telegram_id = tg_user.id

    result = await db.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(selectinload(User.roles), selectinload(User.realtor_profile))
    )
    user = result.scalar_one_or_none()
    if user is None:
        if tg_user is None:
            if x_telegram_init_data:
                parsed = validate_init_data(x_telegram_init_data)
                tg_user = parsed["_user"]
            else:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not registered")
        user = await ensure_user_from_telegram(db, tg_user)
    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User blocked")
    return user


async def get_optional_user(
    authorization: str | None = Header(default=None),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not authorization and not x_telegram_init_data:
        return None
    try:
        return await get_current_user(authorization, x_telegram_init_data, db)
    except HTTPException:
        return None


def require_roles(*roles: UserRole):
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if not any(user.has_role(r) for r in roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return _checker


RequireAdmin = Depends(require_roles(UserRole.ADMIN))
RequireRealtor = Depends(require_roles(UserRole.REALTOR, UserRole.ADMIN))
