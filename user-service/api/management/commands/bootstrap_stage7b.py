import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import ApplicationMaster, Permission, User, UserserviceConfig
from api.management.commands.seed_users_and_roles import Command as RecoveredCatalogSeed


class Command(BaseCommand):
    help = "Idempotently bootstrap the environment-supplied Stage 7B test administrator."

    @transaction.atomic
    def handle(self, *args, **options):
        email = os.environ.get("VECTORFLOW_TEST_USERNAME", "").strip().lower()
        password = os.environ.get("VECTORFLOW_TEST_PASSWORD", "")
        display_name = os.environ.get("VECTORFLOW_TEST_DISPLAY_NAME", "Stage 7B Administrator").strip()
        if not email or not password:
            raise CommandError("VECTORFLOW_TEST_USERNAME and VECTORFLOW_TEST_PASSWORD are required")

        ApplicationMaster.objects.update_or_create(
            application_id=2, defaults={"application_name": "Distribution"}
        )
        ApplicationMaster.objects.update_or_create(
            application_id=3, defaults={"application_name": "Orders"}
        )

        legacy_mta_permission = Permission.objects.filter(
            code="MTA-PLANNING", url="/supply-chain-intelligence-hub/planning"
        ).first()
        if legacy_mta_permission is not None:
            if Permission.objects.filter(url="/mta/supply-chain-intelligence-hub/planning").exists():
                legacy_mta_permission.delete()
            else:
                legacy_mta_permission.url = "/mta/supply-chain-intelligence-hub/planning"
                legacy_mta_permission.save(update_fields=["url"])

        # The frontend navigation and landing catalogue are permission-driven.
        # Reuse the recovered application catalogue instead of maintaining a
        # Stage 7B-only subset that hides otherwise preserved MTA/MTO screens.
        recovered_catalog = RecoveredCatalogSeed()
        recovered_catalog.seed_permissions()
        recovered_catalog.seed_features()

        UserserviceConfig.objects.update_or_create(
            flag="Is_ADS_ACTIVE",
            defaults={"value": "false", "description": "Local Stage 7B authentication", "isvisible": False},
        )
        UserserviceConfig.objects.update_or_create(
            flag="IDLE_TIMEOUT",
            defaults={"value": "900000", "description": "Session idle timeout in milliseconds", "isvisible": False},
        )

        user = User.all_objects.filter(email__iexact=email).first()
        if user is None:
            user = User(email=email, name=display_name, tc=True)
        user.name = display_name
        user.tc = True
        user.is_active = True
        user.is_admin = True
        user.is_deleted = False
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Stage 7B administrator ready: {email}"))
