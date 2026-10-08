"""Durable effect receipts around nontransactional file work.

Calculation rows remain read-only. A crashed RUNNING operation is unfinished;
recovery records a new attempt rather than blessing the interrupted directory.
The orchestration adapter owns the complete canonical operation roster.
"""
from contextlib import contextmanager
from django.db import transaction
from django.utils import timezone

from mta.application import operational_io
from mta.runtime.operational_models import (
    OperationalAttempt, OperationalOperation, OperationalFile,
    OperationalArchiveMember, OperationalAlertIntent, OperationalIntentAttachment,
    OperationalIntentEvaluation,
)
from mta.serialization import digest
from mta.runtime.operational_lease import require_attempt_lease,OperationalLeaseError


def _require_autocommit():
    if not transaction.get_autocommit():
        raise ValueError('Operational effects require their own durable transaction boundary')


@contextmanager
def operation(attempt, *, ordinal, group, name, stage, source_digest):
    """Commit RUNNING before I/O and the truthful terminal result afterwards."""
    _require_autocommit()
    with transaction.atomic():
        owner = OperationalAttempt.objects.select_for_update().get(pk=attempt.pk)
        require_attempt_lease(owner)
        if owner.status != 'RUNNING':
            raise ValueError('Effect requires a running operational attempt')
        if (group not in tuple('O' + str(i) for i in range(1, 10))
                or type(ordinal) is not int or ordinal < 0
                or len(source_digest) != 64):
            raise ValueError('Explicit canonical operation identity required')
        effect = OperationalOperation.objects.create(attempt=owner, ordinal=ordinal,
            group=group, name=name, stage=stage, source_digest=source_digest,
            status='RUNNING', started_at=timezone.now())
        require_attempt_lease(owner)
    try:
        yield effect
        # Read each recorded artifact again immediately before success. A caller
        # cannot turn a missing/changed file into a successful operation receipt.
        verify_files(effect)
        with transaction.atomic():
            owner = OperationalAttempt.objects.select_for_update().get(pk=attempt.pk)
            current = OperationalOperation.objects.select_for_update().get(pk=effect.pk)
            require_attempt_lease(owner)
            if owner.status != 'RUNNING' or current.status != 'RUNNING':
                raise ValueError('Operational ownership changed during effects')
            current.status = 'SUCCEEDED'
            current.completed_at = timezone.now()
            current.save(update_fields=['status', 'completed_at'])
            require_attempt_lease(owner)
    except Exception as error:
        # A lost lease cannot authorize even a failure transition. The next
        # exclusive worker records interruption while preserving these files.
        # Deliberately outside the I/O transaction. Existing files and successful
        # predecessor operations remain evidence; no filesystem rollback claim.
        try:
            with transaction.atomic():
                owner = OperationalAttempt.objects.select_for_update().get(pk=attempt.pk)
                require_attempt_lease(owner)
                current = OperationalOperation.objects.select_for_update().get(pk=effect.pk)
                if current.status == 'RUNNING':
                    current.status = 'FAILED'
                    current.reason = type(error).__name__ + ': ' + str(error)
                    current.completed_at = timezone.now()
                    current.save(update_fields=['status', 'reason', 'completed_at'])
                OperationalAttempt.objects.filter(pk=attempt.pk, status='RUNNING').update(
                    status='FAILED', failure=type(error).__name__ + ': ' + str(error),
                    completed_at=timezone.now())
                require_attempt_lease(owner)
        except OperationalLeaseError:
            raise error
        raise


@transaction.atomic
def record_file(effect, *, relative_path, role, archive=False):
    owner = OperationalAttempt.objects.select_for_update().get(pk=effect.attempt_id)
    require_attempt_lease(owner)
    current = OperationalOperation.objects.select_for_update().get(pk=effect.pk)
    if owner.status != 'RUNNING' or current.status != 'RUNNING':
        raise ValueError('File receipt requires a running effect')
    receipt = operational_io.inspect_file(owner.root, relative_path)
    row = OperationalFile.objects.create(operation=current, role=role, **receipt)
    if archive:
        members = operational_io.zip_members(owner.root, relative_path)
        OperationalArchiveMember.objects.bulk_create([
            OperationalArchiveMember(archive=row, **member) for member in members])
    require_attempt_lease(owner)
    return row


def verify_files(effect,*,missing_file_ids=()):
    from mta.runtime.operational_repair import resolve_operational_file
    for row in effect.files.order_by('id'):
        if row.pk in missing_file_ids:
            if effect.attempt.status!='SUCCEEDED' or operational_io.owned_path(effect.attempt.root,row.relative_path).exists():
                raise ValueError('Repair admission permits only missing historical files')
        else:resolve_operational_file(row)


def intent_content_digest(intent):
    """Bind an evaluation to exact content as well as its deduplication key."""
    fields = ('configuration_id', 'alert_name', 'branch', 'stage', 'business_date',
              'source_digest', 'recipients', 'subject', 'body', 'disposition', 'reason')
    values = {name: getattr(intent, name) for name in fields}
    values['run_id'] = str(intent.run_id)
    values['attachments'] = list(intent.attachments.order_by('ordinal').values(
        'ordinal', 'relative_path', 'sha256', 'size_bytes'))
    return digest(values)


def verify_intent_evaluation(evaluation):
    if not evaluation.evaluated_digest or evaluation.evaluated_digest != intent_content_digest(evaluation.intent):
        raise ValueError('Operational alert evaluation content drift or missing receipt')


@transaction.atomic
def record_intent(effect, *, alert_name, branch, stage, source_digest, recipients,
                  subject, body, disposition, reason, attachments):
    """Deduplicate only an identical run/config/source/branch evaluation."""
    owner = OperationalAttempt.objects.select_for_update().get(pk=effect.attempt_id)
    require_attempt_lease(owner)
    current = OperationalOperation.objects.select_for_update().get(pk=effect.pk)
    if owner.status != 'RUNNING' or current.status != 'RUNNING':
        raise ValueError('Intent requires a running effect')
    if disposition not in ('LOCAL_READY', 'DISABLED', 'PREDICATE_FALSE',
                           'RECIPIENT_SUPPRESSED', 'ATTACHMENT_UNAVAILABLE'):
        raise ValueError('Explicit local intent disposition required')
    if disposition == 'LOCAL_READY' and (subject is None or body is None):
        raise ValueError('Ready local intent requires native message content')
    values = dict(run_id=owner.run_id, configuration_id=owner.configuration_id,
        alert_name=alert_name, branch=branch, stage=stage, business_date=owner.business_date,
        source_digest=source_digest, recipients=recipients, subject=subject, body=body,
        disposition=disposition, reason=reason)
    identity = digest(dict(run=str(owner.run_id), configuration=owner.configuration_id,
        source=source_digest, alert=alert_name, branch=branch, stage=stage))
    checked = []
    for ordinal, attachment in enumerate(attachments):
        receipt = operational_io.verify_file(owner.root, attachment)
        checked.append(dict(ordinal=ordinal, **receipt))
    intent, created = OperationalAlertIntent.objects.get_or_create(identity=identity, defaults=values)
    if created:
        OperationalIntentAttachment.objects.bulk_create([
            OperationalIntentAttachment(intent=intent, **receipt) for receipt in checked])
    else:
        if any(getattr(intent, name) != value for name, value in values.items()):
            raise ValueError('Existing intent has different evaluation content')
        previous = list(intent.attachments.order_by('ordinal').values(
            'ordinal', 'relative_path', 'sha256', 'size_bytes'))
        if previous != checked:
            raise ValueError('Existing intent has different attachments')
    evaluation, _ = OperationalIntentEvaluation.objects.get_or_create(operation=current, intent=intent,
        defaults={'evaluated_digest': intent_content_digest(intent)})
    verify_intent_evaluation(evaluation)
    require_attempt_lease(owner)
    return intent
