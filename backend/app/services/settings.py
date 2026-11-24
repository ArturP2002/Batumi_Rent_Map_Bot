from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SystemSetting
from app.schemas.admin import SettingsOut, SettingsUpdateIn

DEFAULTS = {
    "freshness_days": "14",
    "freshness_remind_days": "3",
    "freshness_hide_days": "4",
    "districts": json.dumps(
        ["Старый Батуми", "Новый бульвар", "Багратиони", "Аладжоба", "Горный Батуми"]
    ),
}


async def ensure_defaults(db: AsyncSession) -> None:
    for key, value in DEFAULTS.items():
        existing = (
            await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        ).scalar_one_or_none()
        if not existing:
            db.add(SystemSetting(key=key, value=value))
    await db.commit()


async def get_settings_map(db: AsyncSession) -> dict[str, str]:
    await ensure_defaults(db)
    rows = (await db.execute(select(SystemSetting))).scalars().all()
    return {r.key: r.value for r in rows}


async def get_app_settings(db: AsyncSession) -> SettingsOut:
    m = await get_settings_map(db)
    return SettingsOut(
        freshness_days=int(m["freshness_days"]),
        freshness_remind_days=int(m["freshness_remind_days"]),
        freshness_hide_days=int(m["freshness_hide_days"]),
        districts=json.loads(m["districts"]),
    )


async def update_app_settings(db: AsyncSession, data: SettingsUpdateIn) -> SettingsOut:
    m = await get_settings_map(db)
    mapping = {
        "freshness_days": data.freshness_days,
        "freshness_remind_days": data.freshness_remind_days,
        "freshness_hide_days": data.freshness_hide_days,
        "districts": json.dumps(data.districts) if data.districts is not None else None,
    }
    for key, value in mapping.items():
        if value is None:
            continue
        row = (
            await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        ).scalar_one()
        row.value = str(value) if key != "districts" else value
    await db.commit()
    return await get_app_settings(db)
