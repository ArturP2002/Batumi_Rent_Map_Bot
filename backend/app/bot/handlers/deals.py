from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.texts import CHANNEL_RU, DECISION_RU, INQUIRY_STATUS_RU
from app.bot.states import DealFSM
from app.db.enums import ConfirmationDecision, ConfirmationSide, InquiryStatus, UserRole
from app.db.models import Inquiry, User
from app.schemas.deals import DealCreateIn
from app.services import deals as deals_svc
from app.services.notifications import enqueue_notification

router = Router()


@router.message(F.text == "📨 Обращения")
async def list_inquiries(message: Message, db_user: User, db: AsyncSession):
    if not db_user.realtor_profile:
        await message.answer("Только для риелторов.")
        return
    rows = (
        await db.execute(
            select(Inquiry)
            .where(Inquiry.realtor_id == db_user.realtor_profile.id)
            .order_by(Inquiry.created_at.desc())
            .limit(20)
        )
    ).scalars().all()
    if not rows:
        await message.answer("Обращений пока нет.")
        return
    lines = [
        (
            f"#{i.id}: объект {i.property_id}, клиент {i.user_id}, "
            f"{CHANNEL_RU.get(i.channel, i.channel)} — "
            f"{INQUIRY_STATUS_RU.get(i.status, i.status)}"
        )
        for i in rows
    ]
    await message.answer("\n".join(lines))


@router.message(F.text == "✅ Подтвердить аренду")
async def start_deal(message: Message, db_user: User, state: FSMContext, db: AsyncSession):
    if not db_user.realtor_profile:
        await message.answer("Только для риелторов.")
        return
    rows = (
        await db.execute(
            select(Inquiry)
            .where(
                Inquiry.realtor_id == db_user.realtor_profile.id,
                Inquiry.status.in_(
                    [
                        InquiryStatus.NEW.value,
                        InquiryStatus.IN_PROGRESS.value,
                        InquiryStatus.AWAITING_CONFIRMATIONS.value,
                    ]
                ),
            )
            .limit(20)
        )
    ).scalars().all()
    if not rows:
        await message.answer(
            "Нет активных обращений.\n"
            "Сначала клиент должен нажать контакт в карточке квартиры."
        )
        return
    await state.set_state(DealFSM.choose_inquiry)
    await message.answer(
        "Выберите ID обращения:\n"
        + "\n".join(f"{i.id}: объект {i.property_id}" for i in rows)
    )


@router.message(DealFSM.choose_inquiry)
async def deal_choose(message: Message, state: FSMContext, db: AsyncSession):
    if not (message.text or "").isdigit():
        await message.answer("Пришлите числовой ID обращения")
        return
    inquiry = await db.get(Inquiry, int(message.text))
    if not inquiry:
        await message.answer("Обращение не найдено")
        return
    await state.update_data(
        inquiry_id=inquiry.id,
        property_id=inquiry.property_id,
        realtor_id=inquiry.realtor_id,
        client_user_id=inquiry.user_id,
    )
    await state.set_state(DealFSM.dates)
    await message.answer(
        "Даты аренды в формате ГГГГ-ММ-ДД ГГГГ-ММ-ДД\n"
        "или отправьте «-», если даты не нужны:"
    )


@router.message(DealFSM.dates)
async def deal_dates(message: Message, state: FSMContext, db_user: User, db: AsyncSession):
    data = await state.get_data()
    start = end = None
    text = (message.text or "").strip()
    if text != "-":
        parts = text.split()
        if len(parts) != 2:
            await message.answer("Нужны две даты или «-»")
            return
        try:
            start = date.fromisoformat(parts[0])
            end = date.fromisoformat(parts[1])
        except ValueError:
            await message.answer("Формат дат: ГГГГ-ММ-ДД ГГГГ-ММ-ДД")
            return
    deal = await deals_svc.create_deal(
        db,
        DealCreateIn(
            inquiry_id=data["inquiry_id"],
            property_id=data["property_id"],
            realtor_id=data["realtor_id"],
            client_user_id=data["client_user_id"],
            start_date=start,
            end_date=end,
        ),
        actor=db_user,
    )
    await enqueue_notification(
        db,
        user_id=data["client_user_id"],
        kind="deal_confirm_request",
        idempotency_key=f"deal_request:{deal.id}:client",
        text=(
            f"Риелтор запросил подтверждение аренды по сделке №{deal.id}. "
            "Откройте уведомление и подтвердите или отклоните."
        ),
        webapp_path=f"deal_{deal.id}",
        payload={"deal_id": deal.id},
    )
    await message.answer(
        f"Сделка №{deal.id} создана. Клиенту отправлен запрос на подтверждение.",
    )
    await state.clear()


@router.callback_query(F.data.startswith("deal_yes:") | F.data.startswith("deal_no:"))
async def client_deal_callback(callback: CallbackQuery, db_user: User, db: AsyncSession):
    action, deal_id_s = callback.data.split(":")
    deal = await deals_svc.get_deal(db, int(deal_id_s))
    if deal.client_user_id != db_user.id and not db_user.has_role(UserRole.ADMIN):
        await callback.answer("Это не ваша сделка", show_alert=True)
        return
    decision = (
        ConfirmationDecision.APPROVED.value
        if action == "deal_yes"
        else ConfirmationDecision.REJECTED.value
    )
    await deals_svc.decide_confirmation(
        db,
        deal,
        side=ConfirmationSide.CLIENT,
        actor=db_user,
        decision=decision,
    )
    await callback.message.answer(
        f"Ваше решение по сделке №{deal.id}: {DECISION_RU.get(decision, decision)}"
    )
    await callback.answer("Сохранено")
