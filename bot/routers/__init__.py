from __future__ import annotations

from aiogram import Router

from .start import router as start_router
from bot.handlers import router as calc_router  # временно здесь остаётся калькулятор

router = Router()
router.include_router(start_router)
router.include_router(calc_router)
