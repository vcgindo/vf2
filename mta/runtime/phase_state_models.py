"""Sealed calculation snapshots; these alone accept no business phase/effect."""
from django.db import models


class DailyPhaseSnapshot(models.Model):
    run = models.ForeignKey('fresh_mta.CalculationRun', on_delete=models.PROTECT,
                            related_name='phase_snapshots')
    phase = models.CharField(max_length=8, choices=(('PRE_BPR', 'PRE_BPR'), ('BPR', 'BPR'), ('DBM', 'DBM')))
    parent = models.ForeignKey('self', null=True, on_delete=models.PROTECT)
    input_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    state_digest = models.CharField(max_length=64)
    manifest = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'phase'],
            name='fresh_phase_snapshot_identity')]
