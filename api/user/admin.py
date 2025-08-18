from __future__ import annotations

from typing import Any

from django.contrib import admin

from api.common.admin import export_as_csv, export_as_json
from api.user.models import User


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
