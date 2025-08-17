# API

## Расчёт таможенных платежей

- Путь: `POST /api/v1/calc/estimate`
- Реализация: `api/calculator/views.py` → `EstimateView`
- DRF роутер/namespace: `calculator`, `name="estimate"`
- Тело запроса (см. `EstimateRequestSerializer`):
  - `price: float`
  - `currency: EUR|USD|RUB|CNY|JPY|KRW`
  - `engine_cc: int`
  - `hp: int`
  - `engine_type: string` (например, `Бензин`|`Дизель`)
  - `age_key: under_3|3_to_5|5_to_7|over_7|over_5`
  - `is_jur: bool`
  - `is_personal_use: bool`
- Ответ (см. `EstimateResponseSerializer`).

Примечание: провайдер валют выбирается фабрикой `get_default_currency_provider()` (см. `api/calculator/services.py`). Конфигурация провайдера описана в `docs/CURRENCY_PROVIDER.md`.
