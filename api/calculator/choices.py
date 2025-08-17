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
