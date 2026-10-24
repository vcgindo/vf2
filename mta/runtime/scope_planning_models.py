"""Phase-owned Planning occurrences; scalar contracts match Full tables."""
from django.db import models
from mta.runtime import models as full


class ScopePlanningProjection(models.Model):
    generation=models.OneToOneField('fresh_mta.ScopeReportGeneration',primary_key=True,on_delete=models.PROTECT)
    report_generation_digest=models.CharField(max_length=64)
    source_projection_digest=models.CharField(max_length=64)
    recipe_digest=models.CharField(max_length=64)
    metadata=models.JSONField(default=dict)
    digest=models.CharField(max_length=64,blank=True)
    sealed=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    sealed_at=models.DateTimeField(null=True)


class ScopePlanningRow(models.Model):
    generation=models.ForeignKey('fresh_mta.ScopeReportGeneration',on_delete=models.PROTECT)
    class Meta:
        abstract=True


class ScopePlanningExcessGrid(ScopePlanningRow):
    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_plan_excess_grid_ord')]
        indexes=[models.Index(fields=['generation','sku_key','location_key'],name='scope_plan_excess_grid_keys')]


class ScopePlanningFulfillmentGrid(ScopePlanningRow):
    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_plan_fulfill_grid_ord')]
        indexes=[models.Index(fields=['generation','sku_key','location_key'],name='scope_plan_fulfill_grid_keys')]


class ScopePlanningExcessCustom(ScopePlanningRow):
    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_plan_excess_custom_ord')]
        indexes=[models.Index(fields=['generation','sku_key','location_key'],name='scope_plan_excess_custom_keys')]


class ScopePlanningFulfillmentCustom(ScopePlanningRow):
    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_plan_fulfill_custom_ord')]
        indexes=[models.Index(fields=['generation','sku_key','location_key'],name='scope_plan_fulfill_custom_keys')]


class ScopePlanningChartMember(ScopePlanningRow):
    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','family','direction','ordinal'],name='scope_plan_chart_member_ord')]
        indexes=[models.Index(fields=['generation','family','direction','group_ordinal'],name='scope_plan_chart_member_group')]


class ScopePlanningChartDisplay(ScopePlanningRow):
    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','family','direction','ordinal'],name='scope_plan_chart_display_ord')]
        indexes=[models.Index(fields=['generation','family','direction','group_ordinal'],name='scope_plan_chart_display_group')]


# Clone scalar fields, never the terminal run ownership/constraints. Migration
# state freezes the resulting explicit typed columns; no JSON row payloads.
for scoped,terminal in (
        (ScopePlanningExcessGrid,full.PlanningExcessGridRow),
        (ScopePlanningFulfillmentGrid,full.PlanningFulfillmentGridRow),
        (ScopePlanningExcessCustom,full.PlanningExcessCustomRow),
        (ScopePlanningFulfillmentCustom,full.PlanningFulfillmentCustomRow),
        (ScopePlanningChartMember,full.PlanningChartMember),
        (ScopePlanningChartDisplay,full.PlanningChartDisplay)):
    for field in terminal._meta.local_fields:
        if field.name not in ('id','run'):scoped.add_to_class(field.name,field.clone())
