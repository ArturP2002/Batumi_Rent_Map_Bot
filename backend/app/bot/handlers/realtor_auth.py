from __future__ import annotations

import html
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    cancel_kb,
    open_map_kb,
    realtor_auth_kb,
    role_choice_kb,
    user_menu,
)
from app.bot.states import RealtorAuthFSM
from app.core.security import is_valid_email, validate_password_strength
from app.db.enums import UserRole
from app.db.models import User
from app.services.users import (
    RealtorAuthError,
    login_realtor_account,
    register_realtor_account,
)

router = Router()
logger = logging.getLogger(__name__)


async def _show_main_menu(message: Message, user: User) -> None:
    is_realtor = user.has_role(UserRole.REALTOR)
    is_admin = user.has_role(UserRole.ADMIN)
    await message.answer(
        "Меню обновлено.",
        reply_markup=user_menu(is_realtor=is_realtor, is_admin=is_admin),
    )
    if not is_realtor:
        await message.answer("Откройте карту квартир:", reply_markup=open_map_kb())


@router.message(F.text == "❌ Отмена")
async def cancel_auth(message: Message, state: FSMContext, db_user: User):
    await state.clear()
    await message.answer("Отменено.")
    await _show_main_menu(message, db_user)


@router.message(F.text == "🏢 Кабинет риелтора")
@router.message(F.text == "🏢 Я риелтор")
async def realtor_entry(message: Message, state: FSMContext, db_user: User):
    if db_user.has_role(UserRole.REALTOR) and db_user.realtor_profile and db_user.realtor_profile.has_credentials:
        await state.clear()
        name = html.escape(db_user.realtor_profile.display_name)
        await message.answer(f"Вы уже в кабинете риелтора <b>{name}</b>.")
        await _show_main_menu(message, db_user)
        return

    await state.set_state(RealtorAuthFSM.choose_action)
    if db_user.has_role(UserRole.REALTOR) and not (
        db_user.realtor_profile and db_user.realtor_profile.has_credentials
    ):
        await message.answer(
            "Профиль риелтора есть, но email/пароль ещё не заданы.\n"
            "Зарегистрируйте кабинет — так сможете войти с другого Telegram.",
            reply_markup=realtor_auth_kb(),
        )
    else:
        await message.answer(
            "Кабинет риелтора защищён email и паролем.\n"
            "После регистрации можно войти с нового Telegram-аккаунта — "
            "объявления и сделки останутся на месте.",
            reply_markup=realtor_auth_kb(),
        )


@router.message(F.text == "🔍 Ищу жильё")
async def choose_tenant(message: Message, state: FSMContext, db_user: User):
    await state.clear()
    await message.answer(
        "Отлично! Ищите квартиры на карте и сохраняйте избранное."
    )
    await _show_main_menu(message, db_user)


@router.message(F.text == "⬅️ Назад")
async def auth_back(message: Message, state: FSMContext, db_user: User):
    await state.clear()
    if db_user.has_role(UserRole.REALTOR):
        await _show_main_menu(message, db_user)
    else:
        await message.answer("Выберите роль:", reply_markup=role_choice_kb())


@router.message(RealtorAuthFSM.choose_action, F.text == "📝 Регистрация кабинета")
async def register_start(message: Message, state: FSMContext, db_user: User):
    if db_user.realtor_profile and db_user.realtor_profile.has_credentials:
        await state.clear()
        await message.answer("Кабинет уже создан.")
        await _show_main_menu(message, db_user)
        return
    await state.set_state(RealtorAuthFSM.register_email)
    await message.answer(
        "Введите email для кабинета риелтора:\n"
        "<i>На него не уходит почта — это логин для входа с любого Telegram.</i>",
        reply_markup=cancel_kb(),
    )


@router.message(RealtorAuthFSM.choose_action, F.text == "🔑 Войти в кабинет")
async def login_start(message: Message, state: FSMContext):
    await state.set_state(RealtorAuthFSM.login_email)
    await message.answer(
        "Введите email кабинета:",
        reply_markup=cancel_kb(),
    )


@router.message(RealtorAuthFSM.register_email)
async def register_email(message: Message, state: FSMContext):
    email = (message.text or "").strip()
    if not is_valid_email(email):
        await message.answer("Некорректный email. Пример: name@example.com")
        return
    await state.update_data(email=email)
    await state.set_state(RealtorAuthFSM.register_password)
    await message.answer(
        "Придумайте пароль (минимум 8 символов, без пробелов):",
        reply_markup=cancel_kb(),
    )


@router.message(RealtorAuthFSM.register_password)
async def register_password(message: Message, state: FSMContext):
    password = message.text or ""
    try:
        await message.delete()
    except Exception:
        pass
    pwd_err = validate_password_strength(password)
    if pwd_err:
        await message.answer(pwd_err + "\nВведите пароль ещё раз:")
        return
    await state.update_data(password=password)
    await state.set_state(RealtorAuthFSM.register_password_confirm)
    await message.answer("Повторите пароль:", reply_markup=cancel_kb())


@router.message(RealtorAuthFSM.register_password_confirm)
async def register_password_confirm(message: Message, state: FSMContext):
    confirm = message.text or ""
    try:
        await message.delete()
    except Exception:
        pass
    data = await state.get_data()
    if confirm != data.get("password"):
        await message.answer("Пароли не совпадают. Введите пароль ещё раз:")
        await state.set_state(RealtorAuthFSM.register_password)
        return
    await state.set_state(RealtorAuthFSM.register_name)
    await message.answer(
        "Как вас представлять клиентам? (имя или название агентства)",
        reply_markup=cancel_kb(),
    )


@router.message(RealtorAuthFSM.register_name)
async def register_name(
    message: Message, state: FSMContext, db_user: User, db: AsyncSession
):
    data = await state.get_data()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        await state.clear()
        await message.answer(
            "Сессия регистрации устарела. Начните заново: «🏢 Кабинет риелтора».",
            reply_markup=realtor_auth_kb(),
        )
        await state.set_state(RealtorAuthFSM.choose_action)
        return

    try:
        user = await register_realtor_account(
            db,
            current_user=db_user,
            email=email,
            password=password,
            display_name=message.text or "",
        )
    except RealtorAuthError as exc:
        logger.info("Realtor register rejected: %s", exc.message)
        # If cabinet already exists, leave FSM and show menu.
        if "уже есть кабинет" in exc.message.lower() or "уже создан" in exc.message.lower():
            await state.clear()
            await message.answer(exc.message)
            await _show_main_menu(message, db_user)
            return
        await message.answer(exc.message)
        return
    except Exception:
        logger.exception("Realtor register failed")
        await state.clear()
        await message.answer(
            "Не удалось зарегистрировать кабинет. Нажмите /start и попробуйте снова."
        )
        await _show_main_menu(message, db_user)
        return

    await state.clear()
    profile = user.realtor_profile
    name = html.escape(profile.display_name if profile else "")
    login = html.escape(profile.email or "") if profile else ""
    await message.answer(
        f"Кабинет <b>{name}</b> создан.\n"
        f"Логин: <code>{login}</code>\n\n"
        "Сохраните пароль. Если Telegram заблокируют — войдите с нового аккаунта "
        "по email и паролю, кабинет подтянется автоматически."
    )
    await _show_main_menu(message, user)


@router.message(RealtorAuthFSM.login_email)
async def login_email(message: Message, state: FSMContext):
    await state.update_data(email=(message.text or "").strip())
    await state.set_state(RealtorAuthFSM.login_password)
    await message.answer("Введите пароль:", reply_markup=cancel_kb())


@router.message(RealtorAuthFSM.login_password)
async def login_password(
    message: Message, state: FSMContext, db_user: User, db: AsyncSession
):
    password = message.text or ""
    try:
        await message.delete()
    except Exception:
        pass
    data = await state.get_data()
    email = data.get("email")
    if not email:
        await state.clear()
        await message.answer("Сессия входа устарела. Начните заново.")
        await _show_main_menu(message, db_user)
        return

    previous_user_id = db_user.id
    try:
        user = await login_realtor_account(
            db,
            current_user=db_user,
            email=email,
            password=password,
        )
    except RealtorAuthError as exc:
        await message.answer(exc.message)
        return
    except Exception:
        logger.exception("Realtor login failed")
        await state.clear()
        await message.answer("Не удалось войти. Нажмите /start и попробуйте снова.")
        await _show_main_menu(message, db_user)
        return

    await state.clear()
    name = html.escape(user.realtor_profile.display_name if user.realtor_profile else "")
    note = ""
    if previous_user_id != user.id:
        note = "\nЭтот Telegram привязан к вашему кабинету."
    await message.answer(f"Вход выполнен: <b>{name}</b>.{note}")
    await _show_main_menu(message, user)
