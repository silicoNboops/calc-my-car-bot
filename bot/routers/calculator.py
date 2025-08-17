from __future__ import annotations

import re
from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from api.calculator.choices import Currency as CurrencyChoices, EngineType as EngineTypeChoices, \
    VehicleType as VehicleTypeChoices, AgeKey as AgeKeyChoices
from api.calculator.choices import ImporterKind
from api.calculator.services import (
    CalculatorService,
    EstimateInput,
    get_default_currency_provider,
)
from bot.keyboards.calculator import (
    VehicleTypeCD,
    CurrencyCD,
    currency_kb,
    format_vehicle_title,
    format_currency_title,
    RoleCD,
    role_kb,
    format_importer_kind_title,
    EngineTypeCD,
    engine_type_kb,
    format_engine_type_title,
    AgeKeyCD,
    age_key_kb,
    format_age_key_title,
)
from bot.states import CalculatorState
from bot.utils.formatting import format_amount, fmt_money, format_selection_header

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message

router = Router()


def _format_calc_result(res) -> str:  # type: ignore[no-untyped-def]
    return (
        "Итог расчёта:\n"
        f"Цена (RUB): <b>{fmt_money(res.price_rub)}</b>\n"
        f"Цена (EUR): <b>{fmt_money(res.price_eur)}</b>\n"
        f"Пошлина (EUR): <b>{fmt_money(res.duty_eur)}</b>\n"
        f"Пошлина (RUB): <b>{fmt_money(res.duty_rub)}</b>\n"
        f"Утильсбор (RUB): <b>{fmt_money(res.util_fee)}</b>\n"
        f"Акциз (RUB): <b>{fmt_money(res.accise_rub)}</b>\n"
        f"НДС (RUB): <b>{fmt_money(res.vat_rub)}</b>\n"
        f"Таможенный сбор (RUB): <b>{fmt_money(res.customs_fee)}</b>\n"
        f"Всего (RUB): <b>{fmt_money(res.subtotal_customs)}</b>\n"
    )


def _estimate_sync(payload: dict) -> tuple[str, dict[str, float]]:
    """Синхронный расчёт через CalculatorService, в стиле /calc."""
    provider = get_default_currency_provider()
    service = CalculatorService(currency_provider=provider)
    calc = service.build_calculator()
    # Приводим типы к TextChoices, если пришли строки
    data = dict(payload)
    try:
        if not isinstance(data.get("currency"), CurrencyChoices):
            data["currency"] = CurrencyChoices(data["currency"])  # type: ignore[arg-type]
        if not isinstance(data.get("engine_type"), EngineTypeChoices):
            data["engine_type"] = EngineTypeChoices(data["engine_type"])  # type: ignore[arg-type]
        if not isinstance(data.get("vehicle_type"), VehicleTypeChoices):
            data["vehicle_type"] = VehicleTypeChoices(data["vehicle_type"])  # type: ignore[arg-type]
        if not isinstance(data.get("age_key"), AgeKeyChoices):
            data["age_key"] = AgeKeyChoices(data["age_key"])  # type: ignore[arg-type]
    except Exception:
        # Если не удалось привести — пусть выбросится позже в расчёте
        pass
    res = calc.estimate(EstimateInput(**data))
    return _format_calc_result(res), provider.get_rates()


async def _edit_or_send(message, text: str, reply_markup=None) -> None:
    """Безопасное редактирование: если редактировать нельзя — отправим новое сообщение."""
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await message.answer(text, reply_markup=reply_markup)


@router.callback_query(CalculatorState.VEHICLE_TYPE, VehicleTypeCD.filter())
async def choose_vehicle_type(call: CallbackQuery, state: FSMContext, callback_data: VehicleTypeCD) -> None:
    # 1) Сохраняем выбранный тип ТС
    await state.update_data(vehicle_type=callback_data.type)
    # 2) Переходим к следующему шагу — выбор валюты
    await state.set_state(CalculatorState.CURRENCY)
    # 3) Редактируем текущее сообщение (не создаём новое), показываем клавиатуру валют
    # Показываем заголовок с выбранным типом и просим выбрать валюту
    cur_data = {"vehicle_type": callback_data.type}
    header = format_selection_header(cur_data)
    await call.message.edit_text(header + "Выберите, в какой валюте будет указана цена автомобиля:",
                                 reply_markup=currency_kb())
    await call.answer()


@router.callback_query(CalculatorState.CURRENCY, CurrencyCD.filter())
async def choose_currency(call: CallbackQuery, state: FSMContext, callback_data: CurrencyCD) -> None:
    # Сохраняем валюту и подтверждаем выбор
    await state.update_data(currency=callback_data.code)
    data = await state.get_data()
    currency_label = format_currency_title(callback_data.code)
    await state.update_data(currency_title=currency_label)
    # Заголовок с авто и валютой, затем просьба ввести цену
    header = format_selection_header({**data, "currency": callback_data.code, "currency_title": currency_label})
    msg = await call.message.edit_text(header + "Введите стоимость автомобиля (например, 💰 1 200 000):",
                                       reply_markup=None)
    # Переходим к вводу стоимости и запоминаем id сообщения с промптом
    await state.update_data(prompt_chat_id=msg.chat.id, prompt_message_id=msg.message_id, currency_title=currency_label)
    await state.set_state(CalculatorState.PRICE)
    await call.answer()


def _parse_price(raw: str) -> int | None:
    """Парсит цену из строки, допускает любые пробелы, запятые и точки как разделители тысяч.

    Возвращает целое число (единицы валюты) или None, если невалидно.
    Ограничения: не пусто, неотрицательно, только цифры после очистки.
    """
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    # Удаляем все пробелы (в т.ч. множественные), запятые и точки
    s = re.sub(r"[\s,\.]+", "", s)
    if not s or not s.isdigit():
        return None
    try:
        value = int(s)
    except ValueError:
        return None
    # Требование: строго > 0
    if value <= 0:
        return None
    return value


@router.message(CalculatorState.PRICE, F.text)
async def input_price(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    chat_id = data.get("prompt_chat_id")
    msg_id = data.get("prompt_message_id")
    vehicle_title = data.get("vehicle_title")
    currency_title = data.get("currency_title")

    value = _parse_price(message.text or "")
    # Пытаемся удалить пользовательское сообщение (эстетика чата)
    try:
        await message.delete()
    except Exception:
        pass
    if value is None:
        # Определяем пояснение ошибки
        raw = (message.text or "").strip()
        if not raw:
            reason = "Ошибка: значение пустое."
        else:
            # Если после очистки не цифры — это не число; либо число <= 0
            cleaned = re.sub(r"[\s,\.]+", "", raw)
            if not cleaned.isdigit():
                reason = "Ошибка: введите целое число, можно с пробелами/запятыми/точками как разделителями тысяч."
            else:
                reason = "Ошибка: стоимость должна быть > 0."

        header = format_selection_header(data)
        error_summary = header + f"<b>— Стоимость: ❌ ОШИБКА</b>\n{reason}"
        if chat_id and msg_id:
            await message.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=error_summary)
        else:
            await message.answer(error_summary)
        return

    # Валидно — сохраняем
    await state.update_data(price=value)
    header = format_selection_header({**data, "price": value})
    prompt_text = header + "Кто ввозит автомобиль:"
    if chat_id and msg_id:
        await message.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=prompt_text,
                                            reply_markup=role_kb())
    else:
        await message.answer(prompt_text, reply_markup=role_kb())
    await state.set_state(CalculatorState.ROLE)


@router.callback_query(CalculatorState.ROLE, RoleCD.filter())
async def choose_role(call: CallbackQuery, state: FSMContext, callback_data: RoleCD) -> None:
    kind = callback_data.kind
    # Маппинг в сервисные флаги: is_jur и is_personal_use
    if kind == ImporterKind.JUR:
        is_jur = True
        is_personal_use = None
    elif kind == ImporterKind.PHYS_PERSONAL:
        is_jur = False
        is_personal_use = True
    else:  # ImporterKind.PHYS_COMMERCIAL
        is_jur = False
        is_personal_use = False

    await state.update_data(
        importer_kind=kind,
        is_jur=is_jur,
        is_personal_use=is_personal_use,
    )
    data = await state.get_data()
    prompt_text = format_selection_header(data) + "Выберите тип двигателя:"
    await call.message.edit_text(prompt_text, reply_markup=engine_type_kb())
    await call.answer()
    await state.set_state(CalculatorState.ENGINE_TYPE)


@router.callback_query(CalculatorState.ENGINE_TYPE, EngineTypeCD.filter())
async def choose_engine_type(call: CallbackQuery, state: FSMContext, callback_data: EngineTypeCD) -> None:
    await state.update_data(engine_type=callback_data.kind)
    data = await state.get_data()
    # Запрос объёма двигателя
    header = _format_selection_header(data)
    prompt_text = header + "Введите объём двигателя в см³ (например, 1500):"
    try:
        msg = await call.message.edit_text(prompt_text)
    except TelegramBadRequest:
        msg = await call.message.answer(prompt_text)
    await state.update_data(prompt_chat_id=msg.chat.id, prompt_message_id=msg.message_id)
    await call.answer()
    await state.set_state(CalculatorState.ENGINE_CC)


@router.message(CalculatorState.ENGINE_CC, F.text)
async def input_engine_cc(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    chat_id = data.get("prompt_chat_id")
    msg_id = data.get("prompt_message_id")
    vehicle_title = data.get("vehicle_title")
    currency_title = data.get("currency_title")
    importer_title = format_importer_kind_title(str(data.get("importer_kind", "")))
    engine_title = format_engine_type_title(str(data.get("engine_type", "")))

    # Парсинг объёма аналогично цене: допускаем пробелы/запятые/точки, строго > 0
    raw = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass

    s = re.sub(r"[\s,\.]+", "", raw)
    value: int | None
    if not raw:
        value = None
    elif s.isdigit():
        value = int(s)
        if value <= 0:
            value = None
    else:
        value = None

    amount_fmt = format_amount(int(data.get("price", 0)))

    if value is None:
        # Подробное сообщение об ошибке
        if not raw:
            reason = "Ошибка: значение пустое."
        else:
            if not s.isdigit():
                reason = "Ошибка: введите целое число, можно с пробелами/запятыми/точками как разделителями тысяч."
            else:
                reason = "Ошибка: объём двигателя должен быть > 0."

        header = _format_selection_header(data)
        error_summary = header + f"<b>— Объём: ❌ ОШИБКА</b>\n{reason}\n\nВведите объём двигателя в см³ (например, 1500):"
        if chat_id and msg_id:
            await message.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=error_summary)
        else:
            await message.answer(error_summary)
        return

    # Валидно: сохраняем и показываем резюме
    await state.update_data(engine_cc=value)
    engine_cc_fmt = f"{format_amount(value)} см³"
    if chat_id and msg_id:
        # После ввода объёма предлагаем выбрать возраст авто
        header2 = format_selection_header({**data, "engine_cc": value})
        prompt_text = header2 + "Выберите возраст автомобиля:"
        try:
            await message.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=prompt_text,
                                                reply_markup=age_key_kb())
        except TelegramBadRequest:
            await message.answer(prompt_text, reply_markup=age_key_kb())
    else:
        header2 = format_selection_header({**data, "engine_cc": value})
        await message.answer(header2)
        await message.answer("Выберите возраст автомобиля:", reply_markup=age_key_kb())
    await state.set_state(CalculatorState.AGE_KEY)


@router.callback_query(CalculatorState.AGE_KEY, AgeKeyCD.filter())
async def choose_age_key(call: CallbackQuery, state: FSMContext, callback_data: AgeKeyCD) -> None:
    await state.update_data(age_key=callback_data.key)
    data = await state.get_data()
    vehicle_title = data.get("vehicle_title") or format_vehicle_title(str(data.get("vehicle_type", "")))
    currency_title = data.get("currency_title") or format_currency_title(str(data.get("currency", "")))
    price = int(data.get("price", 0))
    amount_fmt = format_amount(price)
    importer_title = format_importer_kind_title(str(data.get("importer_kind", "")))
    engine_title = format_engine_type_title(str(data.get("engine_type", "")))
    engine_cc = int(data.get("engine_cc", 0))
    engine_cc_fmt = f"{format_amount(engine_cc)} см³" if engine_cc else "—"
    age_title = format_age_key_title(callback_data.key)
    # Пакуем пейлоад как для /calc
    payload = {
        "price": float(price),
        "currency": str(data.get("currency", "RUB")),
        "engine_cc": int(engine_cc),
        "hp": int(data.get("hp", 0) or 0),  # hp шага пока нет — используем 0
        "engine_type": str(data.get("engine_type", "")),
        "age_key": str(callback_data.key),
        "is_jur": bool(data.get("is_jur", False)),
        "is_personal_use": data.get("is_personal_use", None),
        "vehicle_type": str(data.get("vehicle_type", "car")),
    }
    try:
        result_text, rates = await sync_to_async(_estimate_sync)(payload)
    except Exception as e:  # noqa: BLE001
        await call.message.edit_text(f"Ошибка расчёта: {e}")
        await call.answer()
        await state.clear()
        return

    # Курс для выбранной валюты
    cur_code = str(data.get("currency", "RUB"))
    fx_line = ""
    try:
        if cur_code and cur_code != "RUB" and cur_code in rates and "RUB" in rates:
            rub_per_cur = float(rates[cur_code])
            fx_line = f"\nРасчёты произведены на актуальном курсе: 1 {cur_code} = {rub_per_cur:.4f} ₽\n"
    except Exception:
        fx_line = ""

    header = format_selection_header(
        {
            "vehicle_title": vehicle_title,
            "vehicle_type": data.get("vehicle_type"),
            "currency_title": currency_title,
            "currency": data.get("currency"),
            "price": price,
            "importer_kind": data.get("importer_kind"),
            "engine_type": data.get("engine_type"),
            "engine_cc": engine_cc,
        },
        age_title=age_title,
    )

    contact = "\nСвяжитесь с нами: @Slaford - Слафординка"

    final_text = header + result_text + fx_line + contact
    await _edit_or_send(call.message, final_text, reply_markup=None)
    await call.answer()
    # Сбрасываем состояние и данные визарда
    await state.clear()
