"""Opt-in local-only reference fixture for the preserved MTO Enquiry Response read."""

import os
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from mto_app.management.commands.seed_stage7b_mto_order import (
    DEPT_ID,
    ITEM_TYPE_ID,
    PLANT_ID,
    _get_exact,
)
from mto_app.models import (
    BufferItemTypeMapping,
    BufferMaster,
    BufferTypeMaster,
    CCRGroupMaster,
    CCRItemTypeMapping,
    CCRMaster,
    DeptMaster,
    FOL_Data,
    ItemTypeMaster,
    PlantMaster,
)


CCR_ID = 900001
CCR_GROUP_ID = 900001
PRODUCTION_BUFFER_ID = 900001
PROCUREMENT_BUFFER_ID = 900002


class Command(BaseCommand):
    help = "Seed one synthetic CCR, item-type buffer mapping and FOL for local Enquiry Response acceptance."

    @transaction.atomic
    def handle(self, *args, **options):
        environment = os.environ.get("VECTORFLOW_RUNTIME_ENVIRONMENT", "").strip().lower()
        enabled = os.environ.get("MTO_STAGE7B_ENABLE_OPERATIONAL_FIXTURE", "").strip().lower()
        if environment not in {"local", "development", "test"} or enabled != "true":
            raise CommandError("Enquiry Response fixture requires a non-production runtime and explicit fixture flag")

        allowed = (
            (CCRGroupMaster, {"ccr_group_id": CCR_GROUP_ID}),
            (CCRMaster, {"ccr_id": CCR_ID}),
            (BufferTypeMaster, {"buffer_type_id__in": [PRODUCTION_BUFFER_ID, PROCUREMENT_BUFFER_ID]}),
            (BufferMaster, {"buffer_id__in": [PRODUCTION_BUFFER_ID, PROCUREMENT_BUFFER_ID]}),
            (CCRItemTypeMapping, {"ccr_id": CCR_ID, "item_type_id": ITEM_TYPE_ID}),
            (BufferItemTypeMapping, {"item_type_id": ITEM_TYPE_ID, "buffer_id__in": [PRODUCTION_BUFFER_ID, PROCUREMENT_BUFFER_ID]}),
            (FOL_Data, {"ccr_id": CCR_ID}),
        )
        for model, identity in allowed:
            if model.objects.exclude(**identity).exists():
                raise CommandError(f"Refusing to mix synthetic Enquiry Response data with other {model.__name__} rows")

        try:
            plant = PlantMaster.objects.get(plant_id=PLANT_ID)
            dept = DeptMaster.objects.get(dept_id=DEPT_ID)
            item_type = ItemTypeMaster.objects.get(item_type_id=ITEM_TYPE_ID)
        except (PlantMaster.DoesNotExist, DeptMaster.DoesNotExist, ItemTypeMaster.DoesNotExist) as error:
            raise CommandError("Seed the guarded Stage 7B DDQ master fixture first") from error

        group = _get_exact(
            CCRGroupMaster,
            {"ccr_group_id": CCR_GROUP_ID},
            {"ccr_group_code": "STAGE7B-TEST-CCR-GROUP", "ccr_group_name": "Stage 7B Test CCR Group", "is_valid": True},
        )
        ccr = _get_exact(
            CCRMaster,
            {"ccr_id": CCR_ID},
            {
                "ccr_code": "STAGE7B-TEST-CCR",
                "ccr_name": "Stage 7B Test CCR",
                "capacity_per_day": Decimal("100.00"),
                "working_hours_per_day": Decimal("8.00"),
                "schedule_horizon": 30,
                "fol_horizon": 30,
                "residual_buffer": Decimal("0.00"),
                "ccr_group": group,
                "plant": plant,
                "dept": dept,
                "is_valid": True,
            },
        )
        _get_exact(CCRItemTypeMapping, {"ccr": ccr, "item_type": item_type}, {"touch_time_in_mins": Decimal("10.00"), "batch_size": Decimal("1.00000")})

        for buffer_id, buffer_type_name, buffer_size in (
            (PRODUCTION_BUFFER_ID, "Production", 5),
            (PROCUREMENT_BUFFER_ID, "Procurement", 3),
        ):
            buffer_type = _get_exact(
                BufferTypeMaster,
                {"buffer_type_id": buffer_id},
                {"buffer_type": buffer_type_name, "buffer_type_desc": f"Stage 7B Test {buffer_type_name}", "is_valid": True},
            )
            buffer = _get_exact(
                BufferMaster,
                {"buffer_id": buffer_id},
                {
                    "buffer_code": f"STAGE7B-TEST-{buffer_type_name.upper()}",
                    "buffer_desc": f"Stage 7B Test {buffer_type_name} Buffer",
                    "buffer_size": buffer_size,
                    "slt": 0,
                    "mlt": 0,
                    "is_blue": False,
                    "buffer_type": buffer_type,
                    "is_valid": True,
                },
            )
            _get_exact(BufferItemTypeMapping, {"item_type": item_type, "buffer": buffer}, {})

        _get_exact(
            FOL_Data,
            {"ccr": ccr},
            {
                "fol_end_date": date(2026, 12, 31),
                "occupied_qty_in_units": 0,
                "occupied_qty_in_mins": 0,
                "fol_in_days": Decimal("6.00"),
                "stpl_in_days": Decimal("4.00"),
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Synthetic Enquiry Response CCR ready: {CCR_ID}"))
