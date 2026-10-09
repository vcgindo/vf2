"""Approved 3005 consumer fixture rows, never calculation state or openings."""
from django.db import models
from mta.runtime.mdm_models import MdmSource


class MdmTargetFixture(models.Model):
    source = models.OneToOneField(MdmSource, on_delete=models.PROTECT)
    run = models.ForeignKey('CalculationRun', on_delete=models.PROTECT)
    digest = models.CharField(max_length=64)
    receipt = models.JSONField()  # Bounded provenance only; rows are typed below.


class FixtureOccurrence(models.Model):
    source = models.ForeignKey(MdmSource, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()

    class Meta:
        abstract = True
        constraints = [models.UniqueConstraint(fields=('source', 'ordinal'),
            name='%(class)s_ordinal')]


class MdmFixturePhaseOut(FixtureOccurrence):
    SKUCode = models.TextField(null=True)
    WHCode = models.TextField(null=True)
    OldNorm = models.BigIntegerField(null=True)
    NewNorm = models.BigIntegerField(null=True)
    PhaseOutFinished = models.BooleanField(null=True)
    PhaseOutStartDate = models.DateField(null=True)
    LastProcessedDate = models.DateField(null=True)
    PhaseInSKUCode = models.TextField(null=True)


class MdmFixturePhaseIn(FixtureOccurrence):
    SKUCode = models.TextField(null=True)
    WHCode = models.TextField(null=True)
    PhaseOutSKUOrigNorm = models.BigIntegerField(null=True)
    TargetNorm = models.BigIntegerField(null=True)
    OldNorm = models.BigIntegerField(null=True)
    NewNorm = models.BigIntegerField(null=True)
    PhaseInStartDate = models.DateField(null=True)
    LastProcessedDate = models.DateField(null=True)


class MdmFixturePhaseMap(FixtureOccurrence):
    PhaseOutSKUCode = models.TextField(null=True)
    WhCode = models.TextField(null=True)
    PhaseInSKUCode = models.TextField(null=True)
    PhaseOutSKUOrigNorm = models.BigIntegerField(null=True)


class MdmFixtureSeasonStatus(FixtureOccurrence):
    Id = models.BigIntegerField(null=True)
    Status = models.TextField(null=True)
