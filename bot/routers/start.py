from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from api.user.models import User
from bot.keyboards.start import inline_start_menu_kb
from bot.keyboards.calculator import vehicle_type_kb
from bot.states import CalculatorState

if TYPE_CHECKING:
    from aiogram.types import Message, CallbackQuery

router = Router()


@router.message(Command(commands=["start"]))
async def handle_start_command(message: Message) -> None:
    if message.from_user is None:
        return

    _, is_new = await User.objects.aget_or_create(
        pk=message.from_user.id,
        defaults={
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
        },
    )

    base = "Вас приветствует ChinaMotorsBot!"
    extra = (
        "\nВы успешно зарегистрированы в боте." if is_new else "\nРады видеть вас снова."
    )
    await message.answer(base + extra, reply_markup=inline_start_menu_kb())


@router.message(Command(commands=["id"]))
async def handle_id_command(message: Message) -> None:
    if message.from_user is None:
        return

    await message.answer(
        f"User Id: <b>{message.from_user.id}</b>\nChat Id: <b>{message.chat.id}</b>",
    )


# Inline-кнопки стартового меню (заглушки)
@router.callback_query(F.data == "start:calc")
async def cb_start_calc(call: CallbackQuery, state: FSMContext) -> None:
    # Запуск визарда: устанавливаем состояние выбора типа ТС
    await state.set_state(CalculatorState.VEHICLE_TYPE)
    await call.message.answer(
        "Выберите тип автомобиля:",
        reply_markup=vehicle_type_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "start:rates")
async def cb_start_rates(call: CallbackQuery) -> None:
    await call.answer("Курсы валют скоро добавлю", show_alert=True)


@router.callback_query(F.data == "start:lead")
async def cb_start_lead(call: CallbackQuery) -> None:
    await call.answer("Форму заявки скоро добавлю", show_alert=True)
