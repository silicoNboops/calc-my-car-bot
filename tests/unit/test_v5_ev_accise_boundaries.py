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
    "hp, expected_rate",
    [
        (90, 0),
        (91, 61),
        (150, 61),
        (151, 583),
        (200, 583),
        (201, 955),
        (300, 955),
        (301, 1628),
        (400, 1628),
        (401, 1685),
        (500, 1685),
        (501, 1740),
    ],
)
@pytest.mark.django_db()
def test_v5_ev_accise_progressive_boundaries(hp: int, expected_rate: int) -> None:
    """Проверяет прогрессивные брекеты акциза для EV по граничным значениям л.с.

    Брейкпойнты из фикстуры `customs_rates_v5_2025_08_17.json` (accise_rates):
    - <=90 => 0
    - 91..150 => 61
    - 151..200 => 583
    - 201..300 => 955
    - 301..400 => 1628
    - 401..500 => 1685
    - >500 => 1740
    """
    client = APIClient()
    payload = {
        "price": 1.0,  # EUR, минимальная цена чтобы не влиять на VAT/пошлину в проверке акциза
        "currency": "EUR",
        "engine_cc": 1,
        "hp": hp,
        "engine_type": "Электро",
        "age_key": "under_3",
        "is_jur": False,
        "is_personal_use": True,  # личное использование: VAT=0, акциз для EV всё равно применяется
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()

    expected_accise = hp * expected_rate
    assert pytest.approx(data["accise_rub"], rel=1e-6) == expected_accise

    # Доп. проверки инвариантов для EV
    assert data["vat_rub"] == 0.0  # личное использование
    # Пошлина 15% от цены в EUR — не предмет проверки здесь, но должна быть >0
    assert data["duty_eur"] > 0
