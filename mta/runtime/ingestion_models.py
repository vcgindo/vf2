"""Certification and compatibility metadata, never a business-state payload.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import uuid
from django.db import models
from django.db.models.functions import Cast, Length
from django.db.models.lookups import LessThanOrEqual


def bounded(field, name):
    return models.CheckConstraint(condition=LessThanOrEqual(
        Length(Cast(field, models.TextField())), models.Value(262144)), name=name)


class InitializationCertification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    initialization = models.ForeignKey('fresh_mta.ProductionInitialization', on_delete=models.PROTECT)
    contract = models.CharField(max_length=64)
    database_name = models.CharField(max_length=128)
    database_oid = models.PositiveBigIntegerField()
    namespace = models.UUIDField()
    source_digest = models.CharField(max_length=64)
    content_digest = models.CharField(max_length=64)
    configuration_digest = models.CharField(max_length=64)
    schema_digest = models.CharField(max_length=64)
    guard_digest = models.CharField(max_length=64)
    release_digest = models.CharField(max_length=64)
    populations = models.JSONField(default=dict)
    families = models.JSONField(default=list)
    authority_roles = models.JSONField(default=list)
    receipt_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default='CERTIFIED')
    certified_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(
            status__in=('CERTIFIED', 'INVALIDATED')), name='ingestion_cert_status'),
            models.UniqueConstraint(fields=('initialization',), condition=models.Q(status='CERTIFIED'),
                name='ingestion_one_current_cert'),
            bounded('populations', 'ingestion_cert_metadata_bound')]


class MasterInputRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    initialization = models.ForeignKey('fresh_mta.ProductionInitialization', on_delete=models.PROTECT)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT)
    run = models.ForeignKey('fresh_mta.CalculationRun', null=True, blank=True, on_delete=models.PROTECT)
    master_epoch = models.PositiveBigIntegerField()
    configuration_epoch = models.PositiveBigIntegerField()
    partitions = models.JSONField(default=dict)
    receipt_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default='CANDIDATE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(
            status__in=('CANDIDATE', 'ACCEPTED')), name='ingestion_master_status'),
            models.UniqueConstraint(fields=('initialization', 'master_epoch', 'configuration_epoch'),
                condition=models.Q(status='ACCEPTED'), name='ingestion_master_one_accepted_cut'),
            bounded('partitions', 'ingestion_master_metadata_bound')]


class IngestionReleaseCompatibility(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    initialization = models.ForeignKey('fresh_mta.ProductionInitialization', on_delete=models.PROTECT)
    original_release = models.CharField(max_length=64)
    target_release = models.CharField(max_length=64)
    original_commit = models.CharField(max_length=40)
    target_commit = models.CharField(max_length=40)
    contract = models.CharField(max_length=64)
    original_registration_digest = models.CharField(max_length=64)
    schema_digest = models.CharField(max_length=64)
    certification_digest = models.CharField(max_length=64)
    receipt_digest = models.CharField(max_length=64)
    activated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('initialization', 'target_release'),
            name='ingestion_one_release_transition')]


class IngestionRevisionState(models.Model):
    """Mutable generations are separate from immutable certification receipts."""
    initialization = models.OneToOneField('fresh_mta.ProductionInitialization',
        primary_key=True, on_delete=models.PROTECT)
    master_epoch = models.PositiveBigIntegerField(default=0)
    configuration_epoch = models.PositiveBigIntegerField(default=0)
    fact_epoch = models.PositiveBigIntegerField(default=0)
    operational_epoch = models.PositiveBigIntegerField(default=0)
    action_epoch = models.PositiveBigIntegerField(default=0)
    bpr_remark_operational_epoch = models.PositiveBigIntegerField(default=0)
    bpr_remark_action_epoch = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(bpr_remark_operational_epoch__lte=models.F('operational_epoch')),
                name='bpr_consumer_operational_bounded'),
            models.CheckConstraint(condition=models.Q(bpr_remark_action_epoch__lte=models.F('action_epoch')),
                name='bpr_consumer_action_bounded'),
        ]
