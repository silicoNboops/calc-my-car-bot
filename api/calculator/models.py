from __future__ import annotations

from django.db import models
from api.calculator.choices import Audience, AgeGroup, DutyUnit, UtilFeeKind



class DutyRate(models.Model):
    audience = models.CharField(max_length=48, choices=Audience.choices)
    age_group = models.CharField(max_length=32, choices=AgeGroup.choices)
    unit = models.CharField(max_length=16, choices=DutyUnit.choices)

    # Threshold for bracket: if unit==VALUE then it's price EUR; otherwise it's cc (engine volume)
    max_value = models.FloatField(null=True, blank=True)

    # Either percent with optional min EUR/cc, or explicit EUR/cc
    rate_percent = models.FloatField(null=True, blank=True)
    rate_eur_cc = models.FloatField(null=True, blank=True)
    min_rate_eur_cc = models.FloatField(null=True, blank=True)
    # HP-based (for non-car audiences)
    rate_eur_hp = models.FloatField(null=True, blank=True)
    min_rate_eur_hp = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["audience", "age_group", "unit", "max_value"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(unit=DutyUnit.EUR_CC)
                        & models.Q(rate_eur_cc__isnull=False)
                        & models.Q(rate_percent__isnull=True)
                        & models.Q(rate_eur_hp__isnull=True)
                        & models.Q(min_rate_eur_hp__isnull=True)
                    )
                    |
                    (
                        models.Q(unit=DutyUnit.EUR_HP)
                        & models.Q(rate_eur_hp__isnull=False)
                        & models.Q(rate_percent__isnull=True)
                        & models.Q(rate_eur_cc__isnull=True)
                        & models.Q(min_rate_eur_cc__isnull=True)
                    )
                    |
                    (
                        models.Q(unit__in=[DutyUnit.PERCENT, DutyUnit.VALUE])
                        & models.Q(rate_percent__isnull=False)
                        & models.Q(rate_eur_cc__isnull=True)
                        & models.Q(rate_eur_hp__isnull=True)
                    )
                    |
                    (
                        models.Q(unit=DutyUnit.PERCENT_HP)
                        & models.Q(rate_percent__isnull=False)
                        & models.Q(rate_eur_cc__isnull=True)
                        & models.Q(rate_eur_hp__isnull=True)
                    )
                ),
                name="duty_rate_valid_combination",
            ),
        ]
        ordering = ["audience", "age_group", "unit", "max_value"]
        verbose_name = "Ставка пошлины"
        verbose_name_plural = "Ставки пошлины"

    def __str__(self) -> str:  # pragma: no cover - admin/debug
        return f"{self.audience} {self.age_group} {self.unit} <= {self.max_value}"


class UtilFee(models.Model):
    kind = models.CharField(max_length=32, choices=UtilFeeKind.choices)
    max_cc = models.FloatField(null=True, blank=True)
    coeff = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["kind", "max_cc"]) ]
        ordering = ["kind", "max_cc"]
        verbose_name = "Утилизационный сбор"
        verbose_name_plural = "Утилизационные сборы"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.kind} <= {self.max_cc}: {self.coeff}"


class AcciseRate(models.Model):
    max_hp = models.FloatField()
    rate_rub_per_hp = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["max_hp"]) ]
        ordering = ["max_hp"]
        verbose_name = "Акцизная ставка"
        verbose_name_plural = "Акцизные ставки"

    def __str__(self) -> str:  # pragma: no cover
        return f"<= {self.max_hp} hp: {self.rate_rub_per_hp} RUB/hp"


class CustomsFee(models.Model):
    max_value_rub = models.FloatField()
    fee_rub = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["max_value_rub"]) ]
        ordering = ["max_value_rub"]
        verbose_name = "Таможенный сбор"
        verbose_name_plural = "Таможенные сборы"

    def __str__(self) -> str:  # pragma: no cover
        return f"<= {self.max_value_rub} RUB: {self.fee_rub} RUB"


class Settings(models.Model):
    vat_rate = models.FloatField(default=0.20)
    company_commission_rub = models.FloatField(default=69000.0)
    util_base = models.FloatField(default=20000.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Настройки калькулятора"
        verbose_name_plural = "Настройки калькулятора"

    def __str__(self) -> str:  # pragma: no cover
        return f"VAT={self.vat_rate}, COMM={self.company_commission_rub}"

