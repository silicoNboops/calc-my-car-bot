# Конфигурация провайдера валют

Провайдер курсов валют использует настройки из окружения и прокидывает их в Django settings через модуль `api/config/currency.py`.

- `settings.CBR_URL` — URL источника курсов (по умолчанию: `https://www.cbr-xml-daily.ru/daily_json.js`).
- `settings.CBR_CACHE_TTL` — TTL кэша в секундах (по умолчанию: `3600`).
- `settings.USE_FIXED_CURRENCY_PROVIDER` — если `1`/`true`, принудительно включает фиксированный провайдер (удобно для CI/оффлайна).

Провайдер по умолчанию выбирается фабрикой `get_default_currency_provider()` из `api/calculator/services.py`.

## Как задать ENV

Заполните `.env` (см. `.env.example`):

```env
CBR_URL=https://www.cbr-xml-daily.ru/daily_json.js
CBR_CACHE_TTL=3600
# В CI/оффлайне можно включить фиксированный провайдер:
# USE_FIXED_CURRENCY_PROVIDER=1
```

Docker Compose автоматически подставляет переменные окружения из `.env` в контейнер. При желании можно продублировать:

```yaml
api:
  environment:
    - CBR_URL=${CBR_URL:-https://www.cbr-xml-daily.ru/daily_json.js}
    - CBR_CACHE_TTL=${CBR_CACHE_TTL:-3600}
    # - USE_FIXED_CURRENCY_PROVIDER=${USE_FIXED_CURRENCY_PROVIDER:-}
```

## Где используется

- `api/config/currency.py` — читает ENV и экспортирует в `settings`.
- `api/calculator/services.py` —
  - `CbrfCurrencyProvider` читает `settings.CBR_URL`/`settings.CBR_CACHE_TTL` по умолчанию.
  - `get_default_currency_provider()` читает `settings.USE_FIXED_CURRENCY_PROVIDER`.
- `api/calculator/views.py` и `bot/handlers.py` используют `get_default_currency_provider()`.

## Примеры

Проверка флага фиксированного провайдера:

```bash
docker compose exec \
  -e USE_FIXED_CURRENCY_PROVIDER=1 \
  api python manage.py shell -c "from django.conf import settings; print(settings.USE_FIXED_CURRENCY_PROVIDER)"
```

Запуск только тестов провайдера (на SQLite in-memory):

```bash
docker compose exec \
  -e USE_TEST_DB=1 \
  -e TEST_DATABASE_URL=sqlite:///:memory: \
  api pytest -q tests/unit/test_currency_provider.py
```
