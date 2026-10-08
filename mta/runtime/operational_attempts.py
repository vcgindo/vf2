"""Run/config-bound operational attempt lifecycle, independent of calculations."""
from pathlib import Path
from contextlib import contextmanager
import uuid

from django.db import transaction
from django.utils import timezone
from mta.application.operational_input_archive import archive_clock
from mta.runtime.models import CalculationRun
from mta.runtime.operational_models import (
    OperationalAttempt, OperationalConfiguration, OperationalSetting,
    OperationalInputTable, OperationalAlertSetting,
)
from mta.runtime.operational_effects import verify_files, verify_intent_evaluation
from mta.application import operational_io
from mta.runtime.operational_native import OperationalPopulation, read_population
from mta.runtime.services import read_outputs
from mta.runtime.temporal import command_state
from mta.serialization import digest
from mta.runtime.operational_lease import (
    require_run_lease,require_attempt_lease,operational_run_lease,OperationalLeaseError,
)


POLICY = 'cohort2-operational-effects-v1'
GROUPS = tuple('O' + str(number) for number in range(1, 10))


def configuration_value(configuration):
    settings = list(configuration.operationalsetting_set.order_by('ordinal').values('ordinal', 'name', 'value'))
    tables = list(configuration.operationalinputtable_set.order_by('ordinal').values(
        'ordinal', 'database_name', 'table_name', 'condition'))
    alerts = list(configuration.operationalalertsetting_set.order_by('ordinal').values('ordinal', 'name', 'active'))
    for rows in (settings, tables, alerts):
        if [row['ordinal'] for row in rows] != list(range(len(rows))):
            raise ValueError('Operational configuration ordinal drift')
    value = dict(policy=configuration.policy, source_digest=configuration.source_digest,
                 bindings=configuration.bindings, settings=settings, tables=tables, alerts=alerts)
    if digest(value) != configuration.pk:
        raise ValueError('Operational configuration identity drift')
    return value


@transaction.atomic
def register_configuration(*, source_digest, bindings, settings, tables, alerts):
    """Exact bounded metadata and explicit ordered settings; never table payloads."""
    import json
    if not isinstance(bindings, dict) or len(json.dumps(bindings)) > 32768:
        raise ValueError('Bounded operational tool/path/provenance metadata required')
    value = dict(policy=POLICY, source_digest=source_digest, bindings=bindings,
                 settings=settings, tables=tables, alerts=alerts)
    identity = digest(value)
    existing = OperationalConfiguration.objects.filter(pk=identity).first()
    if existing:
        configuration_value(existing)
        return existing
    owner = OperationalConfiguration.objects.create(digest=identity, policy=POLICY,
                                                     source_digest=source_digest, bindings=bindings)
    for rows, model in ((settings, OperationalSetting), (tables, OperationalInputTable),
                        (alerts, OperationalAlertSetting)):
        if [row['ordinal'] for row in rows] != list(range(len(rows))):
            raise ValueError('Explicit ordered configuration roster required')
        model.objects.bulk_create([model(configuration=owner, **row) for row in rows])
    configuration_value(owner)
    return owner


def _identity(run):
    output = read_outputs(run)
    _, actions = command_state(run, output['DBMFinal'][0])
    return dict(output_digest=run.output_digest, action_digest=digest(actions),
                source_digest=digest(dict(input=run.input_digest, output=run.output_digest,
                                         production=run.production_digest, actions=actions)))


def start_attempt(*, run_id, configuration_id, request_key, owned_root,
                  expected_output_digest, predecessor_id=None, retry_of_id=None,
                  repair_of_id=None,repair_file_ids=()):
    if not transaction.get_autocommit():
        raise ValueError('Operational attempt owns its durable boundary')
    run_id=uuid.UUID(str(run_id))
    predecessor_id=uuid.UUID(str(predecessor_id)) if predecessor_id is not None else None
    retry_of_id=uuid.UUID(str(retry_of_id)) if retry_of_id is not None else None
    repair_of_id=uuid.UUID(str(repair_of_id)) if repair_of_id is not None else None
    lease=require_run_lease(run_id)
    root = Path(owned_root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Existing explicit owned output directory required')
    root = root.resolve(strict=True)
    if not isinstance(request_key, str) or not 1 <= len(request_key) <= 120:
        raise ValueError('Explicit bounded request identity required')
    with transaction.atomic():
        run = CalculationRun.objects.select_for_update().get(pk=run_id)
        if run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED' or run.output_digest != expected_output_digest:
            raise ValueError('Exact completed daily source required')
        configuration = OperationalConfiguration.objects.get(pk=configuration_id)
        configuration_value(configuration)
        identity = _identity(run)
        existing = OperationalAttempt.objects.filter(request_key=request_key).first()
        if existing:
            if (existing.run_id != run.pk or existing.configuration_id != configuration.pk
                    or Path(existing.root).parent != root or existing.predecessor_id != predecessor_id
                    or existing.retry_of_id != retry_of_id or existing.source_digest != identity['source_digest']
                    or existing.repair_of_id!=repair_of_id
                    or list(existing.repair_targets.order_by('ordinal').values_list('original_file_id',flat=True))!=list(repair_file_ids)):
                raise ValueError('Operational request identity reused with different facts')
            if existing.status != 'SUCCEEDED':
                raise ValueError('Prior operational attempt unfinished/failed; explicit new retry required')
            verify_attempt(existing)
            return existing
        if OperationalAttempt.objects.filter(run=run, status='RUNNING').exists():
            raise ValueError('A running operational attempt already owns this daily run')
        predecessor = None
        if predecessor_id is not None:
            predecessor = OperationalAttempt.objects.select_for_update().get(pk=predecessor_id)
            if (predecessor.status != 'SUCCEEDED' or predecessor.repair_of_id is not None or predecessor.configuration_id != configuration.pk
                    or predecessor.run_id != run.predecessor_id or predecessor.business_date >= run.business_date):
                raise ValueError('Operational predecessor is not the own accepted daily predecessor')
            verify_attempt(predecessor)
        elif run.predecessor_id is not None:
            raise ValueError('Successor requires its explicit operational predecessor')
        repair_parent=None;repair_files=[]
        if repair_of_id is not None:
            from mta.runtime.operational_repair import validate_repair_parent
            repair_parent=OperationalAttempt.objects.select_for_update().get(pk=repair_of_id)
            if (repair_parent.run_id!=run.pk or repair_parent.configuration_id!=configuration.pk
                    or repair_parent.predecessor_id!=predecessor_id
                    or repair_parent.source_digest!=identity['source_digest']):
                raise ValueError('Repair must retain original run/configuration/source')
            repair_files=validate_repair_parent(repair_parent,list(repair_file_ids))
        elif repair_file_ids:raise ValueError('Repair file roster requires an explicit parent')
        if retry_of_id is not None:
            previous = OperationalAttempt.objects.select_for_update().get(pk=retry_of_id)
            if (previous.status != 'FAILED' or previous.run_id != run.pk
                    or previous.configuration_id != configuration.pk
                    or previous.predecessor_id != predecessor_id or previous.source_digest != identity['source_digest']
                    or previous.repair_of_id!=repair_of_id
                    or list(previous.repair_targets.order_by('ordinal').values_list('original_file_id',flat=True))!=list(repair_file_ids)):
                raise ValueError('Retry must retain the same failed attempt source/configuration')
            if previous.retries.exists():
                raise ValueError('Failed attempt already has a retry; continue that explicit lineage')
        elif repair_parent is None and OperationalAttempt.objects.filter(run=run, configuration=configuration).exists():
            raise ValueError('Existing operational history requires explicit recovery lineage')
        attempt_id = uuid.uuid4()
        folder = root / str(attempt_id)
        folder.mkdir(exist_ok=False)
        created=OperationalAttempt.objects.create(id=attempt_id, run=run, configuration=configuration,
            request_key=request_key, predecessor=predecessor, retry_of_id=retry_of_id,repair_of=repair_parent,
            business_date=run.business_date, run_output_digest=identity['output_digest'],
            action_digest=identity['action_digest'], source_digest=identity['source_digest'],
            clock=archive_clock(run.business_date)['clock'], root=str(folder), status='RUNNING',
            lease_key=lease.key if lease else None,lease_owner=lease.owner if lease else None)
        require_attempt_lease(created)
        if repair_files:
            from mta.runtime.operational_models import OperationalRepairTarget
            OperationalRepairTarget.objects.bulk_create([
                OperationalRepairTarget(attempt=created,ordinal=i,original_file=row)
                for i,row in enumerate(repair_files)])
            require_attempt_lease(created)
        return created


def verify_attempt(attempt):
    return _verify_attempt(attempt)


def _verify_attempt(attempt,*,missing_file_ids=()):
    attempt = OperationalAttempt.objects.select_related('run', 'configuration').get(pk=attempt.pk)
    if attempt.status not in ('RUNNING', 'SUCCEEDED'):
        raise ValueError('Failed or unfinished operational attempt cannot verify')
    if (attempt.run.kind != 'DAILY_CHAIN' or attempt.run.status != 'SUCCEEDED'
            or attempt.business_date != attempt.run.business_date):
        raise ValueError('Operational daily owner/status/date differs')
    configuration = configuration_value(attempt.configuration)
    current = _identity(attempt.run)
    if (attempt.run_output_digest != current['output_digest']
            or attempt.action_digest != current['action_digest']
            or attempt.source_digest != current['source_digest']):
        raise ValueError('Operational run/action/source identity drift')
    if missing_file_ids and attempt.status!='SUCCEEDED':
        raise ValueError('Only historical repair admission may identify missing files')
    if attempt.repair_of_id is not None:
        from mta.runtime.operational_repair import verify_repair_attempt
        return verify_repair_attempt(attempt,missing_file_ids=missing_file_ids)
    roster = configuration['bindings'].get('operation_roster')
    if (not isinstance(roster, list) or not roster
            or set(row['group'] for row in roster) != set(GROUPS)):
        raise ValueError('Complete explicit O1–O9 operation roster required')
    operations = list(attempt.operations.order_by('ordinal'))
    actual = [dict(ordinal=row.ordinal, group=row.group, name=row.name, stage=row.stage,
                   source_digest=row.source_digest) for row in operations]
    if actual != roster or any(row.status != 'SUCCEEDED' for row in operations):
        raise ValueError('Operational completion roster is incomplete or failed')
    # An entire required O-group cannot be waived by marking its receipt DISABLED.
    # Individual inactive branches are represented by explicit alert evaluations.
    for population in OperationalPopulation.objects.filter(attempt=attempt):
        read_population(attempt, population.image)
    for row in operations:
        verify_files(row,missing_file_ids=missing_file_ids)
        for evaluation in row.operationalintentevaluation_set.select_related('intent'):
            verify_intent_evaluation(evaluation)
            intent = evaluation.intent
            if (intent.run_id != attempt.run_id or intent.configuration_id != attempt.configuration_id
                    or intent.business_date != attempt.business_date):
                raise ValueError('Operational alert intent belongs to a different owner')
            identity = digest(dict(run=str(intent.run_id), configuration=intent.configuration_id,
                source=intent.source_digest, alert=intent.alert_name, branch=intent.branch, stage=intent.stage))
            if intent.identity != identity:
                raise ValueError('Operational alert intent identity drift')
            if intent.disposition == 'ATTACHMENT_UNAVAILABLE':
                raise ValueError('Required alert attachment is unavailable')
            if intent.disposition == 'LOCAL_READY' and (intent.subject is None or intent.body is None):
                raise ValueError('Ready local intent content is unavailable')
            attachments = list(intent.attachments.order_by('ordinal'))
            if [item.ordinal for item in attachments] != list(range(len(attachments))):
                raise ValueError('Operational alert attachment ordinal drift')
            for attachment in attachments:
                from mta.runtime.operational_repair import resolve_intent_attachment
                resolve_intent_attachment(attempt,attachment,missing_file_ids=missing_file_ids)
        for backup in row.backups.all():
            from mta.runtime.operational_backup import verify_backup
            verify_backup(backup)
    if not any(row.backups.filter(restore_status__in=('VERIFIED','QUALIFIED')).exists() for row in operations if row.group == 'O8'):
        raise ValueError('Required verified operational backup absent')
    from mta.runtime.operational_runner import verify_required_outputs
    verify_required_outputs(attempt)
    return actual


def finish_attempt(attempt):
    if not transaction.get_autocommit():
        raise ValueError('Operational completion owns its durable boundary')
    with transaction.atomic():
        owner = OperationalAttempt.objects.select_for_update().select_related('run', 'configuration').get(pk=attempt.pk)
        CalculationRun.objects.select_for_update().get(pk=owner.run_id)
        if owner.status != 'RUNNING':
            raise ValueError('Only a running attempt may complete')
        require_attempt_lease(owner)
        verify_attempt(owner)
        require_attempt_lease(owner)
        owner.status = 'SUCCEEDED'
        owner.completed_at = timezone.now()
        owner.save(update_fields=['status', 'completed_at'])
        require_attempt_lease(owner)
        return owner


def _fail_locked(owner,reason):
    now=timezone.now()
    owner.operations.filter(status='RUNNING').update(status='FAILED',reason=reason,completed_at=now)
    owner.status='FAILED';owner.failure=reason;owner.completed_at=now
    owner.save(update_fields=['status','failure','completed_at'])
    return owner


@transaction.atomic
def fail_attempt(attempt_id,reason):
    if not isinstance(reason,str) or not reason:raise ValueError('Explicit operational failure reason required')
    owner=OperationalAttempt.objects.select_for_update().get(pk=attempt_id)
    require_attempt_lease(owner)
    if owner.status!='RUNNING':raise ValueError('Terminal operational attempt cannot be rewritten')
    result=_fail_locked(owner,reason)
    require_attempt_lease(owner)
    return result


@transaction.atomic
def fail_interrupted_attempt(attempt_id):
    owner=OperationalAttempt.objects.select_for_update().get(pk=attempt_id)
    lease=require_run_lease(owner.run_id)
    if (lease is None or owner.lease_key!=lease.key or owner.lease_owner is None
            or owner.lease_owner==lease.owner):
        raise ValueError('Only a prior managed worker can be recorded interrupted')
    if owner.status!='RUNNING':raise ValueError('Terminal operational attempt cannot be rewritten')
    lease.check()
    result=_fail_locked(owner,'Interrupted operational worker; prior session lease is no longer held')
    lease.check()
    return result


@contextmanager
def operational_worker(*,interrupted_attempt_id=None,**start_arguments):
    """Own the lease across all stages, including errors between effects."""
    with operational_run_lease(start_arguments['run_id']):
        if interrupted_attempt_id is not None:
            if start_arguments.get('retry_of_id')!=interrupted_attempt_id:
                raise ValueError('Interruption recovery requires the exact explicit retry link')
            previous=OperationalAttempt.objects.get(pk=interrupted_attempt_id)
            if previous.run_id!=uuid.UUID(str(start_arguments['run_id'])):
                raise ValueError('Interrupted attempt belongs to another daily run')
            if (previous.configuration_id!=start_arguments['configuration_id']
                    or previous.run_output_digest!=start_arguments['expected_output_digest']
                    or previous.predecessor_id!=start_arguments.get('predecessor_id')
                    or previous.source_digest!=_identity(previous.run)['source_digest']):
                raise ValueError('Interrupted retry source/configuration differs')
            fail_interrupted_attempt(interrupted_attempt_id)
        owner=start_attempt(**start_arguments)
        if owner.status=='SUCCEEDED':
            # A verified idempotent request performs no effects.
            yield owner
            return
        try:
            yield owner
            finish_attempt(owner)
        except BaseException as error:
            owner.refresh_from_db()
            if owner.status=='RUNNING':
                try:
                    fail_attempt(owner.pk,type(error).__name__+': '+str(error))
                except OperationalLeaseError:
                    # A hard/session interruption is recorded by the next
                    # exclusive worker, never by an unowned terminal write.
                    pass
            raise
