# Makes calculator_v2 a package for clean imports

from .customs_calculator_v6 import (
    VehicleSpec,
    VehicleType,
    ImporterType,
    EngineType,
    FuelType,
    CalculationResult,
    calculate_customs_payments,
)

__all__ = [
    "VehicleSpec",
    "VehicleType",
    "ImporterType",
    "EngineType",
    "FuelType",
    "CalculationResult",
    "calculate_customs_payments",
]
