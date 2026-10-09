"""Bounded immutable metadata for an explicitly combined MDM source roster."""
from django.db import models
from mta.runtime.mdm_models import MdmSource


class MdmSourceIntegration(models.Model):
    source = models.OneToOneField(MdmSource, on_delete=models.PROTECT)
    digest = models.CharField(max_length=64, unique=True)
    receipt = models.JSONField()

    class Meta:
        app_label = 'fresh_mta'
