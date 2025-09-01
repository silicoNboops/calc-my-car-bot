# V5 → API Mapping

Документ фиксирует соответствие каноничных правил V5 (см. `calculator/customs_calculator_v5.py`) моделям и сервисам API,
а также правила сидирования фикстур и запуск тестов.

## Область действия

- Только логика V5 (без флагов совместимости).
- Источники данных: фикстуры в `api/calculator/fixtures/`, сидер
  `api/calculator/management/commands/seed_customs_rates.py`.
- Расчёт: `api/calculator/services.py` (`CustomsCalculator` и вспомогательные методы).

## Модели и соответствие

- **`Settings`**: `vat_rate`, `company_commission_rub`, `util_base`.
    - V5: `VAT_RATE` → `vat_rate` (по умолчанию 0.2).
    - V5: `UTIL_BASE` → `util_base` (20000.0). Для неавто используется множитель, см. Util ниже.
- **`DutyRate`**: поля `audience`, `age_group`, `unit`, `max_value`, `rate_percent`, `rate_eur_cc`, `min_rate_eur_cc`,
  `rate_eur_hp`, `min_rate_eur_hp`.
    - V5-таблицы: легковые (физ/юр, бензин/дизель), мото, квадроциклы, снегоходы.
    - Возрастные группы V5 соответствуют `AgeGroup`/`AgeKey`:
        - ФЛ авто: `UNDER_3`, `FROM_3_TO_5`, `OVER_5`.
        - ЮЛ авто: `UNDER_3`, `FROM_3_TO_5`, `FROM_5_TO_7`, `OVER_7`.
- **`UtilFee`**: `kind`, `max_cc`, `coeff`.
    - V5 виды: `personal_new`, `personal_old`, `commercial_under_3`, `commercial_over_3`.
    - Для V5 персональных авто используем единственную запись с `max_cc = null` (детерминированный выбор).
- **`AcciseRate`**: `max_hp`, `rate_rub_per_hp` (прогрессивная шкала).
    - Используется для EV всегда; для прочих — только коммерция/юр.
- **`CustomsFee`**: `max_value_rub`, `fee_rub` (ПП РФ №1637; напр. 4269 руб для 450k–1.2m).

## Расчёт в сервисе (`api/calculator/services.py`)

- **Пошлина (duty)**: методы `_calc_duty`, `_calc_duty_quad`, `_calc_duty_snowmobile`, `_calc_duty_motorcycle`.
    - Легковые, ФЛ (`VehicleType.CAR`, `is_jur=False`):
        - `UNDER_3`: процент от цены (EUR) с минимумом в €/см³; брекеты по цене → `DutyUnit.VALUE` + `min_rate_eur_cc`.
        - `FROM_3_TO_5`, `OVER_5`: фикс €/см³; брекеты по объёму → `DutyUnit.EUR_CC`.
        - EV: всегда 15% от цены в EUR (без min €/см³). Гибриды считаются как ДВС по ETS.
    - Легковые, ЮЛ (`is_jur=True`):
        - EV: 15% от цены в EUR.
        - Гибриды: считаются как бензин (`Audience.PASSENGER_CAR_JUR_BENZ`).
        - Иное: согласно таблицам ЮЛ бензин/дизель; используются `PERCENT` (с `min_rate_eur_cc`) либо `EUR_CC`.
    - Квадро/снего (ФЛ/ЮЛ): используются `EUR_HP`/`PERCENT_HP` с `min_rate_eur_hp` согласно возрасту.
    - Мотоциклы: аналогично — ФЛ микс `PERCENT`+min €/см³ (младшие возрастные), далее `EUR_CC`; ЮЛ — по проценту или
      €/см³ в зависимости от возраста.

- **Утилизационный сбор (util)**: метод `_calc_util`.
    - `util_base`: из `Settings.util_base` (fallback 20000.0).
    - Персональные авто (ФЛ): берётся запись `UtilFee` с `kind=personal_new|personal_old` и `max_cc IS NULL`, `coeff`
      умножается на `util_base`.
    - Коммерческие авто (ICE): по брекетам `UtilFee` (`commercial_under_3|commercial_over_3`) и `max_cc` →
      `coeff * util_base`.
    - EV/Hybrid коммерческие авто: фикс коэффициенты V5 — 1.42 (новые), 2.84 (старше).
    - Неавто (quad/snowmobile/motorcycle): коэффициенты V5 — 1.63 (новые), 6.1 (старше), но база в V5 — 172500. В API
      сохраняем `util_base=20000` и применяем множитель `8.625` (172500/20000) к базовой сумме для эквивалентности.

- **Акциз (accise)**: метод `_calc_accise`.
    - EV: акциз считается ВСЕГДА по прогрессивной шкале `AcciseRate` (руб/л.с.).
    - Прочие типы: акциз только для коммерции/юр (для личного использования — 0).
    - Гибриды: мощность для акциза —
        - Серийный: `dvs_hp + electric_hp`.
        - Параллельный: `dvs_hp`, иначе `0.65 * hp`.

- **НДС (VAT)**: метод `_calc_vat` — только для коммерции/юр: `(price_rub + duty_rub + accise_rub) * vat_rate`.

- **Таможенный сбор**: метод `_calc_customs_fee` — по таблице `CustomsFee` (брекеты по цене в рублях).

## Фикстуры и сидирование

- V5 фикстура: `api/calculator/fixtures/customs_rates_v5_2025_08_17.json`.
    - Содержит секции: `settings` (в т.ч. `util_base`), `duty_rates`, `util_fees`, `accise_rates`, `customs_fees`.
    - Типы/ключи строго соответствуют полям моделей.
- Команда: `manage.py seed_customs_rates`.
    - Production safety: в `ENVIRONMENT=production` требуется `--version-tag`.
    - Объединение нескольких JSON: для `settings` действует «last-file-wins».
    - Dedup:
        - `util_fees`: по ключу `(kind, max_cc)`, стабильная сортировка перед `bulk_create`.
        - `customs_fees`: по `max_value_rub`, вставка по возрастанию; «last-file-wins» гарантирует актуальные ставки (
          напр. 4269 руб для 450k–1.2m).
    - Поддержка `util_base` при создании `Settings` (см. правки в сидере).

### Примеры запуска сидирования

- Локально (dry-run, затем применить):

```bash
ENVIRONMENT=local python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag 2025_08_17 --dry-run
ENVIRONMENT=local python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag 2025_08_17 --replace
```

- Через Docker Compose (пример):

```bash
ENVIRONMENT=local docker compose run --rm api \
  python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag 2025_08_17 --replace
```

- Makefile (prod-safe цели см. `Makefile` цели `seed.rates.*`).

## Тесты и проверка

- Запуск тестов (Docker + Postgres + фиксированный провайдер валют):

```bash
make test-pg-docker  # устанавливает USE_FIXED_CURRENCY_PROVIDER=1
```

- Быстрые локальные тесты (SQLite in-memory):

```bash
make test-sqlite
```

- Примеры проверок V5 (см. `tests/unit/test_v5_ev_rules.py`):
    - EV ФЛ, старше 3 лет: duty = 15% от EUR-цены; VAT=0; акциз > 0 по шкале `AcciseRate`.
    - EV ЮЛ: duty = 15%; акциз по шкале (не 0).

## Версионирование

- Версия фикстуры V5: `2025_08_17` (см. имя файла и `--version-tag`).
- При обновлении ставок добавлять новый файл фикстуры с новой датой/тегом и повторять сидирование.
