from __future__ import annotations

from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest
from django.core.cache import cache

from api.calculator.services import CbrfCurrencyProvider, FixedCurrencyProvider


def _fake_cbr_json(valutes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    return {"Valute": valutes}


def _clear_provider_cache() -> None:
    try:
        cache.delete("currency_rates_cbrf_v1")
    except Exception:
        # В среде без Redis (локальные/CI-тесты) игнорируем ошибки удаления
        pass
    # Сбросим процессный кэш провайдера на случай отсутствия Redis
    CbrfCurrencyProvider._mem_cache = None


def test_cbrf_provider_success_uses_cache_between_calls() -> None:
    _clear_provider_cache()

    # 1-й вызов: успешный ответ ЦБ
    payload = _fake_cbr_json({
        "EUR": {"Value": 93.7, "Nominal": 1},
        "USD": {"Value": 80.0, "Nominal": 1},
        "CNY": {"Value": 11.1, "Nominal": 1},
        "JPY": {"Value": 0.54, "Nominal": 1},
        "KRW": {"Value": 0.057, "Nominal": 1},
    })

    with patch("api.calculator.services.requests.get") as mget:
        resp = Mock()
        resp.json.return_value = payload
        resp.raise_for_status.return_value = None
        mget.return_value = resp

        provider = CbrfCurrencyProvider(cache_timeout_seconds=3600)
        rates1 = provider.get_rates()
        assert rates1["RUB"] == 1.0
        assert pytest.approx(rates1["EUR"], rel=1e-6) == 93.7
        assert pytest.approx(rates1["USD"], rel=1e-6) == 80.0

        # 2-й вызов: должен прийти из кэша, без сетевого запроса
        mget.reset_mock()
        rates2 = provider.get_rates()
        mget.assert_not_called()
        assert rates2 == rates1


def test_cbrf_provider_missing_eur_triggers_fallback() -> None:
    _clear_provider_cache()

    # Ответ без EUR — должен сработать fallback
    payload = _fake_cbr_json({
        "USD": {"Value": 80.0, "Nominal": 1},
    })

    with patch("api.calculator.services.requests.get") as mget, \
         patch.object(FixedCurrencyProvider, "get_rates", return_value={
             "RUB": 1.0, "EUR": 100.0, "USD": 95.0, "CNY": 13.5, "JPY": 0.65, "KRW": 0.07
         }) as mfallback:
        resp = Mock()
        resp.json.return_value = payload
        resp.raise_for_status.return_value = None
        mget.return_value = resp

        provider = CbrfCurrencyProvider(cache_timeout_seconds=1)
        rates = provider.get_rates()

        # Убедимся, что использован fallback
        mfallback.assert_called_once()
        assert rates["EUR"] == 100.0
        assert rates["RUB"] == 1.0


def test_cbrf_provider_network_error_fallback() -> None:
    _clear_provider_cache()

    with patch("api.calculator.services.requests.get", side_effect=Exception("boom")), \
         patch.object(FixedCurrencyProvider, "get_rates", return_value={
             "RUB": 1.0, "EUR": 100.0, "USD": 95.0, "CNY": 13.5, "JPY": 0.65, "KRW": 0.07
         }) as mfallback:
        provider = CbrfCurrencyProvider(cache_timeout_seconds=1)
        rates = provider.get_rates()

        mfallback.assert_called_once()
        assert rates["EUR"] == 100.0
        assert rates["RUB"] == 1.0
