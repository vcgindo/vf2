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


class BprNumericField(models.DecimalField):
    """Unconstrained PostgreSQL numeric, retaining every native pen digit."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_digits', 1000)
        kwargs.setdefault('decimal_places', 500)
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        return 'numeric'


class BprPreparedProjection(models.Model):
    """Immutable receipt for one complete fixture-only native candidate bag."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    schema_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class BprPreparedRow(models.Model):
    """Typed pre-auth/filter candidate occurrence; source ordinals retain bags."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.BigIntegerField()
    sku_key = models.TextField(null=True)
    location_key = models.TextField(null=True)
    a_ordinal = models.BigIntegerField()
    v_ordinal = models.BigIntegerField(null=True)
    s_ordinal = models.BigIntegerField(null=True)
    c_ordinal = models.BigIntegerField(null=True)
    d_ordinal = models.BigIntegerField(null=True)
    b_ordinal = models.BigIntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'],
                                               name='fresh_bpr_prepared_ordinal')]
        indexes = [models.Index(fields=['run', 'sku_key', 'location_key'],
                                name='fresh_bpr_prepared_keys')]


from mta.presentation.bpr_prepared_fields import FIELDS as _BPR_FIELDS, field_name as _bpr_field_name
for _owner, _fields in _BPR_FIELDS.items():
    for _field, _kind in _fields.items():
        _factory = {'text': models.TextField, 'bigint': models.BigIntegerField,
                    'numeric': BprNumericField}[_kind]
        BprPreparedRow.add_to_class(_bpr_field_name(_owner, _field), _factory(null=True))


class GuidedDbmPreparedProjection(models.Model):
    """Immutable source receipt for one fixture daily-suggestion occurrence bag."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    schema_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class GuidedDbmPreparedRow(models.Model):
    """Common native occurrence before endpoint descriptions, auth, or filters."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.BigIntegerField()
    a_ordinal = models.BigIntegerField()
    s_ordinal = models.BigIntegerField()
    l_ordinal = models.BigIntegerField()
    p_ordinal = models.BigIntegerField(null=True)
    m_ordinal = models.BigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'],
                                               name='fresh_guided_dbm_ordinal')]
        indexes = [models.Index(fields=['run', 'a_skucode', 'a_whcode'],
                                name='fresh_guided_dbm_keys')]


from mta.presentation.guided_dbm_fields import FIELDS as _GUIDED_DBM_FIELDS, field_name as _guided_dbm_field_name
for _owner, _fields in _GUIDED_DBM_FIELDS.items():
    for _field, _kind in _fields.items():
        _factory = {'text': models.TextField, 'bigint': models.BigIntegerField}[_kind]
        GuidedDbmPreparedRow.add_to_class(_guided_dbm_field_name(_owner, _field), _factory(null=True))


class GuidedChronicPreparedProjection(models.Model):
    """Immutable source receipt for the fixture Chronic grid occurrence bag."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    schema_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class GuidedChronicPreparedRow(models.Model):
    """Prepared grid output plus exact retained filter-owner occurrences."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.BigIntegerField()
    a_ordinal = models.BigIntegerField()
    n_ordinal = models.BigIntegerField(null=True)
    l_ordinal = models.BigIntegerField(null=True)
    s_ordinal = models.BigIntegerField(null=True)
    p_ordinal = models.BigIntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'],
                                               name='fresh_guided_chronic_ordinal')]
        indexes = [models.Index(fields=['run', 'skucode', 'location'],
                                name='fresh_guided_chronic_keys')]


from mta.presentation.guided_chronic_fields import OUTPUTS as _GUIDED_CHRONIC_OUTPUTS
for _field, _kind in _GUIDED_CHRONIC_OUTPUTS.items():
    _factory = {'text': models.TextField, 'bigint': models.BigIntegerField}[_kind]
    GuidedChronicPreparedRow.add_to_class(_field, _factory(null=True))


class GuidedHistoryPreparedProjection(models.Model):
    """Immutable receipt for one fixture history occurrence family."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    family = models.CharField(max_length=16)
    source_digest = models.CharField(max_length=64)
    schema_digest = models.CharField(max_length=64, null=True)
    rows_digest = models.CharField(max_length=64, null=True)
    row_count = models.PositiveBigIntegerField()
    reference_count = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'family'],
                                               name='fresh_guided_history_family')]


class GuidedAvailabilityHistoryRow(models.Model):
    """BPR fact and exact stable attribute/pair occurrence ordinals."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.BigIntegerField()
    fact_ordinal = models.BigIntegerField()
    sku_ordinal = models.BigIntegerField()
    location_ordinal = models.BigIntegerField()
    pair_ordinal = models.BigIntegerField(null=True)
    snapshot_anchor_ordinal = models.BigIntegerField(null=True)
    report_date = models.DateField()
    sku_code = models.TextField(null=True)
    location_code = models.TextField(null=True)
    parent_location_code = models.TextField(null=True)
    location_type = models.TextField(null=True)
    physical_inventory_color = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'],
                                               name='fresh_guided_availability_ordinal')]
        indexes = [models.Index(fields=['run', 'report_date'],
                                name='fresh_guided_avail_date'),
                   models.Index(fields=['run', 'report_date'],
                                include=['sku_code', 'location_code',
                                         'location_type',
                                         'physical_inventory_color', 'ordinal',
                                         'snapshot_anchor_ordinal'],
                                name='fresh_guided_avail_cover')]


class GuidedAvailabilitySnapshotReference(models.Model):
    """Prepared exact key-to-current-snapshot occurrence and live age."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    snapshot_anchor_ordinal = models.BigIntegerField()
    snapshot_ordinal = models.BigIntegerField()
    age_physical_inventory = models.BigIntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=['run', 'snapshot_anchor_ordinal', 'snapshot_ordinal'],
            name='fresh_guided_snapshot_reference')]
        indexes = [models.Index(fields=['run', 'snapshot_anchor_ordinal',
                                       'age_physical_inventory'],
                                name='fresh_guided_snapshot_age')]


class GuidedExcessHistoryRow(models.Model):
    """Excess fact and exact importer attribute/pair occurrence ordinals."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.BigIntegerField()
    fact_ordinal = models.BigIntegerField()
    sku_ordinal = models.BigIntegerField()
    location_ordinal = models.BigIntegerField()
    pair_ordinal = models.BigIntegerField(null=True)
    report_date = models.DateField()
    sku_code = models.TextField(null=True)
    location_code = models.TextField(null=True)
    parent_location_code = models.TextField(null=True)
    location_type = models.TextField(null=True)
    physical_inventory_color = models.TextField(null=True)
    amount = models.BigIntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'],
                                               name='fresh_guided_excess_history_ordinal')]
        indexes = [models.Index(fields=['run', 'report_date'],
                                name='fresh_guided_excess_date')]


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


class BtrPresentationRow(models.Model):
    """One prepared grid join occurrence; never a replacement calculation fact."""
    generation = models.ForeignKey(BtrReportingGeneration, on_delete=models.PROTECT)
    branch = models.CharField(max_length=4)
    sku_key = models.TextField(null=True)
    location_key = models.TextField(null=True)
    a_ordinal = models.BigIntegerField()
    btd_ordinal = models.BigIntegerField(null=True)
    e_ordinal = models.BigIntegerField(null=True)
    sla_ordinal = models.BigIntegerField(null=True)
    sa_ordinal = models.BigIntegerField(null=True)
    la_ordinal = models.BigIntegerField(null=True)
    b_ordinal = models.BigIntegerField(null=True)
    parent_location_type = models.TextField(null=True)
    availability = models.FloatField(null=True)

    class Meta:
        indexes = [models.Index(fields=['generation', 'branch', 'sku_key', 'location_key'],
                                name='fresh_btr_presentation_keys'),
                   models.Index(fields=['generation', 'sa_ordinal'],
                                include=['filter_sa_skucode', 'filter_sa_sl1', 'filter_sa_sl2', 'filter_sa_sl3'],
                                condition=models.Q(sa_ordinal__isnull=False), name='fresh_btr_snapshot_sku_scope'),
                   models.Index(fields=['generation', 'la_ordinal'],
                                include=['filter_la_whcode', 'filter_la_ll1', 'filter_la_ll2', 'filter_la_ll3'],
                                condition=models.Q(la_ordinal__isnull=False), name='fresh_btr_snapshot_loc_scope')]
        constraints = [models.CheckConstraint(condition=models.Q(branch__in=['tech', 'eco']),
                                               name='fresh_btr_presentation_branch')]


# Finite repeated BTR columns, registered as ordinary Django fields/migrations.
from django.contrib.postgres.fields import ArrayField
from mta.presentation.btr_snapshot_fields import (
    TEXT_FIELDS as _BTR_TEXT, DISPLAY_FIELDS as _BTR_DISPLAY,
    FILTER_FIELDS as _BTR_FILTER, display_field as _btr_display_field,
    filter_field as _btr_filter_field,
)
for _field in _BTR_TEXT:
    BtrPresentationRow.add_to_class(_btr_display_field(_field, 'text'), models.TextField())
for _field in _BTR_DISPLAY:
    BtrPresentationRow.add_to_class(_btr_display_field(_field, 'number'), models.FloatField(null=True))
    BtrPresentationRow.add_to_class(_btr_display_field(_field, 'text'), models.TextField(null=True))
for _owner, _fields in _BTR_FILTER.items():
    for _field, _kind in _fields.items():
        BtrPresentationRow.add_to_class(_btr_filter_field(_owner, _field),
            models.DecimalField(max_digits=38, decimal_places=10, null=True)
            if _kind == 'numeric' else models.TextField(null=True))
for _field in ('available_prefix', 'empty_prefix'):
    BtrPresentationRow.add_to_class(_field, ArrayField(models.PositiveSmallIntegerField(), size=91))
for _field in ('nonfinite_fields', 'nonfinite_tokens'):
    BtrPresentationRow.add_to_class(_field, ArrayField(models.TextField(), default=list))


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


class PlanningSourceProjection(models.Model):
    """Separate receipt for canonical derived masters; never an imported image."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    bpr_count = models.PositiveBigIntegerField()
    bpr_digest = models.CharField(max_length=64)
    git_count = models.PositiveBigIntegerField()
    git_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class PlanningBprMasterRow(models.Model):
    """One occurrence per retained importer MasterData row."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    source_ordinal = models.BigIntegerField()
    sku_key = models.TextField(null=True)
    location_key = models.TextField(null=True)
    parent_key = models.TextField(null=True)
    SKUCode = models.CharField(max_length=50)
    WHCode = models.CharField(max_length=50)
    Norm = models.IntegerField()
    ParentWhCode = models.CharField(max_length=50, null=True)
    SKUIntroDate = models.DateField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'source_ordinal'], name='planning_bpr_source_ordinal')]
        indexes = [models.Index(fields=['run', 'sku_key', 'location_key'], name='planning_bpr_source_keys')]


class PlanningGitMasterRow(models.Model):
    """One rationed/standard occurrence; flags do not multiply the source bag."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    rationed_ordinal = models.BigIntegerField()
    standard_ordinal = models.BigIntegerField()
    sku_key = models.TextField(null=True)
    location_key = models.TextField(null=True)
    parent_key = models.TextField(null=True)
    Status = models.CharField(max_length=50, null=True)
    SKUCode = models.CharField(max_length=50, null=True)
    WhCode = models.CharField(max_length=50, null=True)
    Tags = models.CharField(max_length=50, null=True)
    ParentWhCode = models.CharField(max_length=50, null=True)
    Norm = models.IntegerField(null=True)
    VirtualNorm = models.IntegerField(null=True)
    Stock = models.IntegerField(null=True)
    Git = models.IntegerField(null=True)
    PhysicalInventoryPen = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PhysicalInventoryColor = models.CharField(max_length=10, null=True)
    PipelineInventoryPen = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PipelineInventoryColor = models.CharField(max_length=10, null=True)
    Req = models.IntegerField(null=True)
    Price = models.IntegerField(null=True)
    IsParent = models.BooleanField(null=True)
    IsReceiving = models.BooleanField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'rationed_ordinal', 'standard_ordinal'],
                                               name='planning_git_source_ordinals')]
        indexes = [models.Index(fields=['run', 'sku_key', 'location_key'], name='planning_git_source_keys'),
                   models.Index(fields=['run', 'parent_key', 'sku_key'], name='planning_git_parent_keys')]
