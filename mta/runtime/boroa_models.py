"""BOR-OA typed sources, stable occurrences and separate append-only history."""
from django.db import models
from mta.runtime.models import CalculationRun
from mta.presentation.boroa_contract import SOURCE_FIELDS,PREPARED_FIELDS,field_name

class BorOaSourceReceipt(models.Model):
    run=models.OneToOneField(CalculationRun,primary_key=True,on_delete=models.PROTECT)
    source_digest=models.CharField(max_length=64)
    recipe_digest=models.CharField(max_length=64)
    allocation_digest=models.CharField(max_length=64)
    requirement_digest=models.CharField(max_length=64)
    history_digest=models.CharField(max_length=64)
    created_at=models.DateTimeField(auto_now_add=True)

class BorOaSourceRow(models.Model):
    run=models.ForeignKey(CalculationRun,on_delete=models.PROTECT)
    ordinal=models.PositiveBigIntegerField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=['run','ordinal'],name='boroa_source_ordinal')]

class BorOaRequirement(models.Model):
    run=models.ForeignKey(CalculationRun,on_delete=models.PROTECT)
    ordinal=models.PositiveBigIntegerField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=['run','ordinal'],name='boroa_req_ordinal')]

class BorOaInitialRemark(models.Model):
    run=models.ForeignKey(CalculationRun,on_delete=models.PROTECT)
    ordinal=models.PositiveBigIntegerField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=['run','ordinal'],name='boroa_initial_ordinal')]

class BorOaLiveRemark(models.Model):
    run=models.ForeignKey(CalculationRun,on_delete=models.PROTECT)
    actor_id=models.CharField(max_length=256)

for model,table in ((BorOaSourceRow,'BORWithOrderAllocation'),(BorOaRequirement,'BOROARequirement'),
                   (BorOaInitialRemark,'BORReport_OARemarkDetails'),(BorOaLiveRemark,'BORReport_OARemarkDetails')):
    for name,spec in SOURCE_FIELDS[table].items():
        kind=spec['kind'];args=dict(null=spec['nullable'])
        if kind=='int':field=models.IntegerField(**args)
        elif kind=='decimal':field=models.DecimalField(max_digits=spec['precision'],decimal_places=spec['scale'],**args)
        elif kind=='datetime':field=models.DateTimeField(**args)
        elif spec['length'] is None:field=models.TextField(**args)
        else:field=models.CharField(max_length=spec['length'],**args)
        model.add_to_class(name,field)

class BorOaPreparedReceipt(models.Model):
    run=models.OneToOneField(CalculationRun,primary_key=True,on_delete=models.PROTECT)
    source_digest=models.CharField(max_length=64)
    recipe_digest=models.CharField(max_length=64)
    rows_digest=models.CharField(max_length=64)
    row_count=models.PositiveBigIntegerField()
    created_at=models.DateTimeField(auto_now_add=True)

class BorOaPreparedRow(models.Model):
    run=models.ForeignKey(CalculationRun,on_delete=models.PROTECT)
    ordinal=models.PositiveBigIntegerField()
    sku_key=models.TextField(null=True)
    location_key=models.TextField(null=True)
    supplier_key=models.TextField(null=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['run','ordinal'],name='boroa_prepared_ordinal')]
        indexes=[models.Index(fields=['run','sku_key','location_key'],name='boroa_prepared_scope')]

for owner,fields in PREPARED_FIELDS.items():
    BorOaPreparedRow.add_to_class(owner.lower()+'_ordinal',models.BigIntegerField(null=True))
    for name,kind in fields.items():
        field=(models.BigIntegerField(null=True) if kind=='bigint' else
               models.DecimalField(max_digits=38,decimal_places=12,null=True) if kind=='numeric' else models.TextField(null=True))
        BorOaPreparedRow.add_to_class(field_name(owner,name),field)
