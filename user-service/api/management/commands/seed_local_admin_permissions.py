import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import (
    User,
    User_Application_Location_Permission,
    User_Application_Product_Permission,
)


class Command(BaseCommand):
    help = "Opt-in local-only assignment of synthetic Stage 7B MTA scopes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            required=True,
            help="Configured Stage 7B test administrator email address.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        configured_email = os.environ.get("VECTORFLOW_TEST_USERNAME", "").strip().lower()
        if (os.environ.get("VECTORFLOW_STAGE7B_LOCAL_SCOPE_FIXTURE", "").lower() != "true"
                or os.environ.get("VECTORFLOW_RUNTIME_ENVIRONMENT", "").lower() not in {
                    "local", "development", "test"
                }
                or os.environ.get("BASE_CLIENT_URL", "").lower() not in {
                    "http://localhost:3000", "http://localhost:3001", "http://localhost:3003",
                    "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3003",
                    "http://localhost:3004", "http://127.0.0.1:3004",
                    "http://localhost:3005", "http://127.0.0.1:3005",
                }
                or not configured_email or options["email"].strip().lower() != configured_email):
            raise CommandError("Synthetic assignment requires local client URL, explicit fixture flag, and exact test administrator")
        user = User.objects.get(email__iexact=options["email"])
        if not user.is_active or not user.is_admin or user.is_deleted:
            raise CommandError("Configured local test user must be an active administrator")
        application_id = 2  # Distribution / MTA in the retained service map.

        User_Application_Product_Permission.objects.update_or_create(
            user_id=user.id,
            application_id=application_id,
            productfilter_id=1,
        )
        User_Application_Location_Permission.objects.update_or_create(
            user_id=user.id,
            application_id=application_id,
            locationfilter_id=1,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Granted MTA local full-access product/location group 1 to user {user.id}."
            )
        )
