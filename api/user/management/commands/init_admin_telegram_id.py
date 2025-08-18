from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = (
        "Assign telegram_id = -1 to the initial admin (first superuser without telegram_id)."
    )

    def handle(self, *args, **options):  # noqa: D401
        User = get_user_model()

        with transaction.atomic():
            minus_one_holder = User.objects.filter(telegram_id=-1).first()
            if minus_one_holder:
                self.stdout.write(
                    self.style.WARNING(
                        f"telegram_id = -1 is already used by user id={minus_one_holder.id}. Nothing to do."
                    )
                )
                return

            admin = (
                User.objects.filter(is_superuser=True, telegram_id__isnull=True)
                .order_by("date_joined")
                .first()
            )

            if not admin:
                self.stdout.write(
                    self.style.WARNING(
                        "No superuser without telegram_id found. Nothing to do."
                    )
                )
                return

            admin.telegram_id = -1
            admin.save(update_fields=["telegram_id"])  # type: ignore[arg-type]
            self.stdout.write(
                self.style.SUCCESS(
                    f"Assigned telegram_id = -1 to superuser id={admin.id} username={admin.username}"
                )
            )
