import os
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from api.models import (
    User,
    User_Application_Location_Permission,
    User_Application_Product_Permission,
)


class LocalDemoIdentitySeedTests(TestCase):
    @patch.dict(os.environ, {
        "VECTORFLOW_STAGE7B_LOCAL_SCOPE_FIXTURE": "true",
        "VECTORFLOW_RUNTIME_ENVIRONMENT": "test",
        "BASE_CLIENT_URL": "http://localhost:3004",
        "VECTORFLOW_TEST_PASSWORD": "test-local-demo-password",
        "VECTORFLOW_RESTRICTED_TEST_USERNAME": "demo.region@example.invalid",
    }, clear=False)
    def test_seed_is_idempotent_and_keeps_supplier_identity_name(self):
        call_command("seed_local_demo_identities", "--supplier-code", "PL001", "--supplier-code", "PL002")
        call_command("seed_local_demo_identities", "--supplier-code", "PL001", "--supplier-code", "PL002")

        restricted = User.all_objects.get(email="demo.region@example.invalid")
        self.assertEqual(restricted.name, "VectorFLOW Demo Restricted")
        self.assertEqual(
            list(User_Application_Product_Permission.objects.filter(user_id=restricted.id).values_list("productfilter_id", flat=True)),
            [2],
        )
        self.assertEqual(
            list(User_Application_Location_Permission.objects.filter(user_id=restricted.id).values_list("locationfilter_id", flat=True)),
            [2],
        )
        supplier = User.all_objects.get(name="PL001")
        self.assertTrue(supplier.check_password("test-local-demo-password"))
        self.assertFalse(User_Application_Product_Permission.objects.filter(user_id=supplier.id).exists())
        self.assertEqual(User.all_objects.filter(name__in=["PL001", "PL002", "DEMO_EMPTY_SUPPLIER"]).count(), 3)
