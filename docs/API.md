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

### Примечания по версиям калькулятора (v3/v4)

- Текущая референсная версия логики — v3. Интеграция v4 ведётся поэтапно под фича-флагом `V4_CALC_ENABLED` (ENV).
- Таможенный сбор всегда рассчитывается по таблице `CustomsFee` (ПП РФ №1637) вне зависимости от статуса ФЛ/ЮЛ.
- Акциз начисляется только для легковых авто (`vehicle_type == "car"`). Для `quad`/`snowmobile`/`motorcycle` акциз = 0.
- Утильсбор соответствует ранее принятой схеме: база берётся из `Settings.util_base`, для не-легковых применяется множитель 8.625 и коэффициенты согласно текущим правилам.

См. также:

- [Сопоставление v3 → API](V3_TO_API_MAPPING.md)
- [Отличия v4 → API (дельта к v3)](V4_TO_API_MAPPING.md)

### Провайдер валют

Провайдер валют выбирается фабрикой `get_default_currency_provider()` (см. `api/calculator/services.py`). Конфигурация:

- `USE_FIXED_CURRENCY_PROVIDER=true` — включает фиксированные курсы (для CI/оффлайн).
- Иначе используется провайдер ЦБ РФ с параметрами из Django settings:
  - `CBR_URL`
  - `CBR_CACHE_TTL`

Подробнее см. `docs/CURRENCY_PROVIDER.md`.
