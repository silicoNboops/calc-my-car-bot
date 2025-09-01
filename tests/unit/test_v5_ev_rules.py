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


@pytest.mark.django_db()
def test_v4_ev_phys_over5_duty_is_15_percent_no_min_cc() -> None:
    """v5: EV у физлица, >3 лет — duty = 15% от цены (без 1 EUR/см³), акциз по прогрессивной шкале."""
    client = APIClient()
    payload = {
        "price": 10000.0,  # EUR
        "currency": "EUR",
        "engine_cc": 2000,  # раньше влияло (1 EUR/cc), теперь нет
        "hp": 150,
        "engine_type": "Электро",
        "age_key": "over_5",
        "is_jur": False,
        "is_personal_use": True,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # duty_eur = 0.15 * 10000 = 1500
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 1500.0
    # VAT остаётся 0 для личного использования
    assert data["vat_rub"] == 0.0
    # v5: EV облагается акцизом: 150 л.с. попадает в брекет 61 руб/л.с. => 9150
    assert pytest.approx(data["accise_rub"], rel=1e-6) == 9150.0


@pytest.mark.django_db()
def test_v4_ev_jur_accise_zero() -> None:
    """v5: EV у ЮЛ — акциз по прогрессивной шкале (не 0)."""
    client = APIClient()
    payload = {
        "price": 12000.0,
        "currency": "EUR",
        "engine_cc": 1,
        "hp": 200,  # раньше мог влиять на акциз, теперь должен быть 0
        "engine_type": "Электро",
        "age_key": "under_3",
        "is_jur": True,
        "is_personal_use": False,
    }
    resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # v5: 200 л.с. попадает в брекет 583 руб/л.с. => 116600
    assert pytest.approx(data["accise_rub"], rel=1e-6) == 116600.0
    # Для ЮЛ duty по-прежнему 15% от цены в EUR
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 0.15 * payload["price"]
