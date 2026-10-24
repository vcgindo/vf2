"""Independent raw Pick and RRR display references; phase facts stay owned."""
import uuid
from django.db import models
from mta.runtime.models import RrrPreparedMembership


class ScopePickGeneration(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    run=models.ForeignKey('fresh_mta.CalculationRun',on_delete=models.PROTECT)
    phase=models.ForeignKey('fresh_mta.RunPhaseAcceptance',on_delete=models.PROTECT)
    action_revision=models.PositiveBigIntegerField()
    source_digest=models.CharField(max_length=64)
    configuration_digest=models.CharField(max_length=64)
    recipe_digest=models.CharField(max_length=64)
    metadata=models.JSONField(default=dict)
    digest=models.CharField(max_length=64,blank=True)
    sealed=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    sealed_at=models.DateTimeField(null=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['phase','action_revision','source_digest','recipe_digest'],
            name='scope_pick_generation_id')]


class ScopePickReference(models.Model):
    generation=models.ForeignKey(ScopePickGeneration,on_delete=models.PROTECT)
    ordinal=models.PositiveBigIntegerField()
    band_ordinal=models.PositiveBigIntegerField()
    rationed_ordinal=models.PositiveBigIntegerField()
    virtual=models.BooleanField()

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_pick_reference_ord')]


class ScopeRrrReference(models.Model):
    generation=models.ForeignKey(ScopePickGeneration,on_delete=models.PROTECT)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_rrr_reference_ord')]
        indexes=[models.Index(fields=['generation','sku_key','location_key'],name='scope_rrr_reference_keys')]


for field in RrrPreparedMembership._meta.local_fields:
    if field.name not in ('id','run'):ScopeRrrReference.add_to_class(field.name,field.clone())
