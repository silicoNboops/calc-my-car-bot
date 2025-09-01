from __future__ import annotations

import os
from typing import List

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_admin_ids() -> List[int]:
    """Получает список ID админов из переменной окружения."""
    admin_ids_str = os.getenv("TELEGRAM_ADMIN_IDS", "")
    if not admin_ids_str.strip():
        return []
    
    admin_ids = []
    for admin_id in admin_ids_str.split(","):
        admin_id = admin_id.strip()
        if admin_id.isdigit():
            admin_ids.append(int(admin_id))
    
    return admin_ids


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом."""
    return user_id in get_admin_ids()