from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    telegram_id = models.BigIntegerField(
        null=True, blank=True, unique=True, db_index=True
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"


class Lead(models.Model):
    """Модель для заявок пользователей."""
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='leads',
        verbose_name="Пользователь"
    )
    name = models.CharField(max_length=100, verbose_name="Имя")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    
    # Данные расчета (если заявка оставлена после расчета)
    calculation_data = models.JSONField(
        null=True, 
        blank=True, 
        verbose_name="Данные расчета",
        help_text="JSON с параметрами и результатами расчета"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    is_processed = models.BooleanField(default=False, verbose_name="Обработана")
    notes = models.TextField(blank=True, verbose_name="Заметки менеджера")
    
    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        return f"Заявка от {self.name} ({self.phone}) - {self.created_at.strftime('%d.%m.%Y %H:%M')}"