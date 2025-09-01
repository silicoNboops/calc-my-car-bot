#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for motorcycles customs calculations
Testing various scenarios for legal entities with different ages, costs, and engine volumes
"""

import os
import sys
import unittest

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from customs_calculator_v5 import (
    VehicleSpec, VehicleType, ImporterType, EngineType, FuelType,
    calculate_customs_payments, RatesFetcher
)


class TestMotorcycles(unittest.TestCase):
    """Test cases for motorcycles customs calculations"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures with mock exchange rates to ensure consistent testing"""
        # Mock exchange rates for consistent testing
        cls.original_cache = RatesFetcher._cache.copy() if RatesFetcher._cache else {}
        cls.original_cache_time = RatesFetcher._cache_time

        # Set fixed rates for testing (similar to actual rates)
        RatesFetcher._cache = {
            'EUR': 94.0479,
            'USD': 80.3316,
            'CNY': 13.5,
            'JPY': 0.65,
            'KRW': 0.07,
            'RUB': 1.0
        }
        RatesFetcher._cache_time = None  # Keep cache valid

    @classmethod
    def tearDownClass(cls):
        """Restore original cache after tests"""
        RatesFetcher._cache = cls.original_cache
        RatesFetcher._cache_time = cls.original_cache_time

    def assertAlmostEqualPercent(self, actual, expected, percent=1.0, msg=None):
        """Assert that actual value is within specified percentage of expected value"""
        if expected == 0:
            self.assertEqual(actual, expected, msg)
            return

        percentage_diff = abs((actual - expected) / expected) * 100
        if msg is None:
            msg = f"Values differ by {percentage_diff:.2f}% (expected: {expected}, actual: {actual})"

        self.assertLessEqual(percentage_diff, percent, msg)

    def test_new_motorcycle_juridical_12000_eur_689cc(self):
        """Test new motorcycle for legal entity - 12000 EUR, 1 year old, 689cc, 75hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.MOTORCYCLE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=12000.0,
            currency='EUR',
            age_years=1,
            engine_volume_cc=689,
            power_hp=75,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )

        result = calculate_customs_payments(spec)

        # Expected values based on user's verified calculation
        expected_cost_rub = 12000 * 94.0479  # 1,128,575 rub
        expected_duty_rub = 169286  # 15% duty for 500-800cc motorcycle
        expected_vat_rub = 259572  # 20% VAT
        expected_util_fee_rub = 0  # No utilization fee for motorcycles
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for motorcycles ≤ 150hp
        expected_total_rub = 433127

        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)

        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Мотоцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')

    def test_old_motorcycle_juridical_9000_eur_948cc(self):
        """Test old motorcycle for legal entity - 9000 EUR, 3 years old, 948cc, 125hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.MOTORCYCLE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=9000.0,
            currency='EUR',
            age_years=3,
            engine_volume_cc=948,
            power_hp=125,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )

        result = calculate_customs_payments(spec)

        # Expected values based on user's verified calculation
        expected_cost_rub = 9000 * 94.0479  # 846,431 rub
        expected_duty_rub = 84643  # 10% duty for >800cc motorcycle
        expected_vat_rub = 186215  # 20% VAT
        expected_util_fee_rub = 0  # No utilization fee for motorcycles
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for motorcycles ≤ 150hp
        expected_total_rub = 275127

        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)

        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Мотоцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')

    def test_older_motorcycle_juridical_6800_eur_675cc(self):
        """Test older motorcycle for legal entity - 6800 EUR, 6 years old, 675cc, 106hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.MOTORCYCLE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=6800.0,
            currency='EUR',
            age_years=6,
            engine_volume_cc=675,
            power_hp=106,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )

        result = calculate_customs_payments(spec)

        # Expected values based on user's verified calculation
        expected_cost_rub = 6800 * 94.0479  # 639,526 rub
        expected_duty_rub = 95929  # 15% duty for 500-800cc motorcycle
        expected_vat_rub = 147091  # 20% VAT
        expected_util_fee_rub = 0  # No utilization fee for motorcycles
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for motorcycles ≤ 150hp
        expected_total_rub = 247289

        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)

        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Мотоцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')

    def test_very_old_motorcycle_juridical_5200_eur_600cc(self):
        """Test very old motorcycle for legal entity - 5200 EUR, 8 years old, 600cc, 98hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.MOTORCYCLE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=5200.0,
            currency='EUR',
            age_years=8,
            engine_volume_cc=600,
            power_hp=98,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )

        result = calculate_customs_payments(spec)

        # Expected values based on user's verified calculation
        expected_cost_rub = 5200 * 94.0479  # 489,049 rub
        expected_duty_rub = 73357  # 15% duty for 500-800cc motorcycle
        expected_vat_rub = 112481  # 20% VAT
        expected_util_fee_rub = 0  # No utilization fee for motorcycles
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for motorcycles ≤ 150hp
        expected_total_rub = 190108

        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)

        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Мотоцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')

    def test_motorcycle_no_utilization_fee(self):
        """Test that motorcycles never have utilization fees"""
        test_cases = [
            {'age': 1, 'volume': 125, 'cost': 3000},
            {'age': 5, 'volume': 600, 'cost': 5000},
            {'age': 10, 'volume': 1000, 'cost': 8000}
        ]

        for case in test_cases:
            with self.subTest(age=case['age'], volume=case['volume']):
                spec = VehicleSpec(
                    vehicle_type=VehicleType.MOTORCYCLE,
                    importer_type=ImporterType.JURIDICAL,
                    cost_original=case['cost'],
                    currency='EUR',
                    age_years=case['age'],
                    engine_volume_cc=case['volume'],
                    power_hp=50,
                    engine_type=EngineType.DVS,
                    fuel_type=FuelType.GASOLINE
                )

                result = calculate_customs_payments(spec)
                self.assertEqual(result.util_fee_rub, 0.0,
                                 f"Utilization fee should be 0 for motorcycles (age={case['age']}, volume={case['volume']})")

    def test_motorcycle_duty_by_volume(self):
        """Test that motorcycle duty rates vary correctly by engine volume"""
        # Test different volume ranges to verify duty rates
        test_cases = [
            {'volume': 125, 'expected_rate': 0.14},  # ≤125cc: 14%
            {'volume': 250, 'expected_rate': 0.14},  # 125-250cc: 14%
            {'volume': 380, 'expected_rate': 0.15},  # 250-380cc: 15%
            {'volume': 500, 'expected_rate': 0.15},  # 380-500cc: 15%
            {'volume': 800, 'expected_rate': 0.15},  # 500-800cc: 15%
            {'volume': 1000, 'expected_rate': 0.10}  # >800cc: 10%
        ]

        for case in test_cases:
            with self.subTest(volume=case['volume']):
                spec = VehicleSpec(
                    vehicle_type=VehicleType.MOTORCYCLE,
                    importer_type=ImporterType.JURIDICAL,
                    cost_original=1000.0,  # Fixed cost for comparison
                    currency='EUR',
                    age_years=1,
                    engine_volume_cc=case['volume'],
                    power_hp=50,
                    engine_type=EngineType.DVS,
                    fuel_type=FuelType.GASOLINE
                )

                result = calculate_customs_payments(spec)
                expected_duty = 1000 * 94.0479 * case['expected_rate']  # Convert to RUB
                self.assertAlmostEqualPercent(result.duty_rub, expected_duty, 1.0,
                                              f"Wrong duty rate for {case['volume']}cc motorcycle")

    def test_electric_motorcycle_juridical_22000_eur(self):
        """Test electric motorcycle for legal entity - 22000 EUR, 1 year old, 100hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.MOTORCYCLE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=22000.0,
            currency='EUR',
            age_years=1,
            engine_volume_cc=0,  # Electric
            power_hp=100,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )

        result = calculate_customs_payments(spec)

        # Expected values based on official customs site calculation
        expected_cost_rub = 22000 * 94.0479  # 2,069,054 rub
        expected_duty_rub = 310358  # 15% duty for electric motorcycles
        expected_vat_rub = 475882  # 20% VAT
        expected_util_fee_rub = 0  # No utilization fee for motorcycles
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for motorcycles ≤ 150hp
        expected_total_rub = 797986

        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)

        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Мотоцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')

    def test_electric_motorcycle_juridical_18500_usd(self):
        """Test electric motorcycle for legal entity - 18500 USD, 4 years old, 105hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.MOTORCYCLE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=18500.0,
            currency='USD',
            age_years=4,
            engine_volume_cc=0,  # Electric
            power_hp=105,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )

        result = calculate_customs_payments(spec)

        # Expected values based on user's verified calculation
        expected_cost_rub = 18500 * 80.3316  # 1,486,135 rub
        expected_duty_rub = 222920  # 15% duty for electric motorcycles
        expected_vat_rub = 341811  # 20% VAT
        expected_util_fee_rub = 0  # No utilization fee for motorcycles
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for motorcycles ≤ 150hp
        expected_total_rub = 576477

        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)

        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Мотоцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')

    def test_electric_motorcycle_juridical_15000_eur(self):
        """Test electric motorcycle for legal entity - 15000 EUR, 6 years old, 107hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.MOTORCYCLE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=15000.0,
            currency='EUR',
            age_years=6,
            engine_volume_cc=0,  # Electric
            power_hp=107,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )

        result = calculate_customs_payments(spec)

        # Expected values based on user's verified calculation
        expected_cost_rub = 15000 * 94.0479  # 1,410,718 rub
        expected_duty_rub = 211608  # 15% duty for electric motorcycles
        expected_vat_rub = 324465  # 20% VAT
        expected_util_fee_rub = 0  # No utilization fee for motorcycles
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for motorcycles ≤ 150hp
        expected_total_rub = 547819

        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)

        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Мотоцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')

    def test_electric_motorcycle_juridical_32000_usd_with_excise(self):
        """Test electric motorcycle for legal entity - 32000 USD, 8 years old, 201hp (with excise)"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.MOTORCYCLE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=32000.0,
            currency='USD',
            age_years=8,
            engine_volume_cc=0,  # Electric
            power_hp=201,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )

        result = calculate_customs_payments(spec)

        # Expected values based on user's verified calculation
        expected_cost_rub = 32000 * 80.3316  # 2,570,611 rub
        expected_duty_rub = 385592  # 15% duty for electric motorcycles
        expected_vat_rub = 614677  # 20% VAT
        expected_util_fee_rub = 0  # No utilization fee for motorcycles
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_excise_rub = 117183  # Excise for motorcycles > 150hp: (201-150) * 583 = 29,733 rub
        expected_total_rub = 1129198

        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)

        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Мотоцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')

    def test_motorcycle_excise_threshold(self):
        """Test that motorcycles only have excise for power > 150hp"""
        # Test motorcycle with 150hp (should have no excise)
        spec_150hp = VehicleSpec(
            vehicle_type=VehicleType.MOTORCYCLE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=10000.0,
            currency='EUR',
            age_years=1,
            engine_volume_cc=600,
            power_hp=150,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )

        result_150hp = calculate_customs_payments(spec_150hp)
        self.assertEqual(result_150hp.excise_rub, 0.0, "No excise for motorcycles ≤150hp")

        # Test motorcycle with 200hp (should have excise)
        spec_200hp = VehicleSpec(
            vehicle_type=VehicleType.MOTORCYCLE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=10000.0,
            currency='EUR',
            age_years=1,
            engine_volume_cc=600,
            power_hp=200,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )

        result_200hp = calculate_customs_payments(spec_200hp)
        expected_excise = 200 * 583.0  # 583 rub per hp for motorcycles >150hp
        self.assertAlmostEqualPercent(result_200hp.excise_rub, expected_excise, 1.0,
                                      "Excise should apply for motorcycles >150hp")


if __name__ == '__main__':
    unittest.main(verbosity=2)
