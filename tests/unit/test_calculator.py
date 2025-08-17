from __future__ import annotations

import pytest
from django.urls import reverse
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient

from api.calculator.serializers import EstimateRequestSerializer
from api.calculator.services import (
    CalculatorService,
    CbrfCurrencyProvider,
    EstimateInput,
    get_default_currency_provider,
)
from api.calculator.models import DutyRate, Audience, AgeGroup, DutyUnit, CustomsFee


@pytest.fixture(autouse=True, scope="session")
def _seed_customs_rates(django_db_setup, django_db_blocker):  # type: ignore[no-untyped-def]
    """Загружаем ставки из JSON через management-команду для тестовой БД.

    Используем seed_customs_rates с --replace чтобы гарантировать консистентные данные
    для всех тестов этого модуля.
    """
    with django_db_blocker.unblock():
        call_command("seed_customs_rates", "--replace", "--path", "api/calculator/fixtures")

@pytest.mark.django_db()
def test_serializer_age_key_forbidden_over5_for_jur() -> None:
    s = EstimateRequestSerializer(data={
        "price": 10000,
        "currency": "EUR",
        "engine_cc": 1600,
        "hp": 100,
        "engine_type": "Бензин",
        "age_key": "over_5",
        "is_jur": True,
    })
    assert not s.is_valid()
    assert "age_key" in s.errors


@pytest.mark.django_db()
def test_serializer_normalizes_phys_over7_to_over5() -> None:
    s = EstimateRequestSerializer(data={
        "price": 10000,
        "currency": "EUR",
        "engine_cc": 1600,
        "hp": 100,
        "engine_type": "Бензин",
        "age_key": "over_7",
        "is_jur": False,
    })
    assert s.is_valid(), s.errors
    assert s.validated_data["age_key"] == "over_5"
    # is_personal_use should default to not is_jur
    assert s.validated_data["is_personal_use"] is True


@pytest.mark.django_db()
def test_boundary_phys_under3_price_bracket_duty_exact_max() -> None:
    # Берём первый брекет по цене для физлиц <3 лет
    row = (
        DutyRate.objects
        .filter(audience=Audience.PASSENGER_CAR_PHYS, age_group=AgeGroup.UNDER_3, unit__in=[DutyUnit.PERCENT, DutyUnit.VALUE])
        .order_by("max_value")
        .first()
    )
    assert row is not None
    price_eur = float(row.max_value)
    rate_percent = float(row.rate_percent or 0.0)
    min_rate_eur_cc = float(row.min_rate_eur_cc or 0.0)

    engine_cc = 1600
    # В фикстурах проценты могут храниться как 54 (т.е. 54%), нормализуем
    rate_percent_norm = rate_percent / 100.0 if rate_percent > 1.0 else rate_percent
    expected_duty = max(price_eur * rate_percent_norm, engine_cc * min_rate_eur_cc)

    client = APIClient()
    resp = client.post(
        reverse("calculator:estimate"),
        data={
            "price": price_eur,
            "currency": "EUR",
            "engine_cc": engine_cc,
            "hp": 100,
            "engine_type": "Бензин",
            "age_key": "under_3",
            "is_jur": False,
            "is_personal_use": True,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    assert pytest.approx(data["duty_eur"], rel=1e-6) == expected_duty


@pytest.mark.django_db()
def test_boundary_phys_over5_volume_bracket_duty_exact_max_cc() -> None:
    # Берём первый брекет €/см³ по объёму для физлиц >5 лет
    row = (
        DutyRate.objects
        .filter(audience=Audience.PASSENGER_CAR_PHYS, age_group=AgeGroup.OVER_5, unit=DutyUnit.EUR_CC)
        .order_by("max_value")
        .first()
    )
    assert row is not None
    max_cc = int(row.max_value)
    rate_eur_cc = float(row.rate_eur_cc or 0.0)

    client = APIClient()
    resp = client.post(
        reverse("calculator:estimate"),
        data={
            "price": 10000.0,
            "currency": "EUR",
            "engine_cc": max_cc,
            "hp": 100,
            "engine_type": "Бензин",
            "age_key": "over_5",
            "is_jur": False,
            "is_personal_use": True,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    expected_duty = max_cc * rate_eur_cc
    assert pytest.approx(data["duty_eur"], rel=1e-6) == expected_duty


@pytest.mark.django_db()
def test_boundary_customs_fee_exact_max_value_rub() -> None:
    fee_row = CustomsFee.objects.order_by("max_value_rub").first()
    assert fee_row is not None
    price_rub = float(fee_row.max_value_rub)

    client = APIClient()
    resp = client.post(
        reverse("calculator:estimate"),
        data={
            "price": price_rub,
            "currency": "RUB",
            "engine_cc": 1600,
            "hp": 100,
            "engine_type": "Бензин",
            "age_key": "under_3",
            "is_jur": False,
            "is_personal_use": True,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # Для физлиц (личное использование) по v2 фиксированный таможенный сбор 500 ₽
    assert pytest.approx(data["customs_fee"], rel=1e-6) == 500.0


@pytest.mark.django_db()
def test_ev_phys_under3_basic_v2_rules() -> None:
    """Физлицо, электро, <3 лет: duty = 15% от цены (EUR), accise=0, VAT=0, util=3400, customs_fee=500."""
    client = APIClient()
    payload = {
        "price": 20000.0,  # EUR
        "currency": "EUR",
        "engine_cc": 1,  # не влияет на EV <3 в наших правилах
        "hp": 150,
        "engine_type": "Электро",
        "age_key": "under_3",
        "is_jur": False,
        "is_personal_use": True,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # duty_eur = 15% от 20000 = 3000
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 3000.0
    # util_fee = 20_000 * 0.17 = 3400
    assert pytest.approx(data["util_fee"], rel=1e-6) == 3400.0
    # accise и VAT = 0 для физ личного использования
    assert data["accise_rub"] == 0.0
    assert data["vat_rub"] == 0.0
    # customs_fee = 500
    assert data["customs_fee"] == 500.0


@pytest.mark.django_db()
def test_hybrid_parallel_jur_over5_min_rule() -> None:
    """Юрлицо, гибрид(паралл), 5-7 лет: duty = max(0.18*price, 1.20*cc)."""
    client = APIClient()
    payload = {
        "price": 10000.0,  # EUR
        "currency": "EUR",
        "engine_cc": 1800,
        "hp": 120,
        "engine_type": "Гибрид(паралл)",
        "age_key": "5_to_7",
        "is_jur": True,
        "is_personal_use": False,
        "dvs_hp": 80,  # для акциза используем ДВС часть; попадает в 0-90 (ставка 0)
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # duty_eur = max(0.18*10000, 1.20*1800) = max(1800, 2160) = 2160
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 2160.0
    # util_fee коммерческий гибрид старше 3 лет: 20_000 * 2.84 = 56800
    assert pytest.approx(data["util_fee"], rel=1e-6) == 56800.0
    # accise по hp=dvs_hp=80 в первой ступени (0 руб/лс) -> 0
    assert data["accise_rub"] == 0.0
    # Для юрлиц VAT > 0
    assert data["vat_rub"] > 0.0


@pytest.mark.django_db()
def test_ev_phys_over5_rules() -> None:
    """Физлицо, электро, >=3 лет: duty = 1 EUR/см³; VAT=0; accise=0; util=5200; customs_fee=500."""
    client = APIClient()
    payload = {
        "price": 10000.0,
        "currency": "EUR",
        "engine_cc": 2000,
        "hp": 150,
        "engine_type": "Электро",
        "age_key": "over_5",
        "is_jur": False,
        "is_personal_use": True,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # duty_eur = 1 * 2000
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 2000.0
    # util_fee = 5200 (старше 3 лет для ФЛ)
    assert pytest.approx(data["util_fee"], rel=1e-6) == 5200.0
    assert data["accise_rub"] == 0.0
    assert data["vat_rub"] == 0.0
    assert data["customs_fee"] == 500.0


@pytest.mark.django_db()
def test_hybrid_series_jur_accise_uses_sum_hp_vs_parallel() -> None:
    """ЮЛ: у последовательного гибрида акциз считается по сумме мощностей и >0, у параллельного с тем же dvs_hp может быть 0."""
    client = APIClient()

    # Series: dvs_hp + electric_hp = 200 hp => ожидаем положительный акциз
    series_payload = {
        "price": 15000.0,
        "currency": "EUR",
        "engine_cc": 1800,
        "hp": 200,
        "engine_type": "Гибрид(послед)",
        "age_key": "under_3",
        "is_jur": True,
        "is_personal_use": False,
        "dvs_hp": 80,
        "electric_hp": 120,
    }
    r1 = client.post(reverse("calculator:estimate"), data=series_payload, format="json")
    assert r1.status_code == status.HTTP_200_OK, r1.content
    d1 = r1.json()
    assert d1["accise_rub"] > 0.0

    # Parallel: используем только dvs_hp=80 => в наших ставках это 0
    parallel_payload = {
        "price": 15000.0,
        "currency": "EUR",
        "engine_cc": 1800,
        "hp": 200,
        "engine_type": "Гибрид(паралл)",
        "age_key": "under_3",
        "is_jur": True,
        "is_personal_use": False,
        "dvs_hp": 80,
    }
    r2 = client.post(reverse("calculator:estimate"), data=parallel_payload, format="json")
    assert r2.status_code == status.HTTP_200_OK, r2.content
    d2 = r2.json()
    assert d2["accise_rub"] == 0.0


@pytest.mark.django_db()
def test_hybrid_parallel_jur_fallback_without_dvs_hp() -> None:
    """ЮЛ: параллельный гибрид без dvs_hp использует fallback 65% от hp для акциза (ожидаем > 0)."""
    client = APIClient()
    payload = {
        "price": 12000.0,
        "currency": "EUR",
        "engine_cc": 1600,
        "hp": 200,
        "engine_type": "Гибрид(паралл)",
        "age_key": "under_3",
        "is_jur": True,
        "is_personal_use": False,
        # dvs_hp отсутствует — задействуется fallback
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    assert data["accise_rub"] > 0.0


@pytest.mark.django_db()
def test_phys_commercial_customs_fee_not_fixed() -> None:
    """ФЛ, но коммерческое использование: таможенный сбор не фикс 500."""
    client = APIClient()
    payload = {
        "price": 8000.0,
        "currency": "EUR",
        "engine_cc": 1600,
        "hp": 110,
        "engine_type": "Бензин",
        "age_key": "under_3",
        "is_jur": False,
        "is_personal_use": False,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    assert data["customs_fee"] != 500.0
    assert data["customs_fee"] > 500.0


@pytest.mark.django_db()
@pytest.mark.parametrize("case", [
    {
        "title": "Физ <3 лет бензин 1999см³ 150лс 20k EUR",
        "payload": {
            "price": 20000.0,
            "currency": "EUR",
            "engine_cc": 1999,
            "hp": 150,
            "engine_type": "Бензин",
            "age_key": "under_3",
            "is_jur": False,
            "is_personal_use": True,
        },
    },
    {
        "title": "Физ 3-5 лет дизель 1600см³ 110лс 8k USD",
        "payload": {
            "price": 8000.0,
            "currency": "USD",
            "engine_cc": 1600,
            "hp": 110,
            "engine_type": "Дизель",
            "age_key": "3_to_5",
            "is_jur": False,
            "is_personal_use": True,
        },
    },
    {
        "title": "Юр бенз 3-5 лет 2200см³ 180лс 15k EUR",
        "payload": {
            "price": 15000.0,
            "currency": "EUR",
            "engine_cc": 2200,
            "hp": 180,
            "engine_type": "Бензин",
            "age_key": "3_to_5",
            "is_jur": True,
            "is_personal_use": False,
        },
    },
    {
        "title": ">=7 лет дизель юр 3000см³ 240лс 10k EUR",
        "payload": {
            "price": 10000.0,
            "currency": "EUR",
            "engine_cc": 3000,
            "hp": 240,
            "engine_type": "Дизель",
            "age_key": "over_7",
            "is_jur": True,
            "is_personal_use": False,
        },
    },
])
def test_estimate_endpoint_smoke(case: dict) -> None:
    client = APIClient()
    url = reverse("calculator:estimate")
    resp = client.post(url, data=case["payload"], format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # Basic shape
    for key in [
        "price_rub",
        "price_eur",
        "duty_eur",
        "duty_rub",
        "util_fee",
        "accise_rub",
        "vat_rub",
        "customs_fee",
        "subtotal_customs",
    ]:
        assert key in data
        assert isinstance(data[key], (int, float))
        assert data[key] >= 0


@pytest.mark.django_db()
def test_service_matches_endpoint_for_sample_case() -> None:
    # Select a sample case
    payload = {
        "price": 15000.0,
        "currency": "EUR",
        "engine_cc": 2200,
        "hp": 180,
        "engine_type": "Бензин",
        "age_key": "3_to_5",
        "is_jur": True,
        "is_personal_use": False,
    }

    # Call API
    client = APIClient()
    url = reverse("calculator:estimate")
    resp = client.post(url, data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    api_data = resp.json()

    # Call service directly (use the same provider factory as API to avoid mismatch)
    svc = CalculatorService(get_default_currency_provider())
    calc = svc.build_calculator()
    res = calc.estimate(EstimateInput(**payload))

    # Compare main numbers with a small tolerance
    def almost(a: float, b: float, eps: float = 1e-6) -> bool:
        return abs(float(a) - float(b)) <= eps * max(1.0, abs(float(b)))

    assert almost(api_data["subtotal_customs"], res.subtotal_customs)
    assert almost(api_data["duty_rub"], res.duty_rub)
    assert almost(api_data["vat_rub"], res.vat_rub)
    assert almost(api_data["util_fee"], res.util_fee)
    assert almost(api_data["customs_fee"], res.customs_fee)
