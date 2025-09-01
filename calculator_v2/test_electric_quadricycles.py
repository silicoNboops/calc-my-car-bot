#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for quadricycles customs calculations
Testing various scenarios for legal entities with electric and gasoline engines
"""

import unittest
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from customs_calculator_v6 import (
    VehicleSpec, VehicleType, ImporterType, EngineType, FuelType,
    calculate_customs_payments, RatesFetcher
)


class TestQuadricycles(unittest.TestCase):
    """Test cases for quadricycles customs calculations - electric and gasoline engines"""
    
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
    
    def test_new_electric_quad_juridical_8000_eur(self):
        """Test new electric quadricycle for legal entity - 8000 EUR, 2 years old"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=8000.0,
            currency='EUR',
            age_years=2,
            engine_volume_cc=0,  # Electric
            power_hp=7,  # Rounded from 6.7
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 8000 * 94.0479  # 752,383 rub
        expected_duty_rub = 112857  # 15% duty
        expected_vat_rub = 173048  # 20% VAT
        expected_util_fee_rub = 120750  # Coefficient 0.7 for new electric quad
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 410925
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test that excise is 0 for quadricycles
        self.assertEqual(result.excise_rub, 0.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Квадроцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
    
    def test_old_electric_quad_juridical_12500_eur(self):
        """Test old electric quadricycle for legal entity - 12500 EUR, 6 years old"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=12500.0,
            currency='EUR',
            age_years=6,
            engine_volume_cc=0,  # Electric
            power_hp=20,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 12500 * 94.0479  # 1,175,599 rub
        expected_duty_rub = 176340  # 15% duty
        expected_vat_rub = 270388  # 20% VAT
        expected_util_fee_rub = 224250  # Coefficient 1.3 for old electric quad
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 675247
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test that excise is 0 for quadricycles
        self.assertEqual(result.excise_rub, 0.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Квадроцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
    
    def test_electric_quad_utilization_fee_coefficients(self):
        """Test that electric quadricycles use correct utilization fee coefficients"""
        # Test new electric quad (≤ 3 years) - should use coefficient 0.7
        spec_new = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=5000.0,
            currency='EUR',
            age_years=1,
            engine_volume_cc=0,
            power_hp=10,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result_new = calculate_customs_payments(spec_new)
        expected_util_fee_new = 172500 * 0.7  # 120,750 rub
        self.assertAlmostEqualPercent(result_new.util_fee_rub, expected_util_fee_new, 1.0)
        
        # Test old electric quad (> 3 years) - should use coefficient 1.3
        spec_old = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=5000.0,
            currency='EUR',
            age_years=5,
            engine_volume_cc=0,
            power_hp=10,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result_old = calculate_customs_payments(spec_old)
        expected_util_fee_old = 172500 * 1.3  # 224,250 rub
        self.assertAlmostEqualPercent(result_old.util_fee_rub, expected_util_fee_old, 1.0)
    
    def test_electric_quad_duty_rate(self):
        """Test that electric quadricycles use 15% duty rate for all ages"""
        test_cases = [
            {'age': 1, 'cost': 5000},   # New
            {'age': 3, 'cost': 8000},   # Edge case - exactly 3 years
            {'age': 5, 'cost': 10000},  # Old
            {'age': 10, 'cost': 15000}  # Very old
        ]
        
        for case in test_cases:
            with self.subTest(age=case['age'], cost=case['cost']):
                spec = VehicleSpec(
                    vehicle_type=VehicleType.QUAD,
                    importer_type=ImporterType.JURIDICAL,
                    cost_original=case['cost'],
                    currency='EUR',
                    age_years=case['age'],
                    engine_volume_cc=0,
                    power_hp=15,
                    engine_type=EngineType.ELECTRIC,
                    fuel_type=FuelType.ELECTRIC
                )
                
                result = calculate_customs_payments(spec)
                expected_duty = case['cost'] * 94.0479 * 0.15  # 15% duty rate
                self.assertAlmostEqualPercent(result.duty_rub, expected_duty, 1.0)
    
    def test_new_gasoline_quad_large_engine_juridical_16000_usd(self):
        """Test new gasoline quadricycle with large engine for legal entity - 16000 USD, 1 year old, 976cc"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=16000.0,
            currency='USD',
            age_years=1,
            engine_volume_cc=976,  # ≥ 300cc, should use K02 rules
            power_hp=89,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 16000 * 80.3316  # 1,285,306 rub
        expected_duty_rub = 64265  # 5% duty for new gasoline quad
        expected_vat_rub = 269914  # 20% VAT
        expected_util_fee_rub = 120750  # Coefficient 0.7 for new K02 (≥300cc)
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_total_rub = 466675
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test that excise is 0 for quadricycles
        self.assertEqual(result.excise_rub, 0.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Квадроцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_old_gasoline_quad_large_engine_juridical_10800_usd(self):
        """Test old gasoline quadricycle with large engine for legal entity - 10800 USD, 4 years old, 475cc"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=10800.0,
            currency='USD',
            age_years=4,
            engine_volume_cc=475,  # ≥ 300cc, should use K02 rules
            power_hp=33,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 10800 * 80.3316  # 867,581 rub
        expected_duty_rub = 173516  # 20%, but not less than 0.36 EUR/cc for old gasoline quad
        expected_vat_rub = 208220  # 20% VAT
        expected_util_fee_rub = 224250  # Coefficient 1.3 for old K02 (≥300cc)
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 610255
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test that excise is 0 for quadricycles
        self.assertEqual(result.excise_rub, 0.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Квадроцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_old_gasoline_quad_large_engine_juridical_8000_usd(self):
        """Test old gasoline quadricycle with large engine for legal entity - 8000 USD, 6 years old, 493cc"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=8000.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=493,  # ≥ 300cc, should use K02 rules
            power_hp=35,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 8000 * 80.3316  # 642,653 rub
        expected_duty_rub = 128531  # 20%, but not less than 0.36 EUR/cc for old gasoline quad
        expected_vat_rub = 154237  # 20% VAT
        expected_util_fee_rub = 224250  # Coefficient 1.3 for old K02 (≥300cc)
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 511286
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test that excise is 0 for quadricycles
        self.assertEqual(result.excise_rub, 0.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Квадроцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_very_old_gasoline_quad_juridical_5800_usd(self):
        """Test very old gasoline quadricycle for legal entity - 5800 USD, 8 years old, 383cc"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=5800.0,
            currency='USD',
            age_years=8,
            engine_volume_cc=383,
            power_hp=24,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 5800 * 80.3316  # 465,923 rub
        expected_duty_rub = 50428  # 1.4 EUR/cc for very old gasoline quad
        expected_vat_rub = 103270  # 20% VAT
        expected_util_fee_rub = 224250  # Coefficient 1.3 for old K02 (≥300cc)
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 382218
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test that excise is 0 for quadricycles
        self.assertEqual(result.excise_rub, 0.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Квадроцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_new_electric_quad_juridical_25000_eur(self):
        """Test new electric quadricycle for legal entity - 25000 EUR, 1 year old, 40hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=25000.0,
            currency='EUR',
            age_years=1,
            engine_volume_cc=0,  # Electric
            power_hp=40,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 25000 * 94.0479  # 2,351,198 rub
        expected_duty_rub = 352680  # 15% duty
        expected_vat_rub = 540775  # 20% VAT
        expected_util_fee_rub = 120750  # Coefficient 0.7 for new electric quad
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_total_rub = 1025951
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test that excise is 0 for quadricycles
        self.assertEqual(result.excise_rub, 0.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Квадроцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
    
    def test_old_electric_quad_juridical_20000_usd(self):
        """Test old electric quadricycle for legal entity - 20000 USD, 4 years old, 64hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=20000.0,
            currency='USD',
            age_years=4,
            engine_volume_cc=0,  # Electric
            power_hp=64,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 20000 * 80.3316  # 1,606,632 rub
        expected_duty_rub = 240995  # 15% duty
        expected_vat_rub = 369525  # 20% VAT
        expected_util_fee_rub = 224250  # Coefficient 1.3 for old electric quad
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_total_rub = 846516
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test that excise is 0 for quadricycles
        self.assertEqual(result.excise_rub, 0.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Квадроцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
    
    def test_old_electric_quad_juridical_16500_eur(self):
        """Test old electric quadricycle for legal entity - 16500 EUR, 6 years old, 80hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=16500.0,
            currency='EUR',
            age_years=6,
            engine_volume_cc=0,  # Electric
            power_hp=80,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 16500 * 94.0479  # 1,551,790 rub
        expected_duty_rub = 232769  # 15% duty
        expected_vat_rub = 356912  # 20% VAT
        expected_util_fee_rub = 224250  # Coefficient 1.3 for old electric quad
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_total_rub = 825676
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test that excise is 0 for quadricycles
        self.assertEqual(result.excise_rub, 0.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Квадроцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
    
    def test_very_old_electric_quad_juridical_12800_usd(self):
        """Test very old electric quadricycle for legal entity - 12800 USD, 8 years old, 60hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.QUAD,
            importer_type=ImporterType.JURIDICAL,
            cost_original=12800.0,
            currency='USD',
            age_years=8,
            engine_volume_cc=0,  # Electric
            power_hp=60,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 12800 * 80.3316  # 1,028,244 rub
        expected_duty_rub = 154237  # 15% duty
        expected_vat_rub = 236496  # 20% VAT
        expected_util_fee_rub = 224250  # Coefficient 1.3 for old electric quad
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 619252
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test that excise is 0 for quadricycles
        self.assertEqual(result.excise_rub, 0.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Квадроцикл')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')


if __name__ == '__main__':
    unittest.main(verbosity=2)