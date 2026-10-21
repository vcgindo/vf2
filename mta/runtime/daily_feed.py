"""One CSV attempt through existing native execution and report publication.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from contextlib import contextmanager
from datetime import date, timedelta
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
from mta.application.streamed_input import JsonInputFile
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
    if today == owner.opening_date + timedelta(days=1):
        return None
    candidates = list(CalculationRun.objects.filter(kind='DAILY_CHAIN', status='SUCCEEDED',
        business_date=today - timedelta(days=1), mdm_input_capture__source=owner.source)[:2])
    if len(candidates) != 1:
        raise ValueError('A unique immediately preceding successful own native day is required')
    return candidates[0]


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


def unresolved_attempts(owner):
    """A retained failure is resolved only by its own published retry owner."""
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
          run__input_payload__schema=SECOND))
    completed = MdmDailyInputCapture.objects.filter(path,
        run__input_digest=OuterRef('run__input_digest'),
        status='CONSUMED',run__status='SUCCEEDED',run__business_date=OuterRef('business_date'),
        run__csv_attempt__initialization=owner,run__csv_attempt__status='PUBLISHED')
    return DailyFeedAttempt.objects.filter(initialization=owner).exclude(
        status__in=('PUBLISHED','REJECTED')).annotate(_resolved=Exists(completed)).exclude(
        status='FAILED',_resolved=True)


def stage(binding_file, source, business_date, *, input_root, work_root, pick_root):
    binding, owner = binding_owner(binding_file)
    identity=uuid.uuid4()
    root=Path(work_root).absolute()/str(identity)
    root.mkdir(parents=True,exist_ok=False)
    try:
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
    with job_lock(owner):
        old = DailyFeedAttempt.objects.filter(request_key=request_key).first()
        if old:
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
            Path(pick_root).mkdir(parents=True, exist_ok=True)
            frozen=batch
            parent = predecessor(owner, business_date)
            payloads = {name:regular(root / 'original' / name, root)
                        for name, state in frozen['feeds'].items() if state == 'PRESENT'}
            raw, positions = assemble(frozen, binding, payloads, first_day=parent is None,
                                      output_file=root / 'native-day.json', _transfer=True)
            atomic_json(root / 'record-lines.json', positions)
            attempt.input_sha256 = raw.sha256
            attempt.predecessor = parent
            attempt.predecessor_output_digest = parent.output_digest if parent else ''
            attempt.save(update_fields=['input_sha256', 'predecessor', 'predecessor_output_digest', 'updated_at'])
            from mta.runtime.daily_preparation import prepare
            from mta.runtime.ingestion_admission import preparation_source
            raw = prepare(raw, attempt.input_sha256)
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
    return attempt


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
                call_command('prepare_guided_aggregates', run_id=str(run.pk), output_digest=run.output_digest,
                             stdout=io.StringIO())
            from mta.application.native_input_archive import prepare
            native_path = root / 'native-day.json'
            from mta.runtime.captured_input import SCHEMAS as CAPTURED, origin
            if run.input_payload.get('schema') in CAPTURED:
                physical = origin(run)
                original_attempt = DailyFeedAttempt.objects.get(run=physical)
                native_path = regular(Path(original_attempt.archive_path)/'native-day.json',
                                      Path(original_attempt.archive_path))
            with operation(str(run.pk)), stage('input_archive'):
                prepare(run, binding['_opening_path'], native_path)
            from mta.presentation.admission import verify
            with operation(str(run.pk)), stage('report_admission'):
                verify(run)
            from mta.presentation.native_selection import candidate
            from mta.presentation.native_publication import identity
            candidate_value = candidate(run, receipt, summary, identity(run))
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
        from mta.presentation.admission import verify
        verify(attempt.run)
        from mta.presentation.native_publication import require_publication, identity
        from mta.presentation.daily_publication import require_ready
        from mta.presentation.planning_summary_admission import require_ready as summary_ready
        from mta.presentation.native_selection import candidate as make_candidate
        require_publication(attempt.run)
        expected = make_candidate(attempt.run, require_ready(attempt.run),
                                  summary_ready(attempt.run), identity(attempt.run))
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
