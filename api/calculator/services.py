from __future__ import annotations

import logging
import requests
from typing import Literal, Optional

from django.core.cache import cache
from django.db.models import QuerySet
from django.conf import settings
from dataclasses import dataclass

from api.calculator.models import (
    AcciseRate,
    CustomsFee,
    DutyRate,
    Settings,
    UtilFee,
    Audience,
    AgeGroup,
    DutyUnit,
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

    def _find_bracket(self, value: float, rows: list[dict], key: str) -> dict:
        for row in rows:
            max_v = float(row.get(key) if row.get(key) is not None else float("inf"))
            if value <= max_v:
                return row
        return rows[-1]

    def _collect_duty_rows(self, audience: str, age_group: str) -> list[dict]:
        rows: list[dict] = []
        qs = self.duty_rates.filter(audience=audience, age_group=age_group).order_by("max_value")
        # Фильтруем неподходящие единицы измерения для конкретных схем расчёта,
        # чтобы исключить "зашумление" данными (например, PERCENT для phys under_3).
        if audience == Audience.PASSENGER_CAR_PHYS:
            if age_group == AgeGroup.UNDER_3:
                qs = qs.filter(unit=DutyUnit.VALUE)
            else:
                qs = qs.filter(unit=DutyUnit.EUR_CC)
        for r in qs:
            if r.unit == DutyUnit.EUR_CC:
                rows.append({"max_cc": r.max_value or float("inf"), "rate_eur_cc": float(r.rate_eur_cc or 0.0)})
            elif r.unit in (DutyUnit.PERCENT, DutyUnit.VALUE):
                key = "max_value" if r.unit == DutyUnit.VALUE else "max_cc"
                rows.append({
                    key: r.max_value or float("inf"),
                    "rate_percent": float(r.rate_percent or 0.0),
                    "min_rate_eur_cc": float(r.min_rate_eur_cc or 0.0),
                })
        return rows

    def _calc_duty(self, price_eur: float, engine_cc: int, age_key: str, is_jur: bool, engine_type: str) -> float:
        if not is_jur:
            # PASSENGER_CAR_PHYS
            group_map = {
                "under_3": AgeGroup.UNDER_3,
                "3_to_5": AgeGroup.FROM_3_TO_5,
                "over_5": AgeGroup.OVER_5,
            }
            g = group_map.get(age_key, AgeGroup.UNDER_3)
            rows = self._collect_duty_rows(Audience.PASSENGER_CAR_PHYS, g)
            if g == AgeGroup.UNDER_3:
                # процентные + минимум €/см³, брекеты по цене (EUR)
                row = self._find_bracket(price_eur, rows, "max_value")
                rate_percent = float(row.get("rate_percent", 0.0))
                # В фикстурах ставка может храниться как 54 (т.е. 54%), нормализуем до 0.54
                if rate_percent > 1.0:
                    rate_percent = rate_percent / 100.0
                duty_from_price = price_eur * rate_percent
                duty_from_volume = engine_cc * float(row.get("min_rate_eur_cc", 0.0))
                return max(duty_from_price, duty_from_volume)
            else:
                # €/см³, брекеты по объёму
                row = self._find_bracket(engine_cc, rows, "max_cc")
                return engine_cc * float(row.get("rate_eur_cc", 0.0))
        else:
            # Юрлица: BENZ/DIESEL
            aud = Audience.PASSENGER_CAR_JUR_BENZ if engine_type == "Бензин" else Audience.PASSENGER_CAR_JUR_DIESEL
            group_map = {
                "under_3": AgeGroup.UNDER_3,
                "3_to_5": AgeGroup.FROM_3_TO_5,
                "5_to_7": AgeGroup.FROM_5_TO_7,
                "over_7": AgeGroup.OVER_7,
            }
            g = group_map.get(age_key, AgeGroup.UNDER_3)
            rows = self._collect_duty_rows(aud, g)
            if not rows:
                return 0.0
            # Два случая: процент (с минимумом €/см³) ИЛИ фикс €/см³
            if "rate_percent" in rows[0]:
                row = self._find_bracket(engine_cc, rows, "max_cc")
                rate_percent = float(row.get("rate_percent", 0.0))
                if rate_percent > 1.0:
                    rate_percent = rate_percent / 100.0
                duty_from_percent = price_eur * rate_percent
                min_from_volume = engine_cc * float(row.get("min_rate_eur_cc", 0.0))
                return max(duty_from_percent, min_from_volume)
            else:
                row = self._find_bracket(engine_cc, rows, "max_cc")
                return engine_cc * float(row.get("rate_eur_cc", 0.0))

    def _calc_util(self, is_commercial: bool, age_key: str, engine_cc: int) -> float:
        # util_base хранится в Settings (fallback к 20000.0 при отсутствии)
        util_base = float(getattr(self.settings, "util_base", 20000.0) or 20000.0)
        if not is_commercial:
            row = self.util_fees.filter(kind="personal_new").first() if age_key == "under_3" else self.util_fees.filter(kind="personal_old").first()
            coeff = float(getattr(row, "coeff", 0.0))
            return util_base * coeff
        else:
            group = "commercial_under_3" if age_key == "under_3" else "commercial_over_3"
            rows = list(self.util_fees.filter(kind=group).order_by("max_cc"))
            table = [{"max_cc": float(r.max_cc or float("inf")), "coeff": float(r.coeff)} for r in rows] if rows else []
            if not table:
                return 0.0
            row = self._find_bracket(engine_cc, table, "max_cc")
            return util_base * float(row.get("coeff", 0.0))

    def _calc_accise(self, hp: int, is_commercial: bool) -> float:
        if not is_commercial:
            return 0.0
        rows = list(self.accise_rates.order_by("max_hp"))
        table = [{"max_hp": float(r.max_hp), "rate": float(r.rate_rub_per_hp)} for r in rows]
        if not table:
            return 0.0
        row = self._find_bracket(hp, table, "max_hp")
        return hp * float(row.get("rate", 0.0))

    def _calc_vat(self, price_rub: float, duty_rub: float, accise_rub: float, is_commercial: bool) -> float:
        if not is_commercial:
            return 0.0
        base = price_rub + duty_rub + accise_rub
        return base * float(self.settings.vat_rate or 0.20)

    def _calc_customs_fee(self, price_rub: float) -> float:
        rows = list(self.customs_fees.order_by("max_value_rub"))
        table = [{"max_value": float(r.max_value_rub), "fee": float(r.fee_rub)} for r in rows]
        if not table:
            return 0.0
        row = self._find_bracket(price_rub, table, "max_value")
        return float(row.get("fee", 0.0))

    def estimate(self, data: EstimateInput) -> EstimateResult:
        # Конвертация валют (как в legacy): fx — RUB за единицу валюты
        fx = self.currency_rates
        if data.currency not in fx:
            raise ValueError(f"Unsupported currency: {data.currency}")
        price_rub = float(data.price) * float(fx[data.currency])
        price_eur = price_rub / float(fx.get("EUR", 1.0))

        is_commercial = data.is_jur or (data.is_personal_use is False)

        duty_eur = self._calc_duty(price_eur, int(data.engine_cc), data.age_key, data.is_jur, data.engine_type)
        duty_rub = duty_eur * float(fx.get("EUR", 1.0))

        util_fee = self._calc_util(is_commercial, data.age_key, int(data.engine_cc))
        accise_rub = self._calc_accise(int(data.hp), is_commercial)
        vat_rub = self._calc_vat(price_rub, duty_rub, accise_rub, is_commercial)
        # Таможенный сбор: для физлиц при личном использовании фиксировано 500 ₽ (v2)
        if not is_commercial:
            customs_fee = 500.0
        else:
            customs_fee = self._calc_customs_fee(price_rub)

        subtotal_customs = duty_rub + util_fee + accise_rub + vat_rub + customs_fee

        return EstimateResult(
            price_rub=price_rub,
            price_eur=price_eur,
            duty_eur=duty_eur,
            duty_rub=duty_rub,
            util_fee=util_fee,
            accise_rub=accise_rub,
            vat_rub=vat_rub,
            customs_fee=customs_fee,
            subtotal_customs=subtotal_customs,
        )


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
        calculator = CustomsCalculator(rates, settings, currency_rates)
        return calculator


class FixedCurrencyProvider(CurrencyProvider):
    """Временный провайдер курсов валют: фиксированные значения.

{{ ... }}
    (RUB=1.0, EUR≈100 и т.д.).

    TODO: заменить на реальный провайдер курсов (ЦБ РФ) с кэшированием.
    """

    def __init__(self, rates: dict[str, float] | None = None) -> None:
        self._rates = rates or {
            "RUB": 1.0,
            "EUR": 100.0,
            "USD": 95.0,
            "CNY": 13.5,
            "JPY": 0.65,
            "KRW": 0.07,
        }

    def get_rates(self) -> dict[str, float]:
        return dict(self._rates)


class CbrfCurrencyProvider(CurrencyProvider):
    """Провайдер курсов ЦБ РФ с кэшированием.

    - Источник: https://www.cbr-xml-daily.ru/daily_json.js
    - Кэш через Django cache, ключ фиксирован, TTL настраиваемый.
    - Fallback: возвращаем фиксированные курсы из FixedCurrencyProvider при ошибке.
    """

    CBR_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
    SUPPORTED = ("EUR", "USD", "CNY", "JPY", "KRW", "RUB")

    def __init__(self, cache_timeout_seconds: Optional[int] = None, url: Optional[str] = None) -> None:
        # Настройки по умолчанию берём из Django settings, но можно переопределить аргументами
        default_ttl = getattr(settings, "CBR_CACHE_TTL", 3600)
        default_url = getattr(settings, "CBR_URL", self.CBR_URL)
        self.cache_timeout = int(cache_timeout_seconds if cache_timeout_seconds is not None else default_ttl)
        self.url = str(url or default_url)
        self.logger = logging.getLogger(__name__)

    def get_rates(self) -> dict[str, float]:
        cache_key = "currency_rates_cbrf_v1"
        cached = cache.get(cache_key)
        if isinstance(cached, dict) and cached:
            return cached

        try:
            resp = requests.get(self.url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            rates: dict[str, float] = {"RUB": 1.0}
            valute = data.get("Valute", {}) or {}
            for code in self.SUPPORTED:
                if code == "RUB":
                    continue
                v = valute.get(code)
                if not v:
                    continue
                value = float(v.get("Value", 0.0))
                nominal = float(v.get("Nominal", 1.0)) or 1.0
                rates[code] = value / nominal

            # Если по какой-то причине не получили EUR, считаем это ошибкой источника
            if "EUR" not in rates:
                raise ValueError("EUR rate is missing from CBR response")

            cache.set(cache_key, rates, timeout=self.cache_timeout)
            return rates
        except Exception as e:  # noqa: BLE001
            self.logger.warning("CBRF rates fetch failed, fallback to fixed: %s", e)
            return FixedCurrencyProvider().get_rates()


def get_default_currency_provider() -> CurrencyProvider:
    """Фабрика провайдера курсов для API/бота, управляется настройками.

    - USE_FIXED_CURRENCY_PROVIDER=true принудительно включает FixedCurrencyProvider (для оффлайна/CI).
    - Иначе используется CbrfCurrencyProvider со значениями URL/TTL из settings.
    """
    if getattr(settings, "USE_FIXED_CURRENCY_PROVIDER", False):
        return FixedCurrencyProvider()
    return CbrfCurrencyProvider()
