from __future__ import annotations

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from calculator.customs_calculator_v5 import (
    VehicleSpec,
    VehicleType,
    EngineType,
    ImporterType,
    calc_excise,
)


# Автосидирование ставок для всего тестового сеанса этого модуля
@pytest.fixture(autouse=True, scope="session")
def _seed_customs_rates(django_db_setup, django_db_blocker):  # type: ignore[no-untyped-def]
    with django_db_blocker.unblock():
        call_command("seed_customs_rates", "--replace", "--path", "api/calculator/fixtures")


def _spec_from_payload(payload: dict) -> VehicleSpec:
    # Определяем тип импортера: для паритета акциза достаточно ФЛ личное или ЮЛ
    importer = ImporterType.JURIDICAL if payload.get("is_jur") else ImporterType.PHYS_PERSONAL
    # Маппинг engine_type из API русских строк на канон
    et = payload.get("engine_type")
    if et == "Электро":
        eng = EngineType.ELECTRIC
    elif et == "Гибрид(послед)":
        eng = EngineType.HYBRID_SERIES
    elif et == "Гибрид(паралл)":
        eng = EngineType.HYBRID_PARALLEL
    else:
        eng = EngineType.DVS

    return VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=importer,
        cost_original=float(payload.get("price", 0.0)),
        currency=str(payload.get("currency", "EUR")),
        age_years=2 if payload.get("age_key") == "under_3" else 6,
        engine_volume_cc=int(payload.get("engine_cc", 0)),
        power_hp=int(payload.get("hp", 0)),
        engine_type=eng,
        dvs_power_hp=int(payload.get("dvs_hp", 0) or 0),
        electric_power_hp=int(payload.get("electric_hp", 0) or 0),
    )


@pytest.mark.parametrize("hp", [90, 150, 151, 200, 201, 500])
@pytest.mark.django_db()
def test_parity_ev_accise_vs_canon(hp: int) -> None:
    client = APIClient()
    payload = {
        "price": 1.0,  # EUR — минимально, чтобы не влиять на VAT
        "currency": "EUR",
        "engine_cc": 1,
        "hp": hp,
        "engine_type": "Электро",
        "age_key": "under_3",
        "is_jur": False,
        "is_personal_use": True,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()

    spec = _spec_from_payload(payload)
    canon = calc_excise(spec)

    assert pytest.approx(data["accise_rub"], rel=1e-6) == canon


@pytest.mark.parametrize(
    "dvs_hp, e_hp",
    [
        (90, 60),  # всего 150 → ставка 61
        (100, 51),  # всего 151 → ставка 583
        (180, 30),  # всего 210 → ставка 955
    ],
)
@pytest.mark.django_db()
def test_parity_hybrid_series_accise_vs_canon(dvs_hp: int, e_hp: int) -> None:
    client = APIClient()
    total_hp = dvs_hp + e_hp
    payload = {
        "price": 0.0,
        "currency": "EUR",
        "engine_cc": 1600,
        "hp": total_hp,
        "engine_type": "Гибрид(послед)",
        "age_key": "under_3",
        "is_jur": True,
        "is_personal_use": False,
        "dvs_hp": dvs_hp,
        "electric_hp": e_hp,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()

    spec = _spec_from_payload(payload)
    canon = calc_excise(spec)

    assert pytest.approx(data["accise_rub"], rel=1e-6) == canon


@pytest.mark.parametrize(
    "given_dvs_hp, hp",
    [
        (150, 999),  # dvs_hp=150 → ставка 61
        (151, 120),  # dvs_hp=151 → ставка 583
    ],
)
@pytest.mark.django_db()
def test_parity_hybrid_parallel_accise_vs_canon_with_dvs(given_dvs_hp: int, hp: int) -> None:
    client = APIClient()
    payload = {
        "price": 0.0,
        "currency": "EUR",
        "engine_cc": 1800,
        "hp": hp,
        "engine_type": "Гибрид(паралл)",
        "age_key": "under_3",
        "is_jur": True,
        "is_personal_use": False,
        "dvs_hp": given_dvs_hp,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()

    spec = _spec_from_payload(payload)
    canon = calc_excise(spec)

    assert pytest.approx(data["accise_rub"], rel=1e-6) == canon


@pytest.mark.parametrize(
    "hp",
    [
        231,  # int(0.65*231)=150 → ставка 61
        233,  # int(0.65*233)=151 → ставка 583
    ],
)
@pytest.mark.django_db()
def test_parity_hybrid_parallel_accise_vs_canon_fallback(hp: int) -> None:
    client = APIClient()
    payload = {
        "price": 0.0,
        "currency": "EUR",
        "engine_cc": 1800,
        "hp": hp,
        "engine_type": "Гибрид(паралл)",
        "age_key": "under_3",
        "is_jur": True,
        "is_personal_use": False,
        # dvs_hp отсутствует — должен сработать fallback 65%
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()

    spec = _spec_from_payload(payload)
    canon = calc_excise(spec)

    assert pytest.approx(data["accise_rub"], rel=1e-6) == canon
