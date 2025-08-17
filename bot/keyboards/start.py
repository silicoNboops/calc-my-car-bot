from __future__ import annotations

from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup


def start_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    # Кнопки как на скрине: по одной в ряд
    builder.button(text="Рассчитать пошлину")
    builder.button(text="Получить курсы валют")
    builder.button(text="Оставить заявку")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)
