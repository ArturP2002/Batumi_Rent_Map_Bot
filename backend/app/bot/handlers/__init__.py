from aiogram import Router

from app.bot.handlers import common, deals, properties, realtor_auth


def setup_routers() -> Router:
    root = Router()
    root.include_router(common.router)
    root.include_router(realtor_auth.router)
    root.include_router(properties.router)
    root.include_router(deals.router)
    return root
