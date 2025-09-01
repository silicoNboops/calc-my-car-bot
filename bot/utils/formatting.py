from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from bot.keyboards.calculator import (
    format_engine_type_title,
    format_importer_kind_title,
    format_vehicle_title,
)
from bot.utils.currency import (
    get_currency_flag,
    format_currency_title,
)

RATES_ORDER: tuple[str, ...] = ("EUR", "USD", "CNY", "KRW", "JPY")
PRECISION_BY_CODE: dict[str, int] = {
    "JPY": 6,
}


def format_amount(value: int) -> str:
    """Форматирует целое число с пробелами как разделителями тысяч.
    Пример: 1200000 -> "1 200 000"
    """
    return f"{value:,}".replace(",", " ")


def fmt_money(value: float) -> str:
    """Локализованный формат денежных сумм: пробелы для тысяч, запятая как десятичный разделитель.
    Пример: 12345.6 -> "12 345,60"
    """
    s = f"{value:,.2f}"
    s = s.replace(",", " ")
    s = s.replace(".", ",")
    return s


def _build_rates_header(date_str: str) -> str:
    """Строит заголовок курсов валют.

    Формат: "<b>Курсы валют на <u>DD/MM/YYYY</u> (<i>ЦБ РФ</i>):</b>"
    """
    return f"<b>Курсы валют на <u>{date_str}</u> (<i>ЦБ РФ</i>):</b>"


def format_rates_message(rates: dict[str, float]) -> str:
    """Строит сообщение с курсами валют.

    Правила форматирования:
    - Заголовок: дата подчёркнута, весь заголовок жирный, пометка (ЦБ РФ) — курсивом.
    - Строки: "<флаг> CODE => <b>VALUE</b>".
    - Точность: JPY — 6 знаков, для остальных — 4.
    - Никаких суффиксов RUB в конце.
    """
    today = datetime.now().strftime("%d/%m/%Y")
    header = _build_rates_header(today)
    lines: list[str] = [header, ""]  # пустая строка после заголовка
    for code in RATES_ORDER:
        try:
            v = float(rates.get(code, 0.0))
        except Exception:
            v = 0.0
        if not v:
            continue
        flag = get_currency_flag(code)
        precision = PRECISION_BY_CODE.get(code, 4)
        lines.append(f"{flag} {code} => <b>{v:.{precision}f}</b>")
    return "\n".join(lines)


def format_selection_header(data: dict, *, age_title: Optional[str] = None) -> str:
    """Строит заголовок выбора для визарда, добавляя только заполненные пункты.

    Ожидаемые ключи:
    - vehicle_type, vehicle_title
    - currency, currency_title
    - price (int)
    - importer_kind
    - engine_type
    - engine_cc (int)
    - age_title (через аргумент)
    """
    lines: list[str] = ["Выбор сделан:"]

    vehicle_type = data.get("vehicle_type")
    vehicle_title = data.get("vehicle_title") or (
        format_vehicle_title(str(vehicle_type)) if vehicle_type else None
    )
    if vehicle_title:
        lines.append(f"— Тип авто: <b>{vehicle_title}</b>")

    currency = data.get("currency")
    currency_title = data.get("currency_title") or (
        format_currency_title(str(currency)) if currency else None
    )
    if currency_title:
        lines.append(f"— Валюта: <b>{currency_title}</b>")

    price = data.get("price")
    if price:
        try:
            price_i = int(price)
            lines.append(f"— Стоимость: <b>💰 {format_amount(price_i)}</b>")
        except Exception:
            pass

    importer_kind = data.get("importer_kind")
    if importer_kind:
        lines.append(
            f"— Кто ввозит: <b>{format_importer_kind_title(str(importer_kind))}</b>"
        )

    engine_type = data.get("engine_type")
    if engine_type:
        lines.append(
            f"— Тип двигателя: <b>{format_engine_type_title(str(engine_type))}</b>"
        )

    engine_cc = data.get("engine_cc")
    if engine_cc:
        try:
            lines.append(f"— Объём: <b>🧱 {format_amount(int(engine_cc))} см³</b>")
        except Exception:
            pass

    if age_title:
        lines.append(f"— Возраст: <b>{age_title}</b>")

    return "\n".join(lines) + "\n\n"


def parse_int_amount(raw: Optional[str]) -> Optional[int]:
    """Парсит положительное целое из строки, допускает пробелы/запятые/точки как разделители тысяч.

    Возвращает None, если пусто/некорректно/<=0.
    """
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    cleaned = re.sub(r"[\s,\.]+", "", s)
    if not cleaned.isdigit():
        return None
    try:
        value = int(cleaned)
    except Exception:
        return None
    if value <= 0:
        return None
    return value


def build_number_error(raw: str, *, what: str) -> str:
    """Строит текст ошибки валидации для числового ввода.

    what — человекочитаемое название поля (например, 'стоимость', 'объём двигателя').
    """
    s = (raw or "").strip()
    if not s:
        return "Ошибка: значение пустое."
    cleaned = re.sub(r"[\s,\.]+", "", s)
    if not cleaned.isdigit():
        return "Ошибка: введите целое число, можно с пробелами/запятыми/точками как разделителями тысяч."
    return f"Ошибка: {what} должна быть > 0."
