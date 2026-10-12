"""Immutable operational qualification, separate from migration parity."""
from django.db import models


class OperationalAcceptance(models.Model):
    run = models.OneToOneField('CalculationRun', primary_key=True, on_delete=models.PROTECT)
    attempt = models.ForeignKey('OperationalAttempt', on_delete=models.PROTECT)
    repair = models.ForeignKey('OperationalAttempt', null=True, related_name='+', on_delete=models.PROTECT)
    predecessor = models.ForeignKey('self', null=True, on_delete=models.PROTECT)
    policy = models.CharField(max_length=80)
    qualification = models.CharField(max_length=80)
    code_digest = models.CharField(max_length=64)
    artifact_path = models.TextField()
    finalization_path = models.TextField()
    pick_config_path = models.TextField(null=True)
    pick_config_digest = models.CharField(max_length=64, null=True)
    shipment_path = models.TextField(null=True)
    shipment_digest = models.CharField(max_length=64, null=True)
    artifact_digest = models.CharField(max_length=64)
    input_digest = models.CharField(max_length=64)
    input_manifest_digest = models.CharField(max_length=64)
    profile_digest = models.CharField(max_length=64)
    execution_revision = models.CharField(max_length=80)
    output_digest = models.CharField(max_length=64)
    production_digest = models.CharField(max_length=64)
    action_digest = models.CharField(max_length=64)
    source_digest = models.CharField(max_length=64)
    operations_digest = models.CharField(max_length=64)
    operational_configuration_digest = models.CharField(max_length=64)
    operational_source_digest = models.CharField(max_length=64)
    predecessor_receipt_digest = models.CharField(max_length=64, blank=True)
    predecessor_output_digest = models.CharField(max_length=64, blank=True)
    publication_seal = models.CharField(max_length=64)
    layers_digest = models.CharField(max_length=64)
    configuration_digest = models.CharField(max_length=64)
    permissions_digest = models.CharField(max_length=64)
    hierarchy_digest = models.CharField(max_length=64)
    activation_digest = models.CharField(max_length=64)
    btr_generation = models.UUIDField()
    binding_digest = models.CharField(max_length=64)
    receipt_digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(policy__in=(
                'supported-synthetic-operational-v1', 'supported-synthetic-active-nms-v1')), name='op_accept_policy'),
            models.CheckConstraint(condition=models.Q(qualification__in=(
                'inactive-nms-critical-flags-remain-false', 'active-nms-enabled-writers-complete')), name='op_accept_qualification'),
            models.CheckConstraint(condition=(
                models.Q(policy='supported-synthetic-operational-v1', qualification='inactive-nms-critical-flags-remain-false')
                | models.Q(policy='supported-synthetic-active-nms-v1', qualification='active-nms-enabled-writers-complete')),
                name='op_accept_policy_qualification_pair'),
        ]
