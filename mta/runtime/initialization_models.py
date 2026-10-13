"""Native initialization identity; never an executed or accepted day."""
import uuid
from django.db import models


class ProductionInitialization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.OneToOneField('fresh_mta.MdmSource', on_delete=models.PROTECT,
                                 related_name='production_initialization')
    opening_identity = models.CharField(max_length=128, unique=True)
    opening_date = models.DateField()
    input_sha256 = models.CharField(max_length=64, unique=True)
    recipe_sha256 = models.CharField(max_length=64)
    configuration_digest = models.CharField(max_length=64)
    implementation_digest = models.CharField(max_length=64)
    input_digest = models.CharField(max_length=64)
    input_payload = models.JSONField(default=dict)
    input_manifest_digest = models.CharField(max_length=64, blank=True)
    receipt = models.JSONField(default=dict)
    receipt_digest = models.CharField(max_length=64, blank=True)
    installed_at = models.DateTimeField(auto_now_add=True)
