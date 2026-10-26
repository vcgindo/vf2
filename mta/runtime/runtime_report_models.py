"""Immutable placement file ownership, distinct from calculation acceptance."""
import uuid
from django.db import models


class RuntimeReportPublication(models.Model):
    # The primary key is the exclusively created candidate directory UUID.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey('fresh_mta.CalculationRun', on_delete=models.PROTECT,
                            related_name='runtime_report_publications')
    phase = models.ForeignKey('fresh_mta.RunPhaseAcceptance', null=True, on_delete=models.PROTECT)
    scope_attempt = models.ForeignKey('fresh_mta.RunScopeAttempt', null=True, on_delete=models.PROTECT)
    operational_attempt = models.ForeignKey('fresh_mta.OperationalAttempt', null=True, on_delete=models.PROTECT)
    # Catalogue continuity is not the calculation predecessor/opening lineage.
    catalogue_parent = models.ForeignKey('self', null=True, on_delete=models.PROTECT,
                                        related_name='catalogue_successors')
    owner_kind = models.CharField(max_length=20, choices=tuple((name, name) for name in
        ('FULL_COMPLETION', 'SCOPED_PHASE', 'SCOPED_FINAL', 'OPERATIONAL')))
    placement = models.CharField(max_length=12, choices=tuple((name,name) for name in
        ('PostImporter', 'PostBPR', 'PostDBM', 'PostBTR', 'Final')))
    input_digest = models.CharField(max_length=64)
    input_manifest_digest = models.CharField(max_length=64)
    source_digest = models.CharField(max_length=64)
    profile_digest = models.CharField(max_length=64)
    scope_request_digest = models.CharField(max_length=64)
    configuration_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    action_revision = models.PositiveBigIntegerField()
    action_digest = models.CharField(max_length=64, blank=True)
    candidate_digest = models.CharField(max_length=64)
    catalogue_digest = models.CharField(max_length=64)
    # Only finite file/member hashes, source references and generated names.
    # No report populations, operational state payloads or credentials.
    metadata = models.JSONField()
    digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['run','placement'], name='runtime_report_run_placement'),
            models.CheckConstraint(condition=(
                models.Q(owner_kind='FULL_COMPLETION', scope_attempt__isnull=True,
                         phase__isnull=True, operational_attempt__isnull=True) |
                models.Q(owner_kind='SCOPED_PHASE', scope_attempt__isnull=False,
                         phase__isnull=False, operational_attempt__isnull=True,
                         placement__in=('PostImporter','PostBPR','PostDBM')) |
                models.Q(owner_kind='SCOPED_FINAL', scope_attempt__isnull=False,
                         phase__isnull=False, operational_attempt__isnull=True,
                         placement__in=('PostBTR','Final')) |
                models.Q(owner_kind='OPERATIONAL', scope_attempt__isnull=True,
                         phase__isnull=True, operational_attempt__isnull=False,
                         placement__in=('PostBTR','Final'))),
                name='runtime_report_publication_owner'),
        ]
