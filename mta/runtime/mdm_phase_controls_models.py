"""Native shared masters7/8 and separate master9 row grains."""
from django.db import models
from mta.runtime.mdm_models import MdmSource


class MdmPhaseControlsOwner(models.Model):
    source = models.OneToOneField(MdmSource, on_delete=models.PROTECT)
    provenance = models.JSONField()  # Bounded binding metadata, never row payloads.
    receipt_digest = models.CharField(max_length=64)
    closing_queue_digest = models.CharField(max_length=64)
    last_run = models.ForeignKey('CalculationRun', on_delete=models.PROTECT)
    generation = models.PositiveBigIntegerField(default=0)


class PhasePair(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    SKUCode = models.CharField(max_length=50, null=True)
    WhCode = models.CharField(max_length=50, null=True)

    class Meta:
        abstract = True


class PhaseRequest(PhasePair):
    ActionType = models.IntegerField(null=True)
    Approved = models.BooleanField(null=True)
    Reverted = models.BooleanField(null=True)
    TaskId = models.CharField(max_length=50, null=True)

    class Meta:
        abstract = True


class PhaseHistory(PhasePair):
    ActionType = models.IntegerField(null=True)
    TaskId = models.CharField(max_length=50, null=True)
    ApproverId = models.TextField(null=True)
    Status = models.CharField(max_length=50, null=True)
    Comments = models.TextField(null=True)
    ApprovedBy = models.CharField(max_length=50, null=True)

    class Meta:
        abstract = True


class MdmPhaseOutRequested(PhaseRequest):
    PhaseInSKUCode = models.CharField(max_length=50, null=True)


class MdmPhaseInNormRequested(PhaseRequest):
    TargetNorm = models.IntegerField(null=True)


class MdmPhaseOutHistory(PhaseHistory):
    PhaseInSKUCode = models.CharField(max_length=50, null=True)


class MdmPhaseInNormHistory(PhaseHistory):
    TargetNorm = models.IntegerField(null=True)


class MdmPhaseOutQueue(PhasePair):
    PhaseInSKUCode = models.CharField(max_length=50, null=True)
    Approved = models.BooleanField(null=True)
    revision = models.PositiveBigIntegerField(default=0)


class MdmPhaseInNormQueue(PhasePair):
    TargetNorm = models.IntegerField(null=True)
    Approved = models.BooleanField(null=True)
    revision = models.PositiveBigIntegerField(default=0)


class PhaseConsumed(PhasePair):
    """Original occurrence entering importer processing; not phase success."""
    run = models.ForeignKey('CalculationRun', on_delete=models.PROTECT)
    source_pk = models.PositiveBigIntegerField()
    revision = models.PositiveBigIntegerField()
    ordinal = models.PositiveBigIntegerField()
    Approved = models.BooleanField(null=True)

    class Meta:
        abstract = True


class MdmPhaseOutConsumed(PhaseConsumed):
    PhaseInSKUCode = models.CharField(max_length=50, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('run', 'ordinal'),
            name='mdm_phase_out_consumed_ordinal')]


class MdmPhaseInNormConsumed(PhaseConsumed):
    TargetNorm = models.IntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('run', 'ordinal'),
            name='mdm_phase_in_consumed_ordinal')]


class MdmPhaseControlsTaskRevision(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    master_id = models.PositiveSmallIntegerField()
    task_id = models.CharField(max_length=50)
    revision = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('source', 'master_id', 'task_id'),
            name='mdm_phase_controls_task_rev')]


class MdmDraftAddPipo(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    RowId = models.IntegerField()
    DraftId = models.CharField(max_length=50)
    SKUCode = models.TextField(null=True)
    WhCode = models.TextField(null=True)
    PhaseInSKUCode = models.TextField(null=True)
    TargetNorm = models.TextField(null=True)
    Warning = models.TextField(null=True)
    Error = models.TextField(null=True)
