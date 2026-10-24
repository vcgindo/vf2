"""Worker claims and atomic business-phase evidence for scoped daily execution."""
import uuid
from django.db import models

SCOPES = tuple((value, value) for value in ('UptoBPR', 'UptoDBM', 'PostBPR', 'PostDBM'))
PHASES = tuple((value, value) for value in ('PRE_BPR', 'BPR', 'DBM', 'DAY_FINAL'))


class RunScopeAttempt(models.Model):
    """One fenced worker attempt; RELEASED does not acknowledge file readiness."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey('fresh_mta.CalculationRun', on_delete=models.PROTECT,
                            related_name='scope_attempts')
    command_key = models.CharField(max_length=120)
    attempt_no = models.PositiveIntegerField()
    recovery_of = models.OneToOneField('self', null=True, on_delete=models.PROTECT,
                                      related_name='recovery')
    scope = models.CharField(max_length=8, choices=SCOPES)
    expected_phase = models.CharField(max_length=9)
    expected_receipt_digest = models.CharField(max_length=64, blank=True)
    input_digest = models.CharField(max_length=64)
    input_manifest_digest = models.CharField(max_length=64)
    compatibility_digest = models.CharField(max_length=64)
    action_revision = models.PositiveBigIntegerField(default=0)
    worker_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    worker_reference = models.CharField(max_length=200)
    status = models.CharField(max_length=8, default='ACTIVE',
        choices=(('ACTIVE', 'ACTIVE'), ('FAILED', 'FAILED'), ('RELEASED', 'RELEASED')))
    failure = models.JSONField(default=dict)
    revision_before = models.JSONField(null=True)
    revision_after = models.JSONField(null=True)
    revision_closed = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['run', 'command_key', 'attempt_no'],
                                    name='fresh_scope_attempt_identity'),
            models.UniqueConstraint(fields=['run'], condition=models.Q(status='ACTIVE'),
                                    name='fresh_scope_one_active_worker'),
            models.CheckConstraint(condition=models.Q(status__in=('ACTIVE', 'FAILED', 'RELEASED')),
                                   name='fresh_scope_attempt_status'),
        ]


class RunPhaseAcceptance(models.Model):
    """An unsealed row is transaction-local and cannot commit or be read ready."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey('fresh_mta.CalculationRun', on_delete=models.PROTECT,
                            related_name='phase_acceptances')
    attempt = models.ForeignKey(RunScopeAttempt, on_delete=models.PROTECT,
                                related_name='phase_acceptances')
    source = models.ForeignKey('fresh_mta.MdmSource', on_delete=models.PROTECT)
    phase = models.CharField(max_length=9, choices=PHASES)
    snapshot = models.OneToOneField('fresh_mta.DailyPhaseSnapshot', null=True,
                                    on_delete=models.PROTECT)
    input_digest = models.CharField(max_length=64)
    capture_digest = models.CharField(max_length=64)
    revision_before = models.JSONField(null=True)
    metadata = models.JSONField(default=dict)
    digest = models.CharField(max_length=64, blank=True)
    state_sealed = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'phase'],
                                               name='fresh_business_phase_identity')]


class ScopePickFiles(models.Model):
    """Derived four-file receipt; accepts no business work or whole-scope readiness."""
    phase = models.OneToOneField(RunPhaseAcceptance, primary_key=True,
        on_delete=models.PROTECT, related_name='pick_files')
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    directory = models.UUIDField(default=uuid.uuid4)
    files = models.JSONField()  # finite names, byte lengths and checksums only
    digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
