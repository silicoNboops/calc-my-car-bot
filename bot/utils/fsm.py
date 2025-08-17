from __future__ import annotations

from aiogram.fsm.context import FSMContext


async def reset_wizard(state: FSMContext) -> None:
    """Единый помощник для сброса состояния и данных визарда."""
    await state.clear()
