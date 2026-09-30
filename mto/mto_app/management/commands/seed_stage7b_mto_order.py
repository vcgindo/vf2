"""Opt-in synthetic DDQ read fixture for isolated local Stage 7B acceptance."""

import os
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from mto_app.models import (
    CustomerMaster,
    DeptMaster,
    ItemMaster,
    ItemTypeMaster,
    OrderData,
    PlantMaster,
)


ITEM_TYPE_ID = 900001
PLANT_ID = 900001
DEPT_ID = 900001
ITEM_CODE = "STAGE7B-TEST-ITEM-001"
CUSTOMER_CODE = "STAGE7B-TEST-CUSTOMER-001"
ORDER_ID = "STAGE7B-TEST-ORDER-001"
ORDER_KEY = f"{ORDER_ID}/1"


def _fixture_only(model, **identity):
    if model.objects.exclude(**identity).exists():
        raise CommandError(f"Refusing to mix the synthetic DDQ fixture with existing {model.__name__} rows")


def _get_exact(model, identity, values):
    record, _ = model.objects.get_or_create(**identity, defaults=values)
    for field, expected in values.items():
        actual = getattr(record, field)
        if actual != expected:
            raise CommandError(f"Refusing to overwrite existing {model.__name__}.{field}")
    return record


class Command(BaseCommand):
    help = "Manually seed one unmistakably synthetic, unscheduled MTO DDQ test order."

    @transaction.atomic
    def handle(self, *args, **options):
        environment = os.environ.get("VECTORFLOW_RUNTIME_ENVIRONMENT", "").strip().lower()
        enabled = os.environ.get("MTO_STAGE7B_ENABLE_OPERATIONAL_FIXTURE", "").strip().lower()
        if environment not in {"local", "development", "test"} or enabled != "true":
            raise CommandError("Synthetic DDQ seed requires a non-production runtime and explicit fixture flag")

        _fixture_only(ItemTypeMaster, item_type_id=ITEM_TYPE_ID)
        _fixture_only(PlantMaster, plant_id=PLANT_ID)
        _fixture_only(DeptMaster, dept_id=DEPT_ID)
        _fixture_only(ItemMaster, item_code=ITEM_CODE)
        _fixture_only(CustomerMaster, cust_code=CUSTOMER_CODE)
        _fixture_only(OrderData, order_key=ORDER_KEY)

        item_type = _get_exact(
            ItemTypeMaster,
            {"item_type_id": ITEM_TYPE_ID},
            {"item_type": "Stage 7B Test Finished Good"},
        )
        plant = _get_exact(
            PlantMaster,
            {"plant_id": PLANT_ID},
            {"plant_code": "STAGE7B-TEST-PLANT", "plant_name": "Stage 7B Test Plant"},
        )
        dept = _get_exact(
            DeptMaster,
            {"dept_id": DEPT_ID},
            {"dept_code": "STAGE7B-TEST-DEPT", "dept_name": "Stage 7B Test Department"},
        )
        item = _get_exact(
            ItemMaster,
            {"item_code": ITEM_CODE},
            {"item_description": "Stage 7B Test Item", "item_type": item_type, "attributes": {}},
        )
        customer = _get_exact(
            CustomerMaster,
            {"cust_code": CUSTOMER_CODE},
            {"cust_name": "Stage 7B Test Customer", "attribute": {}},
        )
        _get_exact(
            OrderData,
            {"order_key": ORDER_KEY},
            {
                "order_id": ORDER_ID,
                "line_id": "1",
                "item": item,
                "plant": plant,
                "dept": dept,
                "customer": customer,
                "order_entry_date": date(2026, 1, 15),
                "vf_order_type": "MTO",
                "total_qty": Decimal("10.000"),
                "pending_qty": Decimal("10.000"),
                "due_date": None,
                "route": None,
                "ccr": None,
                "expected_due_date": None,
                "trailing_dept": None,
                "order_attributes": {},
                "line_order_attributes": {},
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Synthetic unscheduled DDQ order ready: {ORDER_KEY}"))
