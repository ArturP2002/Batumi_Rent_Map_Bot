from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings


async def geocode_address(address: str) -> tuple[float, float]:
    settings = get_settings()
    params = {
        "q": f"{address}, Batumi, Georgia",
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": settings.geocoder_user_agent}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(settings.geocoder_url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Address not found, send location pin")
    return float(data[0]["lat"]), float(data[0]["lon"])
