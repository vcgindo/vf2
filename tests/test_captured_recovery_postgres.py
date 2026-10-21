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
from django.db import connection, transaction, DataError, ProgrammingError


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
        finite=os.environ.get('VF_CAPTURED_FINITE_PROOF')=='1'
        sixth=os.environ.get('VF_CAPTURED_SIXTH_PROOF')=='1' or finite
        fifth=os.environ.get('VF_CAPTURED_FIFTH_PROOF')=='1' or sixth
        fourth=os.environ.get('VF_CAPTURED_FOURTH_PROOF')=='1' or fifth
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
        self.assertEqual(connection.settings_dict['NAME'],
            'vf_btr_terminal_admission_20261022' if os.environ.get('VF_CAPTURED_TERMINAL_PROOF')=='1' else
            'vf_admission_contracts_20261022' if finite else
            'vf_section9_fifth_proof_20261021' if fifth else 'vf_daily_optimization_20261021')
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
            archive=Path(__file__).resolve().parents[1]/'examples/starter-data/vectorflow-starter-inputs-v1.zip'
            if fifth:
                from tests.section9_native_fixture import source_archive,enqueue_control,verify_positive
                archive=source_archive(archive,Path(td)/'positive-native.zip')
            root=create(archive,Path(td)/'csv',csv_onboarding=True)
            opening=root/'opening/opening-manifest.json'
            document=json.loads(opening.read_bytes()); pin=hashlib.sha256(opening.read_bytes()).hexdigest()
            receipt=root/'onboarding.json'
            driver.write_receipt(receipt,dict(status='VALIDATING',phase='CSV',manifest_sha256=pin,
                pack_pins={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
                    for name in ('binding-template.json','permissions.json')}))
            driver.run(root,pin,document['configuration_digest'],document['recipe_digest'],receipt)
            owner=ProductionInitialization.objects.select_related('source').get()
            if fifth:enqueue_control(owner)
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
                raw=read_input(old)
                if os.environ.get('VF_CAPTURED_TERMINAL_PROOF')=='1':
                    from tests.test_captured_terminal_postgres import prove_terminal
                    prove_terminal(self,owner,old,raw,release,root,pick)
                    return
                before=(old.input_digest,old.input_manifest_digest,digest(old.input_payload),
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
                if fifth:
                    # Exactly the current production checkpoint: five genuinely
                    # FAILED captures, latest an empty fourth reference. No
                    # successful state is rewritten to manufacture eligibility.
                    with patch.object(temporal,'calculate_day',side_effect=ValueError('fourth native assignment proof')):
                        with self.assertRaisesRegex(ValueError,'fourth native assignment proof'):
                            resume(Path(attempt.archive_path).with_name('failed-fourth'))
                    leaf=CalculationRun.objects.get(execution_revision=revision)
                    leaf_attempt=DailyFeedAttempt.objects.get(run=leaf)
                    self.assertEqual((leaf.status,leaf_attempt.status,leaf_attempt.phase),('FAILED','FAILED','CALCULATE'))
                    leaf_before=(leaf.status,leaf.input_manifest_digest,digest(leaf.input_payload),
                        leaf_attempt.status,digest(leaf_attempt.error))
                    leaf_expected=dict(expected,run_id=str(leaf.pk),input_manifest_digest=leaf.input_manifest_digest,
                        capture_cut=leaf.production_manifest['ingestion_preparation']['capture_cut'])
                    second=dict(second,current_revision_cut=epochs(owner.pk))
                    revision='capture-recovery-proof-terminal-fifth'
                    def resume(path,*,spec=None,pins=None,enabled=True):
                        return temporal.execute_day(day=None,profile=None,execution_revision=revision,
                            _captured_retry=dict(origin_run_id=str(leaf.pk),expected=leaf_expected if pins is None else pins,
                                archive_path=str(path),second_hop=second if spec is None else spec,
                                final_failed_fifth_hop=enabled))
                    def failed_record(pk):
                        item=DailyFeedAttempt.objects.get(run_id=pk)
                        files={name:(hashlib.sha256((Path(item.archive_path)/name).read_bytes()).hexdigest()
                            if (Path(item.archive_path)/name).exists() else None)
                            for name in ('result.json','captured-origin.json','phases.jsonl')}
                        return json.dumps(dict(run=CalculationRun.objects.filter(pk=pk).values().get(),
                            attempt=DailyFeedAttempt.objects.filter(pk=item.pk).values().get(),
                            capture=MdmDailyInputCapture.objects.filter(run_id=pk).values().get(),files=files),
                            sort_keys=True,default=str)
                    failed_exact={str(v.pk):failed_record(v.pk) for v in CalculationRun.objects.order_by('created_at')}
                    self.assertEqual(len(failed_exact),5)
                    self.assertEqual(daily_feed.unresolved_attempts(owner).count(),5)
                    from copy import deepcopy
                    for mutation in ('database','source','cycle','digest'):
                        bad=deepcopy(leaf.input_payload)
                        if mutation=='database':bad['identity']['database_oid']+=1
                        if mutation=='source':bad['identity']['source_digest']='0'*64
                        if mutation=='cycle':bad['origin_run_id']=str(leaf.pk)
                        if mutation=='digest':bad['origin_manifest_digest']='0'*64
                        leaf.input_payload=bad;leaf.input_manifest_digest=digest(bad)
                        with self.assertRaises(ValueError):captured_input.origin(leaf)
                        leaf.refresh_from_db()
                    cut=epochs(owner.pk)
                    with transaction.atomic():
                        sibling=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=old.business_date,
                            execution_revision='adversarial-fifth-sibling',input_digest=old.input_digest,
                            input_payload={},status='RUNNING')
                        captured=MdmDailyInputCapture.objects.get(run=old)
                        values={f.attname:getattr(captured,f.attname) for f in captured._meta.concrete_fields
                            if f.name not in ('run','captured_at')}
                        values.update(run_id=sibling.pk,origin_id=old.pk)
                        MdmDailyInputCapture.objects.create(**values)
                        with self.assertRaisesRegex(ValueError,'canonical origin differs'):captured_input.origin(leaf)
                        transaction.set_rollback(True)
                    self.assertEqual(epochs(owner.pk),cut)
                    with self.assertRaises(ValueError):resume(Path(attempt.archive_path).with_name('fifth-not-released'),enabled=False)
                    for field in ('run_id','initialization_id','source_digest','input_digest','input_manifest_digest','daily_input_sha256','capture_cut'):
                        wrong=[] if field=='capture_cut' else 'foreign'
                        with self.assertRaisesRegex(ValueError,'checkpoint pins differ'):
                            resume(Path(attempt.archive_path).with_name('fifth-bad-pin-'+field),pins=dict(leaf_expected,**{field:wrong}))
                    for field in ('physical_run_id','physical_manifest_digest','physical_attempt_id'):
                        with self.assertRaisesRegex(ValueError,'physical input/attempt ownership differs'):
                            resume(Path(attempt.archive_path).with_name('fifth-foreign-'+field),spec=dict(second,**{field:'foreign'}))
                    with self.assertRaisesRegex(ValueError,'physical input/attempt ownership differs'):
                        resume(Path(attempt.archive_path).with_name('fifth-numeric-attempt'),spec=dict(second,physical_attempt_id=str(attempt.pk)))
                    with self.assertRaisesRegex(ValueError,'revisions or unique frozen leaf changed'):
                        resume(Path(attempt.archive_path).with_name('fifth-stale'),spec=dict(second,current_revision_cut=[0,0,0,0,0]))
                    allowed_revision=revision
                    try:
                        revision=old.execution_revision
                        with self.assertRaisesRegex(ValueError,'already attempted'):
                            resume(Path(attempt.archive_path).with_name('fifth-duplicate-revision'))
                    finally:revision=allowed_revision
                    with self.assertRaisesRegex(ValueError,'new sibling operation directory'):
                        resume(Path(attempt.archive_path))
                    for key,error,message in (('vectorflow-daily-csv:'+str(owner.pk),ValueError,'Another daily worker owns'),
                            (_key(owner.source_id),OperationalError,'lock timeout')):
                        with psycopg.connect(host=options['HOST'],port=options['PORT'],dbname=options['NAME'],
                                user=options['USER'],password=options['PASSWORD'],autocommit=True) as competing:
                            competing.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',[key])
                            with self.assertRaisesRegex(error,message):resume(Path(attempt.archive_path).with_name('fifth-race-'+str(len(key))))
                    cut=epochs(owner.pk)
                    for target,error in (('mta.runtime.daily_feed.atomic_json',OSError('fifth receipt failure')),
                            ('mta.runtime.capture_preparation.seal',psycopg.DataError('fifth metadata failure'))):
                        with patch(target,side_effect=error),self.assertRaises(type(error)):
                            resume(Path(attempt.archive_path).with_name('fifth-rollback-'+type(error).__name__))
                        self.assertEqual(epochs(owner.pk),cut)
                        self.assertEqual((CalculationRun.objects.count(),MdmDailyInputCapture.objects.count()),(5,5))
                        self.assertEqual({pk:failed_record(pk) for pk in failed_exact},failed_exact)
                    print('TERMINAL_FIFTH_GUARDS_PASS exact5FAILED foreign/pins/numericUUID/stale/duplicate/locks/fs+SQLmetadata rollback')
                if sixth:
                    # Reproduce the stopped fifth owner through the actual
                    # prior writer, never by rewriting successful status.
                    with patch.object(temporal,'_finish_captured_day',side_effect=SystemExit('human stopped fifth')):
                        with self.assertRaises(SystemExit):
                            resume(Path(attempt.archive_path).with_name('human-stopped-fifth'))
                    leaf=CalculationRun.objects.get(execution_revision=revision)
                    leaf_attempt=DailyFeedAttempt.objects.get(run=leaf)
                    self.assertEqual((leaf.status,leaf_attempt.status,leaf_attempt.phase),('RUNNING','RUNNING','CALCULATE'))
                    self.assertEqual({pk:failed_record(pk) for pk in failed_exact},failed_exact)
                    leaf_before=(leaf.status,leaf.input_manifest_digest,digest(leaf.input_payload),
                        leaf_attempt.status,digest(leaf_attempt.error))
                    leaf_expected=dict(expected,run_id=str(leaf.pk),input_manifest_digest=leaf.input_manifest_digest,
                        capture_cut=leaf.production_manifest['ingestion_preparation']['capture_cut'])
                    second=dict(second,current_revision_cut=epochs(owner.pk))
                    revision='native-interrupted-sixth-'+release['source_commit']
                    def resume(path,*,spec=None,pins=None,enabled=True):
                        return temporal.execute_day(day=None,profile=None,execution_revision=revision,
                            _captured_retry=dict(origin_run_id=str(leaf.pk),expected=leaf_expected if pins is None else pins,
                                archive_path=str(path),second_hop=second if spec is None else spec,
                                final_interrupted_sixth_hop=enabled))
                    def unchanged_sixth():
                        leaf.refresh_from_db();leaf_attempt.refresh_from_db()
                        self.assertEqual((leaf.status,leaf_attempt.status),('RUNNING','RUNNING'))
                        self.assertEqual((CalculationRun.objects.count(),MdmDailyInputCapture.objects.count()),(6,6))
                        self.assertEqual(epochs(owner.pk),second['current_revision_cut'])
                        self.assertEqual({pk:failed_record(pk) for pk in failed_exact},failed_exact)
                        self.assertEqual(read_input(leaf),raw)
                    with self.assertRaises(ValueError):resume(Path(attempt.archive_path).with_name('sixth-unflagged'),enabled=False)
                    allowed_revision=revision
                    try:
                        revision='unbound-source-revision'
                        with self.assertRaisesRegex(ValueError,'must bind its packaged source'):
                            resume(Path(attempt.archive_path).with_name('sixth-unbound-revision'))
                    finally:revision=allowed_revision
                    for field in leaf_expected:
                        with self.assertRaisesRegex(ValueError,'checkpoint pins differ'):
                            resume(Path(attempt.archive_path).with_name('sixth-bad-'+field),
                                pins=dict(leaf_expected,**{field:[] if field=='capture_cut' else 'foreign'}))
                    for field in ('physical_run_id','physical_manifest_digest','physical_attempt_id'):
                        with self.assertRaisesRegex(ValueError,'physical input/attempt ownership differs'):
                            resume(Path(attempt.archive_path).with_name('sixth-foreign-'+field),spec=dict(second,**{field:'foreign'}))
                    with self.assertRaisesRegex(ValueError,'revisions or unique frozen leaf changed'):
                        resume(Path(attempt.archive_path).with_name('sixth-stale'),spec=dict(second,current_revision_cut=[0,0,0,0,0]))
                    for key,error,message in (('vectorflow-daily-csv:'+str(owner.pk),ValueError,'Another daily worker owns'),
                            (_key(owner.source_id),OperationalError,'lock timeout')):
                        with psycopg.connect(host=options['HOST'],port=options['PORT'],dbname=options['NAME'],
                                user=options['USER'],password=options['PASSWORD'],autocommit=True) as competing:
                            competing.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',[key])
                            with self.assertRaisesRegex(error,message):resume(Path(attempt.archive_path).with_name('sixth-race-'+str(len(key))))
                    # Actual row lock contention in a distinct SQL session.
                    with psycopg.connect(host=options['HOST'],port=options['PORT'],dbname=options['NAME'],
                            user=options['USER'],password=options['PASSWORD'],options=options['OPTIONS']['options']) as competing:
                        competing.execute('SELECT id FROM mta.fresh_mta_calculationrun WHERE id=%s FOR UPDATE',[leaf.pk])
                        with self.assertRaisesRegex(OperationalError,'lock timeout'):
                            resume(Path(attempt.archive_path).with_name('sixth-row-race'))
                    for target,error in (('mta.runtime.daily_feed.atomic_json',OSError('sixth receipt failure')),
                            ('mta.runtime.capture_preparation.seal',psycopg.DataError('sixth metadata failure'))):
                        with patch(target,side_effect=error),self.assertRaises(type(error)):
                            resume(Path(attempt.archive_path).with_name('sixth-rollback-'+type(error).__name__))
                        unchanged_sixth()
                    # Inject real scratch rows only after metadata ownership
                    # starts. Rejection rolls back both injected data and its
                    # revision trigger, leaving every original cut unchanged.
                    from mta.runtime.models import PickProjection,ExcessProjection,FulfillmentProjection,ExpediteProjection,PickPostProjection
                    from mta.runtime.publication_models import DailySourceReceipt
                    from mta.runtime.offline_rrr_models import OfflineRrrColourSource
                    from django.db import models
                    guard_cases=['typed','export',PickProjection,ExcessProjection,FulfillmentProjection,
                        ExpediteProjection,PickPostProjection,DailySourceReceipt,OfflineRrrColourSource]
                    for guard_case in guard_cases:
                        injected=[]
                        def inject_guard_row(execute,sql,params,many,context):
                            if not injected and sql.startswith('SELECT 1 FROM mta_state.'):
                                injected.append(True)
                                if guard_case=='typed':
                                    with connection.cursor() as c:c.execute('INSERT INTO mta_state.bpr_bprmaster (vf_run_id,vf_image,vf_ordinal) VALUES (%s,%s,0)',[leaf.pk,'guard-only'])
                                elif guard_case=='export':
                                    with connection.cursor() as c:c.execute('INSERT INTO mta_state.report_export_cell (vf_run_id,vf_image,row_ordinal,column_ordinal,value_type) VALUES (%s,%s,0,0,%s)',[leaf.pk,'guard-only','null'])
                                else:
                                    fields={}
                                    for f in guard_case._meta.concrete_fields:
                                        if f.name=='run' or f.auto_created or getattr(f,'auto_now_add',False) or f.has_default():continue
                                        if isinstance(f,models.CharField):fields[f.name]='0'*min(64,f.max_length or 64)
                                        elif isinstance(f,models.IntegerField):fields[f.name]=0
                                        elif isinstance(f,models.JSONField):fields[f.name]={}
                                        else:raise AssertionError('Unspecified scratch receipt field '+f.name)
                                    if 'input_digest' in fields:fields['input_digest']=leaf.input_digest
                                    guard_case.objects.create(run=leaf,**fields)
                            return execute(sql,params,many,context)
                        # Offline RRR cannot belong to this ordinary native
                        # fixture: its existing SQL owner guard rejects the
                        # row itself, before the continuation may see it.
                        offline=guard_case is OfflineRrrColourSource
                        message=('Explicit owned offline RRR transaction required' if offline else
                            'typed result rows' if isinstance(guard_case,str) else 'output source receipts')
                        with connection.execute_wrapper(inject_guard_row),self.assertRaisesRegex(ProgrammingError if offline else ValueError,message):
                            resume(Path(attempt.archive_path).with_name('sixth-injected-'+(guard_case if isinstance(guard_case,str) else guard_case.__name__)))
                        self.assertEqual(injected,[True]);unchanged_sixth()
                    # Execute a real failing SQL statement at outer COMMIT,
                    # after the receipt exists. The directory is diagnostic.
                    real_commit=connection.commit
                    diagnostic=Path(attempt.archive_path).with_name('sixth-late-sql-commit-failure')
                    def fail_commit():
                        if (diagnostic/'captured-origin.json').exists():
                            with connection.cursor() as cursor:cursor.execute('SELECT 1/0')
                        return real_commit()
                    with patch.object(connection,'commit',side_effect=fail_commit),self.assertRaises(DataError):
                        resume(diagnostic)
                    self.assertTrue((diagnostic/'captured-origin.json').exists())
                    unchanged_sixth()
                    with self.assertRaisesRegex(ValueError,'new sibling operation directory'):resume(diagnostic)
                    print('TERMINAL_SIXTH_GUARDS_PASS exact6owners locks stale foreign packaged-revision filesystem+actualSQLcommit rollback')
                if finite:
                    with patch.object(temporal,'calculate_day',side_effect=KeyboardInterrupt('stopped OOM sixth fixture')):
                        with self.assertRaises(KeyboardInterrupt):
                            resume(Path(attempt.archive_path).with_name('stopped-sixth'))
                    leaf=CalculationRun.objects.get(execution_revision=revision)
                    from tests.test_captured_finite_postgres import prove_finite
                    prove_finite(self,owner,leaf,raw,release,root,pick,failed_record)
                    return
                commit=temporal.finish_run
                rolled=[]
                def commit_with_rollback(run,output,**options):
                    from copy import deepcopy
                    cut=epochs(owner.pk)
                    if sixth:
                        # Database-backed seventh resolution, with a valid
                        # uncommitted sixth prefix and no result rows. Every
                        # adversarial row is removed by this SQL rollback.
                        import uuid
                        from mta.runtime.input_v3 import _live_identity
                        with transaction.atomic():
                            from mta.runtime.services import fail_run
                            fail_run(run,RuntimeError('Adversarial seventh boundary; entire transaction rolls back'))
                            a6=DailyFeedAttempt.objects.get(run=run)
                            a6.status='FAILED';a6.save(update_fields=['status'])
                            seventh=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=run.business_date,
                                execution_revision='adversarial-seventh-reader',input_digest=run.input_digest,input_payload={},status='RUNNING')
                            cap=MdmDailyInputCapture.objects.get(run=run)
                            copied={f.attname:getattr(cap,f.attname) for f in cap._meta.concrete_fields if f.name not in ('run','captured_at')}
                            copied.update(run_id=seventh.pk,origin_id=run.pk)
                            MdmDailyInputCapture.objects.create(**copied)
                            a6=DailyFeedAttempt.objects.get(run=run)
                            a7={f.attname:getattr(a6,f.attname) for f in a6._meta.concrete_fields if f.name not in ('id','attempt_id','created_at','updated_at')}
                            a7.update(run_id=seventh.pk,status='RUNNING',request_key=str(uuid.uuid4()),archive_path=str(Path(a6.archive_path).with_name('adversarial-seventh-reader')))
                            seventh_attempt=DailyFeedAttempt.objects.create(**a7)
                            seventh.input_payload=dict(schema=captured_input.SECOND,identity=_live_identity(seventh,reading=False),
                                origin_run_id=str(run.pk),origin_manifest_digest=run.input_manifest_digest,
                                content_digest=run.input_digest,images={},physical_origin_run_id=str(old.pk),
                                physical_origin_manifest_digest=old.input_manifest_digest)
                            seventh.input_manifest_digest=digest(seventh.input_payload)
                            seventh.save(update_fields=['input_payload','input_manifest_digest'])
                            for status in ('RUNNING','FAILED'):
                                seventh.status=status;seventh.save(update_fields=['status'])
                                seventh_attempt.status=status;seventh_attempt.save(update_fields=['status'])
                                with self.assertRaisesRegex(ValueError,'fixed third-hop boundary'):captured_input.origin(seventh)
                            transaction.set_rollback(True)
                        run.refresh_from_db();self.assertEqual(run.status,'RUNNING')
                        self.assertEqual(epochs(owner.pk),cut)
                    expected_error='division by zero' if fifth else 'test late commit failure'
                    with self.assertRaisesRegex(DataError if fifth else ValueError,expected_error), transaction.atomic():
                        commit(run,deepcopy(output),**options)
                        if fifth:
                            with connection.cursor() as cursor:cursor.execute('SELECT 1/0')
                        else:raise ValueError('test late commit failure')
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
                if (fourth and not fifth) or sixth:
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
                expected_count=7 if sixth else 6 if fifth else 5 if fourth else 4
                self.assertEqual(CalculationRun.objects.count(),expected_count)
                self.assertEqual(MdmDailyInputCapture.objects.count(),expected_count)
                self.assertFalse(CalculationRun.objects.filter(pk=candidate.pk).exists())
                result.refresh_from_db()
                self.assertEqual(result.status,'SUCCEEDED')
                rejection='exact failed V1 leaf' if sixth else 'already attempted' if fifth else 'exact failed V1 leaf' if fourth else 'already attempted'
                with self.assertRaisesRegex(ValueError,rejection):
                    resume(Path(attempt.archive_path).with_name('duplicate'))
                self.assertEqual(epochs(owner.pk),cut)
                self.assertEqual((CalculationRun.objects.count(),MdmDailyInputCapture.objects.count()),
                    (expected_count,expected_count))
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
                if fifth:
                    verify_positive(self,result)
                    from mta.runtime.services import read_outputs
                    from mta.application.complete_daily_batch_files import reports_from_pick_state,sqlcmd_bytes,PICK_NAMES
                    values=read_outputs(result)
                    for kind,report_value in reports_from_pick_state(values['ClosingState'][0]['complete']).items():
                        self.assertEqual((pick/str(result.pk)/'download'/PICK_NAMES[kind]).read_bytes(),sqlcmd_bytes(report_value['resultsets']))
                    if sixth:
                        continuation=json.loads((Path(new.archive_path)/'captured-origin.json').read_bytes())
                        self.assertEqual(continuation['native_release'],release)
                        self.assertEqual(continuation['execution_revision'],revision)
                        self.assertEqual(continuation['origin_execution_revision'],leaf.execution_revision)
                        self.assertEqual(values['Lineage'][0]['captured_continuation'],continuation)
                        self.assertNotEqual(result.pk,leaf.pk)
                        self.assertNotEqual(new.attempt_id,leaf_attempt.attempt_id)
                    self.assertEqual({pk:failed_record(pk) for pk in failed_exact},failed_exact)
                    self.assertEqual(daily_feed.unresolved_attempts(owner).count(),7 if sixth else 6)
                    # The successful fifth cannot be used to make a sixth; the
                    # independent boundary fixture also proves an all-FAILED
                    # sixth reference is unreadable by the fixed reader limit.
                    with self.assertRaises(ValueError):
                        captured_input.manifest(candidate,result,final_failed_fifth_hop=True)
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
                if fifth:self.assertEqual({pk:failed_record(pk) for pk in failed_exact},failed_exact)
                if sixth:
                    # Publishing resolves only this exact failed ancestry.
                    with transaction.atomic():
                        for day_value in (__import__('datetime').date(2026,10,17),__import__('datetime').date(2026,10,18)):
                            a0=DailyFeedAttempt.objects.create(initialization=owner,business_date=day_value,
                                batch_id='unrelated-failure-'+str(day_value),batch_digest='0'*64,binding_digest='0'*64,
                                request_key='unrelated-failure-'+str(day_value),input_sha256='0'*64,
                                status='FAILED',phase='VALIDATE',archive_path=str(root/('unrelated-'+str(day_value))))
                            self.assertTrue(daily_feed.unresolved_attempts(owner).filter(pk=a0.pk).exists())
                        transaction.set_rollback(True)
                    self.assertFalse(daily_feed.unresolved_attempts(owner).exists())
                print(('TERMINAL_SIXTH_POSTGRES_PASS ' if sixth else 'TERMINAL_FIFTH_POSTGRES_PASS ' if fifth else 'INTERRUPTED_FOURTH_POSTGRES_PASS ' if fourth else 'CAPTURED_RECOVERY_POSTGRES_PASS ')+'exact-inputs no-rewrite distinct-owners filesystem+late-commit-rollback reports+archive duplicate-denial')
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
