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

- Быстрый прогон тестов на SQLite (рекомендуется в Docker):

```bash
# внутри хоста
docker compose exec \
  -e USE_TEST_DB=1 \
  -e TEST_DATABASE_URL=sqlite:///:memory: \
  api pytest -q
```

- Прогон с использованием БД по умолчанию (`DATABASE_URL`):

```bash
docker compose exec api pytest -q
```

- Запуск с отчётом покрытия и настройками из `pyproject.toml` (по умолчанию уже включены):

```bash
docker compose exec \
  -e USE_TEST_DB=1 \
  -e TEST_DATABASE_URL=sqlite:///:memory: \
  api pytest --cov --cov-report=html -vv
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

Добавлен модуль `tests/unit/test_currency_provider.py` для проверки `CbrfCurrencyProvider`:

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
- Эндпоинт расчёта: `api/calculator/views.py` (`name="estimate"`, namespace `calculator`).
