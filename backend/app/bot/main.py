from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import setup_routers
from app.bot.middlewares import DbUserMiddleware
from app.core.config import get_settings
from app.db.bootstrap import bootstrap_db
from app.db.session import engine


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [bot] %(name)s: %(message)s",
    )
    settings = get_settings()
    if not settings.bot_token or settings.bot_token == "replace_me":
        raise SystemExit("Укажите BOT_TOKEN в файле .env")

    await bootstrap_db(engine)
    logging.getLogger(__name__).info(
        "Starting bot polling (db=%s)",
        settings.database_url.split("@")[-1],
    )
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    me = await bot.get_me()
    logging.getLogger(__name__).info("Authorized as @%s (%s)", me.username, me.id)

    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbUserMiddleware())
    dp.include_router(setup_routers())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
