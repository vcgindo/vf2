"""Explicit late history completion; never modifies the original BPR receipt."""
from django.db import models


class BprHistoryCompletion(models.Model):
    run = models.OneToOneField('fresh_mta.CalculationRun', primary_key=True,
                              on_delete=models.PROTECT)
    phase = models.OneToOneField('fresh_mta.RunPhaseAcceptance', on_delete=models.PROTECT)
    predecessor = models.ForeignKey('fresh_mta.CalculationRun', on_delete=models.PROTECT,
                                    related_name='+')
    input_digest = models.CharField(max_length=64)
    phase_digest = models.CharField(max_length=64)
    snapshot_digest = models.CharField(max_length=64)
    predecessor_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    authority = models.JSONField()  # bounded explicit decision, no business rows
    images = models.JSONField(default=dict)  # typed image shape/checksum only
    digest = models.CharField(max_length=64, blank=True)
    state_sealed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
