from __future__ import annotations

import datetime
import logging
import os
from dataclasses import dataclass
from typing import Optional

import requests
from django.conf import settings
from django.core.cache import cache
from django.db.models import QuerySet

from api.calculator.choices import (
    EngineType as EngineTypeChoices,
    VehicleType as VehicleTypeChoices,
    Audience,
    AgeGroup,
    DutyUnit,
    Currency as CurrencyChoices,
    AgeKey as AgeKeyChoices,
    UtilFeeKind,
)
from api.calculator.models import (
    AcciseRate,
    CustomsFee,
    DutyRate,
    Settings,
    UtilFee,
)
# V5 legacy calculator (single source of calculation truth)
from calculator.customs_calculator_v5 import (
    VehicleType as V5VehicleType,
    ImporterType as V5ImporterType,
    EngineType as V5EngineType,
    VehicleSpec as V5VehicleSpec,
    calculate_customs_payments as v5_calculate,
    RatesFetcher as V5RatesFetcher,
)

# Используем Django TextChoices как единый источник истины.
EngineType = EngineTypeChoices
VehicleType = VehicleTypeChoices
AgeKey = AgeKeyChoices
Currency = CurrencyChoices


@dataclass
class EstimateInput:
    price: float
    currency: Currency
    engine_cc: int
    hp: int
    vehicle_type: VehicleType = VehicleTypeChoices.CAR
    engine_type: EngineType = EngineTypeChoices.BENZIN
    age_key: AgeKey = AgeKeyChoices.UNDER_3
    is_jur: bool = False
    is_personal_use: Optional[bool] = None
    # Доп. поля для гибридов
    dvs_hp: Optional[int] = None
    electric_hp: Optional[int] = None


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

    def __init__(self, rates: dict[str, QuerySet], settings: Settings, currency_rates: dict[str, float]) -> None:
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
            elif r.unit == DutyUnit.EUR_HP:
                rows.append({"max_hp": r.max_value or float("inf"), "rate_eur_hp": float(r.rate_eur_hp or 0.0)})
            elif r.unit == DutyUnit.PERCENT_HP:
                rows.append({
                    "max_hp": r.max_value or float("inf"),
                    "rate_percent": float(r.rate_percent or 0.0),
                    "min_rate_eur_hp": float(r.min_rate_eur_hp or 0.0),
                })
        return rows

    def _collect_hp_rows(self, audience: str, age_group: str, unit: DutyUnit) -> list[dict]:
        """Помощник: собрать hp-строки для EUR_HP или PERCENT_HP."""
        rows: list[dict] = []
        qs = (
            self.duty_rates
            .filter(audience=audience, age_group=age_group, unit=unit)
            .order_by("max_value")
        )
        for r in qs:
            if unit == DutyUnit.EUR_HP:
                rows.append({"max_hp": r.max_value or float("inf"), "rate_eur_hp": float(r.rate_eur_hp or 0.0)})
            else:  # PERCENT_HP
                rows.append({
                    "max_hp": r.max_value or float("inf"),
                    "rate_percent": float(r.rate_percent or 0.0),
                    "min_rate_eur_hp": float(r.min_rate_eur_hp or 0.0),
                })
        return rows

    def _calc_duty_quad(self, price_eur: float, hp: int, age_key: AgeKey, is_jur: bool) -> float:
        if not is_jur:
            g = AgeGroup.UNDER_3 if age_key == AgeKeyChoices.UNDER_3 else AgeGroup.OVER_5
            if g == AgeGroup.UNDER_3:
                rows = self._collect_hp_rows(Audience.QUAD_PHYS, g, DutyUnit.PERCENT_HP)
                if not rows:
                    return 0.0
                row = self._find_bracket(int(hp), rows, "max_hp")
                rate_percent = float(row.get("rate_percent", 0.0))
                if rate_percent > 1.0:
                    rate_percent /= 100.0
                duty_val = price_eur * rate_percent
                duty_min = int(hp) * float(row.get("min_rate_eur_hp", 0.0))
                return max(duty_val, duty_min)
            else:
                rows = self._collect_hp_rows(Audience.QUAD_PHYS, g, DutyUnit.EUR_HP)
                if not rows:
                    return 0.0
                row = self._find_bracket(int(hp), rows, "max_hp")
                return int(hp) * float(row.get("rate_eur_hp", 0.0))
        else:
            g = AgeGroup.UNDER_3 if age_key == AgeKeyChoices.UNDER_3 else AgeGroup.OVER_5
            if g == AgeGroup.UNDER_3:
                rows = list(self.duty_rates.filter(audience=Audience.QUAD_JUR, age_group=g, unit=DutyUnit.PERCENT))
                if not rows:
                    return 0.0
                rate_percent = float(rows[0].rate_percent or 0.0)
                if rate_percent > 1.0:
                    rate_percent /= 100.0
                return price_eur * rate_percent
            else:
                rows = self._collect_hp_rows(Audience.QUAD_JUR, g, DutyUnit.PERCENT_HP)
                if not rows:
                    return 0.0
                row = rows[0]
                rate_percent = float(row.get("rate_percent", 0.0))
                if rate_percent > 1.0:
                    rate_percent /= 100.0
                return max(price_eur * rate_percent, int(hp) * float(row.get("min_rate_eur_hp", 0.0)))

    def _calc_duty_snowmobile(self, price_eur: float, hp: int, age_key: AgeKey, is_jur: bool) -> float:
        if not is_jur:
            g = AgeGroup.UNDER_3 if age_key == AgeKeyChoices.UNDER_3 else AgeGroup.OVER_5
            if g == AgeGroup.UNDER_3:
                rows = self._collect_hp_rows(Audience.SNOWMOBILE_PHYS, g, DutyUnit.PERCENT_HP)
                if not rows:
                    return 0.0
                row = self._find_bracket(int(hp), rows, "max_hp")
                rate_percent = float(row.get("rate_percent", 0.0))
                if rate_percent > 1.0:
                    rate_percent /= 100.0
                duty_val = price_eur * rate_percent
                duty_min = int(hp) * float(row.get("min_rate_eur_hp", 0.0))
                return max(duty_val, duty_min)
            else:
                rows = self._collect_hp_rows(Audience.SNOWMOBILE_PHYS, g, DutyUnit.EUR_HP)
                if not rows:
                    return 0.0
                row = self._find_bracket(int(hp), rows, "max_hp")
                return int(hp) * float(row.get("rate_eur_hp", 0.0))
        else:
            g = AgeGroup.UNDER_3 if age_key == AgeKeyChoices.UNDER_3 else AgeGroup.OVER_5
            if g == AgeGroup.UNDER_3:
                rows = list(
                    self.duty_rates.filter(audience=Audience.SNOWMOBILE_JUR, age_group=g, unit=DutyUnit.PERCENT))
                if not rows:
                    return 0.0
                rate_percent = float(rows[0].rate_percent or 0.0)
                if rate_percent > 1.0:
                    rate_percent /= 100.0
                return price_eur * rate_percent
            else:
                rows = self._collect_hp_rows(Audience.SNOWMOBILE_JUR, g, DutyUnit.PERCENT_HP)
                if not rows:
                    return 0.0
                row = rows[0]
                rate_percent = float(row.get("rate_percent", 0.0))
                if rate_percent > 1.0:
                    rate_percent /= 100.0
                return max(price_eur * rate_percent, int(hp) * float(row.get("min_rate_eur_hp", 0.0)))

    def _calc_duty_motorcycle(self, price_eur: float, engine_cc: int, age_key: AgeKey, is_jur: bool) -> float:
        cc = int(engine_cc)
        if not is_jur:
            g = AgeGroup.UNDER_3 if age_key == AgeKeyChoices.UNDER_3 else AgeGroup.OVER_5
            if g == AgeGroup.UNDER_3:
                rows = self.duty_rates.filter(audience=Audience.MOTORCYCLE_PHYS, age_group=g,
                                              unit=DutyUnit.PERCENT).order_by("max_value")
                table = [{"max_cc": float(r.max_value or float("inf")), "rate_percent": float(r.rate_percent or 0.0),
                          "min_rate_eur_cc": float(r.min_rate_eur_cc or 0.0)} for r in rows]
                if not table:
                    return 0.0
                row = self._find_bracket(cc, table, "max_cc")
                rate_percent = float(row.get("rate_percent", 0.0))
                if rate_percent > 1.0:
                    rate_percent /= 100.0
                return max(price_eur * rate_percent, cc * float(row.get("min_rate_eur_cc", 0.0)))
            else:
                rows = self.duty_rates.filter(audience=Audience.MOTORCYCLE_PHYS, age_group=g,
                                              unit=DutyUnit.EUR_CC).order_by("max_value")
                table = [{"max_cc": float(r.max_value or float("inf")), "rate_eur_cc": float(r.rate_eur_cc or 0.0)} for
                         r in rows]
                if not table:
                    return 0.0
                row = self._find_bracket(cc, table, "max_cc")
                return cc * float(row.get("rate_eur_cc", 0.0))
        else:
            g = AgeGroup.UNDER_3 if age_key == AgeKeyChoices.UNDER_3 else AgeGroup.OVER_5
            if g == AgeGroup.UNDER_3:
                rows = list(
                    self.duty_rates.filter(audience=Audience.MOTORCYCLE_JUR, age_group=g, unit=DutyUnit.PERCENT))
                if not rows:
                    return 0.0
                rate_percent = float(rows[0].rate_percent or 0.0)
                if rate_percent > 1.0:
                    rate_percent /= 100.0
                return price_eur * rate_percent
            else:
                rows = self.duty_rates.filter(audience=Audience.MOTORCYCLE_JUR, age_group=g,
                                              unit=DutyUnit.PERCENT).order_by("max_value")
                table = [{"max_cc": float(r.max_value or float("inf")), "rate_percent": float(r.rate_percent or 0.0),
                          "min_rate_eur_cc": float(r.min_rate_eur_cc or 0.0)} for r in rows]
                if not table:
                    return 0.0
                row = self._find_bracket(cc, table, "max_cc")
                rate_percent = float(row.get("rate_percent", 0.0))
                if rate_percent > 1.0:
                    rate_percent /= 100.0
                return max(price_eur * rate_percent, cc * float(row.get("min_rate_eur_cc", 0.0)))

    def _calc_duty(self, price_eur: float, engine_cc: int, age_key: AgeKey, is_jur: bool,
                   engine_type: EngineType) -> float:
        if not is_jur:
            # PASSENGER_CAR_PHYS
            group_map: dict[AgeKey, AgeGroup] = {
                AgeKeyChoices.UNDER_3: AgeGroup.UNDER_3,
                AgeKeyChoices.FROM_3_TO_5: AgeGroup.FROM_3_TO_5,
                AgeKeyChoices.OVER_5: AgeGroup.OVER_5,
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
            aud = Audience.PASSENGER_CAR_JUR_BENZ if engine_type == EngineTypeChoices.BENZIN else Audience.PASSENGER_CAR_JUR_DIESEL
            group_map: dict[AgeKey, AgeGroup] = {
                AgeKeyChoices.UNDER_3: AgeGroup.UNDER_3,
                AgeKeyChoices.FROM_3_TO_5: AgeGroup.FROM_3_TO_5,
                AgeKeyChoices.FROM_5_TO_7: AgeGroup.FROM_5_TO_7,
                AgeKeyChoices.OVER_7: AgeGroup.OVER_7,
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

    def _calc_util(self, is_commercial: bool, age_key: AgeKey, engine_cc: int, engine_type: EngineType,
                   vehicle_type: VehicleType = VehicleTypeChoices.CAR) -> float:
        # util_base хранится в Settings (fallback к 20000.0 при отсутствии)
        util_base = float(getattr(self.settings, "util_base", 20000.0) or 20000.0)
        # По требованиям оригинального калькулятора: для мотоциклов и снегоходов утильсбор всегда 0
        if vehicle_type in (VehicleTypeChoices.MOTORCYCLE, VehicleTypeChoices.SNOWMOBILE):
            return 0.0
        if not is_commercial and vehicle_type == VehicleTypeChoices.CAR:
            # Берём детерминированно запись с max_cc IS NULL из боевых фикстур
            # (избегаем влияния шаблонных фикстур и сортировки NULL в разных СУБД)
            row = (
                self.util_fees.filter(kind=UtilFeeKind.PERSONAL_NEW, max_cc__isnull=True).first()
                if age_key == AgeKeyChoices.UNDER_3
                else self.util_fees.filter(kind=UtilFeeKind.PERSONAL_OLD, max_cc__isnull=True).first()
            )
            coeff = float(getattr(row, "coeff", 0.0))
            return util_base * coeff
        elif not is_commercial and vehicle_type != VehicleTypeChoices.CAR:
            # v2: фикс коэффициенты для quad/snowmobile/motorcycle у ФЛ
            is_new = (age_key == AgeKeyChoices.UNDER_3)
            coeff = 1.63 if is_new else 6.1
            # Для этих ТС util_base отличается от авто: 172500 в v2.
            # Но мы используем Settings.util_base как базу и умножаем на отношение (172500/20000)=8.625,
            # чтобы не вводить миграции. При default util_base=20000 это даст корректные суммы.
            base_multiplier = 8.625
            return util_base * base_multiplier * coeff
        else:
            # EV/Hybrid коммерческий: по v2 фиксированные коэффициенты, не зависящие от объёма
            if vehicle_type == VehicleTypeChoices.CAR and engine_type in (
                    EngineTypeChoices.ELECTRO,
                    EngineTypeChoices.HYBRID_SERIES,
                    EngineTypeChoices.HYBRID_PARALLEL,
            ):
                if age_key == AgeKeyChoices.UNDER_3:
                    coeff = 1.42  # new_electric/new_hybrid
                else:
                    coeff = 2.84  # old_electric/old_hybrid
                return util_base * coeff
            elif vehicle_type != VehicleTypeChoices.CAR:
                # Коммерческий quad/snowmobile/motorcycle: те же коэффициенты, что для персональных в v2
                is_new = (age_key == AgeKeyChoices.UNDER_3)
                coeff = 1.63 if is_new else 6.1
                base_multiplier = 8.625
                return util_base * base_multiplier * coeff
            # ICE коммерческий: как раньше, по объёму из БД
            group = UtilFeeKind.COMMERCIAL_UNDER_3 if age_key == AgeKeyChoices.UNDER_3 else UtilFeeKind.COMMERCIAL_OVER_3
            rows = list(self.util_fees.filter(kind=group).order_by("max_cc"))
            table = [{"max_cc": float(r.max_cc or float("inf")), "coeff": float(r.coeff)} for r in rows] if rows else []
            if not table:
                return 0.0
            row = self._find_bracket(engine_cc, table, "max_cc")
            return util_base * float(row.get("coeff", 0.0))

    def _calc_accise(self, hp: int, is_commercial: bool, engine_type: EngineType, dvs_hp: int | None = None,
                     electric_hp: int | None = None) -> float:
        """Акциз по v5.

        - EV: прогрессивный акциз по мощности применяется всегда (включая ФЛ личное использование).
        - Прочие типы: как ранее, акциз только для коммерции/юрлиц.
        - Для гибридов определяем мощность согласно типу гибрида (серийный: сумма, параллельный: dvs_hp или 65% от hp).
        Ставки берём из таблицы AcciseRate (руб/л.с. по брекетам max_hp).
        """
        # EV — всегда считаем по прогрессивной шкале
        if engine_type == EngineTypeChoices.ELECTRO:
            power_for_tax = int(hp)
        else:
            # Для не-EV: применяем акциз только для коммерции
            if not is_commercial:
                return 0.0
            if engine_type == EngineTypeChoices.HYBRID_SERIES:
                power_for_tax = int((dvs_hp or 0) + (electric_hp or 0))
            elif engine_type == EngineTypeChoices.HYBRID_PARALLEL:
                power_for_tax = int(dvs_hp if dvs_hp is not None else int(hp * 0.65))
            else:
                power_for_tax = int(hp)

        rows = list(self.accise_rates.order_by("max_hp"))
        table = [{"max_hp": float(r.max_hp), "rate": float(r.rate_rub_per_hp)} for r in rows]
        if not table:
            return 0.0
        row = self._find_bracket(power_for_tax, table, "max_hp")
        return power_for_tax * float(row.get("rate", 0.0))

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
        """Полная переадресация расчёта в legacy V5 калькулятор.

        1) Переносим входные данные EstimateInput -> V5 VehicleSpec.
        2) Подсовываем курсы валют из текущего провайдера в кэш V5 RatesFetcher,
           чтобы избежать сетевых запросов и обеспечить детерминизм.
        3) Вызываем v5_calculate(...) и маппим результат в EstimateResult.
        """

        # 1) Нормализуем перечисления (допускаем строки)
        cur = data.currency if not isinstance(data.currency, str) else CurrencyChoices(data.currency)
        veh = data.vehicle_type if not isinstance(data.vehicle_type, str) else VehicleTypeChoices(data.vehicle_type)
        eng = data.engine_type if not isinstance(data.engine_type, str) else EngineTypeChoices(data.engine_type)
        age = data.age_key if not isinstance(data.age_key, str) else AgeKeyChoices(data.age_key)

        # 2) Курсы валют: кладём в кэш V5
        fx = dict(self.currency_rates)
        V5RatesFetcher._cache = {k.upper(): float(v) for k, v in fx.items()}
        V5RatesFetcher._cache["RUB"] = float(V5RatesFetcher._cache.get("RUB", 1.0))
        V5RatesFetcher._cache_time = datetime.datetime.now()

        # 3) Маппинг импортёра
        if data.is_jur:
            importer = V5ImporterType.JURIDICAL
        else:
            if data.is_personal_use is False:
                importer = V5ImporterType.PHYS_RESALE
            else:
                importer = V5ImporterType.PHYS_PERSONAL

        # 4) Маппинг типов
        v5_vehicle = {
            VehicleTypeChoices.CAR: V5VehicleType.CAR,
            VehicleTypeChoices.QUAD: V5VehicleType.QUAD,
            VehicleTypeChoices.SNOWMOBILE: V5VehicleType.SNOWMOBILE,
            VehicleTypeChoices.MOTORCYCLE: V5VehicleType.MOTORCYCLE,
        }[veh]

        v5_engine = {
            EngineTypeChoices.ELECTRO: V5EngineType.ELECTRIC,
            EngineTypeChoices.HYBRID_SERIES: V5EngineType.HYBRID_SERIES,
            EngineTypeChoices.HYBRID_PARALLEL: V5EngineType.HYBRID_PARALLEL,
        }.get(eng, V5EngineType.DVS)

        # 5) Возраст в годах для V5
        def _age_years(a: AgeKeyChoices) -> int:
            if a == AgeKeyChoices.UNDER_3:
                return 1
            if a in (AgeKeyChoices.BETWEEN_3_5, AgeKeyChoices.BETWEEN_3_7, AgeKeyChoices.FROM_3_TO_5):
                return 4
            return 6

        # 6) Собираем спеку V5
        spec = V5VehicleSpec(
            vehicle_type=v5_vehicle,
            importer_type=importer,
            cost_original=float(data.price),
            currency=str(cur.value),
            age_years=_age_years(age),
            engine_volume_cc=int(data.engine_cc),
            power_hp=int(data.hp or 0),
            engine_type=v5_engine,
            dvs_power_hp=int(data.dvs_hp or 0),
            electric_power_hp=int(data.electric_hp or 0),
        )

        # 7) Вызываем V5 калькулятор
        v5_res = v5_calculate(spec)

        # 8) Маппим ответ V5 -> EstimateResult
        # price_eur берём из breakdown, если есть; иначе пересчитываем из курса
        bd = v5_res.breakdown or {}
        eur_rate = float(bd.get("eur_rate") or fx.get("EUR") or 1.0)
        price_eur = float(bd.get("cost_eur")) if "cost_eur" in bd else float(v5_res.cost_rub) / float(eur_rate)

        return EstimateResult(
            price_rub=float(v5_res.cost_rub),
            price_eur=float(price_eur),
            duty_eur=float(bd.get("duty_eur", 0.0)),
            duty_rub=float(v5_res.duty_rub),
            util_fee=float(v5_res.util_fee_rub),
            accise_rub=float(v5_res.excise_rub),
            vat_rub=float(v5_res.vat_rub),
            customs_fee=float(v5_res.customs_fee_rub),
            subtotal_customs=float(v5_res.total_rub),
        )


class CalculatorService:
    """Фасад: достаёт ORM-данные и курсы валют, конфигурирует калькулятор."""

    def __init__(self, currency_provider: CurrencyProvider) -> None:
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
        return CustomsCalculator(rates, settings, currency_rates)


class FixedCurrencyProvider(CurrencyProvider):
    """Static currency provider for offline/CI.

    Default sample rates: RUB=1.0, EUR≈100, USD≈95, etc.
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
    # Процессный запасной кэш, чтобы тесты могли проверить повторное использование без Redis
    _MEM_CACHE_KEY = "currency_rates_cbrf_v1"
    _mem_cache: dict[str, float] | None = None

    def __init__(self, cache_timeout_seconds: int | None = None, url: str | None = None) -> None:
        # Настройки по умолчанию берём из Django settings, но можно переопределить аргументами
        default_ttl = getattr(settings, "CBR_CACHE_TTL", 3600)
        default_url = getattr(settings, "CBR_URL", self.CBR_URL)
        self.cache_timeout = int(cache_timeout_seconds if cache_timeout_seconds is not None else default_ttl)
        self.url = str(url or default_url)
        self.logger = logging.getLogger(__name__)

    def get_rates(self) -> dict[str, float]:
        cache_key = "currency_rates_cbrf_v1"
        # 1) Попытка чтения из кэша — ошибки кэша не критичны
        try:
            cached = cache.get(cache_key)
            if isinstance(cached, dict) and cached:
                return cached
        except Exception as e:  # noqa: BLE001
            self.logger.warning("CBRF rates cache get failed, continue without cache: %s", e)

        # 1a) Попробуем процессный кэш
        if isinstance(self._mem_cache, dict) and self._mem_cache:
            return dict(self._mem_cache)

        # 2) Сетевой запрос; на любые ошибки источника — fallback к фиксированным курсам
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

            if "EUR" not in rates:
                msg = "EUR rate is missing from CBR response"
                raise ValueError(msg)

            # 3) Пишем в кэш — ошибки игнорируем
            try:
                cache.set(cache_key, rates, timeout=self.cache_timeout)
            except Exception as e:  # noqa: BLE001
                self.logger.warning("CBRF rates cache set failed, continue: %s", e)
            # Всегда обновляем процессный кэш на случай отсутствия Redis
            self.__class__._mem_cache = dict(rates)
        except Exception as e:  # noqa: BLE001
            self.logger.warning("CBRF rates fetch failed, fallback to fixed: %s", e)
            return FixedCurrencyProvider().get_rates()
        else:
            return rates


def get_default_currency_provider() -> CurrencyProvider:
    """Select default currency provider for API/bot.

    - USE_FIXED_CURRENCY_PROVIDER=true forces FixedCurrencyProvider (offline/CI).
    - Otherwise CbrfCurrencyProvider is used with URL/TTL from Django settings.
    """
    # 1) Explicit Django settings take precedence over env.
    try:
        if bool(settings.USE_FIXED_CURRENCY_PROVIDER):  # type: ignore[attr-defined]
            return FixedCurrencyProvider()
        return CbrfCurrencyProvider()
    except AttributeError:
        # 2) Fallback to env (for CI/local)
        env_flag = os.environ.get("USE_FIXED_CURRENCY_PROVIDER", "").strip().lower()
        env_enabled = env_flag in {"1", "true", "yes", "on"}
        return FixedCurrencyProvider() if env_enabled else CbrfCurrencyProvider()
