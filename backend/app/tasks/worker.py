from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import select

from app.bot.keyboards import freshness_kb
from app.core.config import get_settings
from app.db.enums import PropertyStatus
from app.db.models import Property
from app.db.session import SessionLocal
from app.services.analytics import aggregate_daily
from app.services.notifications import (
    deep_link,
    mark_sent,
    pending_notifications,
    resolve_telegram_id,
)
from app.services.settings import get_app_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("worker")


async def process_notifications(bot: Bot | None) -> None:
    async with SessionLocal() as db:
        logs = await pending_notifications(db)
        for item in logs:
            if bot is None:
                continue
            tg_id = await resolve_telegram_id(db, item.user_id)
            payload = json.loads(item.payload_json or "{}")
            text = payload.get("text", item.kind)
            try:
                kb = None
                path = payload.get("webapp_path")
                if path:
                    url = deep_link(path)
                    kb = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="Открыть в приложении", web_app=WebAppInfo(url=url))]
                        ]
                    )
                msg = await bot.send_message(tg_id, text, reply_markup=kb)
                await mark_sent(db, item, message_id=msg.message_id)
            except Exception as exc:
                await mark_sent(db, item, error=str(exc))
                log.exception("notify failed %s", item.id)


async def process_freshness(bot: Bot | None) -> None:
    async with SessionLocal() as db:
        settings = await get_app_settings(db)
        now = datetime.now(timezone.utc)
        props = (
            await db.execute(
                select(Property).where(Property.status == PropertyStatus.ACTIVE.value)
            )
        ).scalars().all()
        for prop in props:
            base = prop.last_confirmed_at or prop.published_at or prop.created_at
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
            age = now - base
            ask_after = timedelta(days=settings.freshness_days)
            remind_after = ask_after + timedelta(days=settings.freshness_remind_days)
            hide_after = remind_after + timedelta(days=settings.freshness_hide_days)

            if age >= hide_after:
                prop.status = PropertyStatus.HIDDEN.value
                continue
            if age >= remind_after and bot and prop.created_by_user_id:
                tg_id = await resolve_telegram_id(db, prop.created_by_user_id)
                if tg_id:
                    try:
                        await bot.send_message(
                            tg_id,
                            (
                                f"Напоминание: подтвердите актуальность объявления "
                                f"{prop.public_code}. Без ответа оно будет скрыто."
                            ),
                            reply_markup=freshness_kb(prop.id),
                        )
                        prop.freshness_reminded_at = now
                    except Exception:
                        log.exception("freshness remind failed")
            elif age >= ask_after and bot and prop.created_by_user_id and not prop.freshness_reminded_at:
                tg_id = await resolve_telegram_id(db, prop.created_by_user_id)
                if tg_id:
                    try:
                        await bot.send_message(
                            tg_id,
                            (
                                f"Пожалуйста, подтвердите актуальность объявления "
                                f"{prop.public_code}."
                            ),
                            reply_markup=freshness_kb(prop.id),
                        )
                        prop.freshness_reminded_at = now
                    except Exception:
                        log.exception("freshness ask failed")
        await db.commit()


async def loop() -> None:
    settings = get_settings()
    bot = None
    if settings.bot_token and settings.bot_token != "replace_me":
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    log.info("Worker started")
    tick = 0
    while True:
        try:
            await process_notifications(bot)
            await process_freshness(bot)
            if tick % 24 == 0:
                async with SessionLocal() as db:
                    await aggregate_daily(db)
        except Exception:
            log.exception("worker tick failed")
        tick += 1
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(loop())
