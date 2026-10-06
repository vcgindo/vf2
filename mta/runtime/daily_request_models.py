"""Explicit application-owned Expedite request source and frozen daily capture."""
from django.db import models
from mta.runtime.models import CalculationRun


class DailyRequestOwner(models.Model):
    # One application database owns one live request population.
    name = models.CharField(max_length=32, primary_key=True)
    provenance = models.JSONField()
    provenance_digest = models.CharField(max_length=64)
    revision = models.PositiveBigIntegerField(default=0)


class RequestFields(models.Model):
    SKUCode = models.CharField(max_length=50, null=True)
    WhCode = models.CharField(max_length=50, null=True)
    ParentWhCode = models.CharField(max_length=50, null=True)
    Request = models.TextField(null=True)
    RequestDate = models.DateTimeField(null=True)
    Action = models.TextField(null=True)
    ActionDate = models.DateTimeField(null=True)
    # Retained deployed metadata, not the older integer DDL.
    UserId = models.TextField(null=True)
    ETA = models.DateTimeField(null=True)

    class Meta:
        abstract = True


class DailyOpenRequest(RequestFields):
    owner = models.ForeignKey(DailyRequestOwner, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=('owner', 'ordinal'),
                                               name='daily_request_owner_ordinal')]


class DailyRequestCapture(models.Model):
    run = models.OneToOneField(CalculationRun, on_delete=models.PROTECT,
                               primary_key=True)
    owner = models.ForeignKey(DailyRequestOwner, on_delete=models.PROTECT)
    revision = models.PositiveBigIntegerField()
    provenance_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()


class DailyCapturedRequest(RequestFields):
    capture = models.ForeignKey(DailyRequestCapture, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=('capture', 'ordinal'),
                                               name='daily_request_capture_ordinal')]
