"""One CSV attempt through existing native execution and report publication.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import contextmanager
from datetime import date
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import uuid
import logging
from time import perf_counter

from django.db import connection, transaction
from mta.serialization import digest, storage
from mta.application.production_csv import assemble, batch_contract, CsvIntakeError
from mta.application.production_csv_files import contained, regular, load_binding, snapshot, decode_json
from mta.runtime.daily_feed_models import DailyFeedAttempt
from mta.runtime.models import ProductionInitialization, CalculationRun
from mta.runtime.day_opening import latest_predecessor
from mta.application.streamed_input import JsonInputFile
from mta.application.stage_observation import observed, stage as observe_stage
logger = logging.getLogger(__name__)


def file_identity(path):
    checksum = hashlib.sha256()
    size = 0
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
            size += len(block)
    return dict(bytes=size, sha256=checksum.hexdigest())


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(storage(value), stream, sort_keys=True, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def job_lock(owner):
    if connection.in_atomic_block:
        raise ValueError('CSV coordinator owns its transaction boundaries')
    key = 'vectorflow-daily-csv:' + str(owner.pk)
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0)),pg_backend_pid()', [key])
        held, pid = cursor.fetchone()
    if not held:
        raise ValueError('Another daily worker owns this initialization')
    def check():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()=%s AND EXISTS(SELECT 1 FROM pg_locks WHERE "
                "pid=pg_backend_pid() AND locktype='advisory' AND granted AND objsubid=1 "
                "AND classid=((hashtextextended(%s,0)>>32)&4294967295)::oid "
                "AND objid=(hashtextextended(%s,0)&4294967295)::oid)", [pid, key, key])
            if cursor.fetchone() != (True,):
                raise ValueError('Daily worker lock/session was lost; automatic takeover is forbidden')
    failed = False
    try:
        yield check
    except BaseException:
        failed = True
        raise
    finally:
        # Never reconnect merely to unlock a dead session, or mask the actual
        # daily failure with a second exception from its lost connection.
        if (not connection.needs_rollback and connection.connection is not None
                and not connection.connection.closed):
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))', [key])
            except Exception:
                if not failed:
                    raise


def binding_owner(filename):
    binding = load_binding(filename)
    owner = ProductionInitialization.objects.select_related('source').get(pk=uuid.UUID(binding['initialization_id']))
    if (owner.source.digest != binding['source_digest']
            or owner.configuration_digest != binding['configuration_digest']
            or owner.input_sha256 != binding['opening_sha256']):
        raise ValueError('CSV onboarding binding differs from this initialized instance')
    return binding, owner


def _batch(source, binding, business_date, root):
    source = contained(source, root)
    regular(source / 'READY', root)
    raw = regular(source / 'batch.json', root).read_bytes()
    batch = decode_json(raw)
    batch_contract(batch, binding, business_date)
    names = {'READY', 'batch.json'} | {name for name, state in batch['feeds'].items() if state == 'PRESENT'}
    if {p.name for p in source.iterdir()} != names:
        raise ValueError('Batch directory differs from its explicit file roster')
    payloads, receipts = {}, {}
    for name in sorted(names):
        path = regular(source / name, root)
        receipts[name] = file_identity(path)
        if name.endswith('.csv'):
            payloads[name] = path
    manifest = dict(schema='vectorflow-csv-snapshot-v1', files=receipts)
    manifest['digest'] = digest(manifest)
    return batch, payloads, manifest


def predecessor(owner, business_date):
    today = date.fromisoformat(business_date)
    candidates = CalculationRun.objects.filter(kind='DAILY_CHAIN', status='SUCCEEDED',
        business_date__lt=today, mdm_input_capture__source=owner.source).order_by('-business_date')[:2]
    return latest_predecessor(candidates)


def _parameters(binding, owner, parent, revision, pick_root):
    return dict(initialization_id=owner.pk, source_digest=binding['source_digest'],
        configuration_digest=binding['configuration_digest'], execution_revision=revision,
        pick_output_root=str(pick_root), predecessor_id=parent.pk if parent else None,
        predecessor_output_digest=parent.output_digest if parent else None)


def _native_inspect(raw, sha, parameters):
    from mta.runtime.production_daily import inspect_execution
    from mta.runtime.production_preflight import require
    report, *_ = inspect_execution(raw, sha, **parameters)
    require(report, 'day')
    return report


def inspect(binding_file, source, business_date, *, input_root, pick_root):
    binding, owner = binding_owner(binding_file)
    batch, payloads, manifest = _batch(source, binding, business_date, input_root)
    parent = predecessor(owner, business_date)
    raw, positions = assemble(batch, binding, payloads, first_day=parent is None)
    sha = hashlib.sha256(raw).hexdigest()
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION READ ONLY')
        report = _native_inspect(raw, sha, _parameters(binding, owner, parent,
            'csv-v1-' + manifest['digest'], pick_root))
    return dict(status='ELIGIBLE_NOT_EXECUTED', business_date=business_date,
        input_sha256=sha, batch_digest=manifest['digest'],
        records={name:len(rows) for name, rows in positions.items()}, preflight=report)


def result(attempt):
    attempt.refresh_from_db()
    run = attempt.run
    value = dict(attempt_id=str(attempt.attempt_id), business_date=str(attempt.business_date),
        status=attempt.status, phase=attempt.phase, archive_path=attempt.archive_path,
        run_id=str(run.pk) if run else None, output_digest=run.output_digest if run else None,
        run_status=run.status if run else None, error=attempt.error)
    value['business_rejections_recorded'] = (Path(attempt.archive_path) / 'business-rejections.csv').exists()
    return value


def save(attempt, phase, status=None, error=None, *, _persist=True):
    attempt.phase = phase
    if status:
        attempt.status = status
    attempt.error = error or {}
    if _persist:
        attempt.save(update_fields=['phase', 'status', 'error', 'updated_at'])
    value = result(attempt)
    root = Path(attempt.archive_path)
    root.mkdir(parents=True, exist_ok=True)
    atomic_json(root / 'result.json', value)
    with (root / 'phases.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(value, sort_keys=True) + '\n')
    return value


def diagnostics(attempt, error):
    issues = getattr(error, 'issues', None)
    if issues is None and hasattr(error, 'report'):
        atomic_json(Path(attempt.archive_path) / 'preflight.json', error.report)
    if issues:
        filename, columns = 'validation-errors.csv', ('file', 'record', 'line', 'column', 'message')
        records = issues
    else:
        filename, columns = 'business-rejections.csv', (
            'SKUCode', 'WhCode', 'RejectionDate', 'ReasonCode', 'ReasonDescription')
        records = getattr(error, 'rejections', [])
    if records:
        target = Path(attempt.archive_path) / filename
        if target.exists():
            target = target.with_name(target.stem + '-' + uuid.uuid4().hex + target.suffix)
        with target.open('x', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            from mta.application.operational_inputs import _cell
            writer.writerows({key:_cell(value) for key,value in row.items()} for row in records)


def _finite_resolved_ancestors(owner):
    """Only an authenticated operational commit resolves the preserved chain."""
    from mta.runtime.captured_input import FINITE, TERMINAL, RETRY, FINAL, finite_origin, finite_prefix, terminal_origin, terminal_prefix, retry_prefix, final_prefix
    resolved=[]
    candidates=CalculationRun.objects.filter(kind='DAILY_CHAIN',status='SUCCEEDED',
        evidence_mode='production',input_payload__schema__in=(FINITE,TERMINAL,RETRY,FINAL),production_manifest__version=3,
        csv_attempt__initialization=owner,
        csv_attempt__status__in=('COMMITTED','PREPARED','PUBLISHED'),
        mdm_input_capture__status='CONSUMED')
    for run in candidates.iterator():
        terminal=run.input_payload["schema"] in (TERMINAL,RETRY,FINAL)
        (terminal_origin if terminal else finite_origin)(run)
        _,rows,_=(final_prefix if run.input_payload["schema"]==FINAL else retry_prefix if run.input_payload["schema"]==RETRY else terminal_prefix if terminal else finite_prefix)(run.mdm_input_capture.origin.run)
        resolved.extend(row['run']['id'] for row in rows)
    return resolved


def unresolved_attempts(owner):
    """A failed day needs its own retry; v3 report readiness is not day admission."""
    from django.db.models import Exists, OuterRef, Q
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.captured_input import SECOND
    path=(Q(origin__run_id=OuterRef('run_id')) |
        Q(origin__origin__run_id=OuterRef('run_id'),origin__run__status='FAILED',
          origin__run__input_payload__schema__in=('fresh-captured-input-reference-v1',SECOND),
          run__input_payload__schema=SECOND) |
        Q(origin__origin__origin__run_id=OuterRef('run_id'),
          origin__run__status='FAILED',origin__origin__run__status='FAILED',
          origin__run__input_payload__schema=SECOND,
          origin__origin__run__input_payload__schema='fresh-captured-input-reference-v1',
          run__input_payload__schema=SECOND) |
        # Exact fourth-wrapper prefix, not a blanket resolution of old errors.
        Q(origin__origin__origin__run_id=OuterRef('run_id'),
          origin__run__status='FAILED',origin__origin__run__status='FAILED',
          origin__run__input_payload__schema=SECOND,
          origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__run__input_payload__schema='fresh-captured-input-reference-v1',
          run__input_payload__schema=SECOND) |
        Q(origin__origin__origin__origin__run_id=OuterRef('run_id'),
          origin__run__status='FAILED',origin__origin__run__status='FAILED',
          origin__origin__origin__run__status='FAILED',
          origin__run__input_payload__schema=SECOND,
          origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__run__input_payload__schema='fresh-captured-input-reference-v1',
          run__input_payload__schema=SECOND) |
        # Exact fifth-wrapper prefix only; never resolve a sibling or foreign failure.
        Q(origin__origin__origin__run_id=OuterRef('run_id'),
          origin__run__status='FAILED',
          origin__origin__run__status='FAILED',
          origin__origin__origin__run__status='FAILED',
          origin__origin__origin__origin__run__status='FAILED',
          origin__run__input_payload__schema=SECOND,
          origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__origin__run__input_payload__schema='fresh-captured-input-reference-v1',
          run__input_payload__schema=SECOND) |
        Q(origin__origin__origin__origin__run_id=OuterRef('run_id'),
          origin__run__status='FAILED',
          origin__origin__run__status='FAILED',
          origin__origin__origin__run__status='FAILED',
          origin__origin__origin__origin__run__status='FAILED',
          origin__run__input_payload__schema=SECOND,
          origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__origin__run__input_payload__schema='fresh-captured-input-reference-v1',
          run__input_payload__schema=SECOND) |
        Q(origin__origin__origin__origin__origin__run_id=OuterRef('run_id'),
          origin__run__status='FAILED',
          origin__origin__run__status='FAILED',
          origin__origin__origin__run__status='FAILED',
          origin__origin__origin__origin__run__status='FAILED',
          origin__run__input_payload__schema=SECOND,
          origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__origin__run__input_payload__schema='fresh-captured-input-reference-v1',
          run__input_payload__schema=SECOND) |
        # Exact terminal-sixth prefix; no seventh/sibling/foreign resolution.
        Q(origin__origin__origin__run_id=OuterRef('run_id'),
          origin__run__status='FAILED',
          origin__origin__run__status='FAILED',
          origin__origin__origin__run__status='FAILED',
          origin__origin__origin__origin__run__status='FAILED',
          origin__origin__origin__origin__origin__run__status='FAILED',
          origin__run__input_payload__schema=SECOND,
          origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__origin__origin__run__input_payload__schema='fresh-captured-input-reference-v1',
          run__input_payload__schema=SECOND) |
        Q(origin__origin__origin__origin__run_id=OuterRef('run_id'),
          origin__run__status='FAILED',
          origin__origin__run__status='FAILED',
          origin__origin__origin__run__status='FAILED',
          origin__origin__origin__origin__run__status='FAILED',
          origin__origin__origin__origin__origin__run__status='FAILED',
          origin__run__input_payload__schema=SECOND,
          origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__origin__origin__run__input_payload__schema='fresh-captured-input-reference-v1',
          run__input_payload__schema=SECOND) |
        Q(origin__origin__origin__origin__origin__run_id=OuterRef('run_id'),
          origin__run__status='FAILED',
          origin__origin__run__status='FAILED',
          origin__origin__origin__run__status='FAILED',
          origin__origin__origin__origin__run__status='FAILED',
          origin__origin__origin__origin__origin__run__status='FAILED',
          origin__run__input_payload__schema=SECOND,
          origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__origin__origin__run__input_payload__schema='fresh-captured-input-reference-v1',
          run__input_payload__schema=SECOND) |
        Q(origin__origin__origin__origin__origin__origin__run_id=OuterRef('run_id'),
          origin__run__status='FAILED',
          origin__origin__run__status='FAILED',
          origin__origin__origin__run__status='FAILED',
          origin__origin__origin__origin__run__status='FAILED',
          origin__origin__origin__origin__origin__run__status='FAILED',
          origin__run__input_payload__schema=SECOND,
          origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__origin__run__input_payload__schema=SECOND,
          origin__origin__origin__origin__origin__run__input_payload__schema='fresh-captured-input-reference-v1',
          run__input_payload__schema=SECOND))
    completed = MdmDailyInputCapture.objects.filter(path,
        run__input_digest=OuterRef('run__input_digest'),
        status='CONSUMED',run__status='SUCCEEDED',run__business_date=OuterRef('business_date'),
        run__csv_attempt__initialization=owner,run__csv_attempt__status='PUBLISHED')
    return DailyFeedAttempt.objects.filter(initialization=owner).exclude(
        status__in=('PUBLISHED','REJECTED')).annotate(_resolved=Exists(completed)).exclude(
        status='FAILED',_resolved=True).exclude(run__status='SUCCEEDED',run__production_manifest__version=3
        ).exclude(run_id__in=_finite_resolved_ancestors(owner))


def _revalidation_key(origin):
    return digest(dict(contract='fresh-csv-revalidation-v1', origin_attempt=str(origin.attempt_id),
                       canonical_request_key=origin.request_key))


def _revalidation_origin_digest(origin):
    names=('attempt_id','initialization_id','business_date','batch_id','request_key','batch_digest',
           'binding_digest','input_sha256','predecessor_id','predecessor_output_digest','status','phase')
    return digest(dict(identity={name:str(getattr(origin,name)) for name in names},error=origin.error))


def _verify_revalidation(attempt, origin=None, *, historical=False):
    receipt_path=Path(attempt.archive_path)/'revalidation.json'
    if origin is None:
        candidates=DailyFeedAttempt.objects.filter(initialization_id=attempt.initialization_id,
            business_date=attempt.business_date,status='REJECTED')
        origin=next((row for row in candidates if _revalidation_key(row)==attempt.request_key),None)
        if origin is None:
            if receipt_path.exists():
                raise ValueError('Revalidation origin is absent or changed')
            return
    receipt=decode_json(regular(receipt_path,Path(attempt.archive_path)).read_bytes())
    from release.native_identity import require_current
    if historical:
        from mta.runtime.ingestion_admission import _admit
        with connection.cursor() as cursor:
            _admit(cursor,str(attempt.initialization_id),receipt['target_release'],pending=True)
        expected_release=receipt['target_release']
    else:
        expected_release=require_current()
    if (receipt.get('contract')!='fresh-csv-revalidation-v1'
            or receipt.get('origin_attempt')!=str(origin.attempt_id)
            or receipt.get('origin_digest')!=_revalidation_origin_digest(origin)
            or receipt.get('replacement_attempt')!=str(attempt.attempt_id)
            or receipt.get('canonical_request_key')!=origin.request_key
            or receipt.get('original_release')!=origin.initialization.source.receipt['owned_namespace']['release_identity']
            or attempt.request_key!=_revalidation_key(origin)
            or receipt.get('target_release')!=expected_release
            or any(str(getattr(attempt,k))!=str(getattr(origin,k)) for k in (
                'initialization_id','business_date','batch_id','batch_digest','binding_digest',
                'input_sha256','predecessor_id','predecessor_output_digest'))):
        raise ValueError('Revalidation origin, release or frozen identity differs')


def _check_rejected_order_origin(origin, owner, binding, manifest, business_date, selection_file):
    if (origin.status!='REJECTED' or origin.phase!='VALIDATE' or origin.run_id
            or str(origin.initialization_id)!=str(owner.pk) or str(origin.business_date)!=business_date
            or origin.accepted_facts or origin.prepared_context
            or origin.binding_digest!=binding['_binding_digest'] or origin.batch_digest!=manifest['digest']
            or origin.error.get('type')!='PreflightError'):
        raise ValueError('Resume requires the preserved unexecuted order preflight rejection')
    root=Path(origin.archive_path)
    report=decode_json(regular(root/'preflight.json',root).read_bytes())
    expected=dict(category='input',code='CONTRACT_INVALID',message='Order source tables must be row lists',
        owner='r1_order_input.validate_order_input',path='/day/order_feed',stages=['day'])
    if ([q for q in report.get('issues',[]) if 'day' in q.get('stages',[])]!=[expected]
            or json.dumps(report,sort_keys=True)[:2000]!=origin.error.get('message')):
        raise ValueError('Resume does not match the preserved order preflight diagnostic')
    original=root/'original'
    frozen=decode_json(regular(original/'snapshot.json',root).read_bytes())
    if (frozen!=manifest or frozen['digest']!=digest({k:v for k,v in frozen.items() if k!='digest'})
            or {p.name for p in original.iterdir()}!=set(frozen['files'])|{'snapshot.json'}
            or any(file_identity(regular(original/name,root))!=identity for name,identity in frozen['files'].items())
            or file_identity(regular(root/'native-day.json',root))['sha256']!=origin.input_sha256):
        raise ValueError('Preserved rejected input bytes differ')
    parent=predecessor(owner,business_date)
    selected=decode_json(Path(selection_file).read_bytes())
    if (parent is None or str(parent.pk)!=str(origin.predecessor_id)
            or parent.output_digest!=origin.predecessor_output_digest
            or selected.get('run_id')!=str(parent.pk) or selected.get('output_digest')!=parent.output_digest
            or selected.get('initialization_id')!=str(owner.pk)):
        raise ValueError('Rejected staging predecessor or selected publication changed')
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    if MdmDailyInputCapture.objects.filter(source=owner.source,run__business_date=business_date).exists():
        raise ValueError('Rejected date already has a captured calculation')
    from mta.runtime import batch_storage
    with connection.cursor() as cursor:
        for name in batch_storage.TABLES:
            cursor.execute('SELECT EXISTS(SELECT 1 FROM '+batch_storage.table_sql(name)+
                           ' WHERE vf_attempt_id=%s LIMIT 1)',[origin.attempt_id])
            if cursor.fetchone()!=(False,):
                raise ValueError('Rejected attempt has accepted staging rows')
    from release.native_identity import require_current
    from mta.runtime.ingestion_admission import preparation_source
    target=require_current()
    original_release=owner.source.receipt['owned_namespace']['release_identity']
    if (target['implementation_sha256']==original_release['implementation_sha256']
            or preparation_source(owner.source.digest) is None):
        raise ValueError('Rejected staging requires an admitted corrected native release')
    return dict(contract='fresh-csv-revalidation-v1',origin_attempt=str(origin.attempt_id),
        canonical_request_key=origin.request_key,origin_digest=_revalidation_origin_digest(origin),
        original_release=original_release,target_release=target)


def _capture_retry_key(origin, release):
    return digest(dict(contract='csv-frozen-retry-v1',origin_run=str(origin.run_id),
        input_digest=origin.run.input_digest,target_release=release['manifest_sha256']))


def _capture_origin(origin):
    failure=dict(type='ValueError',message='DailyConsumption must be an ordered row table')
    if (origin.status!='FAILED' or origin.phase!='VALIDATED' or not origin.run_id
            or origin.run.status!='FAILED' or origin.run.failure!=failure or origin.error!=failure
            or not origin.accepted_facts or not origin.prepared_context):
        raise ValueError('Resume requires the preserved failed DailyConsumption capture')
    _verify_revalidation(origin,historical=True)
    capture=origin.run.mdm_input_capture
    if capture.status!='CAPTURED' or capture.source_id!=origin.initialization.source_id:
        raise ValueError('Failed retry capture owner or status differs')
    return capture


def _verify_capture_retry(attempt, origin=None):
    path=Path(attempt.archive_path)/'capture-retry.json'
    from release.native_identity import require_current
    if not path.exists():
        candidates=DailyFeedAttempt.objects.filter(initialization_id=attempt.initialization_id,
            business_date=attempt.business_date,status='FAILED').select_related('run')
        for row in candidates:
            if row.run_id and _capture_retry_key(row,require_current())==attempt.request_key:
                raise ValueError('Frozen retry lineage receipt is absent')
        return None
    receipt=decode_json(regular(path,Path(attempt.archive_path)).read_bytes())
    if origin is None:
        origin=DailyFeedAttempt.objects.select_related('run','initialization__source').get(
            attempt_id=uuid.UUID(receipt['origin_attempt']))
    capture=_capture_origin(origin)
    target=require_current()
    old_receipt=decode_json(regular(Path(origin.archive_path)/'revalidation.json',
                                   Path(origin.archive_path)).read_bytes())
    if (receipt.get('contract')!='csv-frozen-retry-v1'
            or receipt.get('origin_attempt')!=str(origin.attempt_id)
            or receipt.get('origin_attempt_digest')!=_revalidation_origin_digest(origin)
            or receipt.get('origin_run')!=str(origin.run_id)
            or receipt.get('origin_input_digest')!=origin.run.input_digest
            or receipt.get('origin_manifest_digest')!=origin.run.input_manifest_digest
            or receipt.get('capture_request_digest')!=capture.request_digest
            or receipt.get('capture_revision_digest')!=capture.revision_digest
            or receipt.get('historical_receipt_digest')!=digest(old_receipt)
            or receipt.get('target_release')!=target
            or receipt.get('replacement_attempt')!=str(attempt.attempt_id)
            or attempt.request_key!=_capture_retry_key(origin,target)
            or receipt.get('execution_revision')!='csv-retry-v1-'+attempt.request_key
            or any(str(getattr(attempt,k))!=str(getattr(origin,k)) for k in (
                'initialization_id','business_date','batch_id','batch_digest','binding_digest',
                'input_sha256','predecessor_id','predecessor_output_digest'))):
        raise ValueError('Frozen retry lineage, release or input identity differs')
    return receipt


def _resume_failed_capture(origin, owner, binding, manifest, root, *, pick_root, selection_file, lock_check):
    capture=_capture_origin(origin)
    from release.native_identity import require_current
    from mta.runtime.ingestion_admission import preparation_source
    target=require_current()
    old_root=Path(origin.archive_path)
    old_receipt=decode_json(regular(old_root/'revalidation.json',old_root).read_bytes())
    if (str(origin.initialization_id)!=str(owner.pk) or origin.binding_digest!=binding['_binding_digest']
            or origin.batch_digest!=manifest['digest']
            or target['manifest_sha256']==old_receipt['target_release']['manifest_sha256']
            or preparation_source(owner.source.digest) is None):
        raise ValueError('Frozen retry requires unchanged input and an admitted corrected release')
    key=_capture_retry_key(origin,target)
    existing=DailyFeedAttempt.objects.filter(request_key=key).first()
    if existing:
        _verify_capture_retry(existing,origin)
        if (existing.status in ('FAILED','REJECTED') or existing.phase=='VALIDATE'
                or existing.run_id and existing.run.status!='SUCCEEDED'
                or existing.phase!='VALIDATED' and not existing.run_id):
            raise ValueError('Frozen retry already attempted; reconcile native state before another action')
        import shutil
        shutil.rmtree(root)  # Only this newly created, unregistered snapshot.
        return result(existing)
    from mta.runtime.captured_recovery import _uncommitted
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    _uncommitted(origin.run)
    leaves=list(MdmDailyInputCapture.objects.filter(source_id=capture.source_id,status='CAPTURED',
        retries__isnull=True).values_list('run_id',flat=True))
    parent=predecessor(owner,str(origin.business_date))
    from mta.presentation.native_selection import read as read_selection
    selected=read_selection(selection_file)
    if (leaves!=[origin.run_id] or parent is None or parent.pk!=origin.predecessor_id
            or parent.output_digest!=origin.predecessor_output_digest
            or selected['run_id']!=str(parent.pk) or selected['output_digest']!=parent.output_digest
            or selected['initialization_id']!=str(owner.pk)
            or parent.successors.filter(status__in=('RUNNING','SUCCEEDED')).exists()
            or unresolved_attempts(owner).exclude(pk=origin.pk).exists()):
        raise ValueError('Frozen retry leaf, predecessor, selection or competing operation changed')
    from mta.runtime.input_reader import read_input
    from mta.runtime.temporal import resolved_pick_root
    if read_input(origin.run,components=('pick_output_root',)).get('pick_output_root')!=resolved_pick_root(pick_root):
        raise ValueError('Frozen retry Pick root changed')
    frozen=decode_json(regular(old_root/'original'/'snapshot.json',old_root).read_bytes())
    if (frozen!=manifest or frozen['digest']!=digest({k:v for k,v in frozen.items() if k!='digest'})
            or any(file_identity(regular(old_root/'original'/name,old_root))!=meta
                   for name,meta in frozen['files'].items())
            or file_identity(regular(old_root/'native-day.json',old_root))['sha256']!=origin.input_sha256):
        raise ValueError('Frozen retry original bytes differ')
    import shutil
    shutil.copyfile(old_root/'native-day.json',root/'native-day.json')
    if (old_root/'record-lines.json').is_file():
        shutil.copyfile(regular(old_root/'record-lines.json',old_root),root/'record-lines.json')
    identity=uuid.UUID(root.name)
    receipt=dict(contract='csv-frozen-retry-v1',origin_attempt=str(origin.attempt_id),
        origin_attempt_digest=_revalidation_origin_digest(origin),origin_run=str(origin.run_id),
        origin_input_digest=origin.run.input_digest,origin_manifest_digest=origin.run.input_manifest_digest,
        capture_request_digest=capture.request_digest,capture_revision_digest=capture.revision_digest,
        historical_receipt_digest=digest(old_receipt),target_release=target,replacement_attempt=str(identity),
        execution_revision='csv-retry-v1-'+key,pick_root=resolved_pick_root(pick_root))
    atomic_json(root/'capture-retry.json',receipt)
    lock_check()
    retry=DailyFeedAttempt.objects.create(attempt_id=identity,initialization=owner,
        business_date=origin.business_date,batch_id=origin.batch_id,request_key=key,
        batch_digest=origin.batch_digest,binding_digest=origin.binding_digest,input_sha256=origin.input_sha256,
        predecessor=parent,predecessor_output_digest=parent.output_digest,archive_path=str(root),
        status='RUNNING',phase='VALIDATED',certification_id=origin.certification_id,master_revision_id=origin.master_revision_id)
    return save(retry,'VALIDATED')


@observed('csv_staging', owner_parameter='business_date')
def stage(binding_file, source, business_date, *, input_root, work_root, pick_root, fullkit=None,
          resume=False, selection_file='/var/lib/vectorflow/selection.json'):
    binding, owner = binding_owner(binding_file)
    identity=uuid.uuid4()
    root=Path(work_root).absolute()/str(identity)
    root.mkdir(parents=True,exist_ok=False)
    try:
        if fullkit is not None:
            from mta.runtime.intake_diagnostics import fullkit_request,capture_fullkit,FullkitUnavailable
            config,clock=fullkit_request(fullkit,initialization=owner,business_date=business_date,
                source=source,input_root=input_root)
            with job_lock(owner):
                diagnostic,_result=capture_fullkit(owner,config,business_date=business_date,
                    run_datetime=clock,capture_root=root/'fullkit-originals')
            if diagnostic is not None:
                from mta.runtime.diagnostic_publication import publish_failure
                try:publish_failure(diagnostic.pk,output_root=root)
                except Exception as publication_error:
                    raise FullkitUnavailable(diagnostic.pk) from publication_error
                raise FullkitUnavailable(diagnostic.pk)
        # Hash originals once, while making the immutable attempt snapshot.
        batch,manifest=snapshot(source,root/'original',input_root)
        batch_contract(batch,binding,business_date)
    except Exception as error:
        # Malformed batch declarations have no usable business identity. Preserve
        # a filesystem intake receipt without fabricating a database day/run.
        copied = {}
        try:
            import shutil
            safe = contained(source, input_root)
            original = root / 'original'
            original.mkdir(exist_ok=True)
            for item in safe.iterdir():
                item = regular(item, input_root)
                target = original / item.name
                if not target.exists():
                    with item.open('rb') as incoming, target.open('xb') as outgoing:
                        shutil.copyfileobj(incoming, outgoing)
                copied[item.name] = file_identity(target)['sha256']
        except (OSError, ValueError) as capture_error:
            copied['capture_error'] = str(capture_error)[:300]
        atomic_json(root / 'result.json', dict(status='REJECTED', phase='BATCH',
            business_date=business_date, preserved=copied,
            error=dict(type=type(error).__name__, message=str(error)[:2000])))
        raise
    request_key = digest(dict(initialization=str(owner.pk), date=business_date,
                              binding=binding['_binding_digest'], batch=manifest['digest']))
    with job_lock(owner) as lock_check:
        old = DailyFeedAttempt.objects.filter(request_key=request_key).first()
        revalidation=None
        if resume and old is None and DailyFeedAttempt.objects.filter(initialization=owner,
                business_date=business_date,status='REJECTED').exists():
            raise ValueError('Resume batch differs from the preserved rejection')
        if old:
            if resume and old.status=='REJECTED':
                request_key=_revalidation_key(old)
                replacement=DailyFeedAttempt.objects.filter(request_key=request_key).first()
                if replacement:
                    if replacement.status=='FAILED':
                        return _resume_failed_capture(replacement,owner,binding,manifest,root,
                            pick_root=pick_root,selection_file=selection_file,lock_check=lock_check)
                    _verify_revalidation(replacement,old)
                    if (replacement.status in ('FAILED','REJECTED') or replacement.phase=='VALIDATE'
                            or replacement.run_id and replacement.run.status!='SUCCEEDED'
                            or replacement.phase!='VALIDATED' and not replacement.run_id):
                        raise ValueError('Replacement requires diagnosis; automatic retry is forbidden')
                    import shutil
                    shutil.rmtree(root)  # Only this newly created, unregistered snapshot.
                    return result(replacement)
                revalidation=_check_rejected_order_origin(old,owner,binding,manifest,business_date,selection_file)
                revalidation['replacement_attempt']=str(identity)
            else:
                import shutil
                shutil.rmtree(root)  # Only this newly created, unregistered snapshot.
                return result(old)
        if unresolved_attempts(owner).exists():
            raise ValueError('An unfinished daily attempt requires reconciliation/resume first')
        if CalculationRun.objects.filter(business_date=business_date,
                mdm_input_capture__source=owner.source, status__in=('RUNNING', 'SUCCEEDED')).exists():
            raise ValueError('This initialized date already has a running or committed native day')
        attempt = DailyFeedAttempt.objects.create(attempt_id=identity, initialization=owner,
            business_date=business_date, batch_id=batch['batch_id'], request_key=request_key,
            batch_digest=manifest['digest'], binding_digest=binding['_binding_digest'],
            archive_path=str(root))
        try:
            if revalidation:
                atomic_json(root/'revalidation.json',revalidation)
            Path(pick_root).mkdir(parents=True, exist_ok=True)
            frozen=batch
            parent = predecessor(owner, business_date)
            payloads = {name:regular(root / 'original' / name, root)
                        for name, state in frozen['feeds'].items() if state == 'PRESENT'}
            raw, positions = assemble(frozen, binding, payloads, first_day=parent is None,
                                      output_file=root / 'native-day.json', _transfer=True)
            if revalidation and (raw.sha256!=old.input_sha256 or str(parent.pk)!=str(old.predecessor_id)
                                 or parent.output_digest!=old.predecessor_output_digest):
                raise ValueError('Revalidated native input or predecessor differs')
            atomic_json(root / 'record-lines.json', positions)
            attempt.input_sha256 = raw.sha256
            attempt.predecessor = parent
            attempt.predecessor_output_digest = parent.output_digest if parent else ''
            attempt.save(update_fields=['input_sha256', 'predecessor', 'predecessor_output_digest', 'updated_at'])
            from mta.runtime.daily_preparation import prepare
            from mta.runtime.ingestion_admission import preparation_source
            with observe_stage('native_daily_validation'):
                raw = prepare(raw, attempt.input_sha256)
            with observe_stage('staging_readiness'):
                ready = preparation_source(owner.source.digest)
            arguments = _parameters(binding, owner, parent, 'csv-v1-' + attempt.batch_digest, pick_root)
            report = _native_inspect(raw, attempt.input_sha256, arguments)
            atomic_json(root / 'preflight.json', report)
            if ready is not None:
                from mta.runtime.accepted_daily import seal
                seal(attempt, raw, arguments, ready)
            return save(attempt, 'VALIDATED', _persist=ready is None)
        except Exception as error:
            root.mkdir(parents=True, exist_ok=True)
            diagnostics(attempt, error)
            save(attempt, 'VALIDATE', 'REJECTED', dict(type=type(error).__name__, message=str(error)[:2000]))
            raise


def _bound_attempt(attempt_id, binding):
    attempt = DailyFeedAttempt.objects.select_related('initialization', 'run', 'predecessor').get(
        attempt_id=uuid.UUID(str(attempt_id)))
    if (str(attempt.initialization_id) != binding['initialization_id']
            or attempt.binding_digest != binding['_binding_digest']):
        raise ValueError('Attempt does not belong to this unchanged onboarding binding')
    _verify_revalidation(attempt,historical=attempt.status=='FAILED')
    _verify_capture_retry(attempt)
    return attempt


@observed('csv_execution', owner_parameter='attempt_id')
def execute(attempt_id, binding_file, *, pick_root, resume=False):
    binding, owner = binding_owner(binding_file)
    with job_lock(owner) as check:
        attempt = _bound_attempt(attempt_id, binding)
        root = Path(attempt.archive_path)
        if attempt.status == 'PUBLISHED':
            return result(attempt)
        if attempt.status in ('FAILED', 'REJECTED'):
            raise ValueError('Failed/rejected native attempt cannot be automatically retried')
        if attempt.phase not in ('VALIDATED',) and not resume:
            raise ValueError('Existing attempt requires explicit publication/serving resume')
        try:
            if attempt.run_id:
                if attempt.run.status != 'SUCCEEDED':
                    raise ValueError('Native run is not SUCCEEDED; reconcile writer/state before any retry')
            else:
                if attempt.phase not in ('VALIDATED', 'CALCULATE'):
                    raise ValueError('No proven unexecuted native boundary')
                arguments = _parameters(binding, owner, attempt.predecessor,
                    'csv-v1-' + attempt.batch_digest, pick_root)
                retry_receipt=_verify_capture_retry(attempt)
                if retry_receipt:
                    from mta.runtime.temporal import resolved_pick_root
                    if retry_receipt['pick_root']!=resolved_pick_root(pick_root):
                        raise ValueError('Frozen retry Pick root differs from its lineage receipt')
                    arguments.update(execution_revision=retry_receipt['execution_revision'],
                                     retry_capture_id=retry_receipt['origin_run'])
                if attempt.accepted_facts:
                    from mta.runtime.accepted_daily import read
                    raw = read(attempt, arguments)
                else:
                    native_path = regular(root / 'native-day.json', root)
                    raw = JsonInputFile(native_path)
                    if file_identity(native_path)['sha256'] != attempt.input_sha256:
                        raise ValueError('Frozen native input bytes differ')
                check()
                if not attempt.accepted_facts:
                    save(attempt, 'CALCULATE')
                from mta.runtime.production_daily import execute as native_execute
                native_execute(raw, attempt.input_sha256,
                    **arguments, feed_attempt=attempt.pk)
                attempt.refresh_from_db()
                if not attempt.run_id or attempt.run.status != 'SUCCEEDED':
                    raise ValueError('Native day did not commit its owned output')
            check()
            save(attempt, 'PREPARE', 'COMMITTED')
            run = attempt.run
            from mta.presentation.selective import image_rows
            records = list(image_rows(run, 'closing/importer/RejectedMaster'))
            if records and not (root / 'business-rejections.csv').exists():
                from mta.application.intake_errors import NativeIntakeRejected
                diagnostics(attempt, NativeIntakeRejected('Native rejections', stage='completed', rejections=records))
            from mta.presentation.daily_publication import prepare_reporting_generation
            from mta.application.stage_observation import operation, stage
            prepare_started = perf_counter()
            with operation(str(run.pk)), stage('report_layers'):
                receipt, summary = prepare_reporting_generation(str(run.pk), expected_output_digest=run.output_digest)
            if receipt.status != 'READY' or summary.status != 'READY':
                raise ValueError('Full report generation is not ready')
            from django.core.management import call_command
            with operation(str(run.pk)), stage('guided_aggregates'):
                from mta.runtime.guided_statistics import refresh_pending
                refresh_pending(run)
                call_command('prepare_guided_aggregates', run_id=str(run.pk), output_digest=run.output_digest,
                             stdout=io.StringIO())
            from mta.application.native_input_archive import prepare_accepted as prepare
            native_path = root / 'native-day.json'
            from mta.runtime.captured_input import SCHEMAS as CAPTURED, origin
            if run.input_payload.get('schema') in CAPTURED:
                physical = origin(run)
                original_attempt = DailyFeedAttempt.objects.get(run=physical)
                native_path = regular(Path(original_attempt.archive_path)/'native-day.json',
                                      Path(original_attempt.archive_path))
            with operation(str(run.pk)), stage('input_archive'):
                archive_result = prepare(run, binding['_opening_path'], native_path)
            from mta.presentation.admission import prepared as verify
            with operation(str(run.pk)), stage('report_admission'):
                verify(run)
            from mta.presentation.native_selection import candidate
            from mta.presentation.native_publication import identity
            with operation(str(run.pk)),stage('candidate_binding'):
                from mta.archive_receipt import prepared as archive_receipt
                candidate_value = candidate(run, receipt, summary, identity(run),
                    input_archive=archive_receipt(archive_result))
                atomic_json(root / 'candidate-selection.json', candidate_value)
            logger.warning('daily_phase run=%s phase=report_preparation_and_admission seconds=%.6f',
                           run.pk, perf_counter()-prepare_started)
            attempt.candidate_selection_digest = candidate_value['selection_digest']
            attempt.save(update_fields=['candidate_selection_digest', 'updated_at'])
            check()
            return save(attempt, 'PREPARED', 'PREPARED')
        except Exception as error:
            try:
                check()
                attempt.refresh_from_db()
                diagnostics(attempt, error)
                committed = attempt.run_id and attempt.run.status == 'SUCCEEDED'
                save(attempt, attempt.phase, 'COMMITTED' if committed else 'FAILED',
                    dict(type=type(error).__name__, message=str(error)[:2000]))
            except Exception as recording_error:
                # Database status is deliberately untouched if ownership or
                # connectivity is lost. Reconciliation must establish what
                # committed before any explicit recovery is permitted.
                atomic_json(root / 'interrupted.json', dict(
                    status='INTERRUPTED_RECONCILIATION_REQUIRED',
                    attempt_id=str(attempt.attempt_id), phase=attempt.phase,
                    error=dict(type=type(error).__name__, message=str(error)[:2000]),
                    recording_error=str(recording_error)[:2000]))
            raise


def select(attempt_id, binding_file, selection_file):
    binding, owner = binding_owner(binding_file)
    with job_lock(owner):
        attempt = _bound_attempt(attempt_id, binding)
        if attempt.status != 'PREPARED':
            raise ValueError('Only a completely prepared native day can be selected')
        from mta.presentation.native_selection import read, write
        root, target = Path(attempt.archive_path), Path(selection_file)
        candidate = read(root / 'candidate-selection.json')
        if candidate['selection_digest'] != attempt.candidate_selection_digest:
            raise ValueError('Prepared selection differs')
        from mta.presentation.admission import prepared as verify
        verify(attempt.run)
        from mta.presentation.native_publication import require_publication, identity
        from mta.presentation.daily_publication import require_ready
        from mta.presentation.planning_summary_admission import require_ready as summary_ready
        from mta.presentation.native_selection import candidate as make_candidate
        require_publication(attempt.run)
        expected = make_candidate(attempt.run, require_ready(attempt.run),
                                  summary_ready(attempt.run), identity(attempt.run),
                                  input_archive=candidate.get('input_archive'))
        if candidate != expected:
            raise ValueError('Prepared generation no longer matches its native receipts')
        if target.exists():
            previous = read(target)
            if previous != candidate:
                backup = root / 'previous-selection.json'
                if not backup.exists():
                    backup.write_bytes(target.read_bytes())
                attempt.prior_selection_digest = previous['selection_digest']
                attempt.save(update_fields=['prior_selection_digest', 'updated_at'])
        write(target, candidate)
        return save(attempt, 'SERVE')


def acknowledge(attempt_id, binding_file, selection_file, proof):
    binding, owner = binding_owner(binding_file)
    with job_lock(owner):
        attempt = _bound_attempt(attempt_id, binding)
        from mta.presentation.native_selection import read
        selected = read(selection_file)
        if (attempt.status != 'PREPARED' or attempt.phase != 'SERVE'
                or selected['selection_digest'] != attempt.candidate_selection_digest
                or proof.get('run_id') != str(attempt.run_id)
                or proof.get('output_digest') != attempt.run.output_digest
                or proof.get('selection_digest') != selected['selection_digest']
                or proof.get('ready') is not True):
            raise ValueError('Serving acknowledgement differs from the prepared native day')
        atomic_json(Path(attempt.archive_path) / 'serving-proof.json', proof)
        return save(attempt, 'FINISHED', 'PUBLISHED')
