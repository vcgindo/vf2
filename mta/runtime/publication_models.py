"""Finite daily UI publication receipts, separate from engine success."""
from django.db import models
from mta.runtime.models import CalculationRun


class DailySourceReceipt(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    input_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    images = models.JSONField(default=dict)  # named typed-image metadata only
    images_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class DailyColorSequence(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    Color = models.TextField()
    SequenceNo = models.IntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'], name='daily_color_sequence_ord')]


class DailyUiPublication(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    output_digest = models.CharField(max_length=64)
    source_digest = models.CharField(max_length=64)
    configuration_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default='INCOMPLETE')
    layers = models.JSONField(default=dict)  # finite layer receipts, never business rows
    seal_digest = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sealed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(status__in=['INCOMPLETE', 'READY']),
                                               name='daily_ui_publication_status')]


class DailyUiPublicationAttempt(models.Model):
    publication = models.ForeignKey(DailyUiPublication, on_delete=models.PROTECT, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=16, default='BUILDING')
    layers = models.JSONField(default=dict)  # bounded diagnostics/receipt identities only

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(status__in=['BUILDING', 'FAILED', 'READY']),
                                               name='daily_ui_attempt_status')]
