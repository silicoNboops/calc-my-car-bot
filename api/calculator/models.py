from __future__ import annotations

from django.db import models


class Audience(models.TextChoices):
    PASSENGER_CAR_PHYS = "PASSENGER_CAR_PHYS", "Passenger Car (Physical Person)"
    PASSENGER_CAR_JUR_BENZ = "PASSENGER_CAR_JUR_BENZ", "Passenger Car (Legal, Petrol)"
    PASSENGER_CAR_JUR_DIESEL = "PASSENGER_CAR_JUR_DIESEL", "Passenger Car (Legal, Diesel)"


class AgeGroup(models.TextChoices):
    UNDER_3 = "under_3_years", "Under 3 years"
    FROM_3_TO_5 = "3_to_5_years", "3 to 5 years"
    FROM_5_TO_7 = "5_to_7_years", "5 to 7 years"
    OVER_7 = "over_7_years", "Over 7 years"
    OVER_5 = "over_5_years", "Over 5 years"


class DutyUnit(models.TextChoices):
    EUR_CC = "eur_cc", "EUR per cc"
    PERCENT = "percent", "% of price"
    VALUE = "value", "Price bracket (EUR)"


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

    class Meta:
        indexes = [
            models.Index(fields=["audience", "age_group", "unit", "max_value"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    (
                        models.Q(unit=DutyUnit.EUR_CC) &
                        models.Q(rate_eur_cc__isnull=False) &
                        models.Q(rate_percent__isnull=True)
                    )
                    |
                    (
                        models.Q(unit__in=[DutyUnit.PERCENT, DutyUnit.VALUE]) &
                        models.Q(rate_percent__isnull=False)
                    )
                ),
                name="duty_rate_valid_combination",
            ),
        ]
        ordering = ["audience", "age_group", "unit", "max_value"]
        verbose_name = "Duty Rate"
        verbose_name_plural = "Duty Rates"

    def __str__(self) -> str:  # pragma: no cover - admin/debug
        return f"{self.audience} {self.age_group} {self.unit} <= {self.max_value}"


class UtilFeeKind(models.TextChoices):
    PERSONAL_NEW = "personal_new", "Personal (new)"
    PERSONAL_OLD = "personal_old", "Personal (old)"
    COMMERCIAL_UNDER_3 = "commercial_under_3", "Commercial under 3t"
    COMMERCIAL_OVER_3 = "commercial_over_3", "Commercial over 3t"


class UtilFee(models.Model):
    kind = models.CharField(max_length=32, choices=UtilFeeKind.choices)
    max_cc = models.FloatField(null=True, blank=True)
    coeff = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["kind", "max_cc"]) ]
        ordering = ["kind", "max_cc"]
        verbose_name = "Utilization Fee"
        verbose_name_plural = "Utilization Fees"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.kind} <= {self.max_cc}: {self.coeff}"


class AcciseRate(models.Model):
    max_hp = models.FloatField()
    rate_rub_per_hp = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["max_hp"]) ]
        ordering = ["max_hp"]
        verbose_name = "Accise Rate"
        verbose_name_plural = "Accise Rates"

    def __str__(self) -> str:  # pragma: no cover
        return f"<= {self.max_hp} hp: {self.rate_rub_per_hp} RUB/hp"


class CustomsFee(models.Model):
    max_value_rub = models.FloatField()
    fee_rub = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["max_value_rub"]) ]
        ordering = ["max_value_rub"]
        verbose_name = "Customs Fee"
        verbose_name_plural = "Customs Fees"

    def __str__(self) -> str:  # pragma: no cover
        return f"<= {self.max_value_rub} RUB: {self.fee_rub} RUB"


class Settings(models.Model):
    vat_rate = models.FloatField(default=0.20)
    company_commission_rub = models.FloatField(default=69000.0)
    util_base = models.FloatField(default=20000.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Calculator Settings"
        verbose_name_plural = "Calculator Settings"

    def __str__(self) -> str:  # pragma: no cover
        return f"VAT={self.vat_rate}, COMM={self.company_commission_rub}"

