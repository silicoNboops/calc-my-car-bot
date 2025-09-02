run.bot:
	python -m bot

run.server.local:
	sh ./run-local.sh

run.server.prod:
	python -m gunicorn api.web.wsgi:application \
		--bind 0.0.0.0:80 \
		--workers ${WORKERS} \
		--threads ${THREADS} \
		--timeout 480

run.bot.local:
	python -m bot

run.bot.prod:
	python -m bot

run.celery.local:
	OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES celery -A tasks.app worker --loglevel=DEBUG

run.celery.prod:
	celery -A tasks.app worker --loglevel=INFO

# Celery beat (scheduler)
run.celery.beat.local:
	celery -A tasks.app beat --loglevel=INFO

# Manual trigger for daily rates task (docker env)
task.rates:
	docker compose --env-file .env run --rm \
	  -e TELEGRAM_API_TOKEN \
	  -e TELEGRAM_RATES_CHANNEL \
	  celery celery -A tasks.app call tasks.daily.send_daily_rates

makemigrations:
	python manage.py makemigrations

migrate:
	python manage.py migrate

collectstatic:
	python manage.py collectstatic --no-input

createsuperuser:
	python manage.py createsuperuser --email "" --username admin
	python manage.py init_admin_telegram_id

# Seed customs rates (production-safe)
.PHONY: seed.rates.dryrun.prod seed.rates.prod check.rates test-pg-docker
seed.rates.dryrun.prod:
	docker compose --env-file .env run --rm \
	  -e ENVIRONMENT=production \
	  api python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag legacy --dry-run
	docker compose --env-file .env run --rm \
	  -e ENVIRONMENT=production \
	  api python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag 2025_08_17 --dry-run

seed.rates.prod:
	docker compose --env-file .env run --rm \
	  -e ENVIRONMENT=production \
	  api python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag legacy --replace
	docker compose --env-file .env run --rm \
	  -e ENVIRONMENT=production \
	  api python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag 2025_08_17

# Quick check of seeded rows
check.rates:
	docker compose --env-file .env run --rm \
	  -e ENVIRONMENT=production \
	  api python manage.py shell -c 'from api.calculator.models import DutyRate, UtilFee, AcciseRate, CustomsFee, Settings; print("DutyRate", DutyRate.objects.count()); print("UtilFee", UtilFee.objects.count()); print("AcciseRate", AcciseRate.objects.count()); print("CustomsFee", CustomsFee.objects.count()); print("Settings", Settings.objects.count())'

# Tests, linters & formatters
fmt:
	make -k ruff-fmt black

lint:
	make -k ruff black-check mypy

black:
	python -m black .

black-check:
	python -m black --check .

ruff:
	python -m ruff check .

ruff-fmt:
	python -m ruff --fix-only --unsafe-fixes .

mypy:
	python -m mypy .


# TESTS

# TODO сделать через точки а не дефисы ебаные. упростить
# Run tests with in-memory SQLite (no Postgres required)
test-sqlite:
	USE_TEST_DB=1 TEST_DATABASE_URL=sqlite://:memory: python -m pytest -q

# Same as test-sqlite but with coverage thresholds from pyproject
test-sqlite-cov:
	USE_TEST_DB=1 TEST_DATABASE_URL=sqlite://:memory: python -m pytest

# Run tests against Postgres inside Docker network (connects to service `db`).
# Requires POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB in environment (e.g., via `--env-file .env`).
test-pg:
	USE_TEST_DB=1 \
	TEST_DATABASE_URL=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB} \
	python -m pytest -q

# Same as test-pg but with coverage thresholds from pyproject
test-pg-cov:
	USE_TEST_DB=1 \
	TEST_DATABASE_URL=postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB} \
	python -m pytest

# Host wrapper: run Postgres tests inside Docker Compose network, loading creds from .env
# Usage (from host): `make test-pg-docker`
test-pg-docker:
	docker compose --env-file .env run --rm \
	  -e ENVIRONMENT=local \
	  -e USE_FIXED_CURRENCY_PROVIDER=1 \
	  -e POSTGRES_USER \
	  -e POSTGRES_PASSWORD \
	  -e POSTGRES_DB \
	  api make test-pg
