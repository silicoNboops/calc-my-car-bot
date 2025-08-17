from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# from api.calculator.models import DutyRate, UtilFee, AcciseRate, CustomsFee, Settings


class Command(BaseCommand):
    help = "Seed customs rates from fixtures JSON files into the database."

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument(
            "--path",
            type=str,
            default=str(Path(__file__).resolve().parents[3] / "api" / "calculator" / "fixtures"),
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

        if not fixtures_dir.exists() or not fixtures_dir.is_dir():
            raise CommandError(f"Fixtures directory not found: {fixtures_dir}")

        # Collect files
        files = sorted(fixtures_dir.glob("*.json"))
        if version_tag:
            files = [p for p in files if version_tag in p.name]
        if not files:
            self.stdout.write(self.style.WARNING("No fixture files found."))
            return

        self.stdout.write(f"Found {len(files)} fixture file(s) in {fixtures_dir}.")

        # For initial skeleton, we don't implement full parsing yet
        # Next steps will implement validation and upsert logic.
        self.stdout.write(self.style.WARNING("Seeding logic is not implemented yet (skeleton)."))
        self.stdout.write("Use --dry-run to just list files:")
        for p in files:
            try:
                # minimal JSON check
                with p.open("r", encoding="utf-8") as f:
                    json.load(f)
                self.stdout.write(f"  - {p.name} [valid JSON]")
            except Exception as e:  # noqa: BLE001
                raise CommandError(f"Invalid JSON in {p.name}: {e}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run finished. No changes applied."))
            return

        if replace:
            self.stdout.write(self.style.WARNING("--replace specified: existing data would be truncated in next step."))

        # Placeholder transaction
        with transaction.atomic():
            # TODO: implement truncate and bulk upsert on next steps
            pass

        self.stdout.write(self.style.SUCCESS("Seed completed (no-op for skeleton)."))
