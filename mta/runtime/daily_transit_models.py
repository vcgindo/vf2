"""Run-owned raw and validated shipment occurrences; no aggregate substitutes."""
from django.db import models
from mta.runtime.models import CalculationRun


class _Shipment(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    SKUCode = models.CharField(max_length=50, null=True)
    CurrentLocationCode = models.CharField(max_length=50, null=True)
    LRCode = models.CharField(max_length=50, null=True)
    OrderNo = models.CharField(max_length=50, null=True)
    CreationDate = models.DateField(null=True)
    GateOutDate = models.DateField(null=True)
    InTransitQty = models.IntegerField(null=True)
    TransporterCode = models.CharField(max_length=50, null=True)
    Remark = models.TextField(null=True)
    ReportDate = models.DateField(null=True)

    class Meta:
        abstract = True


class DailyTransitRaw(_Shipment):
    ToLocationCode = models.CharField(max_length=50, null=True)
    FromLocationCode = models.CharField(max_length=50, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'],
                                               name='daily_transit_raw_ordinal')]


class DailyTransitRow(_Shipment):
    WhCode = models.CharField(max_length=50, null=True)
    ParentWhCode = models.CharField(max_length=50, null=True)
    Ageing = models.IntegerField(null=True)
    ETA = models.DateField(null=True)
    TLT = models.IntegerField(null=True)
    SLT = models.IntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'],
                                               name='daily_transit_row_ordinal')]
