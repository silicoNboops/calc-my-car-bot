from __future__ import annotations

from rest_framework import serializers


class EstimateRequestSerializer(serializers.Serializer):
    price = serializers.FloatField(min_value=0)
    currency = serializers.ChoiceField(choices=["EUR", "USD", "CNY", "JPY", "KRW", "RUB"])
    engine_cc = serializers.IntegerField(min_value=1)
    hp = serializers.IntegerField(min_value=1)
    engine_type = serializers.ChoiceField(choices=["Бензин", "Дизель"], default="Бензин")
    age_key = serializers.ChoiceField(choices=["under_3", "3_to_5", "5_to_7", "over_7", "over_5"], default="under_3")
    is_jur = serializers.BooleanField(default=False)
    is_personal_use = serializers.BooleanField(required=False)

    def validate(self, attrs: dict) -> dict:  # type: ignore[override]
        is_jur: bool = attrs.get("is_jur", False)
        age_key: str = attrs.get("age_key", "under_3")

        # Default is_personal_use: if not provided, mirror legacy behavior (not is_jur)
        if "is_personal_use" not in attrs:
            attrs["is_personal_use"] = not is_jur

        if is_jur:
            # For legal entities we do not accept 'over_5' (legacy splits into 5-7 and over_7)
            if age_key == "over_5":
                raise serializers.ValidationError({
                    "age_key": "Для юрлиц используйте '5_to_7' или 'over_7' вместо 'over_5'."
                })
        else:
            # For physical persons normalize jur-only tails to 'over_5'
            if age_key in {"5_to_7", "over_7"}:
                attrs["age_key"] = "over_5"

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
