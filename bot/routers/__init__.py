from __future__ import annotations

from aiogram import Router

from .start import router as start_router
from .calculator import router as calculator_router

router = Router()
router.include_router(start_router)
router.include_router(calculator_router)
