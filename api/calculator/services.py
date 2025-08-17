from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

# from django.core.cache import cache
from django.db.models import QuerySet

from api.calculator.models import (
    AcciseRate,
    CustomsFee,
    DutyRate,
    Settings,
    UtilFee,
)

EngineType = Literal["Бензин", "Дизель"]
AgeKey = Literal["under_3", "3_to_5", "5_to_7", "over_7", "over_5"]
Currency = Literal["EUR", "USD", "CNY", "JPY", "KRW", "RUB"]


@dataclass
class EstimateInput:
    price: float
    currency: Currency
    engine_cc: int
    hp: int
    engine_type: EngineType = "Бензин"
    age_key: AgeKey = "under_3"
    is_jur: bool = False
    is_personal_use: Optional[bool] = None


@dataclass
class EstimateResult:
    price_rub: float
    price_eur: float
    duty_eur: float
    duty_rub: float
    util_fee: float
    accise_rub: float
    vat_rub: float
    customs_fee: float
    subtotal_customs: float


class CurrencyProvider:
    """Абстракция над источником курсов валют.

    В следующем шаге будет реализована реализация с кэшем и внешним API.
    """

    def get_rates(self) -> dict[str, float]:
        # EUR base expected: {"EUR": 1.0, "USD": ..., "RUB": ...}
        raise NotImplementedError


class CustomsCalculator:
    """Чистая логика расчёта без обращений к внешним источникам.

    Будет реализована после переноса правил из legacy-калькулятора.
    """

    def __init__(self, rates: dict[str, QuerySet], settings: Settings, currency_rates: dict[str, float]):
        self.duty_rates: QuerySet[DutyRate] = rates["duty"]
        self.util_fees: QuerySet[UtilFee] = rates["util"]
        self.accise_rates: QuerySet[AcciseRate] = rates["accise"]
        self.customs_fees: QuerySet[CustomsFee] = rates["customs_fee"]
        self.settings = settings
        self.currency_rates = currency_rates

    def estimate(self, data: EstimateInput) -> EstimateResult:
        raise NotImplementedError


class CalculatorService:
    """Фасад: достаёт ORM-данные и курсы валют, конфигурирует калькулятор."""

    def __init__(self, currency_provider: CurrencyProvider):
        self.currency_provider = currency_provider

    def build_calculator(self) -> CustomsCalculator:
        currency_rates = self.currency_provider.get_rates()
        settings = Settings.objects.order_by("-updated_at").first() or Settings()
        rates = {
            "duty": DutyRate.objects.all(),
            "util": UtilFee.objects.all(),
            "accise": AcciseRate.objects.all(),
            "customs_fee": CustomsFee.objects.all(),
        }
        return CustomsCalculator(rates=rates, settings=settings, currency_rates=currency_rates)
