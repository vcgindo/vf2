"""Empty produced Pick still means an exact empty INNER-join membership."""
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.core.management.base import CommandError

from mta.runtime.models import CalculationRun, Checkpoint, PickProjection
from mta.presentation import rrr_preparation as rrr
from mta.serialization import digest


class EmptyDailyPickTests(TestCase):
    def test_verified_empty_source_compiles_native_membership_and_missing_source_denies(self):
        run = CalculationRun.objects.create(kind='DAILY_CHAIN', status='RUNNING',
            business_date='2026-06-06', input_digest='i'*64, input_payload={},
            execution_revision='verified-empty-pick')
        from mta.presentation.pick_storage import write_pick_bands
        calculated = [dict(capability='r1_ration_bifurcation', rows=[])]
        write_pick_bands(run, calculated, provenance={'origin':'production-calculation'})
        Checkpoint.objects.create(run=run, name='CalculationOutputs', digest=digest(calculated),
                                  row_count=1, rows=calculated)
        run.status='SUCCEEDED'; run.save(update_fields=['status'])
        sql, params = rrr.bands_query(run)
        columns = {
            'R': ('SKUCode','WhCode','ParentWhCode','DispatchColorSequence','DispatchPen'),
            'S': ('SKUCode','WhCode'), 'B': ('SKUCode','LocCode'),
            'C': ('SKUCode',), 'D': ('WHCode',),
        }
        sources = {path: 'SELECT 0::bigint AS vf_ordinal,' + ','.join(
            "'x'::text AS " + '"'+field+'"' for field in columns[alias])
            for alias, path in rrr.SOURCES}
        with patch.object(rrr, 'image_query', side_effect=lambda run,path:(sources[path], [])), \
                connection.cursor() as cursor:
            rrr.validate_positions(cursor, run, sql, params)
            query, values = rrr.membership_query(run, sql, params)
            cursor.execute(query, values)
            self.assertEqual(cursor.fetchall(), [])
        with self.assertRaises(PickProjection.DoesNotExist):
            rrr.bands_query(CalculationRun(pk='00000000-0000-0000-0000-000000000001', kind='DAILY_CHAIN'))
        with patch('mta.presentation.pick_storage.read_pick_bands', return_value=[]), \
                self.assertRaisesRegex(ValueError, 'published Pick'):
            rrr.bands_query(SimpleNamespace(kind='LEGACY_UI_FIXTURE'))

    @override_settings(VF_GUIDED_PREPARED=False, VF_MTA_DAILY_PUBLICATION=True)
    def test_fixture_switch_denies_fixture_but_daily_reaches_existing_owner_guards(self):
        from mta.runtime.management.commands import prepare_guided_dbm_fixture as dbm
        from mta.runtime.management.commands import prepare_guided_chronic_fixture as chronic
        for module in (dbm, chronic):
            with self.assertRaisesRegex(CommandError, 'switch is disabled'):
                module.prepare()
            with patch.object(module, 'verify_guards', side_effect=ValueError('existing owner guards')), \
                    self.assertRaisesRegex(ValueError, 'existing owner guards'):
                module.prepare(run=SimpleNamespace(kind='DAILY_CHAIN'))
