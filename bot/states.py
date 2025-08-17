from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CalculatorState(StatesGroup):
    """FSM для мастера расчёта таможни.

    Шаги будут расширяться по мере добавления экранов.
    """

    VEHICLE_TYPE = State()
    CURRENCY = State()
    PRICE = State()
    ROLE = State()
    ENGINE_TYPE = State()
    ENGINE_CC = State()
    AGE_KEY = State()
