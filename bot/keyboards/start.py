from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def inline_start_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Кнопки: одна в ряд
    builder.button(text="Рассчитать пошлину", callback_data="start:calc")
    builder.button(text="Получить курсы валют", callback_data="start:rates")
    builder.button(text="Оставить заявку", callback_data="start:lead")
    builder.adjust(1)
    return builder.as_markup()
