"""Bounded identity for native closing-master publication; no copied state."""
from django.db import models


class MdmClosingProjectionReceipt(models.Model):
    run = models.OneToOneField('fresh_mta.CalculationRun', primary_key=True,
        on_delete=models.PROTECT)
    version = models.CharField(max_length=48)
    transition_id = models.UUIDField(null=True)
    source_digest = models.CharField(max_length=64)
    adapter_digest = models.CharField(max_length=64)
    source_manifest_digest = models.CharField(max_length=64)
    integration_digest = models.CharField(max_length=64)
    capture_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=8, default='PENDING')
    metadata = models.JSONField(default=dict)
    digest = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(status__in=('PENDING','SEALED')),
            name='mdm_closing_projection_status')]
