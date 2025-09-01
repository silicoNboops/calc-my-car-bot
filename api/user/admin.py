from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.utils.html import format_html

from api.common.admin import export_as_csv, export_as_json
from api.user.models import User, Lead


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    filter_horizontal = ("groups", "user_permissions")

    list_display = (
        "id",
        "telegram_id",
        "username",
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
    )
    search_fields = ("username", "email")
    readonly_fields = ("date_joined", "last_login")
    date_hierarchy = "date_joined"
    ordering = ("-date_joined",)
    list_per_page = 50
    actions = [export_as_csv, export_as_json]

    fieldsets = (
        ("Учётная запись", {"fields": ("telegram_id", "username", "password", "email")}),
        (
            "Права",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Важные даты", {"fields": ("last_login", "date_joined")}),
    )

    def save_model(
            self,
            request: Any,
            obj: User,
            form: None,
            change: bool,  # noqa: FBT001
    ) -> None:
        """Update user password if it is not raw.

        This is needed to hash password when updating user from admin panel.
        """
        has_raw_password = obj.password.startswith("pbkdf2_sha256")
        if not has_raw_password:
            obj.set_password(obj.password)

        super().save_model(request, obj, form, change)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name", 
        "phone",
        "user_link",
        "has_calculation",
        "is_processed",
        "created_at"
    )
    list_filter = (
        "is_processed",
        "created_at",
    )
    search_fields = ("name", "phone", "user__username", "user__telegram_id")
    readonly_fields = ("created_at", "calculation_display")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 50
    actions = [export_as_csv, export_as_json, "mark_as_processed"]
    
    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "phone", "user", "created_at")
        }),
        ("Статус", {
            "fields": ("is_processed", "notes")
        }),
        ("Данные расчета", {
            "fields": ("calculation_display",),
            "classes": ("collapse",)
        }),
    )
    
    def user_link(self, obj):
        if obj.user:
            return format_html(
                '<a href="/admin/user/user/{}/change/">{}</a>',
                obj.user.id,
                obj.user.username or f"ID: {obj.user.telegram_id}"
            )
        return "-"
    user_link.short_description = "Пользователь"
    
    def has_calculation(self, obj):
        return "✅" if obj.calculation_data else "❌"
    has_calculation.short_description = "Есть расчет"
    has_calculation.boolean = True
    
    def calculation_display(self, obj):
        if not obj.calculation_data:
            return "Нет данных расчета"
        
        data = obj.calculation_data
        html = "<div style='font-family: monospace;'>"
        
        # Параметры расчета
        if 'params' in data:
            params = data['params']
            html += "<h4>Параметры расчета:</h4>"
            html += f"<p>Тип ТС: {params.get('vehicle_type', '-')}</p>"
            html += f"<p>Цена: {params.get('price', '-')} {params.get('currency', '')}</p>"
            html += f"<p>Объем двигателя: {params.get('engine_cc', '-')} см³</p>"
            html += f"<p>Тип двигателя: {params.get('engine_type', '-')}</p>"
            html += f"<p>Возраст: {params.get('age_key', '-')}</p>"
            html += f"<p>Импортер: {params.get('importer_kind', '-')}</p>"
        
        # Результаты расчета
        if 'result' in data:
            result = data['result']
            html += "<h4>Результат расчета:</h4>"
            html += f"<p>Итого (RUB): <strong>{result.get('subtotal_customs', '-')}</strong></p>"
            html += f"<p>Пошлина (RUB): {result.get('duty_rub', '-')}</p>"
            html += f"<p>НДС (RUB): {result.get('vat_rub', '-')}</p>"
            html += f"<p>Утильсбор (RUB): {result.get('util_fee', '-')}</p>"
        
        html += "</div>"
        return format_html(html)
    calculation_display.short_description = "Детали расчета"
    
    @admin.action(description="Отметить как обработанные")
    def mark_as_processed(self, request, queryset):
        updated = queryset.update(is_processed=True)
        self.message_user(
            request,
            f"Отмечено как обработанные: {updated} заявок."
        )
