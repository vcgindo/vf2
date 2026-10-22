"""Actual PostgreSQL post-DBM contract proof; no large business replay.

The retained small native test gains the three actual April8 capture policies.
An explicit transport-only savepoint uses10001 force/history occurrences and
rolls back before the unchanged small native calculation output is committed.
Post-DBM reloads additionally use actual disk-spooled SQL rows at small counts.
"""
import hashlib, json, os, unittest, zipfile
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('VF_POST_DBM_PERSISTENCE_PROOF')=='1', 'Explicit owned post-DBM SQL proof required')
class PostDbmPersistencePostgres(unittest.TestCase):
    proof_database='vf_btr_terminal_admission_20261022'

    def test_native_policy_readbacks_threshold_transport_rollback_and_report_rebuild(self):
        from django.db import connection, transaction, DatabaseError
        from tests import section9_native_fixture as fixture
        from tests import test_section11_native_day_postgres as native
        from tests.test_operational_bor import bor_row, rrr_row
        from mta.application.operational_capture import CAPTURE_POLICY
        from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY
        from mta.application.timeline_controls import FORCE_CAPTURE_POLICY
        from mta.application import operational_bor
        from mta.runtime import temporal, relational_state as typed, operational_force_source as force
        from mta.runtime import operational_input_source, production_report_storage
        from mta.presentation import daily_sources, daily_transit, operational_reports
        from mta.row_sequences import RecordRows
        from mta.serialization import digest, storage

        self.assertEqual(connection.settings_dict['NAME'],self.proof_database)
        archive=fixture.source_archive
        policies=dict(operational_sources=CAPTURE_POLICY,operational_input_sources=INPUT_CAPTURE_POLICY,
                      operational_force_sources=FORCE_CAPTURE_POLICY)
        def source_archive(original,destination):
            base=archive(original,Path(destination).with_suffix('.base.zip'))
            with zipfile.ZipFile(base) as source:bodies={n:source.read(n) for n in source.namelist()}
            value=json.loads(bodies['initialization.json'])
            value['configuration'].update(policies)
            # These are declared isolated policy overrides, not substitutions
            # for the retained large inputs. Both actual horizons are90.
            value['configuration']['complete_daily'].update(consumption_days=90,remark_days=90)
            bodies['initialization.json']=json.dumps(value).encode()
            with zipfile.ZipFile(destination,'x') as target:
                for name,body in bodies.items():target.writestr(name,body)
            return Path(destination)

        original_finish=temporal.finish_run
        original_load=typed.load_image
        observed=dict(forced_spooled_sql_reads=0,threshold_force_rows=0,threshold_history_rows=0)
        def spooled_sql(run,item):
            value=original_load(run,item)
            if isinstance(value,RecordRows):return value
            observed['forced_spooled_sql_reads']+=1
            return RecordRows.from_rows(value)

        def finish(run,output,**options):
            from mta.runtime.input_reader import read_input
            profile=read_input(run,components=('profile',))['profile']
            for key,value in policies.items():self.assertEqual(profile[key],value)
            self.assertEqual(profile['complete_daily']['consumption_days'],90)
            self.assertEqual(profile['complete_daily']['remark_days'],90)
            # All producer APIs keep their declared list contract. Only actual
            # SQL image reloads cross to the closed immutable representation.
            with ExitStack() as stack:
                for module in (typed,force,operational_input_source,production_report_storage,
                               daily_sources,daily_transit,operational_reports):
                    if hasattr(module,'load_image'):stack.enter_context(patch.object(module,'load_image',side_effect=spooled_sql))
                if not observed['threshold_force_rows']:
                    with self.assertRaises(DatabaseError),transaction.atomic():
                        populations=deepcopy(output['_OperationalForceSources'])
                        for name in ('DBMMaster','MasterDataRaw'):
                            template=populations[name][0]
                            populations[name]=[dict(template) for _ in range(10001)]
                        source=force.write_force_source(run,populations)
                        actual=force._rows(source)
                        self.assertIsInstance(actual['DBMMaster'],RecordRows)
                        self.assertIsInstance(actual['MasterDataRaw'],RecordRows)
                        self.assertEqual(actual,storage(populations))
                        observed['threshold_force_rows']=20002
                        for name,make,writer,current in (
                            ('BOR_OrderAllocationHistory',bor_row,operational_bor.collect_bor_order_allocation_history,'current_bor'),
                            ('RRR_OrderAllocationHistory',rrr_row,operational_bor.collect_rrr_order_allocation_history,'current_rrr')):
                            rows=[dict(make(),ReportDate='2026-10-17') for _ in range(10001)]
                            item=production_report_storage.save(run,name,rows)
                            values=original_load(run,item)
                            self.assertIsInstance(values,RecordRows)
                            args=dict(opening_history=values,business_date='2026-10-18',horizon=90,**{current:[make()]})
                            expected=writer(**dict(args,opening_history=rows))
                            actual=writer(**args)
                            self.assertEqual(len(actual),len(expected))
                            self.assertEqual(digest(actual),digest(expected))
                            self.assertTrue(all(storage(a)==storage(b) for a,b in zip(actual,expected)))
                            self.assertEqual(digest(values),digest(rows))
                            observed['threshold_history_rows']+=10001
                        with connection.cursor() as cursor:cursor.execute('SELECT 1/0')
                    self.assertFalse(force.OperationalForceSource.objects.filter(run=run).exists())
                    with connection.cursor() as cursor:
                        for table,image in [(force.BINDINGS[n],'operational/force/'+n) for n in force.BINDINGS]+[
                            ('production/'+n,production_report_storage.PATHS[n]) for n in ('BOR_OrderAllocationHistory','RRR_OrderAllocationHistory')]:
                            cursor.execute('SELECT count(*) FROM '+typed.table_sql(table)+' WHERE vf_run_id=%s AND vf_image=%s',[run.pk,image])
                            self.assertEqual(cursor.fetchone()[0],0)
                return original_finish(run,output,**options)

        with patch.object(fixture,'source_archive',side_effect=source_archive),patch.object(temporal,'finish_run',side_effect=finish):
            native.Section11NativeDayPostgresTests.test_positive_native_day_atomic_readback_reports_selection_and_early_rejection(self)
        self.assertGreater(observed['forced_spooled_sql_reads'],0)
        self.assertEqual(observed['threshold_force_rows'],20002)
        self.assertEqual(observed['threshold_history_rows'],20002)
        print('POST_DBM_POLICY_THRESHOLD_SQL_PASS '+json.dumps(observed,sort_keys=True))
