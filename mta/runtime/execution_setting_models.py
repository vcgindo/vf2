"""Immutable business-control versions, separate from initialized business state."""
import uuid
from django.db import models


class ExecutionSettingsVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    initialization = models.ForeignKey('fresh_mta.ProductionInitialization', on_delete=models.PROTECT)
    parent = models.ForeignKey('self', null=True, on_delete=models.PROTECT)
    revision = models.PositiveBigIntegerField()
    effective_date = models.DateField(null=True)
    format_version = models.PositiveSmallIntegerField(default=1)
    values_digest = models.CharField(max_length=64)
    profile_digest = models.CharField(max_length=64)
    reason = models.CharField(max_length=512)
    actor = models.CharField(max_length=128)
    status = models.CharField(max_length=12, default='PREPARING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('initialization', 'revision'), name='exec_settings_revision'),
            models.CheckConstraint(condition=models.Q(status__in=('PREPARING', 'COMMITTED')), name='exec_settings_status'),
            models.CheckConstraint(condition=models.Q(format_version=1), name='exec_settings_format'),
        ]


class ExecutionSetting(models.Model):
    version = models.ForeignKey(ExecutionSettingsVersion, on_delete=models.PROTECT, related_name='values')
    position = models.PositiveIntegerField()
    path = models.CharField(max_length=512)
    module = models.CharField(max_length=128)
    parameter = models.CharField(max_length=128)
    ordinal = models.PositiveIntegerField()
    value_kind = models.CharField(max_length=12)
    value_text = models.TextField(null=True)
    value_state = models.CharField(max_length=8)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('version', 'position'), name='exec_settings_position'),
            models.UniqueConstraint(fields=('version', 'path'), name='exec_settings_path'),
            models.CheckConstraint(condition=models.Q(value_state__in=('VALUE', 'NULL', 'ABSENT')), name='exec_settings_value_state')]
