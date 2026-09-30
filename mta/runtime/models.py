"""Single run identity and atomic checkpoint storage for the fresh engine."""
import uuid
from django.db import models


class CalculationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    input_digest = models.CharField(max_length=64)
    execution_revision = models.CharField(max_length=80)
    kind = models.CharField(max_length=24, default='CURRENT_DAY')
    opening_key = models.CharField(max_length=64, null=True, blank=True, unique=True)
    predecessor = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='successors')
    business_date = models.DateField()
    input_payload = models.JSONField()
    status = models.CharField(max_length=16, default='RUNNING')
    output_digest = models.CharField(max_length=64, blank=True)
    output_roster = models.JSONField(default=list)
    failure = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['input_digest', 'execution_revision'], name='fresh_run_identity')]


class Checkpoint(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT, related_name='checkpoints')
    name = models.CharField(max_length=100)
    rows = models.JSONField()
    row_count = models.PositiveIntegerField()
    digest = models.CharField(max_length=64)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'name'], name='fresh_checkpoint_identity')]


class RunCommand(models.Model):
    """Ordered API actions on immutable daily output, consumed by its next run."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT, related_name='commands')
    idempotency_key = models.CharField(max_length=120)
    payload = models.JSONField()
    digest = models.CharField(max_length=64)
    before_digest = models.CharField(max_length=64)
    after_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','idempotency_key'], name='fresh_command_identity')]
