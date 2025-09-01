from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from api.user.models import User, Lead
from bot.keyboards.lead import lead_back_to_menu_kb
from bot.keyboards.start import inline_start_menu_kb
from bot.states import LeadState
from bot.utils.fsm import reset_wizard
from bot.utils.notifications import notify_admins_about_new_lead

if TYPE_CHECKING:
    from aiogram.types import Message, CallbackQuery

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "lead:create_with_calc")
async def start_lead_with_calc(call: CallbackQuery, state: FSMContext) -> None:
    """Начинаем создание заявки с сохранением данных расчета."""
    await call.answer()
    await state.set_state(LeadState.WAITING_NAME)
    await call.message.answer(
        "📝 Создание заявки\n\n"
        "Введите ваше имя (например, Максим):",
        reply_markup=None
    )


@router.callback_query(F.data == "start:lead")
async def start_lead_from_menu(call: CallbackQuery, state: FSMContext) -> None:
    """Начинаем создание заявки из главного меню."""
    await call.answer()
    await reset_wizard(state)
    await state.set_state(LeadState.WAITING_NAME)
    await call.message.answer(
        "📝 Создание заявки\n\n"
        "Введите ваше имя (например, Максим):",
        reply_markup=None
    )


@router.message(LeadState.WAITING_NAME, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    """Обрабатываем ввод имени."""
    name = message.text.strip()
    
    if not name or len(name) < 2:
        await message.answer(
            "❌ Имя должно содержать минимум 2 символа.\n\n"
            "Введите ваше имя (например, Максим):"
        )
        return
    
    if len(name) > 100:
        await message.answer(
            "❌ Имя слишком длинное (максимум 100 символов).\n\n"
            "Введите ваше имя (например, Максим):"
        )
        return
    
    await state.update_data(name=name)
    await state.set_state(LeadState.WAITING_PHONE)
    await message.answer(
        f"✅ Имя: {name}\n\n"
        "Введите ваш номер телефона (например, 71234567890 или 81234567890):"
    )


@router.message(LeadState.WAITING_PHONE, F.text)
async def process_phone(message: Message, state: FSMContext) -> None:
    """Обрабатываем ввод телефона и сохраняем заявку."""
    phone = message.text.strip()
    
    # Простая валидация телефона
    phone_digits = ''.join(filter(str.isdigit, phone))
    
    if not phone_digits:
        await message.answer(
            "❌ Номер телефона должен содержать цифры.\n\n"
            "Введите ваш номер телефона (например, 71234567890 или 81234567890):"
        )
        return
    
    if len(phone_digits) < 10 or len(phone_digits) > 12:
        await message.answer(
            "❌ Номер телефона должен содержать от 10 до 12 цифр.\n\n"
            "Введите ваш номер телефона (например, 71234567890 или 81234567890):"
        )
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    name = data.get('name')
    
    if not name:
        await message.answer("❌ Ошибка: имя не найдено. Начните заново.")
        await reset_wizard(state)
        return
    
    # Получаем пользователя
    if not message.from_user:
        await message.answer("❌ Ошибка: не удалось определить пользователя.")
        return
    
    try:
        user = await User.objects.aget(telegram_id=message.from_user.id)
    except User.DoesNotExist:
        await message.answer("❌ Ошибка: пользователь не найден. Выполните /start")
        return
    
    # Подготавливаем данные расчета если есть
    calculation_data = None
    calc_params = data.get('calculation_params')
    calc_result = data.get('calculation_result')
    
    if calc_params and calc_result:
        calculation_data = {
            'params': calc_params,
            'result': calc_result,
            'created_at': data.get('calculation_created_at')
        }
    
    # Сохраняем заявку
    try:
        lead = await Lead.objects.acreate(
            user=user,
            name=name,
            phone=phone_digits,
            calculation_data=calculation_data
        )
        
        # Формируем сообщение об успехе
        success_message = (
            "✅ Спасибо! Ваша заявка сохранена.\n\n"
            f"Имя: {name}\n"
            f"Телефон: {phone_digits}\n\n"
            "Наш менеджер свяжется с вами в ближайшее время!"
        )
        
        await message.answer(
            success_message,
            reply_markup=lead_back_to_menu_kb()
        )
        
        # Уведомляем админов
        logger.info(
            f"Новая заявка #{lead.id}: {name} ({phone_digits}) "
            f"от пользователя {user.username or user.telegram_id}"
        )
        
        # Отправляем уведомление админам
        try:
            await notify_admins_about_new_lead(message.bot, lead)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления админам: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении заявки: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении заявки. Попробуйте позже.",
            reply_markup=lead_back_to_menu_kb()
        )
    
    await reset_wizard(state)


@router.callback_query(F.data == "lead:back_to_menu")
async def back_to_menu(call: CallbackQuery, state: FSMContext) -> None:
    """Возврат в главное меню."""
    await call.answer()
    await reset_wizard(state)
    await call.message.edit_text(
        "🏠 Главное меню",
        reply_markup=inline_start_menu_kb()
    )


# Обработчик для любых других сообщений в состоянии заявки
@router.message(LeadState.WAITING_NAME)
@router.message(LeadState.WAITING_PHONE)
async def handle_invalid_input(message: Message, state: FSMContext) -> None:
    """Обрабатываем некорректный ввод в состояниях заявки."""
    current_state = await state.get_state()
    
    if current_state == LeadState.WAITING_NAME:
        await message.answer(
            "❌ Пожалуйста, введите ваше имя текстом.\n\n"
            "Введите ваше имя (например, Максим):"
        )
    elif current_state == LeadState.WAITING_PHONE:
        await message.answer(
            "❌ Пожалуйста, введите номер телефона текстом.\n\n"
            "Введите ваш номер телефона (например, 71234567890 или 81234567890):"
        )