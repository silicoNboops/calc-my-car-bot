from __future__ import annotations

from django.db import models


class VehicleType(models.TextChoices):
    CAR = "car", "Легковой"
    QUAD = "quad", "Квадроцикл"
    SNOWMOBILE = "snowmobile", "Снегоход"
    MOTORCYCLE = "motorcycle", "Мотоцикл"


class EngineType(models.TextChoices):
    BENZIN = "Бензин", "Бензин"
    DIESEL = "Дизель", "Дизель"
    ELECTRO = "Электро", "Электро"
    HYBRID_SERIES = "Гибрид(послед)", "Гибрид (послед.)"
    HYBRID_PARALLEL = "Гибрид(паралл)", "Гибрид (паралл.)"


class AgeKey(models.TextChoices):
    UNDER_3 = "under_3", "До 3 лет"
    FROM_3_TO_5 = "3_to_5", "3–5 лет"
    FROM_5_TO_7 = "5_to_7", "5–7 лет"
    OVER_7 = "over_7", "> 7 лет"
    OVER_5 = "over_5", "> 5 лет"


class Currency(models.TextChoices):
    EUR = "EUR", "EUR"
    USD = "USD", "USD"
    CNY = "CNY", "CNY"
    JPY = "JPY", "JPY"
    KRW = "KRW", "KRW"
    RUB = "RUB", "RUB"


# Модельные choices (ранишь были определены в models.py). Значения не меняем —
# они должны совпасть с фикстурами и БД.
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


class UtilFeeKind(models.TextChoices):
    PERSONAL_NEW = "personal_new", "Personal (new)"
    PERSONAL_OLD = "personal_old", "Personal (old)"
    COMMERCIAL_UNDER_3 = "commercial_under_3", "Commercial under 3t"
    COMMERCIAL_OVER_3 = "commercial_over_3", "Commercial over 3t"
