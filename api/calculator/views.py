from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.calculator.serializers import EstimateRequestSerializer, EstimateResponseSerializer
from api.calculator.services import CalculatorService, EstimateInput, get_default_currency_provider


class EstimateView(APIView):
    """Расчёт таможенных платежей.

    Пока логика калькулятора не реализована, возвращаем 501. После переноса правил
    из legacy будет возвращаться рассчитанный ответ.
    """

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = EstimateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        service = CalculatorService(currency_provider=get_default_currency_provider())
        calculator = service.build_calculator()

        try:
            result = calculator.estimate(
                EstimateInput(
                    price=data["price"],
                    currency=data["currency"],
                    engine_cc=data["engine_cc"],
                    hp=data["hp"],
                    engine_type=data.get("engine_type", "Бензин"),
                    age_key=data.get("age_key", "under_3"),
                    is_jur=data.get("is_jur", False),
                    is_personal_use=data.get("is_personal_use"),
                    dvs_hp=data.get("dvs_hp"),
                    electric_hp=data.get("electric_hp"),
                )
            )
        except NotImplementedError:
            return Response({"detail": "Calculation logic not implemented yet"}, status=status.HTTP_501_NOT_IMPLEMENTED)

        out = EstimateResponseSerializer(result)
        return Response(out.data, status=status.HTTP_200_OK)
