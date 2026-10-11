"""Report-only Planning contributions; never calculation inputs."""
import uuid
from django.db import models

METRICS = ('git_parent', 'git_child', 'git_custom', 'expedite_parent',
           'expedite_child', 'expedite_custom', 'excess_review', 'excess_custom',
           'fulfillment_review', 'fulfillment_custom')


class PlanningSummaryReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey('fresh_mta.CalculationRun', on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    generation_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    business_date = models.DateField()
    status = models.CharField(max_length=12, default='BUILDING')
    metrics = models.JSONField(default=list)
    row_count = models.PositiveBigIntegerField(default=0)
    rows_digest = models.CharField(max_length=64, default='')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'source_digest',
            'generation_digest', 'recipe_digest'], name='fresh_planning_summary_identity'),
            models.CheckConstraint(condition=models.Q(status__in=['BUILDING','READY']), name='planning_summary_status')]


class PlanningSummaryContribution(models.Model):
    receipt = models.ForeignKey(PlanningSummaryReceipt, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    metric = models.CharField(max_length=24, choices=[(v, v) for v in METRICS])
    product_key = models.TextField(null=True)
    location_key = models.TextField(null=True)
    equality_profile = models.CharField(max_length=12, choices=[('raw', 'raw'), ('normalized', 'normalized')])
    occurrence_count = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['receipt', 'ordinal'],
            name='fresh_planning_summary_ordinal'),
            models.CheckConstraint(condition=models.Q(metric__in=METRICS), name='planning_summary_metric'),
            models.CheckConstraint(condition=models.Q(equality_profile__in=['raw','normalized']), name='planning_summary_profile'),
            models.CheckConstraint(condition=models.Q(occurrence_count__gt=0), name='planning_summary_positive')]
        indexes = [models.Index(fields=['receipt', 'metric'], name='fresh_planning_summary_metric')]


class PlanningSummaryAttempt(models.Model):
    run = models.ForeignKey('fresh_mta.CalculationRun', on_delete=models.PROTECT)
    identity_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=12, default='BUILDING')
    error = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(status__in=['BUILDING','READY','FAILED']),
            name='planning_summary_attempt_status')]
