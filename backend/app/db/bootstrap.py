"""Create tables and apply lightweight column patches for local/dev DBs."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import models  # noqa: F401 — register metadata
from app.db.base import Base


async def bootstrap_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)
        # create_all does not add columns to existing tables — patch manually.
        await conn.execute(
            text(
                "ALTER TABLE realtor_profiles "
                "ADD COLUMN IF NOT EXISTS email VARCHAR(255)"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE realtor_profiles "
                "ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"
            )
        )
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_realtor_profiles_email "
                "ON realtor_profiles (email) "
                "WHERE email IS NOT NULL"
            )
        )
