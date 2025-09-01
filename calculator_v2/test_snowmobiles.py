#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for snowmobiles customs calculations
Testing various scenarios for legal entities with gasoline engines
"""

import unittest
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from customs_calculator_v5 import (
    VehicleSpec, VehicleType, ImporterType, EngineType, FuelType,
    calculate_customs_payments, RatesFetcher
)


class TestSnowmobiles(unittest.TestCase):
    """Test cases for snowmobiles customs calculations"""
    
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
    
    def test_gasoline_snowmobile_juridical_22500_eur_899cc(self):
        """Test gasoline snowmobile for legal entity - 22500 EUR, 1 year old, 899cc, 150hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.SNOWMOBILE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=22500.0,
            currency='EUR',
            age_years=1,
            engine_volume_cc=899,
            power_hp=150,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 22500 * 94.0479  # 2,116,078 rub
        expected_duty_rub = 105804  # 5% duty for new snowmobiles (≤3 years)
        expected_vat_rub = 444376  # 20% VAT
        expected_util_fee_rub = 120750  # Utilization fee for snowmobiles
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for snowmobiles
        expected_total_rub = 682676
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Снегоход')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_snowmobile_no_excise(self):
        """Test that snowmobiles never have excise tax"""
        test_cases = [
            {'power': 100, 'cost': 15000},
            {'power': 150, 'cost': 20000},
            {'power': 200, 'cost': 25000}
        ]
        
        for case in test_cases:
            with self.subTest(power=case['power']):
                spec = VehicleSpec(
                    vehicle_type=VehicleType.SNOWMOBILE,
                    importer_type=ImporterType.JURIDICAL,
                    cost_original=case['cost'],
                    currency='EUR',
                    age_years=1,
                    engine_volume_cc=800,
                    power_hp=case['power'],
                    engine_type=EngineType.DVS,
                    fuel_type=FuelType.GASOLINE
                )
                
                result = calculate_customs_payments(spec)
                self.assertEqual(result.excise_rub, 0.0, 
                               f"Excise should be 0 for snowmobiles (power={case['power']}hp)")
    
    def test_snowmobile_duty_rate(self):
        """Test that snowmobiles use 5% duty rate for all ages"""
        test_cases = [
            {'cost': 10000, 'age': 1, 'volume': 800},
            {'cost': 15000, 'age': 3, 'volume': 800},
            {'cost': 16500, 'age': 4, 'volume': 840},  # Our verified case
            {'cost': 25000, 'age': 8, 'volume': 900}
        ]
        
        for case in test_cases:
            with self.subTest(cost=case['cost'], age=case['age']):
                spec = VehicleSpec(
                    vehicle_type=VehicleType.SNOWMOBILE,
                    importer_type=ImporterType.JURIDICAL,
                    cost_original=case['cost'],
                    currency='EUR',
                    age_years=case['age'],
                    engine_volume_cc=case['volume'],
                    power_hp=120,
                    engine_type=EngineType.DVS,
                    fuel_type=FuelType.GASOLINE
                )
                
                result = calculate_customs_payments(spec)
                expected_duty_rub = case['cost'] * 94.0479 * 0.05  # 5% duty for all snowmobiles
                
                self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0,
                                            f"Wrong duty rate for snowmobile (cost={case['cost']}, age={case['age']})")
    
    def test_gasoline_snowmobile_juridical_16500_usd_840cc(self):
        """Test gasoline snowmobile for legal entity - 16500 USD, 4 years old, 840cc, 155hp
        This was a problematic case that confirmed snowmobiles use 5% duty regardless of age.
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.SNOWMOBILE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=16500.0,
            currency='USD',
            age_years=4,
            engine_volume_cc=840,
            power_hp=155,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on official customs site calculation
        expected_cost_rub = 16500 * 80.3316  # 1,325,471 rub
        expected_duty_rub = 66274  # 5% duty for all snowmobiles
        expected_vat_rub = 278349  # 20% VAT
        expected_util_fee_rub = 224250  # Utilization fee coefficient 1.3 for old vehicles
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for snowmobiles
        expected_total_rub = 580619
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Снегоход')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_gasoline_snowmobile_juridical_12400_usd_899cc(self):
        """Test gasoline snowmobile for legal entity - 12400 USD, 6 years old, 899cc, 90hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.SNOWMOBILE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=12400.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=899,
            power_hp=90,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 12400 * 80.3316  # 996,112 rub
        expected_duty_rub = 49806  # 5% duty for all snowmobiles
        expected_vat_rub = 209183  # 20% VAT
        expected_util_fee_rub = 224250  # Utilization fee coefficient 1.3 for old vehicles
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for snowmobiles
        expected_total_rub = 487508
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Снегоход')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_gasoline_snowmobile_juridical_9200_usd_599cc(self):
        """Test gasoline snowmobile for legal entity - 9200 USD, 8 years old, 599cc, 120hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.SNOWMOBILE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=9200.0,
            currency='USD',
            age_years=8,
            engine_volume_cc=599,
            power_hp=120,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 9200 * 80.3316  # 739,051 rub
        expected_duty_rub = 36953  # 5% duty for all snowmobiles
        expected_vat_rub = 155201  # 20% VAT
        expected_util_fee_rub = 224250  # Utilization fee coefficient 1.3 for old vehicles
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for snowmobiles
        expected_total_rub = 420672
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Снегоход')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_electric_snowmobile_juridical_28000_eur_161hp(self):
        """Test electric snowmobile for legal entity - 28000 EUR, 1 year old, 161hp
        This test covers the fix for electric snowmobile utilization fee calculation.
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.SNOWMOBILE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=28000.0,
            currency='EUR',
            age_years=1,
            engine_volume_cc=0,  # Electric snowmobile has no engine volume
            power_hp=161,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on official customs site calculation
        expected_cost_rub = 28000 * 94.0479  # 2,633,341 rub
        expected_duty_rub = 131667  # 5% duty for all snowmobiles
        expected_vat_rub = 553002  # 20% VAT
        expected_util_fee_rub = 120750  # Utilization fee coefficient 0.7 for new electric snowmobiles (172500 * 0.7)
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for snowmobiles
        expected_total_rub = 817165
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Снегоход')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
    
    def test_old_electric_snowmobile_juridical_21200_eur_107hp(self):
        """Test old electric snowmobile for legal entity - 21200 EUR, 4 years old, 107hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.SNOWMOBILE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=21200.0,
            currency='EUR',
            age_years=4,
            engine_volume_cc=0,  # Electric snowmobile has no engine volume
            power_hp=107,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 21200 * 94.0479  # 1,993,815 rub
        expected_duty_rub = 99691  # 5% duty for all snowmobiles
        expected_vat_rub = 418701  # 20% VAT
        expected_util_fee_rub = 224250  # Utilization fee coefficient 1.3 for old electric snowmobiles
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for snowmobiles
        expected_total_rub = 754388
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Снегоход')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
    
    def test_old_electric_snowmobile_juridical_18000_usd_20hp(self):
        """Test old electric snowmobile for legal entity - 18000 USD, 6 years old, 20hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.SNOWMOBILE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=18000.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=0,  # Electric snowmobile has no engine volume
            power_hp=20,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 18000 * 80.3316  # 1,445,969 rub
        expected_duty_rub = 72298  # 5% duty for all snowmobiles
        expected_vat_rub = 303653  # 20% VAT
        expected_util_fee_rub = 224250  # Utilization fee coefficient 1.3 for old electric snowmobiles
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for snowmobiles
        expected_total_rub = 611948
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Снегоход')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
    
    def test_very_old_electric_snowmobile_juridical_14500_eur_47hp(self):
        """Test very old electric snowmobile for legal entity - 14500 EUR, 8 years old, 47hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.SNOWMOBILE,
            importer_type=ImporterType.JURIDICAL,
            cost_original=14500.0,
            currency='EUR',
            age_years=8,
            engine_volume_cc=0,  # Electric snowmobile has no engine volume
            power_hp=47,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 14500 * 94.0479  # 1,363,695 rub
        expected_duty_rub = 68185  # 5% duty for all snowmobiles
        expected_vat_rub = 286376  # 20% VAT
        expected_util_fee_rub = 224250  # Utilization fee coefficient 1.3 for old electric snowmobiles
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_excise_rub = 0  # No excise for snowmobiles
        expected_total_rub = 590557
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Снегоход')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')


if __name__ == '__main__':
    unittest.main(verbosity=2)