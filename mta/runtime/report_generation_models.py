"""Typed derived-report generation attached to one immutable operational run.

This is a receipt for the existing daily preparation operation, not a scheduler
or another business run. Metadata contains shapes/digests/recipes only.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from django.db import models


class DailyReportGeneration(models.Model):
    run = models.OneToOneField('fresh_mta.CalculationRun',primary_key=True,on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=12,default='INCOMPLETE')
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    metadata = models.JSONField(default=dict)
    digest = models.CharField(max_length=64,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sealed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(status__in=['INCOMPLETE','READY']),name='daily_report_generation_status')]


class DailyReportOrderRouteSource(models.Model):
    """Original ordered route identity required by later fulfilment reports."""
    run = models.ForeignKey('fresh_mta.CalculationRun',on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    OrderKey = models.BigIntegerField()
    SrcWhCode = models.CharField(max_length=50,null=True)
    DestWhCode = models.CharField(max_length=50,null=True)
    DueDate = models.DateField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='daily_report_route_ordinal')]
