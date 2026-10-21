"""CSV execution metadata only; native rows remain the business-state authority."""
import uuid
from django.db import models
from django.db.models import Q
from mta.runtime.ingestion_models import bounded


class DailyFeedAttempt(models.Model):
    attempt_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    initialization = models.ForeignKey('fresh_mta.ProductionInitialization', on_delete=models.PROTECT)
    recovery_origin = models.ForeignKey('self',null=True,blank=True,on_delete=models.PROTECT,
        related_name='finite_recoveries')
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
    accepted_facts = models.JSONField(default=dict)
    prepared_context = models.JSONField(default=dict)
    certification = models.ForeignKey('fresh_mta.InitializationCertification', null=True,
        blank=True, related_name='daily_feed_attempts', on_delete=models.PROTECT)
    master_revision = models.ForeignKey('fresh_mta.MasterInputRevision', null=True,
        blank=True, related_name='daily_feed_attempts', on_delete=models.PROTECT)
    error = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(status__in=(
                'RUNNING', 'REJECTED', 'COMMITTED', 'PREPARED', 'PUBLISHED', 'FAILED')),
                name='csv_attempt_status'),
            models.UniqueConstraint(fields=('initialization', 'business_date'),
                condition=Q(status__in=('RUNNING', 'COMMITTED', 'PREPARED', 'PUBLISHED'),recovery_origin__isnull=True),
                name='csv_one_live_initialized_date'),
            models.UniqueConstraint(fields=('recovery_origin',),condition=Q(recovery_origin__isnull=False),
                name='csv_one_finite_origin'),
            bounded('accepted_facts', 'csv_accepted_facts_bound'),
            bounded('prepared_context', 'csv_prepared_context_bound'),
        ]
