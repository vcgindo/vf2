"""Explicit disposable native PostgreSQL finite-continuation acceptance proof."""
import os
from pathlib import Path
import json
import hashlib
import unittest
from unittest.mock import patch


def prove_finite(test,owner,leaf,raw,release,root,pick,record):
    from django.db import connection,transaction,DatabaseError
    from mta.runtime import captured_input as ci,temporal,daily_feed
    from mta.runtime.models import CalculationRun
    from mta.runtime.daily_feed_models import DailyFeedAttempt
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.accepted_daily import epochs
    from mta.runtime.input_reader import read_input
    from mta.runtime.receipt_integrity import audit_input,audit_output,verify
    from mta.runtime.services import read_outputs
    import psycopg
    physical,rows,prefix=ci.finite_prefix(leaf)
    a=DailyFeedAttempt.objects.get(run=leaf)
    original=DailyFeedAttempt.objects.get(run=physical)
    before={row['run']['id']:record(row['run']['id']) for row in rows}
    def archives():
        return {str(path):hashlib.sha256(path.read_bytes()).hexdigest()
            for item in DailyFeedAttempt.objects.filter(run_id__in=before)
            for path in Path(item.archive_path).rglob('*') if path.is_file()}
    archive_before=archives()
    test.assertEqual(len(before),7)
    test.assertEqual(daily_feed.unresolved_attempts(owner).count(),7)
    expected=dict(run_id=str(leaf.pk),initialization_id=str(owner.pk),source_digest=owner.source.digest,
        input_digest=leaf.input_digest,input_manifest_digest=leaf.input_manifest_digest,
        daily_input_sha256=a.input_sha256,capture_cut=leaf.production_manifest['ingestion_preparation']['capture_cut'])
    spec=dict(prefix_digest=prefix,physical_run_id=str(physical.pk),
        physical_manifest_digest=physical.input_manifest_digest,physical_attempt_id=str(original.attempt_id),
        current_revision_cut=epochs(owner.pk))
    revision='native-finite-'+release['source_commit']
    def resume(name,*,pins=spec,execution=revision):
        return temporal.execute_day(day=None,profile=None,execution_revision=execution,
            _captured_retry=dict(origin_run_id=str(leaf.pk),expected=expected,
                archive_path=str(Path(a.archive_path).with_name(name)),finite_continuation=pins))
    def unchanged():
        test.assertEqual({key:record(key) for key in before},before)
        test.assertEqual((CalculationRun.objects.count(),MdmDailyInputCapture.objects.count()),(7,7))
        test.assertEqual(epochs(owner.pk),spec['current_revision_cut'])
        test.assertEqual(archives(),archive_before)
    for key in ('prefix_digest','physical_run_id','physical_manifest_digest','physical_attempt_id'):
        with test.assertRaises(ValueError):resume('bad-'+key,pins=dict(spec,**{key:'foreign'}))
        unchanged()
    with test.assertRaises(ValueError):resume('bad-cut',pins=dict(spec,current_revision_cut=[0]*5))
    with test.assertRaises(ValueError):resume('bad-release',execution='native-finite-'+'9'*40)
    options=connection.settings_dict
    with psycopg.connect(host=options['HOST'],port=options['PORT'],dbname=options['NAME'],
            user=options['USER'],password=options['PASSWORD'],autocommit=True) as competing:
        competing.execute('SELECT pg_advisory_lock(hashtextextended(%s,0))',
            ['vectorflow-daily-csv:'+str(owner.pk)])
        with test.assertRaisesRegex(ValueError,'Another daily worker owns'):resume('active-owner')
    for target,error in (('mta.runtime.daily_feed.atomic_json',OSError('finite receipt rollback')),
                         ('mta.runtime.capture_preparation.seal',psycopg.DataError('finite SQL rollback'))):
        with patch(target,side_effect=error),test.assertRaises(type(error)):resume('rollback-'+type(error).__name__)
        unchanged()
    commit=temporal.finish_run
    def commit_with_rollback(run,output,**kwargs):
        from copy import deepcopy
        with test.assertRaises(DatabaseError),transaction.atomic():
            commit(run,deepcopy(output),**kwargs)
            with connection.cursor() as cursor:cursor.execute('SELECT 1/0')
        run.refresh_from_db();test.assertEqual(run.status,'RUNNING')
        test.assertFalse(run.checkpoints.exists())
        return commit(run,output,**kwargs)
    with patch.object(temporal,'finish_run',side_effect=commit_with_rollback), \
            patch('mta.runtime.input_storage.save_input',side_effect=AssertionError('No physical payload copy')), \
            patch('mta.runtime.accepted_daily.read',side_effect=AssertionError('No CSV reparse')):
        result=resume('finite-continued')
    test.assertEqual(result.status,'SUCCEEDED')
    test.assertEqual(result.input_payload['schema'],ci.FINITE)
    test.assertEqual(read_input(result),raw)
    test.assertEqual(ci.origin(result).pk,physical.pk)
    test.assertEqual({key:record(key) for key in before},before)
    test.assertEqual(archives(),archive_before)
    test.assertEqual(DailyFeedAttempt.objects.get(run=result).recovery_origin_id,a.pk)
    audit_input(result);audit_output(result);verify(result)
    test.assertFalse(daily_feed.unresolved_attempts(owner).exists())
    test.assertEqual(daily_feed.predecessor(owner,(__import__('datetime').date(2026,10,19)).isoformat()).pk,result.pk)
    # Real SQL guards retain the stopped ancestry and child identity in all statuses.
    for model,pk,field,value in ((DailyFeedAttempt,a.pk,'status','FAILED'),
            (CalculationRun,leaf.pk,'status','FAILED'),
            (MdmDailyInputCapture,leaf.pk,'status','CONSUMED'),
            (DailyFeedAttempt,DailyFeedAttempt.objects.get(run=result).pk,'recovery_origin_id',None)):
        with test.assertRaises(DatabaseError),transaction.atomic():model.objects.filter(pk=pk).update(**{field:value})
    with test.assertRaises(ValueError):resume('second-sibling')
    with test.assertRaises(ValueError):ci.manifest(result,result)
    new=DailyFeedAttempt.objects.get(run=result)
    from mta.presentation import daily_publication
    with patch.object(daily_publication,'prepare_reporting_generation',side_effect=RuntimeError('report-only failure')), \
            patch.object(temporal,'calculate_day',side_effect=AssertionError('No recalculation')):
        with test.assertRaisesRegex(RuntimeError,'report-only failure'):
            daily_feed.execute(new.attempt_id,root/'binding.json',pick_root=pick,resume=True)
    result.refresh_from_db();test.assertEqual(result.status,'SUCCEEDED')
    test.assertFalse(daily_feed.unresolved_attempts(owner).exists())
    with patch.object(temporal,'calculate_day',side_effect=AssertionError('No recalculation')):
        report=daily_feed.execute(new.attempt_id,root/'binding.json',pick_root=pick,resume=True)
    test.assertEqual(report['status'],'PREPARED')
    from mta.application.native_input_archive import open_archive
    import zipfile
    stream,_=open_archive(result)
    with stream,zipfile.ZipFile(stream) as archive:
        exported=json.loads(archive.read('manifest.json'))
    test.assertEqual(exported['input_digest'],physical.input_digest)
    for day in ('2026-10-17','2026-10-18'):
        with transaction.atomic():
            other=DailyFeedAttempt.objects.create(initialization=owner,business_date=day,batch_id='foreign',
                batch_digest='0'*64,binding_digest='0'*64,input_sha256='0'*64,request_key='foreign-'+day,
                status='FAILED',phase='VALIDATE',archive_path=str(root/('foreign-'+day)))
            test.assertTrue(daily_feed.unresolved_attempts(owner).filter(pk=other.pk).exists())
            transaction.set_rollback(True)
    test.assertEqual({key:record(key) for key in before},before)
    read_outputs(result)
    print('FINITE_NATIVE_POSTGRES_PASS exact7 originals preserved physical input/readback/archives rollback guards reportrebuild successor unresolved')


@unittest.skipUnless(os.environ.get('VF_CAPTURED_FINITE_PROOF')=='1','Explicit disposable PostgreSQL finite proof required')
class FiniteNativePostgresTests(unittest.TestCase):
    def test_native_six_prefix_finite_continuation(self):
        from tests import test_captured_recovery_postgres as existing
        with patch.dict(os.environ,VF_CAPTURED_RECOVERY_PROOF='1'):
            existing.CapturedRecoveryPostgresTests.test_exact_capture_reuse_rollback_and_normal_writer(self)
