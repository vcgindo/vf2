"""Typed SOB/MOQ application owners from the pinned native schema.

Business identities are deliberately non-unique: native occurrence bags survive.
Raw/current, requested/history and approved inputs are distinct owners.
"""
from django.db import models
from mta.runtime.mdm_models import MdmSource


class SupplierArchive(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    run = models.ForeignKey('CalculationRun', on_delete=models.PROTECT)
    source_pk = models.PositiveBigIntegerField()
    ordinal = models.PositiveBigIntegerField()
    Input_Date = models.DateTimeField()
    SKUCode = models.CharField(max_length=50)
    SupplierCode = models.CharField(max_length=50)
    ActionType = models.IntegerField()
    Approved = models.BooleanField()
    Reverted = models.BooleanField()

    class Meta:
        abstract = True


class MdmSobArchive(SupplierArchive):
    WhCode = models.CharField(max_length=50)
    SOB = models.FloatField(null=True)


class MdmMoqWithDestinationArchive(SupplierArchive):
    WhCode = models.CharField(max_length=50)
    MOQ = models.IntegerField(null=True)


class MdmMoqWithoutDestinationArchive(SupplierArchive):
    MOQ = models.IntegerField(null=True)


class MdmSupplierConfiguration(models.Model):
    source = models.OneToOneField(MdmSource, on_delete=models.PROTECT)
    moq_format = models.CharField(max_length=32)
    upload_log_active = models.BooleanField()
    receipt_digest = models.CharField(max_length=64)
    provenance = models.JSONField()  # Bounded source identifiers, never business rows.

    class Meta:
        constraints = [models.CheckConstraint(
            condition=models.Q(moq_format__in=('WithDestLoc', 'WithoutDestLoc')),
            name='mdm_supplier_moq_format')]


class MdmSupplierTaskRevision(models.Model):
    """Internal decision generation; native task/history values stay unchanged."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    master_id = models.PositiveSmallIntegerField()
    task_id = models.CharField(max_length=50)
    revision = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('source', 'master_id', 'task_id'),
            name='mdm_supplier_task_revision_identity')]


class MdmSobUploadLog(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    SupplierCode = models.CharField(max_length=50)
    SOB = models.FloatField(null=True)
    UserName = models.CharField(max_length=256)
    ActionTimeStamp = models.DateTimeField()
    ActionId = models.IntegerField()


class MdmMoqUploadLog(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50, null=True)
    SupplierCode = models.CharField(max_length=50)
    MOQ = models.IntegerField(null=True)
    UserName = models.CharField(max_length=256)
    ActionTimeStamp = models.DateTimeField()
    ActionId = models.IntegerField()


class MdmDraftSob(models.Model):
    """Native DraftSOBMaster."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    RowId = models.IntegerField()
    DraftId = models.CharField(max_length=50)
    Error = models.TextField(null=True)
    SKUCode = models.TextField(null=True)
    WhCode = models.TextField(null=True)
    SupplierCode = models.TextField(null=True)
    SOB = models.TextField(null=True)
    Warning = models.TextField(null=True)


class MdmDraftMoq(models.Model):
    """Native DraftMOQMaster."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    RowId = models.IntegerField()
    DraftId = models.TextField()
    Error = models.TextField(null=True)
    SKUCode = models.TextField(null=True)
    WhCode = models.TextField(null=True)
    SupplierCode = models.TextField(null=True)
    MOQ = models.TextField(null=True)
    Warning = models.TextField(null=True)


class MdmSobRequested(models.Model):
    """Native TaskNMSSOB."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    SupplierCode = models.CharField(max_length=50)
    SOB = models.FloatField(null=True)
    ActionType = models.IntegerField()
    Approved = models.BooleanField()
    Reverted = models.BooleanField()
    TaskId = models.CharField(max_length=50)


class MdmSobHistory(models.Model):
    """Native TaskNMSSOBHistory."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    SupplierCode = models.CharField(max_length=50, null=True)
    SOB = models.FloatField(null=True)
    ActionType = models.IntegerField(null=True)
    TaskId = models.CharField(max_length=50)
    ApproverId = models.TextField(null=True)
    ApprovedBy = models.CharField(max_length=50, null=True)
    Status = models.CharField(max_length=50, null=True)
    Comments = models.TextField(null=True)


class MdmMoqRequested(models.Model):
    """Native TaskNMSMOQWithOrWithoutDestination."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50, null=True)
    SupplierCode = models.CharField(max_length=50, null=True)
    MOQ = models.IntegerField(null=True)
    ActionType = models.IntegerField(null=True)
    Approved = models.BooleanField(null=True)
    Reverted = models.BooleanField(null=True)
    TaskId = models.CharField(max_length=50, null=True)


class MdmMoqHistory(models.Model):
    """Native TaskNMSMOQWithOrWithoutDestinationHistory."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50, null=True)
    SupplierCode = models.CharField(max_length=50, null=True)
    MOQ = models.IntegerField(null=True)
    ActionType = models.IntegerField(null=True)
    TaskId = models.CharField(max_length=50, null=True)
    ApproverId = models.TextField(null=True)
    Status = models.CharField(max_length=50, null=True)
    Comments = models.TextField(null=True)
    ApprovedBy = models.IntegerField(null=True)


class MdmSobApproved(models.Model):
    """Native NMSSOB."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    revision = models.PositiveBigIntegerField(default=0)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    SupplierCode = models.CharField(max_length=50)
    SOB = models.FloatField(null=True)
    ActionType = models.IntegerField()
    Approved = models.BooleanField()
    Reverted = models.BooleanField()


class MdmMoqWithDestinationApproved(models.Model):
    """Native NMSMOQWithDestination."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    revision = models.PositiveBigIntegerField(default=0)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    SupplierCode = models.CharField(max_length=50)
    MOQ = models.IntegerField(null=True)
    ActionType = models.IntegerField()
    Approved = models.BooleanField()
    Reverted = models.BooleanField()


class MdmMoqWithoutDestinationApproved(models.Model):
    """Native NMSMOQWithoutDestination."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    revision = models.PositiveBigIntegerField(default=0)
    SKUCode = models.CharField(max_length=50)
    SupplierCode = models.CharField(max_length=50)
    MOQ = models.IntegerField(null=True)
    ActionType = models.IntegerField()
    Approved = models.BooleanField()
    Reverted = models.BooleanField()


class MdmSobRaw(models.Model):
    """Native SOBDataRaw."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    SKUCode = models.CharField(max_length=50, null=True)
    WHCode = models.CharField(max_length=50, null=True)
    SupplierCode = models.CharField(max_length=50, null=True)
    SupplierDescription = models.CharField(max_length=125, null=True)
    SOB = models.FloatField(null=True)


class MdmMoqRaw1(models.Model):
    """Native MOQDataRaw1."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    SKUCode = models.CharField(max_length=50, null=True)
    SupplierCode = models.CharField(max_length=50, null=True)
    SupplierDescription = models.CharField(max_length=125, null=True)
    MOQ = models.IntegerField(null=True)


class MdmMoqRaw2(models.Model):
    """Native MOQDataRaw2."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    SKUCode = models.CharField(max_length=50, null=True)
    WHCode = models.CharField(max_length=50, null=True)
    SupplierCode = models.CharField(max_length=50, null=True)
    SupplierDescription = models.CharField(max_length=125, null=True)
    MOQ = models.IntegerField(null=True)
