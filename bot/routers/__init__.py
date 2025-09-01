from __future__ import annotations

from aiogram import Router

from .start import router as start_router
from .calculator import router as calculator_router
from .calculator_command import router as calculator_command_router
from .lead import router as lead_router

router = Router()
router.include_router(start_router)
router.include_router(calculator_router)
router.include_router(calculator_command_router)
router.include_router(lead_router)
