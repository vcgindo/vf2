"""Existing-opening completion must never adopt another database or replay a day.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import ExitStack
import os
import io
import json
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'onboarding-unit-only')
import django
django.setup()
from release.csv_onboarding import complete, check
from mta.mdm import production_families


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.initial = SimpleNamespace(pk='opening', source=SimpleNamespace(digest='source'),
                                       input_sha256='input')
        self.receipt = dict(initialization=dict(opening_id='opening', source_digest='source',
                                               input_sha256='input'),
                            registration=dict(database='db', database_oid=123, namespace='ns'))
        def mock(name, **kw):
            return self.stack.enter_context(patch(name, **kw))
        mock('release.native_identity.require_current')
        mock('mta.runtime.models.ProductionInitialization.objects.count', return_value=1)
        mock('mta.runtime.models.ProductionInitialization.objects.select_related').return_value.get.return_value = self.initial
        cursor = MagicMock()
        cursor.__enter__.return_value.fetchone.return_value = ('db', 123)
        mock('django.db.connection.cursor', return_value=cursor)
        mock('mta.mdm.owned_namespace._registered_identity')
        mock('mta.mdm.owned_namespace._receipt_identity', return_value={'registration_id': 'ns'})
        self.runs = mock('mta.runtime.models.CalculationRun.objects.exists', return_value=False)
        self.captures = mock('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.exists', return_value=False)
        self.bootstrap = mock('mta.mdm.production_families.bootstrap_native_families')
        self.families = mock('mta.mdm.families.installed_ids', return_value=list(range(1, 14)))

    def test_matching_opening_completes_existing_families(self):
        self.assertEqual(complete(self.receipt)['status'], 'MDM_FAMILIES_READY')
        self.bootstrap.assert_called_once_with(self.initial)

    def test_inspection_never_bootstraps(self):
        self.assertEqual(complete(self.receipt, inspect=True)['status'], 'OPENING_RECONCILED')
        self.bootstrap.assert_not_called()

    def test_wrong_opening_and_reused_database_oid_cannot_adopt_receipt(self):
        for section, key in (('initialization', 'opening_id'), ('initialization', 'source_digest'),
                             ('initialization', 'input_sha256'), ('registration', 'database_oid'),
                             ('registration', 'namespace'), ('registration', 'database')):
            with self.subTest(key=key):
                old = self.receipt[section][key]
                self.receipt[section][key] = 'different'
                with self.assertRaises(ValueError):
                    complete(self.receipt)
                self.receipt[section][key] = old
        self.bootstrap.assert_not_called()

    def test_started_day_and_capture_block_onboarding(self):
        for model in (self.runs, self.captures):
            model.return_value = True
            with self.assertRaisesRegex(ValueError, 'Daily work already'):
                complete(self.receipt)
            model.return_value = False
        self.bootstrap.assert_not_called()

    def test_partial_families_cannot_claim_success(self):
        self.families.return_value = [1, 2, 3]
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            complete(self.receipt)

    def test_changed_pack_is_rejected_before_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ('binding-template.json', 'permissions.json'):
                (Path(directory)/name).write_text('{}')
            self.receipt['pack_pins'] = {'binding-template.json':'wrong','permissions.json':'wrong'}
            with self.assertRaisesRegex(ValueError, 'binding/access files changed'):
                complete(self.receipt, input_directory=directory)
        self.bootstrap.assert_not_called()

    def test_serving_probe_requires_auth_guard_not_publication_failure(self):
        with patch('mta.presentation.installation_metadata.require_installation', return_value=self.initial.source), \
                patch('urllib.request.urlopen') as request:
            request.side_effect = lambda *a, **kw: (_ for _ in ()).throw(HTTPError(
                'http://localhost',403,'Forbidden',{},io.BytesIO(b'{"error":"gateway_identity_required"}')))
            self.assertTrue(check()['gateway_identity_required'])
            request.side_effect = HTTPError('http://localhost',503,'Unavailable',{},
                                            io.BytesIO(b'{"error":"publication_not_admitted"}'))
            with self.assertRaises(HTTPError):
                check()
