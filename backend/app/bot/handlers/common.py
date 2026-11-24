from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import open_admin_kb, open_map_kb, role_choice_kb, user_menu
from app.db.enums import UserRole
from app.db.models import User

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User, state: FSMContext):
    await state.clear()
    is_realtor = db_user.has_role(UserRole.REALTOR)
    is_admin = db_user.has_role(UserRole.ADMIN)
    has_cabinet = bool(
        is_realtor and db_user.realtor_profile and db_user.realtor_profile.has_credentials
    )

    text = (
        "Добро пожаловать в <b>Batumi Rent Map</b>!\n\n"
        "Ищите квартиры на интерактивной карте Батуми, "
        "фильтруйте по цене и удобствам, сохраняйте избранное "
        "и связывайтесь с риелторами.\n\n"
        "Риелторам: кабинет защищён email и паролем — его можно открыть "
        "с нового Telegram, если старый аккаунт недоступен."
    )
    await message.answer(text)

    if has_cabinet:
        await message.answer(
            f"Кабинет риелтора: <b>{db_user.realtor_profile.display_name}</b>",
            reply_markup=user_menu(is_realtor=True, is_admin=is_admin),
        )
        await message.answer("Откройте карту квартир:", reply_markup=open_map_kb())
        return

    if is_realtor and not has_cabinet:
        await message.answer(
            "Профиль риелтора найден, но email/пароль ещё не заданы.\n"
            "Выберите «🏢 Я риелтор» → регистрация кабинета.",
            reply_markup=role_choice_kb(),
        )
        return

    await message.answer("Кто вы?", reply_markup=role_choice_kb())


@router.message(F.text == "🏠 Актуальные предложения")
async def actual(message: Message):
    await message.answer("Актуальные предложения в Mini App:", reply_markup=open_map_kb())


@router.message(F.text == "❤️ Избранное")
async def favorites(message: Message):
    from app.bot.keyboards import webapp_button
    from aiogram.types import InlineKeyboardMarkup

    kb = InlineKeyboardMarkup(inline_keyboard=[[webapp_button("Открыть избранное", "favorites")]])
    await message.answer("Ваше избранное:", reply_markup=kb)


@router.message(F.text == "❓ Помощь")
async def help_msg(message: Message):
    await message.answer(
        "Batumi Rent Map — поиск аренды в Батуми.\n"
        "• Карта и фильтры — в Mini App\n"
        "• Контакты риелтора — из карточки квартиры\n"
        "• Отзыв можно оставить только после подтверждённой сделки\n\n"
        "Риелторам: зарегистрируйте кабинет (email + пароль). "
        "При смене Telegram войдите тем же логином — объекты и сделки сохранятся."
    )


@router.message(F.text == "🛠 Открыть админ-панель")
async def admin_panel(message: Message, db_user: User):
    if not db_user.has_role(UserRole.ADMIN):
        await message.answer("Недостаточно прав.")
        return
    await message.answer("Админ-панель:", reply_markup=open_admin_kb())


@router.message(F.text == "👤 Мой профиль")
async def my_profile(message: Message, db_user: User):
    if not db_user.realtor_profile:
        await message.answer(
            "Профиль риелтора не найден. Нажмите «🏢 Кабинет риелтора» для регистрации."
        )
        return
    p = db_user.realtor_profile
    await message.answer(
        f"<b>{p.display_name}</b>\n"
        f"Email: <code>{p.email or 'не задан'}</code>\n"
        f"Рейтинг: {p.rating_avg} ({p.rating_count} отзывов)\n"
        f"Телефон: {p.phone or '—'}\n"
        f"WhatsApp: {p.whatsapp or '—'}\n"
        f"Telegram: {p.telegram_contact or '—'}\n"
        f"{p.bio or 'Описание пока не заполнено.'}"
    )
