"""Русские подписи и нормализация ввода для Telegram-бота."""

from __future__ import annotations

from app.db.enums import AMENITY_KEYS, AMENITY_LABELS_RU, PropertyStatus, RentType

STATUS_RU = {
    PropertyStatus.DRAFT.value: "черновик",
    PropertyStatus.MODERATION.value: "на модерации",
    PropertyStatus.ACTIVE.value: "активно",
    PropertyStatus.NEEDS_FIX.value: "нужны правки",
    PropertyStatus.HIDDEN.value: "скрыто",
    PropertyStatus.BLOCKED.value: "заблокировано",
    PropertyStatus.ARCHIVED.value: "в архиве",
}

RENT_TYPE_RU = {
    RentType.LONG_TERM.value: "долгосрочно",
    RentType.DAILY.value: "посуточно",
}

ROOMS_RU = {
    "studio": "студия",
    "1": "1",
    "2": "2",
    "3": "3",
    "4+": "4+",
}

INQUIRY_STATUS_RU = {
    "new": "новое",
    "in_progress": "в работе",
    "failed": "не состоялась",
    "awaiting_confirmations": "ожидает подтверждений",
    "confirmed": "подтверждена",
    "rejected": "отклонена",
}

CHANNEL_RU = {
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "phone": "телефон",
}

DECISION_RU = {
    "approved": "подтверждено",
    "rejected": "отклонено",
    "pending": "ожидает",
}

# Ввод удобств: и ключ, и русская подпись
AMENITY_INPUT_MAP: dict[str, str] = {}
for key in AMENITY_KEYS:
    AMENITY_INPUT_MAP[key.lower()] = key
    AMENITY_INPUT_MAP[AMENITY_LABELS_RU[key].lower()] = key
    # без спецсимволов
    AMENITY_INPUT_MAP[AMENITY_LABELS_RU[key].lower().replace("‑", "-").replace("ё", "е")] = key


def rent_type_label(value: str) -> str:
    return RENT_TYPE_RU.get(value, value)


def rooms_label(value: str) -> str:
    return ROOMS_RU.get(value, value)


def status_label(value: str) -> str:
    return STATUS_RU.get(value, value)


def parse_rent_type(raw: str) -> str | None:
    val = raw.strip().lower()
    mapping = {
        "долгосрочно": RentType.LONG_TERM.value,
        "долгосрок": RentType.LONG_TERM.value,
        "long_term": RentType.LONG_TERM.value,
        "посуточно": RentType.DAILY.value,
        "сутки": RentType.DAILY.value,
        "daily": RentType.DAILY.value,
        "1": RentType.LONG_TERM.value,
        "2": RentType.DAILY.value,
    }
    return mapping.get(val)


def parse_rooms(raw: str) -> str | None:
    val = raw.strip().lower().replace("ё", "е")
    mapping = {
        "студия": "studio",
        "studio": "studio",
        "0": "studio",
        "1": "1",
        "2": "2",
        "3": "3",
        "4": "4+",
        "4+": "4+",
        "4 и более": "4+",
    }
    return mapping.get(val)


def amenities_help_text() -> str:
    lines = [f"• {AMENITY_LABELS_RU[k]}" for k in AMENITY_KEYS]
    return (
        "Укажите удобства через запятую (по-русски) или отправьте «-», чтобы пропустить.\n"
        "Например: Wi‑Fi, кондиционер, балкон\n\n"
        "Доступные варианты:\n" + "\n".join(lines)
    )


def parse_amenities(raw: str) -> dict[str, bool]:
    feats = {k: False for k in AMENITY_KEYS}
    text = raw.strip()
    if text in {"-", "нет", "пропустить"}:
        return feats
    for part in text.split(","):
        key = AMENITY_INPUT_MAP.get(part.strip().lower())
        if key:
            feats[key] = True
    return feats
