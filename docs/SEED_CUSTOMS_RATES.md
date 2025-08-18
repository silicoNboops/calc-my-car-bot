# Загрузка ставок из JSON (seed_customs_rates)

Команда: `python manage.py seed_customs_rates [--path <dir>] [--replace] [--dry-run] [--version-tag <tag>]`

- `--path` — директория с JSON-фикстурами (по умолчанию: `api/calculator/fixtures`).
- `--replace` — предварительно очищает таблицы перед загрузкой.
- `--dry-run` — валидация и сводка без записи в БД.
- `--version-tag` — строковый тег, по которому фильтруются файлы (часть имени файла).

## Ограничение в production

В окружении `ENVIRONMENT=production|prod` команда требует указать `--version-tag`, иначе завершится с ошибкой. Это защищает от случайной загрузки шаблонных фикстур.

Пример:
```bash
# корректно (production)
ENVIRONMENT=production python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag 2025_08_16

# упадёт (нет --version-tag)
ENVIRONMENT=production python manage.py seed_customs_rates --path api/calculator/fixtures
```

Вариант через Docker:
```bash
docker compose exec \
  -e ENVIRONMENT=production \
  api python manage.py seed_customs_rates \
  --path api/calculator/fixtures \
  --version-tag 2025_08_16
```

## Поддержка V4 единиц измерения (HP)

Команда поддерживает загрузку новых полей для V4 не‑авто ставок в модели `DutyRate`:
- `rate_eur_hp`
- `min_rate_eur_hp`

Также поддерживаются новые единицы измерения: `EUR_HP`, `PERCENT_HP`.

## Использование в тестах

Для детерминированных тестов ставки загружаются через фикстуру pytest (один раз на сессию):

```python
@pytest.fixture(autouse=True, scope="session")
def _seed_customs_rates(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("seed_customs_rates", "--replace", "--path", "api/calculator/fixtures")
```

Например, `tests/unit/test_v4_non_car_duty.py` использует такую фикстуру для ставок V4 не‑авто.

## Формат JSON

Ожидается объединяемая структура (ключи опциональны, кроме массивов, которые могут быть пустыми):
```json
{
  "settings": {
    "vat_rate": 0.2,
    "company_commission_rub": 69000.0
  },
  "duty_rates": [ ... ],
  "util_fees": [ ... ],
  "accise_rates": [ ... ],
  "customs_fees": [ ... ]
}
```

Поздние файлы переопределяют ранние. Если передан `--replace`, таблицы очищаются перед загрузкой. Настройки (`Settings`) создаются одной актуальной записью.
