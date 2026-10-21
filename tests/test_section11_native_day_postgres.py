"""Operational/report separation: real SQL rollback, report-only failure/rebuild and successor admission.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib,json,os,tempfile,unittest,zipfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('VF_SECTION11_POSTGRES_PROOF')=='1','Owned small Section9 PostgreSQL proof required')
class Section11NativeDayPostgresTests(unittest.TestCase):
    def test_positive_native_day_atomic_readback_reports_selection_and_early_rejection(self):
        from django.db import connection,transaction,DatabaseError
        from release import initialize_csv as driver,register_mta
        from mta.mdm import initialization as init
        from mta.runtime import daily_feed,temporal
        from mta.runtime.models import ProductionInitialization,CalculationRun
        from mta.runtime.daily_feed_models import DailyFeedAttempt
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        from mta.runtime.accepted_daily import epochs
        from mta.runtime.receipt_integrity import audit_input,audit_output,verify
        from mta.runtime.input_reader import read_input
        from mta.runtime.services import read_outputs
        from mta.serialization import digest
        from tools.create_daily_csv_example import create
        from tests.section9_native_fixture import source_archive,enqueue_control,verify_positive
        self.assertEqual(connection.settings_dict['NAME'],'vf_section9_contracts_20261021')
        self.assertFalse(ProductionInitialization.objects.exists())
        release=dict(schema='vectorflow-native-release-source-v1',source_commit='4'*40,
            manifest_sha256='5'*64,implementation_sha256=init.current_implementation_digest(),
            source_files_digest='6'*64,migrations_digest='7'*64)
        render=register_mta.render_sql
        def local_sql(text,values):return render(text.replace('GRANT :"owner_role", fresh_operational_acceptor TO :"issuer_role";',''),values)
        with tempfile.TemporaryDirectory() as td,patch('release.native_identity.require_current',return_value=release), \
                patch.object(register_mta,'render_sql',side_effect=local_sql), \
                patch.dict(os.environ,MTA_DB_NAME=connection.settings_dict['NAME'],
                    MTA_INSTALLER_PASSWORD_FILE='/run/secrets/mta_installer_password',
                    VF_NATIVE_RELEASE_COMMIT=release['source_commit'],VF_NATIVE_RELEASE_SHA256=release['manifest_sha256']):
            root=create(source_archive(Path(__file__).resolve().parents[1]/'examples/starter-data/vectorflow-starter-inputs-v1.zip',
                Path(td)/'section9.zip'),Path(td)/'csv',csv_onboarding=True)
            manifest=root/'opening/opening-manifest.json';doc=json.loads(manifest.read_bytes());pin=hashlib.sha256(manifest.read_bytes()).hexdigest()
            receipt=root/'onboarding.json'
            driver.write_receipt(receipt,dict(status='VALIDATING',phase='CSV',manifest_sha256=pin,
                pack_pins={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('binding-template.json','permissions.json')}))
            driver.run(root,pin,doc['configuration_digest'],doc['recipe_digest'],receipt)
            owner=ProductionInitialization.objects.select_related('source').get();enqueue_control(owner)
            binding=json.loads((root/'binding-template.json').read_bytes());binding.update(initialization_id=str(owner.pk),source_digest=owner.source.digest)
            (root/'binding.json').write_text(json.dumps(binding));pick=Path(td)/'pick';pick.mkdir()
            with driver.installer_login():
                staged=daily_feed.stage(root/'binding.json',root/'2026-10-18','2026-10-18',input_root=root,work_root=root/'operations',pick_root=pick)
                attempt=DailyFeedAttempt.objects.get(attempt_id=staged['attempt_id'])
                commit=temporal.finish_run;rolled=[]
                def prove_atomic(run,output,**options):
                    cut=epochs(owner.pk)
                    with self.assertRaisesRegex(ValueError,'Section9 late SQL rollback'),transaction.atomic():
                        commit(run,deepcopy(output),**options)
                        raise ValueError('Section9 late SQL rollback')
                    run.refresh_from_db();self.assertEqual(run.status,'RUNNING')
                    self.assertFalse(run.checkpoints.exists());self.assertEqual(epochs(owner.pk),cut)
                    self.assertEqual(MdmDailyInputCapture.objects.get(run=run).status,'CAPTURED');rolled.append(True)
                    return commit(run,output,**options)
                from mta.presentation import operational_reports
                from mta.runtime.models import DailyReportGeneration,ExcessProjection,FulfillmentProjection,ExpediteProjection,PickPostProjection
                build=operational_reports._build
                recipe=operational_reports.recipe_identity()
                def fail_report(run):
                    build(run)
                    raise ValueError('Section11 derived-only rollback')
                with patch.object(temporal,'finish_run',side_effect=prove_atomic),patch.object(operational_reports,'_build',new=fail_report),patch.object(operational_reports,'recipe_identity',return_value=recipe):
                    with self.assertRaisesRegex(ValueError,'Section11 derived-only rollback'):
                        daily_feed.execute(attempt.attempt_id,root/'binding.json',pick_root=pick)
                attempt.refresh_from_db();run=attempt.run;run.refresh_from_db()
                self.assertEqual(run.status,'SUCCEEDED');self.assertEqual(run.production_manifest['version'],3)
                self.assertEqual(attempt.status,'COMMITTED')
                self.assertEqual(MdmDailyInputCapture.objects.get(run=run).status,'CONSUMED')
                self.assertEqual(DailyReportGeneration.objects.get(run=run).status,'INCOMPLETE')
                for model in (ExcessProjection,FulfillmentProjection,ExpediteProjection,PickPostProjection):
                    self.assertFalse(model.objects.filter(run=run).exists())
                with connection.cursor() as cursor:
                    cursor.execute("SELECT count(*) FROM mta_state.btr_btrsnapshotforui WHERE vf_run_id=%s",[run.pk])
                    self.assertEqual(cursor.fetchone()[0],0)
                    cursor.execute("SELECT count(*) FROM mta_state.report_export_cell WHERE vf_run_id=%s",[run.pk])
                    self.assertEqual(cursor.fetchone()[0],0)
                from mta.runtime.receipt_integrity import verify_root
                verify_root(run);audit_output(run)
                operational=read_outputs(run,include_reports=False)
                operational_before=(run.output_digest,run.production_digest,digest(operational['ClosingState']))
                # Report readiness must not gate exact own successor admission.
                next_stage=daily_feed.stage(root/'binding.json',root/'2026-10-19','2026-10-19',input_root=root,work_root=root/'operations',pick_root=pick)
                next_attempt=DailyFeedAttempt.objects.get(attempt_id=next_stage['attempt_id'])
                self.assertEqual(next_attempt.predecessor_id,run.pk)
                cut=epochs(owner.pk)
                from mta.runtime.accepted_daily import check as check_accepted
                params=daily_feed._parameters(binding,owner,run,'csv-v1-'+next_attempt.batch_digest,pick)
                check_accepted(next_attempt,params)
                with patch.object(temporal,'calculate_day',side_effect=AssertionError('Report-only resume cannot calculate')):
                    result=daily_feed.execute(attempt.attempt_id,root/'binding.json',pick_root=pick,resume=True)
                run.refresh_from_db();self.assertEqual(operational_before,(run.output_digest,run.production_digest,digest(read_outputs(run,include_reports=False)['ClosingState'])))
                self.assertEqual(epochs(owner.pk),cut)
                next_attempt.refresh_from_db();check_accepted(next_attempt,params)
                generation=operational_reports.generation(run)
                operational_reports.verify_rows(run,generation.metadata)
                # The report cut does not waive real input/operational invalidation.
                with self.assertRaises(DatabaseError),transaction.atomic():
                    DailyFeedAttempt.objects.filter(pk=next_attempt.pk).update(batch_id=next_attempt.batch_id+'-changed')
                with transaction.atomic():
                    DailyFeedAttempt.objects.filter(pk=next_attempt.pk).update(error={'fixture':'unexecuted-owner-change'})
                    self.assertNotEqual(epochs(owner.pk),cut)
                    transaction.set_rollback(True)
                self.assertEqual(epochs(owner.pk),cut)
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute('UPDATE mta_state.dbm_dbmmaster SET "Norm"=COALESCE("Norm",0)+1 WHERE vf_run_id=%s',[run.pk])
                    self.assertNotEqual(epochs(owner.pk),cut)
                    transaction.set_rollback(True)
                self.assertEqual(epochs(owner.pk),cut)
                with self.assertRaises(DatabaseError),transaction.atomic():
                    ExcessProjection.objects.filter(run=run).update(row_count=0)
                with self.assertRaises(DatabaseError),transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("UPDATE mta_state.btr_btrsnapshotforui SET vf_image='forbidden-renamed-image' WHERE vf_run_id=%s",[run.pk])
                self.assertEqual(epochs(owner.pk),cut)
                self.assertEqual(operational_reports.generation(run).digest,generation.digest)
                self.assertEqual(DailyReportGeneration.objects.filter(run=run).count(),1)
                print('SECTION11_REVISION_GUARDS_PASS report-only lifecycle does not stale successor; actual facts/operational writes invalidate; sealed derived rows reject writes')
                print('SECTION11_OPERATIONAL_REPORT_FAILURE_REBUILD_PASS unchanged run/root/nextopening; successor admitted while report incomplete; no engine replay')
                self.assertEqual(rolled,[True]);self.assertEqual(result['status'],'PREPARED')
                run=CalculationRun.objects.get(pk=result['run_id']);verify_positive(self,run)
                frozen=read_input(run);audit_input(run);audit_output(run);verify(run)
                outputs=read_outputs(run);self.assertTrue(outputs['Reports'])
                from mta.application.complete_daily_batch_files import reports_from_pick_state,sqlcmd_bytes,PICK_NAMES
                state=outputs['ClosingState'][0]['complete']
                for kind,report in reports_from_pick_state(state).items():
                    expected=sqlcmd_bytes(report['resultsets'])
                    self.assertEqual((pick/str(run.pk)/'download'/PICK_NAMES[kind]).read_bytes(),expected)
                from mta.application.native_input_archive import open_archive
                stream,_=open_archive(run)
                with stream,zipfile.ZipFile(stream) as archive:
                    exported=json.loads(archive.read('manifest.json'))
                    self.assertEqual(exported['captured_input_digest'],digest(frozen))
                daily_feed.select(attempt.attempt_id,root/'binding.json',root/'selection.json')
                selection=json.loads((root/'selection.json').read_bytes())
                daily_feed.acknowledge(attempt.attempt_id,root/'binding.json',root/'selection.json',dict(
                    run_id=str(run.pk),output_digest=run.output_digest,selection_digest=selection['selection_digest'],ready=True,
                    proof_kind='component-contract-no-http-no-browser'))
                self.assertEqual(list(daily_feed.unresolved_attempts(owner).values_list('pk',flat=True)),[next_attempt.pk])
                print('SECTION9_NATIVE_TERMINAL_PASS full values typed commit/readback, controls, reports, fourfiles, archive, admission/select')
                from mta.application import native_output_contracts as contracts
                validate=contracts.validate_row
                def invalid(row,table,**kwargs):
                    if table=='Intermediate/RequirementInColorBand':row=dict(row,RelPSO='2147483648')
                    return validate(row,table,**kwargs)
                bad=daily_feed.stage(root/'binding.json',root/'2026-10-19','2026-10-19',input_root=root,work_root=root/'operations',pick_root=pick)
                with self.assertRaisesRegex(ValueError,'RelPSO'),patch.object(contracts,'validate_row',side_effect=invalid):
                    daily_feed.execute(bad['attempt_id'],root/'binding.json',pick_root=pick)
                failed=DailyFeedAttempt.objects.get(attempt_id=bad['attempt_id']).run
                self.assertEqual(failed.status,'FAILED');self.assertFalse(failed.checkpoints.exists())
                self.assertEqual(MdmDailyInputCapture.objects.get(run=failed).status,'CAPTURED')
                run.refresh_from_db();self.assertEqual(run.status,'SUCCEEDED');self.assertEqual(read_input(run),frozen)
                self.assertEqual(MdmDailyInputCapture.objects.get(run=run).status,'CONSUMED')
                print('SECTION9_NATIVE_EARLY_REJECTION_PASS no committed outputs/consumption, accepted prefix unchanged')


if __name__=='__main__':unittest.main()
