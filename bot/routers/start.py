from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from api.user.models import User
from bot.keyboards.calculator import vehicle_type_kb
from bot.keyboards.start import inline_start_menu_kb
from bot.states import CalculatorState
from bot.utils.fsm import reset_wizard
from bot.utils.strings import (
    PROMPT_CHOOSE_VEHICLE_TYPE,
    RESET_MESSAGE,
    START_RATES_SOON,
    START_LEAD_SOON,
)

if TYPE_CHECKING:
    from aiogram.types import Message, CallbackQuery

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command(commands=["start"]))
async def handle_start_command(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    # Сброс состояния визарда при входе в /start
    await reset_wizard(state)

    # Безопасно нормализуем поля профиля TG: они могут быть None
    tg = message.from_user
    # username в Django уникален, поэтому при отсутствии ника используем id
    # как безопасный fallback
    username = tg.username or str(tg.id)
    first_name = tg.first_name or ""
    last_name = tg.last_name or ""

    payload = {
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "email": "",
        "telegram_id": tg.id,
    }
    logger.info("/start юзер данные епта: %s", payload)

    # 1) Нормальный путь: ищем по telegram_id
    try:
        _ = await User.objects.aget(telegram_id=tg.id)
        is_new = False
    except User.DoesNotExist:
        # 2) Бэкап: если раньше юзер создавался с pk == telegram_id, то мигрируем в новое поле
        try:
            legacy = await User.objects.aget(pk=tg.id)
            # Обновим необходимые поля и проставим telegram_id
            await User.objects.filter(pk=legacy.pk).aupdate(
                telegram_id=tg.id,
                username=legacy.username or username,
                first_name=legacy.first_name or first_name,
                last_name=legacy.last_name or last_name,
                email=legacy.email or "",
            )
            is_new = False
        except User.DoesNotExist:
            # 3) Создаем нового по telegram_id
            _, is_new = await User.objects.aget_or_create(
                telegram_id=tg.id,
                defaults={
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": "",
                },
            )

    base = "Вас приветствует ChinaMotorsBot!"
    extra = (
        "\nВы успешно зарегистрированы в боте." if is_new else "\nРады видеть вас снова."
    )
    await message.answer(base + extra, reply_markup=inline_start_menu_kb())


@router.message(Command(commands=["id"]))
async def handle_id_command(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return

    # Сброс состояния визарда при запросе /id
    await reset_wizard(state)

    await message.answer(
        f"User Id: <b>{message.from_user.id}</b>\nChat Id: <b>{message.chat.id}</b>",
    )


# Inline-кнопки стартового меню (заглушки)
@router.callback_query(F.data == "start:calc")
async def cb_start_calc(call: CallbackQuery, state: FSMContext) -> None:
    # Перед запуском — сброс существующего состояния
    await reset_wizard(state)
    # Запуск визарда: устанавливаем состояние выбора типа ТС
    await state.set_state(CalculatorState.VEHICLE_TYPE)
    await call.message.answer(
        PROMPT_CHOOSE_VEHICLE_TYPE,
        reply_markup=vehicle_type_kb(),
    )
    await call.answer()


@router.message(Command(commands=["cancel"]))
async def handle_cancel_command(message: Message, state: FSMContext) -> None:
    # Универсальная отмена визарда
    await reset_wizard(state)
    await message.answer(RESET_MESSAGE)


@router.callback_query(F.data == "start:rates")
async def cb_start_rates(call: CallbackQuery) -> None:
    await call.answer(START_RATES_SOON, show_alert=True)


@router.callback_query(F.data == "start:lead")
async def cb_start_lead(call: CallbackQuery) -> None:
    await call.answer(START_LEAD_SOON, show_alert=True)
