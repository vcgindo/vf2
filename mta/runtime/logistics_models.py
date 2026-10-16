"""Operational annotations/history, separate from immutable daily source rows."""
from django.db import models
from mta.runtime.models import CalculationRun


class LogisticsHistoryOwner(models.Model):
    name = models.CharField(max_length=32, primary_key=True)
    provenance = models.JSONField()
    provenance_digest = models.CharField(max_length=64)
    next_ordinal = models.PositiveBigIntegerField(default=0)
    revision = models.PositiveBigIntegerField(default=0)


class TransitLiveGeneration(models.Model):
    run = models.OneToOneField(CalculationRun, on_delete=models.PROTECT, primary_key=True)
    source_digest = models.CharField(max_length=64)
    revision = models.PositiveBigIntegerField(default=0)


class TransitAnnotation(models.Model):
    generation = models.ForeignKey(TransitLiveGeneration, on_delete=models.PROTECT)
    source_ordinal = models.PositiveBigIntegerField()
    CurrentLocationCode = models.CharField(max_length=50, null=True)
    ETA = models.DateField(null=True)
    Remark = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('generation', 'source_ordinal'),
                                               name='transit_annotation_occurrence')]


class TransitRemarkHistory(models.Model):
    owner = models.ForeignKey(LogisticsHistoryOwner, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    generation = models.ForeignKey(TransitLiveGeneration, on_delete=models.PROTECT)
    OrderNo = models.CharField(max_length=50, null=True)
    SKUCode = models.CharField(max_length=50, null=True)
    WhCode = models.CharField(max_length=50, null=True)
    ParentWHCode = models.CharField(max_length=50, null=True)
    Remarks = models.TextField(null=True)
    CurrentLocation = models.TextField(null=True)
    ETA = models.DateField(null=True)
    UserId = models.IntegerField(null=True)
    RemarksDate = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('owner', 'ordinal'),
                                               name='transit_history_occurrence')]


class ExpediteRemarkHistory(models.Model):
    owner = models.ForeignKey(LogisticsHistoryOwner, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    SKUCode = models.CharField(max_length=50, null=True)
    WHCode = models.CharField(max_length=50, null=True)
    Remark = models.TextField(null=True)
    UserId = models.TextField(null=True)
    RemarkDate = models.DateTimeField(null=True)
    ETA = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('owner', 'ordinal'),
                                               name='expedite_history_occurrence')]
