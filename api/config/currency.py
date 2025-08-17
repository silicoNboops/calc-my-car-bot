from __future__ import annotations

from os import getenv

# Настройки провайдера курсов ЦБ РФ
# Значения по умолчанию дублируют те, что используются в коде как fallback
CBR_URL = getenv("CBR_URL", "https://www.cbr-xml-daily.ru/daily_json.js")
CBR_CACHE_TTL = int(getenv("CBR_CACHE_TTL", "3600"))

# Флаг для CI/оффлайна: форсировать фиксированный провайдер
_USE_FIXED = getenv("USE_FIXED_CURRENCY_PROVIDER", "false").lower()
USE_FIXED_CURRENCY_PROVIDER = _USE_FIXED in ("1", "true", "yes", "on")
