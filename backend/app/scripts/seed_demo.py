"""Seed 10 curated demo listings with external photo URLs (no MinIO required).

Usage (from repo root, with DB up):

    cd backend && source .venv/bin/activate
    ENV_FILE=../.env PYTHONPATH=. python -m app.scripts.seed_demo
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Allow running without exporting ENV_FILE
_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("ENV_FILE", str(_ROOT / ".env"))

from app.core.security import TelegramUser, hash_password, normalize_email
from app.db.bootstrap import bootstrap_db
from app.db.enums import PropertyStatus, RentType
from app.db.models import Property, PropertyPhoto, RealtorProfile, User
from app.db.session import SessionLocal, engine
from app.schemas.property import FeaturesIn, PropertyCreateIn
from app.services import properties as properties_svc
from app.services.properties import _point
from app.services.settings import ensure_defaults
from app.services.users import create_realtor, ensure_user_from_telegram


def _img(photo_id: str, w: int = 1200) -> str:
    return f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w={w}&q=80"


DEMO_LISTINGS = [
    {
        "title": "Студия у моря, Новый бульвар",
        "rent_type": RentType.DAILY.value,
        "rooms": "studio",
        "area_m2": 32,
        "floor": 8,
        "floors_total": 22,
        "sleeping_places": 2,
        "price_usd": 45,
        "district": "Новый бульвар",
        "address": "ул. Новая набережная, 12",
        "lat": 41.6412,
        "lon": 41.6335,
        "description": "Светлая студия с видом на море. 5 минут до пляжа, Wi‑Fi, кондиционер, кухня.",
        "features": FeaturesIn(
            wifi=True,
            air_conditioning=True,
            kitchen=True,
            sea_view=True,
            washing_machine=True,
            elevator=True,
            hot_water=True,
            tv=True,
        ),
        "photos": [
            "photo-1502672260266-1c1ef2d93688",
            "photo-1522708323590-d24dbb6b0267",
            "photo-1560448204-e02f11c3d0e2",
        ],
    },
    {
        "title": "2к в Старом Батуми",
        "rent_type": RentType.LONG_TERM.value,
        "rooms": "2",
        "area_m2": 68,
        "floor": 3,
        "floors_total": 5,
        "sleeping_places": 3,
        "price_usd": 520,
        "district": "Старый Батуми",
        "address": "ул. Мемеда Абашидзе, 45",
        "lat": 41.6498,
        "lon": 41.6410,
        "description": "Уютная двушка в историческом центре. Рядом кафе и бульвар. Мебель, стиралка, балкон.",
        "features": FeaturesIn(
            wifi=True,
            kitchen=True,
            furniture=True,
            washing_machine=True,
            balcony=True,
            hot_water=True,
            central_heating=True,
            tv=True,
        ),
        "photos": [
            "photo-1493809842364-78817add7ffb",
            "photo-1484154218962-a197022b5858",
            "photo-1505693416388-ac5ce068fe85",
        ],
    },
    {
        "title": "Апартаменты с видом на горы",
        "rent_type": RentType.DAILY.value,
        "rooms": "1",
        "area_m2": 42,
        "floor": 12,
        "floors_total": 18,
        "sleeping_places": 2,
        "price_usd": 55,
        "district": "Горный Батуми",
        "address": "ул. Горная, 7",
        "lat": 41.6285,
        "lon": 41.6520,
        "description": "Панорамный вид на горы. Идеально для пары. Парковка во дворе.",
        "features": FeaturesIn(
            wifi=True,
            air_conditioning=True,
            kitchen=True,
            parking=True,
            mountain_view=True,
            elevator=True,
            washing_machine=True,
            tv=True,
        ),
        "photos": [
            "photo-1600596542815-ffad4c1539a9",
            "photo-1600607687939-ce8a6c25118c",
            "photo-1600585154340-be6161a56a0c",
        ],
    },
    {
        "title": "3к семейная у Багратиони",
        "rent_type": RentType.LONG_TERM.value,
        "rooms": "3",
        "area_m2": 95,
        "floor": 5,
        "floors_total": 9,
        "sleeping_places": 5,
        "price_usd": 780,
        "district": "Багратиони",
        "address": "пр. Багратиони, 88",
        "lat": 41.6502,
        "lon": 41.6418,
        "description": "Просторная квартира для семьи. Можно с питомцами. Посудомойка, мебель, лифт.",
        "features": FeaturesIn(
            wifi=True,
            kitchen=True,
            oven=True,
            dishwasher=True,
            furniture=True,
            washing_machine=True,
            elevator=True,
            pets_allowed=True,
            hot_water=True,
            central_heating=True,
        ),
        "photos": [
            "photo-1560184897-ae75f418493e",
            "photo-1560185127-6ed189bf02f4",
            "photo-1556912173-46c336c7fd55",
        ],
    },
    {
        "title": "Лофт у пляжа",
        "rent_type": RentType.DAILY.value,
        "rooms": "1",
        "area_m2": 50,
        "floor": 4,
        "floors_total": 22,
        "sleeping_places": 3,
        "price_usd": 70,
        "district": "Новый бульвар",
        "address": "ул. Новая набережная, 12",
        "lat": 41.6412,
        "lon": 41.6335,
        "description": "Тот же дом у моря, другой этаж. Балкон, Wi‑Fi, кондиционер.",
        "features": FeaturesIn(
            wifi=True,
            air_conditioning=True,
            kitchen=True,
            sea_view=True,
            balcony=True,
            washing_machine=True,
            furniture=True,
            tv=True,
        ),
        "photos": [
            "photo-1630698747733-3f2f0ea0c0b1",
            "photo-1616594039964-ae9021a400a0",
            "photo-1615529328331-f8917597711f",
        ],
    },
    {
        "title": "Компактная 1к в том же доме",
        "rent_type": RentType.LONG_TERM.value,
        "rooms": "1",
        "area_m2": 38,
        "floor": 1,
        "floors_total": 5,
        "sleeping_places": 2,
        "price_usd": 430,
        "district": "Старый Батуми",
        "address": "ул. Мемеда Абашидзе, 45",
        "lat": 41.6498,
        "lon": 41.6410,
        "description": "Ещё одна квартира в доме на Абашидзе, 45. Бюджетный вариант для одного или пары.",
        "features": FeaturesIn(
            wifi=True,
            kitchen=True,
            furniture=True,
            washing_machine=True,
            hot_water=True,
            elevator=True,
        ),
        "photos": [
            "photo-1522771739844-6a9f6d5f14af",
            "photo-1536376072261-38c75010e6c9",
        ],
    },
    {
        "title": "Пентхаус с террасой",
        "rent_type": RentType.DAILY.value,
        "rooms": "3",
        "area_m2": 120,
        "floor": 20,
        "floors_total": 22,
        "sleeping_places": 6,
        "price_usd": 140,
        "district": "Новый бульвар",
        "address": "ул. Новая набережная, 12",
        "lat": 41.6412,
        "lon": 41.6335,
        "description": "Верхние этажи того же дома у моря. Терраса, для компании или семьи.",
        "features": FeaturesIn(
            wifi=True,
            air_conditioning=True,
            kitchen=True,
            oven=True,
            dishwasher=True,
            sea_view=True,
            balcony=True,
            elevator=True,
            parking=True,
            washing_machine=True,
            tv=True,
            furniture=True,
        ),
        "photos": [
            "photo-1600607687644-c7171b42498f",
            "photo-1600566753190-17f0baa2a6c3",
            "photo-1600210492486-724fe5c67fb0",
        ],
    },
    {
        "title": "Тихая 2к у парка",
        "rent_type": RentType.LONG_TERM.value,
        "rooms": "2",
        "area_m2": 74,
        "floor": 4,
        "floors_total": 5,
        "sleeping_places": 4,
        "price_usd": 610,
        "district": "Старый Батуми",
        "address": "ул. Мемеда Абашидзе, 45",
        "lat": 41.6498,
        "lon": 41.6410,
        "description": "Та же дом, другой подъезд. Спокойный двор, рядом парк. Для удалённой работы.",
        "features": FeaturesIn(
            wifi=True,
            kitchen=True,
            furniture=True,
            washing_machine=True,
            balcony=True,
            bedrooms_with_windows=True,
            hot_water=True,
            central_heating=True,
            tv=True,
        ),
        "photos": [
            "photo-1554995207-c18c203602cb",
            "photo-1616486338812-3dadae4b4ace",
            "photo-1616137466211-f939a420be84",
        ],
    },
    {
        "title": "Студия в новом ЖК",
        "rent_type": RentType.DAILY.value,
        "rooms": "studio",
        "area_m2": 28,
        "floor": 10,
        "floors_total": 20,
        "sleeping_places": 2,
        "price_usd": 38,
        "district": "Багратиони",
        "address": "Alliance Palace, 14",
        "lat": 41.6185,
        "lon": 41.6180,
        "description": "Новая студия с техникой. Чистая, компактная, удобно для короткого заезда.",
        "features": FeaturesIn(
            wifi=True,
            air_conditioning=True,
            kitchen=True,
            microwave=True,
            elevator=True,
            washing_machine=True,
            hot_water=True,
            tv=True,
        ),
        "photos": [
            "photo-1595526114035-0d45ed16cfbf",
            "photo-1598928506311-c55ded91a20c",
        ],
    },
    {
        "title": "4к для большой семьи",
        "rent_type": RentType.LONG_TERM.value,
        "rooms": "4+",
        "area_m2": 140,
        "floor": 2,
        "floors_total": 6,
        "sleeping_places": 7,
        "price_usd": 1100,
        "district": "Аладжоба",
        "address": "ул. Сельская, 4",
        "lat": 41.6055,
        "lon": 41.6020,
        "description": "Большой дом-квартира с двором. Парковка, мебель, можно с детьми и питомцами.",
        "features": FeaturesIn(
            wifi=True,
            kitchen=True,
            oven=True,
            dishwasher=True,
            parking=True,
            furniture=True,
            washing_machine=True,
            pets_allowed=True,
            balcony=True,
            hot_water=True,
            central_heating=True,
            mountain_view=True,
        ),
        "photos": [
            "photo-1600585154526-990dced4db0d",
            "photo-1600573472592-401b489a3cdc",
            "photo-1600047509807-ba8f99d2cdde",
        ],
    },
]


async def _ensure_demo_realtor(db) -> RealtorProfile:
    # Prefer existing demo realtor by telegram stub id
    existing = (
        await db.execute(
            select(RealtorProfile)
            .join(User, User.id == RealtorProfile.user_id)
            .where(User.telegram_id == 900001)
            .options(selectinload(RealtorProfile.user))
        )
    ).scalar_one_or_none()
    if existing:
        if not existing.email:
            existing.email = normalize_email("demo.realtor@batumi.local")
            existing.password_hash = hash_password("password1")
            await db.commit()
            await db.refresh(existing)
        return existing

    await ensure_user_from_telegram(
        db,
        TelegramUser(id=900001, first_name="Demo", last_name="Realtor", username="demo_realtor"),
    )
    profile = await create_realtor(
        db,
        telegram_id=900001,
        display_name="Nino Demo",
        bio="Демо-риелтор Batumi Rent Map. Тестовые объекты на карте.",
        phone="+995555000001",
        whatsapp="+995555000001",
        telegram_contact="@demo_realtor",
        email="demo.realtor@batumi.local",
        password="password1",
    )
    return profile


async def main() -> None:
    await bootstrap_db(engine)
    async with SessionLocal() as db:
        await ensure_defaults(db)
        realtor = await _ensure_demo_realtor(db)
        existing = (
            await db.execute(
                select(Property)
                .where(Property.created_by_user_id == realtor.user_id)
                .order_by(Property.id.asc())
            )
        ).scalars().all()

        created = 0
        updated = 0
        for idx, item in enumerate(DEMO_LISTINGS):
            if idx < len(existing):
                prop = existing[idx]
                prop.rent_type = item["rent_type"]
                prop.rooms = item["rooms"]
                prop.area_m2 = Decimal(item["area_m2"])
                prop.floor = item["floor"]
                prop.floors_total = item["floors_total"]
                prop.sleeping_places = item["sleeping_places"]
                prop.price_usd = Decimal(item["price_usd"])
                prop.district = item["district"]
                prop.address = item["address"]
                prop.description = f"{item['title']}\n\n{item['description']}"
                prop.lat = item["lat"]
                prop.lon = item["lon"]
                prop.location = _point(item["lat"], item["lon"])
                prop.status = PropertyStatus.ACTIVE.value
                now = datetime.now(timezone.utc)
                prop.published_at = now
                prop.last_confirmed_at = now
                await db.commit()
                updated += 1
                print(f"~ {item['title']} (#{prop.id})")
                continue

            prop = await properties_svc.create_property(
                db,
                PropertyCreateIn(
                    rent_type=item["rent_type"],
                    rooms=item["rooms"],
                    area_m2=Decimal(item["area_m2"]),
                    floor=item["floor"],
                    floors_total=item["floors_total"],
                    sleeping_places=item["sleeping_places"],
                    price_usd=Decimal(item["price_usd"]),
                    district=item["district"],
                    address=item["address"],
                    description=f"{item['title']}\n\n{item['description']}",
                    lat=item["lat"],
                    lon=item["lon"],
                    features=item["features"],
                    realtor_ids=[realtor.id],
                    primary_realtor_id=realtor.id,
                ),
                created_by_user_id=realtor.user_id,
                status=PropertyStatus.ACTIVE.value,
            )
            now = datetime.now(timezone.utc)
            prop.published_at = now
            prop.last_confirmed_at = now
            for pidx, photo_id in enumerate(item["photos"]):
                url = _img(photo_id)
                thumb = _img(photo_id, w=480)
                db.add(
                    PropertyPhoto(
                        property_id=prop.id,
                        object_key=f"seed/{prop.id}/{pidx}-{photo_id}",
                        url=url,
                        thumb_url=thumb,
                        sort_order=pidx,
                        width=1200,
                        height=800,
                    )
                )
            await db.commit()
            created += 1
            print(f"+ {item['title']} (#{prop.id}, {prop.public_code})")

        print(f"\nDone: {created} created, {updated} updated.")
        print("Realtor login: demo.realtor@batumi.local / password1")


if __name__ == "__main__":
    asyncio.run(main())
