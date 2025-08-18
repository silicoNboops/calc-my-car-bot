from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.core.management import call_command


# Автозагрузка ставок для тестовой БД из JSON-фикстур (один раз на сессию)
@pytest.fixture(autouse=True, scope="session")
def _seed_customs_rates(django_db_setup, django_db_blocker):  # type: ignore[no-untyped-def]
    with django_db_blocker.unblock():
        call_command("seed_customs_rates", "--replace", "--path", "api/calculator/fixtures")

# QUAD tests
@pytest.mark.django_db()
def test_v4_quad_phys_under3_uses_max_of_percent_and_min_per_hp() -> None:
    client = APIClient()
    payload = {
        "price": 10000.0,  # EUR
        "currency": "EUR",
        "engine_cc": 500,  # не используется для QUAD duty в v4
        "hp": 40,  # <= 50 hp
        "vehicle_type": "quad",
        "engine_type": "Бензин",
        "age_key": "under_3",
        "is_jur": False,
        "is_personal_use": True,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # v4: rate 25%, min {<=50:1.0, >50:2.0} EUR/HP -> max(0.25*10000=2500, 40*1.0=40) = 2500
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 2500.0


@pytest.mark.django_db()
def test_v4_quad_phys_over3_uses_eur_per_hp() -> None:
    client = APIClient()
    payload = {
        "price": 5000.0,
        "currency": "EUR",
        "engine_cc": 600,
        "hp": 60,  # > 50 hp
        "vehicle_type": "quad",
        "engine_type": "Бензин",
        "age_key": "over_5",  # у ФЛ нормализуется
        "is_jur": False,
        "is_personal_use": True,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # v4: EUR/HP {<=50:1.0, >50:2.0} -> 60*2.0 = 120
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 120.0


@pytest.mark.django_db()
def test_v4_quad_jur_under3_percent_15() -> None:
    client = APIClient()
    payload = {
        "price": 8000.0,
        "currency": "EUR",
        "engine_cc": 500,
        "hp": 70,
        "vehicle_type": "quad",
        "engine_type": "Бензин",
        "age_key": "under_3",
        "is_jur": True,
        "is_personal_use": False,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 0.15 * payload["price"]


@pytest.mark.django_db()
def test_v4_quad_jur_over3_max_percent_vs_min_hp() -> None:
    client = APIClient()
    payload = {
        "price": 1000.0,
        "currency": "EUR",
        "engine_cc": 500,
        "hp": 500,
        "vehicle_type": "quad",
        "engine_type": "Бензин",
        "age_key": "5_to_7",
        "is_jur": True,
        "is_personal_use": False,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # max(20%*1000=200, 0.5*500=250) = 250
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 250.0


# SNOWMOBILE tests
@pytest.mark.django_db()
def test_v4_snowmobile_phys_under3_max_percent_vs_min_hp() -> None:
    client = APIClient()
    payload = {
        "price": 10000.0,
        "currency": "EUR",
        "engine_cc": 800,
        "hp": 120,  # >100
        "vehicle_type": "snowmobile",
        "engine_type": "Бензин",
        "age_key": "under_3",
        "is_jur": False,
        "is_personal_use": True,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # max(15%*10000=1500, 120*3.0=360) -> 1500
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 1500.0


@pytest.mark.django_db()
def test_v4_snowmobile_phys_over3_eur_per_hp_threshold() -> None:
    client = APIClient()
    payload = {
        "price": 4000.0,
        "currency": "EUR",
        "engine_cc": 700,
        "hp": 80,  # <=100
        "vehicle_type": "snowmobile",
        "engine_type": "Бензин",
        "age_key": "over_5",
        "is_jur": False,
        "is_personal_use": True,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # EUR/HP {<=100:1.5, >100:3.0} -> 80*1.5 = 120
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 120.0


@pytest.mark.django_db()
def test_v4_snowmobile_jur_under3_percent_10() -> None:
    client = APIClient()
    payload = {
        "price": 9000.0,
        "currency": "EUR",
        "engine_cc": 700,
        "hp": 90,
        "vehicle_type": "snowmobile",
        "engine_type": "Бензин",
        "age_key": "under_3",
        "is_jur": True,
        "is_personal_use": False,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 0.10 * payload["price"]


@pytest.mark.django_db()
def test_v4_snowmobile_jur_over3_max_percent_vs_min_hp() -> None:
    client = APIClient()
    payload = {
        "price": 1000.0,
        "currency": "EUR",
        "engine_cc": 700,
        "hp": 120,
        "vehicle_type": "snowmobile",
        "engine_type": "Бензин",
        "age_key": "5_to_7",
        "is_jur": True,
        "is_personal_use": False,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # max(15%*1000=150, 1.0*120=120) = 150
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 150.0


# MOTORCYCLE tests
@pytest.mark.django_db()
def test_v4_motorcycle_phys_under3_percent_with_min_by_cc() -> None:
    client = APIClient()
    payload = {
        "price": 5000.0,
        "currency": "EUR",
        "engine_cc": 600,  # -> bracket <=800: 20% min 1.2
        "hp": 70,
        "vehicle_type": "motorcycle",
        "engine_type": "Бензин",
        "age_key": "under_3",
        "is_jur": False,
        "is_personal_use": True,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # max(20%*5000=1000, 600*1.2=720) -> 1000
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 1000.0


@pytest.mark.django_db()
def test_v4_motorcycle_phys_over3_eur_per_cc() -> None:
    client = APIClient()
    payload = {
        "price": 10000.0,
        "currency": "EUR",
        "engine_cc": 900,  # >800 => 1.5 EUR/cc
        "hp": 100,
        "vehicle_type": "motorcycle",
        "engine_type": "Бензин",
        "age_key": "over_5",
        "is_jur": False,
        "is_personal_use": True,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 900 * 1.5


@pytest.mark.django_db()
def test_v4_motorcycle_jur_under3_percent_6() -> None:
    client = APIClient()
    payload = {
        "price": 7000.0,
        "currency": "EUR",
        "engine_cc": 250,
        "hp": 50,
        "vehicle_type": "motorcycle",
        "engine_type": "Бензин",
        "age_key": "under_3",
        "is_jur": True,
        "is_personal_use": False,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 0.06 * payload["price"]


@pytest.mark.django_db()
def test_v4_motorcycle_jur_over3_percent_with_min_by_cc() -> None:
    client = APIClient()
    payload = {
        "price": 10000.0,
        "currency": "EUR",
        "engine_cc": 900,  # >800 => min 0.25 EUR/cc
        "hp": 150,
        "vehicle_type": "motorcycle",
        "engine_type": "Бензин",
        "age_key": "5_to_7",
        "is_jur": True,
        "is_personal_use": False,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # max(10%*10000=1000, 900*0.25=225) -> 1000
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 1000.0
