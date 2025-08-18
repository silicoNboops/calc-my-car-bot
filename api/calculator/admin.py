from __future__ import annotations

from django.contrib import admin

from api.calculator.models import (
    AcciseRate,
    CustomsFee,
    DutyRate,
    Settings,
    UtilFee,
)


@admin.register(DutyRate)
class DutyRateAdmin(admin.ModelAdmin):
    list_display = (
        "audience",
        "age_group",
        "unit",
        "max_value",
        "rate_percent",
        "rate_eur_cc",
        "min_rate_eur_cc",
        "rate_eur_hp",
        "min_rate_eur_hp",
    )
    list_filter = ("audience", "age_group", "unit")
    search_fields = ("audience", "age_group", "unit")
    ordering = ("audience", "age_group", "unit", "max_value")
    list_per_page = 50


@admin.register(UtilFee)
class UtilFeeAdmin(admin.ModelAdmin):
    list_display = ("kind", "max_cc", "coeff")
    list_filter = ("kind",)
    search_fields = ("kind",)
    ordering = ("kind", "max_cc")
    list_per_page = 50


@admin.register(AcciseRate)
class AcciseRateAdmin(admin.ModelAdmin):
    list_display = ("max_hp", "rate_rub_per_hp")
    ordering = ("max_hp",)
    list_per_page = 50


@admin.register(CustomsFee)
class CustomsFeeAdmin(admin.ModelAdmin):
    list_display = ("max_value_rub", "fee_rub")
    ordering = ("max_value_rub",)
    list_per_page = 50


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ("vat_rate", "company_commission_rub", "util_base", "updated_at")
    readonly_fields = ("updated_at",)
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)
    list_per_page = 50
