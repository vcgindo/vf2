"""Native Seasonality owners; duplicate business keys remain separate rows."""
from django.db import models
from mta.runtime.mdm_models import MdmSource


class MdmSeasonOwner(models.Model):
    source = models.OneToOneField(MdmSource, on_delete=models.PROTECT)
    provenance = models.JSONField()  # Bounded installation identity, not state.
    receipt_digest = models.CharField(max_length=64)
    root_state_digest = models.CharField(max_length=64)
    closing_queue_digest = models.CharField(max_length=64)
    closing_current_digest = models.CharField(max_length=64)
    last_run = models.ForeignKey('CalculationRun', null=True, on_delete=models.PROTECT)
    generation = models.PositiveBigIntegerField(default=0)


class SeasonValues(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    StartDate = models.DateField()
    EndDate = models.DateField(null=True)
    TargetNorm = models.IntegerField(null=True)
    DeltaNormPercentage = models.IntegerField(null=True)
    UpperLowerCap = models.IntegerField(null=True)
    BuildupDuration = models.IntegerField(null=True)
    ActivateDBM = models.BooleanField(null=True)

    class Meta:
        abstract = True


class SeasonCalculated(SeasonValues):
    OrigNorm = models.IntegerField(null=True)
    NewNorm = models.IntegerField(null=True)
    ActivateDBM = models.BooleanField()
    Type = models.IntegerField()
    Comment = models.CharField(max_length=100, null=True)
    LastProcessedOn = models.DateField(null=True)

    class Meta:
        abstract = True


class MdmSeasonQueue(SeasonValues):
    Approved = models.BooleanField(null=True)
    revision = models.PositiveBigIntegerField(default=0)


class MdmSeasonCurrent(SeasonCalculated):
    Status = models.IntegerField()
    revision = models.PositiveBigIntegerField(default=0)
    ordinal = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=('source', 'ordinal'),
            name='mdm_season_current_ordinal')]


class MdmSeasonRequested(SeasonValues):
    CurrentNorm = models.IntegerField(null=True)
    ActionType = models.IntegerField(null=True)
    Approved = models.BooleanField(null=True)
    Reverted = models.BooleanField(null=True)
    TaskId = models.CharField(max_length=50, null=True)


class MdmSeasonHistory(SeasonValues):
    CurrentNorm = models.IntegerField(null=True)
    ActionType = models.IntegerField(null=True)
    TaskId = models.CharField(max_length=50, null=True)
    ApproverId = models.TextField(null=True)
    Status = models.CharField(max_length=50, null=True)
    Comments = models.TextField(null=True)
    ApprovedBy = models.CharField(max_length=50, null=True)


class MdmSeasonStatusRequested(SeasonCalculated):
    Status1 = models.IntegerField()
    ActionType = models.IntegerField(null=True)
    Approved = models.BooleanField(null=True)
    Reverted = models.BooleanField(null=True)
    TaskId = models.CharField(max_length=50, null=True)


class MdmSeasonStatusHistory(SeasonCalculated):
    Status1 = models.IntegerField()
    ActionType = models.IntegerField(null=True)
    TaskId = models.CharField(max_length=50, null=True)
    ApproverId = models.TextField(null=True)
    Status = models.CharField(max_length=50, null=True)
    Comments = models.TextField(null=True)
    ApproverBy = models.CharField(max_length=50, null=True)


class MdmSeasonTaskRevision(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    master_id = models.PositiveIntegerField()
    task_id = models.CharField(max_length=50)
    revision = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('source', 'master_id', 'task_id'),
            name='mdm_season_task_revision_identity')]


class MdmSeasonEligibility(models.Model):
    """Approved immutable opening lookup for uploads only; never current state."""
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    Norm = models.IntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=('source', 'ordinal'),
            name='mdm_season_eligibility_ordinal')]


class MdmSeasonConsumed(SeasonValues):
    run = models.ForeignKey('CalculationRun', on_delete=models.PROTECT)
    source_pk = models.PositiveBigIntegerField()
    revision = models.PositiveBigIntegerField()
    ordinal = models.PositiveBigIntegerField()
    Approved = models.BooleanField(null=True)
    cleared = models.BooleanField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=('run', 'ordinal'),
            name='mdm_season_consumed_ordinal')]


class MdmDraftSeason(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    RowId = models.IntegerField()
    DraftId = models.CharField(max_length=50, null=True)
    IsSelected = models.CharField(max_length=50, null=True)


for _name in ('Error', 'SKUCode', 'WhCode', 'WhDescription', 'StartDate', 'EndDate',
              'TargetNorm', 'RLT', 'DeltaNormPercentage', 'NewNorm', 'OriginalNorm',
              'UpperLowerCap', 'BuildupDuration', 'Type', 'Status', 'Comment',
              'SKUDescription', 'Warning', 'CurrentNorm'):
    MdmDraftSeason.add_to_class(_name, models.TextField(null=True))
