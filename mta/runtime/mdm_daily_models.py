"""Typed ownership for one immutable MDM revision consumed by a daily run."""
from django.db import models

from mta.runtime.mdm_models import MdmSource
from mta.runtime.models import CalculationRun


class MdmDailyInputCapture(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True,
                               on_delete=models.PROTECT, related_name='mdm_input_capture')
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    origin = models.ForeignKey('self', null=True, on_delete=models.PROTECT,
                               related_name='retries')
    request_digest = models.CharField(max_length=64)
    revision_digest = models.CharField(max_length=64)
    sku_revision_digest = models.CharField(max_length=64)
    location_revision_digest = models.CharField(max_length=64)
    skuloc_revision_digest = models.CharField(max_length=64)
    sql_digest = models.CharField(max_length=64)
    nms_active = models.BooleanField()
    status = models.CharField(max_length=16, default='CAPTURED')
    captured_at = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=models.Q(status__in=('CAPTURED', 'CONSUMED')),
            name='mdm_daily_capture_status')]


class MdmDailyInputOccurrence(models.Model):
    capture = models.ForeignKey(MdmDailyInputCapture, on_delete=models.PROTECT,
                                related_name='occurrences')
    family = models.CharField(max_length=16)
    queue_kind = models.CharField(max_length=16)
    source_pk = models.PositiveBigIntegerField()
    ordinal = models.PositiveBigIntegerField()
    sku_code = models.CharField(max_length=50, null=True)
    location_code = models.CharField(max_length=50, null=True)
    action_type = models.IntegerField(null=True)
    approved = models.BooleanField()
    reverted = models.BooleanField(null=True)
    row_digest = models.CharField(max_length=64)
    archived_at = models.DateTimeField(null=True)
    cleared_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=('capture', 'family', 'queue_kind', 'source_pk'),
            name='mdm_daily_occurrence_identity')]


class MdmDailyInputTask(models.Model):
    """A native task/subtask transition selected with the captured queue revision."""
    capture = models.ForeignKey(MdmDailyInputCapture, on_delete=models.PROTECT,
                                related_name='task_occurrences')
    family = models.CharField(max_length=16)
    task_id = models.CharField(max_length=50)
    task_pk = models.PositiveBigIntegerField()
    subtask_pk = models.PositiveBigIntegerField()
    action_type = models.IntegerField(null=True)
    prior_subtask_status = models.CharField(max_length=50)
    task_digest = models.CharField(max_length=64)
    history_digest = models.CharField(max_length=64)
    transitioned_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=('capture', 'subtask_pk'), name='mdm_daily_task_identity')]


class MdmDailyInputHistory(models.Model):
    """Pending Add history which native status processing rejects as existing."""
    capture = models.ForeignKey(MdmDailyInputCapture, on_delete=models.PROTECT,
                                related_name='history_occurrences')
    family = models.CharField(max_length=16)
    history_pk = models.PositiveBigIntegerField()
    task_id = models.CharField(max_length=50)
    row_digest = models.CharField(max_length=64)
    transitioned_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=('capture', 'family', 'history_pk'),
            name='mdm_daily_history_identity')]


class MdmDailyArchiveBase(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    occurrence = models.OneToOneField(MdmDailyInputOccurrence, on_delete=models.PROTECT)
    Input_Date = models.DateTimeField(db_index=True)

    class Meta:
        abstract = True


class MdmDailySkuArchive(MdmDailyArchiveBase):
    pass


class MdmDailyLocationArchive(MdmDailyArchiveBase):
    pass


class MdmDailySkuLocAddArchive(MdmDailyArchiveBase):
    pass


class MdmDailySkuLocModifyArchive(MdmDailyArchiveBase):
    pass


class MdmDailySkuLocRemoveArchive(MdmDailyArchiveBase):
    pass


from mta.runtime.mdm_models import MdmSkuApproved, MdmLocationApproved
from mta.runtime.mdm_skuloc_models import (MdmSkuLocAddApproved,
    MdmSkuLocModifyApproved, MdmSkuLocRemoveApproved)
for _archive, _source_model in (
        (MdmDailySkuArchive, MdmSkuApproved),
        (MdmDailyLocationArchive, MdmLocationApproved),
        (MdmDailySkuLocAddArchive, MdmSkuLocAddApproved),
        (MdmDailySkuLocModifyArchive, MdmSkuLocModifyApproved),
        (MdmDailySkuLocRemoveArchive, MdmSkuLocRemoveApproved)):
    for _field in _source_model._meta.fields:
        if _field.name not in ('id', 'source'):
            _archive.add_to_class(_field.name, _field.clone())
