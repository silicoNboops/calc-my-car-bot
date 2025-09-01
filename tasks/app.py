from __future__ import annotations

import os

import django
from celery import Celery

from api.config import celery as config

# Ensure Django is initialized for ORM access in tasks
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.config.settings")
django.setup()

app = Celery("main")
app.config_from_object(config)
app.autodiscover_tasks()
