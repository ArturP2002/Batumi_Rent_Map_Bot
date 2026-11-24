from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from app.core.config import get_settings


def webapp_button(text: str, startapp: str = "") -> InlineKeyboardButton:
    url = get_settings().webapp_url
    if startapp:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}startapp={startapp}"
    return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))


def role_choice_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Ищу жильё")],
            [KeyboardButton(text="🏢 Я риелтор")],
        ],
        resize_keyboard=True,
    )


def realtor_auth_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Регистрация кабинета")],
            [KeyboardButton(text="🔑 Войти в кабинет")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def user_menu(*, is_realtor: bool, is_admin: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🏠 Актуальные предложения")],
        [KeyboardButton(text="❤️ Избранное"), KeyboardButton(text="❓ Помощь")],
    ]
    if is_realtor:
        rows.append([KeyboardButton(text="📋 Мои квартиры"), KeyboardButton(text="➕ Добавить квартиру")])
        rows.append(
            [KeyboardButton(text="📨 Обращения"), KeyboardButton(text="✅ Подтвердить аренду")]
        )
        rows.append([KeyboardButton(text="📅 Календарь"), KeyboardButton(text="👤 Мой профиль")])
    else:
        rows.append([KeyboardButton(text="🏢 Кабинет риелтора")])
    if is_admin:
        rows.append([KeyboardButton(text="🛠 Открыть админ-панель")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def open_map_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[webapp_button("🗺 Открыть карту квартир", "")]]
    )


def open_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[webapp_button("Открыть админ-панель", "admin")]]
    )


def deal_client_kb(deal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"deal_yes:{deal_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"deal_no:{deal_id}"),
            ]
        ]
    )


def freshness_kb(property_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Актуально", callback_data=f"fresh:{property_id}")]
        ]
    )
