"""Focused M3 SQL ownership proof in one explicitly disposable database.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
if not os.environ.get('VF_SECRET_KEY_FILE'):
    os.environ.setdefault('VF_SECRET_KEY','m3-postgres-proof-only')
import django
django.setup()
from django.db import connection, transaction, DatabaseError
from django.test import override_settings


@unittest.skipUnless(os.environ.get('VF_INGESTION_M3_POSTGRES_PROOF') == '1',
                     'Explicit disposable M3 database required')
class AcceptedDailyPostgresTests(unittest.TestCase):
    def test_accepted_facts_and_preparation_transaction_boundary(self):
        from release import initialize_csv as driver, register_mta
        from tools.create_daily_csv_example import create
        from mta.mdm import initialization as init
        from mta.runtime import daily_feed, accepted_daily, batch_storage
        from mta.runtime.daily_feed_models import DailyFeedAttempt
        from mta.runtime.ingestion_models import InitializationCertification
        from mta.runtime.models import ProductionInitialization, CalculationRun
        from mta.runtime.ingestion_admission import readiness
        from mta.serialization import digest
        self.assertEqual(connection.settings_dict['NAME'],'vf_ingestion_m3_20261021')
        self.assertEqual(ProductionInitialization.objects.count(),0)
        release=dict(schema='vectorflow-native-release-source-v1',source_commit='4'*40,
            manifest_sha256='5'*64,implementation_sha256=init.current_implementation_digest(),
            source_files_digest='6'*64,migrations_digest='7'*64)
        # Existing incremental-current SQL guard/rollback proofs run before
        # certification and leave no source, capture, header or projection rows.
        with patch.dict(os.environ,VF_MDM_CURRENT_PG_PROOF='1'):
            from tests.test_mdm_daily_current import CurrentOwnerPostgresTests
            def owned(test,db):
                test.assertEqual(db.settings_dict['NAME'],'vf_ingestion_m3_20261021')
            class Incremental(CurrentOwnerPostgresTests):
                def runTest(case):
                    from copy import deepcopy
                    from decimal import Decimal
                    from mta.mdm import daily_current
                    before={}
                    for _,model,part,rows,path in daily_current.closing_owners(case.closing):
                        before[(model.__name__,str(part))]=list(model.objects.filter(source=case.source,**part).order_by('ordinal').values_list('pk',flat=True))
                    case.consume();case.guc('fresh.mdm_current_run',str(case.run.pk))
                    from mta.runtime.mdm_models import MdmLocationUse
                    with case.assertRaisesRegex(DatabaseError,'cannot move its occurrence'),transaction.atomic():
                        MdmLocationUse.objects.filter(source=case.source,use_kind='direct').update(use_kind='parent')
                    for _,model,part,rows,path in daily_current.closing_owners(case.closing):
                        case.assertEqual(daily_current._write_partition(case.source,model,part,rows,path),
                            dict(updated=0,inserted=0,deleted=0))
                        case.assertEqual(before[(model.__name__,str(part))],list(model.objects.filter(source=case.source,**part).order_by('ordinal').values_list('pk',flat=True)))
                    changed=deepcopy(case.closing)
                    changed['importer']['SkuAttributeData'][0]['Weight']=Decimal('2.125')
                    with case.assertRaisesRegex(ValueError,'late writer'),transaction.atomic():
                        for _,model,part,rows,path in daily_current.closing_owners(changed):
                            daily_current._write_partition(case.source,model,part,rows,path)
                        daily_current.verify_current(case.source,changed)
                        raise ValueError('late writer')
                    daily_current.verify_current(case.source,case.closing)
            suite=unittest.TestSuite([CurrentOwnerPostgresTests(
                'test_all_tables_are_guarded_and_wrong_state_update_truncate_denied'),Incremental('runTest')])
            with patch('tests.mdm_proof_resources.assert_owned_mdm_proof',side_effect=owned):
                component=unittest.TextTestRunner(verbosity=1).run(suite)
            self.assertTrue(component.wasSuccessful())
            self.assertEqual(CalculationRun.objects.count(),0)
        render=register_mta.render_sql
        def local_sql(text,values):
            return render(text.replace('GRANT :"owner_role", fresh_operational_acceptor TO :"issuer_role";',''),values)
        with tempfile.TemporaryDirectory() as td, patch('release.native_identity.require_current',return_value=release), \
                patch.object(register_mta,'render_sql',side_effect=local_sql), \
                patch.dict(os.environ,MTA_DB_NAME=connection.settings_dict['NAME'],
                    MTA_INSTALLER_PASSWORD_FILE='/run/secrets/mta_installer_password',
                    VF_NATIVE_RELEASE_COMMIT=release['source_commit'],VF_NATIVE_RELEASE_SHA256=release['manifest_sha256']):
            root=create(Path(__file__).resolve().parents[1]/'examples/starter-data/vectorflow-starter-inputs-v1.zip',
                Path(td)/'csv',csv_onboarding=True)
            manifest=json.loads((root/'opening/opening-manifest.json').read_text())
            pin=hashlib.sha256((root/'opening/opening-manifest.json').read_bytes()).hexdigest()
            receipt=root/'onboarding.json'
            driver.write_receipt(receipt,dict(status='VALIDATING',phase='CSV',manifest_sha256=pin,
                pack_pins={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
                    for name in ('binding-template.json','permissions.json')}))
            driver.run(root,pin,manifest['configuration_digest'],manifest['recipe_digest'],receipt)
            owner=ProductionInitialization.objects.select_related('source').get()
            binding=json.loads((root/'binding-template.json').read_text())
            binding.update(initialization_id=str(owner.pk),source_digest=owner.source.digest)
            (root/'binding.json').write_text(json.dumps(binding))
            pick=Path(td)/'pick';pick.mkdir()
            with driver.installer_login(), override_settings(
                    VF_MDM_SOURCE_DIGEST=owner.source.digest,
                    VF_MTA_PERMISSIONS_FILE=str(root/'permissions.json'),
                    VF_MTA_PERMISSIONS_SHA256=hashlib.sha256((root/'permissions.json').read_bytes()).hexdigest()):
                from mta.runtime import production_daily as native_contract
                validation=patch.object(native_contract,'_decode_csv_value',wraps=native_contract._decode_csv_value)
                validator=validation.start();self.addCleanup(validation.stop)
                # The normal operation prepares this one native graph once.
                staged=daily_feed.stage(root/'binding.json',root/'2026-10-18','2026-10-18',
                    input_root=root,work_root=root/'operations',pick_root=pick)
                attempt=DailyFeedAttempt.objects.get(attempt_id=staged['attempt_id'])
                args=daily_feed._parameters(daily_feed.load_binding(root/'binding.json'),owner,None,
                    'csv-v1-'+attempt.batch_digest,pick)
                from mta.runtime.production_daily import decode
                prepared=accepted_daily.read(attempt,args)
                original=json.loads((Path(attempt.archive_path)/'native-day.json').read_bytes())
                self.assertEqual(decode(prepared,attempt.input_sha256),original)
                self.assertEqual(staged['phase'],'VALIDATED')
                self.assertEqual(CalculationRun.objects.count(),0)
                self.assertEqual(readiness(owner.pk).master_revision_id,str(attempt.master_revision_id))
                # Same bytes reuse the attempt; rejected writes cannot change
                # accepted facts, context, chronology, or their SQL rows.
                self.assertEqual(daily_feed.stage(root/'binding.json',root/'2026-10-18','2026-10-18',
                    input_root=root,work_root=root/'operations',pick_root=pick)['attempt_id'],str(attempt.attempt_id))
                def denied(sql,values=()):
                    with self.assertRaises(DatabaseError),transaction.atomic(),connection.cursor() as cursor:
                        cursor.execute(sql,values)
                denied('UPDATE mta.fresh_mta_dailyfeedattempt SET prepared_context=%s WHERE id=%s',
                    [json.dumps({'forged':True}),attempt.pk])
                entry=next(item for item in attempt.accepted_facts['feeds'] if item['count'])
                denied('UPDATE '+batch_storage.table_sql(entry['filename'])+' SET vf_ordinal=vf_ordinal+1 WHERE vf_attempt_id=%s',
                    [str(attempt.attempt_id)])
                denied('DELETE FROM '+batch_storage.table_sql(entry['filename'])+' WHERE vf_attempt_id=%s',[str(attempt.attempt_id)])
                denied('TRUNCATE '+batch_storage.table_sql(entry['filename']))
                with transaction.atomic():
                    from mta.runtime.ingestion_models import IngestionRevisionState
                    from django.db.models import F
                    IngestionRevisionState.objects.filter(initialization=owner).update(action_epoch=F('action_epoch')+1)
                    with self.assertRaisesRegex(ValueError,'stale'):accepted_daily.check(attempt,args)
                    transaction.set_rollback(True)
                self.assertEqual(digest(decode(accepted_daily.read(attempt,args),attempt.input_sha256)),digest(original))
                print('M3_POSTGRES_STAGING_PASS full typed reconstruction, seal/update/delete/truncate denial, '
                      'stale action cut, rollback, duplicate attempt')
                from mta.runtime import production_daily
                from mta.runtime.input_reader import read_input
                from mta.runtime.services import read_outputs
                from mta.runtime.receipt_integrity import verify as verify_run, audit_output
                from mta.runtime.ingestion_models import MasterInputRevision
                from mta.application import r1_importer_master as producer
                from mta.temporal import entry_preparation
                from mta.mdm import daily_input
                def execute_day(attempt):
                    result=daily_feed.execute(attempt.attempt_id,root/'binding.json',pick_root=pick)
                    self.assertEqual(result['status'],'PREPARED')
                    daily_feed.select(attempt.attempt_id,root/'binding.json',root/'selection.json')
                    selected=json.loads((root/'selection.json').read_bytes())
                    daily_feed.acknowledge(attempt.attempt_id,root/'binding.json',root/'selection.json',
                        dict(run_id=result['run_id'],output_digest=result['output_digest'],
                             selection_digest=selected['selection_digest'],ready=True,
                             proof_kind='component-contract-no-http-no-browser'))
                    attempt.refresh_from_db();run=attempt.run
                    verify_run(run);audit_output(run)
                    outputs=read_outputs(run)
                    self.assertTrue(outputs['ClosingState'][0]['importer']['MasterData'])
                    return run,outputs
                from mta.runtime import temporal
                from mta.runtime.mdm_daily_models import MdmDailyInputCapture
                from mta.runtime.accepted_daily import epochs
                from copy import deepcopy
                commit=temporal.finish_run
                rollback_proved=[]
                def commit_with_rollback_proof(run,output,**arguments):
                    cut=epochs(owner.pk)
                    before_revisions=MasterInputRevision.objects.count()
                    with self.assertRaisesRegex(ValueError,'M3 deliberate late rollback'),transaction.atomic():
                        commit(run,deepcopy(output),**arguments)
                        raise ValueError('M3 deliberate late rollback')
                    self.assertEqual(epochs(owner.pk),cut)
                    self.assertEqual(MasterInputRevision.objects.count(),before_revisions)
                    self.assertEqual(CalculationRun.objects.get(pk=run.pk).status,'RUNNING')
                    self.assertEqual(MdmDailyInputCapture.objects.get(run=run).status,'CAPTURED')
                    self.assertEqual(CalculationRun.objects.get(pk=run.pk).production_digest,'')
                    rollback_proved.append(True)
                    return commit(run,output,**arguments)
                with patch.object(entry_preparation,'process_importer_master',wraps=producer.process_importer_master) as full, \
                     patch.object(temporal,'finish_run',side_effect=commit_with_rollback_proof):
                    first,first_outputs=execute_day(attempt)
                    self.assertEqual(full.call_count,1)
                self.assertEqual(rollback_proved,[True])
                self.assertEqual(validator.call_count,1)
                self.assertTrue(first.production_manifest['master_preparation']['qualified'])
                # The unchanged successor must not reconstruct masters or invoke
                # the canonical full producer; accepted static leaves are refs.
                from mta.runtime import opening_storage, accepted_input_read
                from contextlib import ExitStack
                image_reader=opening_storage.load_image
                def no_opening(owner,metadata):
                    self.assertFalse(metadata['image'].startswith('input/opening'),
                        'successor reconstructed immutable opening')
                    return image_reader(owner,metadata)
                accepted_reader=accepted_input_read._load_opening_image
                def no_accepted_opening(owner,metadata):
                    self.assertFalse(metadata['image'].startswith('input/opening'),
                        'successor reconstructed immutable opening')
                    return accepted_reader(owner,metadata)
                successor_opening=ExitStack()
                successor_opening.enter_context(patch.object(opening_storage,'load_image',side_effect=no_opening))
                successor_opening.enter_context(patch.object(accepted_input_read,'_load_opening_image',side_effect=no_accepted_opening))
                self.addCleanup(successor_opening.close)
                second_stage=daily_feed.stage(root/'binding.json',root/'2026-10-19','2026-10-19',
                    input_root=root,work_root=root/'operations',pick_root=pick)
                second_attempt=DailyFeedAttempt.objects.get(attempt_id=second_stage['attempt_id'])
                unchanged_dml=[]
                def observe(execute,sql,params,many,context):
                    if sql.lstrip().split(None,1)[0].upper() in ('INSERT','UPDATE','DELETE') and any(
                            name in sql for name in ('fresh_mta_mdmskuattributes','fresh_mta_mdmskudescription',
                            'fresh_mta_mdmlocationattributes','fresh_mta_mdmlocationdescription',
                            'fresh_mta_mdmskulocpair','fresh_mta_mdmskuuse','fresh_mta_mdmlocationuse')):
                        unchanged_dml.append(sql)
                    return execute(sql,params,many,context)
                original_native_execute=production_daily.execute
                def native_without_opening(*arguments,**options):
                    try:
                        return original_native_execute(*arguments,**options)
                    finally:
                        # The unchanged history-report producer legitimately
                        # reads the initial historical opening. This gate covers
                        # daily preparation/capture/engine/commit, not that report.
                        successor_opening.close()
                original_entry=entry_preparation.prepare
                def compare_master(prior,opening_date,day,profile,identity,**owned):
                    actual=original_entry(prior,opening_date,day,profile,identity,**owned)
                    from mta.temporal.chain import entry_inputs
                    payload,_=entry_inputs(actual['prior'],opening_date,actual['day'],profile,identity)
                    # Independent pure full-producer comparison only: no second
                    # engine/day, database write, capture or persisted result.
                    payload['raw_master']=list(payload['raw_master'])
                    expected_master=producer.process_importer_master(payload)
                    self.assertEqual(digest(actual['master']),digest(expected_master))
                    return actual
                with connection.execute_wrapper(observe), patch.object(daily_input,'nms_master_raw',side_effect=AssertionError('raw rebuild')), \
                     patch.object(daily_input,'compose',side_effect=AssertionError('full compose')), \
                     patch.object(entry_preparation,'prepare',side_effect=compare_master), \
                     patch.object(production_daily,'execute',side_effect=native_without_opening), \
                     patch.object(entry_preparation,'process_importer_master',side_effect=AssertionError('full master producer')), \
                     patch.object(production_daily,'inspect_execution',side_effect=AssertionError('second complete preflight')):
                    second,second_outputs=execute_day(second_attempt)
                self.assertEqual(validator.call_count,2)
                self.assertEqual(unchanged_dml,[])
                self.assertEqual(second.predecessor_id,first.pk)
                self.assertTrue(second.production_manifest['master_preparation']['reused'])
                self.assertEqual(second.production_manifest['master_preparation']['full_master_producer_calls'],0)
                rebuilt=read_input(second)
                expected=daily_input.compose(rebuilt['mdm_input'],
                    daily_input.nms_master_raw(first_outputs['ClosingState'][0]),last_run_date='2026-10-19')
                self.assertEqual(list(rebuilt['day']['raw_master']),expected)
                self.assertTrue(second.input_payload['owner_references'])
                self.assertTrue(second.input_payload['batch_references'])
                self.assertTrue(second.input_payload['derived_references'])
                self.assertEqual(readiness(owner.pk).master_revision_id,
                    str(MasterInputRevision.objects.filter(initialization=owner,status='ACCEPTED').order_by('-master_epoch').first().pk))
                self.assertEqual(daily_feed.execute(second_attempt.attempt_id,root/'binding.json',pick_root=pick)['run_id'],str(second.pk))
                # Exercise the actual database cut guard independently of an
                # additional business date. All component metadata/writes roll back.
                from copy import deepcopy
                from mta.runtime.capture_preparation import require_commit
                from mta.runtime.accepted_daily import epochs
                from mta.runtime.ingestion_models import IngestionRevisionState
                from django.db.models import F
                old_manifest=deepcopy(second.production_manifest)
                with transaction.atomic():
                    body=deepcopy(second.production_manifest['ingestion_preparation'])
                    body['capture_cut']=epochs(owner.pk)
                    body['receipt_digest']=digest({k:v for k,v in body.items() if k!='receipt_digest'})
                    second.production_manifest=dict(second.production_manifest,ingestion_preparation=body)
                    self.assertEqual(require_commit(second),body)
                    IngestionRevisionState.objects.filter(initialization=owner).update(action_epoch=F('action_epoch')+1)
                    with self.assertRaisesRegex(ValueError,'changed during calculation'):require_commit(second)
                    transaction.set_rollback(True)
                second.production_manifest=old_manifest
                print('M3_POSTGRES_DAILY_PASS root+own-successor, full typed audit, accepted references, '
                      'zero unchanged master reconstruction, no repeated preflight, publication/idempotency')
