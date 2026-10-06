"""Typed master-3 state; source occurrences intentionally have no pair key."""
from django.db import models

from mta.runtime.mdm_models import MdmSource


def _source_occurrence(cls):
    cls.add_to_class('source', models.ForeignKey(MdmSource, on_delete=models.PROTECT))
    cls.add_to_class('owner', models.CharField(max_length=32))
    cls.add_to_class('ordinal', models.PositiveBigIntegerField())
    return cls


def _text(cls, names, *, null=True, max_length=50):
    for name in names:
        cls.add_to_class(name, models.CharField(max_length=max_length, null=null))


def _integer(cls, names, *, null=True):
    for name in names:
        cls.add_to_class(name, models.IntegerField(null=null))


def _decimal(cls, names):
    for name in names:
        cls.add_to_class(name, models.DecimalField(max_digits=10, decimal_places=2, null=True))


class SkuLocValues(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    ParentWhCode = models.CharField(max_length=50, null=True)
    Norm = models.IntegerField(null=True)
    MinNorm = models.IntegerField(null=True)
    RLT = models.IntegerField(null=True)
    RCP = models.IntegerField(null=True)
    GCP = models.IntegerField(null=True)
    OCP = models.IntegerField(null=True)
    PackSize = models.IntegerField(null=True)
    SpikeThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PSOThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    FGRMFlag = models.CharField(max_length=10, null=True)
    DBMActive = models.BooleanField(null=True)
    StockPercentForRat = models.IntegerField(null=True)
    NormPercentReservation = models.IntegerField(null=True)
    MinOrderCount = models.IntegerField(null=True)

    class Meta:
        abstract = True


_text(SkuLocValues, ('SKULocAtt%02d' % i for i in range(1, 16)))


@_source_occurrence
class MdmSkuLocCurrent(models.Model):
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    Norm = models.IntegerField()
    MinNorm = models.IntegerField()
    RLT = models.IntegerField()
    RCP = models.IntegerField()
    GCP = models.IntegerField()
    OCP = models.IntegerField(null=True)
    ParentWhCode = models.CharField(max_length=50)
    SKUIntroDate = models.DateField()
    SKUDescription = models.CharField(max_length=125)
    WHDescription = models.CharField(max_length=125)
    ParentDescription = models.CharField(max_length=125)
    PackSize = models.IntegerField()
    SpikeThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    DefaultSpikeThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PSOThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    DefaultPSOThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    FGRMFlag = models.CharField(max_length=10, null=True)
    StockPercentForRationing = models.IntegerField()
    NormPercentReservation = models.IntegerField()
    MinOrderCount = models.IntegerField(null=True)
    DBMActive = models.BooleanField()
    ElephantOrderCapping = models.IntegerField(null=True)
    Weight = models.DecimalField(max_digits=13, decimal_places=3, null=True)
    Volume = models.DecimalField(max_digits=13, decimal_places=3, null=True)
    LocationType = models.CharField(max_length=50, null=True)
    LogisticsLocation = models.CharField(max_length=50, null=True)


_text(MdmSkuLocCurrent, ('SL%d' % i for i in range(1, 6)))
_text(MdmSkuLocCurrent, ('LL%d' % i for i in range(1, 6)))
_text(MdmSkuLocCurrent, ('SKUAtt%02d' % i for i in range(1, 16)))
_text(MdmSkuLocCurrent, ('LocAtt%02d' % i for i in range(1, 16)))
_text(MdmSkuLocCurrent, ('SKULocAtt%02d' % i for i in range(1, 16)))


@_source_occurrence
class MdmSkuLocPair(models.Model):
    SKUCode = models.CharField(max_length=50)
    LocCode = models.CharField(max_length=50)
    PackSize = models.IntegerField()
    SpikeThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PSOThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    FGRMFlag = models.CharField(max_length=10, null=True)
    StockPercentForRationing = models.IntegerField()
    NormPercentReservation = models.IntegerField()
    NonNMS = models.BooleanField()


_text(MdmSkuLocPair, ('c%d' % i for i in range(1, 16)))


@_source_occurrence
class MdmSkuLocMasterPair(models.Model):
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    Norm = models.IntegerField()
    MinNorm = models.IntegerField()
    RLT = models.IntegerField()
    RCP = models.IntegerField()
    GCP = models.IntegerField()
    OCP = models.IntegerField(null=True)
    MinOrderCount = models.IntegerField(null=True)
    ParentWhCode = models.CharField(max_length=50, null=True)
    SKUIntroDate = models.DateField(null=True)


class MdmSkuLocAddRequested(SkuLocValues):
    ParentWhCode = models.CharField(max_length=50)
    StockPercentForRat = models.IntegerField(null=True, db_default=100)
    NormPercentReservation = models.IntegerField(null=True, db_default=0)
    Approved = models.BooleanField(db_default=True)
    TaskId = models.CharField(max_length=50, null=True, db_index=True)


class SkuLocModifyValues(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    ParentWhCode = models.CharField(max_length=50)
    MinNorm = models.IntegerField(null=True)
    RLT = models.IntegerField(null=True)
    RCP = models.IntegerField(null=True)
    GCP = models.IntegerField(null=True)
    OCP = models.IntegerField(null=True)
    PackSize = models.IntegerField(null=True)
    SpikeThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PSOThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    FGRMFlag = models.CharField(max_length=10, null=True)
    DBMActive = models.BooleanField(null=True)
    StockPercentForRat = models.IntegerField(null=True)
    NormPercentReservation = models.IntegerField(null=True)
    MinOrderCount = models.IntegerField(null=True)

    class Meta:
        abstract = True


_text(SkuLocModifyValues, ('SKULocAtt%02d' % i for i in range(1, 16)))


class MdmSkuLocModifyRequested(SkuLocModifyValues):
    Approved = models.BooleanField()
    TaskId = models.CharField(max_length=50, db_index=True)


class MdmSkuLocRemoveRequested(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    Approved = models.BooleanField()
    TaskId = models.CharField(max_length=50, null=True, db_index=True)


class MdmSkuLocHistory(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    ParentWhCode = models.CharField(max_length=50, null=True)
    Norm = models.IntegerField(null=True)
    MinNorm = models.IntegerField(null=True)
    RLT = models.IntegerField(null=True)
    RCP = models.IntegerField(null=True)
    GCP = models.IntegerField(null=True)
    OCP = models.IntegerField(null=True)
    SKUDescription = models.CharField(max_length=200, null=True)
    WHDescription = models.CharField(max_length=200, null=True)
    ParentDescription = models.CharField(max_length=125, null=True)
    PackSize = models.IntegerField(null=True)
    SpikeThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    DefaultSpikeThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PSOThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    DefaultPSOThreshold = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    FGRMFlag = models.CharField(max_length=10, null=True)
    StockPercentForRationing = models.IntegerField(null=True)
    NormPercentReservation = models.IntegerField(null=True)
    MinOrderCount = models.IntegerField(null=True)
    DBMActive = models.BooleanField(null=True)
    ElephantOrderCapping = models.IntegerField(null=True)
    Weight = models.DecimalField(max_digits=13, decimal_places=3, null=True)
    Volume = models.DecimalField(max_digits=13, decimal_places=3, null=True)
    TaskId = models.CharField(max_length=50, db_index=True)
    ApproverId = models.TextField(null=True)
    Status = models.CharField(max_length=50, null=True)
    Comments = models.TextField(null=True)
    ApprovedBy = models.CharField(max_length=50, null=True)
    SKUIntroDate = models.DateField(null=True)


_text(MdmSkuLocHistory, ('SKULocAtt%02d' % i for i in range(1, 16)))


class MdmSkuLocAddApproved(SkuLocValues):
    ParentWhCode = models.CharField(max_length=50)
    Norm = models.IntegerField()
    MinNorm = models.IntegerField()
    RLT = models.IntegerField()
    RCP = models.IntegerField()
    GCP = models.IntegerField()
    PackSize = models.IntegerField()
    DBMActive = models.BooleanField()
    StockPercentForRat = models.IntegerField()
    NormPercentReservation = models.IntegerField()
    Approved = models.BooleanField()


class MdmSkuLocModifyApproved(SkuLocModifyValues):
    ParentWhCode = models.CharField(max_length=50, null=True)
    Approved = models.BooleanField()


class MdmSkuLocRemoveApproved(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    Approved = models.BooleanField()


class MdmDraftSkuLoc(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    RowId = models.IntegerField()
    DraftId = models.CharField(max_length=50, db_index=True)
    Error = models.TextField(null=True)
    Warning = models.TextField(null=True)


for _name in (
    'SKUCode', 'WhCode', 'ParentWhCode', 'ParentDescription', 'Norm', 'MinNorm',
    'RLT', 'RCP', 'GCP', 'PackSize', 'SpikeThreshold', 'DefaultPSOThreshold',
    'PSOThreshold', 'DBMActive', 'FGRMFlag', 'NormPercentReservation',
    'SKUDescription', 'WHDescription', 'DefaultSpikeThreshold', 'OCP',
    *('SKULocAtt%02d' % i for i in range(1, 16)), 'MinOrderCount',
    'StockPercentForRat'):
    MdmDraftSkuLoc.add_to_class(_name, models.TextField(null=True))
