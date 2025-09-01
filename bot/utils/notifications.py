from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# Загружаем переменные окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from bot.utils.admin import get_admin_ids

if TYPE_CHECKING:
    from aiogram import Bot
    from api.user.models import Lead

logger = logging.getLogger(__name__)


async def notify_admins_about_new_lead(bot: Bot, lead: Lead) -> None:
    """Отправляет уведомление админам о новой заявке."""
    admin_ids = get_admin_ids()
    
    if not admin_ids:
        logger.warning("Нет настроенных админов для уведомлений")
        return
    
    # Формируем сообщение
    message = (
        "🔔 <b>Новая заявка!</b>\n\n"
        f"📝 <b>ID заявки:</b> #{lead.id}\n"
        f"👤 <b>Имя:</b> {lead.name}\n"
        f"📞 <b>Телефон:</b> {lead.phone}\n"
        f"🕐 <b>Дата:</b> {lead.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )
    
    # Добавляем информацию о пользователе
    if lead.user:
        message += f"👨‍💻 <b>Пользователь:</b> @{lead.user.username or 'без_ника'} (ID: {lead.user.telegram_id})\n"
    
    # Добавляем информацию о расчете если есть
    if lead.calculation_data:
        calc_data = lead.calculation_data
        if 'params' in calc_data:
            params = calc_data['params']
            message += "\n💰 <b>Данные расчета:</b>\n"
            message += f"🚗 Тип ТС: {params.get('vehicle_type', '-')}\n"
            message += f"💵 Цена: {params.get('price', '-')} {params.get('currency', '')}\n"
            message += f"⚙️ Объем: {params.get('engine_cc', '-')} см³\n"
            
            if 'result' in calc_data:
                result = calc_data['result']
                message += f"💸 <b>Итого:</b> {result.get('subtotal_customs', '-')} ₽\n"
    
    message += f"\n🔗 <a href='http://localhost:8011/admin/user/lead/{lead.id}/change/'>Открыть в админке</a>"
    
    # Отправляем всем админам
    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            logger.info(f"Уведомление о заявке #{lead.id} отправлено админу {admin_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")


async def notify_admins_about_error(bot: Bot, error_message: str, user_id: int = None) -> None:
    """Отправляет уведомление админам об ошибке."""
    admin_ids = get_admin_ids()
    
    if not admin_ids:
        return
    
    message = (
        "⚠️ <b>Ошибка в боте</b>\n\n"
        f"📝 <b>Описание:</b> {error_message}\n"
    )
    
    if user_id:
        message += f"👤 <b>Пользователь:</b> {user_id}\n"
    
    message += f"🕐 <b>Время:</b> {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
    
    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об ошибке админу {admin_id}: {e}")