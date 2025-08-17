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
