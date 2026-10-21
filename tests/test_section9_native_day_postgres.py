"""Bounded real native day, positive allocation/Pick and terminal consumers.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib,json,os,tempfile,unittest,zipfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('VF_SECTION9_POSTGRES_PROOF')=='1','Owned small Section9 PostgreSQL proof required')
class Section9NativeDayPostgresTests(unittest.TestCase):
    def test_positive_native_day_atomic_readback_reports_selection_and_early_rejection(self):
        from django.db import connection,transaction
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
                with patch.object(temporal,'finish_run',side_effect=prove_atomic):
                    result=daily_feed.execute(attempt.attempt_id,root/'binding.json',pick_root=pick)
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
                self.assertFalse(daily_feed.unresolved_attempts(owner).exists())
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
