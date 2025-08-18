from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

if TYPE_CHECKING:  # pragma: no cover - type-only import
    from rest_framework.request import Request

from api.calculator.serializers import EstimateRequestSerializer, EstimateResponseSerializer
from api.calculator.services import CalculatorService, EstimateInput, get_default_currency_provider
from api.calculator.choices import (
    Currency as CurrencyChoices,
    VehicleType as VehicleTypeChoices,
    EngineType as EngineTypeChoices,
    AgeKey as AgeKeyChoices,
)


class EstimateView(APIView):
    """Расчёт таможенных платежей.

    Пока логика калькулятора не реализована, возвращаем 501. После переноса правил
    из legacy будет возвращаться рассчитанный ответ.
    """

    def post(self, request: Request, *_args: Any, **_kwargs: Any) -> Response:  # type: ignore[override]
        serializer = EstimateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        service = CalculatorService(currency_provider=get_default_currency_provider())
        calculator = service.build_calculator()

        try:
            result = calculator.estimate(
                EstimateInput(
                    price=data["price"],
                    currency=CurrencyChoices(data["currency"]),
                    engine_cc=data["engine_cc"],
                    hp=data["hp"],
                    vehicle_type=VehicleTypeChoices(data.get("vehicle_type", "car")),
                    engine_type=EngineTypeChoices(data.get("engine_type", "Бензин")),
                    age_key=AgeKeyChoices(data.get("age_key", "under_3")),
                    is_jur=data.get("is_jur", False),
                    is_personal_use=data.get("is_personal_use"),
                    dvs_hp=data.get("dvs_hp"),
                    electric_hp=data.get("electric_hp"),
                ),
            )
        except NotImplementedError:
            return Response({"detail": "Calculation logic not implemented yet"}, status=status.HTTP_501_NOT_IMPLEMENTED)

        out = EstimateResponseSerializer(result)
        return Response(out.data, status=status.HTTP_200_OK)
