"""CSV execution metadata only; native rows remain the business-state authority."""
import uuid
from django.db import models
from django.db.models import Q


class DailyFeedAttempt(models.Model):
    attempt_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    initialization = models.ForeignKey('fresh_mta.ProductionInitialization', on_delete=models.PROTECT)
    business_date = models.DateField()
    batch_id = models.CharField(max_length=120)
    request_key = models.CharField(max_length=64, unique=True)
    batch_digest = models.CharField(max_length=64)
    binding_digest = models.CharField(max_length=64)
    input_sha256 = models.CharField(max_length=64, blank=True)
    predecessor = models.ForeignKey('fresh_mta.CalculationRun', null=True, blank=True,
        related_name='csv_successor_attempts', on_delete=models.PROTECT)
    predecessor_output_digest = models.CharField(max_length=64, blank=True)
    run = models.OneToOneField('fresh_mta.CalculationRun', null=True, blank=True,
        related_name='csv_attempt', on_delete=models.PROTECT)
    status = models.CharField(max_length=16, default='RUNNING')
    phase = models.CharField(max_length=24, default='VALIDATE')
    archive_path = models.TextField()
    prior_selection_digest = models.CharField(max_length=64, blank=True)
    candidate_selection_digest = models.CharField(max_length=64, blank=True)
    error = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(status__in=(
                'RUNNING', 'REJECTED', 'COMMITTED', 'PREPARED', 'PUBLISHED', 'FAILED')),
                name='csv_attempt_status'),
            models.UniqueConstraint(fields=('initialization', 'business_date'),
                condition=Q(status__in=('RUNNING', 'COMMITTED', 'PREPARED', 'PUBLISHED')),
                name='csv_one_live_initialized_date'),
        ]
