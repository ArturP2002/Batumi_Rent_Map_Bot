"""Telegram WebApp initData validation, session tokens, password hashing."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

from fastapi import HTTPException, status

from app.core.config import get_settings

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LEN = 8


@dataclass
class TelegramUser:
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    photo_url: str | None = None


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(normalize_email(email))) and len(email) <= 255


def validate_password_strength(password: str) -> str | None:
    if len(password) < _MIN_PASSWORD_LEN:
        return f"Пароль должен быть не короче {_MIN_PASSWORD_LEN} символов."
    if password.strip() != password or " " in password:
        return "Пароль не должен содержать пробелы."
    return None


def _scrypt_digest(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = _scrypt_digest(password, salt)
    return (
        "scrypt$"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(digest).decode('ascii')}"
    )


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algo, salt_b64, digest_b64 = password_hash.split("$", 2)
        if algo != "scrypt":
            return False
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(digest_b64.encode("ascii"))
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            dklen=len(expected),
        )
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def validate_init_data(init_data: str) -> dict[str, Any]:
    settings = get_settings()
    if not init_data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing initData")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing hash")

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    calculated = hmac.new(
        _secret_key(settings.bot_token),
        data_check.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid initData signature")

    auth_date = int(parsed.get("auth_date", "0"))
    if time.time() - auth_date > settings.init_data_max_age_seconds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "initData expired")

    user_raw = parsed.get("user")
    if not user_raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing user in initData")
    user = json.loads(user_raw)
    parsed["_user"] = TelegramUser(
        id=int(user["id"]),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        username=user.get("username"),
        language_code=user.get("language_code"),
        photo_url=user.get("photo_url"),
    )
    parsed["_start_param"] = parsed.get("start_param")
    return parsed


def make_session_token(telegram_id: int) -> str:
    settings = get_settings()
    expires = int(time.time()) + settings.session_ttl_seconds
    payload = f"{telegram_id}:{expires}"
    sig = hmac.new(
        settings.session_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{sig}"


def parse_session_token(token: str) -> int:
    settings = get_settings()
    try:
        telegram_id_s, expires_s, sig = token.split(":")
        telegram_id = int(telegram_id_s)
        expires = int(expires_s)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session") from exc

    payload = f"{telegram_id}:{expires}"
    expected = hmac.new(
        settings.session_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session signature")
    if time.time() > expires:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    return telegram_id
