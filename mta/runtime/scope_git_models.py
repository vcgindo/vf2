"""GIT occurrences owned by exact scoped report and transit generations."""
import uuid
from django.db import models
from mta.runtime.models import PlanningGitOccurrence


class ScopeGitGeneration(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    run=models.ForeignKey('fresh_mta.CalculationRun',on_delete=models.PROTECT)
    phase=models.ForeignKey('fresh_mta.RunPhaseAcceptance',on_delete=models.PROTECT)
    action_revision=models.PositiveBigIntegerField()
    source_digest=models.CharField(max_length=64)
    configuration_digest=models.CharField(max_length=64)
    recipe_digest=models.CharField(max_length=64)
    report_generation=models.ForeignKey('fresh_mta.ScopeReportGeneration',on_delete=models.PROTECT)
    report_generation_digest=models.CharField(max_length=64)
    source_projection_digest=models.CharField(max_length=64)
    transit_generation=models.ForeignKey('fresh_mta.ScopeTransitGeneration',on_delete=models.PROTECT)
    transit_generation_digest=models.CharField(max_length=64)
    metadata=models.JSONField(default=dict)
    digest=models.CharField(max_length=64,blank=True)
    sealed=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    sealed_at=models.DateTimeField(null=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['report_generation','transit_generation','recipe_digest'],
            name='scope_git_generation_id')]


class ScopeGitOccurrence(models.Model):
    generation=models.ForeignKey(ScopeGitGeneration,on_delete=models.PROTECT)
    transporter_ordinal=models.PositiveBigIntegerField(null=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_git_occurrence_ord')]
        indexes=[models.Index(fields=['generation','rationed_ordinal','standard_ordinal'],name='scope_git_occurrence_source')]


# Freeze explicit scalar columns in migration state; no terminal run ownership.
for field in PlanningGitOccurrence._meta.local_fields:
    if field.name not in ('id','run'):ScopeGitOccurrence.add_to_class(field.name,field.clone())
