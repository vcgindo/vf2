"""Complete the local synthetic delayed order's route and buffer read estate."""

import os
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from mto_app.management.commands.seed_stage7b_enquiry_response import (
    CCR_ID,
    PROCUREMENT_BUFFER_ID,
    PRODUCTION_BUFFER_ID,
)
from mto_app.management.commands.seed_stage7b_mto_order import ORDER_KEY as DDQ_ORDER_KEY, _get_exact
from mto_app.management.commands.seed_stage7b_poogi_reason import ORDER_KEY as POOGI_ORDER_KEY
from mto_app.models import (
    BufferMaster,
    CCRMaster,
    LineCCRDetails,
    OrderBufferMapping,
    OrderData,
    RouteMaster,
)


ROUTE_ID = 900001


class Command(BaseCommand):
    help = "Link only the labelled local POOGI order to a synthetic route, CCR and production/procurement buffers."

    @transaction.atomic
    def handle(self, *args, **options):
        environment = os.environ.get("VECTORFLOW_RUNTIME_ENVIRONMENT", "").strip().lower()
        enabled = os.environ.get("MTO_STAGE7B_ENABLE_OPERATIONAL_FIXTURE", "").strip().lower()
        if environment not in {"local", "development", "test"} or enabled != "true":
            raise CommandError("Order Rescheduling fixture requires a non-production runtime and explicit fixture flag")
        if OrderData.objects.exclude(order_key__in=[DDQ_ORDER_KEY, POOGI_ORDER_KEY]).exists():
            raise CommandError("Refusing to seed into an order estate beyond the two Stage 7B fixtures")
        if RouteMaster.objects.exclude(route_id=ROUTE_ID).exists():
            raise CommandError("Refusing to mix synthetic route with other routes")
        if OrderBufferMapping.objects.exclude(order_id=POOGI_ORDER_KEY, buffer_id__in=[PRODUCTION_BUFFER_ID, PROCUREMENT_BUFFER_ID]).exists():
            raise CommandError("Refusing to mix synthetic order buffers with other order buffers")
        if LineCCRDetails.objects.exclude(order_id=POOGI_ORDER_KEY, ccr_id=CCR_ID).exists():
            raise CommandError("Refusing to mix synthetic line CCR with other line CCR details")

        try:
            order = OrderData.objects.select_for_update().get(order_key=POOGI_ORDER_KEY)
            ccr = CCRMaster.objects.get(ccr_id=CCR_ID)
            production_buffer = BufferMaster.objects.get(buffer_id=PRODUCTION_BUFFER_ID)
            procurement_buffer = BufferMaster.objects.get(buffer_id=PROCUREMENT_BUFFER_ID)
        except (OrderData.DoesNotExist, CCRMaster.DoesNotExist, BufferMaster.DoesNotExist) as error:
            raise CommandError("Seed the guarded POOGI order and Enquiry Response references first") from error
        if (order.order_id != "STAGE7B-TEST-POOGI-ORDER-001" or order.color != "Black"
                or order.due_date != date(2026, 1, 31) or order.is_rm_released):
            raise CommandError("Refusing to modify a non-matching scheduled-order fixture")

        route = _get_exact(
            RouteMaster,
            {"route_id": ROUTE_ID},
            {"route_code": "STAGE7B-TEST-ROUTE", "route_name": "Stage 7B Test Route"},
        )
        if order.route_id not in {None, route.pk} or order.ccr_id not in {None, ccr.pk}:
            raise CommandError("Refusing to overwrite existing order route or CCR")
        if order.route_id is None or order.ccr_id is None:
            order.route = route
            order.ccr = ccr
            order.save(update_fields=["route", "ccr"])
        for buffer in (production_buffer, procurement_buffer):
            _get_exact(OrderBufferMapping, {"order": order, "buffer": buffer}, {"buffer_date": None})
        _get_exact(
            LineCCRDetails,
            {"order": order, "ccr": ccr},
            {"route": route, "pending_ccr_qty": Decimal("8.00"), "order_load": Decimal("80.00")},
        )
        self.stdout.write(self.style.SUCCESS(f"Synthetic Order Rescheduling read estate ready: {POOGI_ORDER_KEY}"))
