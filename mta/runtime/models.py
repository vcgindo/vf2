"""Single run identity and atomic checkpoint storage for the fresh engine."""
import uuid
from django.db import models


class UserReportLayout(models.Model):
    """Per-user presentation preference; separate from immutable run state."""
    username = models.CharField(max_length=256, null=True)
    reportname = models.CharField(max_length=50, null=True)
    state = models.TextField(null=True)


class CalculationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    input_digest = models.CharField(max_length=64)
    execution_revision = models.CharField(max_length=80)
    kind = models.CharField(max_length=24, default='CURRENT_DAY')
    opening_key = models.CharField(max_length=64, null=True, blank=True, unique=True)
    predecessor = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='successors')
    business_date = models.DateField()
    input_payload = models.JSONField()
    status = models.CharField(max_length=16, default='RUNNING')
    output_digest = models.CharField(max_length=64, blank=True)
    production_digest = models.CharField(max_length=64, blank=True)
    production_manifest = models.JSONField(default=dict)
    parity_summary = models.JSONField(default=dict)
    output_roster = models.JSONField(default=list)
    failure = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['input_digest', 'execution_revision'], name='fresh_run_identity')]


class BtrReportingGeneration(models.Model):
    """Immutable derived BTR references, never calculation or permission state."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)
    source_digest = models.CharField(max_length=64)
    source_kind = models.CharField(max_length=24)
    business_date = models.DateField()
    status = models.CharField(max_length=16, default='BUILDING')
    lineage = models.JSONField(default=dict)
    eligible = models.BooleanField(default=False)
    qualification = models.JSONField(default=dict)
    row_count = models.PositiveBigIntegerField(default=0)
    rows_digest = models.CharField(max_length=64, blank=True)
    failure = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'version', 'source_digest'],
            condition=models.Q(status='READY'), name='fresh_btr_ready_source')]


class BtrJoinReference(models.Model):
    """A complete stable join bag; ordinals identify rows, never sort priority."""
    generation = models.ForeignKey(BtrReportingGeneration, on_delete=models.PROTECT)
    branch = models.CharField(max_length=4)
    export = models.BooleanField()
    sku_code = models.TextField(null=True)
    location_code = models.TextField(null=True)
    sku_key = models.TextField(null=True)
    location_key = models.TextField(null=True)
    a_ordinal = models.BigIntegerField()
    btd_ordinal = models.BigIntegerField(null=True)
    e_ordinal = models.BigIntegerField(null=True)
    sla_ordinal = models.BigIntegerField(null=True)
    sa_ordinal = models.BigIntegerField(null=True)
    la_ordinal = models.BigIntegerField(null=True)
    b_ordinal = models.BigIntegerField(null=True)

    class Meta:
        indexes = [models.Index(fields=['generation', 'branch', 'export', 'sku_key', 'location_key'],
                                name='fresh_btr_reference_keys')]
        constraints = [models.CheckConstraint(condition=models.Q(branch__in=['tech', 'eco']),
                                               name='fresh_btr_reference_branch')]


class Checkpoint(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT, related_name='checkpoints')
    name = models.CharField(max_length=100)
    rows = models.JSONField()
    evidence_path = models.CharField(max_length=240, blank=True)
    evidence_sha256 = models.CharField(max_length=64, blank=True)
    row_count = models.PositiveIntegerField()
    digest = models.CharField(max_length=64)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'name'], name='fresh_checkpoint_identity'),
            models.CheckConstraint(condition=(models.Q(evidence_path='', evidence_sha256='') |
                (~models.Q(evidence_path='') & ~models.Q(evidence_sha256='') & models.Q(rows=[]))),
                name='fresh_checkpoint_storage_boundary')]


class RunCommand(models.Model):
    """Ordered API actions on immutable daily output, consumed by its next run."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT, related_name='commands')
    idempotency_key = models.CharField(max_length=120)
    payload = models.JSONField()
    digest = models.CharField(max_length=64)
    before_digest = models.CharField(max_length=64)
    after_digest = models.CharField(max_length=64)
    state_manifest = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','idempotency_key'], name='fresh_command_identity')]


class PickProjection(models.Model):
    """Read-model receipt, not another execution/state/publication hierarchy."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT,
                              related_name='pick_projection')
    version = models.PositiveIntegerField(default=1)
    calculation_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    row_count = models.PositiveIntegerField()
    provenance = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class PickBand(models.Model):
    """Already-computed RRR bands, with source order and duplicates retained."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT, related_name='pick_bands')
    ordinal = models.PositiveIntegerField()
    sku_code = models.CharField(max_length=50)
    location_code = models.CharField(max_length=50)
    parent_location_code = models.CharField(max_length=50)
    to_black = models.BigIntegerField()
    to_red = models.BigIntegerField()
    to_yellow = models.BigIntegerField()
    to_green = models.BigIntegerField()
    to_blue = models.BigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'], name='fresh_pick_band_ordinal')]


class ExcessProjection(models.Model):
    """Bounded receipt for the canonical current-day Excess report producer."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    producer_sha256 = models.CharField(max_length=64)
    source_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    row_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class ExcessInventoryRow(models.Model):
    """ExcessInventoryDetails columns, preserving SQL types, NULLs and bags."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    Tags = models.CharField(max_length=50, null=True)
    SKUCode = models.CharField(max_length=50, null=True)
    WhCode = models.CharField(max_length=50, null=True)
    ParentWhCode = models.CharField(max_length=50, null=True)
    Norm = models.IntegerField(null=True)
    VirtualNorm = models.IntegerField(null=True)
    Stock = models.IntegerField(null=True)
    GIT = models.IntegerField(null=True)
    BlueReq = models.IntegerField(null=True)
    RequiredQty = models.IntegerField(null=True)
    PhysicalInventoryPen = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PhysicalInventoryColor = models.CharField(max_length=10, null=True)
    PipelineInventoryPen = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PipelineInventoryColor = models.CharField(max_length=10, null=True)
    ExcessQty = models.IntegerField(null=True)
    Amount = models.BigIntegerField(null=True)
    ReportDate = models.DateField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='fresh_excess_ordinal')]


class FulfillmentProjection(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    producer_sha256 = models.CharField(max_length=64)
    source_digest = models.CharField(max_length=64)
    calculation_digest = models.CharField(max_length=64)
    summary_digest = models.CharField(max_length=64)
    summary_count = models.PositiveIntegerField()
    details_digest = models.CharField(max_length=64)
    details_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class FulfillmentSummaryRow(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    Coverage = models.CharField(max_length=20, null=True)
    Tags = models.CharField(max_length=50, null=True)
    SKUCode = models.CharField(max_length=50, null=True)
    WhCode = models.CharField(max_length=50, null=True)
    ParentWhCode = models.CharField(max_length=50, null=True)
    VirtualNorm = models.IntegerField(null=True)
    Norm = models.IntegerField(null=True)
    Stock = models.IntegerField(null=True)
    GIT = models.IntegerField(null=True)
    RationedQty = models.IntegerField(null=True)
    NormReq = models.IntegerField(null=True)
    SpikeReq = models.IntegerField(null=True)
    RelPSOAndCNR = models.IntegerField(null=True)
    TotalReq = models.IntegerField(null=True)
    Gap = models.IntegerField(null=True)
    PhysicalInventoryPen = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PhysicalInventoryColor = models.CharField(max_length=10, null=True)
    PipelineInventoryPen = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PipelineInventoryColor = models.CharField(max_length=10, null=True)
    Price = models.BigIntegerField(null=True)
    TotalSnP = models.IntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='fresh_fulfillment_summary_ordinal')]


class FulfillmentDetailRow(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    OrderNo = models.CharField(max_length=50, null=True)
    SKUCode = models.CharField(max_length=50, null=True)
    WhCode = models.CharField(max_length=50, null=True)
    Introdate = models.DateField(null=True)
    PendingQty = models.IntegerField(null=True)
    DueDate = models.DateField(null=True)
    Customer = models.CharField(max_length=50, null=True)
    Price = models.BigIntegerField(null=True)
    OrderStatus = models.CharField(max_length=10, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='fresh_fulfillment_detail_ordinal')]


class ExpediteProjection(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    producer_sha256 = models.CharField(max_length=64)
    source_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    row_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class ExpediteRow(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    ParentWhCode = models.CharField(max_length=50)
    PhysicalInventoryPen = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PhysicalInventoryColor = models.CharField(max_length=10, null=True)
    PipelineInventoryPen = models.DecimalField(max_digits=10, decimal_places=2)
    PipelineInventoryColor = models.CharField(max_length=10)
    RationedQty = models.IntegerField()
    Req = models.IntegerField()
    StockAtParent = models.IntegerField(null=True)
    ParentPipelineInventoryColor = models.CharField(max_length=10, null=True)
    RLT = models.IntegerField()
    BRAge = models.IntegerField(null=True)
    BRAgeRedCount = models.IntegerField(null=True)
    BRAgeBlackCount = models.IntegerField(null=True)
    Norm = models.IntegerField()
    VirtualNorm = models.IntegerField()
    Stock = models.IntegerField()
    GIT = models.IntegerField()
    PotentialLossPerDay = models.BigIntegerField(null=True)
    IsParent = models.BooleanField(null=True)
    IsReceiving = models.BooleanField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='fresh_expedite_ordinal')]


class PickPostProjection(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    producers_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    row_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class PickPostRow(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    ParentWhCode = models.CharField(max_length=50)
    PostPipelineInventoryPen = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PostPipelineInventoryColor = models.CharField(max_length=10, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='fresh_pick_post_ordinal')]
