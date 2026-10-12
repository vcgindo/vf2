"""Derived, run-bound reporting measures; never production calculation inputs."""
from django.db import models


class ReportAggregateReceipt(models.Model):
    run = models.OneToOneField('fresh_mta.CalculationRun', on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    members_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()
    member_count = models.PositiveBigIntegerField()


class ReportScopeMember(models.Model):
    run = models.ForeignKey('fresh_mta.CalculationRun', on_delete=models.PROTECT)
    family = models.CharField(max_length=16)
    dimension = models.CharField(max_length=8)
    class_key = models.CharField(max_length=64)
    permission_id = models.BigIntegerField()
    weight = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'family', 'dimension',
            'class_key', 'permission_id'], name='fresh_report_scope_member')]


class GuidedHistoryAggregate(models.Model):
    run = models.ForeignKey('fresh_mta.CalculationRun', on_delete=models.PROTECT)
    family = models.CharField(max_length=16)
    report_date = models.DateField()
    product_class = models.CharField(max_length=64)
    location_class = models.CharField(max_length=64)
    location_type = models.TextField(null=True)
    snapshot_age = models.BigIntegerField(null=True)
    occurrence_count = models.PositiveBigIntegerField()
    nonnull_count = models.PositiveBigIntegerField()
    nonblack_count = models.PositiveBigIntegerField()
    black_count = models.PositiveBigIntegerField()
    red_count = models.PositiveBigIntegerField()
    white_count = models.PositiveBigIntegerField()
    excess_white_count = models.PositiveBigIntegerField()
    amount = models.DecimalField(max_digits=38, decimal_places=0, null=True)
    first_ordinal = models.BigIntegerField()

    class Meta:
        indexes = [models.Index(fields=['run', 'family', 'report_date'],
                                name='fresh_guided_agg_date')]
