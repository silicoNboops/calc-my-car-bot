# quick_tests.py — Быстрые проверки расчётов без интерактива
# Использует те же классы и ставки, что и CLI в customs_calculator_v1.py

from typing import Dict, Any
from customs_calculator_v1 import RatesStore, CustomsCalculator


def run_case(calc: CustomsCalculator, case: Dict[str, Any]) -> Dict[str, float]:
    # входные параметры
    price_native = case["price"]
    currency_code = case["currency"]  # 'EUR', 'USD', 'RUB', ...
    engine_cc = case["engine_cc"]
    hp = case["hp"]
    engine_type = case.get("engine_type", "Бензин")  # "Бензин" | "Дизель"
    age_key = case["age_key"]  # 'under_3' | '3_to_5' | '5_to_7' | 'over_7'
    is_jur = case["is_jur"]
    is_personal_use = case.get("is_personal_use", not is_jur)
    is_commercial = is_jur or not is_personal_use

    # конвертации валют
    fx = calc.fx
    price_rub = price_native * fx[currency_code]
    price_eur = price_rub / fx["EUR"]

    # пошлина (в EUR возвращается из _calc_duty)
    duty_eur = calc._calc_duty(price_eur, engine_cc, age_key, is_jur, engine_type)
    duty_rub = duty_eur * fx["EUR"]

    # утиль, акциз, НДС, таможенный сбор
    util_fee = calc._calc_util(is_commercial, age_key, engine_cc)
    accise_rub = calc._calc_accise(hp) if is_commercial else 0.0
    vat_rub = calc._calc_vat(price_rub, duty_rub, accise_rub) if is_commercial else 0.0
    customs_fee = calc._calc_customs_fee(price_rub)

    subtotal_customs = duty_rub + customs_fee + util_fee + accise_rub + vat_rub

    return {
        "price_rub": price_rub,
        "price_eur": price_eur,
        "duty_eur": duty_eur,
        "duty_rub": duty_rub,
        "util_fee": util_fee,
        "accise_rub": accise_rub,
        "vat_rub": vat_rub,
        "customs_fee": customs_fee,
        "subtotal_customs": subtotal_customs,
    }


def fmt(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ").replace(".", ",")


def main():
    store = RatesStore()
    calc = CustomsCalculator(store)

    cases = [
        # 1) Физлицо, <3 лет, бензин, 1999 см³, 150 лс, цена 20 000 EUR
        {
            "title": "Физ <3 лет бензин 1999см³ 150лс 20k EUR",
            "price": 20000.0,
            "currency": "EUR",
            "engine_cc": 1999,
            "hp": 150,
            "engine_type": "Бензин",
            "age_key": "under_3",
            "is_jur": False,
            "is_personal_use": True,
        },
        # 2) Физлицо, 3-5 лет, дизель, 1600 см³, 110 лс, цена 8 000 USD
        {
            "title": "Физ 3-5 лет дизель 1600см³ 110лс 8k USD",
            "price": 8000.0,
            "currency": "USD",
            "engine_cc": 1600,
            "hp": 110,
            "engine_type": "Дизель",
            "age_key": "3_to_5",
            "is_jur": False,
            "is_personal_use": True,
        },
        # 3) Юрлицо бензин 3-5 лет, 2200 см³, 180 лс, цена 15 000 EUR (коммерческий)
        {
            "title": "Юр бенз 3-5 лет 2200см³ 180лс 15k EUR",
            "price": 15000.0,
            "currency": "EUR",
            "engine_cc": 2200,
            "hp": 180,
            "engine_type": "Бензин",
            "age_key": "3_to_5",
            "is_jur": True,
        },
        # 4) Юрлицо дизель >7 лет, 3000 см³, 240 лс, цена 10 000 EUR (коммерческий)
        {
            "title": ">=7 лет дизель юр 3000см³ 240лс 10k EUR",
            "price": 10000.0,
            "currency": "EUR",
            "engine_cc": 3000,
            "hp": 240,
            "engine_type": "Дизель",
            "age_key": "over_7",
            "is_jur": True,
        },
    ]

    for i, case in enumerate(cases, 1):
        res = run_case(calc, case)
        print("\n" + "=" * 70)
        print(f"КЕЙС {i}: {case['title']}")
        print("-" * 70)
        print(f"Стоимость: {fmt(res['price_rub'])} ₽  ({fmt(case['price'])} {case['currency']})")
        print(f"Пошлина:  {fmt(res['duty_rub'])} ₽  ({fmt(res['duty_eur'])} €)")
        print(f"Таможенный сбор: {fmt(res['customs_fee'])} ₽")
        print(f"Утильсбор: {fmt(res['util_fee'])} ₽")
        if res['accise_rub'] > 0:
            print(f"Акциз: {fmt(res['accise_rub'])} ₽")
        if res['vat_rub'] > 0:
            print(f"НДС:   {fmt(res['vat_rub'])} ₽")
        print(f"ИТОГО растаможка: {fmt(res['subtotal_customs'])} ₽")
        print("Примечание: без учёта доставки. Курсы ЦБ РФ из сети либо fallback.")


if __name__ == "__main__":
    main()
