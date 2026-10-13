"""Required exclusively owned PostgreSQL initialization proof; no day execution."""
import os
import json
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.db import connection, transaction, DatabaseError
from mta.serialization import storage
from mta.mdm.initialization import initialize, read_initialized_input
from mta.mdm.initialization_contract import decode
from mta.mdm.daily_source import require_binding
from mta.runtime.models import ProductionInitialization, MdmSource, CalculationRun
from mta.runtime.mdm_models import MdmSkuAttributes, MdmFamilySource
from mta.runtime import opening_storage
from tests.initialization_input_fixture import encoded


@unittest.skipUnless(os.environ.get('VF_INITIALIZATION_POSTGRES_PROOF') == '1',
    'Explicit exclusively owned PostgreSQL proof required')
class InitializationPostgresTest(unittest.TestCase):
    def setUp(self):
        if (connection.settings_dict['NAME'] != 'handoff3005_s2_20261013_001'
                or connection.settings_dict['HOST'] != 'handoff3005-s2-20261013-001-pg'):
            raise RuntimeError('This proof requires its exclusively owned S2 component PostgreSQL resource')
        self.atomic = transaction.atomic()
        self.atomic.__enter__()
        def cleanup():
            transaction.set_rollback(True)
            self.atomic.__exit__(None, None, None)
        self.addCleanup(cleanup)
        self.raw = Path('/proof/operator-input.json').read_bytes()
        self.value = json.loads(self.raw)
        encoded_raw, self.sha, self.args = encoded(self.value)
        self.assertEqual(encoded_raw, self.raw)

    def install(self):
        return initialize(self.raw, self.sha, **self.args)

    def test_complete_typed_values_nulls_duplicates_ordinals_and_native_binding(self):
        owner, created = self.install()
        self.assertTrue(created)
        expected = json.loads(Path('/proof/component-expected.json').read_text())
        self.assertEqual(storage(decode(self.raw, self.sha, **self.args)[1]), expected)
        self.assertEqual(storage(read_initialized_input(owner)), storage(expected))
        rows = list(MdmSkuAttributes.objects.filter(source=owner.source, owner='Importer')
            .order_by('ordinal').values('ordinal', 'SKUCode', 'Weight', 'Volume', 'ElephantOrderCapping'))
        self.assertEqual([row['ordinal'] for row in rows], [1, 2])
        self.assertEqual(rows[0]['SKUCode'], 'SUPPLIED-Z9')
        self.assertEqual(str(rows[0]['Weight']), '2.125')
        self.assertIsNone(rows[0]['Volume'])
        self.assertIsNone(rows[0]['ElephantOrderCapping'])
        self.assertEqual({key: value for key, value in rows[0].items() if key != 'ordinal'},
                         {key: value for key, value in rows[1].items() if key != 'ordinal'})
        self.assertEqual(owner.source.dll_digest, '')
        self.assertEqual(set(MdmFamilySource.objects.filter(source=owner.source).values_list('master_id', flat=True)), {2, 3})
        self.assertEqual(require_binding(owner.source, artifact_sha256=self.sha,
            artifact_schema='fresh-production-initialization-input-v1').pk, owner.source_id)
        self.assertEqual(CalculationRun.objects.count(), 0)

    def test_identical_retry_reverifies_original_identity_without_rows(self):
        first, _ = self.install()
        count = MdmSkuAttributes.objects.count()
        second, created = self.install()
        self.assertFalse(created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.source_id, second.source_id)
        self.assertEqual(first.receipt_digest, second.receipt_digest)
        self.assertEqual(MdmSkuAttributes.objects.count(), count)
        self.assertEqual(ProductionInitialization.objects.count(), 1)

    def test_changed_input_or_configuration_cannot_replace_instance(self):
        first, _ = self.install()
        self.value['configuration']['complete_daily']['remark_days'] += 1
        raw, sha, args = encoded(self.value)
        with self.assertRaises(ValueError):
            initialize(raw, sha, **args)
        first.refresh_from_db()
        self.assertEqual(first.input_sha256, self.sha)
        self.assertEqual(MdmSource.objects.count(), 1)
        self.assertEqual(CalculationRun.objects.count(), 0)

    def test_injected_terminal_readback_failure_rolls_back_all_typed_rows(self):
        with patch('mta.mdm.initialization.verify', side_effect=ValueError('injected terminal readback failure')):
            with self.assertRaisesRegex(ValueError, 'injected terminal'):
                self.install()
        self.assertEqual(MdmSource.objects.count(), 0)
        self.assertEqual(ProductionInitialization.objects.count(), 0)
        self.assertEqual(MdmSkuAttributes.objects.count(), 0)
        with connection.cursor() as cursor:
            cursor.execute('SELECT sum(n) FROM ('+' UNION ALL '.join(
                'SELECT count(*) AS n FROM '+opening_storage.table_sql(key)
                for key in opening_storage.STORAGE_TABLES)+') rows')
            self.assertEqual(cursor.fetchone()[0], 0)
        self.assertEqual(CalculationRun.objects.count(), 0)

    def test_seals_images_and_current_owners_deny_overwrite(self):
        owner, _ = self.install()
        image = next(item for item in owner.input_payload['images'].values() if item['count'])
        statements = [
            ('UPDATE mta.fresh_mta_productioninitialization SET input_sha256=%s WHERE id=%s', ['0'*64, owner.pk]),
            ('UPDATE mta.fresh_mta_mdmsource SET receipt=%s WHERE id=%s', ['{}', owner.source_id]),
            ('UPDATE '+opening_storage.table_sql(image['table'])+' SET vf_ordinal=vf_ordinal+1 WHERE vf_initialization_id=%s', [owner.pk]),
            ('DELETE FROM mta.fresh_mta_mdmskuattributes WHERE source_id=%s', [owner.source_id]),
            ('UPDATE mta.fresh_mta_mdmfamilysource SET digest=%s WHERE source_id=%s', ['0'*64, owner.source_id])]
        for query, values in statements:
            with self.subTest(query=query), self.assertRaises(DatabaseError), transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(query, values)
        self.assertEqual(read_initialized_input(owner)['opening']['identity'], 'SUPPLIED-OPENING-K8')

    def test_unknown_invalid_schema_populations_and_hashes_leave_no_rows(self):
        self.value['masters']['importer']['SkuAttributeData'][0]['Weight'] = '2.1251'
        raw, sha, args = encoded(self.value)
        with self.assertRaises(ValueError):
            initialize(raw, sha, **args)
        with self.assertRaises(ValueError):
            initialize(self.raw, '0'*64, **self.args)
        self.assertEqual(MdmSource.objects.count(), 0)
        self.assertEqual(ProductionInitialization.objects.count(), 0)
