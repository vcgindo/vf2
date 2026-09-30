"""Opt-in, local-only POOGI assignment fixture for Stage 7B acceptance."""

import os
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from mto_app.management.commands.seed_stage7b_mto_order import (
    CUSTOMER_CODE,
    DEPT_ID,
    ITEM_CODE,
    ORDER_KEY as DDQ_ORDER_KEY,
    PLANT_ID,
    _get_exact,
)
from mto_app.models import (
    CustomerMaster,
    DeptMaster,
    ItemMaster,
    OrderData,
    PlantMaster,
    POOGIMajorReason,
    POOGIMinorReason,
)


ORDER_ID = "STAGE7B-TEST-POOGI-ORDER-001"
ORDER_KEY = f"{ORDER_ID}/1"
MAJOR_REASON_ID = 900001
MINOR_REASON_ID = 900001


class Command(BaseCommand):
    help = "Seed one synthetic Black delayed order and POOGI reason pair in isolated local Stage 7B data."

    @transaction.atomic
    def handle(self, *args, **options):
        environment = os.environ.get("VECTORFLOW_RUNTIME_ENVIRONMENT", "").strip().lower()
        enabled = os.environ.get("MTO_STAGE7B_ENABLE_OPERATIONAL_FIXTURE", "").strip().lower()
        if environment not in {"local", "development", "test"} or enabled != "true":
            raise CommandError("POOGI fixture requires a non-production runtime and explicit fixture flag")

        if OrderData.objects.exclude(order_key__in=[DDQ_ORDER_KEY, ORDER_KEY]).exists():
            raise CommandError("Refusing to seed POOGI into an order estate beyond the two Stage 7B fixtures")
        if not OrderData.objects.filter(order_key=DDQ_ORDER_KEY).exists():
            raise CommandError("Seed the guarded Stage 7B DDQ order first")
        if POOGIMajorReason.objects.exclude(major_reason_id=MAJOR_REASON_ID).exists():
            raise CommandError("Refusing to mix synthetic POOGI reasons with other major reasons")
        if POOGIMinorReason.objects.exclude(minor_reason_id=MINOR_REASON_ID).exists():
            raise CommandError("Refusing to mix synthetic POOGI reasons with other minor reasons")

        item = ItemMaster.objects.get(item_code=ITEM_CODE)
        plant = PlantMaster.objects.get(plant_id=PLANT_ID)
        dept = DeptMaster.objects.get(dept_id=DEPT_ID)
        customer = CustomerMaster.objects.get(cust_code=CUSTOMER_CODE)
        major = _get_exact(
            POOGIMajorReason,
            {"major_reason_id": MAJOR_REASON_ID},
            {"major_reason_code": "STAGE7B-TEST-MAJOR", "major_reason_desc": "Stage 7B Test Delay", "plant": plant, "is_valid": True},
        )
        _get_exact(
            POOGIMinorReason,
            {"minor_reason_id": MINOR_REASON_ID},
            {"minor_reason_code": "STAGE7B-TEST-MINOR", "minor_reason_desc": "Stage 7B Test Cause", "major_reason": major, "is_valid": True},
        )
        order_defaults = {
                "order_id": ORDER_ID,
                "line_id": "1",
                "item": item,
                "plant": plant,
                "dept": dept,
                "customer": customer,
                "order_entry_date": date(2026, 1, 15),
                "vf_order_type": "MTO",
                "total_qty": Decimal("8.000"),
                "pending_qty": Decimal("8.000"),
                "due_date": date(2026, 1, 31),
                "actual_released_date": date(2026, 1, 20),
                "planned_release_date": date(2026, 1, 18),
                "bpp": Decimal("88.00"),
                "color": "Black",
                "major_reason": None,
                "minor_reason": None,
                "order_attributes": {},
                "line_order_attributes": {},
                "computed_line_attributes": {},
        }
        order, created = OrderData.objects.get_or_create(order_key=ORDER_KEY, defaults=order_defaults)
        if not created:
            for field, expected in order_defaults.items():
                if field in {"major_reason", "minor_reason"}:
                    continue  # Preserve a reason assigned by the browser acceptance test.
                if getattr(order, field) != expected:
                    raise CommandError(f"Refusing to overwrite existing OrderData.{field}")
        self.stdout.write(self.style.SUCCESS(f"Synthetic POOGI delayed order ready: {ORDER_KEY}"))
