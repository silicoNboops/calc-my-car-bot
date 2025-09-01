from __future__ import annotations

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


# Автосидирование ставок для всего тестового сеанса этого модуля
@pytest.fixture(autouse=True, scope="session")
def _seed_customs_rates(django_db_setup, django_db_blocker):  # type: ignore[no-untyped-def]
    with django_db_blocker.unblock():
        call_command("seed_customs_rates", "--replace", "--path", "api/calculator/fixtures")


@pytest.mark.parametrize(
    "dvs_hp, e_hp, expected_rate",
    [
        (90, 0, 0),
        (91, 0, 61),
        (150, 0, 61),
        (151, 0, 583),
        (200, 0, 583),
        (201, 0, 955),
    ],
)
@pytest.mark.django_db()
def test_v5_hybrid_series_accise_by_sum_boundaries(dvs_hp: int, e_hp: int, expected_rate: int) -> None:
    """Серийный гибрид: мощность для акциза = dvs_hp + electric_hp. Проверяем границы брекетов."""
    client = APIClient()
    total_hp = dvs_hp + e_hp
    payload = {
        "price": 0.0,  # чтобы VAT не зависел от цены, акциз проверяем отдельно
        "currency": "EUR",
        "engine_cc": 1500,
        "hp": max(1, total_hp),  # общее hp (не влияет на формулу для series)
        "engine_type": "Гибрид(послед)",
        "age_key": "under_3",
        "is_jur": True,  # акциз для не-EV применяем только при коммерции/ЮЛ
        "is_personal_use": False,
        "dvs_hp": dvs_hp,
        "electric_hp": e_hp,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()

    expected_accise = total_hp * expected_rate
    assert pytest.approx(data["accise_rub"], rel=1e-6) == expected_accise


@pytest.mark.parametrize(
    "given_dvs_hp, hp, expected_power_for_tax, expected_rate",
    [
        # С явно заданным dvs_hp — используем его напрямую
        (150, 999, 150, 61),  # <=150
        (151, 120, 151, 583),  # >150..200
        # Без dvs_hp — используем int(hp * 0.65)
        (None, 231, 150, 61),  # 0.65*231=150.15 -> int=150
        (None, 233, 151, 583),  # 0.65*233=151.45 -> int=151
    ],
)
@pytest.mark.django_db()
def test_v5_hybrid_parallel_accise_power_selection(
        given_dvs_hp: int | None,
        hp: int,
        expected_power_for_tax: int,
        expected_rate: int,
) -> None:
    """Параллельный гибрид: мощность для акциза = dvs_hp, иначе int(hp*0.65). Проверяем границы и усечение."""
    client = APIClient()
    payload = {
        "price": 0.0,
        "currency": "EUR",
        "engine_cc": 1600,
        "hp": hp,
        "engine_type": "Гибрид(паралл)",
        "age_key": "under_3",
        "is_jur": True,
        "is_personal_use": False,
    }
    if given_dvs_hp is not None:
        payload["dvs_hp"] = given_dvs_hp
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()

    expected_accise = expected_power_for_tax * expected_rate
    assert pytest.approx(data["accise_rub"], rel=1e-6) == expected_accise
