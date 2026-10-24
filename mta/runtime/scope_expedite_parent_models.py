"""Immutable parent Expedite ingredients owned by one core and remark prefix."""
import uuid
from django.db import models
from mta.runtime import models as full


class ScopeExpediteParentGeneration(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    run=models.ForeignKey('fresh_mta.CalculationRun',on_delete=models.PROTECT)
    phase=models.ForeignKey('fresh_mta.RunPhaseAcceptance',on_delete=models.PROTECT)
    action_revision=models.PositiveBigIntegerField()
    source_digest=models.CharField(max_length=64)
    configuration_digest=models.CharField(max_length=64)
    recipe_digest=models.CharField(max_length=64)
    core_generation=models.ForeignKey('fresh_mta.ScopeExpediteGeneration',on_delete=models.PROTECT)
    core_generation_digest=models.CharField(max_length=64)
    remark_capture=models.ForeignKey('fresh_mta.RemarkCapture',on_delete=models.PROTECT)
    remark_watermark=models.PositiveBigIntegerField()
    remark_highwater=models.PositiveBigIntegerField()
    remark_cutoff=models.DateTimeField()
    remark_row_count=models.PositiveBigIntegerField()
    remark_rows_digest=models.CharField(max_length=64)
    remark_provenance_digest=models.CharField(max_length=64)
    remark_digest=models.CharField(max_length=64)
    metadata=models.JSONField(default=dict)
    digest=models.CharField(max_length=64,blank=True)
    sealed=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    sealed_at=models.DateTimeField(null=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['core_generation','remark_digest','recipe_digest'],
            name='scope_exp_parent_generation_id')]


class ScopeExpediteParentBase(models.Model):
    generation=models.ForeignKey(ScopeExpediteParentGeneration,on_delete=models.PROTECT)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_exp_parent_base_ord')]


class ScopeExpediteParentMatch(models.Model):
    generation=models.ForeignKey(ScopeExpediteParentGeneration,on_delete=models.PROTECT)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_exp_parent_match_ord')]
        indexes=[models.Index(fields=['generation','branch','grid_ordinal'],name='scope_exp_parent_grid')]


for scoped,terminal in ((ScopeExpediteParentBase,full.PlanningExpediteTransitBase),
        (ScopeExpediteParentMatch,full.PlanningExpediteTransitMatch)):
    for field in terminal._meta.local_fields:
        if field.name not in ('id','run'):scoped.add_to_class(field.name,field.clone())
