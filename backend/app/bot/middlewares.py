from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.core.security import TelegramUser
from app.db.session import SessionLocal
from app.services.users import ensure_user_from_telegram

logger = logging.getLogger(__name__)


class DbUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        try:
            async with SessionLocal() as session:
                data["db"] = session
                if tg_user:
                    user = await ensure_user_from_telegram(
                        session,
                        TelegramUser(
                            id=tg_user.id,
                            first_name=tg_user.first_name,
                            last_name=tg_user.last_name,
                            username=tg_user.username,
                            language_code=getattr(tg_user, "language_code", None),
                        ),
                    )
                    data["db_user"] = user
                return await handler(event, data)
        except Exception:
            logger.exception("Bot handler failed (often DB connection)")
            if isinstance(event, Message):
                try:
                    await event.answer(
                        "Временная ошибка сервера. Нажмите /start и попробуйте ещё раз."
                    )
                except Exception:
                    logger.exception("Failed to send error reply")
            # Do not re-raise: keeps polling alive after a single failed update.
            return None
