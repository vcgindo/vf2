import os

from django.core.management.base import BaseCommand, CommandError

from mto_app.models import DBRSettings


class Command(BaseCommand):
    help = "Apply explicit development-only MTO browser acceptance settings."

    def handle(self, *args, **options):
        raw = os.environ.get("MTO_STAGE7B_ENABLE_DDQ_UI", "false").strip().lower()
        if raw not in {"true", "false", "1", "0", "yes", "no"}:
            raise CommandError("MTO_STAGE7B_ENABLE_DDQ_UI must be a boolean")
        enabled = raw in {"true", "1", "yes"}
        DBRSettings.objects.update_or_create(
            flag="IsDDQFromUI",
            defaults={
                "value": "1" if enabled else "0",
                "description": "0-DDQ is not from UI  1-DDQ is from UI",
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Stage 7B DDQ browser flow enabled: {enabled}"))
