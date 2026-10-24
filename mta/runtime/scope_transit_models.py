"""Phase-generation transit outputs; raw facts keep their captured owner."""
import uuid
from django.db import models
from mta.runtime.sql_datetime import SqlDateTimeField


class ScopeTransitGeneration(models.Model):
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
            name='scope_transit_generation_id')]


class _Row(models.Model):
    generation=models.ForeignKey(ScopeTransitGeneration,on_delete=models.PROTECT)
    ordinal=models.PositiveBigIntegerField()
    SKUCode=models.CharField(max_length=50,null=True)
    WhCode=models.CharField(max_length=50,null=True)

    class Meta:
        abstract=True
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='%(class)s_ord')]
        indexes=[models.Index(fields=['generation','SKUCode','WhCode'],name='%(class)s_pair')]


class ScopeTransitRow(_Row):
    ParentWhCode=models.CharField(max_length=50,null=True)
    CurrentLocationCode=models.CharField(max_length=50,null=True)
    LRCode=models.CharField(max_length=50,null=True)
    OrderNo=models.CharField(max_length=50,null=True)
    CreationDate=models.DateField(null=True)
    GateOutDate=models.DateField(null=True)
    InTransitQty=models.IntegerField(null=True)
    TransporterCode=models.CharField(max_length=50,null=True)
    Remark=models.TextField(null=True)
    ReportDate=models.DateField(null=True)
    Ageing=models.IntegerField(null=True)
    ETA=models.DateField(null=True)
    TLT=models.IntegerField(null=True)
    SLT=models.IntegerField(null=True)


class ScopeTransporterRow(_Row):
    Status=models.CharField(max_length=50,null=True)
    OrderNo=models.CharField(max_length=50,null=True)
    ParentWhCode=models.CharField(max_length=50,null=True)
    CurrentLocation=models.CharField(max_length=50,null=True)
    TransporterCode=models.CharField(max_length=50,null=True)
    TransporterName=models.CharField(max_length=125,null=True)
    TransporterContact=models.CharField(max_length=20,null=True)
    LRCode=models.CharField(max_length=50,null=True)
    InTransitQty=models.IntegerField(null=True)
    PhysicalInventoryPen=models.DecimalField(max_digits=10,decimal_places=2,null=True)
    PhysicalInventoryColor=models.CharField(max_length=10,null=True)
    PipelineInventoryColor=models.CharField(max_length=10,null=True)
    Price=models.IntegerField(null=True)
    SLT=models.IntegerField(null=True)
    Ageing=models.IntegerField(null=True)
    ETA=models.DateField(null=True)
    Remark=models.TextField(null=True)
    CreationDate=models.DateField(null=True)
    TruckStatus=models.CharField(max_length=20,null=True)
    SKUStatus=models.CharField(max_length=20,null=True)
    IsParent=models.BooleanField(null=True)
    IsReceiving=models.BooleanField(null=True)


class ScopeTransitDiagnostic(_Row):
    SKUCode=models.CharField(max_length=50)
    WhCode=models.CharField(max_length=50)
    RejectionDate=SqlDateTimeField()
    ReasonCode=models.IntegerField()
    ReasonDescription=models.CharField(max_length=100,null=True)
