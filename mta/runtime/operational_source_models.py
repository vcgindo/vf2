"""Minimal immutable producer sources missing from retained Cohort1 runs."""
from django.db import models
from mta.runtime.models import CalculationRun


class OperationalCaptureAuthorization(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    policy = models.CharField(max_length=80)
    input_digest = models.CharField(max_length=64)


class OperationalInputSource(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    policy = models.CharField(max_length=80)
    input_digest = models.CharField(max_length=64)
    schema_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    # Four bounded typed-image receipts only. Business cells live in mta_state.
    images = models.JSONField()


class OperationalForceSource(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    policy = models.CharField(max_length=80)
    input_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    # Three typed image receipts; no business cells in this metadata.
    images = models.JSONField()


class OperationalCalculationSource(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    policy = models.CharField(max_length=80)
    input_digest = models.CharField(max_length=64)
    calculation_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    band_count = models.PositiveBigIntegerField()
    stock_count = models.PositiveBigIntegerField()


class OperationalRequirementBand(models.Model):
    source = models.ForeignKey(OperationalCalculationSource, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    SKUCode = models.TextField()
    WhCode = models.TextField()
    ParentWhCode = models.TextField(null=True)
    OrderReqBlack = models.BigIntegerField(null=True)
    OrderReqRed = models.BigIntegerField(null=True)
    OrderReqYellow = models.BigIntegerField(null=True)
    OrderReqGreen = models.BigIntegerField(null=True)
    OrderReqBlue = models.BigIntegerField(null=True)
    NormReqBlack = models.BigIntegerField(null=True)
    NormReqRed = models.BigIntegerField(null=True)
    NormReqYellow = models.BigIntegerField(null=True)
    NormReqGreen = models.BigIntegerField(null=True)
    OrderBlackBand = models.BigIntegerField(null=True)
    OrderRedBand = models.BigIntegerField(null=True)
    OrderYellowBand = models.BigIntegerField(null=True)
    OrderGreenBand = models.BigIntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['source', 'ordinal'], name='op_band_source_ordinal')]


class OperationalAdvanceStock(models.Model):
    source = models.ForeignKey(OperationalCalculationSource, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    sku_code = models.TextField()
    source_location_code = models.TextField()
    allocated_quantity = models.BigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['source', 'ordinal'], name='op_stock_source_ordinal')]
