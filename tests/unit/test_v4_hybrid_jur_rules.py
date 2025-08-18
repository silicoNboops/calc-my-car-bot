from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db()
def test_v4_hybrid_jur_uses_benzine_tables() -> None:
    """
    V4: ЮЛ гибрид считается как бензин. Проверяем эквивалентность результата duties.
    Не завязываемся на конкретные значения таблиц — сравниваем ответ для гибрида с ответом для бензина при одинаковых входах.
    """
    client = APIClient()
    common = {
        "price": 14000.0,
        "currency": "EUR",
        "engine_cc": 1800,
        "hp": 140,
        "age_key": "3_to_5",
        "is_jur": True,
        "is_personal_use": False,
    }

    payload_hybrid = {**common, "engine_type": "Гибрид(паралл)"}
    r1 = client.post(reverse("calculator:estimate"), data=payload_hybrid, format="json")
    assert r1.status_code == status.HTTP_200_OK, r1.content
    d1 = r1.json()

    payload_benz = {**common, "engine_type": "Бензин"}
    r2 = client.post(reverse("calculator:estimate"), data=payload_benz, format="json")
    assert r2.status_code == status.HTTP_200_OK, r2.content
    d2 = r2.json()

    assert d1["duty_eur"] == pytest.approx(d2["duty_eur"], rel=1e-9)
