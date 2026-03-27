# calc-my-car-bot

Car import cost calculator with Telegram bot, Celery tasks, and RabbitMQ.

## Stack

- Django, Python, PostgreSQL, PgBouncer, Redis, RabbitMQ 3-alpine, Celery
- Telegram bot: aiogram 3.22 (@china_motors_23_bot)
- Server: Gunicorn (workers=$WORKERS, threads=$THREADS)

## Local commands

```bash
# No make up/down targets — use docker compose directly:
docker compose up -d
docker compose up -d --build
docker compose down

# Inside containers:
make run.server.local    # Django dev server
make run.bot.local       # Telegram bot
make run.celery.local    # Celery worker
make run.celery.beat.local  # Celery beat
make migrate
make collectstatic
make createsuperuser

# Testing:
make test-sqlite         # fast tests (SQLite)
make test-pg-docker      # full tests (PostgreSQL in Docker)
make lint                # ruff + black-check + mypy
make fmt                 # ruff + black formatting

# Manual tasks:
make task.rates          # trigger daily rates send via docker
```

## Production (VPS thorgash.xyz, SSH alias: tg)

```bash
# Deploy: push to main, then on server:
cd /root/calc-my-car-bot && git pull origin main && docker compose up -d --force-recreate

# Logs:
docker compose logs api --tail=50
docker compose logs bot --tail=50
docker compose logs celery --tail=50

# Restart single service:
docker compose restart api
```

- **API:** port 8011 (Gunicorn behind nginx)
- **Admin:** https://thorgash.xyz:8011/admin/

## Key files

- `api/config/settings.py` — Django settings
- `api/config/logging.py` — logging config (console + Telegram handler)
- `api/config/telegram_log_handler.py` — Telegram error alerts
- `api/config/sentry.py` — optional Sentry (USE_SENTRY env)

## Environment

Required in `.env`: `TELEGRAM_API_TOKEN`, `TELEGRAM_ADMIN_IDS`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS`, `API_PORT`

Note: uses `TELEGRAM_API_TOKEN` (not `TELEGRAM_BOT_TOKEN`) — handler checks both.

## Gotchas

- `celery_beat` uses `make run.celery.beat.local` target in prod compose — known issue, works fine
- Celery worker runs with `--pool=solo --concurrency=1` on prod (RAM constrained)
- All containers have `mem_limit` and restart policies
- `collectstatic` service in compose had no `restart: "no"` — fixed 2026-03-26
