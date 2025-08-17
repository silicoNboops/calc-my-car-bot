from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings

from api.calculator.models import DutyRate, UtilFee, AcciseRate, CustomsFee, Settings


class Command(BaseCommand):
    help = "Seed customs rates from fixtures JSON files into the database."

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument(
            "--path",
            type=str,
            # default to app fixtures: api/calculator/fixtures
            default=str(Path(__file__).resolve().parents[2] / "fixtures"),
            help="Directory with fixtures JSON files.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Replace existing data (truncate tables before load).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and show summary without writing to DB.",
        )
        parser.add_argument(
            "--version-tag",
            type=str,
            default=None,
            help="Optional version tag to filter files, e.g., 2025_08_16.",
        )

    def handle(self, *args, **options):  # type: ignore[override]
        fixtures_dir = Path(options["path"]).expanduser().resolve()
        version_tag = options["version_tag"]
        dry_run = options["dry_run"]
        replace = options["replace"]

        # Защита от загрузки шаблонных фикстур в проде: требуем явный --version-tag
        env = getattr(settings, "ENVIRONMENT", "local").lower()
        if env in {"production", "prod"} and not version_tag:
            raise CommandError(
                "Refusing to seed rates in production without --version-tag. "
                "Run with explicit --version-tag=<release_tag>."
            )

        if not fixtures_dir.exists() or not fixtures_dir.is_dir():
            raise CommandError(f"Fixtures directory not found: {fixtures_dir}")

        files = sorted(fixtures_dir.glob("*.json"))
        if version_tag:
            files = [p for p in files if version_tag in p.name]
        if not files:
            self.stdout.write(self.style.WARNING("No fixture files found."))
            return

        self.stdout.write(f"Found {len(files)} fixture file(s) in {fixtures_dir}.")

        payloads: list[dict[str, Any]] = []
        for p in files:
            try:
                with p.open("r", encoding="utf-8") as f:
                    payloads.append(json.load(f))
                self.stdout.write(f"  - {p.name} [loaded]")
            except Exception as e:  # noqa: BLE001
                raise CommandError(f"Invalid JSON in {p.name}: {e}")

        # merge payloads (later files can override earlier ones)
        merged: dict[str, Any] = {
            "settings": None,
            "duty_rates": [],
            "util_fees": [],
            "accise_rates": [],
            "customs_fees": [],
        }
        for data in payloads:
            if data.get("settings"):
                merged["settings"] = data["settings"]
            for key in ("duty_rates", "util_fees", "accise_rates", "customs_fees"):
                merged[key].extend(data.get(key, []))

        # Validate minimal schema
        if merged["settings"] is None:
            self.stdout.write(self.style.WARNING("No 'settings' provided; defaults will be used."))

        summary = {
            "duty": len(merged["duty_rates"]),
            "util": len(merged["util_fees"]),
            "accise": len(merged["accise_rates"]),
            "customs": len(merged["customs_fees"]),
        }
        self.stdout.write(
            f"Summary: duty={summary['duty']}, util={summary['util']}, accise={summary['accise']}, customs={summary['customs']}"
        )

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run finished. No changes applied."))
            return

        with transaction.atomic():
            if replace:
                DutyRate.objects.all().delete()
                UtilFee.objects.all().delete()
                AcciseRate.objects.all().delete()
                CustomsFee.objects.all().delete()
                # Settings: keep history minimal, just single latest row
                Settings.objects.all().delete()

            # Upsert settings (single row)
            settings_payload = merged.get("settings") or {}
            if settings_payload:
                Settings.objects.create(
                    vat_rate=settings_payload.get("vat_rate", 0.2),
                    company_commission_rub=settings_payload.get("company_commission_rub", 69000.0),
                )

            # Bulk create rate tables
            if merged["duty_rates"]:
                DutyRate.objects.bulk_create([
                    DutyRate(
                        audience=item["audience"],
                        age_group=item["age_group"],
                        unit=item["unit"],
                        max_value=item.get("max_value"),
                        rate_percent=item.get("rate_percent"),
                        rate_eur_cc=item.get("rate_eur_cc"),
                        min_rate_eur_cc=item.get("min_rate_eur_cc"),
                    )
                    for item in merged["duty_rates"]
                ])

            if merged["util_fees"]:
                UtilFee.objects.bulk_create([
                    UtilFee(
                        kind=item["kind"],
                        max_cc=item.get("max_cc"),
                        coeff=item["coeff"],
                    )
                    for item in merged["util_fees"]
                ])

            if merged["accise_rates"]:
                AcciseRate.objects.bulk_create([
                    AcciseRate(
                        max_hp=item["max_hp"],
                        rate_rub_per_hp=item["rate_rub_per_hp"],
                    )
                    for item in merged["accise_rates"]
                ])

            if merged["customs_fees"]:
                CustomsFee.objects.bulk_create([
                    CustomsFee(
                        max_value_rub=item["max_value_rub"],
                        fee_rub=item["fee_rub"],
                    )
                    for item in merged["customs_fees"]
                ])

        self.stdout.write(self.style.SUCCESS("Seed completed successfully."))
