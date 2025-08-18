from __future__ import annotations

import csv
import json
from datetime import date, datetime
from typing import Iterable

from django.http import HttpResponse


def _serialize_value(value: object) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return "" if value is None else str(value)


def export_as_csv(modeladmin, request, queryset):  # noqa: D401
    """Admin action: export selected queryset as CSV of model concrete fields."""
    opts = modeladmin.model._meta
    field_names: list[str] = [f.name for f in opts.concrete_fields]

    filename = f"{opts.app_label}-{opts.model_name}.csv"
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f"attachment; filename={filename}"

    writer = csv.writer(response)
    writer.writerow(field_names)

    for obj in queryset.iterator():
        row = [_serialize_value(getattr(obj, f)) for f in field_names]
        writer.writerow(row)

    return response


def export_as_json(modeladmin, request, queryset):  # noqa: D401
    """Admin action: export selected queryset as JSON (list of dicts)."""
    opts = modeladmin.model._meta
    filename = f"{opts.app_label}-{opts.model_name}.json"

    data: Iterable[dict] = queryset.values()
    body = json.dumps(list(data), ensure_ascii=False, default=_serialize_value)

    response = HttpResponse(body, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


# Nice names in actions dropdown (Russian)
export_as_csv.short_description = "Экспорт в CSV"  # type: ignore[attr-defined]
export_as_json.short_description = "Экспорт в JSON"  # type: ignore[attr-defined]
