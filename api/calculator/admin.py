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
    list_display = ("audience", "age_group", "unit", "max_value", "rate_percent", "rate_eur_cc", "min_rate_eur_cc")
    list_filter = ("audience", "age_group", "unit")
    search_fields = ("audience", "age_group")


@admin.register(UtilFee)
class UtilFeeAdmin(admin.ModelAdmin):
    list_display = ("kind", "max_cc", "coeff")
    list_filter = ("kind",)


@admin.register(AcciseRate)
class AcciseRateAdmin(admin.ModelAdmin):
    list_display = ("max_hp", "rate_rub_per_hp")


@admin.register(CustomsFee)
class CustomsFeeAdmin(admin.ModelAdmin):
    list_display = ("max_value_rub", "fee_rub")


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ("vat_rate", "company_commission_rub", "updated_at")
