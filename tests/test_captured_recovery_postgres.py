"""Focused actual-SQL capture reuse/rollback proof in one EMPTY owned test DB.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','release.mta_settings')
import django
django.setup()
from django.db import connection, transaction


class CapturedArgumentTests(unittest.TestCase):
    def test_no_normal_argument_can_replace_frozen_capture(self):
        from mta.runtime.temporal import execute_day
        names = ('day','profile','predecessor','opening','mdm_source','mdm_retry',
            'feed_attempt','prepared_arguments','prepared_state','production_initialization',
            'report_exceptions','pick_output_root','pick_config_sha256','finalization_config',
            'shipment_sha256','daily_input_sha256','consumer_opening','report_disposition')
        for name in names:
            with self.subTest(name=name), patch('mta.runtime.captured_recovery.resume') as resume:
                options = dict(day=None,profile=None,execution_revision='frozen-only',_captured_retry={})
                options[name] = {} if name in ('report_exceptions','profile','day') else 'replacement'
                with self.assertRaisesRegex(ValueError,'cannot replace its frozen native arguments'):
                    execute_day(**options)
                resume.assert_not_called()


@unittest.skipUnless(os.environ.get('VF_CAPTURED_RECOVERY_PROOF')=='1','Explicit disposable PostgreSQL proof required')
class CapturedRecoveryPostgresTests(unittest.TestCase):
    def test_exact_capture_reuse_rollback_and_normal_writer(self):
        fourth=os.environ.get('VF_CAPTURED_FOURTH_PROOF')=='1'
        from release import initialize_csv as driver, register_mta
        from tools.create_daily_csv_example import create
        from mta.mdm import initialization as init
        from mta.runtime import daily_feed, temporal, captured_input
        from mta.runtime.daily_feed_models import DailyFeedAttempt
        from mta.runtime.models import ProductionInitialization, CalculationRun
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        from mta.runtime.input_reader import read_input
        from mta.runtime.receipt_integrity import audit_input, audit_output, verify
        from mta.serialization import digest
        from mta.runtime.accepted_daily import epochs
        from mta.runtime.captured_recovery import _pins
        self.assertEqual(connection.settings_dict['NAME'],'vf_daily_optimization_20261021')
        self.assertEqual(ProductionInitialization.objects.count(),0)
        release=dict(schema='vectorflow-native-release-source-v1',source_commit='4'*40,
            manifest_sha256='5'*64,implementation_sha256=init.current_implementation_digest(),
            source_files_digest='6'*64,migrations_digest='7'*64)
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
            opening=root/'opening/opening-manifest.json'
            document=json.loads(opening.read_bytes()); pin=hashlib.sha256(opening.read_bytes()).hexdigest()
            receipt=root/'onboarding.json'
            driver.write_receipt(receipt,dict(status='VALIDATING',phase='CSV',manifest_sha256=pin,
                pack_pins={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
                    for name in ('binding-template.json','permissions.json')}))
            driver.run(root,pin,document['configuration_digest'],document['recipe_digest'],receipt)
            owner=ProductionInitialization.objects.select_related('source').get()
            binding=json.loads((root/'binding-template.json').read_bytes())
            binding.update(initialization_id=str(owner.pk),source_digest=owner.source.digest)
            (root/'binding.json').write_text(json.dumps(binding))
            pick=Path(td)/'pick';pick.mkdir()
            with driver.installer_login():
                staged=daily_feed.stage(root/'binding.json',root/'2026-10-18','2026-10-18',
                    input_root=root,work_root=root/'operations',pick_root=pick)
                attempt=DailyFeedAttempt.objects.get(attempt_id=staged['attempt_id'])
                # Interrupt only after the ordinary native input transaction.
                # BaseException models process loss, leaving no output or retry.
                with patch.object(temporal,'_finish_captured_day',side_effect=SystemExit('simulated external stop')):
                    with self.assertRaises(SystemExit):
                        daily_feed.execute(attempt.attempt_id,root/'binding.json',pick_root=pick)
                attempt.refresh_from_db();old=attempt.run
                self.assertEqual(old.status,'RUNNING');self.assertEqual(attempt.status,'RUNNING')
                raw=read_input(old); before=(old.input_digest,old.input_manifest_digest,digest(old.input_payload),
                    digest(attempt.accepted_facts),digest(attempt.prepared_context))
                expected=dict(run_id=str(old.pk),initialization_id=str(owner.pk),source_digest=owner.source.digest,
                    input_digest=old.input_digest,input_manifest_digest=old.input_manifest_digest,
                    daily_input_sha256=attempt.input_sha256,
                    capture_cut=old.production_manifest['ingestion_preparation']['capture_cut'])
                _pins(old,attempt,expected)
                revision='capture-recovery-proof-final'
                def resume(path):
                    return temporal.execute_day(day=None,profile=None,execution_revision=revision,
                        _captured_retry=dict(origin_run_id=str(old.pk),expected=expected,archive_path=str(path)))
                with patch.object(daily_feed,'atomic_json',side_effect=OSError('test receipt failure')):
                    with self.assertRaisesRegex(OSError,'test receipt failure'):
                        resume(Path(attempt.archive_path).with_name('receipt-failure'))
                old.refresh_from_db();attempt.refresh_from_db()
                self.assertEqual(old.status,'RUNNING');self.assertEqual(attempt.status,'RUNNING')
                self.assertEqual(CalculationRun.objects.count(),1)
                self.assertEqual(MdmDailyInputCapture.objects.count(),1)
                self.assertEqual(epochs(owner.pk),expected['capture_cut'])
                # Model the real first continuation failure after its new
                # canonical capture, preserving both FAILED generations.
                with patch.object(temporal,'calculate_day',side_effect=TypeError('immutable entry proof')):
                    with self.assertRaisesRegex(TypeError,'immutable entry proof'):
                        resume(Path(attempt.archive_path).with_name('failed-v1'))
                leaf=CalculationRun.objects.get(execution_revision=revision)
                leaf_attempt=DailyFeedAttempt.objects.get(run=leaf)
                self.assertEqual((leaf.status,leaf_attempt.status,leaf_attempt.phase),('FAILED','FAILED','CALCULATE'))
                self.assertEqual(leaf.input_payload['schema'],captured_input.SCHEMA)
                leaf_before=(leaf.status,leaf.input_manifest_digest,digest(leaf.input_payload),
                    leaf_attempt.status,digest(leaf_attempt.error))
                leaf_expected=dict(expected,run_id=str(leaf.pk),input_manifest_digest=leaf.input_manifest_digest,
                    capture_cut=leaf.production_manifest['ingestion_preparation']['capture_cut'])
                second=dict(physical_run_id=str(old.pk),physical_manifest_digest=old.input_manifest_digest,
                    physical_attempt_id=str(attempt.attempt_id),current_revision_cut=epochs(owner.pk))
                self.assertIsInstance(attempt.pk,int)
                self.assertNotEqual(str(attempt.pk),str(attempt.attempt_id))
                revision='capture-recovery-proof-second'
                def resume(path,*,spec=None):
                    return temporal.execute_day(day=None,profile=None,execution_revision=revision,
                        _captured_retry=dict(origin_run_id=str(leaf.pk),expected=leaf_expected,
                            archive_path=str(path),second_hop=second if spec is None else spec))
                foreign=dict(second,physical_run_id='00000000-0000-4000-8000-000000000001')
                with self.assertRaisesRegex(ValueError,'physical input/attempt ownership differs'):
                    resume(Path(attempt.archive_path).with_name('foreign'),spec=foreign)
                for invalid in (str(attempt.pk),'00000000-0000-4000-8000-000000000001'):
                    with self.assertRaisesRegex(ValueError,'physical input/attempt ownership differs'):
                        resume(Path(attempt.archive_path).with_name('wrong-attempt'),
                            spec=dict(second,physical_attempt_id=invalid))
                stale=dict(second,current_revision_cut=[0,0,0,0,0])
                with self.assertRaisesRegex(ValueError,'revisions or unique frozen leaf changed'):
                    resume(Path(attempt.archive_path).with_name('stale'),spec=stale)
                # An actual second SQL session owns the lock: duplicate-race
                # denial must occur before new run/capture metadata exists.
                import psycopg
                options=connection.settings_dict
                with psycopg.connect(host=options['HOST'],port=options['PORT'],dbname=options['NAME'],
                        user=options['USER'],password=options['PASSWORD'],autocommit=True) as competing:
                    competing.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',
                        ['vectorflow-daily-csv:'+str(owner.pk)])
                    with self.assertRaisesRegex(ValueError,'Another daily worker owns'):
                        resume(Path(attempt.archive_path).with_name('race'))
                with patch.object(daily_feed,'atomic_json',side_effect=OSError('second-hop receipt failure')):
                    with self.assertRaisesRegex(OSError,'second-hop receipt failure'):
                        resume(Path(attempt.archive_path).with_name('second-receipt-failure'))
                self.assertEqual(CalculationRun.objects.count(),2)
                self.assertEqual(MdmDailyInputCapture.objects.count(),2)
                self.assertEqual(epochs(owner.pk),second['current_revision_cut'])
                # Match the actual three-FAILED prefix. This intentional test
                # failure occurs before business math; no accepted day replay.
                with patch.object(temporal,'calculate_day',side_effect=TypeError('stock opening ownership proof')):
                    with self.assertRaisesRegex(TypeError,'stock opening ownership proof'):
                        resume(Path(attempt.archive_path).with_name('failed-v2'))
                first_leaf=leaf
                leaf=CalculationRun.objects.get(execution_revision=revision)
                leaf_attempt=DailyFeedAttempt.objects.get(run=leaf)
                self.assertEqual((leaf.status,leaf_attempt.status,leaf_attempt.phase),('FAILED','FAILED','CALCULATE'))
                self.assertEqual(leaf.input_payload['schema'],captured_input.SECOND)
                leaf_before=(leaf.status,leaf.input_manifest_digest,digest(leaf.input_payload),
                    leaf_attempt.status,digest(leaf_attempt.error))
                failed_before={str(v.pk):(v.status,v.input_digest,v.input_manifest_digest,digest(v.input_payload))
                    for v in CalculationRun.objects.order_by('created_at')}
                self.assertEqual(len(failed_before),3)
                leaf_expected=dict(expected,run_id=str(leaf.pk),input_manifest_digest=leaf.input_manifest_digest,
                    capture_cut=leaf.production_manifest['ingestion_preparation']['capture_cut'])
                second=dict(second,current_revision_cut=epochs(owner.pk))
                revision='capture-recovery-proof-final-third'
                def resume(path,*,spec=None,enabled=True):
                    return temporal.execute_day(day=None,profile=None,execution_revision=revision,
                        _captured_retry=dict(origin_run_id=str(leaf.pk),expected=leaf_expected,
                            archive_path=str(path),second_hop=second if spec is None else spec,
                            final_third_hop=enabled))
                with self.assertRaisesRegex(ValueError,'exact failed V1 leaf'):
                    resume(Path(attempt.archive_path).with_name('not-released'),enabled=False)
                for invalid in (str(attempt.pk),'00000000-0000-4000-8000-000000000001'):
                    with self.assertRaisesRegex(ValueError,'physical input/attempt ownership differs'):
                        resume(Path(attempt.archive_path).with_name('third-foreign'),
                            spec=dict(second,physical_attempt_id=invalid))
                with self.assertRaisesRegex(ValueError,'revisions or unique frozen leaf changed'):
                    resume(Path(attempt.archive_path).with_name('third-stale'),
                        spec=dict(second,current_revision_cut=[0,0,0,0,0]))
                with psycopg.connect(host=options['HOST'],port=options['PORT'],dbname=options['NAME'],
                        user=options['USER'],password=options['PASSWORD'],autocommit=True) as competing:
                    competing.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',
                        ['vectorflow-daily-csv:'+str(owner.pk)])
                    with self.assertRaisesRegex(ValueError,'Another daily worker owns'):
                        resume(Path(attempt.archive_path).with_name('third-race'))
                # Adversarial sibling metadata only in this scratch transaction;
                # actual canonical resolution must reject it, then roll back.
                cut=epochs(owner.pk)
                with transaction.atomic():
                    sibling=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=old.business_date,
                        execution_revision='adversarial-sibling',input_digest=old.input_digest,
                        input_payload={},status='RUNNING')
                    captured=MdmDailyInputCapture.objects.get(run=old)
                    values={f.attname:getattr(captured,f.attname) for f in captured._meta.concrete_fields
                        if f.name not in ('run','captured_at')}
                    values.update(run_id=sibling.pk,origin_id=old.pk)
                    MdmDailyInputCapture.objects.create(**values)
                    with self.assertRaisesRegex(ValueError,'canonical origin differs'):
                        captured_input.origin(first_leaf)
                    transaction.set_rollback(True)
                self.assertEqual(epochs(owner.pk),cut)
                original=leaf.input_payload
                leaf.input_payload=dict(original,origin_run_id=str(leaf.pk))
                leaf.input_manifest_digest=digest(leaf.input_payload)
                with self.assertRaisesRegex(ValueError,'canonical origin differs'):
                    captured_input.origin(leaf)
                leaf.refresh_from_db()
                with patch.object(daily_feed,'atomic_json',side_effect=OSError('third-hop receipt failure')):
                    with self.assertRaisesRegex(OSError,'third-hop receipt failure'):
                        resume(Path(attempt.archive_path).with_name('third-receipt-failure'))
                self.assertEqual(CalculationRun.objects.count(),3)
                self.assertEqual(MdmDailyInputCapture.objects.count(),3)
                self.assertEqual(epochs(owner.pk),second['current_revision_cut'])
                if fourth:
                    # Simulate a real external interruption after canonical
                    # snapshot commit; BaseException must not fake FAILED or
                    # relabel a successful run. No calculation returns here.
                    with patch.object(temporal,'calculate_day',side_effect=KeyboardInterrupt('human stop proof')):
                        with self.assertRaises(KeyboardInterrupt):
                            resume(Path(attempt.archive_path).with_name('human-stopped-third'))
                    leaf=CalculationRun.objects.get(execution_revision=revision)
                    leaf_attempt=DailyFeedAttempt.objects.get(run=leaf)
                    self.assertEqual((leaf.status,leaf_attempt.status,leaf_attempt.phase),('RUNNING','RUNNING','CALCULATE'))
                    self.assertFalse(leaf.checkpoints.exists())
                    self.assertEqual(MdmDailyInputCapture.objects.get(run=leaf).status,'CAPTURED')
                    leaf_before=(leaf.status,leaf.input_manifest_digest,digest(leaf.input_payload),
                        leaf_attempt.status,digest(leaf_attempt.error))
                    leaf_expected=dict(expected,run_id=str(leaf.pk),input_manifest_digest=leaf.input_manifest_digest,
                        capture_cut=leaf.production_manifest['ingestion_preparation']['capture_cut'])
                    second=dict(second,current_revision_cut=epochs(owner.pk))
                    revision='capture-recovery-proof-final-interrupted-fourth'
                    def resume(path,*,spec=None,enabled=True):
                        return temporal.execute_day(day=None,profile=None,execution_revision=revision,
                            _captured_retry=dict(origin_run_id=str(leaf.pk),expected=leaf_expected,
                                archive_path=str(path),second_hop=second if spec is None else spec,
                                final_interrupted_fourth_hop=enabled))
                    with self.assertRaisesRegex(ValueError,'exact failed V1 leaf'):
                        resume(Path(attempt.archive_path).with_name('fourth-not-released'),enabled=False)
                    with self.assertRaisesRegex(ValueError,'physical input/attempt ownership differs'):
                        resume(Path(attempt.archive_path).with_name('fourth-foreign'),
                            spec=dict(second,physical_attempt_id=str(attempt.pk)))
                    with self.assertRaisesRegex(ValueError,'revisions or unique frozen leaf changed'):
                        resume(Path(attempt.archive_path).with_name('fourth-stale'),
                            spec=dict(second,current_revision_cut=[0,0,0,0,0]))
                    with psycopg.connect(host=options['HOST'],port=options['PORT'],dbname=options['NAME'],
                            user=options['USER'],password=options['PASSWORD'],autocommit=True) as competing:
                        competing.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',
                            ['vectorflow-daily-csv:'+str(owner.pk)])
                        with self.assertRaisesRegex(ValueError,'Another daily worker owns'):
                            resume(Path(attempt.archive_path).with_name('fourth-race'))
                    cut=epochs(owner.pk)
                    # Exercise duplicate revision on an eligible RUNNING owner,
                    # before recovery consumes that owner. Replaying it after
                    # success is separately denied by the earlier owner guard.
                    allowed_revision=revision
                    try:
                        revision=old.execution_revision
                        with self.assertRaisesRegex(ValueError,'already attempted'):
                            resume(Path(attempt.archive_path).with_name('fourth-duplicate-revision'))
                    finally:
                        revision=allowed_revision
                    from django.db import OperationalError
                    from mta.mdm.supplier_revisions import _key
                    with connection.cursor() as cursor:
                        cursor.execute('SHOW lock_timeout')
                        self.assertEqual(cursor.fetchone()[0],'5s')
                    with psycopg.connect(host=options['HOST'],port=options['PORT'],dbname=options['NAME'],
                            user=options['USER'],password=options['PASSWORD'],autocommit=True) as competing:
                        competing.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',[_key(owner.source_id)])
                        with self.assertRaisesRegex(OperationalError,'lock timeout'):
                            resume(Path(attempt.archive_path).with_name('fourth-source-race'))
                    self.assertEqual(epochs(owner.pk),cut)
                    self.assertEqual((CalculationRun.objects.count(),MdmDailyInputCapture.objects.count()),(4,4))
                    print('INTERRUPTED_FOURTH_DUPLICATE_AND_SOURCE_LOCK_PASS')
                    with patch.object(daily_feed,'atomic_json',side_effect=OSError('fourth-hop receipt failure')):
                        with self.assertRaisesRegex(OSError,'fourth-hop receipt failure'):
                            resume(Path(attempt.archive_path).with_name('fourth-receipt-failure'))
                    leaf.refresh_from_db();leaf_attempt.refresh_from_db()
                    self.assertEqual((leaf.status,leaf_attempt.status),('RUNNING','RUNNING'))
                    self.assertEqual((CalculationRun.objects.count(),MdmDailyInputCapture.objects.count()),(4,4))
                    self.assertEqual(epochs(owner.pk),cut)
                    # A late metadata SQL failure must also undo the canonical
                    # human-stop disposition, new owner and its epoch writes.
                    import psycopg
                    with patch('mta.runtime.capture_preparation.seal',side_effect=psycopg.DataError('fourth metadata failure')):
                        with self.assertRaisesRegex(psycopg.DataError,'fourth metadata failure'):
                            resume(Path(attempt.archive_path).with_name('fourth-metadata-failure'))
                    leaf.refresh_from_db();leaf_attempt.refresh_from_db()
                    self.assertEqual((leaf.status,leaf_attempt.status),('RUNNING','RUNNING'))
                    self.assertEqual((CalculationRun.objects.count(),MdmDailyInputCapture.objects.count()),(4,4))
                    self.assertEqual(epochs(owner.pk),cut)
                    print('INTERRUPTED_FOURTH_METADATA_ROLLBACK_PASS oldRUNNING epochs counts unchanged')
                commit=temporal.finish_run
                rolled=[]
                def commit_with_rollback(run,output,**options):
                    from copy import deepcopy
                    cut=epochs(owner.pk)
                    with self.assertRaisesRegex(ValueError,'test late commit failure'), transaction.atomic():
                        commit(run,deepcopy(output),**options)
                        raise ValueError('test late commit failure')
                    run.refresh_from_db()
                    self.assertEqual(run.status,'RUNNING')
                    self.assertEqual(MdmDailyInputCapture.objects.get(run=run).status,'CAPTURED')
                    self.assertEqual(epochs(owner.pk),cut)
                    self.assertFalse(run.checkpoints.exists())
                    rolled.append(True)
                    return commit(run,output,**options)
                with patch.object(temporal,'finish_run',side_effect=commit_with_rollback), \
                        patch('mta.runtime.input_storage.save_input',side_effect=AssertionError('No typed input rewrite')), \
                        patch('mta.runtime.accepted_daily.read',side_effect=AssertionError('No CSV restaging')):
                    result=resume(Path(attempt.archive_path).with_name('continued'))
                self.assertEqual(rolled,[True]);self.assertEqual(result.status,'SUCCEEDED')
                new=DailyFeedAttempt.objects.get(run=result)
                self.assertEqual((new.status,new.phase),('COMMITTED','PREPARE'))
                self.assertEqual(new.accepted_facts,{})
                self.assertEqual(result.input_digest,old.input_digest)
                self.assertNotEqual(result.input_manifest_digest,old.input_manifest_digest)
                self.assertEqual(read_input(result),raw)
                audit_input(result);audit_output(result);verify(result)
                old.refresh_from_db();attempt.refresh_from_db()
                self.assertEqual((old.status,attempt.status),('FAILED','FAILED'))
                self.assertEqual((old.input_digest,old.input_manifest_digest,digest(old.input_payload),
                    digest(attempt.accepted_facts),digest(attempt.prepared_context)),before)
                self.assertEqual(result.input_payload['schema'],captured_input.SECOND)
                self.assertEqual(MdmDailyInputCapture.objects.get(run=result).origin_id,leaf.pk)
                self.assertEqual(captured_input.origin(result).pk,old.pk)
                self.assertEqual(read_input(leaf),raw)
                leaf.refresh_from_db();leaf_attempt.refresh_from_db()
                if fourth:
                    self.assertEqual((leaf.status,leaf_attempt.status),('FAILED','FAILED'))
                    self.assertEqual(leaf_attempt.error['type'],'HumanInterruption')
                    self.assertEqual((leaf.input_manifest_digest,digest(leaf.input_payload)),leaf_before[1:3])
                    self.assertFalse(leaf.checkpoints.exists())
                else:
                    self.assertEqual((leaf.status,leaf.input_manifest_digest,digest(leaf.input_payload),
                        leaf_attempt.status,digest(leaf_attempt.error)),leaf_before)
                for failed in CalculationRun.objects.filter(pk__in=failed_before):
                    self.assertEqual((failed.status,failed.input_digest,failed.input_manifest_digest,
                        digest(failed.input_payload)),failed_before[str(failed.pk)])
                with self.assertRaisesRegex(ValueError,'fixed two-hop boundary'):
                    captured_input._origin(result,second_allowed=False)
                with self.assertRaisesRegex(ValueError,'fixed third-hop boundary'):
                    captured_input._origin(result,second_allowed=True,third_allowed=False)
                cut=epochs(owner.pk)
                with transaction.atomic():
                    candidate=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=old.business_date,
                        execution_revision='adversarial-fourth',input_digest=old.input_digest,
                        input_payload={},status='RUNNING')
                    captured=MdmDailyInputCapture.objects.get(run=result)
                    values={f.attname:getattr(captured,f.attname) for f in captured._meta.concrete_fields
                        if f.name not in ('run','captured_at')}
                    values.update(run_id=candidate.pk,origin_id=result.pk,status='CAPTURED',consumed_at=None)
                    MdmDailyInputCapture.objects.create(**values)
                    with self.assertRaisesRegex(ValueError,'fixed third-hop boundary'):
                        captured_input.manifest(candidate,result)
                    if fourth:
                        with self.assertRaisesRegex(ValueError,'fixed third-hop boundary'):
                            captured_input.manifest(candidate,result,final_interrupted_fourth_hop=True)
                    transaction.set_rollback(True)
                self.assertEqual(epochs(owner.pk),cut)
                self.assertEqual(CalculationRun.objects.count(),5 if fourth else 4)
                self.assertEqual(MdmDailyInputCapture.objects.count(),5 if fourth else 4)
                self.assertFalse(CalculationRun.objects.filter(pk=candidate.pk).exists())
                result.refresh_from_db()
                self.assertEqual(result.status,'SUCCEEDED')
                rejection='exact failed V1 leaf' if fourth else 'already attempted'
                with self.assertRaisesRegex(ValueError,rejection):
                    resume(Path(attempt.archive_path).with_name('duplicate'))
                self.assertEqual(epochs(owner.pk),cut)
                self.assertEqual((CalculationRun.objects.count(),MdmDailyInputCapture.objects.count()),
                    (5,5) if fourth else (4,4))
                # Changed reference roots must be denied by actual DB-backed
                # resolution, even if a caller recomputes the wrapper checksum.
                original=result.input_payload
                bad=dict(original,origin_manifest_digest='0'*64)
                result.input_payload=bad;result.input_manifest_digest=digest(bad)
                with self.assertRaisesRegex(ValueError,'original typed manifest differs'):
                    captured_input.origin(result)
                result.refresh_from_db()
                from django.core.exceptions import ValidationError
                for invalid in (new.pk,str(new.pk)):
                    with self.assertRaises((ValueError,ValidationError)):
                        daily_feed.execute(invalid,root/'binding.json',pick_root=pick,resume=True)
                    with self.assertRaises((ValueError,ValidationError)):
                        daily_feed.select(invalid,root/'binding.json',root/'selection.json')
                report=daily_feed.execute(new.attempt_id,root/'binding.json',pick_root=pick,resume=True)
                self.assertEqual(report['status'],'PREPARED')
                from mta.application.native_input_archive import open_archive
                import zipfile
                stream,_=open_archive(result)
                with stream,zipfile.ZipFile(stream) as archive:
                    exported=json.loads(archive.read('manifest.json'))
                self.assertEqual(exported['input_digest'],old.input_digest)
                if old.input_payload.get('content_kind')=='native-prepared-input-v1':
                    self.assertEqual(exported['schema'],'fresh-native-input-download-v2')
                    self.assertEqual(exported['captured_input_digest'],digest(read_input(result)))
                daily_feed.select(new.attempt_id,root/'binding.json',root/'selection.json')
                selected=json.loads((root/'selection.json').read_bytes())
                daily_feed.acknowledge(new.attempt_id,root/'binding.json',root/'selection.json',
                    dict(run_id=str(result.pk),output_digest=result.output_digest,
                         selection_digest=selected['selection_digest'],ready=True,
                         proof_kind='component-contract-no-http-no-browser'))
                self.assertFalse(daily_feed.unresolved_attempts(owner).exists())
                print(('INTERRUPTED_FOURTH_POSTGRES_PASS ' if fourth else 'CAPTURED_RECOVERY_POSTGRES_PASS ')+'exact-inputs no-rewrite distinct-owners filesystem+late-commit-rollback reports+archive duplicate-denial')
            from release.advance_ingestion import transition
            from release.upgrade_ingestion import retained
            from mta.runtime import ingestion_admission as admission
            from mta.runtime.ingestion_models import InitializationCertification
            before_transition=retained(owner)
            cert_before=InitializationCertification.objects.get(initialization=owner).receipt_digest
            newer=dict(release,source_commit='8'*40,manifest_sha256='7'*64)
            # Only image identities are synthetic here. The actual database,
            # original certificate, append-only registrar and schema/role joins
            # are real. Packaged exact-release proof belongs to the final image.
            with patch('release.native_identity.require_current',return_value=newer), \
                    patch.object(admission,'BASELINE_RELEASE',release['source_commit']), \
                    patch.object(admission,'BASELINE_MANIFEST',release['manifest_sha256']):
                changed=transition(owner.pk,previous_release=release,target_release=newer)
                self.assertEqual(changed['status'],'COMPATIBLE_RELEASE_APPENDED_ORIGINAL_CERTIFICATE_PRESERVED')
                owner.refresh_from_db();owner.source.refresh_from_db()
                self.assertEqual(retained(owner),before_transition)
                self.assertEqual(InitializationCertification.objects.get(initialization=owner).receipt_digest,cert_before)
                with connection.cursor() as c:
                    self.assertEqual(admission._admit(c,owner.pk,newer,pending=True).certification_digest,cert_before)
                print('COMPATIBLE_RELEASE_POSTGRES_PASS append-only real-schema-roles original-certificate-seals-unchanged')


if __name__=='__main__':
    unittest.main()
