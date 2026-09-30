import os
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import (
    User,
    User_Application_Location_Permission,
    User_Application_Product_Permission,
)


class Command(BaseCommand):
    """Seed only the isolated demo principals required for MTA UI QA."""

    help = "Idempotently seed local restricted and supplier MTA demo identities."

    _local_urls = {
        "http://localhost:3000", "http://localhost:3001", "http://localhost:3003",
        "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3003",
        "http://localhost:3004", "http://127.0.0.1:3004",
    }
    _supplier_code = re.compile(r"^[A-Za-z0-9_-]{1,50}$")

    def add_arguments(self, parser):
        parser.add_argument("--supplier-code", action="append", default=[])

    def _assert_local_fixture(self):
        if (
            os.environ.get("VECTORFLOW_STAGE7B_LOCAL_SCOPE_FIXTURE", "").lower() != "true"
            or os.environ.get("VECTORFLOW_RUNTIME_ENVIRONMENT", "").lower() not in {"local", "development", "test"}
            or os.environ.get("BASE_CLIENT_URL", "").lower() not in self._local_urls
        ):
            raise CommandError("Demo identities require local runtime, local client URL, and explicit fixture flag")
        password = os.environ.get("VECTORFLOW_TEST_PASSWORD", "")
        if not password:
            raise CommandError("VECTORFLOW_TEST_PASSWORD is required for local demo identities")
        return password

    @staticmethod
    def _supplier_email(code: str) -> str:
        return f"supplier.{code.lower()}@example.invalid"

    def _ensure_user(self, *, email: str, name: str, password: str) -> User:
        email_match = User.all_objects.filter(email__iexact=email).first()
        name_match = User.all_objects.filter(name__iexact=name).first()
        if email_match is not None and name_match is not None and email_match.pk != name_match.pk:
            raise CommandError(f"Refusing to merge unrelated demo identity for {name}")
        user = email_match or name_match
        if user is not None and (user.email.casefold() != email.casefold() or user.name.casefold() != name.casefold()):
            raise CommandError(f"Refusing to repurpose unrelated user for demo identity {name}")
        if user is None:
            user = User(email=email, name=name, tc=True)
        user.email = email
        user.name = name
        user.tc = True
        # The preserved frontend derives navigation from administrator status.
        # MTA row scope remains explicit gateway-injected permission groups.
        user.is_admin = True
        user.is_active = True
        user.is_deleted = False
        user.set_password(password)
        user.save()
        return user

    @staticmethod
    def _set_scope(user: User, *, product_scope: int | None, location_scope: int | None):
        application_id = 2  # Distribution / MTA in the retained service map.
        User_Application_Product_Permission.objects.filter(user_id=user.id, application_id=application_id).delete()
        User_Application_Location_Permission.objects.filter(user_id=user.id, application_id=application_id).delete()
        if product_scope is not None:
            User_Application_Product_Permission.objects.create(
                user_id=user.id, application_id=application_id, productfilter_id=product_scope
            )
        if location_scope is not None:
            User_Application_Location_Permission.objects.create(
                user_id=user.id, application_id=application_id, locationfilter_id=location_scope
            )

    @transaction.atomic
    def handle(self, *args, **options):
        password = self._assert_local_fixture()
        supplier_codes = sorted(set(options["supplier_code"]))
        if not supplier_codes:
            raise CommandError("At least one --supplier-code is required")
        if any(not self._supplier_code.fullmatch(code) for code in supplier_codes):
            raise CommandError("Supplier codes must be 1-50 characters of A-Z, 0-9, _ or -")

        restricted_email = os.environ.get(
            "VECTORFLOW_RESTRICTED_TEST_USERNAME", "demo.region@example.invalid"
        ).strip().lower()
        restricted = self._ensure_user(
            email=restricted_email, name="VectorFLOW Demo Restricted", password=password
        )
        self._set_scope(restricted, product_scope=2, location_scope=2)

        empty = self._ensure_user(
            email="demo.empty.supplier@example.invalid", name="DEMO_EMPTY_SUPPLIER", password=password
        )
        self._set_scope(empty, product_scope=None, location_scope=None)

        for code in supplier_codes:
            supplier = self._ensure_user(
                email=self._supplier_email(code), name=code, password=password
            )
            self._set_scope(supplier, product_scope=None, location_scope=None)

        self.stdout.write(self.style.SUCCESS(
            f"Local demo identities ready: 1 restricted, 1 empty supplier, {len(supplier_codes)} supplier accounts."
        ))
