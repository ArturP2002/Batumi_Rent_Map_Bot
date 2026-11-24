"""Rich demo dataset for local UI / admin / stats review.

Usage (DB must be up):

    cd backend && source .venv/bin/activate
    ENV_FILE=../.env PYTHONPATH=. python -m app.scripts.seed_rich

Optional flags:
    --properties 120
    --days 45
    --wipe-demo   delete previous rich-seed rows tagged by telegram_id range 910000+
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select, text
from sqlalchemy.orm import selectinload

_ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("ENV_FILE", str(_ROOT / ".env"))

from app.core.security import TelegramUser
from app.db.bootstrap import bootstrap_db
from app.db.enums import (
    AvailabilityKind,
    ConfirmationDecision,
    ConfirmationSide,
    ContactChannel,
    DealStatus,
    InquiryStatus,
    LongTermAvailability,
    PropertyStatus,
    RentType,
    ReviewStatus,
    UserRole,
)
from app.db.models import (
    AnalyticsEvent,
    AvailabilityInterval,
    DealConfirmation,
    Favorite,
    Inquiry,
    Property,
    PropertyPhoto,
    RentalDeal,
    Review,
    User,
    UserRoleAssignment,
)
from app.db.session import SessionLocal, engine
from app.schemas.property import FeaturesIn, PropertyCreateIn
from app.services import properties as properties_svc
from app.services.reviews import recalculate_realtor_rating
from app.services.settings import ensure_defaults
from app.services.users import create_realtor, ensure_user_from_telegram

# Dedicated telegram id band so wipe is safe (must not overlap real admin IDs)
REALTOR_TG_BASE = 910100
CLIENT_TG_BASE = 920100
DEMO_TG_MAX = 929999
DEMO_TAG = "seed_rich"


DISTRICTS = [
    ("Старый Батуми", 41.6505, 41.6418),
    ("Новый бульвар", 41.6410, 41.6325),
    ("Багратиони", 41.6355, 41.6180),
    ("Аладжоба", 41.6220, 41.6055),
    ("Горный Батуми", 41.6280, 41.6550),
    ("Махинджаури", 41.6730, 41.6850),
    ("Буффет", 41.6458, 41.6250),
]

STREETS = [
    "ул. Мемеда Абашидзе",
    "пр. Руставели",
    "ул. Човхадзе",
    "ул. Горгиладзе",
    "Новая набережная",
    "ул. Пушкина",
    "ул. З. Гамсахурдия",
    "ул. Бараташвили",
]

ROOMS = ["studio", "1", "2", "3", "4+"]
PHOTO_IDS = [
    "photo-1502672260266-1c1ef2d93688",
    "photo-1522708323590-d24dbb6b0267",
    "photo-1560448204-e02f11c3d0e2",
    "photo-1493809842364-78817add7ffb",
    "photo-1484154218962-a197022b5858",
    "photo-1505693416388-ac5ce068fe85",
    "photo-1560185127-6ed189bf02f4",
    "photo-1560185893-a55cbc8c57e0",
    "photo-1600585154340-be6161a56a0c",
    "photo-1600607687939-ce8a6c25118c",
    "photo-1600566753190-17f0baa2a6c3",
    "photo-1600210492486-724fe5c67fb0",
    "photo-1616594039964-ae9021a400a0",
    "photo-1615874959474-d609969a20ed",
    "photo-1618221195710-dd6b41faaea6",
    "photo-1630699446273-8b0f0c0c0c0c",  # may 404; fallback handled via common ids
    "photo-1586023492125-27b2c045efd7",
    "photo-1616486338812-3dadae4b4ace",
    "photo-1615529328331-f8917597711f",
    "photo-1554995207-c18c203602cb",
]
# Keep only known-good Unsplash ids
PHOTO_IDS = [p for p in PHOTO_IDS if "0699446273" not in p]

REALTOR_PROFILES = [
    ("Nino Beridze", "Семейная долгосрочная аренда и новостройки у моря.", "+995555101001", "@nino_batumi"),
    ("Giorgi Kapanadze", "Посуточная аренда, апартаменты с видом на бульвар.", "+995555101002", "@giorgi_rent"),
    ("Mariami Tsiklauri", "Премиум-объекты и релокация IT-специалистов.", "+995555101003", "@mariami_homes"),
    ("Luka Maisuradze", "Бюджетные квартиры рядом с университетом.", "+995555101004", "@luka_flats"),
    ("Ana Gelashvili", "Горный район и тихие семейные дома.", "+995555101005", "@ana_mountain"),
    ("David Chikvaidze", "Быстрые сделки, WhatsApp-first.", "+995555101006", "@david_deals"),
    ("Sofia Abashidze", "Дизайнерский ремонт и апарт-отели.", "+995555101007", "@sofia_design"),
    ("Blocked Demo", "Заблокированный риелтор для проверки админки.", "+995555101099", "@blocked_demo"),
]

CLIENT_NAMES = [
    ("Alex", "Ivanov"), ("Maria", "Petrova"), ("John", "Smith"), ("Elena", "Kozlova"),
    ("Omar", "Hassan"), ("Kate", "Novik"), ("Pavel", "Sokolov"), ("Nina", "Orlova"),
    ("Ryan", "Cole"), ("Irina", "Belova"), ("Sam", "Wright"), ("Daria", "Moroz"),
    ("Leo", "Park"), ("Vera", "Smirnova"), ("Max", "Volkov"), ("Olga", "Frolova"),
    ("Tim", "Brown"), ("Anya", "Lebedeva"), ("Chris", "Lee"), ("Yulia", "Egorova"),
    ("Noah", "Green"), ("Polina", "Zaitseva"), ("Erik", "Hansen"), ("Sasha", "Kuznetsov"),
    ("Mia", "Chen"), ("Igor", "Baranov"), ("Lara", "White"), ("Denis", "Gromov"),
]

REVIEW_TEXTS = [
    "Отличный риелтор, всё показали честно и быстро помогли с заездом.",
    "Квартира соответствовала фото. Связь была оперативной.",
    "Немного задержали ключи, но в целом всё хорошо.",
    "Супер локация, рядом море. Рекомендую.",
    "Чисто, тихо, удобно для удалённой работы.",
    "Хотелось бы больше посуды на кухне, но жильё приятное.",
    "Профессиональный подход, договор оформили без сюрпризов.",
    "Вид из окна потрясающий. Обязательно вернёмся.",
    "Цена адекватная рынку. Спасибо за помощь с трансфером.",
    "Были мелкие замечания по Wi‑Fi, быстро починили.",
]

STATUSES_WEIGHTED = (
    [PropertyStatus.ACTIVE.value] * 55
    + [PropertyStatus.MODERATION.value] * 12
    + [PropertyStatus.NEEDS_FIX.value] * 8
    + [PropertyStatus.HIDDEN.value] * 8
    + [PropertyStatus.BLOCKED.value] * 5
    + [PropertyStatus.DRAFT.value] * 4
    + [PropertyStatus.ARCHIVED.value] * 3
)


def _img(photo_id: str, w: int = 1200) -> str:
    return f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w={w}&q=80"


def _utc(days_ago: float = 0, hour: int | None = None) -> datetime:
    base = datetime.now(timezone.utc) - timedelta(days=days_ago)
    if hour is not None:
        return base.replace(hour=hour % 24, minute=random.randint(0, 59), second=random.randint(0, 59), microsecond=0)
    return base


def _features() -> FeaturesIn:
    picks = {k: random.random() > 0.45 for k in FeaturesIn().model_dump()}
    picks["wifi"] = True
    picks["hot_water"] = True
    if random.random() > 0.5:
        picks["air_conditioning"] = True
    return FeaturesIn(**picks)


def _description(district: str, rooms: str, rent_type: str) -> str:
    room_label = {"studio": "студия", "1": "однокомнатная", "2": "двухкомнатная", "3": "трёхкомнатная", "4+": "просторная 4+"}.get(rooms, rooms)
    mode = "посуточно" if rent_type == RentType.DAILY.value else "на длительный срок"
    return (
        f"Светлая {room_label} квартира в районе {district}, сдаётся {mode}.\n\n"
        f"Рядом магазины, остановки и кафе. В квартире есть всё необходимое для комфортного проживания. "
        f"Идеально для {'короткого отпуска у моря' if rent_type == RentType.DAILY.value else 'релокации и удалённой работы'}.\n\n"
        f"Свяжитесь с риелтором, чтобы уточнить свободные даты и условия."
    )


async def wipe_demo(db) -> None:
    """Remove previous rich-seed users in the reserved telegram_id band."""
    users = (
        await db.execute(
            select(User).where(
                User.telegram_id >= REALTOR_TG_BASE,
                User.telegram_id <= DEMO_TG_MAX,
            )
        )
    ).scalars().all()
    user_ids = [u.id for u in users]
    if not user_ids:
        print("wipe: nothing to remove")
        return

    prop_ids = list(
        (
            await db.execute(select(Property.id).where(Property.created_by_user_id.in_(user_ids)))
        ).scalars().all()
    )
    from sqlalchemy import or_

    deal_filters = [RentalDeal.client_user_id.in_(user_ids)]
    inquiry_filters = [Inquiry.user_id.in_(user_ids)]
    if prop_ids:
        deal_filters.append(RentalDeal.property_id.in_(prop_ids))
        inquiry_filters.append(Inquiry.property_id.in_(prop_ids))
    deal_ids = list((await db.execute(select(RentalDeal.id).where(or_(*deal_filters)))).scalars().all())
    inquiry_ids = list((await db.execute(select(Inquiry.id).where(or_(*inquiry_filters)))).scalars().all())

    if deal_ids:
        await db.execute(delete(Review).where(Review.deal_id.in_(deal_ids)))
        await db.execute(delete(DealConfirmation).where(DealConfirmation.deal_id.in_(deal_ids)))
        await db.execute(delete(RentalDeal).where(RentalDeal.id.in_(deal_ids)))
    if inquiry_ids:
        await db.execute(delete(Inquiry).where(Inquiry.id.in_(inquiry_ids)))
    if prop_ids:
        await db.execute(delete(AnalyticsEvent).where(AnalyticsEvent.property_id.in_(prop_ids)))
        await db.execute(delete(Favorite).where(Favorite.property_id.in_(prop_ids)))
        await db.execute(delete(AvailabilityInterval).where(AvailabilityInterval.property_id.in_(prop_ids)))
        await db.execute(delete(Property).where(Property.id.in_(prop_ids)))

    await db.execute(delete(AnalyticsEvent).where(AnalyticsEvent.user_id.in_(user_ids)))
    await db.execute(delete(Favorite).where(Favorite.user_id.in_(user_ids)))
    await db.execute(delete(Review).where(Review.author_user_id.in_(user_ids)))
    await db.execute(delete(UserRoleAssignment).where(UserRoleAssignment.user_id.in_(user_ids)))
    await db.execute(delete(User).where(User.id.in_(user_ids)))
    await db.commit()
    print(f"wipe: removed {len(user_ids)} demo users and related data")


async def seed(properties_count: int, days: int, wipe: bool) -> None:
    random.seed(42)
    await bootstrap_db(engine)

    async with SessionLocal() as db:
        await ensure_defaults(db)
        if wipe:
            await wipe_demo(db)

        print("→ realtors")
        realtors = []
        for i, (name, bio, phone, tg) in enumerate(REALTOR_PROFILES):
            first, _, last = name.partition(" ")
            await ensure_user_from_telegram(
                db,
                TelegramUser(
                    id=REALTOR_TG_BASE + i,
                    first_name=first or name,
                    last_name=last or None,
                    username=tg.lstrip("@"),
                    language_code="ru",
                ),
            )
            profile = await create_realtor(
                db,
                telegram_id=REALTOR_TG_BASE + i,
                display_name=name,
                bio=bio,
                phone=phone,
                whatsapp=phone,
                telegram_contact=tg,
                email=f"realtor{i+1}@batumi.demo",
                password="password1",
            )
            profile.photo_url = _img(PHOTO_IDS[i % len(PHOTO_IDS)], w=400)
            if i == len(REALTOR_PROFILES) - 1:
                profile.is_blocked = True
                profile.can_publish = False
            realtors.append(profile)
            await db.commit()
        active_realtors = [r for r in realtors if not r.is_blocked]

        print("→ clients")
        clients = []
        for i, (first, last) in enumerate(CLIENT_NAMES):
            user = await ensure_user_from_telegram(
                db,
                TelegramUser(
                    id=CLIENT_TG_BASE + i,
                    first_name=first,
                    last_name=last,
                    username=f"{first.lower()}_{last.lower()}",
                    language_code="ru",
                ),
            )
            user.created_at = _utc(days_ago=random.uniform(1, days))
            clients.append(user)
        await db.commit()

        print(f"→ properties ({properties_count})")
        props: list[Property] = []
        prop_realtor: dict[int, int] = {}
        for i in range(properties_count):
            district, base_lat, base_lon = random.choice(DISTRICTS)
            rent_type = random.choice([RentType.LONG_TERM.value, RentType.DAILY.value, RentType.DAILY.value, RentType.LONG_TERM.value])
            rooms = random.choice(ROOMS)
            price = (
                random.randint(25, 160)
                if rent_type == RentType.DAILY.value
                else random.randint(280, 1600)
            )
            realtor = random.choice(active_realtors)
            status = random.choice(STATUSES_WEIGHTED)
            lat = base_lat + random.uniform(-0.012, 0.012)
            lon = base_lon + random.uniform(-0.012, 0.012)
            area = random.randint(22, 160)
            sleep = {"studio": 2, "1": 2, "2": 3, "3": 4, "4+": 6}.get(rooms, random.randint(1, 6))
            prop = await properties_svc.create_property(
                db,
                PropertyCreateIn(
                    rent_type=rent_type,
                    rooms=rooms,
                    area_m2=Decimal(area),
                    floor=random.randint(1, 22),
                    floors_total=random.randint(5, 28),
                    sleeping_places=sleep,
                    price_usd=Decimal(price),
                    district=district,
                    address=f"{random.choice(STREETS)}, {random.randint(1, 120)}",
                    description=_description(district, rooms, rent_type),
                    lat=lat,
                    lon=lon,
                    features=_features(),
                    realtor_ids=[realtor.id],
                    primary_realtor_id=realtor.id,
                ),
                created_by_user_id=realtor.user_id,
                status=status,
            )
            prop_realtor[prop.id] = realtor.id
            created_days = random.uniform(0, days)
            prop.created_at = _utc(days_ago=created_days)
            if status == PropertyStatus.ACTIVE.value:
                prop.published_at = _utc(days_ago=max(0, created_days - 1))
                prop.last_confirmed_at = _utc(days_ago=random.uniform(0, 10))
                if rent_type == RentType.LONG_TERM.value:
                    prop.long_term_availability = random.choice(
                        [
                            LongTermAvailability.AVAILABLE.value,
                            LongTermAvailability.AVAILABLE.value,
                            LongTermAvailability.OCCUPIED.value,
                            LongTermAvailability.UNKNOWN.value,
                        ]
                    )
            if status == PropertyStatus.NEEDS_FIX.value:
                prop.moderation_comment = "Добавьте больше фото и уточните адрес."
            if status == PropertyStatus.BLOCKED.value:
                prop.moderation_comment = "Подозрение на дубль / недостоверные данные."

            photo_n = random.randint(2, 6)
            chosen = random.sample(PHOTO_IDS, k=min(photo_n, len(PHOTO_IDS)))
            for pidx, pid in enumerate(chosen):
                db.add(
                    PropertyPhoto(
                        property_id=prop.id,
                        object_key=f"{DEMO_TAG}/{prop.id}/{pidx}-{pid}",
                        url=_img(pid),
                        thumb_url=_img(pid, w=480),
                        sort_order=pidx,
                        width=1200,
                        height=800,
                    )
                )

            if rent_type == RentType.DAILY.value and status == PropertyStatus.ACTIVE.value:
                # 2–4 busy intervals over next 90 days
                cursor = date.today() + timedelta(days=random.randint(0, 10))
                for _ in range(random.randint(2, 4)):
                    length = random.randint(2, 8)
                    start = cursor + timedelta(days=random.randint(1, 7))
                    end = start + timedelta(days=length)
                    db.add(
                        AvailabilityInterval(
                            property_id=prop.id,
                            start_date=start,
                            end_date=end,
                            kind=random.choice(
                                [AvailabilityKind.BOOKED.value, AvailabilityKind.BOOKED.value, AvailabilityKind.BLOCKED.value]
                            ),
                            note=random.choice([None, "Бронь гостя", "Личное использование", "Уборка"]),
                            created_by_user_id=realtor.user_id,
                        )
                    )
                    cursor = end
            props.append(prop)
            if (i + 1) % 25 == 0:
                await db.commit()
                print(f"   properties {i + 1}/{properties_count}")
        await db.commit()

        active_props = [p for p in props if p.status == PropertyStatus.ACTIVE.value]
        print(f"→ favorites / inquiries / deals / reviews (active props: {len(active_props)})")

        # Favorites
        for client in clients:
            for prop in random.sample(active_props, k=min(len(active_props), random.randint(1, 6))):
                db.add(Favorite(user_id=client.id, property_id=prop.id))
        await db.commit()

        deals_confirmed: list[RentalDeal] = []
        pending_deals = 0
        for i in range(min(70, len(active_props) * 2)):
            prop = random.choice(active_props)
            client = random.choice(clients)
            realtor_id = prop_realtor.get(prop.id, active_realtors[0].id)

            created = _utc(days_ago=random.uniform(0, days), hour=random.randint(8, 22))
            inquiry = Inquiry(
                user_id=client.id,
                realtor_id=realtor_id,
                property_id=prop.id,
                channel=random.choice(
                    [ContactChannel.TELEGRAM.value, ContactChannel.WHATSAPP.value, ContactChannel.PHONE.value]
                ),
                status=InquiryStatus.NEW.value,
                note="Демо-обращение из seed_rich",
                last_event_at=created,
            )
            inquiry.created_at = created
            db.add(inquiry)
            await db.flush()

            roll = random.random()
            if roll < 0.25:
                inquiry.status = InquiryStatus.NEW.value
                continue

            start = date.today() + timedelta(days=random.randint(-20, 40))
            end = start + timedelta(days=random.randint(3, 21))
            if prop.rent_type == RentType.LONG_TERM.value:
                end = start + timedelta(days=random.randint(90, 365))

            if roll < 0.45:
                status = DealStatus.PENDING.value
                pending_deals += 1
            elif roll < 0.8:
                status = DealStatus.CONFIRMED.value
            elif roll < 0.9:
                status = DealStatus.REJECTED.value
            else:
                status = DealStatus.NEEDS_CLARIFICATION.value

            deal = RentalDeal(
                inquiry_id=inquiry.id,
                property_id=prop.id,
                realtor_id=realtor_id,
                client_user_id=client.id,
                start_date=start,
                end_date=end,
                status=status,
                admin_comment="Демо-сделка" if status != DealStatus.PENDING.value else None,
                confirmed_at=created + timedelta(days=1) if status == DealStatus.CONFIRMED.value else None,
            )
            deal.created_at = created + timedelta(hours=2)
            db.add(deal)
            await db.flush()

            for side in (ConfirmationSide.REALTOR.value, ConfirmationSide.CLIENT.value, ConfirmationSide.ADMIN.value):
                decision = ConfirmationDecision.PENDING.value
                if status == DealStatus.CONFIRMED.value:
                    decision = ConfirmationDecision.APPROVED.value
                elif status == DealStatus.REJECTED.value and side == ConfirmationSide.ADMIN.value:
                    decision = ConfirmationDecision.REJECTED.value
                elif status == DealStatus.NEEDS_CLARIFICATION.value and side == ConfirmationSide.ADMIN.value:
                    decision = ConfirmationDecision.PENDING.value
                db.add(
                    DealConfirmation(
                        deal_id=deal.id,
                        side=side,
                        decision=decision,
                        actor_user_id=client.id if side == ConfirmationSide.CLIENT.value else None,
                        decided_at=created + timedelta(days=1) if decision != ConfirmationDecision.PENDING.value else None,
                    )
                )

            if status == DealStatus.CONFIRMED.value:
                deals_confirmed.append(deal)
                inquiry.status = InquiryStatus.CONFIRMED.value
            elif status == DealStatus.REJECTED.value:
                inquiry.status = InquiryStatus.REJECTED.value
            elif status == DealStatus.PENDING.value:
                inquiry.status = InquiryStatus.AWAITING_CONFIRMATIONS.value
            else:
                inquiry.status = InquiryStatus.IN_PROGRESS.value

        await db.commit()

        # Reviews for most confirmed deals
        published = pending_rev = rejected = 0
        for deal in deals_confirmed:
            if random.random() < 0.12:
                continue
            status = random.choices(
                [
                    ReviewStatus.PUBLISHED.value,
                    ReviewStatus.PENDING_MODERATION.value,
                    ReviewStatus.REJECTED.value,
                    ReviewStatus.HIDDEN.value,
                ],
                weights=[60, 25, 10, 5],
                k=1,
            )[0]
            review = Review(
                deal_id=deal.id,
                author_user_id=deal.client_user_id,
                realtor_id=deal.realtor_id,
                property_id=deal.property_id,
                rating=random.choices([5, 4, 3, 2], weights=[55, 30, 12, 3], k=1)[0],
                text=random.choice(REVIEW_TEXTS),
                status=status,
                moderation_comment="Недостаточно конкретики" if status == ReviewStatus.REJECTED.value else None,
            )
            review.created_at = (deal.confirmed_at or deal.created_at) + timedelta(days=random.randint(1, 7))
            db.add(review)
            if status == ReviewStatus.PUBLISHED.value:
                published += 1
            elif status == ReviewStatus.PENDING_MODERATION.value:
                pending_rev += 1
            elif status == ReviewStatus.REJECTED.value:
                rejected += 1
        await db.commit()

        for r in active_realtors:
            await recalculate_realtor_rating(db, r.id)

        print(f"→ analytics events (~{days} days)")
        events: list[AnalyticsEvent] = []
        for day_offset in range(days, -1, -1):
            # weekend boost
            d = datetime.now(timezone.utc).date() - timedelta(days=day_offset)
            weekend = d.weekday() >= 5
            views_n = random.randint(40, 90) if weekend else random.randint(18, 55)
            for _ in range(views_n):
                prop = random.choice(active_props or props)
                client = random.choice(clients)
                events.append(
                    AnalyticsEvent(
                        event_type="property_view",
                        occurred_at=_utc(days_ago=day_offset, hour=random.randint(7, 23)),
                        user_id=client.id,
                        property_id=prop.id,
                        realtor_id=prop_realtor.get(prop.id),
                        session_id=f"sess-{random.randint(1000, 9999)}",
                        referrer=random.choice([None, "map", "list", "favorites", "telegram"]),
                    )
                )
            for event_type in (
                "contact_click_telegram",
                "contact_click_whatsapp",
                "contact_click_phone",
            ):
                for _ in range(random.randint(2, 10 if weekend else 6)):
                    prop = random.choice(active_props or props)
                    client = random.choice(clients)
                    events.append(
                        AnalyticsEvent(
                            event_type=event_type,
                            occurred_at=_utc(days_ago=day_offset, hour=random.randint(9, 22)),
                            user_id=client.id,
                            property_id=prop.id,
                            realtor_id=prop_realtor.get(prop.id),
                            session_id=f"sess-{random.randint(1000, 9999)}",
                        )
                    )
            if len(events) >= 800:
                db.add_all(events)
                await db.commit()
                events.clear()
        if events:
            db.add_all(events)
            await db.commit()

        # Ensure realtor links loaded for summary
        counts = (
            await db.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*) FROM properties) AS properties,
                      (SELECT count(*) FROM realtor_profiles) AS realtors,
                      (SELECT count(*) FROM rental_deals) AS deals,
                      (SELECT count(*) FROM reviews) AS reviews,
                      (SELECT count(*) FROM analytics_events) AS events,
                      (SELECT count(*) FROM favorites) AS favorites
                    """
                )
            )
        ).mappings().one()

        print("\n✅ seed_rich complete")
        print(f"   properties: {counts['properties']}")
        print(f"   realtors:   {counts['realtors']}")
        print(f"   deals:      {counts['deals']} (pending created this run ≈ {pending_deals})")
        print(f"   reviews:    {counts['reviews']} (published≈{published}, pending≈{pending_rev}, rejected≈{rejected})")
        print(f"   analytics:  {counts['events']}")
        print(f"   favorites:  {counts['favorites']}")
        print("   realtor logins: realtor1@batumi.demo … realtor7@batumi.demo / password1")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed rich Batumi demo data")
    parser.add_argument("--properties", type=int, default=110)
    parser.add_argument("--days", type=int, default=45)
    parser.add_argument("--wipe-demo", action="store_true", help="Remove previous seed_rich users/data first")
    args = parser.parse_args()
    asyncio.run(seed(args.properties, args.days, args.wipe_demo))


if __name__ == "__main__":
    main()
