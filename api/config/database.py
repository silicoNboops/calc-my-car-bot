from __future__ import annotations

import logging
from os import getenv

import dj_database_url

logger = logging.getLogger(__name__)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

_default_db_url = "sqlite:///db.sqlite3"
DB_URL = getenv("DATABASE_URL", default=_default_db_url)

# Allow overriding DB during tests by setting both envs:
#   USE_TEST_DB=1 and TEST_DATABASE_URL=<url>
# This is explicit and doesn't depend on pytest internals.
_use_test_db = getenv("USE_TEST_DB") == "1"
_test_db_url = getenv("TEST_DATABASE_URL")
if _use_test_db and _test_db_url:
    logger.info("Using TEST_DATABASE_URL due to USE_TEST_DB=1: '%s'", _test_db_url)
    DB_URL = _test_db_url

if _default_db_url == DB_URL:
    logger.warning("Using default database url: '%s'", DB_URL)

CONN_MAX_AGE = int(getenv("CONN_MAX_AGE", default="600"))
DATABASES = {
    "default": dj_database_url.parse(DB_URL, conn_max_age=CONN_MAX_AGE),
}
