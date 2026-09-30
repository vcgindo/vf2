import os
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIRequestFactory

from mto_app.common.commonfunctions import fetch_leaf_nodes_with_plant
from mto_app.management.commands.seed_stage7b_mto_order import ORDER_KEY
from mto_app.management.commands.seed_stage7b_enquiry_response import CCR_ID
from mto_app.management.commands.seed_stage7b_order_rescheduling import ROUTE_ID
from mto_app.management.commands.seed_stage7b_poogi_reason import (
    MAJOR_REASON_ID,
    MINOR_REASON_ID,
    ORDER_KEY as POOGI_ORDER_KEY,
)
from mto_app.models import CCRGroupMaster, DBRSettings, DDQChangesLog, ItemTypeMaster, OrderData, RouteMaster
from poogi.PoogiReasonsForDelayedOrders.views import (
    AssignPoogiReasonForOrdersView,
    GetDelayedOrdersForPoogiReasonAssignmentView,
    GetPoogiReasonsForDelayedOrdersAnalyticsDataView,
    PoogiMajorMinorReasonMasterView,
)
from procurement.MaterialCoverageForOpenSo.views import GetOpenSOSummaryDataView
from production.DDQ.views import GetOrdersForDDQView
from production.EnquiryResponse.views import EnquiryResponseView
from production.OrderRescheduling.views import GetOrderReschedulingDataView, UpdateOrderDueDateView


class EmptyEstatePortabilityTests(TestCase):
    def setUp(self):
        DBRSettings.objects.create(
            flag="IsDataPermissionEnabled", value="False"
        )

    def test_leaf_node_projection_has_stable_empty_schema(self):
        result = fetch_leaf_nodes_with_plant()

        self.assertTrue(result.empty)
        self.assertEqual(
            list(result.columns), ["component_item_code", "plant_code"]
        )

    def test_material_coverage_summary_returns_zero_shape_on_clean_estate(self):
        request = APIRequestFactory().put(
            "/api/mto/getOpenSOSummaryData/",
            {"product_permissions": [], "location_permissions": [], "user": {}},
            format="json",
        )

        response = GetOpenSOSummaryDataView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["msg"], "All records fetched successfully")
        self.assertEqual(len(response.data["data"]), 12)
        self.assertEqual(
            set(response.data["data"][0]),
            {"col", "kit", "ordcnt", "custcnt", "ordval", "bkt", "S", "E"},
        )


class Stage7BMtoOrderFixtureTests(TestCase):
    def setUp(self):
        DBRSettings.objects.create(flag="IsDataPermissionEnabled", value="0")

    def seed(self, environment="local", enabled="true"):
        with patch.dict(os.environ, {
            "VECTORFLOW_RUNTIME_ENVIRONMENT": environment,
            "MTO_STAGE7B_ENABLE_OPERATIONAL_FIXTURE": enabled,
        }):
            call_command("seed_stage7b_mto_order", stdout=StringIO())

    def test_clean_database_and_unflagged_command_stay_empty(self):
        self.assertEqual(OrderData.objects.count(), 0)
        with self.assertRaises(CommandError):
            self.seed(enabled="false")
        self.assertEqual(OrderData.objects.count(), 0)

    def test_production_rejects_fixture_even_when_flagged(self):
        with self.assertRaises(CommandError):
            self.seed(environment="production")
        self.assertEqual(OrderData.objects.count(), 0)

    def test_command_is_idempotent_for_exact_fixture_values(self):
        self.seed()
        self.seed()
        self.assertEqual(OrderData.objects.count(), 1)
        self.assertEqual(OrderData.objects.get().order_key, ORDER_KEY)

    def test_fixture_produces_preserved_ddq_row_and_analytics(self):
        self.seed()
        request = APIRequestFactory().put(
            "/getOrdersForDDQ/?page=1&unSch=1&page_size=15",
            {"product_permissions": [], "location_permissions": [], "user": {"is_admin": True}},
            format="json",
        )
        response = GetOrdersForDDQView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["count"], 1)
        row = response.data["data"]["results"][0]
        self.assertEqual(row["ok"], ORDER_KEY)
        self.assertEqual(row["oid"], "STAGE7B-TEST-ORDER-001")
        self.assertIsNone(row["dd"])
        self.assertIsNone(row["rid"])

        analytics = GetOrdersForDDQView.as_view()(
            APIRequestFactory().put("/getOrdersForDDQ/?analytics=1", {}, format="json")
        )
        self.assertEqual(analytics.status_code, 200)
        self.assertEqual(analytics.data["data"], {
            "pcb": 1, "pdb": 1, "ccr": 1, "us": 1, "sc": 0, "ttl": 1,
        })

    def test_ddq_only_order_does_not_invent_ccr_or_scheduled_order(self):
        self.seed()

        enquiry = EnquiryResponseView.as_view()(
            APIRequestFactory().get("/getEnquiryResponseData/")
        )
        self.assertEqual(enquiry.status_code, 200)
        self.assertEqual(enquiry.data["data"], [])

        rescheduling = GetOrderReschedulingDataView.as_view()(
            APIRequestFactory().put(
                "/GetOrderReschedulingData/?page=1&page_size=15",
                {},
                format="json",
            )
        )
        self.assertEqual(rescheduling.status_code, 200)
        self.assertEqual(rescheduling.data["data"]["count"], 0)

    def test_existing_non_fixture_master_prevents_any_fixture_write(self):
        ItemTypeMaster.objects.create(item_type_id=2, item_type="Existing")
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(OrderData.objects.count(), 0)
        self.assertEqual(ItemTypeMaster.objects.count(), 1)


class Stage7BPoogiFixtureTests(TestCase):
    def seed(self, environment="local", enabled="true"):
        with patch.dict(os.environ, {
            "VECTORFLOW_RUNTIME_ENVIRONMENT": environment,
            "MTO_STAGE7B_ENABLE_OPERATIONAL_FIXTURE": enabled,
        }):
            call_command("seed_stage7b_poogi_reason", stdout=StringIO())

    def setUp(self):
        DBRSettings.objects.create(flag="IsDataPermissionEnabled", value="0")
        with patch.dict(os.environ, {
            "VECTORFLOW_RUNTIME_ENVIRONMENT": "test",
            "MTO_STAGE7B_ENABLE_OPERATIONAL_FIXTURE": "true",
        }):
            call_command("seed_stage7b_mto_order", stdout=StringIO())

    def test_guard_and_idempotence(self):
        with self.assertRaises(CommandError):
            self.seed(enabled="false")
        with self.assertRaises(CommandError):
            self.seed(environment="production")
        self.seed()
        self.seed()
        self.assertEqual(OrderData.objects.count(), 2)
        self.assertEqual(OrderData.objects.get(order_key=POOGI_ORDER_KEY).color, "Black")

    def test_delayed_order_master_analytics_and_reason_assignment(self):
        self.seed()
        factory = APIRequestFactory()
        listing = GetDelayedOrdersForPoogiReasonAssignmentView.as_view()(
            factory.put(
                "/getPoogiReasonForDealyedOrdersData/?isAssigned=0&page=1&page_size=15",
                {"product_permissions": [], "location_permissions": [], "user": {"is_admin": True}},
                format="json",
            )
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["data"]["count"], 1)
        self.assertEqual(listing.data["data"]["results"][0]["ok"], POOGI_ORDER_KEY)

        master = PoogiMajorMinorReasonMasterView.as_view()(factory.get("/getPoogiReasonMasterData/"))
        self.assertEqual(master.status_code, 200)
        self.assertEqual(master.data["data"][900001][900001]["min"][0]["minid"], MINOR_REASON_ID)

        assigned = AssignPoogiReasonForOrdersView.as_view()(
            factory.put(
                "/updatePoogiReasonsforOrders/",
                {"data": [{"ok": POOGI_ORDER_KEY, "majid": MAJOR_REASON_ID, "minid": MINOR_REASON_ID}]},
                format="json",
            )
        )
        self.assertEqual(assigned.status_code, 200)
        order = OrderData.objects.get(order_key=POOGI_ORDER_KEY)
        self.assertEqual(order.major_reason_id, MAJOR_REASON_ID)
        self.assertEqual(order.minor_reason_id, MINOR_REASON_ID)

        analytics = GetPoogiReasonsForDelayedOrdersAnalyticsDataView.as_view()(
            factory.get("/getPoogiReasonForDelayedOrdersAnalyticsData/")
        )
        self.assertEqual(analytics.status_code, 200)
        self.assertEqual(analytics.data["data"]["open"]["assigned"], 1)
        self.assertEqual(analytics.data["data"]["open"]["unassigned"], 1)

        unassigned = GetDelayedOrdersForPoogiReasonAssignmentView.as_view()(
            factory.put(
                "/getPoogiReasonForDealyedOrdersData/?isAssigned=0&page=1&page_size=15",
                {"product_permissions": [], "location_permissions": [], "user": {"is_admin": True}},
                format="json",
            )
        )
        self.assertEqual(unassigned.data["data"]["count"], 0)
        self.seed()  # Running the fixture again must not erase the assigned reason.
        order.refresh_from_db()
        self.assertEqual(order.major_reason_id, MAJOR_REASON_ID)


class Stage7BEnquiryResponseFixtureTests(TestCase):
    def setUp(self):
        DBRSettings.objects.create(flag="IsDataPermissionEnabled", value="0")
        with patch.dict(os.environ, {
            "VECTORFLOW_RUNTIME_ENVIRONMENT": "test",
            "MTO_STAGE7B_ENABLE_OPERATIONAL_FIXTURE": "true",
        }):
            call_command("seed_stage7b_mto_order", stdout=StringIO())

    def seed(self, environment="test", enabled="true"):
        with patch.dict(os.environ, {
            "VECTORFLOW_RUNTIME_ENVIRONMENT": environment,
            "MTO_STAGE7B_ENABLE_OPERATIONAL_FIXTURE": enabled,
        }):
            call_command("seed_stage7b_enquiry_response", stdout=StringIO())

    def test_nonproduction_guard_and_repeat_are_exact(self):
        with self.assertRaises(CommandError):
            self.seed(enabled="false")
        with self.assertRaises(CommandError):
            self.seed(environment="production")
        self.seed()
        self.seed()
        self.assertEqual(CCRGroupMaster.objects.count(), 1)

    def test_preserved_enquiry_response_returns_one_ccr_with_buffer_and_fol(self):
        self.seed()
        view = EnquiryResponseView.as_view()
        result = view(APIRequestFactory().get("/getEnquiryResponseData/?plant=900001"))
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.data["data"]), 1)
        row = result.data["data"][0]
        self.assertEqual(row["cid"], CCR_ID)
        self.assertEqual(row["plnm"], "Stage 7B Test Plant")
        self.assertEqual(row["fol"], 6)
        self.assertEqual(row["it"]["Stage 7B Test Finished Good"], {
            "id": 900001, "proc_size": 3, "prod_size": 5,
        })
        no_match = view(APIRequestFactory().get("/getEnquiryResponseData/?plant=1"))
        self.assertEqual(no_match.status_code, 200)
        self.assertEqual(no_match.data["data"], [])

    def test_existing_customer_ccr_group_blocks_fixture(self):
        CCRGroupMaster.objects.create(ccr_group_id=1, ccr_group_code="CUSTOMER", ccr_group_name="Customer")
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(CCRGroupMaster.objects.count(), 1)


class Stage7BOrderReschedulingFixtureTests(TransactionTestCase):
    def setUp(self):
        DBRSettings.objects.create(flag="IsDataPermissionEnabled", value="0")
        with patch.dict(os.environ, {
            "VECTORFLOW_RUNTIME_ENVIRONMENT": "test",
            "MTO_STAGE7B_ENABLE_OPERATIONAL_FIXTURE": "true",
        }):
            for command in (
                "seed_stage7b_mto_order",
                "seed_stage7b_poogi_reason",
                "seed_stage7b_enquiry_response",
            ):
                call_command(command, stdout=StringIO())

    def seed(self, environment="test", enabled="true"):
        with patch.dict(os.environ, {
            "VECTORFLOW_RUNTIME_ENVIRONMENT": environment,
            "MTO_STAGE7B_ENABLE_OPERATIONAL_FIXTURE": enabled,
        }):
            call_command("seed_stage7b_order_rescheduling", stdout=StringIO())

    def test_guard_and_repeat_are_exact(self):
        with self.assertRaises(CommandError):
            self.seed(enabled="false")
        with self.assertRaises(CommandError):
            self.seed(environment="production")
        self.seed()
        self.seed()
        self.assertEqual(RouteMaster.objects.count(), 1)
        order = OrderData.objects.get(order_key=POOGI_ORDER_KEY)
        self.assertEqual(order.route_id, ROUTE_ID)
        self.assertEqual(order.ccr_id, CCR_ID)

    def test_preserved_order_rescheduling_read_has_route_and_both_buffers(self):
        self.seed()
        request = APIRequestFactory().put(
            "/GetOrderReschedulingData/?page=1&page_size=15", {}, format="json"
        )
        response = GetOrderReschedulingDataView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"], [{
            "oid": "STAGE7B-TEST-POOGI-ORDER-001",
            "lid": "1",
            "dd": date(2026, 1, 31),
            "rnm": "Stage 7B Test Route",
            "odk": POOGI_ORDER_KEY,
            "PdSz": 5,
            "PcSz": 3,
        }])

    def test_existing_route_blocks_fixture_without_modifying_order(self):
        RouteMaster.objects.create(route_id=1, route_code="CUSTOMER", route_name="Customer")
        with self.assertRaises(CommandError):
            self.seed()
        self.assertEqual(RouteMaster.objects.count(), 1)
        self.assertIsNone(OrderData.objects.get(order_key=POOGI_ORDER_KEY).route_id)

    def test_missing_calendar_rejects_update_without_changing_due_date(self):
        self.seed()
        original = OrderData.objects.get(order_key=POOGI_ORDER_KEY)
        response = UpdateOrderDueDateView.as_view()(
            APIRequestFactory().put(
                "/UpdateOrderDueDate/",
                {"data": [{
                    "unm": "Stage 7B Test",
                    "isUnSch": 0,
                    "ordData": [{"ok": POOGI_ORDER_KEY, "dd": "2026-12-15", "r": "Stage 7B negative calendar probe"}],
                }]},
                format="json",
            )
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("FOl update data failed", str(response.data))
        original.refresh_from_db()
        self.assertEqual(original.due_date, date(2026, 1, 31))
        self.assertEqual(DDQChangesLog.objects.count(), 0)
