"""SKU application ownership, separate from immutable calculation publications.

Business columns mirror the retained Importer types. Synthetic primary keys
identify occurrences only; native SKU/draft identifiers are not made unique.
"""
from django.db import models
from django.db.models.functions import Cast, Lower


def sku_lookup(name):
    return models.Index(models.F('source'), models.F('owner'),
        Lower(models.Func(Cast('SKUCode',models.TextField()),models.Value(' '),function='rtrim')),
        name=name)


class MdmSource(models.Model):
    """Explicitly installed master source, with bounded provenance metadata."""
    digest = models.CharField(max_length=64, unique=True)
    database_name = models.CharField(max_length=128)
    dll_digest = models.CharField(max_length=64)
    implementation_digest = models.CharField(max_length=64, blank=True)
    receipt = models.JSONField()
    installed_at = models.DateTimeField(auto_now_add=True)


class MdmSkuAttributes(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    owner = models.CharField(max_length=16, default='Importer')
    ordinal = models.PositiveBigIntegerField()
    SKUCode = models.CharField(max_length=50)
    ElephantOrderCapping = models.IntegerField(null=True)
    Weight = models.DecimalField(max_digits=13, decimal_places=3, null=True)
    Volume = models.DecimalField(max_digits=13, decimal_places=3, null=True)

    class Meta:
        indexes = [sku_lookup('mdm_sku_attr_lookup')]


for _name in (*('SL' + str(i) for i in range(1, 6)), *('c' + str(i) for i in range(1, 16))):
    MdmSkuAttributes.add_to_class(_name, models.CharField(max_length=50, null=True))


class MdmSkuDescription(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    owner = models.CharField(max_length=16, default='Importer')
    ordinal = models.PositiveBigIntegerField()
    SKUCode = models.CharField(max_length=50)
    SKUDescription = models.CharField(max_length=125)

    class Meta:
        indexes = [sku_lookup('mdm_sku_desc_lookup')]


class MdmDraft(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    DraftId = models.CharField(max_length=50, db_index=True)
    ActionType = models.IntegerField(null=True)
    Masters = models.TextField(null=True)
    Userid = models.TextField(null=True)
    LastModifiedDateTime = models.DateTimeField(null=True)
    SearchKeys = models.TextField(null=True)
    CreationDateTime = models.DateTimeField(null=True)


class MdmDraftMaster(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    DraftId = models.CharField(max_length=50, db_index=True)
    MasterId = models.IntegerField(null=True)
    GridState = models.TextField(null=True)
    Status = models.TextField(null=True)


class MdmDraftSku(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    RowId = models.IntegerField()
    Draftid = models.CharField(max_length=50, db_index=True)
    Error = models.TextField(null=True)
    Warning = models.TextField(null=True)


# Drafts deliberately preserve invalid numeric text and NULLs for revalidation.
for _name in ('SKUCode', 'SKUDescription', 'ElephantOrderCapping', 'Weight', 'Volume',
              *('c' + str(i) for i in range(1, 16)), *('SL' + str(i) for i in range(1, 6))):
    MdmDraftSku.add_to_class(_name, models.TextField(null=True))


class MdmTask(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    TaskID = models.CharField(max_length=50, null=True, db_index=True)
    PendingSince = models.DateTimeField(null=True)
    TaskName = models.CharField(max_length=50, null=True)
    ApproverId = models.TextField(null=True)
    ApproversName = models.TextField(null=True)
    RequesterId = models.TextField(null=True)
    RequesterName = models.CharField(max_length=50, null=True)
    TaskStatus = models.CharField(max_length=50, null=True)
    MasterId = models.CharField(max_length=200, null=True)
    Actiontype = models.IntegerField(null=True)
    ColumnList = models.CharField(max_length=500, null=True)


class MdmSubTask(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    TaskID = models.CharField(max_length=50, null=True, db_index=True)
    ApproverId = models.CharField(max_length=50, null=True)
    ApproverName = models.CharField(max_length=50, null=True)
    TaskStatus = models.CharField(max_length=50, null=True)
    ApprovedOrRejectedDate = models.CharField(max_length=50, null=True)
    DBUpdatedDate = models.CharField(max_length=50, null=True)


class SkuWorkflowRow(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    SKUDescription = models.CharField(max_length=125, null=True)
    ElephantOrderCapping = models.IntegerField(null=True)
    Weight = models.DecimalField(max_digits=13, decimal_places=3, null=True)
    Volume = models.DecimalField(max_digits=13, decimal_places=3, null=True)

    class Meta:
        abstract = True


for _name in (*('SL' + str(i) for i in range(1, 6)), *('c' + str(i) for i in range(1, 16))):
    SkuWorkflowRow.add_to_class(_name, models.CharField(max_length=50, null=True))


class MdmSkuRequested(SkuWorkflowRow):
    TaskId = models.CharField(max_length=50, null=True, db_index=True)
    ActionType = models.IntegerField()
    Approved = models.BooleanField()
    Reverted = models.BooleanField()


class MdmSkuHistory(SkuWorkflowRow):
    TaskId = models.CharField(max_length=50, null=True, db_index=True)
    ApproverId = models.TextField(null=True)
    ApprovedBy = models.IntegerField(null=True)
    Status = models.CharField(max_length=50, null=True)
    Comments = models.TextField(null=True)


class MdmSkuApproved(SkuWorkflowRow):
    SKUDescription = models.CharField(max_length=125)
    ActionType = models.IntegerField()
    Approved = models.BooleanField()
    Reverted = models.BooleanField()


class MdmSkuUploadLog(SkuWorkflowRow):
    UserName = models.CharField(max_length=256)
    ActionTimeStamp = models.DateTimeField()
    ActionId = models.IntegerField()


class MdmSkuUse(models.Model):
    """Read-only source occurrences for SKU delete eligibility, not a new family."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    SKUCode = models.CharField(max_length=50, null=True, db_index=True)


class MdmFamilySource(models.Model):
    """Pinned additions to the shared application, without changing SKU's receipt."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    master_id = models.PositiveSmallIntegerField(choices=((2, 'Location'), (3, 'SKU Location')))
    digest = models.CharField(max_length=64)
    receipt = models.JSONField()
    installed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('source', 'master_id'),
                                               name='mdm_family_install_once')]


class LocationFields(models.Model):
    WHCode = models.CharField(max_length=50)
    LocationType = models.CharField(max_length=50, null=True)
    LogisticsLocation = models.CharField(max_length=50, null=True)

    class Meta:
        abstract = True


for _name in (*('LL' + str(i) for i in range(1, 6)), *('c' + str(i) for i in range(1, 16))):
    LocationFields.add_to_class(_name, models.CharField(max_length=50, null=True))


class MdmLocationAttributes(LocationFields):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    owner = models.CharField(max_length=16)
    ordinal = models.PositiveBigIntegerField()


class MdmLocationDescription(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    owner = models.CharField(max_length=16)
    ordinal = models.PositiveBigIntegerField()
    WHCode = models.CharField(max_length=50)
    WHDescription = models.CharField(max_length=125)


class LocationWorkflowRow(LocationFields):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    WHDescription = models.CharField(max_length=125)

    class Meta:
        abstract = True


class MdmLocationRequested(LocationWorkflowRow):
    TaskId = models.CharField(max_length=50, null=True, db_index=True)
    ActionType = models.IntegerField()
    Approved = models.BooleanField()
    Reverted = models.BooleanField()


class MdmLocationHistory(LocationWorkflowRow):
    TaskId = models.CharField(max_length=50, db_index=True)
    ActionType = models.IntegerField(null=True)
    ApproverId = models.TextField(null=True)
    ApprovedBy = models.IntegerField(null=True)
    Status = models.CharField(max_length=50, null=True)
    Comments = models.TextField(null=True)


class MdmLocationApproved(LocationWorkflowRow):
    ActionType = models.IntegerField()
    Approved = models.BooleanField()
    Reverted = models.BooleanField()


class MdmDraftLocation(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    RowId = models.IntegerField()
    DraftId = models.TextField(db_index=True)
    Error = models.TextField(null=True)
    Warning = models.TextField(null=True)


for _name in ('WHCode', 'WHDescription', 'LogisticsLocation', 'LocationType',
              *('c' + str(i) for i in range(1, 16)), *('LL' + str(i) for i in range(1, 6))):
    MdmDraftLocation.add_to_class(_name, models.TextField(null=True))


class MdmLocationUploadLog(LocationFields):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    WHDescription = models.CharField(max_length=125, null=True)
    UserName = models.CharField(max_length=256)
    ActionTimeStamp = models.DateTimeField()
    ActionId = models.IntegerField()


class MdmLocationUse(models.Model):
    """Distinct native delete guards retain their respective source identities."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    use_kind = models.CharField(max_length=6, choices=(('direct', 'direct'), ('parent', 'parent')))
    ordinal = models.PositiveBigIntegerField()
    WHCode = models.CharField(max_length=50)
