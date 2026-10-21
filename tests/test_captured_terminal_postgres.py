"""Changed terminal path only; prior hop-writer acceptance is reused.

The physical input is genuinely initialized/captured; six immutable reference
metadata rows are fixture setup, not a claim to rerun old writer campaigns.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib,json
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from django.db import connection,transaction
from mta.serialization import digest


@contextmanager
def metadata_setup():
    """Admin only for declared historical metadata fixtures in the owned DB."""
    if connection.settings_dict['NAME']!='vf_btr_terminal_admission_20261022':
        raise RuntimeError('Terminal metadata setup requires the owned scratch database')
    if not connection.get_autocommit():
        raise RuntimeError('Metadata fixture must not replace an active transaction')
    original=deepcopy(connection.settings_dict)
    connection.close()
    connection.settings_dict.update(USER='postgres',
        PASSWORD=Path('/proof-secrets/postgres_admin_password').read_text().strip())
    connection.settings_dict['OPTIONS']=dict(original['OPTIONS'],options='-c search_path=mta,public')
    try:
        with transaction.atomic(),connection.cursor() as cursor:
            cursor.execute('SET LOCAL session_replication_role=replica')
            yield cursor
    finally:
        connection.close()
        connection.settings_dict.clear();connection.settings_dict.update(original)


def prove_terminal(test,owner,physical,raw,release,root,pick):
    from mta.runtime.models import CalculationRun
    from mta.runtime.daily_feed_models import DailyFeedAttempt
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime import captured_input as ci
    from mta.runtime.input_v3 import _live_identity
    original=DailyFeedAttempt.objects.get(run=physical)
    previous=physical;cap=MdmDailyInputCapture.objects.get(run=physical)
    with metadata_setup() as cursor:
        cursor.execute('SELECT current_database(),oid::bigint FROM pg_database WHERE datname=current_database()')
        database,database_oid=cursor.fetchone()
        CalculationRun.objects.filter(pk=physical.pk).update(status='FAILED',failure={'fixture':'prior interrupted original'})
        DailyFeedAttempt.objects.filter(pk=original.pk).update(status='FAILED',error={'fixture':'prior interruption'})
        for index in range(1,7):
            run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date=physical.business_date,
                predecessor=physical.predecessor,execution_revision='prior-reference-fixture-'+str(index),
                evidence_mode='production',input_digest=physical.input_digest,input_payload={},
                production_manifest=deepcopy(physical.production_manifest),status='RUNNING' if index==6 else 'FAILED')
            fields={f.attname:getattr(original,f.attname) for f in original._meta.concrete_fields
                if f.name not in ('id','attempt_id','created_at','updated_at')}
            archive=root/'operations'/('prior-reference-fixture-'+str(index));archive.mkdir()
            (archive/'fixture.json').write_text(json.dumps({'prior_reference_metadata_only':index}))
            fields.update(run_id=run.pk,request_key=digest('prior-reference-fixture-'+str(index)),
                status=run.status,phase='CALCULATE',archive_path=str(archive),accepted_facts={},prepared_context={},error={})
            DailyFeedAttempt.objects.create(**fields)
            values={f.attname:getattr(cap,f.attname) for f in cap._meta.concrete_fields if f.name not in ('run','captured_at')}
            cap=MdmDailyInputCapture.objects.create(run=run,**dict(values,origin_id=previous.pk))
            identity=(_live_identity(run,reading=False) if run.status=='RUNNING' else
                dict(database_name=database,database_oid=database_oid,source_digest=owner.source.digest,
                     owner_kind='run',owner_id=str(run.pk)))
            value=dict(schema=ci.SCHEMA if index==1 else ci.SECOND,identity=identity,
                origin_run_id=str(previous.pk),origin_manifest_digest=previous.input_manifest_digest,
                content_digest=physical.input_digest,images={})
            if index>1:value.update(physical_origin_run_id=str(physical.pk),physical_origin_manifest_digest=physical.input_manifest_digest)
            run.input_payload=value;run.input_manifest_digest=digest(value)
            run.save(update_fields=['input_payload','input_manifest_digest'])
            previous=run
    def record(pk):
        attempt=DailyFeedAttempt.objects.get(run_id=pk)
        files={str(path):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in Path(attempt.archive_path).rglob('*') if path.is_file()}
        return json.dumps(dict(run=CalculationRun.objects.filter(pk=pk).values().get(),
            attempt=DailyFeedAttempt.objects.filter(pk=attempt.pk).values().get(),
            capture=MdmDailyInputCapture.objects.filter(run_id=pk).values().get(),files=files),sort_keys=True,default=str)
    from tests.test_captured_finite_postgres import prove_finite
    prove_finite(test,owner,previous,raw,release,root,pick,record)
