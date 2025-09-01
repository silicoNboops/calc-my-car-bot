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
	docker compose run --rm celery celery -A tasks.app call tasks.daily.send_daily_rates

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
seed.rates.dryrun.prod:
	ENVIRONMENT=production python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag legacy --dry-run
	ENVIRONMENT=production python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag 2025_08_17 --dry-run

seed.rates.prod:
	ENVIRONMENT=production python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag legacy --replace
	ENVIRONMENT=production python manage.py seed_customs_rates --path api/calculator/fixtures --version-tag 2025_08_17

# Quick check of seeded rows
check.rates:
	python manage.py shell -c "from api.calculator.models import DutyRate, UtilFee, AcciseRate, CustomsFee, Settings; \
	print('DutyRate', DutyRate.objects.count()); \
	print('UtilFee', UtilFee.objects.count()); \
	print('AcciseRate', AcciseRate.objects.count()); \
	print('CustomsFee', CustomsFee.objects.count()); \
	print('Settings', Settings.objects.count())"

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

test:
	python -m pytest

# Run tests with in-memory SQLite (no Postgres required)
test-sqlite:
	USE_TEST_DB=1 TEST_DATABASE_URL=sqlite://:memory: python -m pytest -q

# Same as test-sqlite but with coverage thresholds from pyproject
test-sqlite-cov:
	USE_TEST_DB=1 TEST_DATABASE_URL=sqlite://:memory: python -m pytest

mypy:
	python -m mypy .
