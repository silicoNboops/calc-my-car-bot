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
