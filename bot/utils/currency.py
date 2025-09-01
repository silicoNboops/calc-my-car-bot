from __future__ import annotations

from api.calculator.choices import Currency

# Человекочитаемые названия валют (RU)
CURRENCY_TITLES_RU: dict[str, str] = {
    "CNY": "Юань",
    "JPY": "Иена",
    "KRW": "Вона",
    "USD": "Доллар",
    "EUR": "Евро",
    "RUB": "Рубль",
}

# Эмодзи-флаги для валют
CURRENCY_FLAGS: dict[str, str] = {
    "CNY": "🇨🇳",
    "JPY": "🇯🇵",
    "KRW": "🇰🇷",
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "RUB": "🇷🇺",
}


def get_currency_flag(code: str) -> str:
    """Возвращает эмодзи-флаг для кода валюты или пустую строку."""
    return CURRENCY_FLAGS.get(code, "")


def format_currency_title(code: str) -> str:
    """Формирует подпись валюты с флагом для UI/сообщений."""
    title = CURRENCY_TITLES_RU.get(code, dict(Currency.choices).get(code, code))
    flag = get_currency_flag(code)
    return f"{flag} {title}".strip()
