"""Typed master13 owners; native business keys intentionally retain duplicates."""
from django.db import models
from mta.runtime.mdm_models import MdmSource


class MdmForceOwner(models.Model):
    source = models.OneToOneField(MdmSource, on_delete=models.PROTECT)
    receipt_digest = models.CharField(max_length=64)
    provenance = models.JSONField()  # Bounded installation identifiers only.
    opening_digest = models.CharField(max_length=64)
    closing_digest = models.CharField(max_length=64)
    root_state_digest = models.CharField(max_length=64, default='')
    closing_log_digest = models.CharField(max_length=64, default='')
    last_run = models.ForeignKey('CalculationRun', null=True, on_delete=models.PROTECT)
    generation = models.PositiveBigIntegerField(default=0)


class ForceValues(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50, null=True)
    WhCode = models.CharField(max_length=50, null=True)
    NewNorm = models.IntegerField(null=True)

    class Meta:
        abstract = True


class MdmForceQueue(ForceValues):
    revision = models.PositiveBigIntegerField(default=0)
    Approved = models.BooleanField(null=True)
    RequestedBy = models.CharField(max_length=256, null=True)


class MdmForceRequested(ForceValues):
    RequestedBy = models.CharField(max_length=256, null=True)
    ActionType = models.IntegerField(null=True)
    Approved = models.BooleanField(null=True)
    Reverted = models.BooleanField(null=True)
    TaskId = models.CharField(max_length=50, null=True)


class MdmForceHistory(ForceValues):
    ActionType = models.IntegerField(null=True)
    TaskId = models.CharField(max_length=50, null=True)
    ApproverId = models.TextField(null=True)
    Status = models.CharField(max_length=50, null=True)
    Comments = models.TextField(null=True)
    ApprovedBy = models.CharField(max_length=50, null=True)


class MdmForceUploadLog(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WHCode = models.CharField(max_length=50)
    OldNorm = models.IntegerField(null=True)
    NewNorm = models.IntegerField(null=True)
    Approved = models.BooleanField(null=True)
    RequestedBy = models.CharField(max_length=256)
    ActionTimeStamp = models.DateTimeField()
    ActionId = models.IntegerField()


class MdmDraftForce(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    RowId = models.IntegerField()
    DraftId = models.CharField(max_length=50)
    Error = models.TextField(null=True)
    SKUCode = models.TextField(null=True)
    WhCode = models.TextField(null=True)
    NewNorm = models.TextField(null=True)
    Warning = models.TextField(null=True)


class MdmForceTaskRevision(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    task_id = models.CharField(max_length=50)
    revision = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('source', 'task_id'),
            name='mdm_force_task_revision_identity')]


class MdmForceConsumed(ForceValues):
    """Internal consumed-generation receipt, not a invented native archive."""
    run = models.ForeignKey('CalculationRun', on_delete=models.PROTECT)
    source_pk = models.PositiveBigIntegerField()
    revision = models.PositiveBigIntegerField()
    ordinal = models.PositiveBigIntegerField()
    Approved = models.BooleanField(null=True)
    RequestedBy = models.CharField(max_length=256, null=True)
    cleared = models.BooleanField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=('run', 'ordinal'),
            name='mdm_force_consumed_ordinal')]


class MdmForceDisplayOwner(models.Model):
    """Explicit acceptance fixture identity, never a calculation state owner."""
    source = models.OneToOneField(MdmSource, on_delete=models.PROTECT)
    provenance = models.JSONField()  # Bounded source/approval/digest identifiers.
    receipt_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)


class MdmForceDisplayRow(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    owner = models.CharField(max_length=20, default='Importer')
    ordinal = models.PositiveIntegerField()
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    Norm = models.IntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=('source', 'ordinal'),
            name='mdm_force_display_ordinal')]
