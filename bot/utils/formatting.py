from __future__ import annotations


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
