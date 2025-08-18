from __future__ import annotations

from django.contrib import admin

from api.calculator.models import (
    AcciseRate,
    CustomsFee,
    DutyRate,
    Settings,
    UtilFee,
)
from api.common.admin import export_as_csv, export_as_json


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
    actions = [export_as_csv, export_as_json]
    fieldsets = (
        ("Параметры", {"fields": ("audience", "age_group", "unit", "max_value")}),
        ("Ставки, %", {"fields": ("rate_percent", "min_rate_eur_cc", "min_rate_eur_hp")}),
        ("Ставки EUR/см³", {"fields": ("rate_eur_cc",)}),
        ("Ставки EUR/л.с.", {"fields": ("rate_eur_hp",)}),
    )


@admin.register(UtilFee)
class UtilFeeAdmin(admin.ModelAdmin):
    list_display = ("kind", "max_cc", "coeff")
    list_filter = ("kind",)
    search_fields = ("kind",)
    ordering = ("kind", "max_cc")
    list_per_page = 50
    actions = [export_as_csv, export_as_json]
    fieldsets = (
        ("Параметры", {"fields": ("kind", "max_cc", "coeff")}),
    )


@admin.register(AcciseRate)
class AcciseRateAdmin(admin.ModelAdmin):
    list_display = ("max_hp", "rate_rub_per_hp")
    ordering = ("max_hp",)
    list_per_page = 50
    actions = [export_as_csv, export_as_json]
    fieldsets = (
        ("Параметры", {"fields": ("max_hp", "rate_rub_per_hp")}),
    )


@admin.register(CustomsFee)
class CustomsFeeAdmin(admin.ModelAdmin):
    list_display = ("max_value_rub", "fee_rub")
    ordering = ("max_value_rub",)
    list_per_page = 50
    actions = [export_as_csv, export_as_json]
    fieldsets = (
        ("Параметры", {"fields": ("max_value_rub", "fee_rub")}),
    )


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ("vat_rate", "company_commission_rub", "util_base", "updated_at")
    readonly_fields = ("updated_at",)
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)
    list_per_page = 50
    actions = [export_as_csv, export_as_json]
    fieldsets = (
        ("Параметры", {"fields": ("vat_rate", "company_commission_rub", "util_base")}),
        ("Служебное", {"fields": ("updated_at",), "classes": ("collapse",)}),
    )
