"""Only the new target-fixture admission/immutability seam; no calculation runs."""
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from django.db import connection, transaction, DatabaseError
from mta.mdm import target_fixture as target
from mta.serialization import digest


class TargetAdmissionTests(unittest.TestCase):
    def test_original_owner_contract_does_not_enter_fixture_admission(self):
        with patch.object(target, 'require') as admission:
            self.assertFalse(target.require_family(None,
                SimpleNamespace(provenance={'schema': 'fresh-mdm-force-owner-v1'}), 'force'))
            admission.assert_not_called()

    def test_non_target_consumer_keeps_original_reader(self):
        with patch('mta.presentation.selective.image_rows', return_value=[{'x': None}]) as read:
            self.assertEqual(target.consumer_rows(SimpleNamespace(digest='other'), 'run', 'path'), [{'x': None}])
            read.assert_called_once_with('run', 'path')

    def test_family_cannot_use_another_fixture_receipt(self):
        with patch.object(target, 'require', return_value=SimpleNamespace(digest='owned', run_id='run')):
            with self.assertRaisesRegex(ValueError, 'family owner differs'):
                target.require_family(None, SimpleNamespace(
                    provenance={'schema': target.SCHEMA}, receipt_digest='wrong', last_run_id='run'), 'force')


@unittest.skipUnless(os.environ.get('VF_TARGET_FIXTURE_PG_PROOF') == '1', 'owned PostgreSQL proof only')
class TargetPostgresGuards(unittest.TestCase):
    def setUp(self):
        self.assertEqual(connection.settings_dict['HOST'], 'freshvcf-complete001-postgres')
        self.assertEqual(connection.settings_dict['NAME'], target.DATABASE)
        self.tx = transaction.atomic()
        self.tx.__enter__()
        self.addCleanup(self.rollback)
        from mta.runtime.models import CalculationRun
        from mta.runtime.mdm_models import MdmSource
        from mta.mdm.source import DLL
        self.source = MdmSource.objects.create(digest=target.SOURCE, dll_digest=DLL,
                                              database_name='isolated-guard-proof', receipt={})
        self.run = CalculationRun.objects.create(id=target.RUN, kind='LEGACY_UI_FIXTURE',
            business_date='2026-04-07', input_digest='target-fixture-guard',
            execution_revision='guard-only-no-calculation', input_payload={})
        with open('/evidence/target-mdm-package.json', encoding='utf-8') as stream:
            self.package = json.load(stream)
        self.assertEqual(digest(self.package), target.INPUT_DIGEST)

    def rollback(self):
        transaction.set_rollback(True)
        self.tx.__exit__(None, None, None)

    def guc(self):
        with connection.cursor() as c:
            c.execute("SELECT set_config('fresh.target_mdm_install',%s,true)", [str(self.source.pk)])

    def receipt(self):
        from mta.runtime.mdm_target_fixture_models import MdmTargetFixture
        p = dict(schema=target.SCHEMA, authority=target.AUTHORITY, input_digest=target.INPUT_DIGEST)
        return MdmTargetFixture.objects.create(source=self.source, run=self.run, receipt=p, digest=digest(p))

    def denied(self, action):
        with self.assertRaises(DatabaseError), transaction.atomic():
            action()

    def test_bootstrap_needs_capability_and_is_closed_by_receipt(self):
        from mta.runtime.mdm_target_fixture_models import MdmFixturePhaseOut
        fields = self.package['tables']['DBM/PhaseOutTbl'][0]
        self.denied(lambda: MdmFixturePhaseOut.objects.create(source=self.source, ordinal=1, **fields))
        self.guc()
        row = MdmFixturePhaseOut.objects.create(source=self.source, ordinal=1, **fields)
        self.receipt()
        self.guc()  # Replay the old bootstrap capability after finalization.
        self.denied(lambda: MdmFixturePhaseOut.objects.create(source=self.source, ordinal=2, **fields))
        self.denied(lambda: MdmFixturePhaseOut.objects.filter(pk=row.pk).update(NewNorm=999))
        self.denied(lambda: MdmFixturePhaseOut.objects.filter(pk=row.pk).delete())

    def test_season_bootstrap_cannot_reopen_or_change_calculated_fields(self):
        from mta.runtime.mdm_season_models import MdmSeasonCurrent
        fields = self.package['tables']['DBM/Seasonality'][0]
        self.denied(lambda: MdmSeasonCurrent.objects.create(source=self.source, ordinal=1, **fields))
        self.guc()
        row = MdmSeasonCurrent.objects.create(source=self.source, ordinal=1, **fields)
        self.receipt()
        self.guc()
        self.denied(lambda: MdmSeasonCurrent.objects.create(source=self.source, ordinal=2, **fields))
        self.denied(lambda: MdmSeasonCurrent.objects.filter(pk=row.pk).update(NewNorm=999, revision=1))
        self.denied(lambda: MdmSeasonCurrent.objects.filter(pk=row.pk).delete())

    def test_receipt_cannot_be_changed_deleted_or_replaced(self):
        self.guc()
        row = self.receipt()
        self.denied(lambda: type(row).objects.filter(pk=row.pk).update(digest='changed'))
        self.denied(lambda: type(row).objects.filter(pk=row.pk).delete())
        self.denied(self.receipt)

    def test_graph_pair_keeps_nulls_duplicates_and_date_tie_order(self):
        rows = [(i, 'Sku ' if i % 2 else 'SKU', 'Wh ',
                 None if i == 0 else '2026-04-07', None if i == 1 else i, 2)
                for i in range(183)]
        rows.append((184, 'OTHER', 'Wh', '2026-04-08', 999, 2))
        query = 'SELECT * FROM (VALUES ' + ','.join(
            ['(%s::int,%s::text,%s::text,%s::date,%s::int,%s::int)'] * len(rows)) + \
            ') v(vf_ordinal,"SKUCode","WhCode","ReportDate","Stock","GIT")'
        item = {'fields': [(n, n, kind) for n, kind in (
            ('SKUCode', 'str'), ('WhCode', 'str'), ('ReportDate', 'str'),
            ('Stock', 'int'), ('GIT', 'int'))]}
        with patch.object(target, 'require', return_value=SimpleNamespace(run_id=self.run.pk)), \
             patch('mta.presentation.selective.image_metadata', return_value=item), \
             patch('mta.presentation.selective.image_query',
                   return_value=(query, [v for row in rows for v in row])):
            actual = target.daily_pair_rows(self.source, self.run, 'sKu ', 'WH')
        self.assertEqual(len(actual), 180)
        self.assertEqual([r['Stock'] for r in actual], [None, *range(2, 181)])
        self.assertEqual({r['ReportDate'] for r in actual}, {'2026-04-07'})


if __name__ == '__main__':
    unittest.main()
