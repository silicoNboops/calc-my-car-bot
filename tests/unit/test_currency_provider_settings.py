from __future__ import annotations

from django.test import override_settings

from api.calculator.services import (
    CbrfCurrencyProvider,
    FixedCurrencyProvider,
    get_default_currency_provider,
)


def test_get_default_currency_provider_fixed_flag() -> None:
    with override_settings(USE_FIXED_CURRENCY_PROVIDER=True):
        provider = get_default_currency_provider()
        assert isinstance(provider, FixedCurrencyProvider)

    with override_settings(USE_FIXED_CURRENCY_PROVIDER=False):
        provider = get_default_currency_provider()
        assert isinstance(provider, CbrfCurrencyProvider)


def test_cbr_provider_reads_url_and_ttl_from_settings() -> None:
    with override_settings(CBR_URL="https://example.test/cbr.json", CBR_CACHE_TTL=123):
        p = CbrfCurrencyProvider()
        assert p.url == "https://example.test/cbr.json"
        assert p.cache_timeout == 123

    # Переопределение аргументами конструктора важнее settings
    with override_settings(CBR_URL="https://should.not/use", CBR_CACHE_TTL=999):
        p2 = CbrfCurrencyProvider(cache_timeout_seconds=45, url="https://override")
        assert p2.url == "https://override"
        assert p2.cache_timeout == 45
