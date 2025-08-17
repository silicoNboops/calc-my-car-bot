from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class EstimateView(APIView):
    """Placeholder endpoint for customs calculation.

    Will be implemented in the next steps.
    """

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        return Response({"detail": "Not implemented yet"}, status=status.HTTP_501_NOT_IMPLEMENTED)
