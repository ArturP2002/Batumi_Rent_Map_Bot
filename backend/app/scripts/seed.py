"""Seed districts settings and optionally generate demo properties for map load tests."""

from __future__ import annotations

import argparse
import asyncio
import random
from decimal import Decimal

from sqlalchemy import text

from app.db.base import Base
from app.db.enums import PropertyStatus, RentType
from app.db.session import SessionLocal, engine
from app.schemas.property import FeaturesIn, PropertyCreateIn
from app.services import properties as properties_svc
from app.services.settings import ensure_defaults
from app.services.users import create_realtor


BATUMI_BOUNDS = {
    "min_lat": 41.58,
    "max_lat": 41.66,
    "min_lon": 41.58,
    "max_lon": 41.70,
}

DISTRICTS = ["Старый Батуми", "Новый бульвар", "Багратиони", "Аладжоба", "Горный Батуми"]
ROOMS = ["studio", "1", "2", "3", "4+"]


async def bootstrap(count: int) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        await ensure_defaults(db)
        realtor = await create_realtor(
            db,
            telegram_id=900001,
            display_name="Demo Realtor",
            bio="Тестовый риелтор для сидов",
            phone="+995555000001",
            whatsapp="+995555000001",
            telegram_contact="@demo_realtor",
        )
        for i in range(count):
            lat = random.uniform(BATUMI_BOUNDS["min_lat"], BATUMI_BOUNDS["max_lat"])
            lon = random.uniform(BATUMI_BOUNDS["min_lon"], BATUMI_BOUNDS["max_lon"])
            rent_type = random.choice([RentType.LONG_TERM.value, RentType.DAILY.value])
            price = (
                random.randint(20, 120)
                if rent_type == RentType.DAILY.value
                else random.randint(250, 1200)
            )
            feats = {k: random.random() > 0.6 for k in FeaturesIn().model_dump()}
            await properties_svc.create_property(
                db,
                PropertyCreateIn(
                    rent_type=rent_type,
                    rooms=random.choice(ROOMS),
                    area_m2=Decimal(random.randint(25, 140)),
                    floor=random.randint(1, 20),
                    floors_total=random.randint(5, 25),
                    sleeping_places=random.randint(1, 6),
                    price_usd=Decimal(price),
                    district=random.choice(DISTRICTS),
                    address=f"Batumi demo street {i}",
                    description="Seed listing for Batumi Rent Map",
                    lat=lat,
                    lon=lon,
                    features=FeaturesIn(**feats),
                    realtor_ids=[realtor.id],
                    primary_realtor_id=realtor.id,
                ),
                created_by_user_id=realtor.user_id,
                status=PropertyStatus.ACTIVE.value,
            )
            if (i + 1) % 100 == 0:
                print(f"seeded {i + 1}/{count}")
        print(f"Done. Seeded {count} properties.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()
    asyncio.run(bootstrap(args.count))
