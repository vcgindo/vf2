"""Core Expedite occurrences, independent of mutable remark-prefix bindings."""
import uuid
from django.db import models
from mta.runtime import models as full


class ScopeExpediteGeneration(models.Model):
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
    pick_generation=models.ForeignKey('fresh_mta.ScopePickGeneration',on_delete=models.PROTECT)
    pick_generation_digest=models.CharField(max_length=64)
    metadata=models.JSONField(default=dict)
    digest=models.CharField(max_length=64,blank=True)
    sealed=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    sealed_at=models.DateTimeField(null=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['report_generation','pick_generation','recipe_digest'],
            name='scope_expedite_generation_id')]


class ScopeExpediteGrid(models.Model):
    generation=models.ForeignKey(ScopeExpediteGeneration,on_delete=models.PROTECT)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','direction','branch','ordinal'],name='scope_expedite_grid_ord')]
        indexes=[models.Index(fields=['generation','direction','branch','fact_ordinal'],name='scope_expedite_grid_fact')]


class ScopeExpediteCustom(models.Model):
    generation=models.ForeignKey(ScopeExpediteGeneration,on_delete=models.PROTECT)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_expedite_custom_ord')]
        indexes=[models.Index(fields=['generation','sku_key','location_key'],name='scope_expedite_custom_keys')]


class ScopeExpediteChartMember(models.Model):
    generation=models.ForeignKey(ScopeExpediteGeneration,on_delete=models.PROTECT)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','direction','family','ordinal'],name='scope_expedite_chart_ord')]
        indexes=[models.Index(fields=['generation','direction','family','fact_ordinal'],name='scope_expedite_chart_fact')]


class ScopeExpeditePrepostMember(models.Model):
    generation=models.ForeignKey(ScopeExpediteGeneration,on_delete=models.PROTECT)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_expedite_prepost_ord')]


for scoped,terminal in ((ScopeExpediteGrid,full.PlanningExpediteGridOccurrence),
        (ScopeExpediteCustom,full.PlanningExpediteCustomOccurrence),
        (ScopeExpediteChartMember,full.PlanningExpediteChartMember),
        (ScopeExpeditePrepostMember,full.PlanningExpeditePrepostMember)):
    for field in terminal._meta.local_fields:
        if field.name not in ('id','run'):scoped.add_to_class(field.name,field.clone())
