"""Compact immutable permission dimensions for one prepared BTR generation."""
from django.db import models


class BtrScopeDimension(models.Model):
    generation = models.ForeignKey('fresh_mta.BtrReportingGeneration', on_delete=models.PROTECT)
    owner = models.CharField(max_length=2)
    source_ordinal = models.BigIntegerField()
    code = models.TextField(null=True)
    level_1 = models.TextField(null=True)
    level_2 = models.TextField(null=True)
    level_3 = models.TextField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['generation', 'owner', 'source_ordinal'],
                                    name='fresh_btr_scope_occurrence'),
            models.CheckConstraint(condition=models.Q(owner__in=['sa', 'la']),
                                   name='fresh_btr_scope_owner'),
        ]
