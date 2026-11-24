from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import AddPropertyFSM, CalendarFSM
from app.bot.texts import (
    amenities_help_text,
    parse_amenities,
    parse_rent_type,
    parse_rooms,
    rent_type_label,
    rooms_label,
    status_label,
)
from app.db.enums import PropertyStatus, UserRole
from app.db.models import Property, PropertyRealtor, User
from app.schemas.property import FeaturesIn, IntervalIn, PropertyCreateIn
from app.services import calendar as calendar_svc
from app.services import geo as geo_svc
from app.services import properties as properties_svc

router = Router()


def _require_realtor(user: User) -> bool:
    return bool(
        user.realtor_profile
        and user.has_role(UserRole.REALTOR)
        and not user.realtor_profile.is_blocked
    )


@router.message(F.text == "📋 Мои квартиры")
async def my_flats(message: Message, db_user: User, db: AsyncSession):
    if not _require_realtor(db_user):
        await message.answer("Доступно только риелторам.")
        return
    rows = (
        await db.execute(
            select(Property)
            .join(PropertyRealtor)
            .where(PropertyRealtor.realtor_id == db_user.realtor_profile.id)
            .order_by(Property.updated_at.desc())
            .limit(30)
        )
    ).scalars().all()
    if not rows:
        await message.answer("Пока нет объявлений. Нажмите «Добавить квартиру».")
        return
    lines = []
    for p in rows:
        lines.append(
            f"#{p.id} {p.public_code} — ${p.price_usd} — "
            f"{status_label(p.status)} — {rooms_label(p.rooms)}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == "➕ Добавить квартиру")
async def add_start(message: Message, db_user: User, state: FSMContext):
    if not _require_realtor(db_user):
        await message.answer("Доступно только риелторам, добавленным администратором.")
        return
    await state.set_state(AddPropertyFSM.rent_type)
    await state.update_data(draft={})
    await message.answer(
        "Тип аренды — отправьте число или слово:\n"
        "1 — долгосрочно\n"
        "2 — посуточно"
    )


@router.message(AddPropertyFSM.rent_type)
async def step_rent(message: Message, state: FSMContext):
    val = parse_rent_type(message.text or "")
    if not val:
        await message.answer("Укажите «1» (долгосрочно) или «2» (посуточно).")
        return
    data = await state.get_data()
    draft = data.get("draft", {})
    draft["rent_type"] = val
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.rooms)
    await message.answer(
        "Количество комнат:\n"
        "студия / 1 / 2 / 3 / 4+"
    )


@router.message(AddPropertyFSM.rooms)
async def step_rooms(message: Message, state: FSMContext):
    val = parse_rooms(message.text or "")
    if not val:
        await message.answer("Допустимо: студия, 1, 2, 3, 4+")
        return
    data = await state.get_data()
    draft = data["draft"]
    draft["rooms"] = val
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.area)
    await message.answer("Площадь в м² (число), например: 45.5")


@router.message(AddPropertyFSM.area)
async def step_area(message: Message, state: FSMContext):
    try:
        area = Decimal((message.text or "").replace(",", "."))
    except InvalidOperation:
        await message.answer("Введите число, например 45.5")
        return
    data = await state.get_data()
    draft = data["draft"]
    draft["area_m2"] = str(area)
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.floor)
    await message.answer("Этаж и этажность через пробел, например: 5 12")


@router.message(AddPropertyFSM.floor)
async def step_floor(message: Message, state: FSMContext):
    parts = (message.text or "").split()
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        await message.answer("Формат: 5 12")
        return
    data = await state.get_data()
    draft = data["draft"]
    draft["floor"] = int(parts[0])
    draft["floors_total"] = int(parts[1])
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.price)
    await message.answer("Цена в USD (число):")


@router.message(AddPropertyFSM.price)
async def step_price(message: Message, state: FSMContext):
    try:
        price = Decimal((message.text or "").replace(",", "."))
    except InvalidOperation:
        await message.answer("Введите число")
        return
    data = await state.get_data()
    draft = data["draft"]
    draft["price_usd"] = str(price)
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.district)
    await message.answer("Район:")


@router.message(AddPropertyFSM.district)
async def step_district(message: Message, state: FSMContext):
    data = await state.get_data()
    draft = data["draft"]
    draft["district"] = message.text
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.address)
    await message.answer("Адрес текстом (или позже пришлите геопозицию):")


@router.message(AddPropertyFSM.address)
async def step_address(message: Message, state: FSMContext):
    data = await state.get_data()
    draft = data["draft"]
    draft["address"] = message.text
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.location)
    await message.answer(
        "Пришлите геопозицию Telegram или напишите «геокод» для поиска по адресу."
    )


@router.message(AddPropertyFSM.location, F.location)
async def step_location_pin(message: Message, state: FSMContext):
    data = await state.get_data()
    draft = data["draft"]
    draft["lat"] = message.location.latitude
    draft["lon"] = message.location.longitude
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.amenities)
    await message.answer(amenities_help_text())


@router.message(AddPropertyFSM.location)
async def step_location_text(message: Message, state: FSMContext):
    data = await state.get_data()
    draft = data["draft"]
    if (message.text or "").lower().startswith("геокод"):
        try:
            lat, lon = await geo_svc.geocode_address(draft.get("address") or "")
        except Exception:
            await message.answer("Не удалось найти адрес. Пришлите геопозицию.")
            return
        draft["lat"], draft["lon"] = lat, lon
    else:
        await message.answer("Нужна геопозиция или команда «геокод».")
        return
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.amenities)
    await message.answer(amenities_help_text())


@router.message(AddPropertyFSM.amenities)
async def step_amenities(message: Message, state: FSMContext):
    feats = parse_amenities(message.text or "")
    data = await state.get_data()
    draft = data["draft"]
    draft["features"] = feats
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.sleeping)
    await message.answer("Спальные места (целое число):")


@router.message(AddPropertyFSM.sleeping)
async def step_sleeping(message: Message, state: FSMContext):
    if not (message.text or "").isdigit():
        await message.answer("Введите целое число")
        return
    data = await state.get_data()
    draft = data["draft"]
    draft["sleeping_places"] = int(message.text)
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.description)
    await message.answer("Описание квартиры:")


@router.message(AddPropertyFSM.description)
async def step_description(message: Message, state: FSMContext):
    data = await state.get_data()
    draft = data["draft"]
    draft["description"] = message.text
    await state.update_data(draft=draft)
    await state.set_state(AddPropertyFSM.preview)
    await message.answer(
        "Предпросмотр:\n"
        f"Тип: {rent_type_label(draft.get('rent_type', ''))}\n"
        f"Комнаты: {rooms_label(draft.get('rooms', ''))}\n"
        f"Цена: ${draft.get('price_usd')}\n"
        f"{draft.get('district')}, {draft.get('address')}\n"
        f"{draft.get('description')}\n\n"
        "Отправьте «ок» для отправки на модерацию или «отмена»."
    )


@router.message(AddPropertyFSM.preview)
async def step_preview(message: Message, state: FSMContext, db_user: User, db: AsyncSession):
    text = (message.text or "").lower().strip()
    if text in {"отмена", "cancel"}:
        await state.clear()
        await message.answer("Создание объявления отменено.")
        return
    if text not in {"ок", "ok", "да"}:
        await message.answer("Отправьте «ок» или «отмена».")
        return
    data = await state.get_data()
    draft = data["draft"]
    create = PropertyCreateIn(
        rent_type=draft["rent_type"],
        rooms=draft["rooms"],
        area_m2=Decimal(draft["area_m2"]),
        floor=draft.get("floor"),
        floors_total=draft.get("floors_total"),
        sleeping_places=draft.get("sleeping_places"),
        price_usd=Decimal(draft["price_usd"]),
        district=draft.get("district"),
        address=draft.get("address"),
        description=draft.get("description"),
        lat=draft.get("lat"),
        lon=draft.get("lon"),
        features=FeaturesIn(**draft.get("features", {})),
        realtor_ids=[db_user.realtor_profile.id],
        primary_realtor_id=db_user.realtor_profile.id,
    )
    prop = await properties_svc.create_property(
        db, create, created_by_user_id=db_user.id, status=PropertyStatus.MODERATION.value
    )
    await state.clear()
    await message.answer(
        f"Объявление {prop.public_code} отправлено на модерацию.\n"
        "Фото можно добавить позже через редактирование (до 10 шт)."
    )


@router.message(F.text == "📅 Календарь")
async def calendar_start(message: Message, db_user: User, state: FSMContext, db: AsyncSession):
    if not _require_realtor(db_user):
        await message.answer("Только для риелторов.")
        return
    rows = (
        await db.execute(
            select(Property)
            .join(PropertyRealtor)
            .where(
                PropertyRealtor.realtor_id == db_user.realtor_profile.id,
                Property.rent_type == "daily",
            )
            .limit(20)
        )
    ).scalars().all()
    if not rows:
        await message.answer("Нет посуточных объектов.")
        return
    await state.set_state(CalendarFSM.choose_property)
    await message.answer(
        "Выберите ID квартиры:\n" + "\n".join(f"{p.id}: {p.public_code}" for p in rows)
    )


@router.message(CalendarFSM.choose_property)
async def calendar_prop(message: Message, state: FSMContext):
    if not (message.text or "").isdigit():
        await message.answer("Пришлите числовой ID")
        return
    await state.update_data(property_id=int(message.text))
    await state.set_state(CalendarFSM.start)
    await message.answer("Дата начала занятости в формате ГГГГ-ММ-ДД:")


@router.message(CalendarFSM.start)
async def calendar_start_date(message: Message, state: FSMContext):
    try:
        start = date.fromisoformat(message.text or "")
    except ValueError:
        await message.answer("Формат даты: ГГГГ-ММ-ДД, например 2026-05-01")
        return
    await state.update_data(start=start.isoformat())
    await state.set_state(CalendarFSM.end)
    await message.answer(
        "Дата окончания (не включая этот день) в формате ГГГГ-ММ-ДД:"
    )


@router.message(CalendarFSM.end)
async def calendar_end_date(message: Message, state: FSMContext, db_user: User, db: AsyncSession):
    try:
        end = date.fromisoformat(message.text or "")
    except ValueError:
        await message.answer("Формат даты: ГГГГ-ММ-ДД, например 2026-05-10")
        return
    data = await state.get_data()
    start = date.fromisoformat(data["start"])
    try:
        interval = await calendar_svc.add_interval(
            db,
            data["property_id"],
            IntervalIn(start_date=start, end_date=end, kind="booked"),
            created_by_user_id=db_user.id,
        )
        await message.answer(
            f"Период занятости #{interval.id} сохранён: {start} → {end}"
        )
    except Exception as exc:
        await message.answer(f"Не удалось сохранить период: {exc}")
    await state.clear()


@router.callback_query(F.data.startswith("fresh:"))
async def freshness_confirm(callback: CallbackQuery, db_user: User, db: AsyncSession):
    property_id = int(callback.data.split(":")[1])
    prop = await properties_svc.get_property(db, property_id)
    if not prop:
        await callback.answer("Объявление не найдено", show_alert=True)
        return
    prop.last_confirmed_at = datetime.now(timezone.utc)
    prop.freshness_reminded_at = None
    if prop.status == PropertyStatus.HIDDEN.value:
        prop.status = PropertyStatus.ACTIVE.value
    await db.commit()
    await callback.message.answer(f"Актуальность {prop.public_code} подтверждена.")
    await callback.answer("Готово")
