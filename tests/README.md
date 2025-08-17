# Тестирование

В репозитории используется pytest + pytest-django.

## Почему и как мы переключаем БД на время тестов

В прод/локале проект может работать на Postgres (через `DATABASE_URL`). В некоторых окружениях Docker/OS могут возникать проблемы с колляциями Postgres при создании тестовой БД (например, "template1 has a collation version mismatch").

Чтобы:
- не плодить отдельные `settings_test.py`,
- не ломать основную конфигурацию,
- и одновременно иметь предсказуемые быстрые тесты,

мы добавили явное переключение БД на время тестов через переменные окружения в `api/config/database.py`:

- `USE_TEST_DB=1` — включает тестовый режим БД;
- `TEST_DATABASE_URL=<url>` — URL тестовой БД (например, `sqlite:///:memory:`).

Если оба ENV заданы, во время запуска тестов берётся `TEST_DATABASE_URL`. В остальных случаях используется обычный `DATABASE_URL` (или дефолт `sqlite:///db.sqlite3`).

## Примеры запуска

- Быстрый smoke-прогон на SQLite in-memory (самый быстрый):

```bash
# внутри хоста
docker compose exec \
  -e USE_TEST_DB=1 \
  -e TEST_DATABASE_URL=sqlite:///:memory: \
  -e USE_FIXED_CURRENCY_PROVIDER=1 \
  api python -m pytest -q
```

- Полный прогон на Postgres (использует переменную `DATABASE_URL`):

```bash
docker compose exec \
  -e DATABASE_URL=postgres://postgres:lolgrec@db:5432/postgres \
  -e USE_FIXED_CURRENCY_PROVIDER=1 \
  api python -m pytest -q
```

Примечания:

- `USE_FIXED_CURRENCY_PROVIDER=1` принудительно включает фиксированный провайдер валют, чтобы тесты были детерминированными и не зависели от сети/ЦБ РФ. Для проверки реального провайдера уберите флаг, но такие прогоны могут быть нестабильными офлайн.
- В smoke-режиме SQLite in-memory даёт максимальную скорость. В Postgres-режиме проверяются миграции, последовательности и колляции.

### Примеры без `USE_FIXED_CURRENCY_PROVIDER=1`

- Postgres (реальный провайдер курсов, нужен доступ в интернет):

```bash
docker compose exec \
  -e DATABASE_URL=postgres://postgres:lolgrec@db:5432/postgres \
  api python -m pytest -q
```

- SQLite in-memory (smoke, реальный провайдер курсов, нужен интернет):

```bash
docker compose exec \
  -e USE_TEST_DB=1 \
  -e TEST_DATABASE_URL=sqlite:///:memory: \
  api python -m pytest -q
```

Замечание: юнит-тесты провайдера (`tests/unit/test_currency_provider.py`) мокают сеть и стабильны в любом режиме; без флага реальные сетевые обращения делает сервис в интеграционных местах (например, при сборке калькулятора).

- Прогон с отчётом покрытия (пример на SQLite in-memory):

```bash
docker compose exec \
  -e USE_TEST_DB=1 \
  -e TEST_DATABASE_URL=sqlite:///:memory: \
  -e USE_FIXED_CURRENCY_PROVIDER=1 \
  api python -m pytest --cov --cov-report=html -vv
```

## Фикстуры данных для расчётов

Тесты калькулятора зависят от ставок таможенных пошлин/сборов. Чтобы эндпоинты не падали на пустых таблицах, в модуле `tests/unit/test_calculator.py` добавлена локальная фикстура (autouse, scope=session), которая один раз на сессию загружает ставки из JSON через management-команду:

```python
# tests/unit/test_calculator.py
@pytest.fixture(autouse=True, scope="session")
def _seed_customs_rates(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("seed_customs_rates", "--replace", "--path", "api/calculator/fixtures")
```

Это локально к модулю тестов и не влияет на остальные тесты. JSON-фикстуры лежат в `api/calculator/fixtures/`.

## Тесты провайдера курсов ЦБ РФ

Добавлен модуль `tests/unit/test_currency_provider.py`<!-- Раздел про конфигурацию провайдера перемещён в docs/CURRENCY_PROVIDER.md -->

- Проверяется корректный разбор ответа ЦБ и использование кэша между вызовами (без повторного HTTP-запроса).
- При отсутствии курса EUR или сетевой ошибке включается безопасный fallback на `FixedCurrencyProvider`.
- Сетевые вызовы замоканы через `unittest.mock.patch` (`requests.get`), кэш Django очищается адресно по ключу `currency_rates_cbrf_v1`.

Запуск только тестов провайдера (в Docker и на SQLite in-memory):

```bash
docker compose exec \
  -e USE_TEST_DB=1 \
  -e TEST_DATABASE_URL=sqlite:///:memory: \
  api pytest -q tests/unit/test_currency_provider.py
```

## Полезное

- Конфигурация pytest: `pyproject.toml` → `[tool.pytest.ini_options]`.
- Основная настройка БД: `api/config/database.py`.
