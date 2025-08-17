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
    # TODO: ENGINE_CC = State()
    # TODO: HP = State()
    # TODO: AGE = State()
    # TODO: ROLE = State()
    # TODO: USAGE = State()
    # TODO: PREVIEW = State()
