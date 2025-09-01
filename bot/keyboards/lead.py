from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def lead_after_calc_kb() -> InlineKeyboardMarkup:
    """Клавиатура с кнопками после расчета."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Оставить заявку", callback_data="lead:create_with_calc")
    builder.button(text="🔄 Повторить расчет", callback_data="calc:restart")
    builder.button(text="🏠 В главное меню", callback_data="lead:back_to_menu")
    builder.adjust(2, 1)  # 2 кнопки в первом ряду, 1 во втором
    return builder.as_markup()


def lead_back_to_menu_kb() -> InlineKeyboardMarkup:
    """Клавиатура для возврата в главное меню."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 В главное меню", callback_data="lead:back_to_menu")
    return builder.as_markup()