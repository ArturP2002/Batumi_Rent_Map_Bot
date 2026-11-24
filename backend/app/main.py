from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, bot_api, public
from app.core.config import get_settings
from app.db.bootstrap import bootstrap_db
from app.db.session import SessionLocal, engine
from app.services.settings import ensure_defaults


@asynccontextmanager
async def lifespan(_: FastAPI):
    await bootstrap_db(engine)
    async with SessionLocal() as db:
        await ensure_defaults(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Batumi Rent Map API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(public.router)
    app.include_router(admin.router)
    app.include_router(bot_api.router)

    @app.get("/api/health")
    async def health():
        return {"ok": True, "service": "batumi-rent-map"}

    return app


app = create_app()
