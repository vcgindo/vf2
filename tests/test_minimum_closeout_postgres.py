"""Bounded native closure proof for the released minimum correction."""
import hashlib
import json
import os
import types
import unittest
import zipfile
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('VF_MINIMUM_CLOSEOUT_PROOF') == '1', 'Explicit owned minimum-closeout SQL proof required')
class MinimumCloseoutPostgresTests(unittest.TestCase):
    proof_database = 'vf_minimum_closeout_20261022'

    def test_expanded_grey_full_tail_and_every_current_partition(self):
        from django.db import connection, transaction, DatabaseError
        from tests import section9_native_fixture as fixture
        from tests.test_post_dbm_persistence_postgres import PostDbmPersistencePostgres
        from mta.mdm import daily_current
        from mta.mdm.master_owners import business_fields
        from mta.presentation import production_reports, daily_sources
        from mta.runtime import temporal
        from mta.runtime.models import DailySourceReceipt
        from mta.runtime.production_report_storage import PATHS
        from mta.application.production_output_policy import SOURCE_SCHEMA, contract
        from mta.application import production_bor_contract
        from mta.serialization import storage, digest
        self.assertEqual(connection.settings_dict['NAME'], self.proof_database)

        original_archive = fixture.source_archive
        original_produce = production_bor_contract.produce
        original_write = daily_current._write_partition
        original_finish = temporal.finish_run
        original_receipt = daily_sources.receipt
        baseline_path = Path(os.environ['VF_BASELINE_CURRENT_SOURCE'])
        code = baseline_path.read_text()
        self.assertEqual(hashlib.sha256(code.replace('\r\n','\n').encode()).hexdigest(),
            'a9c00ef56d19605f010ef7578848275b6171e5a5edb814c533d9fd3896897958')
        baseline = types.ModuleType('minimum_baseline_current')
        exec(compile(code, str(baseline_path), 'exec'), baseline.__dict__)
        observed = dict(grey_projections=0, native_current_partitions=[], receipt_bytes=[],
            late_sql_rollbacks=0, expanded_source_writes=0, optional_audit_policy='absent-as-in-saved-workload')

        def source_archive(original, destination):
            initial = original_archive(original, Path(destination).with_suffix('.minimum-base.zip'))
            with zipfile.ZipFile(initial) as archive:
                bodies = {name: archive.read(name) for name in archive.namelist()}
            value = json.loads(bodies['initialization.json'])
            # Declared synthetic rule-boundary overrides only. Preserve the
            # positive order/Pick/control rows owned by the retained fixture.
            def zero_norm(item):
                if isinstance(item, dict):
                    if item.get('SKUCode') == '5954' and 'Norm' in item: item['Norm'] = 0
                    for child in item.values(): zero_norm(child)
                elif isinstance(item, list):
                    for child in item: zero_norm(child)
            zero_norm(value)
            self.assertNotIn('native_upload_audit',value['configuration'])
            for row in value['configuration']['calculation']['stock_openings']:
                if row['sku_code'] == '5954': row['stock'] = 0
            bodies['initialization.json'] = json.dumps(value).encode()
            for name in ('day-01.json','day-02.json'):
                day = json.loads(bodies[name])
                for row in day['day']['raw_daily']:
                    if row['SKUCode'] == '5954':
                        row.update(Stock=0, Consumption=0, GIT=0, Receipts=0, PSO=0)
                sources = day['producer_sources']
                self.assertEqual(sources['schema'], SOURCE_SCHEMA)
                self.assertEqual(sources['report_policy']['output_contract'], contract())
                sources['report_policy'].update(bor_history_horizon=90, rrr_history_horizon=90)
                bodies[name] = json.dumps(day).encode()
            with zipfile.ZipFile(destination, 'x') as archive:
                for name, body in bodies.items(): archive.writestr(name, body)
            return Path(destination)

        def produce(**options):
            self.assertEqual(options['policy'],contract()['normal_bor'])
            self.assertTrue(any(row['DispatchColor']=='GREY' for row in options['dispatch_colours']))
            observed['grey_projections'] += 1
            return original_produce(**options)

        def partition(source, model, owner, expected, path):
            names = [f.name for f in business_fields(model)]
            def rows():
                return list(model.objects.filter(source=source, **owner).order_by('ordinal').values('pk','ordinal',*names))
            def epochs():
                with connection.cursor() as cursor:
                    cursor.execute('SELECT to_jsonb(C) FROM mta.fresh_mta_initializationcertification C ORDER BY initialization_id')
                    return cursor.fetchall()
            before = rows()
            retained = {r['ordinal']:r['pk'] for r in before if r['ordinal']<=len(expected)}
            with transaction.atomic():
                old_result = baseline._write_partition(source,model,owner,expected,path)
                old_rows, old_epochs = rows(), epochs()
                transaction.set_rollback(True)
            self.assertEqual(rows(),before)
            result = original_write(source,model,owner,expected,path)
            new_rows = rows()
            self.assertEqual(result,old_result)
            self.assertEqual(storage([{k:v for k,v in r.items() if k!='pk'} for r in new_rows]),
                             storage([{k:v for k,v in r.items() if k!='pk'} for r in old_rows]))
            self.assertTrue(all(r['pk']==retained[r['ordinal']] for r in new_rows if r['ordinal'] in retained))
            self.assertEqual(epochs(),old_epochs)
            observed['native_current_partitions'].append(dict(model=model.__name__,partition=owner,
                rows=len(expected),full_values=True,retained_pks=True,certification_epochs_equal=True))
            return result

        def finish(run, output, **options):
            if not observed['late_sql_rollbacks']:
                with self.assertRaises(DatabaseError), transaction.atomic():
                    original_finish(run,deepcopy(output),**options)
                    self.assertEqual(DailySourceReceipt.objects.get(run=run).run_id,run.pk)
                    with connection.cursor() as cursor: cursor.execute('SELECT 1/0')
                run.refresh_from_db()
                self.assertEqual(run.status,'RUNNING')
                self.assertFalse(DailySourceReceipt.objects.filter(run=run).exists())
                observed['late_sql_rollbacks'] += 1
            return original_finish(run,output,**options)

        with ExitStack() as stack:
            stack.enter_context(patch.object(fixture,'source_archive',side_effect=source_archive))
            stack.enter_context(patch.object(production_bor_contract,'produce',side_effect=produce))
            stack.enter_context(patch.object(daily_current,'_write_partition',side_effect=partition))
            stack.enter_context(patch.object(temporal,'finish_run',side_effect=finish))
            PostDbmPersistencePostgres.test_native_policy_readbacks_threshold_transport_rollback_and_report_rebuild(self)
        from mta.runtime.models import CalculationRun
        for run in CalculationRun.objects.filter(status='SUCCEEDED'):
            value = original_receipt(run)
            self.assertTrue(set(PATHS.values())<=set(value.images))
            observed['receipt_bytes'].append(len(json.dumps(value.images)))
            for name,path in PATHS.items():
                rows = daily_sources.image_rows(run,path)
                self.assertEqual(len(rows),value.images[path]['count'])
                self.assertEqual(digest(rows),value.images[path]['digest'])
            observed['expanded_source_writes']+=1
            from mta.runtime.native_audit_models import NativeUploadAudit
            from mta.mdm import native_audit
            self.assertFalse(NativeUploadAudit.objects.filter(run=run).exists())
            self.assertIsNone(native_audit.receipt(run))
        self.assertGreater(observed['grey_projections'],0)
        self.assertGreater(observed['expanded_source_writes'],0)
        self.assertEqual(observed['late_sql_rollbacks'],1)
        self.assertEqual({x['model'] for x in observed['native_current_partitions']},
            {'MdmSkuAttributes','MdmSkuDescription','MdmLocationAttributes','MdmLocationDescription',
             'MdmSkuLocPair','MdmSkuLocMasterPair','MdmSkuLocCurrent','MdmSkuUse','MdmLocationUse'})
        if os.environ.get('VF_MINIMUM_CLOSEOUT_PROOF_OUTPUT'):
            Path(os.environ['VF_MINIMUM_CLOSEOUT_PROOF_OUTPUT']).write_text(json.dumps(observed,indent=2))
        print('MINIMUM_NATIVE_GREY_FULL_TAIL_PASS '+json.dumps(observed),flush=True)
