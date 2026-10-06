"""Registered ten-pair bootstrap and rollback on the owned PostgreSQL test DB."""
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase

from mta.mdm.daily_source_install import install, owners, registered
from mta.mdm.daily_source import require_binding
from mta.mdm.families import installed_ids
from mta.runtime.mdm_models import MdmSource, MdmSkuAttributes
from mta.runtime.mdm_skuloc_models import MdmSkuLocMasterPair
from mta.runtime.daily_request_models import DailyRequestOwner
from mta.runtime.ancillary_models import RemarkOwner

SHA='7ee7d940da3bab89ffeeddff94b4f2a7d9abace4aacdd589d698df6de85c24fc'


class DailySourceInstallTests(TestCase):
    def raw(self):
        return Path('/evidence/ten-pair-input-v1.json').read_bytes()

    def test_typed_registered_owners_bind_all_families_and_cannot_reset(self):
        raw=self.raw();source=install(raw,SHA)
        self.assertEqual(installed_ids(source),[1,2,3])
        require_binding(source,artifact_sha256=SHA,
                        artifact_schema=registered(raw,SHA)['schema'])
        self.assertEqual(MdmSkuLocMasterPair.objects.filter(source=source).count(),10)
        self.assertEqual(MdmSkuAttributes.objects.filter(source=source,owner='BTR').count(),0)
        self.assertEqual(DailyRequestOwner.objects.count(),1)
        self.assertEqual(RemarkOwner.objects.count(),1)
        with self.assertRaisesRegex(ValueError,'already exists'):
            install(raw,SHA)
        self.assertEqual(MdmSource.objects.count(),1)

    def test_late_source_failure_rolls_back_all_owners(self):
        with patch('mta.mdm.daily_input.install_pair_exclusions',side_effect=ValueError('injected source failure')), \
                self.assertRaisesRegex(ValueError,'injected source failure'):
            install(self.raw(),SHA)
        self.assertFalse(MdmSource.objects.exists())
        self.assertFalse(MdmSkuAttributes.objects.exists())
        self.assertFalse(DailyRequestOwner.objects.exists())
        self.assertFalse(RemarkOwner.objects.exists())

    def test_other_artifact_identity_rejected_before_install(self):
        with self.assertRaisesRegex(ValueError,'exact registered ten-pair'):
            install(self.raw(),'0f3084b7a6fb60b84edbd7c4dc01fef3c4b40f1a7c389ec82f88b9ad22519546')
        self.assertFalse(MdmSource.objects.exists())
