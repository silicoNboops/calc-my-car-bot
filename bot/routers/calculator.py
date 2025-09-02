from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from api.calculator.choices import Currency as CurrencyChoices, EngineType as EngineTypeChoices, \
    VehicleType as VehicleTypeChoices, AgeKey as AgeKeyChoices
from api.calculator.choices import ImporterKind
from api.calculator.models import Settings
from api.calculator.services import (
    CalculatorService,
    EstimateInput,
    get_default_currency_provider,
)
from api.user.models import User, CalculationLog
from bot.keyboards.calculator import (
    VehicleTypeCD,
    CurrencyCD,
    currency_kb,
    format_vehicle_title,
    RoleCD,
    role_kb,
    format_importer_kind_title,
    EngineTypeCD,
    engine_type_kb,
    format_engine_type_title,
    AgeKeyCD,
    age_key_kb,
    format_age_key_title,
    HybridFuelCD,
    hybrid_fuel_kb,
    YesNoCD,
    yes_no_kb,
)
from bot.keyboards.calculator import vehicle_type_kb
from bot.keyboards.lead import lead_after_calc_kb
from bot.states import CalculatorState
from bot.utils.currency import format_currency_title
from bot.utils.formatting import (
    format_amount,
    fmt_money,
    format_selection_header,
    parse_int_amount,
    build_number_error,
    format_result_block_rub_only,
)
from bot.utils.strings import (
    PROMPT_CHOOSE_CURRENCY,
    PROMPT_ENTER_PRICE,
    PROMPT_CHOOSE_ROLE,
    PROMPT_CHOOSE_ENGINE_TYPE,
    PROMPT_ENTER_ENGINE_CC,
    PROMPT_ENTER_ENGINE_HP,
    PROMPT_CHOOSE_AGE,
    PROMPT_CHOOSE_HYBRID_FUEL,
    PROMPT_CHOOSE_DVS_GT_ED,
    CONTACT_LINE,
)
from calculator_v2.adapter import run_v6_with_bot_payload
from calculator_v2.customs_calculator_v6 import RatesFetcher, CalculationResult

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message

router = Router()


def _format_calc_result(res) -> str:  # type: ignore[no-untyped-def]
    return (
        "🧮 Итог расчёта:\n"
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


def _format_calc_result_v6(res: CalculationResult) -> str:
    """Форматирование результата v6 под текущий UI."""
    duty_eur = float(res.breakdown.get("duty_eur", 0.0) or 0.0)
    price_eur = float(res.breakdown.get("cost_eur", 0.0) or 0.0)
    return (
        "🧮 Итог расчёта:\n"
        f"Цена (RUB): <b>{fmt_money(res.cost_rub)}</b>\n"
        f"Пошлина (RUB): <b>{fmt_money(res.duty_rub)}</b>\n"
        f"Утильсбор (RUB): <b>{fmt_money(res.util_fee_rub)}</b>\n"
        f"Акциз (RUB): <b>{fmt_money(res.excise_rub)}</b>\n"
        f"НДС (RUB): <b>{fmt_money(res.vat_rub)}</b>\n"
        f"Таможенный сбор (RUB): <b>{fmt_money(res.customs_fee_rub)}</b>\n"
    )


def _estimate_sync(payload: dict) -> tuple[str, dict[str, float], float]:
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
    return _format_calc_result(res), provider.get_rates(), float(res.subtotal_customs)


def _estimate_v6_sync(payload: dict) -> tuple[str, dict[str, float], float, dict]:
    """Синхронный расчёт через v6-адаптер без Django/ORM.

    Возвращает текст, курсы, итог в RUB и подробный словарь результата для сохранения.
    """
    res_v6 = run_v6_with_bot_payload(payload)
    rates = RatesFetcher.get_currency_rates()

    # Приводим результат к формату как у старого калькулятора, чтобы единообразно сохранять
    duty_eur = float((res_v6.breakdown or {}).get("duty_eur", 0.0) or 0.0)
    price_eur = float((res_v6.breakdown or {}).get("cost_eur", 0.0) or 0.0)
    result_data = {
        "subtotal_customs": float(res_v6.total_rub),
        "duty_rub": float(res_v6.duty_rub),
        "duty_eur": duty_eur,
        "vat_rub": float(res_v6.vat_rub),
        "util_fee": float(res_v6.util_fee_rub),
        "accise_rub": float(res_v6.excise_rub),
        "customs_fee": float(res_v6.customs_fee_rub),
        "price_rub": float(res_v6.cost_rub),
        "price_eur": price_eur,
    }

    # Возвращаем пустой текст — итоговый блок построим выше из словаря и комиссии брокера
    return "", rates, float(res_v6.total_rub), result_data


def _estimate_sync_with_data(payload: dict) -> tuple[str, dict[str, float], float, dict]:
    """Синхронный расчёт с возвратом полных данных для заявки."""
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

    # Формируем полные данные результата
    result_data = {
        'subtotal_customs': float(res.subtotal_customs),
        'duty_rub': float(res.duty_rub),
        'duty_eur': float(res.duty_eur),
        'vat_rub': float(res.vat_rub),
        'util_fee': float(res.util_fee),
        'accise_rub': float(res.accise_rub),
        'customs_fee': float(res.customs_fee),
        'price_rub': float(res.price_rub),
        'price_eur': float(res.price_eur),
    }

    return _format_calc_result(res), provider.get_rates(), float(res.subtotal_customs), result_data


def _get_company_commission_rub() -> float:
    """Возвращает комиссию компании в рублях из Settings.

    Поле admin может храниться в тысячах (например, 69 => 69 000),
    поэтому делаем мягкую нормализацию: если значение < 1000, умножаем на 1000.
    """
    s = Settings.objects.order_by("-updated_at").first()
    raw = float(getattr(s, "company_commission_rub", 0.0) or 0.0)
    if raw < 1000.0:
        return raw * 1000.0
    return raw


async def _edit_or_send(
        message=None,
        text: str | None = None,
        reply_markup=None,
        *,
        bot=None,
        chat_id: int | None = None,
        message_id: int | None = None,
):
    """Единый helper: редактирует существующее сообщение или отправляет новое.

    Поддерживает два режима:
    - message: aiogram Message — будет вызван edit_text, fallback answer.
    - bot+chat_id+message_id: используем bot.edit_message_text, fallback bot.send_message.

    Возвращает объект Message, который в итоге отображён пользователю.
    """
    if message is not None:
        try:
            return await message.edit_text(text, reply_markup=reply_markup)
        except TelegramBadRequest:
            return await message.answer(text, reply_markup=reply_markup)
    if bot is not None and chat_id is not None and message_id is not None:
        try:
            return await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text,
                                               reply_markup=reply_markup)
        except TelegramBadRequest:
            return await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    # В крайнем случае — ничего не делаем
    return None


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
    await _edit_or_send(call.message, header + PROMPT_CHOOSE_CURRENCY, reply_markup=currency_kb())
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
    msg = await _edit_or_send(call.message, header + PROMPT_ENTER_PRICE, reply_markup=None)
    # Переходим к вводу стоимости и запоминаем id сообщения с промптом
    await state.update_data(prompt_chat_id=msg.chat.id, prompt_message_id=msg.message_id, currency_title=currency_label)
    await state.set_state(CalculatorState.PRICE)
    await call.answer()


@router.message(CalculatorState.PRICE, F.text)
async def input_price(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    chat_id = data.get("prompt_chat_id")
    msg_id = data.get("prompt_message_id")
    vehicle_title = data.get("vehicle_title")
    currency_title = data.get("currency_title")

    value = parse_int_amount(message.text)
    # Пытаемся удалить пользовательское сообщение (эстетика чата)
    try:
        await message.delete()
    except Exception:
        pass
    if value is None:
        # Определяем пояснение ошибки
        raw = message.text or ""
        reason = build_number_error(raw, what="стоимость")
        header = format_selection_header(data)
        error_summary = header + f"<b>— Стоимость: ❌ ОШИБКА</b>\n{reason}"
        if chat_id and msg_id:
            await _edit_or_send(None, error_summary, bot=message.bot, chat_id=chat_id, message_id=msg_id)
        else:
            await _edit_or_send(message, error_summary)
        return

    # Валидно — сохраняем
    await state.update_data(price=value)
    header = format_selection_header({**data, "price": value})
    prompt_text = header + PROMPT_CHOOSE_ROLE
    if chat_id and msg_id:
        await _edit_or_send(None, prompt_text, reply_markup=role_kb(), bot=message.bot, chat_id=chat_id,
                            message_id=msg_id)
    else:
        await _edit_or_send(message, prompt_text, reply_markup=role_kb())
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
    prompt_text = format_selection_header(data) + PROMPT_CHOOSE_ENGINE_TYPE
    await _edit_or_send(call.message, prompt_text, reply_markup=engine_type_kb())
    await call.answer()
    await state.set_state(CalculatorState.ENGINE_TYPE)


@router.callback_query(CalculatorState.ENGINE_TYPE, EngineTypeCD.filter())
async def choose_engine_type(call: CallbackQuery, state: FSMContext, callback_data: EngineTypeCD) -> None:
    await state.update_data(engine_type=callback_data.kind)
    data = await state.get_data()
    header = format_selection_header(data)
    # Если гибрид — сначала уточняем топливо ДВС, затем флаг ДВС>ЭД
    if callback_data.kind in {EngineTypeChoices.HYBRID_PARALLEL, EngineTypeChoices.HYBRID_SERIES}:
        msg = await _edit_or_send(call.message, header + PROMPT_CHOOSE_HYBRID_FUEL, reply_markup=hybrid_fuel_kb())
        await state.update_data(prompt_chat_id=msg.chat.id, prompt_message_id=msg.message_id)
        await call.answer()
        await state.set_state(CalculatorState.HYBRID_ICE_FUEL)
        return
    # Для остальных типов — сразу к объёму двигателя
    # Очистим гибридные поля, если ранее что-то было выбрано
    await state.update_data(hybrid_ice_fuel=None, dvs_gt_electric=None)
    prompt_text = header + PROMPT_ENTER_ENGINE_CC
    msg = await _edit_or_send(call.message, prompt_text)
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

    value = parse_int_amount(raw)

    amount_fmt = format_amount(int(data.get("price", 0)))

    if value is None:
        # Подробное сообщение об ошибке
        reason = build_number_error(raw, what="объём двигателя")
        header = format_selection_header(data)
        error_summary = header + f"<b>— Объём: ❌ ОШИБКА</b>\n{reason}\n\n{PROMPT_ENTER_ENGINE_CC}"
        if chat_id and msg_id:
            await _edit_or_send(None, error_summary, bot=message.bot, chat_id=chat_id, message_id=msg_id)
        else:
            await _edit_or_send(message, error_summary)
        return

    # Валидно: сохраняем и решаем — нужен ли шаг мощности
    await state.update_data(engine_cc=value)
    engine_cc_fmt = f"{format_amount(value)} см³"

    # Определяем, нужен ли ввод мощности
    vt = str(data.get("vehicle_type", ""))
    et = str(data.get("engine_type", ""))
    is_jur = bool(data.get("is_jur", False))

    need_hp = False
    try:
        if vt == VehicleTypeChoices.MOTORCYCLE:
            need_hp = True
        elif et == EngineTypeChoices.ELECTRO and vt in {VehicleTypeChoices.CAR, VehicleTypeChoices.MOTORCYCLE}:
            need_hp = True
        elif vt == VehicleTypeChoices.CAR and is_jur and (
                et in {EngineTypeChoices.BENZIN, EngineTypeChoices.DIESEL, EngineTypeChoices.HYBRID_PARALLEL,
                       EngineTypeChoices.HYBRID_SERIES}
        ):
            need_hp = True
    except Exception:
        # На всякий случай не ломаем поток
        need_hp = False

    header2 = format_selection_header({**data, "engine_cc": value})
    if need_hp:
        prompt_text = header2 + PROMPT_ENTER_ENGINE_HP
        if chat_id and msg_id:
            await _edit_or_send(None, prompt_text, bot=message.bot, chat_id=chat_id, message_id=msg_id)
        else:
            await _edit_or_send(message, prompt_text)
        await state.set_state(CalculatorState.ENGINE_HP)
        return

    # Иначе — сразу к возрасту
    if chat_id and msg_id:
        prompt_text = header2 + PROMPT_CHOOSE_AGE
        await _edit_or_send(None, prompt_text, reply_markup=age_key_kb(), bot=message.bot, chat_id=chat_id,
                            message_id=msg_id)
    else:
        await _edit_or_send(message, header2)
        await _edit_or_send(message, PROMPT_CHOOSE_AGE, reply_markup=age_key_kb())
    await state.set_state(CalculatorState.AGE_KEY)


@router.callback_query(CalculatorState.HYBRID_ICE_FUEL, HybridFuelCD.filter())
async def choose_hybrid_fuel(call: CallbackQuery, state: FSMContext, callback_data: HybridFuelCD) -> None:
    # Сохраняем топливо ДВС в гибриде и спрашиваем про "ДВС > ЭД?"
    await state.update_data(hybrid_ice_fuel=callback_data.fuel)
    data = await state.get_data()
    header = format_selection_header(data)
    msg = await _edit_or_send(call.message, header + PROMPT_CHOOSE_DVS_GT_ED, reply_markup=yes_no_kb())
    await state.update_data(prompt_chat_id=msg.chat.id, prompt_message_id=msg.message_id)
    await call.answer()
    await state.set_state(CalculatorState.HYBRID_DVS_GT_ED)


@router.callback_query(CalculatorState.HYBRID_DVS_GT_ED, YesNoCD.filter())
async def choose_hybrid_dvs_vs_ed(call: CallbackQuery, state: FSMContext, callback_data: YesNoCD) -> None:
    # Сохраняем булев флаг и переходим к вводу объёма двигателя
    val = True if callback_data.val == "yes" else False
    await state.update_data(dvs_gt_electric=val)
    data = await state.get_data()
    header = format_selection_header(data)
    msg = await _edit_or_send(call.message, header + PROMPT_ENTER_ENGINE_CC)
    await state.update_data(prompt_chat_id=msg.chat.id, prompt_message_id=msg.message_id)
    await call.answer()
    await state.set_state(CalculatorState.ENGINE_CC)


@router.message(CalculatorState.ENGINE_HP, F.text)
async def input_engine_hp(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    chat_id = data.get("prompt_chat_id")
    msg_id = data.get("prompt_message_id")

    raw = (message.text or "").strip()
    try:
        await message.delete()
    except Exception:
        pass

    value = parse_int_amount(raw)
    if value is None:
        reason = build_number_error(raw, what="мощность (л.с.)")
        header = format_selection_header(data)
        error_summary = header + f"<b>— Мощность: ❌ ОШИБКА</b>\n{reason}\n\n{PROMPT_ENTER_ENGINE_HP}"
        if chat_id and msg_id:
            await _edit_or_send(None, error_summary, bot=message.bot, chat_id=chat_id, message_id=msg_id)
        else:
            await _edit_or_send(message, error_summary)
        return

    # Сохраняем и переходим к возрасту
    await state.update_data(hp=value)
    data2 = await state.get_data()
    header2 = format_selection_header(data2)
    if chat_id and msg_id:
        prompt_text = header2 + PROMPT_CHOOSE_AGE
        await _edit_or_send(None, prompt_text, reply_markup=age_key_kb(), bot=message.bot, chat_id=chat_id,
                            message_id=msg_id)
    else:
        await _edit_or_send(message, header2)
        await _edit_or_send(message, PROMPT_CHOOSE_AGE, reply_markup=age_key_kb())
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
    """
В 
services.py
акциз считается на основе hp только для коммерческого использования/юрлиц:
см. 
_calc_accise(self, hp, is_commercial, engine_type, ...)
.
Для ФЛ (personal) акциз = 0, и hp не влияет на результат. Поэтому hp=0 безопасен для большинства персональных сценариев.
Для коммерческих сценариев без запроса мощности результат по акцизу может отличаться от реального. Правильнее будет добавить шаг ввода мощности в визард.
Предложение на будущее (без внедрения сейчас)
Добавить шаг ввода мощности:
Показывать шаг только если is_jur == True или is_personal_use == False.
Для гибридов/электро — обсудить ввод dvs_hp/electric_hp или упрощённую стратегию.
Пока временно оставляем hp=0 как разумный дефолт.
"""
    payload = {
        "price": float(price),
        "currency": str(data.get("currency", "RUB")),
        "engine_cc": int(engine_cc),
        "hp": int(data.get("hp", 0)),
        "engine_type": str(data.get("engine_type", "")),
        "age_key": str(callback_data.key),
        "is_jur": bool(data.get("is_jur", False)),
        "is_personal_use": data.get("is_personal_use", None),
        "vehicle_type": str(data.get("vehicle_type", "car")),
        # гибридные уточнения (если были заданы)
        "hybrid_ice_fuel": data.get("hybrid_ice_fuel"),
        "dvs_gt_electric": data.get("dvs_gt_electric"),
    }
    try:
        # Используем новый калькулятор v6 напрямую
        _text_unused, rates, subtotal_customs, result_data = await sync_to_async(_estimate_v6_sync)(payload)
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
            fx_line = f"\n<i>Расчёты произведены на актуальном курсе: <b>1 {cur_code} = {rub_per_cur:.4f} ₽</b></i>\n"
    except Exception:
        fx_line = ""

    # Комиссия брокера (Settings) и построение единого блока результата в RUB
    try:
        commission_rub = await sync_to_async(_get_company_commission_rub)()
    except Exception:
        commission_rub = 0.0

    result_block = format_result_block_rub_only(result_data, commission_rub=commission_rub)

    # Используем весь state (включая hp и гибридные поля) + принудительно актуальный engine_cc
    header = format_selection_header({**data, "engine_cc": engine_cc}, age_title=age_title)

    final_text = header + result_block + fx_line + CONTACT_LINE

    # Сохраняем данные расчета для возможной заявки и историю в БД
    # Расширим параметры для сохранения (для удобства админки)
    params_for_log = {
        **payload,
        "importer_kind": str(data.get("importer_kind", "")),
        "vehicle_title": vehicle_title,
        "currency_title": currency_title,
    }
    await state.update_data(
        calculation_params=params_for_log,
        calculation_result=result_data,
        calculation_created_at=datetime.datetime.now().isoformat(),
    )

    # Пишем CalculationLog, если знаем пользователя
    try:
        if call.from_user is not None:
            try:
                user = await User.objects.aget(telegram_id=call.from_user.id)
            except User.DoesNotExist:
                user = None
            if user is not None:
                await CalculationLog.objects.acreate(
                    user=user,
                    params=params_for_log,
                    result=result_data,
                )
    except Exception:
        # Не блокируем UX при ошибке записи истории
        pass

    await _edit_or_send(call.message, final_text, reply_markup=lead_after_calc_kb())
    await call.answer()
    # НЕ сбрасываем состояние - оставляем данные для заявки


@router.callback_query(F.data == "calc:restart")
async def restart_calculation(call: CallbackQuery, state: FSMContext) -> None:
    """Перезапуск расчета с сохранением предыдущих данных."""
    await call.answer()

    # Сохраняем текущие данные расчета как предыдущие (если есть)
    current_data = await state.get_data()
    if current_data.get('calculation_params'):
        await state.update_data(
            previous_calculation_params=current_data.get('calculation_params'),
            previous_calculation_result=current_data.get('calculation_result'),
            previous_calculation_created_at=current_data.get('calculation_created_at')
        )

    # Очищаем текущие данные расчета, но оставляем предыдущие
    calculation_keys_to_clear = [
        'vehicle_type', 'currency', 'price', 'importer_kind', 'engine_type',
        'engine_cc', 'hp', 'age_key', 'is_jur', 'is_personal_use', 'vehicle_title',
        'currency_title', 'prompt_chat_id', 'prompt_message_id',
        'calculation_params', 'calculation_result', 'calculation_created_at',
        # гибридные уточнения
        'hybrid_ice_fuel', 'dvs_gt_electric'
    ]

    for key in calculation_keys_to_clear:
        current_data.pop(key, None)

    await state.set_data(current_data)

    # Запускаем новый расчет - отправляем НОВОЕ сообщение
    from bot.utils.strings import PROMPT_CHOOSE_VEHICLE_TYPE
    await state.set_state(CalculatorState.VEHICLE_TYPE)
    await call.message.answer(
        PROMPT_CHOOSE_VEHICLE_TYPE,
        reply_markup=vehicle_type_kb()
    )
