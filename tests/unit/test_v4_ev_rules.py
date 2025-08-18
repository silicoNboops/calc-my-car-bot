from __future__ import annotations

import os
import contextlib

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@contextlib.contextmanager
def _v4_enabled_env():
    prev = os.environ.get("V4_CALC_ENABLED")
    os.environ["V4_CALC_ENABLED"] = "true"
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop("V4_CALC_ENABLED", None)
        else:
            os.environ["V4_CALC_ENABLED"] = prev


@pytest.mark.django_db()
def test_v4_ev_phys_over5_duty_is_15_percent_no_min_cc() -> None:
    """При включенном V4_CALC_ENABLED: EV у физлица, >3 лет — duty = 15% от цены, без 1 EUR/см³."""
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
    with _v4_enabled_env():
        resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # duty_eur = 0.15 * 10000 = 1500
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 1500.0
    # VAT/Accise остаются 0 для личного использования
    assert data["vat_rub"] == 0.0
    assert data["accise_rub"] == 0.0


@pytest.mark.django_db()
def test_v4_ev_jur_accise_zero() -> None:
    """При включенном V4_CALC_ENABLED: EV у ЮЛ — акциз всегда 0."""
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
    with _v4_enabled_env():
        resp = client.post(reverse("calculator:estimate"), data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    assert data["accise_rub"] == 0.0
    # Для ЮЛ duty по-прежнему 15% от цены в EUR
    assert pytest.approx(data["duty_eur"], rel=1e-6) == 0.15 * payload["price"]
