from __future__ import annotations

from django.urls import path

from api.calculator.views import EstimateView

app_name = "calculator"

urlpatterns = [
    path("estimate/", EstimateView.as_view(), name="estimate"),
]
