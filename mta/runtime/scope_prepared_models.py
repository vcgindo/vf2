"""Phase-generation source/candidate rows; no terminal OneToOne collision."""
from django.db import models
from mta.runtime.models import BprNumericField


class ScopeSourceProjection(models.Model):
    generation=models.OneToOneField('fresh_mta.ScopeReportGeneration',primary_key=True,on_delete=models.PROTECT)
    report_generation_digest=models.CharField(max_length=64)
    recipe_digest=models.CharField(max_length=64)
    metadata=models.JSONField(default=dict)
    digest=models.CharField(max_length=64,blank=True)
    sealed=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    sealed_at=models.DateTimeField(null=True)


class ScopeBprCandidateRow(models.Model):
    generation=models.ForeignKey('fresh_mta.ScopeReportGeneration',on_delete=models.PROTECT)
    ordinal=models.BigIntegerField()
    sku_key=models.TextField(null=True)
    location_key=models.TextField(null=True)
    a_ordinal=models.BigIntegerField()
    v_ordinal=models.BigIntegerField(null=True)
    s_ordinal=models.BigIntegerField(null=True)
    c_ordinal=models.BigIntegerField(null=True)
    d_ordinal=models.BigIntegerField(null=True)
    b_ordinal=models.BigIntegerField(null=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='scope_bpr_candidate_ordinal')]
        indexes=[models.Index(fields=['generation','sku_key','location_key'],name='scope_bpr_candidate_keys'),
            models.Index(fields=['generation','sku_key','location_key'],
                         condition=models.Q(s_ordinal__isnull=False),name='scope_bpr_candidate_count')]


from mta.presentation.bpr_prepared_fields import FIELDS,field_name
for owner,fields in FIELDS.items():
    for field,kind in fields.items():
        factory={'text':models.TextField,'bigint':models.BigIntegerField,'numeric':BprNumericField}[kind]
        ScopeBprCandidateRow.add_to_class(field_name(owner,field),factory(null=True))


class ScopePlanningBprRow(models.Model):
    generation=models.ForeignKey('fresh_mta.ScopeReportGeneration',on_delete=models.PROTECT)
    source_ordinal=models.BigIntegerField()
    sku_key=models.TextField(null=True)
    location_key=models.TextField(null=True)
    parent_key=models.TextField(null=True)
    SKUCode=models.CharField(max_length=50)
    WHCode=models.CharField(max_length=50)
    Norm=models.IntegerField()
    ParentWhCode=models.CharField(max_length=50,null=True)
    SKUIntroDate=models.DateField(null=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','source_ordinal'],name='scope_planning_bpr_ordinal')]
        indexes=[models.Index(fields=['generation','sku_key','location_key'],name='scope_planning_bpr_keys')]


class ScopePlanningGitRow(models.Model):
    generation=models.ForeignKey('fresh_mta.ScopeReportGeneration',on_delete=models.PROTECT)
    rationed_ordinal=models.BigIntegerField()
    standard_ordinal=models.BigIntegerField()
    sku_key=models.TextField(null=True)
    location_key=models.TextField(null=True)
    parent_key=models.TextField(null=True)
    Status=models.CharField(max_length=50,null=True)
    SKUCode=models.CharField(max_length=50,null=True)
    WhCode=models.CharField(max_length=50,null=True)
    Tags=models.CharField(max_length=50,null=True)
    ParentWhCode=models.CharField(max_length=50,null=True)
    Norm=models.IntegerField(null=True)
    VirtualNorm=models.IntegerField(null=True)
    Stock=models.IntegerField(null=True)
    Git=models.IntegerField(null=True)
    PhysicalInventoryPen=models.DecimalField(max_digits=10,decimal_places=2,null=True)
    PhysicalInventoryColor=models.CharField(max_length=10,null=True)
    PipelineInventoryPen=models.DecimalField(max_digits=10,decimal_places=2,null=True)
    PipelineInventoryColor=models.CharField(max_length=10,null=True)
    Req=models.IntegerField(null=True)
    Price=models.IntegerField(null=True)
    IsParent=models.BooleanField(null=True)
    IsReceiving=models.BooleanField(null=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['generation','rationed_ordinal','standard_ordinal'],
                                              name='scope_planning_git_ordinals')]
        indexes=[models.Index(fields=['generation','sku_key','location_key'],name='scope_planning_git_keys'),
            models.Index(fields=['generation','parent_key','sku_key'],name='scope_planning_git_parent')]
