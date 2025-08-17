
# main.py — Таможенный калькулятор с БД ставок (SQLite) и обновлением
# Версия 21.0 (16.08.2025, Asia/Bangkok)
#
# Что нового:
# - Хранение ставок в SQLite (`customs_rates.db`), загрузка при старте.
# - Классы RatesFetcher (курсы ЦБ РФ) и RatesStore (работа с БД).
# - Режимы: расчёт / инициализация БД дефолтами / "заглушка" обновления ставок из оф. источников.
# - Структура ставок совместима с будущим скрейпингом (не требуется переписывать калькулятор).
#
# Примечание: курсы валют берутся с API ЦБ РФ (https://www.cbr-xml-daily.ru/daily_json.js).
# В среде без интернета будет использован fallback.

import sqlite3
import requests
import datetime
import logging
import os
from typing import Dict, Any, Optional, List

DB_PATH = os.environ.get("CUSTOMS_DB_PATH", os.path.join(os.path.dirname(__file__), "customs_rates.db"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------- Курсы валют ----------

class RatesFetcher:
    CURRENCY_API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
    SUPPORTED = ["EUR", "USD", "CNY", "JPY", "KRW", "RUB"]

    @staticmethod
    def get_currency_rates() -> Dict[str, float]:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            resp = requests.get(RatesFetcher.CURRENCY_API_URL, timeout=10)
            resp.raise_for_status()
            j = resp.json()
            res = {"RUB": 1.0}
            for code in RatesFetcher.SUPPORTED:
                if code == "RUB": 
                    continue
                val = j["Valute"][code]["Value"]
                nominal = j["Valute"][code]["Nominal"]
                res[code] = float(val) / float(nominal)
            logging.info(f"Курсы валют (ЦБ РФ) на {now}: EUR={res['EUR']:.4f}")
            return res
        except Exception as e:
            logging.warning(f"Не удалось получить курсы ЦБ РФ: {e}. Использую fallback.")
            return {"EUR": 100.0, "USD": 95.0, "CNY": 13.5, "JPY": 0.65, "KRW": 0.07, "RUB": 1.0}

# ---------- Дефолтные ставки (актуализируйте при изменениях нормативки) ----------

DEFAULT_RATES: Dict[str, Any] = {
    "PASSENGER_CAR_PHYS": {
        "DUTY_RATES": {
            "under_3_years": [
                {"max_value": 8500, "rate_percent": 0.54, "min_rate_eur_cc": 2.5},
                {"max_value": 16700, "rate_percent": 0.48, "min_rate_eur_cc": 3.5},
                {"max_value": 42300, "rate_percent": 0.48, "min_rate_eur_cc": 5.5},
                {"max_value": 84500, "rate_percent": 0.48, "min_rate_eur_cc": 7.5},
                {"max_value": 169000, "rate_percent": 0.48, "min_rate_eur_cc": 15.0},
                {"max_value": float('inf'), "rate_percent": 0.48, "min_rate_eur_cc": 20.0},
            ],
            "3_to_5_years": [
                {"max_cc": 1000, "rate_eur_cc": 1.5}, {"max_cc": 1500, "rate_eur_cc": 1.7},
                {"max_cc": 1800, "rate_eur_cc": 2.5}, {"max_cc": 2300, "rate_eur_cc": 2.7},
                {"max_cc": 3000, "rate_eur_cc": 3.0}, {"max_cc": float('inf'), "rate_eur_cc": 3.6},
            ],
            "over_5_years": [
                {"max_cc": 1000, "rate_eur_cc": 3.0}, {"max_cc": 1500, "rate_eur_cc": 3.2},
                {"max_cc": 1800, "rate_eur_cc": 3.5}, {"max_cc": 2300, "rate_eur_cc": 4.8},
                {"max_cc": 3000, "rate_eur_cc": 5.0}, {"max_cc": float('inf'), "rate_eur_cc": 5.7},
            ]
        }
    },
    "PASSENGER_CAR_JUR_BENZ": {
        "DUTY_RATES": {
            "under_3_years": [
                {"max_cc": 3000, "rate_percent": 0.15}, {"max_cc": float('inf'), "rate_percent": 0.125},
            ],
            "3_to_5_years": [
                {"max_cc": 1000, "rate_percent": 0.20, "min_rate_eur_cc": 0.36},
                {"max_cc": 1500, "rate_percent": 0.20, "min_rate_eur_cc": 0.4},
                {"max_cc": 1800, "rate_percent": 0.20, "min_rate_eur_cc": 0.36},
                {"max_cc": 2300, "rate_percent": 0.20, "min_rate_eur_cc": 0.44},
                {"max_cc": 3000, "rate_percent": 0.20, "min_rate_eur_cc": 0.44},
                {"max_cc": float('inf'), "rate_percent": 0.20, "min_rate_eur_cc": 0.8},
            ],
            "5_to_7_years": [
                {"max_cc": 1000, "rate_percent": 0.20, "min_rate_eur_cc": 0.36},
                {"max_cc": 1500, "rate_percent": 0.20, "min_rate_eur_cc": 0.4},
                {"max_cc": 1800, "rate_percent": 0.20, "min_rate_eur_cc": 0.36},
                {"max_cc": 2300, "rate_percent": 0.20, "min_rate_eur_cc": 0.44},
                {"max_cc": 3000, "rate_percent": 0.20, "min_rate_eur_cc": 0.44},
                {"max_cc": float('inf'), "rate_percent": 0.20, "min_rate_eur_cc": 0.8},
            ],
            "over_7_years": [
                {"max_cc": 1000, "rate_eur_cc": 1.4}, {"max_cc": 1500, "rate_eur_cc": 1.5},
                {"max_cc": 1800, "rate_eur_cc": 1.6}, {"max_cc": 2300, "rate_eur_cc": 2.2},
                {"max_cc": 3000, "rate_eur_cc": 2.2}, {"max_cc": float('inf'), "rate_eur_cc": 3.2},
            ]
        }
    },
    "PASSENGER_CAR_JUR_DIESEL": {
        "DUTY_RATES": {
            "under_3_years": [
                {"max_cc": float('inf'), "rate_percent": 0.15},
            ],
            "3_to_5_years": [
                {"max_cc": 1500, "rate_percent": 0.20, "min_rate_eur_cc": 0.32},
                {"max_cc": 2500, "rate_percent": 0.20, "min_rate_eur_cc": 0.4},
                {"max_cc": float('inf'), "rate_percent": 0.20, "min_rate_eur_cc": 0.8},
            ],
            "5_to_7_years": [
                {"max_cc": 1500, "rate_percent": 0.20, "min_rate_eur_cc": 0.32},
                {"max_cc": 2500, "rate_percent": 0.20, "min_rate_eur_cc": 0.4},
                {"max_cc": float('inf'), "rate_percent": 0.20, "min_rate_eur_cc": 0.8},
            ],
            "over_7_years": [
                {"max_cc": 1500, "rate_eur_cc": 1.5}, {"max_cc": 2500, "rate_eur_cc": 2.2},
                {"max_cc": float('inf'), "rate_eur_cc": 3.2},
            ]
        }
    },
    "UTILIZATION_FEE": {
        "base": 20000,
        "personal_new": 0.17,
        "personal_old": 0.26,
        "commercial": {
            "under_3": [
                {"max_cc": 1000, "coeff": 9.91},
                {"max_cc": 2000, "coeff": 37.07},
                {"max_cc": 3000, "coeff": 103.15},
                {"max_cc": 3500, "coeff": 118.44},
                {"max_cc": float('inf'), "coeff": 150.82},
            ],
            "over_3": [
                {"max_cc": 1000, "coeff": 25.3},
                {"max_cc": 2000, "coeff": 64.57},
                {"max_cc": 3000, "coeff": 156.17},
                {"max_cc": 3500, "coeff": 236.87},
                {"max_cc": float('inf'), "coeff": 301.64},
            ]
        }
    },
    "ACCISE_RATES": [
        {"max_hp": 90, "rate": 0},
        {"max_hp": 150, "rate": 61},
        {"max_hp": 200, "rate": 583},
        {"max_hp": 300, "rate": 955},
        {"max_hp": 400, "rate": 1627},
        {"max_hp": 500, "rate": 1680},
        {"max_hp": float('inf'), "rate": 1733},
    ],
    "VAT_RATE": 0.20,
    "CUSTOMS_FEE_FROM_VALUE_RUB": [
        {"max_value": 200000, "fee": 1067},
        {"max_value": 450000, "fee": 2134},
        {"max_value": 1200000, "fee": 5870},
        {"max_value": 2700000, "fee": 11746},
        {"max_value": 4200000, "fee": 16524},
        {"max_value": 5500000, "fee": 21344},
        {"max_value": 7000000, "fee": 27540},
        {"max_value": 10000000, "fee": 30000},
        {"max_value": float('inf'), "fee": 30000},
    ],
    "SHIPPING_RATES": {
        "Europe": {"container": 2000, "roro": 1500, "truck": 1000},
        "Asia": {"container": 3000, "roro": 2500, "truck": 4000},
        "USA": {"container": 4000, "roro": 3500, "truck": 5000},
        "insurance_rate": 0.005,
    }
}

# ---------- Хранилище ставок (SQLite) ----------

class RatesStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _ensure_db(self):
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS duty_rates (
                id INTEGER PRIMARY KEY,
                audience TEXT NOT NULL,  -- PASSENGER_CAR_PHYS / PASSENGER_CAR_JUR_BENZ / PASSENGER_CAR_JUR_DIESEL
                age_group TEXT NOT NULL, -- under_3_years / 3_to_5_years / 5_to_7_years / over_7_years / over_5_years
                max_value REAL,          -- max_cc (см³) или max_value (€) в зависимости от unit
                unit TEXT NOT NULL,      -- 'eur_cc' / 'percent' / 'value'
                rate_percent REAL,
                rate_eur_cc REAL,
                min_rate_eur_cc REAL
            )""")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS util_fee (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,      -- personal_new / personal_old / commercial_under_3 / commercial_over_3
                max_cc REAL,             -- только для commercial*
                coeff REAL NOT NULL
            )""")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS accise_rates (
                id INTEGER PRIMARY KEY,
                max_hp REAL NOT NULL,
                rate_rub_per_hp REAL NOT NULL
            )""")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS customs_fee (
                id INTEGER PRIMARY KEY,
                max_value_rub REAL NOT NULL,
                fee_rub REAL NOT NULL
            )""")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                k TEXT PRIMARY KEY,
                v TEXT
            )""")
            con.commit()

    # ---- Инициализация дефолтов ----
    def seed_defaults(self, defaults: Dict[str, Any] = DEFAULT_RATES):
        with self._conn() as con:
            cur = con.cursor()
            # Очистка
            cur.execute("DELETE FROM duty_rates")
            cur.execute("DELETE FROM util_fee")
            cur.execute("DELETE FROM accise_rates")
            cur.execute("DELETE FROM customs_fee")

            # duty_rates
            def ins(audience: str, age_key: str, rows: List[Dict[str, Any]]):
                for row in rows:
                    if "rate_eur_cc" in row:
                        cur.execute("""INSERT INTO duty_rates
                            (audience, age_group, max_value, unit, rate_percent, rate_eur_cc, min_rate_eur_cc)
                            VALUES (?, ?, ?, 'eur_cc', NULL, ?, NULL)""",
                            (audience, age_key, float(row.get("max_cc", row.get("max_value", 9e18))), float(row["rate_eur_cc"]))
                        )
                    else:
                        # процент + min €/см³
                        max_value = float(row.get("max_cc", row.get("max_value", 9e18)))
                        min_rate = float(row.get("min_rate_eur_cc", 0.0))
                        rate_percent = float(row.get("rate_percent", 0.0))
                        unit = "value" if "max_value" in row else "percent"
                        cur.execute("""INSERT INTO duty_rates
                            (audience, age_group, max_value, unit, rate_percent, rate_eur_cc, min_rate_eur_cc)
                            VALUES (?, ?, ?, ?, ?, NULL, ?)""",
                            (audience, age_key, max_value, unit, rate_percent, min_rate)
                        )

            # PHYS
            phys = defaults["PASSENGER_CAR_PHYS"]["DUTY_RATES"]
            ins("PASSENGER_CAR_PHYS", "under_3_years", phys["under_3_years"])
            ins("PASSENGER_CAR_PHYS", "3_to_5_years",  phys["3_to_5_years"])
            # В БД используем "over_5_years" вместо "over_7_years" для физлиц (как в дефолте)
            ins("PASSENGER_CAR_PHYS", "over_5_years",  phys["over_5_years"])

            # JUR BENZ
            benz = defaults["PASSENGER_CAR_JUR_BENZ"]["DUTY_RATES"]
            ins("PASSENGER_CAR_JUR_BENZ", "under_3_years", benz["under_3_years"])
            ins("PASSENGER_CAR_JUR_BENZ", "3_to_5_years",  benz["3_to_5_years"])
            ins("PASSENGER_CAR_JUR_BENZ", "5_to_7_years",  benz["5_to_7_years"])
            ins("PASSENGER_CAR_JUR_BENZ", "over_7_years",  benz["over_7_years"])

            # JUR DIESEL
            diesel = defaults["PASSENGER_CAR_JUR_DIESEL"]["DUTY_RATES"]
            ins("PASSENGER_CAR_JUR_DIESEL", "under_3_years", diesel["under_3_years"])
            ins("PASSENGER_CAR_JUR_DIESEL", "3_to_5_years",  diesel["3_to_5_years"])
            ins("PASSENGER_CAR_JUR_DIESEL", "5_to_7_years",  diesel["5_to_7_years"])
            ins("PASSENGER_CAR_JUR_DIESEL", "over_7_years",  diesel["over_7_years"])

            # util_fee
            base = defaults["UTILIZATION_FEE"]["base"]
            # personal_new / personal_old (без max_cc)
            cur.execute("INSERT INTO util_fee (kind, max_cc, coeff) VALUES (?, NULL, ?)", ("personal_new", defaults["UTILIZATION_FEE"]["personal_new"]))
            cur.execute("INSERT INTO util_fee (kind, max_cc, coeff) VALUES (?, NULL, ?)", ("personal_old",  defaults["UTILIZATION_FEE"]["personal_old"]))
            # commercial under/over 3
            for row in defaults["UTILIZATION_FEE"]["commercial"]["under_3"]:
                cur.execute("INSERT INTO util_fee (kind, max_cc, coeff) VALUES (?, ?, ?)", ("commercial_under_3", float(row["max_cc"]), float(row["coeff"])))
            for row in defaults["UTILIZATION_FEE"]["commercial"]["over_3"]:
                cur.execute("INSERT INTO util_fee (kind, max_cc, coeff) VALUES (?, ?, ?)", ("commercial_over_3", float(row["max_cc"]), float(row["coeff"])))

            # accise
            for row in defaults["ACCISE_RATES"]:
                cur.execute("INSERT INTO accise_rates (max_hp, rate_rub_per_hp) VALUES (?, ?)", (float(row["max_hp"]), float(row["rate"])))

            # customs_fee
            for row in defaults["CUSTOMS_FEE_FROM_VALUE_RUB"]:
                cur.execute("INSERT INTO customs_fee (max_value_rub, fee_rub) VALUES (?, ?)", (float(row["max_value"]), float(row["fee"])))

            # meta
            cur.execute("INSERT OR REPLACE INTO meta (k, v) VALUES ('util_base', ?)", (str(base),))
            cur.execute("INSERT OR REPLACE INTO meta (k, v) VALUES ('updated_at', ?)", (datetime.datetime.utcnow().isoformat(),))
            con.commit()
            logging.info("База ставок инициализирована дефолтами.")

    # Загрузка в структуру, пригодную для калькулятора
    def load_structured(self) -> Dict[str, Any]:
        res = {
            "PASSENGER_CAR_PHYS": {"DUTY_RATES": {}},
            "PASSENGER_CAR_JUR_BENZ": {"DUTY_RATES": {}},
            "PASSENGER_CAR_JUR_DIESEL": {"DUTY_RATES": {}},
            "UTILIZATION_FEE": {"base": 20000, "personal_new": 0.17, "personal_old": 0.26, "commercial": {"under_3": [], "over_3": []}},
            "ACCISE_RATES": [],
            "VAT_RATE": 0.20,
            "CUSTOMS_FEE_FROM_VALUE_RUB": []
        }
        with self._conn() as con:
            cur = con.cursor()
            # util base
            cur.execute("SELECT v FROM meta WHERE k='util_base'")
            r = cur.fetchone()
            if r:
                res["UTILIZATION_FEE"]["base"] = float(r[0])

            # duty_rates
            cur.execute("SELECT audience, age_group, max_value, unit, rate_percent, rate_eur_cc, min_rate_eur_cc FROM duty_rates ORDER BY audience, age_group, max_value")
            for audience, age_group, max_value, unit, rate_percent, rate_eur_cc, min_rate_eur_cc in cur.fetchall():
                dest = res[audience]["DUTY_RATES"].setdefault(age_group, [])
                row = {}
                if unit == "eur_cc":
                    row = {"max_cc": float(max_value), "rate_eur_cc": float(rate_eur_cc)}
                elif unit in ("percent", "value"):
                    # under_3: привязка по price brackets -> max_value это price cap (EUR)
                    key = "max_value" if unit == "value" else "max_cc"
                    row = {key: float(max_value), "rate_percent": float(rate_percent), "min_rate_eur_cc": float(min_rate_eur_cc or 0.0)}
                dest.append(row)

            # util_fee
            cur.execute("SELECT kind, max_cc, coeff FROM util_fee ORDER BY kind, max_cc")
            for kind, max_cc, coeff in cur.fetchall():
                if kind == "personal_new":
                    res["UTILIZATION_FEE"]["personal_new"] = float(coeff)
                elif kind == "personal_old":
                    res["UTILIZATION_FEE"]["personal_old"] = float(coeff)
                elif kind == "commercial_under_3":
                    res["UTILIZATION_FEE"]["commercial"]["under_3"].append({"max_cc": float(max_cc), "coeff": float(coeff)})
                elif kind == "commercial_over_3":
                    res["UTILIZATION_FEE"]["commercial"]["over_3"].append({"max_cc": float(max_cc), "coeff": float(coeff)})
            # accise
            cur.execute("SELECT max_hp, rate_rub_per_hp FROM accise_rates ORDER BY max_hp")
            for max_hp, rate in cur.fetchall():
                res["ACCISE_RATES"].append({"max_hp": float(max_hp), "rate": float(rate)})
            # customs fee
            cur.execute("SELECT max_value_rub, fee_rub FROM customs_fee ORDER BY max_value_rub")
            for mv, fee in cur.fetchall():
                res["CUSTOMS_FEE_FROM_VALUE_RUB"].append({"max_value": float(mv), "fee": float(fee)})
        return res

# ---------- Калькулятор ----------

class CustomsCalculator:
    COMPANY_COMMISSION_RUB = 69000.0

    def __init__(self, store: RatesStore):
        self.store = store
        # если БД пуста — проинициализировать дефолтами
        try:
            rates = self.store.load_structured()
            if not rates["CUSTOMS_FEE_FROM_VALUE_RUB"]:
                raise RuntimeError("Empty DB")
            self.RATES = rates
            logging.info("Ставки загружены из БД.")
        except Exception:
            logging.info("Инициализация БД дефолтными ставками...")
            self.store.seed_defaults(DEFAULT_RATES)
            self.RATES = self.store.load_structured()
        self.fx = RatesFetcher.get_currency_rates()

    @staticmethod
    def _find_rate(value: float, table: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
        for item in table:
            if value <= float(item.get(key, float('inf'))):
                return item
        return table[-1]

    def _calc_duty(self, price_eur: float, engine_cc: int, age_key: str, is_jur: bool, engine_type: str) -> float:
        if not is_jur:
            table_group = self.RATES["PASSENGER_CAR_PHYS"]["DUTY_RATES"]
            # физлица: under_3_years / 3_to_5_years / over_5_years
            if age_key == "under_3":
                row = self._find_rate(price_eur, table_group["under_3_years"], "max_value")
                duty_from_price = price_eur * float(row["rate_percent"])
                duty_from_volume = engine_cc * float(row["min_rate_eur_cc"])
                return max(duty_from_price, duty_from_volume)
            elif age_key == "3_to_5":
                row = self._find_rate(engine_cc, table_group["3_to_5_years"], "max_cc")
                return engine_cc * float(row["rate_eur_cc"])
            else:
                row = self._find_rate(engine_cc, table_group["over_5_years"], "max_cc")
                return engine_cc * float(row["rate_eur_cc"])
        else:
            key = "PASSENGER_CAR_JUR_BENZ" if engine_type == "Бензин" else "PASSENGER_CAR_JUR_DIESEL"
            table_group = self.RATES[key]["DUTY_RATES"]
            mapped = {
                "under_3": "under_3_years",
                "3_to_5": "3_to_5_years",
                "5_to_7": "5_to_7_years",
                "over_7": "over_7_years",
            }
            g = mapped.get(age_key, "under_3_years")
            rows = table_group[g]
            # два случая: процент (с минимумом €/см³) или фикс €/см³
            if "rate_percent" in rows[0]:
                # процентные строки: ищем по max_cc
                row = self._find_rate(engine_cc, rows, "max_cc")
                duty_from_percent = price_eur * float(row["rate_percent"])
                min_from_volume = engine_cc * float(row["min_rate_eur_cc"])
                return max(duty_from_percent, min_from_volume)
            else:
                row = self._find_rate(engine_cc, rows, "max_cc")
                return engine_cc * float(row["rate_eur_cc"])

    def _calc_util(self, is_commercial: bool, age_key: str, engine_cc: int) -> float:
        base = float(self.RATES["UTILIZATION_FEE"]["base"])
        if not is_commercial:
            coeff = float(self.RATES["UTILIZATION_FEE"]["personal_new"] if age_key == "under_3" else self.RATES["UTILIZATION_FEE"]["personal_old"])
            return base * coeff
        else:
            group = "under_3" if age_key == "under_3" else "over_3"
            row = self._find_rate(engine_cc, self.RATES["UTILIZATION_FEE"]["commercial"][group], "max_cc")
            return base * float(row["coeff"])

    def _calc_accise(self, hp: int) -> float:
        row = self._find_rate(hp, self.RATES["ACCISE_RATES"], "max_hp")
        return hp * float(row["rate"])

    def _calc_vat(self, price_rub: float, duty_rub: float, accise_rub: float) -> float:
        base = price_rub + duty_rub + accise_rub
        return base * float(self.RATES.get("VAT_RATE", 0.20))

    def _calc_customs_fee(self, price_rub: float) -> float:
        row = self._find_rate(price_rub, self.RATES["CUSTOMS_FEE_FROM_VALUE_RUB"], "max_value")
        return float(row["fee"])

    def _calc_shipping(self, price_rub: float, customs_total: float) -> Optional[tuple]:
        country_map = {"1": "Europe", "2": "Asia", "3": "USA"}
        method_map = {"1": "container", "2": "roro", "3": "truck"}
        print("Выберите регион отправки: 1: Европа, 2: Азия, 3: США")
        country = country_map.get(input("Ваш выбор: ").strip(), "Europe")
        print("Выберите метод доставки: 1: Контейнер, 2: Ro-Ro, 3: Автовоз")
        method = method_map.get(input("Ваш выбор: ").strip(), "container")
        base_eur = float(DEFAULT_RATES["SHIPPING_RATES"][country][method])  # хранить в БД не обязательно
        base_rub = base_eur * self.fx["EUR"]
        insurance = (price_rub + customs_total) * float(DEFAULT_RATES["SHIPPING_RATES"]["insurance_rate"])
        return base_rub + insurance, base_rub, insurance

    def run_once(self, vehicle_type_str: str = "легковой"):
        try:
            currency_map = {"1": "RUB", "2": "EUR", "3": "USD", "4": "CNY", "5": "JPY", "6": "KRW"}
            print("Выберите валюту стоимости автомобиля: 1: RUB, 2: EUR, 3: USD, 4: CNY, 5: JPY, 6: KRW")
            currency_code = currency_map.get(input("Ваш выбор: ").strip(), "RUB")
            price_native = float(input(f"Введите стоимость в {currency_code}: ").strip())
            price_rub = price_native * self.fx[currency_code]
            price_eur = price_rub / self.fx["EUR"]

            is_jur = input("Кто ввозит (1: Физ, 2: Юр): ").strip() == '2'
            owner_type_str = "юридическое лицо" if is_jur else "физическое лицо"

            is_personal_use = False
            usage_type_str = "коммерческое"
            if not is_jur:
                is_personal_use = input("Цель (1: Личное, 2: Перепродажа): ").strip() == '1'
                usage_type_str = "личное" if is_personal_use else "коммерческое"
            is_commercial = is_jur or not is_personal_use

            engine_map = {"1": "Бензин", "2": "Дизель"}
            engine_type = engine_map.get(input("Тип двигателя (1: Бензин, 2: Дизель): ").strip(), "Бензин")

            engine_cc = int(input("Объём двигателя (см³): ").strip())
            horse_power = int(input("Мощность (л.с.): ").strip())

            # возрастные группы
            print("Возраст авто: 1:<3 лет, 2: 3-5 лет, 3: 5-7 лет (только для юрлиц), 4: >7 лет (только для юрлиц/физ 'старше 5')")
            age_map = {"1": "under_3", "2": "3_to_5", "3": "5_to_7", "4": "over_7"}
            age_choice = input("Ваш выбор: ").strip()
            age_key = age_map.get(age_choice, "under_3")
            age_str = {"1":"<3 лет","2":"3-5 лет","3":"5-7 лет","4":">7 лет"}.get(age_choice, "<3 лет")

            duty_eur = self._calc_duty(price_eur, engine_cc, age_key, is_jur, engine_type)
            duty_rub = duty_eur * self.fx["EUR"]

            util_fee = self._calc_util(is_commercial, age_key, engine_cc)
            accise_rub = self._calc_accise(horse_power) if is_commercial else 0.0
            vat_rub = self._calc_vat(price_rub, duty_rub, accise_rub) if is_commercial else 0.0
            customs_fee = self._calc_customs_fee(price_rub)

            customs_total = duty_rub + customs_fee + util_fee + accise_rub + vat_rub

            shipping_info = None
            if input("Рассчитать доставку (да/нет): ").strip().lower() == "да":
                shipping_info = self._calc_shipping(price_rub, customs_total)

            # отчёт
            self._print_report({
                "vehicle_type": vehicle_type_str, "price_native": price_native, "currency_code": currency_code,
                "price_rub": price_rub, "owner_type": owner_type_str, "usage_type": usage_type_str,
                "engine_type": engine_type, "engine_cc": engine_cc, "horse_power": horse_power, "age_str": age_str,
            }, {
                "duty_rub": duty_rub, "duty_eur": duty_eur, "util_fee": util_fee, "customs_fee": customs_fee,
                "commission": self.COMPANY_COMMISSION_RUB, "accise_rub": accise_rub, "vat_rub": vat_rub,
            }, shipping_info)

        except ValueError as e:
            logging.error(f"Ошибка ввода: {e}")
        except Exception as e:
            logging.error(f"Сбой расчёта: {e}")

    @staticmethod
    def _fmt(x: float) -> str:
        return f"{x:,.2f}".replace(",", " ").replace(".", ",")

    def _print_report(self, params: Dict[str, Any], payments: Dict[str, float], shipping_info: Optional[tuple] = None):
        print("\n" + "=" * 34)
        print("       РЕЗУЛЬТАТЫ РАСЧЁТА")
        print("=" * 34)
        print(f"Тип ТС: {params['vehicle_type']}")
        print(f"Стоимость: {self._fmt(params['price_native'])} {params['currency_code']} ({self._fmt(params['price_rub'])} ₽)")
        print(f"Двигатель: {params['engine_cc']} см³, {params['horse_power']} л.с., {params['engine_type']}")
        print(f"Клиент: {params['owner_type']}  |  Цель: {params['usage_type']}  |  Возраст: {params['age_str']}")
        print("\nПлатежи (по ставкам 2025):")
        print(f"• Пошлина: {self._fmt(payments['duty_rub'])} ₽ ({self._fmt(payments['duty_eur'])} €)")
        print(f"• Таможенный сбор: {self._fmt(payments['customs_fee'])} ₽")
        print(f"• Утильсбор: {self._fmt(payments['util_fee'])} ₽")
        if payments['accise_rub'] > 0: print(f"• Акциз: {self._fmt(payments['accise_rub'])} ₽")
        if payments['vat_rub'] > 0:    print(f"• НДС: {self._fmt(payments['vat_rub'])} ₽")
        subtotal = sum([payments['duty_rub'], payments['customs_fee'], payments['util_fee'], payments['accise_rub'], payments['vat_rub']])
        print(f"\nИТОГО растаможка: {self._fmt(subtotal)} ₽")
        print("\nСервисные услуги:")
        print(f"• Комиссия компании: {self._fmt(payments['commission'])} ₽")
        total = subtotal + payments['commission']
        print(f"\nРасходы по РФ (без доставки): {self._fmt(total)} ₽")
        if shipping_info:
            total_shipping, base_shipping, insurance = shipping_info
            print("\nДоставка:")
            print(f"• База: {self._fmt(base_shipping)} ₽")
            print(f"• Страховка: {self._fmt(insurance)} ₽")
            print(f"ИТОГО доставка: {self._fmt(total_shipping)} ₽")
            print(f"\nОБЩАЯ стоимость: {self._fmt(total + total_shipping)} ₽")
        print("\nПримечание: Курсы ЦБ и ставки из БД. Для точности регулярно обновляйте ставки.")
        print("=" * 34)

# ---------- Обновление ставок (заглушка для будущего скрейпинга) ----------

def update_rates_from_official_sources(store: RatesStore):
    """
    Заглушка: здесь в будущем — парсинг официальных источников (ЕЭК/ФТС/ПП РФ),
    чтобы обновить таблицы ставок. Сейчас просто обновляет updated_at.
    """
    with store._conn() as con:
        cur = con.cursor()
        cur.execute("INSERT OR REPLACE INTO meta (k, v) VALUES ('updated_at', ?)", (datetime.datetime.utcnow().isoformat(),))
        con.commit()
    logging.info("Ставки обновлены (заглушка). Реализуйте парсинг для продакшена.")

# ---------- CLI ----------

def main():
    print("=" * 54)
    print("   Таможенный калькулятор РФ — версия 21.0 (SQLite)")
    print("=" * 54)
    store = RatesStore(DB_PATH)
    calc = CustomsCalculator(store)

    while True:
        print("\nМеню:")
        print("1 — Расчёт растаможки (легковой)")
        print("2 — Инициализировать БД дефолтами (перезапись)")
        print("3 — Обновить ставки из официальных источников (заглушка)")
        print("0 — Выход")
        choice = input("Ваш выбор: ").strip()
        if choice == "1":
            calc.run_once("легковой")
        elif choice == "2":
            store.seed_defaults(DEFAULT_RATES)
            calc = CustomsCalculator(store)
            print("БД инициализирована дефолтами.")
        elif choice == "3":
            update_rates_from_official_sources(store)
            calc = CustomsCalculator(store)
            print("Ставки обновлены (заглушка).")
        elif choice == "0":
            print("До свидания.")
            break
        else:
            print("Неверный выбор.")

if __name__ == "__main__":
    main()
