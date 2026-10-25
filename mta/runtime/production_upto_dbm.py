"""Fresh native execution through the accepted pre-BTR DBM boundary.

Reuse capture, PRE/BPR, actions and DBM owners. Never finalize a day here.
This entry currently qualifies explicit owned-test no-op site hooks only.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.db import connection, transaction
from mta.serialization import digest

SCHEMA = 'fresh-native-upto-dbm-request-v1'
DISPOSITION = 'fresh-owned-upto-dbm-disposition-v1'


def disposition(value):
    if (type(value) is not dict or set(value) != {
            'schema','purpose','site_code','hooks','input_download','authority'}
            or value['schema'] != DISPOSITION or value['purpose'] != 'owned-scoped-test'
            or value['site_code'] != 'SUPPLIED-INSTANCE'
            or value['hooks'] != {name:'explicit-test-no-op' for name in ('PostBPR','PreDBM','PostDBM')}
            or value['input_download'] != 'enabled-five-file-four-table-archive'
            or type(value['authority']) is not str or not 1 <= len(value['authority']) <= 1000
            or not value['authority'].strip()):
        raise ValueError('Explicit applicable UptoDBM test hook and InputData disposition required')
    return deepcopy(value)


def load_disposition(path, expected_sha256):
    from mta.mdm.initialization_contract import object_pairs
    from mta.runtime.ingestion_context import sha
    sha(expected_sha256)
    with Path(path).open('rb') as stream: raw = stream.read(4097)
    if len(raw) > 4096 or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('UptoDBM disposition bytes differ')
    return disposition(json.loads(raw, object_pairs_hook=object_pairs))


def request(command_key, *, runtime_reports, dispositions):
    from release.native_identity import require_current
    from mta.runtime.phase_state import recipe_digest
    from mta.runtime.scope_runtime_reports import validate
    if type(command_key) is not str or not 1 <= len(command_key) <= 120:
        raise ValueError('Explicit UptoDBM command key required')
    value = dict(schema=SCHEMA, scope='UptoDBM', command_key=command_key,
        runtime_reports=validate(runtime_reports), dispositions=disposition(dispositions))
    value['compatibility_digest'] = digest(dict(request=value,
        release=require_current(), phase_recipe=recipe_digest()))
    return value


def validate_request(value):
    if (type(value) is not dict or set(value) != {'schema','scope','command_key',
            'runtime_reports','dispositions','compatibility_digest'}
            or value != request(value.get('command_key'),
                runtime_reports=value.get('runtime_reports'), dispositions=value.get('dispositions'))):
        raise ValueError('Native UptoDBM request or implementation identity differs')
    return value


def configuration(profile, day, value):
    if profile.get('delivery', {}).get('site_code') != value['dispositions']['site_code']:
        raise ValueError('UptoDBM site differs from its explicit disposition')
    if profile.get('daily_publication') is not True:
        raise ValueError('UptoDBM requires configured report publication')
    if not {'production_report_policy','production_report_opening','production_report_schema'} <= set(day):
        raise ValueError('UptoDBM requires configured BPR allocation histories')
    from mta.application import production_source_inputs, production_output_policy
    if day['production_report_schema'] not in (
            production_source_inputs.SCHEMA, production_output_policy.SOURCE_SCHEMA):
        raise ValueError('UptoDBM allocation-history schema differs')
    policy = day['production_report_policy']
    if (type(policy) is not dict or
            not {'bor_history_horizon','rrr_history_horizon'} <= set(policy)):
        raise ValueError('UptoDBM requires explicit allocation-history horizons')


def _configuration(run, value):
    from mta.runtime.input_reader import read_input
    from mta.runtime.scope_runtime_reports import require_test_database
    require_test_database()
    raw = read_input(run, components=('profile','day'))
    # A fresh request must declare the normal BPR history producer. The earlier
    # retained run's exceptional late completion cannot apply to this run.
    configuration(raw['profile'], raw['day'], value)


def _disposition_file(path, raw):
    """Install complete immutable bytes without a partially written final name."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        candidate = None
        try:
            with NamedTemporaryFile(dir=path.parent, prefix='.disposition-', delete=False) as stream:
                candidate = Path(stream.name)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(candidate, path)
            except FileExistsError:
                pass
            if os.name == 'posix':
                descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try: os.fsync(descriptor)
                finally: os.close(descriptor)
        finally:
            if candidate is not None: candidate.unlink(missing_ok=True)
    if path.is_symlink() or path.read_bytes() != raw:
        raise ValueError('Owned BPR artifact disposition changed')


def _bpr_files(run, bpr, value, *, repair):
    from mta.runtime import scoped_pick_files
    from mta.presentation import scoped_artifacts
    from mta.runtime.input_reader import read_input
    from mta.application.operational_io import owned_path
    files = scoped_pick_files.prepare(bpr.pk, expected_digest=bpr.digest, repair=repair)
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        database = cursor.fetchone()[0]
    declaration = dict(schema=scoped_artifacts.SCHEMA, purpose='owned-scoped-test',
        run_id=str(run.pk), phase_id=str(bpr.pk), phase_digest=bpr.digest,
        input_digest=run.input_digest, input_manifest_digest=run.input_manifest_digest,
        site_code=value['dispositions']['site_code'], post_bpr_hook='explicit-test-no-op',
        input_download=True, importer_database=archive_label(database),
        physical_files=list(scoped_artifacts.PHYSICAL), input_tables=list(scoped_artifacts.TABLES),
        archive_clock='business-midnight-Asia-Kolkata', authority=value['dispositions']['authority'])
    raw = (json.dumps(declaration, sort_keys=True)+'\n').encode()
    checksum = hashlib.sha256(raw).hexdigest()
    root = Path(read_input(run, components=('pick_output_root',))['pick_output_root'])
    path = owned_path(root, str(run.pk)+'/scope-dispositions/'+checksum+'.json')
    _disposition_file(path, raw)
    artifact = scoped_artifacts.prepare(bpr.pk, expected_digest=bpr.digest,
        declaration_file=path, declaration_sha256=checksum)
    return files, artifact


def archive_label(database):
    """PostgreSQL identity is case-folded; retain the native archive prefix."""
    import re
    if type(database) is not str or not re.fullmatch(r'(?i:vftest_fresh_)[A-Za-z0-9_]+',database):
        raise ValueError('Owned Fresh database required for InputData')
    return 'VFTEST_Fresh_'+database[len('vftest_fresh_'):]


def advance(run, value, *, worker_reference, recovery_of=None, repair_files=False, prepare_reads=False):
    from mta.runtime import production_scope as fresh, scope_execution as workers
    from mta.runtime.models import CalculationRun, RunScopeAttempt
    from mta.runtime.scoped_actions import calculate_dbm, revision
    if type(prepare_reads) is not bool:
        raise ValueError('Explicit UptoDBM read preparation flag required')
    run = CalculationRun.objects.get(pk=run.pk)
    fresh.captured_run(run, value)
    _configuration(run, value)
    compatibility = value['compatibility_digest']
    previous = RunScopeAttempt.objects.filter(run=run, command_key=value['command_key']).order_by('-attempt_no').first()
    if previous is not None and (previous.scope != 'UptoDBM' or previous.compatibility_digest != compatibility):
        raise ValueError('UptoDBM command compatibility differs')
    phase, checksum = workers.head(run.pk)
    if phase not in ('START','PRE_BPR','BPR','DBM') or run.status != 'RUNNING':
        raise ValueError('UptoDBM cannot advance or reinterpret a completed day')
    if phase == 'DBM':
        owner = run.phase_acceptances.select_related('attempt').get(phase='DBM', state_sealed=True).attempt
        if (owner.scope, owner.command_key, owner.compatibility_digest) != (
                'UptoDBM', value['command_key'], compatibility):
            raise ValueError('UptoDBM cannot adopt a different DBM command')
    if previous is not None and previous.status == 'RELEASED':
        if recovery_of is not None or phase != 'DBM':
            raise ValueError('Released UptoDBM requires its accepted DBM stop')
        with transaction.atomic():
            workers._source_lock(run.pk)
            run = CalculationRun.objects.select_for_update().get(pk=run.pk)
            workers._frozen(run)
            latest = run.scope_attempts.order_by('-created_at','-id').first()
            if (latest is None or latest.pk != previous.pk or latest.status != 'RELEASED'
                    or workers.head(run.pk) != ('DBM', checksum)):
                raise ValueError('UptoDBM repeat requires its latest released DBM stop')
            bpr = run.phase_acceptances.get(phase='BPR', state_sealed=True)
            files, artifact = _bpr_files(run, bpr, value, repair=repair_files)
            receipt = fresh._phase(run, 'DBM', checksum)
    else:
        attempt = workers.claim(run.pk, scope='UptoDBM', command_key=value['command_key'],
            worker_reference=worker_reference, compatibility_digest=compatibility,
            expected_phase=phase, expected_receipt_digest=checksum, recovery_of=recovery_of)
        try:
            bpr = (run.phase_acceptances.get(phase='BPR', state_sealed=True)
                   if phase == 'DBM' else fresh._produce(attempt, value))
            # Post-BPR files finish before DBM, including on recovery from BPR.
            files, artifact = _bpr_files(run, bpr, value, repair=repair_files)
            receipt = (fresh._phase(run, 'DBM', checksum) if phase == 'DBM' else
                calculate_dbm(attempt.pk, attempt.worker_token, compatibility_digest=compatibility))
            workers.release(attempt.pk, attempt.worker_token, compatibility_digest=compatibility)
        except Exception as error:
            try: workers.fail(attempt.pk, attempt.worker_token, compatibility_digest=compatibility, error=error)
            except Exception as closing_error: raise error from closing_error
            raise
    read_reference = None
    current_revision = revision(run)
    if prepare_reads:
        from mta.presentation.scoped_dbm_view import prepare
        read_reference = prepare(receipt.pk,expected_digest=receipt.digest,
            action_revision=current_revision).read_identity
    return dict(scope='UptoDBM', run_id=str(run.pk), status=run.status,
        business_date=run.business_date.isoformat(), phase_acceptance_id=str(receipt.pk),
        phase_acceptance_digest=receipt.digest, snapshot_digest=receipt.snapshot.state_digest,
        action_revision=current_revision, accepted_action_revision=receipt.attempt.action_revision,
        pick_files_digest=files.digest,
        input_archive_receipt=artifact['receipt_sha256'], calculation_accepted=True,
        scope_ready=False, serving_selected=False, application_acceptance=False,
        read_reference=read_reference,
        pending=(['pre_btr_read_binding'] if read_reference is None else [])+['end_to_end_acceptance'])


def execute(raw, expected_sha256, *, command_key, worker_reference, runtime_reports,
            dispositions, recovery_of=None, inspect_only=False, repair_files=False, prepare_reads=False,
            archive_recovery=False, **arguments):
    from mta.runtime import production_scope as fresh, production_daily
    from mta.runtime.production_preflight import require
    from mta.runtime.scope_runtime_reports import require_test_database
    if not transaction.get_autocommit():
        raise ValueError('Native UptoDBM owns its phase transactions')
    if (type(worker_reference) is not str or not 1 <= len(worker_reference) <= 200
            or type(repair_files) is not bool or type(inspect_only) is not bool or type(prepare_reads) is not bool
            or type(archive_recovery) is not bool):
        raise ValueError('Explicit UptoDBM worker and flags required')
    if any(arguments.get(name) is not None for name in ('retry_capture_id','report_disposition','feed_attempt')):
        raise ValueError('UptoDBM recovery retains its original scoped capture')
    value = request(command_key, runtime_reports=runtime_reports, dispositions=dispositions)
    fresh.authorize()
    require_test_database()
    if archive_recovery:
        from mta.runtime.scoped_dbm_archive_recovery import resolve,RUN
        value = resolve(value, recovery_of=recovery_of, initialization_id=arguments.get('initialization_id'))
    run = fresh.repeated(raw, expected_sha256, value, arguments)
    if archive_recovery and (run is None or str(run.pk)!=RUN):
        raise ValueError('Archive recovery requires its exact retained day')
    if run is None:
        if recovery_of is not None:
            raise ValueError('UptoDBM recovery requires its existing frozen day')
        if inspect_only:
            report, *_ = production_daily.inspect_execution(raw, expected_sha256, scope_request=value, **arguments)
            require(report, 'day')
            return report
        run = production_daily.execute(raw, expected_sha256, scope_request=value, **arguments)
    if inspect_only:
        from mta.runtime.scope_execution import head
        _configuration(run, value)
        return dict(scope='UptoDBM', run_id=str(run.pk), accepted_head=list(head(run.pk)),
            mutation=False, scope_ready=False, serving_selected=False)
    return advance(run, value, worker_reference=worker_reference,
        recovery_of=recovery_of, repair_files=repair_files, prepare_reads=prepare_reads)
