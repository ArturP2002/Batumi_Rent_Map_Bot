from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, ModerationHistory


async def write_audit(
    db: AsyncSession,
    actor_user_id: int | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=json.dumps(payload) if payload else None,
        )
    )
    await db.commit()


async def write_moderation(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    action: str,
    actor_user_id: int | None,
    comment: str | None = None,
) -> None:
    db.add(
        ModerationHistory(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_user_id=actor_user_id,
            comment=comment,
        )
    )
    await db.commit()
