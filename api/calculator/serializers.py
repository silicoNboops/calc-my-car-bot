from __future__ import annotations

from rest_framework import serializers


class EstimateRequestSerializer(serializers.Serializer):
    price = serializers.FloatField(min_value=0)
    currency = serializers.ChoiceField(choices=["EUR", "USD", "CNY", "JPY", "KRW", "RUB"])
    engine_cc = serializers.IntegerField(min_value=1)
    hp = serializers.IntegerField(min_value=1)
    vehicle_type = serializers.ChoiceField(
        choices=["car", "quad", "snowmobile", "motorcycle"], default="car",
    )
    engine_type = serializers.ChoiceField(
        choices=[
            "Бензин",
            "Дизель",
            "Электро",
            "Гибрид(послед)",
            "Гибрид(паралл)",
        ],
        default="Бензин",
    )
    age_key = serializers.ChoiceField(choices=["under_3", "3_to_5", "5_to_7", "over_7", "over_5"], default="under_3")
    is_jur = serializers.BooleanField(default=False)
    is_personal_use = serializers.BooleanField(required=False)
    # Доп. поля для гибридов (опционально)
    dvs_hp = serializers.IntegerField(min_value=0, required=False)
    electric_hp = serializers.IntegerField(min_value=0, required=False)

    def validate(self, attrs: dict) -> dict:  # type: ignore[override]
        is_jur: bool = attrs.get("is_jur", False)
        age_key: str = attrs.get("age_key", "under_3")
        engine_type: str = attrs.get("engine_type", "Бензин")
        vehicle_type: str = attrs.get("vehicle_type", "car")

        # Default is_personal_use: if not provided, mirror legacy behavior (not is_jur)
        if "is_personal_use" not in attrs:
            attrs["is_personal_use"] = not is_jur

        if is_jur:
            # For legal entities we do not accept 'over_5' (legacy splits into 5-7 and over_7)
            if age_key == "over_5":
                raise serializers.ValidationError({
                    "age_key": "Для юрлиц используйте '5_to_7' или 'over_7' вместо 'over_5'.",
                })
        elif age_key in {"5_to_7", "over_7"}:
            # For physical persons normalize jur-only tails to 'over_5'
            attrs["age_key"] = "over_5"

        # Валидация для гибридов
        if engine_type in {"Гибрид(послед)", "Гибрид(паралл)"}:
            dvs_hp = int(attrs.get("dvs_hp") or 0)
            electric_hp = int(attrs.get("electric_hp") or 0)
            # Не заставляем указывать оба, но проверим разумность
            if dvs_hp < 0 or electric_hp < 0:
                raise serializers.ValidationError({"dvs_hp": "Значение не может быть отрицательным", "electric_hp": "Значение не может быть отрицательным"})

        # Ограничения по типу ТС: для не-"car" запрещаем EV/гибриды
        if vehicle_type != "car" and engine_type in {"Электро", "Гибрид(послед)", "Гибрид(паралл)"}:
            raise serializers.ValidationError({
                "engine_type": "Для выбранного типа ТС поддерживаются только ДВС (Бензин/Дизель).",
            })

        return attrs


class EstimateResponseSerializer(serializers.Serializer):
    price_rub = serializers.FloatField()
    price_eur = serializers.FloatField()
    duty_eur = serializers.FloatField()
    duty_rub = serializers.FloatField()
    util_fee = serializers.FloatField()
    accise_rub = serializers.FloatField()
    vat_rub = serializers.FloatField()
    customs_fee = serializers.FloatField()
    subtotal_customs = serializers.FloatField()
