from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import NotificationLog, User


def deep_link(path: str) -> str:
    """Build WebApp URL with startapp-like hash for Mini App router."""
    base = get_settings().webapp_url.rstrip("/")
    return f"{base}?startapp={path}"


async def enqueue_notification(
    db: AsyncSession,
    *,
    user_id: int,
    kind: str,
    idempotency_key: str,
    text: str,
    webapp_path: str | None = None,
    payload: dict[str, Any] | None = None,
) -> NotificationLog | None:
    existing = (
        await db.execute(
            select(NotificationLog).where(NotificationLog.idempotency_key == idempotency_key)
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    body = {"text": text, "webapp_path": webapp_path, **(payload or {})}
    log = NotificationLog(
        user_id=user_id,
        kind=kind,
        idempotency_key=idempotency_key,
        payload_json=json.dumps(body),
        sent=False,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def mark_sent(
    db: AsyncSession, log: NotificationLog, *, message_id: int | None = None, error: str | None = None
) -> None:
    log.sent = error is None
    log.telegram_message_id = message_id
    log.error = error
    await db.commit()


async def pending_notifications(db: AsyncSession, limit: int = 50) -> list[NotificationLog]:
    result = await db.execute(
        select(NotificationLog)
        .where(NotificationLog.sent.is_(False), NotificationLog.error.is_(None))
        .order_by(NotificationLog.id.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def resolve_telegram_id(db: AsyncSession, user_id: int) -> int | None:
    user = await db.get(User, user_id)
    return user.telegram_id if user else None
