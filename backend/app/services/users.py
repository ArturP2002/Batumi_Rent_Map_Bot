from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import (
    TelegramUser,
    hash_password,
    is_valid_email,
    normalize_email,
    validate_password_strength,
    verify_password,
)
from app.db.enums import UserRole
from app.db.models import RealtorProfile, User, UserRoleAssignment


class RealtorAuthError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def _load_user_by_telegram(db: AsyncSession, telegram_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(selectinload(User.roles), selectinload(User.realtor_profile))
    )
    return result.scalar_one_or_none()


async def _load_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles), selectinload(User.realtor_profile))
    )
    return result.scalar_one_or_none()


async def _load_realtor_by_email(db: AsyncSession, email: str) -> RealtorProfile | None:
    result = await db.execute(
        select(RealtorProfile)
        .where(RealtorProfile.email == normalize_email(email))
        .options(selectinload(RealtorProfile.user).selectinload(User.roles))
    )
    return result.scalar_one_or_none()


async def ensure_user_from_telegram(db: AsyncSession, tg: TelegramUser) -> User:
    user = await _load_user_by_telegram(db, tg.id)
    if user is None:
        user = User(
            telegram_id=tg.id,
            username=tg.username,
            first_name=tg.first_name,
            last_name=tg.last_name,
            language_code=tg.language_code,
            photo_url=tg.photo_url,
        )
        db.add(user)
        try:
            await db.flush()
            db.add(UserRoleAssignment(user_id=user.id, role=UserRole.TENANT.value, is_active=True))
            settings = get_settings()
            if tg.id in settings.admin_ids:
                db.add(
                    UserRoleAssignment(user_id=user.id, role=UserRole.ADMIN.value, is_active=True)
                )
            await db.commit()
        except IntegrityError:
            # Concurrent /start (or API + bot) created the same telegram_id.
            await db.rollback()
        return await ensure_user_from_telegram(db, tg)

    user.username = tg.username or user.username
    user.first_name = tg.first_name or user.first_name
    user.last_name = tg.last_name or user.last_name
    user.photo_url = tg.photo_url or user.photo_url
    user.last_seen_at = datetime.now(timezone.utc)
    settings = get_settings()
    if tg.id in settings.admin_ids and not user.has_role(UserRole.ADMIN):
        db.add(UserRoleAssignment(user_id=user.id, role=UserRole.ADMIN.value, is_active=True))
    await db.commit()
    await db.refresh(user, attribute_names=["roles", "realtor_profile"])
    return user


async def add_role(db: AsyncSession, user: User, role: UserRole) -> None:
    if user.has_role(role):
        for r in user.roles:
            if r.role == role.value:
                r.is_active = True
                break
    else:
        db.add(UserRoleAssignment(user_id=user.id, role=role.value, is_active=True))
    await db.commit()


async def create_realtor(
    db: AsyncSession,
    *,
    telegram_id: int,
    display_name: str,
    bio: str | None = None,
    phone: str | None = None,
    whatsapp: str | None = None,
    telegram_contact: str | None = None,
    email: str | None = None,
    password: str | None = None,
) -> RealtorProfile:
    result = await db.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(selectinload(User.roles), selectinload(User.realtor_profile))
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, first_name=display_name)
        db.add(user)
        await db.flush()
        db.add(UserRoleAssignment(user_id=user.id, role=UserRole.TENANT.value))

    await add_role(db, user, UserRole.REALTOR)
    await db.refresh(user, attribute_names=["realtor_profile", "roles"])

    email_norm = normalize_email(email) if email else None
    # scrypt is CPU-heavy — keep the asyncio event loop responsive
    password_digest = (
        await asyncio.to_thread(hash_password, password) if password else None
    )

    if user.realtor_profile:
        profile = user.realtor_profile
        profile.display_name = display_name
        profile.bio = bio
        profile.phone = phone
        profile.whatsapp = whatsapp
        profile.telegram_contact = telegram_contact
        profile.is_blocked = False
        profile.can_publish = True
        if email_norm:
            profile.email = email_norm
        if password_digest:
            profile.password_hash = password_digest
    else:
        profile = RealtorProfile(
            user_id=user.id,
            display_name=display_name,
            email=email_norm,
            password_hash=password_digest,
            bio=bio,
            phone=phone,
            whatsapp=whatsapp,
            telegram_contact=telegram_contact,
        )
        db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def register_realtor_account(
    db: AsyncSession,
    *,
    current_user: User,
    email: str,
    password: str,
    display_name: str,
) -> User:
    if not is_valid_email(email):
        raise RealtorAuthError("Введите корректный email.")
    pwd_err = validate_password_strength(password or "")
    if pwd_err:
        raise RealtorAuthError(pwd_err)
    name = display_name.strip()
    if len(name) < 2:
        raise RealtorAuthError("Укажите имя / название агентства (минимум 2 символа).")

    email_norm = normalize_email(email)
    existing = await _load_realtor_by_email(db, email_norm)
    if existing and existing.user_id != current_user.id:
        raise RealtorAuthError("Этот email уже зарегистрирован. Войдите в кабинет.")

    # Already registered on this Telegram — do not silently overwrite password.
    if current_user.realtor_profile and current_user.realtor_profile.has_credentials:
        raise RealtorAuthError(
            "У вас уже есть кабинет. Нажмите «Отмена» или /start — откроется меню."
        )

    try:
        await create_realtor(
            db,
            telegram_id=current_user.telegram_id,
            display_name=name,
            email=email_norm,
            password=password,
            telegram_contact=f"@{current_user.username}" if current_user.username else None,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise RealtorAuthError(
            "Этот email уже занят или кабинет уже создан. Попробуйте войти."
        ) from exc

    user = await _load_user_by_telegram(db, current_user.telegram_id)
    if user is None or user.realtor_profile is None:
        raise RealtorAuthError("Не удалось создать кабинет. Попробуйте ещё раз.")
    return user


async def login_realtor_account(
    db: AsyncSession,
    *,
    current_user: User,
    email: str,
    password: str,
) -> User:
    if not is_valid_email(email):
        raise RealtorAuthError("Введите корректный email.")
    profile = await _load_realtor_by_email(db, email)
    ok = (
        bool(profile)
        and bool(profile.password_hash)
        and await asyncio.to_thread(verify_password, password, profile.password_hash)
    )
    if profile is None or not ok:
        raise RealtorAuthError("Неверный email или пароль.")
    if profile.is_blocked:
        raise RealtorAuthError("Кабинет заблокирован. Обратитесь к администратору.")

    owner = await _load_user_by_id(db, profile.user_id)
    if owner is None:
        raise RealtorAuthError("Кабинет не найден.")

    if owner.id == current_user.id:
        owner.last_seen_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(owner, attribute_names=["roles", "realtor_profile"])
        return owner

    # New Telegram account → rebind cabinet telegram_id to the current chat.
    new_tg_id = current_user.telegram_id
    new_username = current_user.username
    new_first = current_user.first_name
    new_last = current_user.last_name
    new_photo = current_user.photo_url
    new_lang = current_user.language_code
    stale_id = current_user.id

    # Free unique telegram_id on the temporary tenant row, then move it to owner.
    current_user.telegram_id = -abs(stale_id)
    await db.flush()

    owner.telegram_id = new_tg_id
    owner.username = new_username or owner.username
    owner.first_name = new_first or owner.first_name
    owner.last_name = new_last or owner.last_name
    owner.photo_url = new_photo or owner.photo_url
    owner.language_code = new_lang or owner.language_code
    owner.last_seen_at = datetime.now(timezone.utc)
    if profile.telegram_contact is None and new_username:
        profile.telegram_contact = f"@{new_username}"

    await db.flush()
    # Drop the temporary TG user via SQL so ORM does not NULL out FKs.
    db.expunge(current_user)
    await db.execute(delete(UserRoleAssignment).where(UserRoleAssignment.user_id == stale_id))
    await db.execute(delete(User).where(User.id == stale_id))
    await db.commit()

    rebound = await _load_user_by_telegram(db, new_tg_id)
    if rebound is None:
        raise RealtorAuthError("Не удалось привязать Telegram. Попробуйте ещё раз.")
    return rebound


async def set_realtor_blocked(db: AsyncSession, realtor: RealtorProfile, blocked: bool) -> None:
    from app.db.enums import PropertyStatus
    from app.db.models import Property, PropertyRealtor

    realtor.is_blocked = blocked
    realtor.can_publish = not blocked
    if blocked:
        prop_ids = (
            await db.execute(
                select(PropertyRealtor.property_id).where(PropertyRealtor.realtor_id == realtor.id)
            )
        ).scalars().all()
        if prop_ids:
            props = (
                await db.execute(select(Property).where(Property.id.in_(prop_ids)))
            ).scalars().all()
            for p in props:
                if p.status == PropertyStatus.ACTIVE.value:
                    p.status = PropertyStatus.HIDDEN.value
    await db.commit()
