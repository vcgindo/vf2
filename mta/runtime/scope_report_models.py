"""Generation-owned current Planning facts; terminal Full tables stay separate."""
import uuid
from django.db import models


class ScopeReportGeneration(models.Model):
    """Only the five current-report bags, not a ready application or selection."""
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    run=models.ForeignKey('fresh_mta.CalculationRun',on_delete=models.PROTECT)
    phase=models.ForeignKey('fresh_mta.RunPhaseAcceptance',on_delete=models.PROTECT)
    action_revision=models.PositiveBigIntegerField()
    source_digest=models.CharField(max_length=64)
    configuration_digest=models.CharField(max_length=64)
    recipe_digest=models.CharField(max_length=64)
    metadata=models.JSONField(default=dict)  # finite identities, counts and checksums only
    digest=models.CharField(max_length=64,blank=True)
    sealed=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    sealed_at=models.DateTimeField(null=True)

    class Meta:
        constraints=[models.UniqueConstraint(fields=['phase','action_revision','source_digest','recipe_digest'],
                                              name='scope_report_generation_identity')]


class ScopeReportRow(models.Model):
    generation=models.ForeignKey(ScopeReportGeneration,on_delete=models.PROTECT)
    ordinal=models.PositiveBigIntegerField()

    class Meta:
        abstract=True
        constraints=[models.UniqueConstraint(fields=['generation','ordinal'],name='%(class)s_ordinal')]
        indexes=[models.Index(fields=['generation','SKUCode','WhCode'],name='%(class)s_p')]


class ScopeExcessRow(ScopeReportRow):
    Tags=models.CharField(max_length=50,null=True)
    SKUCode=models.CharField(max_length=50,null=True)
    WhCode=models.CharField(max_length=50,null=True)
    ParentWhCode=models.CharField(max_length=50,null=True)
    Norm=models.IntegerField(null=True)
    VirtualNorm=models.IntegerField(null=True)
    Stock=models.IntegerField(null=True)
    GIT=models.IntegerField(null=True)
    BlueReq=models.IntegerField(null=True)
    RequiredQty=models.IntegerField(null=True)
    PhysicalInventoryPen=models.DecimalField(max_digits=10,decimal_places=2,null=True)
    PhysicalInventoryColor=models.CharField(max_length=10,null=True)
    PipelineInventoryPen=models.DecimalField(max_digits=10,decimal_places=2,null=True)
    PipelineInventoryColor=models.CharField(max_length=10,null=True)
    ExcessQty=models.IntegerField(null=True)
    Amount=models.BigIntegerField(null=True)
    ReportDate=models.DateField(null=True)


class ScopeFulfillmentSummaryRow(ScopeReportRow):
    Coverage=models.CharField(max_length=20,null=True)
    Tags=models.CharField(max_length=50,null=True)
    SKUCode=models.CharField(max_length=50,null=True)
    WhCode=models.CharField(max_length=50,null=True)
    ParentWhCode=models.CharField(max_length=50,null=True)
    VirtualNorm=models.IntegerField(null=True)
    Norm=models.IntegerField(null=True)
    Stock=models.IntegerField(null=True)
    GIT=models.IntegerField(null=True)
    RationedQty=models.IntegerField(null=True)
    NormReq=models.IntegerField(null=True)
    SpikeReq=models.IntegerField(null=True)
    RelPSOAndCNR=models.IntegerField(null=True)
    TotalReq=models.IntegerField(null=True)
    Gap=models.IntegerField(null=True)
    PhysicalInventoryPen=models.DecimalField(max_digits=10,decimal_places=2,null=True)
    PhysicalInventoryColor=models.CharField(max_length=10,null=True)
    PipelineInventoryPen=models.DecimalField(max_digits=10,decimal_places=2,null=True)
    PipelineInventoryColor=models.CharField(max_length=10,null=True)
    Price=models.BigIntegerField(null=True)
    TotalSnP=models.IntegerField(null=True)


class ScopeFulfillmentDetailRow(ScopeReportRow):
    OrderNo=models.CharField(max_length=50,null=True)
    SKUCode=models.CharField(max_length=50,null=True)
    WhCode=models.CharField(max_length=50,null=True)
    Introdate=models.DateField(null=True)
    PendingQty=models.IntegerField(null=True)
    DueDate=models.DateField(null=True)
    Customer=models.CharField(max_length=50,null=True)
    Price=models.BigIntegerField(null=True)
    OrderStatus=models.CharField(max_length=10,null=True)


class ScopeExpediteRow(ScopeReportRow):
    SKUCode=models.CharField(max_length=50)
    WhCode=models.CharField(max_length=50)
    ParentWhCode=models.CharField(max_length=50)
    PhysicalInventoryPen=models.DecimalField(max_digits=10,decimal_places=2,null=True)
    PhysicalInventoryColor=models.CharField(max_length=10,null=True)
    PipelineInventoryPen=models.DecimalField(max_digits=10,decimal_places=2)
    PipelineInventoryColor=models.CharField(max_length=10)
    RationedQty=models.IntegerField()
    Req=models.IntegerField()
    StockAtParent=models.IntegerField(null=True)
    ParentPipelineInventoryColor=models.CharField(max_length=10,null=True)
    RLT=models.IntegerField()
    BRAge=models.IntegerField(null=True)
    BRAgeRedCount=models.IntegerField(null=True)
    BRAgeBlackCount=models.IntegerField(null=True)
    Norm=models.IntegerField()
    VirtualNorm=models.IntegerField()
    Stock=models.IntegerField()
    GIT=models.IntegerField()
    PotentialLossPerDay=models.BigIntegerField(null=True)
    IsParent=models.BooleanField(null=True)
    IsReceiving=models.BooleanField(null=True)


class ScopePickPostRow(ScopeReportRow):
    SKUCode=models.CharField(max_length=50)
    WhCode=models.CharField(max_length=50)
    ParentWhCode=models.CharField(max_length=50)
    PostPipelineInventoryPen=models.DecimalField(max_digits=10,decimal_places=2,null=True)
    PostPipelineInventoryColor=models.CharField(max_length=10,null=True)
