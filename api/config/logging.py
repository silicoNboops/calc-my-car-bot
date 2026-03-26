from __future__ import annotations

import logging.config
from os import getenv

LOG_LEVEL = getenv("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(asctime)s %(log_color)s%(levelname)s %(name)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "colored",
        },
        "telegram": {
            "class": "api.config.telegram_log_handler.TelegramHandler",
            "level": "ERROR",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "telegram"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
    },
}

logging.config.dictConfig(LOGGING)
