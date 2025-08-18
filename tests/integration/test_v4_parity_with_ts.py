import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
from rest_framework.test import APIClient
from django.core.management import call_command

# Автосидинг только V4 non-car+сопутствующие ставки через версионированную фикстуру
@pytest.fixture(autouse=True, scope="session")
def _seed_v4_noncar_only(django_db_setup, django_db_blocker):  # type: ignore[no-untyped-def]
    with django_db_blocker.unblock():
        call_command(
            "seed_customs_rates",
            "--replace",
            "--path",
            "api/calculator/fixtures",
            "--version-tag",
            "2025_08_17",
        )


def _load_ts_module():
    """Динамически загружаем calculator-ts/customs_calculator_v4.py как модуль."""
    repo_root = Path(__file__).resolve().parents[2]
    ts_path = repo_root / "calculator-ts" / "customs_calculator_v4.py"
    spec = importlib.util.spec_from_file_location("customs_calculator_v4", ts_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Не удалось загрузить customs_calculator_v4.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ts = _load_ts_module()


# Фиксируем курсы валют в TS-скрипте, чтобы совпадали с API FixedCurrencyProvider
@pytest.fixture(autouse=True, scope="session")
def _patch_ts_rates_to_fixed():  # type: ignore[no-untyped-def]
    fixed = {
        "RUB": 1.0,
        "EUR": 100.0,
        "USD": 95.0,
        "CNY": 13.5,
        "JPY": 0.65,
        "KRW": 0.07,
    }

    def _fake_get_rates(_cls):  # cls ignored
        return dict(fixed)

    # Перепривязываем classmethod у TS RatesFetcher
    orig = ts.RatesFetcher.get_currency_rates
    ts.RatesFetcher.get_currency_rates = classmethod(_fake_get_rates)
    try:
        yield
    finally:
        ts.RatesFetcher.get_currency_rates = orig


# Маппинги значений из нашего API в TS-энумы
VT_MAP = {
    "quad": ts.VehicleType.QUAD,
    "snowmobile": ts.VehicleType.SNOWMOBILE,
    "motorcycle": ts.VehicleType.MOTORCYCLE,
    "car": ts.VehicleType.CAR,
}

ET_MAP = {
    "Бензин": ts.EngineType.DVS,
    "Дизель": ts.EngineType.DVS,  # для non-car в API только ДВС допустим; различия бенз/дизель для non-car не существенны
}


def _age_years_from_age_key(age_key: str) -> int:
    # Условное соответствие возрастных ключей TS-числам лет
    return {
        "under_3": 2,
        "3_to_5": 4,
        "over_5": 6,
        "5_to_7": 6,
        "over_7": 8,
    }[age_key]


def _ts_importer_type(is_jur: bool, is_personal_use: bool) -> Any:
    if is_jur:
        return ts.ImporterType.JURIDICAL
    return ts.ImporterType.PHYS_PERSONAL if is_personal_use else ts.ImporterType.PHYS_RESALE


# Набор кейсов (сконцентрирован на V4 non-car). При необходимости расширим до авто/EV/гибридов.
CASES: List[Dict[str, Any]] = [
    # QUAD phys
    {"vehicle_type": "quad", "age_key": "under_3", "is_jur": False, "is_personal_use": True,  "engine_cc": 500, "hp": 40,  "price": 10000.0, "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "quad", "age_key": "under_3", "is_jur": False, "is_personal_use": True,  "engine_cc": 500, "hp": 60,  "price": 6000.0,  "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "quad", "age_key": "over_5",  "is_jur": False, "is_personal_use": True,  "engine_cc": 500, "hp": 40,  "price": 8000.0,  "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "quad", "age_key": "over_5",  "is_jur": False, "is_personal_use": True,  "engine_cc": 500, "hp": 60,  "price": 8000.0,  "currency": "EUR", "engine_type": "Бензин"},
    # QUAD jur
    {"vehicle_type": "quad", "age_key": "under_3", "is_jur": True,  "is_personal_use": False, "engine_cc": 500, "hp": 60,  "price": 10000.0, "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "quad", "age_key": "over_5",  "is_jur": True,  "is_personal_use": False, "engine_cc": 500, "hp": 60,  "price": 1000.0,  "currency": "EUR", "engine_type": "Бензин"},  # спровоцировать min €/hp
    {"vehicle_type": "quad", "age_key": "over_5",  "is_jur": True,  "is_personal_use": False, "engine_cc": 500, "hp": 60,  "price": 10000.0, "currency": "EUR", "engine_type": "Бензин"},

    # SNOWMOBILE phys
    {"vehicle_type": "snowmobile", "age_key": "under_3", "is_jur": False, "is_personal_use": True,  "engine_cc": 600, "hp": 80,  "price": 10000.0, "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "snowmobile", "age_key": "under_3", "is_jur": False, "is_personal_use": True,  "engine_cc": 600, "hp": 120, "price": 10000.0, "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "snowmobile", "age_key": "over_5",  "is_jur": False, "is_personal_use": True,  "engine_cc": 600, "hp": 80,  "price": 8000.0,  "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "snowmobile", "age_key": "over_5",  "is_jur": False, "is_personal_use": True,  "engine_cc": 600, "hp": 120, "price": 8000.0,  "currency": "EUR", "engine_type": "Бензин"},
    # SNOWMOBILE jur
    {"vehicle_type": "snowmobile", "age_key": "under_3", "is_jur": True,  "is_personal_use": False, "engine_cc": 600, "hp": 120, "price": 10000.0, "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "snowmobile", "age_key": "over_5",  "is_jur": True,  "is_personal_use": False, "engine_cc": 600, "hp": 120, "price": 1000.0,  "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "snowmobile", "age_key": "over_5",  "is_jur": True,  "is_personal_use": False, "engine_cc": 600, "hp": 120, "price": 10000.0, "currency": "EUR", "engine_type": "Бензин"},

    # MOTORCYCLE phys
    {"vehicle_type": "motorcycle", "age_key": "under_3", "is_jur": False, "is_personal_use": True,  "engine_cc": 100,  "hp": 20,  "price": 3000.0,  "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "motorcycle", "age_key": "under_3", "is_jur": False, "is_personal_use": True,  "engine_cc": 600,  "hp": 70,  "price": 8000.0,  "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "motorcycle", "age_key": "over_5",  "is_jur": False, "is_personal_use": True,  "engine_cc": 100,  "hp": 20,  "price": 3000.0,  "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "motorcycle", "age_key": "over_5",  "is_jur": False, "is_personal_use": True,  "engine_cc": 900,  "hp": 120, "price": 10000.0, "currency": "EUR", "engine_type": "Бензин"},
    # MOTORCYCLE jur
    {"vehicle_type": "motorcycle", "age_key": "under_3", "is_jur": True,  "is_personal_use": False, "engine_cc": 600,  "hp": 70,  "price": 8000.0,  "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "motorcycle", "age_key": "over_5",  "is_jur": True,  "is_personal_use": False, "engine_cc": 100,  "hp": 20,  "price": 3000.0,  "currency": "EUR", "engine_type": "Бензин"},
    {"vehicle_type": "motorcycle", "age_key": "over_5",  "is_jur": True,  "is_personal_use": False, "engine_cc": 900,  "hp": 120, "price": 10000.0, "currency": "EUR", "engine_type": "Бензин"},
]


@pytest.mark.django_db()
@pytest.mark.parametrize("case", CASES)
def test_parity_with_ts(case: Dict[str, Any]) -> None:
    # 1) Запуск эталона TS
    spec = ts.VehicleSpec(
        vehicle_type=VT_MAP[case["vehicle_type"]],
        importer_type=_ts_importer_type(case["is_jur"], case["is_personal_use"]),
        cost_original=float(case["price"]),
        currency=case["currency"],
        age_years=_age_years_from_age_key(case["age_key"]),
        engine_volume_cc=int(case["engine_cc"]),
        power_hp=int(case["hp"]),
        engine_type=ET_MAP[case["engine_type"]],
        dvs_power_hp=0,
        electric_power_hp=0,
    )
    ts_result = ts.calculate_customs_payments(spec)

    # 2) Запуск нашего API
    client = APIClient()
    # Нормализуем age_key для API: для юрлиц 'over_5' недопустимо, используем '5_to_7'
    age_key_for_api = case["age_key"]
    if case["is_jur"] and age_key_for_api == "over_5":
        age_key_for_api = "5_to_7"
    payload = {
        "price": case["price"],
        "currency": case["currency"],
        "engine_cc": case["engine_cc"],
        "hp": case["hp"],
        "vehicle_type": case["vehicle_type"],
        "engine_type": case["engine_type"],
        "age_key": age_key_for_api,
        "is_jur": case["is_jur"],
        "is_personal_use": case["is_personal_use"],
    }
    resp = client.post("/api/v1/calc/estimate/", data=payload, format="json")
    assert resp.status_code == 200, f"API returned {resp.status_code}: {resp.data}"
    api = resp.json()

    # 3) Сравнение компонент (с небольшими допусками от округления)
    def approx(a: float, b: float, tol: float = 0.51) -> bool:
        return abs(float(a) - float(b)) <= tol

    # duty
    assert approx(api["duty_rub"], ts_result.duty_rub), (
        f"duty_rub mismatch: API={api['duty_rub']} TS={ts_result.duty_rub} case={case}"
    )
    # excise/accise
    assert approx(api["accise_rub"], ts_result.excise_rub), (
        f"accise_rub mismatch: API={api['accise_rub']} TS={ts_result.excise_rub} case={case}"
    )
    # VAT
    assert approx(api["vat_rub"], ts_result.vat_rub), (
        f"vat_rub mismatch: API={api['vat_rub']} TS={ts_result.vat_rub} case={case}"
    )
    # Util
    assert approx(api["util_fee"], ts_result.util_fee_rub), (
        f"util_fee mismatch: API={api['util_fee']} TS={ts_result.util_fee_rub} case={case}"
    )
    # Customs fee
    assert approx(api["customs_fee"], ts_result.customs_fee_rub), (
        f"customs_fee mismatch: API={api['customs_fee']} TS={ts_result.customs_fee_rub} case={case}"
    )
