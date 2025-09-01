#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for cars customs calculations
Testing various scenarios for different importer types with gasoline, diesel, and electric engines
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


class TestCars(unittest.TestCase):
    """Test cases for cars customs calculations"""
    
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
    
    def test_diesel_car_juridical_25000_usd_2200cc_163hp(self):
        """Test diesel car for legal entity - 25000 USD, 4 years old, 2200cc, 163hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.JURIDICAL,
            cost_original=25000.0,
            currency='USD',
            age_years=4,
            engine_volume_cc=2200,
            power_hp=163,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.DIESEL
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 25000 * 80.3316  # 2,008,290 rub
        expected_duty_rub = 401658  # Duty for juridical diesel car 4 years old
        expected_excise_rub = 95029  # Excise for 163hp car
        expected_vat_rub = 500995  # 20% VAT
        expected_util_fee_rub = 2839400  # Utilization fee for juridical old car
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_total_rub = 3848828
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_electric_car_phys_resale_38000_usd_283hp(self):
        """Test electric car for physical person resale - 38000 USD, 2 years old, 283hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=38000.0,
            currency='USD',
            age_years=2,
            engine_volume_cc=0,  # Electric car has no engine volume
            power_hp=283,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 38000 * 80.3316  # 3,052,601 rub
        expected_duty_rub = 457890  # 15% duty for electric cars
        expected_excise_rub = 270265  # Electric car excise: 283hp * 955 rub/hp (283hp is in 201-300hp range)
        expected_vat_rub = 756151  # 20% VAT
        expected_util_fee_rub = 667400  # Utilization fee for resale new electric car
        expected_customs_fee_rub = 16524  # Fixed fee for this cost range
        expected_total_rub = 2168230
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (перепродажа)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
    
    def test_electric_car_phys_resale_12000_usd_150hp(self):
        """Test electric car for physical person resale - 12000 USD, 7 years old, 150hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=12000.0,
            currency='USD',
            age_years=7,
            engine_volume_cc=0,  # Electric car has no engine volume
            power_hp=150,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 12000 * 80.3316  # 963,979 rub
        expected_duty_rub = 144597  # 15% duty for electric cars
        expected_excise_rub = 9150  # Electric car excise: 150hp * 61 rub/hp (150hp is in 91-150hp range)
        expected_vat_rub = 223545  # 20% VAT
        expected_util_fee_rub = 1174000  # Utilization fee for resale old electric car
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 1555561
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (перепродажа)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
    
    def test_electric_car_juridical_90000_usd_530hp(self):
        """Test high-power electric car for legal entity - 90000 USD, 1 year old, 530hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.JURIDICAL,
            cost_original=90000.0,
            currency='USD',
            age_years=1,
            engine_volume_cc=0,  # Electric car has no engine volume
            power_hp=530,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 90000 * 80.3316  # 7,229,844 rub
        expected_duty_rub = 1084477  # 15% duty for electric cars
        expected_excise_rub = 922200  # Electric car excise: 530hp * 1740 rub/hp (530hp is >500hp range)
        expected_vat_rub = 1847304  # 20% VAT
        expected_util_fee_rub = 667400  # Utilization fee for juridical new electric car
        expected_customs_fee_rub = 30000  # Fixed fee for this cost range
        expected_total_rub = 4551381
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
    
    def test_electric_car_excise_power_ranges(self):
        """Test that electric cars use correct excise rates based on power ranges"""
        test_cases = [
            {'power': 85, 'expected_rate': 0, 'range': '≤90hp'},
            {'power': 120, 'expected_rate': 61, 'range': '91-150hp'},
            {'power': 180, 'expected_rate': 583, 'range': '151-200hp'},
            {'power': 250, 'expected_rate': 955, 'range': '201-300hp'},
            {'power': 350, 'expected_rate': 1628, 'range': '301-400hp'},
            {'power': 450, 'expected_rate': 1685, 'range': '401-500hp'},
            {'power': 600, 'expected_rate': 1740, 'range': '>500hp'}
        ]
        
        for case in test_cases:
            with self.subTest(power=case['power'], range=case['range']):
                spec = VehicleSpec(
                    vehicle_type=VehicleType.CAR,
                    importer_type=ImporterType.JURIDICAL,
                    cost_original=20000.0,
                    currency='USD',
                    age_years=2,
                    engine_volume_cc=0,
                    power_hp=case['power'],
                    engine_type=EngineType.ELECTRIC,
                    fuel_type=FuelType.ELECTRIC
                )
                
                result = calculate_customs_payments(spec)
                expected_excise = case['power'] * case['expected_rate']
                
                self.assertAlmostEqualPercent(result.excise_rub, expected_excise, 1.0,
                                            f"Wrong excise rate for {case['range']} (power={case['power']}hp)")
    
    def test_electric_car_personal_use_still_has_excise(self):
        """Test that electric cars have excise tax even for personal use (unlike conventional cars)"""
        spec_electric = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=20000.0,
            currency='USD',
            age_years=2,
            engine_volume_cc=0,
            power_hp=150,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result_electric = calculate_customs_payments(spec_electric)
        expected_excise_electric = 150 * 61  # 9150 rub
        
        self.assertAlmostEqualPercent(result_electric.excise_rub, expected_excise_electric, 1.0,
                                    "Electric cars should have excise even for personal use")
        
        # Compare with conventional car for personal use (should be 0)
        spec_gasoline = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=20000.0,
            currency='USD',
            age_years=2,
            engine_volume_cc=2000,
            power_hp=150,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result_gasoline = calculate_customs_payments(spec_gasoline)
        
        self.assertEqual(result_gasoline.excise_rub, 0.0,
                        "Conventional cars should have no excise for personal use")
    
    def test_electric_car_personal_use_has_vat(self):
        """Test that electric cars for personal use have VAT applied (unlike conventional cars)
        This test covers the Nissan Leaf scenario from user feedback.
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=12000.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=0,  # Electric car has no engine volume
            power_hp=150,
            engine_type=EngineType.ELECTRIC,
            fuel_type=FuelType.ELECTRIC
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation from official site
        expected_cost_rub = 12000 * 80.3316  # 963,979 rub
        expected_duty_rub = 144597  # 15% duty for electric cars
        expected_excise_rub = 9150  # Electric car excise: 150hp * 61 rub/hp
        expected_vat_rub = 223545  # 20% VAT (should be applied for electric cars even personal use)
        expected_util_fee_rub = 5200  # Personal use utilization fee for old electric car
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 386761
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Verify that VAT is correctly applied for electric cars personal use
        self.assertGreater(result.vat_rub, 0, "Electric cars should have VAT even for personal use")
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (личное использование)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'Электро')
        
        # Compare with conventional car for personal use (should not have VAT)
        spec_conventional = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=12000.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=2000,
            power_hp=150,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result_conventional = calculate_customs_payments(spec_conventional)
        self.assertEqual(result_conventional.vat_rub, 0.0,
                        "Conventional cars should not have VAT for personal use")
    
    def test_gasoline_car_personal_16000_usd_2500cc_181hp_new(self):
        """Test new gasoline car for personal use - 16000 USD, 2 years old, 2500cc, 181hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=16000.0,
            currency='USD',
            age_years=2,
            engine_volume_cc=2500,
            power_hp=181,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 16000 * 80.3316  # 1,285,306 rub
        expected_duty_rub = 822919  # ETS duty for new car personal use
        expected_excise_rub = 0  # No excise for personal use conventional cars
        expected_vat_rub = 0  # No VAT for personal use conventional cars
        expected_util_fee_rub = 3400  # Personal use utilization fee for new car
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_total_rub = 838065
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (личное использование)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_gasoline_car_personal_16000_usd_2500cc_181hp_old(self):
        """Test old gasoline car for personal use - 16000 USD, 6 years old, 2500cc, 181hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=16000.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=2500,
            power_hp=181,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 16000 * 80.3316  # 1,285,306 rub
        expected_duty_rub = 1175599  # ETS duty for old car personal use (higher rates)
        expected_excise_rub = 0  # No excise for personal use conventional cars
        expected_vat_rub = 0  # No VAT for personal use conventional cars
        expected_util_fee_rub = 5200  # Personal use utilization fee for old car
        expected_customs_fee_rub = 11746  # Fixed fee for this cost range
        expected_total_rub = 1192545
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (личное использование)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_gasoline_car_personal_8000_usd_1600cc_106hp_new(self):
        """Test new gasoline car for personal use - 8000 USD, 1 year old, 1600cc, 106hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=8000.0,
            currency='USD',
            age_years=1,
            engine_volume_cc=1600,
            power_hp=106,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 8000 * 80.3316  # 642,653 rub
        expected_duty_rub = 376192  # ETS duty for new car personal use
        expected_excise_rub = 0  # No excise for personal use conventional cars
        expected_vat_rub = 0  # No VAT for personal use conventional cars
        expected_util_fee_rub = 3400  # Personal use utilization fee for new car
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 383861
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (личное использование)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_conventional_cars_personal_use_exemptions(self):
        """Test that conventional cars for personal use have proper exemptions from excise and VAT"""
        test_cases = [
            {'cost': 8000, 'age': 1, 'volume': 1600, 'power': 106},
            {'cost': 16000, 'age': 2, 'volume': 2500, 'power': 181},
            {'cost': 16000, 'age': 6, 'volume': 2500, 'power': 181},
            {'cost': 20000, 'age': 3, 'volume': 3000, 'power': 250}  # High power case
        ]
        
        for case in test_cases:
            with self.subTest(cost=case['cost'], age=case['age'], power=case['power']):
                spec = VehicleSpec(
                    vehicle_type=VehicleType.CAR,
                    importer_type=ImporterType.PHYS_PERSONAL,
                    cost_original=case['cost'],
                    currency='USD',
                    age_years=case['age'],
                    engine_volume_cc=case['volume'],
                    power_hp=case['power'],
                    engine_type=EngineType.DVS,
                    fuel_type=FuelType.GASOLINE
                )
                
                result = calculate_customs_payments(spec)
                
                # Verify exemptions for personal use conventional cars
                self.assertEqual(result.excise_rub, 0.0,
                               f"Conventional cars should have no excise for personal use (cost={case['cost']}, power={case['power']}hp)")
                self.assertEqual(result.vat_rub, 0.0,
                               f"Conventional cars should have no VAT for personal use (cost={case['cost']})")
                
                # Verify that duty and utilization fees are still applied
                self.assertGreater(result.duty_rub, 0,
                                 f"Conventional cars should still have duty for personal use (cost={case['cost']})")
                self.assertGreater(result.util_fee_rub, 0,
                                 f"Conventional cars should still have utilization fee for personal use (cost={case['cost']})")
    
    def test_conventional_car_phys_resale_50000_usd_3000cc_340hp(self):
        """Test conventional car for physical person resale - BMW X5 scenario
        This test covers the fix for PHYS_RESALE conventional cars having no excise and no VAT.
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=50000.0,
            currency='USD',
            age_years=4,
            engine_volume_cc=3000,
            power_hp=340,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation (BMW X5 scenario)
        expected_cost_rub = 50000 * 80.3316  # 4,016,580 rub
        expected_duty_rub = 846431  # ETS duty: 3 EUR/cc × 3000cc = 9000 EUR
        expected_excise_rub = 0  # No excise for PHYS_RESALE conventional cars
        expected_vat_rub = 0  # No VAT for PHYS_RESALE conventional cars
        expected_util_fee_rub = 2839400  # Utilization fee for resale old car
        expected_customs_fee_rub = 16524  # Fixed fee for this cost range
        expected_total_rub = 3702355
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Verify exemptions for PHYS_RESALE conventional cars
        self.assertEqual(result.excise_rub, 0.0, "Conventional cars should have no excise for PHYS_RESALE")
        self.assertEqual(result.vat_rub, 0.0, "Conventional cars should have no VAT for PHYS_RESALE")
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (перепродажа)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_gasoline_car_phys_resale_8000_usd_1600cc_106hp_new(self):
        """Test new gasoline car for physical person resale - 8000 USD, 1 year old, 1600cc, 106hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=8000.0,
            currency='USD',
            age_years=1,
            engine_volume_cc=1600,
            power_hp=106,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 8000 * 80.3316  # 642,653 rub
        expected_duty_rub = 376192  # ETS duty for new car
        expected_excise_rub = 0  # No excise for PHYS_RESALE conventional cars
        expected_vat_rub = 0  # No VAT for PHYS_RESALE conventional cars
        expected_util_fee_rub = 667400  # Utilization fee for resale new car
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 1047861
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (перепродажа)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_diesel_car_phys_resale_10000_usd_2000cc_150hp_old(self):
        """Test old diesel car for physical person resale - 10000 USD, 8 years old, 2000cc, 150hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=10000.0,
            currency='USD',
            age_years=8,
            engine_volume_cc=2000,
            power_hp=150,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.DIESEL
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 10000 * 80.3316  # 803,316 rub
        expected_duty_rub = 902860  # ETS duty for old car (higher rate)
        expected_excise_rub = 0  # No excise for PHYS_RESALE conventional cars
        expected_vat_rub = 0  # No VAT for PHYS_RESALE conventional cars
        expected_util_fee_rub = 1174000  # Utilization fee for resale old car
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 2081129
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (перепродажа)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_diesel_car_personal_10000_usd_2000cc_150hp_old(self):
        """Test old diesel car for personal use - 10000 USD, 8 years old, 2000cc, 150hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=10000.0,
            currency='USD',
            age_years=8,
            engine_volume_cc=2000,
            power_hp=150,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.DIESEL
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 10000 * 80.3316  # 803,316 rub
        expected_duty_rub = 902860  # ETS duty for old car (same as resale)
        expected_excise_rub = 0  # No excise for personal use conventional cars
        expected_vat_rub = 0  # No VAT for personal use conventional cars
        expected_util_fee_rub = 5200  # Personal use utilization fee for old car (much lower)
        expected_customs_fee_rub = 4269  # Fixed fee for this cost range
        expected_total_rub = 912329
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (личное использование)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_diesel_car_personal_60000_usd_3000cc_306hp_old(self):
        """Test old high-power diesel car for personal use - 60000 USD, 6 years old, 3000cc, 306hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=60000.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=3000,
            power_hp=306,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.DIESEL
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 60000 * 80.3316  # 4,819,896 rub
        expected_duty_rub = 1410718  # ETS duty for old expensive car
        expected_excise_rub = 0  # No excise for personal use conventional cars (even high power)
        expected_vat_rub = 0  # No VAT for personal use conventional cars
        expected_util_fee_rub = 5200  # Personal use utilization fee for old car
        expected_customs_fee_rub = 21344  # Fixed fee for this high cost range
        expected_total_rub = 1437262
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (личное использование)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_diesel_car_phys_resale_60000_usd_3000cc_306hp_old(self):
        """Test old high-power diesel car for physical person resale - 60000 USD, 6 years old, 3000cc, 306hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=60000.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=3000,
            power_hp=306,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.DIESEL
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 60000 * 80.3316  # 4,819,896 rub
        expected_duty_rub = 1410718  # ETS duty for old expensive car (same as personal)
        expected_excise_rub = 0  # No excise for PHYS_RESALE conventional cars (even high power)
        expected_vat_rub = 0  # No VAT for PHYS_RESALE conventional cars
        expected_util_fee_rub = 2839400  # Utilization fee for resale old car (much higher than personal)
        expected_customs_fee_rub = 21344  # Fixed fee for this high cost range
        expected_total_rub = 4271462
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Физлицо (перепродажа)')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_diesel_car_juridical_60000_usd_3000cc_306hp_old(self):
        """Test old high-power diesel car for legal entity - 60000 USD, 6 years old, 3000cc, 306hp"""
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.JURIDICAL,
            cost_original=60000.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=3000,
            power_hp=306,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.DIESEL
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on user's verified calculation
        expected_cost_rub = 60000 * 80.3316  # 4,819,896 rub
        expected_duty_rub = 963979  # Juridical duty calculation (different from ETS)
        expected_excise_rub = 498168  # Excise for 306hp car for juridical entity
        expected_vat_rub = 1256409  # 20% VAT for juridical entity
        expected_util_fee_rub = 2839400  # Utilization fee for juridical old car
        expected_customs_fee_rub = 21344  # Fixed fee for this cost range
        expected_total_rub = 5579300
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
        
        # Test breakdown data
        self.assertEqual(result.breakdown['vehicle_type_ru'], 'Легковой автомобиль')
        self.assertEqual(result.breakdown['importer_type_ru'], 'Юридическое лицо')
        self.assertEqual(result.breakdown['engine_type_ru'], 'ДВС')
    
    def test_gasoline_car_phys_resale_8000_usd_1600cc_106hp_new_interactive(self):
        """Test new gasoline car for physical person resale - 8000 USD, 1 year old, 1600cc, 106hp
        This test verifies the interactive mode calculation from test 1.
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=8000.0,
            currency='USD',
            age_years=1,
            engine_volume_cc=1600,
            power_hp=106,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.GASOLINE
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on interactive mode output - Total: 1,047,861 rub
        expected_cost_rub = 8000 * 80.3316  # 642,653 rub
        expected_duty_rub = 376192  # Duty (4000.00 EUR)
        expected_excise_rub = 0  # No excise for PHYS_RESALE conventional cars
        expected_vat_rub = 0  # No VAT for PHYS_RESALE conventional cars
        expected_util_fee_rub = 667400  # Utilization fee
        expected_customs_fee_rub = 4269  # Customs fee
        expected_total_rub = 1047861
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
    
    def test_diesel_car_phys_resale_10000_usd_2000cc_150hp_old_interactive(self):
        """Test old diesel car for physical person resale - 10000 USD, 8 years old, 2000cc, 150hp
        This test verifies the interactive mode calculation from test 2.
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=10000.0,
            currency='USD',
            age_years=8,
            engine_volume_cc=2000,
            power_hp=150,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.DIESEL
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on interactive mode output - Total: 2,081,129 rub
        expected_cost_rub = 10000 * 80.3316  # 803,316 rub
        expected_duty_rub = 902860  # Duty (9600.00 EUR)
        expected_excise_rub = 0  # No excise for PHYS_RESALE conventional cars
        expected_vat_rub = 0  # No VAT for PHYS_RESALE conventional cars
        expected_util_fee_rub = 1174000  # Utilization fee
        expected_customs_fee_rub = 4269  # Customs fee
        expected_total_rub = 2081129
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
    
    def test_diesel_car_personal_10000_usd_2000cc_150hp_old_interactive(self):
        """Test old diesel car for personal use - 10000 USD, 8 years old, 2000cc, 150hp
        This test verifies the interactive mode calculation from test 3.
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=10000.0,
            currency='USD',
            age_years=8,
            engine_volume_cc=2000,
            power_hp=150,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.DIESEL
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on interactive mode output - Total: 912,329 rub
        expected_cost_rub = 10000 * 80.3316  # 803,316 rub
        expected_duty_rub = 902860  # Duty (9600.00 EUR)
        expected_excise_rub = 0  # No excise for personal use conventional cars
        expected_vat_rub = 0  # No VAT for personal use conventional cars
        expected_util_fee_rub = 5200  # Personal use utilization fee
        expected_customs_fee_rub = 4269  # Customs fee
        expected_total_rub = 912329
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
    
    def test_diesel_car_personal_60000_usd_3000cc_306hp_old_interactive(self):
        """Test old high-power diesel car for personal use - 60000 USD, 6 years old, 3000cc, 306hp
        This test verifies the interactive mode calculation from test 4.
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=60000.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=3000,
            power_hp=306,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.DIESEL
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on interactive mode output - Total: 1,437,262 rub
        expected_cost_rub = 60000 * 80.3316  # 4,819,896 rub
        expected_duty_rub = 1410718  # Duty (15000.00 EUR)
        expected_excise_rub = 0  # No excise for personal use conventional cars
        expected_vat_rub = 0  # No VAT for personal use conventional cars
        expected_util_fee_rub = 5200  # Personal use utilization fee
        expected_customs_fee_rub = 21344  # Customs fee
        expected_total_rub = 1437262
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
    
    def test_diesel_car_phys_resale_60000_usd_3000cc_306hp_old_interactive(self):
        """Test old high-power diesel car for physical person resale - 60000 USD, 6 years old, 3000cc, 306hp
        This test verifies the interactive mode calculation from test 5.
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=60000.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=3000,
            power_hp=306,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.DIESEL
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on interactive mode output - Total: 4,271,462 rub
        expected_cost_rub = 60000 * 80.3316  # 4,819,896 rub
        expected_duty_rub = 1410718  # Duty (15000.00 EUR)
        expected_excise_rub = 0  # No excise for PHYS_RESALE conventional cars
        expected_vat_rub = 0  # No VAT for PHYS_RESALE conventional cars
        expected_util_fee_rub = 2839400  # Utilization fee for resale
        expected_customs_fee_rub = 21344  # Customs fee
        expected_total_rub = 4271462
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
    
    def test_diesel_car_juridical_60000_usd_3000cc_306hp_old_interactive(self):
        """Test old high-power diesel car for legal entity - 60000 USD, 6 years old, 3000cc, 306hp
        This test verifies the interactive mode calculation from test 6.
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.JURIDICAL,
            cost_original=60000.0,
            currency='USD',
            age_years=6,
            engine_volume_cc=3000,
            power_hp=306,
            engine_type=EngineType.DVS,
            fuel_type=FuelType.DIESEL
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on interactive mode output - Total: 5,579,300 rub
        expected_cost_rub = 60000 * 80.3316  # 4,819,896 rub
        expected_duty_rub = 963979  # Duty (10249.87 EUR)
        expected_excise_rub = 498168  # Excise for juridical entity
        expected_vat_rub = 1256409  # 20% VAT for juridical entity
        expected_util_fee_rub = 2839400  # Utilization fee
        expected_customs_fee_rub = 21344  # Customs fee
        expected_total_rub = 5579300
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
    
    def test_hybrid_gasoline_car_phys_resale_45000_usd_1600cc_160hp_parallel(self):
        """Test parallel gasoline hybrid car for physical person resale - 45000 USD, 1 year old, 1600cc, 160hp
        This test verifies the interactive mode calculation from test 1 (parallel hybrid with ICE > Electric).
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=45000.0,
            currency='USD',
            age_years=1,
            engine_volume_cc=1600,
            power_hp=160,
            engine_type=EngineType.HYBRID_PARALLEL,
            fuel_type=FuelType.GASOLINE_ELECTRIC,
            is_series_hybrid=False,
            dvs_power_hp=160,
            electric_power_hp=1,
            dvs_power_greater_than_electric=True
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on interactive mode output - Total: 2,419,087 rub
        expected_cost_rub = 45000 * 80.3316  # 3,614,922 rub
        expected_duty_rub = 1735163  # Duty (18449.77 EUR)
        expected_excise_rub = 0  # No excise for PHYS_RESALE conventional hybrids
        expected_vat_rub = 0  # No VAT for PHYS_RESALE conventional hybrids
        expected_util_fee_rub = 667400  # Utilization fee for resale new car
        expected_customs_fee_rub = 16524  # Customs fee
        expected_total_rub = 2419087
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
    
    def test_hybrid_gasoline_car_personal_45000_usd_1600cc_160hp_parallel(self):
        """Test parallel gasoline hybrid car for personal use - 45000 USD, 1 year old, 1600cc, 160hp
        This test verifies the interactive mode calculation from test 2 (parallel hybrid with ICE > Electric).
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_PERSONAL,
            cost_original=45000.0,
            currency='USD',
            age_years=1,
            engine_volume_cc=1600,
            power_hp=160,
            engine_type=EngineType.HYBRID_PARALLEL,
            fuel_type=FuelType.GASOLINE_ELECTRIC,
            is_series_hybrid=False,
            dvs_power_hp=160,
            electric_power_hp=1,
            dvs_power_greater_than_electric=True
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on interactive mode output - Total: 1,755,087 rub
        expected_cost_rub = 45000 * 80.3316  # 3,614,922 rub
        expected_duty_rub = 1735163  # Duty (18449.77 EUR)
        expected_excise_rub = 0  # No excise for personal use conventional hybrids
        expected_vat_rub = 0  # No VAT for personal use conventional hybrids
        expected_util_fee_rub = 3400  # Personal use utilization fee for new car
        expected_customs_fee_rub = 16524  # Customs fee
        expected_total_rub = 1755087
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
    
    def test_hybrid_gasoline_car_phys_resale_25000_usd_1400cc_120hp_sequential(self):
        """Test sequential gasoline hybrid car for physical person resale - 25000 USD, 4 years old, 1400cc, 120hp
        This test verifies the interactive mode calculation from test 3 (sequential hybrid with Electric >= ICE).
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=25000.0,
            currency='USD',
            age_years=4,
            engine_volume_cc=1400,
            power_hp=120,
            engine_type=EngineType.HYBRID_SERIES,
            fuel_type=FuelType.GASOLINE_ELECTRIC,
            is_series_hybrid=True,
            dvs_power_hp=120,
            electric_power_hp=120,
            dvs_power_greater_than_electric=False
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on interactive mode output - Total: 1,957,680 rub
        expected_cost_rub = 25000 * 80.3316  # 2,008,290 rub
        expected_duty_rub = 301243  # Duty (3203.09 EUR)
        expected_excise_rub = 7320  # Excise for sequential hybrid (120hp * 61 rub/hp)
        expected_vat_rub = 463371  # 20% VAT for sequential hybrid resale
        expected_util_fee_rub = 1174000  # Utilization fee for resale old car
        expected_customs_fee_rub = 11746  # Customs fee
        expected_total_rub = 1957680
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
    
    def test_hybrid_diesel_car_phys_resale_30000_usd_1800cc_150hp_sequential(self):
        """Test sequential diesel hybrid car for physical person resale - 30000 USD, 4 years old, 1800cc, 150hp
        This test verifies the interactive mode calculation from test 4 (sequential diesel hybrid with Electric >= ICE).
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=30000.0,
            currency='USD',
            age_years=4,
            engine_volume_cc=1800,
            power_hp=150,
            engine_type=EngineType.HYBRID_SERIES,
            fuel_type=FuelType.DIESEL_ELECTRIC,
            is_series_hybrid=True,
            dvs_power_hp=150,
            electric_power_hp=150,
            dvs_power_greater_than_electric=False
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on interactive mode output - Total: 2,112,506 rub
        expected_cost_rub = 30000 * 80.3316  # 2,409,948 rub
        expected_duty_rub = 361492  # Duty (3843.70 EUR)
        expected_excise_rub = 9150  # Excise for sequential hybrid (150hp * 61 rub/hp)
        expected_vat_rub = 556118  # 20% VAT for sequential hybrid resale
        expected_util_fee_rub = 1174000  # Utilization fee for resale old car
        expected_customs_fee_rub = 11746  # Customs fee
        expected_total_rub = 2112506
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)
    
    def test_hybrid_gasoline_car_phys_resale_12000_usd_1200cc_100hp_parallel_old(self):
        """Test old parallel gasoline hybrid car for physical person resale - 12000 USD, 8 years old, 1200cc, 100hp
        This test verifies the interactive mode calculation from test 5 (parallel hybrid with Electric >= ICE).
        """
        spec = VehicleSpec(
            vehicle_type=VehicleType.CAR,
            importer_type=ImporterType.PHYS_RESALE,
            cost_original=12000.0,
            currency='USD',
            age_years=8,
            engine_volume_cc=1200,
            power_hp=100,
            engine_type=EngineType.HYBRID_PARALLEL,
            fuel_type=FuelType.GASOLINE_ELECTRIC,
            is_series_hybrid=False,
            dvs_power_hp=100,
            electric_power_hp=100,
            dvs_power_greater_than_electric=False
        )
        
        result = calculate_customs_payments(spec)
        
        # Expected values based on interactive mode output - Total: 1,539,413 rub
        expected_cost_rub = 12000 * 80.3316  # 963,979 rub
        expected_duty_rub = 361144  # Duty (3840.00 EUR)
        expected_excise_rub = 0  # No excise for PHYS_RESALE conventional hybrids
        expected_vat_rub = 0  # No VAT for PHYS_RESALE conventional hybrids
        expected_util_fee_rub = 1174000  # Utilization fee for resale old car
        expected_customs_fee_rub = 4269  # Customs fee
        expected_total_rub = 1539413
        
        # Test individual components with 1% tolerance
        self.assertAlmostEqualPercent(result.cost_rub, expected_cost_rub, 1.0)
        self.assertAlmostEqualPercent(result.duty_rub, expected_duty_rub, 1.0)
        self.assertAlmostEqualPercent(result.excise_rub, expected_excise_rub, 1.0)
        self.assertAlmostEqualPercent(result.vat_rub, expected_vat_rub, 1.0)
        self.assertAlmostEqualPercent(result.util_fee_rub, expected_util_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.customs_fee_rub, expected_customs_fee_rub, 1.0)
        self.assertAlmostEqualPercent(result.total_rub, expected_total_rub, 1.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)