# Сопоставление v3 → API

Краткая матрица соответствия логики Customs Calculator v3 к текущей реализации API и БД.

## Обозначения
- Код API: `api/calculator/services.py`
- Модели/таблицы: `api/calculator/models.py`
- Фикстуры/команды: `api/calculator/management/commands/seed_customs_rates.py`
- Сериализаторы/валидация: `api/calculator/serializers.py`

## Валюты (ЦБ РФ)
- v3: `RatesFetcher` с кэшем, URL ЦБ РФ, fallback-курсы.
- API: `CbrfCurrencyProvider` + `FixedCurrencyProvider`; выбор по `get_default_currency_provider()`.
  - Код: `services.py:CbrfCurrencyProvider.get_rates()`, `get_default_currency_provider()`
  - Настройки: `settings.CBR_URL`, `settings.CBR_CACHE_TTL`, ENV `USE_FIXED_CURRENCY_PROVIDER`

## Пошлина — легковые (ФЛ, ЕТС)
- v3: ЕТС для ФЛ
  - under_3: проценты по цене (EUR) с минимумом €/см³.
  - over_3/over_5: €/см³ по объёму двигателя.
  - EV/Гибриды (льготы ФЛ): under_3 — 15% без минимума; иначе — 1 €/см³.
- API:
  - Код (ФЛ ICE): `services.py:CustomsCalculator._calc_duty()` — сбор строк из БД через `Audience.PASSENGER_CAR_PHYS` и `AgeGroup`, фильтр по `unit` (VALUE для under_3, EUR_CC иначе).
  - Код (ФЛ EV/гибриды): `services.py:estimate()` явные ветки с 15%/1 €/см³.
  - Таблицы: `DutyRate` (AUDIENCE=PASSENGER_CAR_PHYS, AGE_GROUP=UNDER_3/FROM_3_TO_5/OVER_5, UNIT=VALUE/EUR_CC, RATE_PERCENT/MIN_RATE_EUR_CC/RATE_EUR_CC).

## Пошлина — легковые (ЮЛ / коммерция)
- v3: Бензин/Дизель — по ставкам (проценты/минимум/€/см³); EV — 15%; Гибрид — 0.15/0.18 и минимум 0.30/1.20.
- API:
  - Код (ICE): `services.py:_calc_duty()` с `Audience.PASSENGER_CAR_JUR_BENZ|JUR_DIESEL`.
  - Код (EV/Hybrid): `services.py:estimate()` — EV 15%; гибрид new/old с минимумом €/см³.
  - Таблицы: `DutyRate` (AUDIENCE=PASSENGER_CAR_JUR_BENZ|_DIESEL, AGE_GROUP=UNDER_3/FROM_3_TO_5/FROM_5_TO_7/OVER_7, UNIT=PERCENT/EUR_CC, RATE_PERCENT/MIN_RATE_EUR_CC/RATE_EUR_CC).

## Пошлина — квадроциклы/мотовездеходы
- v3: new 30%, old 35%, минимум 1.2/1.5 €/см³.
- API: `services.py:estimate()` ветка `vehicle_type=="quad"` — `max(price_eur*rate, cc*min_eur_cc)`.

## Пошлина — снегоходы
- v3: 5% без минимума.
- API: `services.py:estimate()` ветка `vehicle_type=="snowmobile"` — `price_eur * 0.05`.

## Пошлина — мотоциклы
- v3: 15% + минимум €/см³: 0.5 (ФЛ персонал) / 0.8 (коммерция/ЮЛ).
- API: `services.py:estimate()` ветка `vehicle_type=="motorcycle"` — выбор минимума по `is_jur`/`is_personal_use`.

## Утилизационный сбор
- v3: базовые ставки: car=20000, quad/snowmobile/motorcycle=172500; коэффициенты:
  - ФЛ (personal): для `car` фикс суммы (через коэффициенты), прочие ТС — 1.63/6.1.
  - Коммерция: `car` ICE — по объёму; `car` EV/Hybrid — 1.42/2.84; прочие ТС — 1.63/6.1.
- API:
  - База: `Settings.util_base`, по умолчанию 20000.
  - Не-`car`: множитель `8.625` (эквивалент 172500/20000).
  - Код: `services.py:CustomsCalculator._calc_util()` — ветки для ФЛ/коммерции, EV/Hybrid, ICE, и не-`car`.
  - Таблица: `UtilFee` (kinds: `personal_new`, `personal_old`, `commercial_under_3`, `commercial_over_3`).

## Акциз (НК РФ ст. 193)
- v3: только `VehicleType.CAR`; мощность:
  - EV — вся, гибрид последовательный — сумма ДВС+электро, гибрид параллельный — только ДВС (или 65% при отсутствии), ICE — вся.
  - Ставка: по брекетам мощности, применяется ко всей мощности (flat по диапазону).
- API:
  - Коммерческий режим: применяется только для коммерции/ЮЛ.
  - Код: `services.py:CustomsCalculator._calc_accise()` — ранний выход для некоммерции; выбор мощности как в v3; ставка из БД.
  - Таблица: `AcciseRate` (max_hp, rate_rub_per_hp).

## НДС
- v3: 20%; база с учётом акциза.
- API: только для коммерции/ЮЛ; база = `price_rub + duty_rub + accise_rub`.
  - Код: `services.py:_calc_vat()`; ставка из `Settings.vat_rate` (по умолчанию 0.20).

## Таможенный сбор (ПП РФ №1637)
- v3: таблица по стоимости в рублях.
- API: из БД `CustomsFee` по брекетам `max_value_rub`.
  - Код: `services.py:_calc_customs_fee()`.
  - Таблица: `CustomsFee` (max_value_rub, fee_rub).

## Определение коммерческого режима
- v3: различает ФЛ личное/перепродажа и ЮЛ.
- API: `is_commercial = is_jur or (is_personal_use is False)`.
  - Код: `services.py:estimate()`.

## Сериализация и валидация
- Возрастные ключи нормализуются: `over_7|5_to_7 => over_5` для ФЛ в части ЕТС.
- Запрет EV/гибридов для не-`car`.
- Код: `api/calculator/serializers.py` (валидаторы полей и общая валидация).

## Настройки и окружение
- `Settings.util_base`, `Settings.vat_rate` — драйвят утиль/НДС.
- `settings.CBR_URL`, `settings.CBR_CACHE_TTL` — курсы ЦБ.
- ENV: `USE_FIXED_CURRENCY_PROVIDER` (форсирует фикс-курсы, удобно в CI), `USE_TEST_DB`/`TEST_DATABASE_URL` (SQLite in-memory для тестов).

## Тестовое покрытие (репрезентативные)
- `tests/unit/test_calculator.py`: ЕТС ФЛ, EV/Hybrid ветки, duty min €/см³, прочие ТС.
- `tests/unit/test_util_stage3.py`: коэффициенты утиля для не-`car` и разные режимы.
- `tests/unit/test_currency_provider*.py`: кэширование и fallback курсов ЦБ, флаг фикс-курсов.

## Концептуальное отличие от v3
- Акциз для ФЛ (личное) отключён по продуктовой договорённости; включён только для коммерции/ЮЛ. Остальная логика соответствует v3.
