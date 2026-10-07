"""Append-only daily RRR sources for the approved offline21-day scenario."""
from django.db import models
from mta.runtime.models import CalculationRun


class OfflineRrrColourSource(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    input_digest = models.CharField(max_length=64)
    artifact_sha256 = models.CharField(max_length=64)
    scenario_sha256 = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    source_inputs_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class OfflineRrrColourRow(models.Model):
    receipt = models.ForeignKey(OfflineRrrColourSource, on_delete=models.PROTECT,
                                related_name='rows')
    ordinal = models.PositiveBigIntegerField()

    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    ParentWhCode = models.CharField(max_length=50)
    AllocationFor = models.CharField(max_length=10, null=True)
    Norm = models.IntegerField(null=True)
    VirtualNorm = models.IntegerField(null=True)
    Stock = models.IntegerField(null=True)
    GIT = models.IntegerField(null=True)
    LeftoverParentStock = models.IntegerField(null=True)
    Requirement = models.IntegerField(null=True)
    TOBlack_ReqQty = models.IntegerField()
    TOR_ReqQty = models.IntegerField()
    TOY_ReqQty = models.IntegerField()
    TOGreen_ReqQty = models.IntegerField()
    TOBlue_ReqQty = models.IntegerField()
    RationedQty = models.IntegerField(null=True)
    RationedCasePacks = models.IntegerField(null=True)
    TOBlack_AllocQty = models.IntegerField()
    TOR_AllocQty = models.IntegerField()
    TOY_AllocQty = models.IntegerField()
    TOGreen_AllocQty = models.IntegerField()
    TOBlue_AllocQty = models.IntegerField()
    DispatchColor = models.CharField(max_length=10, null=True)
    AdvAllocDone = models.IntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=('receipt', 'ordinal'), name='offline_rrr_source_ordinal')]

