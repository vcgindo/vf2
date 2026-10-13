"""Native master6 owners; business keys are nullable and not unique."""
from django.db import models
from mta.runtime.mdm_models import MdmSource


class MdmStopPipoOwner(models.Model):
    source = models.OneToOneField(MdmSource, on_delete=models.PROTECT)
    provenance = models.JSONField()  # Bounded binding metadata only.
    receipt_digest = models.CharField(max_length=64)
    root_state_digest = models.CharField(max_length=64, default='')
    closing_queue_digest = models.CharField(max_length=64)
    last_run = models.ForeignKey('CalculationRun', null=True, on_delete=models.PROTECT)
    generation = models.PositiveBigIntegerField(default=0)


class StopPair(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50, null=True)
    WhCode = models.CharField(max_length=50, null=True)

    class Meta:
        abstract = True


class MdmStopPipoQueue(StopPair):
    revision = models.PositiveBigIntegerField(default=0)


class MdmStopPipoRequested(StopPair):
    ActionType = models.IntegerField(null=True)
    Approved = models.BooleanField(null=True)
    Reverted = models.BooleanField(null=True)
    TaskId = models.CharField(max_length=50, null=True)


class MdmStopPipoHistory(StopPair):
    ActionType = models.IntegerField(null=True)
    TaskId = models.CharField(max_length=50, null=True)
    ApproverId = models.TextField(null=True)
    Status = models.CharField(max_length=50, null=True)
    Comments = models.TextField(null=True)
    ApprovedBy = models.IntegerField(null=True)


class MdmStopPipoTaskRevision(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    task_id = models.CharField(max_length=50)
    revision = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('source', 'task_id'),
            name='mdm_stop_pipo_task_revision')]


class MdmStopPipoConsumed(StopPair):
    run = models.ForeignKey('CalculationRun', on_delete=models.PROTECT)
    source_pk = models.PositiveBigIntegerField()
    revision = models.PositiveBigIntegerField()
    ordinal = models.PositiveBigIntegerField()
    cleared = models.BooleanField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=('run', 'ordinal'),
            name='mdm_stop_pipo_consumed_ordinal')]


class MdmDraftStopPipo(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    RowId = models.IntegerField()
    DraftId = models.CharField(max_length=50)
    IsSelected = models.CharField(max_length=50, null=True)
    SKUCode = models.CharField(max_length=50, null=True)
    PhaseOutSKUName = models.CharField(max_length=125, null=True)
    WHCode = models.CharField(max_length=50, null=True)
    LocationName = models.CharField(max_length=125, null=True)
    OriginalNorm = models.IntegerField(null=True)
    CurrentNorm = models.IntegerField(null=True)
    LastNormChangeDate = models.DateField(null=True)
    PhaseOutStartDate = models.DateField(null=True)
    PhaseInSkuCode = models.CharField(max_length=50, null=True)
    PhaseInSkuName = models.CharField(max_length=125, null=True)
    PhaseInCurrNorm = models.IntegerField(null=True)
    PhaseInTargetNorm = models.IntegerField(null=True)
    Warning = models.TextField(null=True)
    Error = models.TextField(null=True)
