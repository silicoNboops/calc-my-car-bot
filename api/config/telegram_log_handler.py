"""
Telegram logging handler — sends ERROR/CRITICAL logs to admin Telegram chats.
Requires env vars: TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_IDS (comma-separated).
"""

import json
import logging
import os
import threading
import time
import traceback
import urllib.request
import urllib.error

PROJECT_NAME = "calc-my-car-bot"
COOLDOWN_SECONDS = 30


class TelegramHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._token = os.environ.get("TELEGRAM_BOT_TOKEN", os.environ.get("TELEGRAM_API_TOKEN", ""))
        self._admin_ids = [
            x.strip()
            for x in os.environ.get("TELEGRAM_ADMIN_IDS", "").split(",")
            if x.strip()
        ]
        self._cooldowns: dict[str, float] = {}
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        if not self._token or not self._admin_ids:
            return

        try:
            key = f"{record.pathname}:{record.lineno}:{record.msg}"
            now = time.time()
            with self._lock:
                if now - self._cooldowns.get(key, 0) < COOLDOWN_SECONDS:
                    return
                self._cooldowns[key] = now

            text = self._format_message(record)
            for chat_id in self._admin_ids:
                self._send(chat_id, text)
        except Exception:
            self.handleError(record)

    def _format_message(self, record: logging.LogRecord) -> str:
        tb = ""
        if record.exc_info and record.exc_info[2]:
            tb = "\n".join(traceback.format_exception(*record.exc_info))
            if len(tb) > 2000:
                tb = tb[:800] + "\n...\n" + tb[-800:]

        parts = [
            f"🔴 <b>[{PROJECT_NAME}]</b> {record.levelname}",
            f"<b>{record.getMessage()}</b>",
            f"📍 {record.pathname}:{record.lineno}",
        ]
        if tb:
            parts.append(f"<pre>{self._escape_html(tb)}</pre>")

        return "\n".join(parts)

    def _send(self, chat_id: str, text: str) -> None:
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        data = json.dumps({
            "chat_id": chat_id,
            "text": text[:4000],
            "parse_mode": "HTML",
            "disable_notification": False,
        }).encode()
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
        except urllib.error.URLError:
            pass

    @staticmethod
    def _escape_html(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
