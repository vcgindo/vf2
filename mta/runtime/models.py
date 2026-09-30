"""Single run identity and atomic checkpoint storage for the fresh engine."""
import uuid
from django.db import models


class CalculationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    input_digest = models.CharField(max_length=64)
    execution_revision = models.CharField(max_length=80)
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
