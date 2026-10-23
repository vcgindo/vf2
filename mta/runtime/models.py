"""Single run identity and atomic checkpoint storage for the fresh engine."""
import uuid
from django.db import models
from django.db.models.functions import Lower


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
    input_manifest_digest = models.CharField(max_length=64, blank=True)
    evidence_mode = models.CharField(max_length=16, default='production')
    validation_digest = models.CharField(max_length=64, blank=True)
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


class BorSourceReceipt(models.Model):
    """Bounded checksum metadata for four immutable retained consumer bags."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    bor_digest = models.CharField(max_length=64)
    sob_digest = models.CharField(max_length=64)
    moq_digest = models.CharField(max_length=64)
    history_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class BorSourceRow(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'], name='bor_source_ordinal')]


class BorSobRow(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'], name='bor_sob_ordinal')]


class BorMoqRow(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'], name='bor_moq_ordinal')]


class BorInitialRemark(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'], name='bor_initial_remark_ordinal')]


class BorLiveRemark(models.Model):
    """Application history; never changes immutable run images or commands."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    actor_id = models.CharField(max_length=256)


from mta.presentation.bor_contract import FIELDS as _BOR_FIELDS
for _model, _table in ((BorSourceRow, 'SupplierDispatchReq'), (BorSobRow, 'SOBData'),
        (BorMoqRow, 'MOQData'), (BorInitialRemark, 'BORReport_RemarkDetails'),
        (BorLiveRemark, 'BORReport_RemarkDetails')):
    for _name, _kind in _BOR_FIELDS[_table].items():
        _field = {
            'text50': lambda: models.CharField(max_length=50),
            'nullable50': lambda: models.CharField(max_length=50, null=True),
            'nullable100': lambda: models.CharField(max_length=100, null=True),
            'nullable_text': lambda: models.TextField(null=True),
            'int': models.IntegerField, 'float': models.FloatField,
            'datetime': models.DateTimeField,
        }[_kind]()
        _model.add_to_class(_name, _field)


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
                                name='fresh_bpr_prepared_keys'),
                   models.Index(fields=['run', 'sku_key', 'location_key'],
                                condition=models.Q(s_ordinal__isnull=False),
                                name='fresh_bpr_count_keys')]


from mta.presentation.bpr_prepared_fields import FIELDS as _BPR_FIELDS, field_name as _bpr_field_name
for _owner, _fields in _BPR_FIELDS.items():
    for _field, _kind in _fields.items():
        _factory = {'text': models.TextField, 'bigint': models.BigIntegerField,
                    'numeric': BprNumericField}[_kind]
        BprPreparedRow.add_to_class(_bpr_field_name(_owner, _field), _factory(null=True))


class BorPreparedReceipt(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    rows_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class BorPreparedRow(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    sku_key = models.TextField(null=True)
    location_key = models.TextField(null=True)
    supplier_key = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'], name='bor_prepared_ordinal')]
        indexes = [models.Index(fields=['run','sku_key','location_key'],name='bor_prepared_pair')]


from mta.presentation.bor_prepared_fields import FIELDS as _BOR_PREPARED_FIELDS, field_name as _bor_field_name
for _owner,_fields in _BOR_PREPARED_FIELDS.items():
    BorPreparedRow.add_to_class(_owner.lower()+'_ordinal',models.BigIntegerField(null=True))
    for _name,_kind in _fields.items():
        BorPreparedRow.add_to_class(_bor_field_name(_owner,_name),
            {'text':models.TextField,'bigint':models.BigIntegerField,
             'numeric':BprNumericField,'float':models.FloatField}[_kind](null=True))


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
                                name='fresh_guided_avail_cover'),
                   models.Index(models.F('run'), Lower(models.Func(models.F('sku_code'), models.Value(' '), function='RTRIM')), models.F('report_date'), name='fresh_guided_avail_sku'),
                   models.Index(models.F('run'), Lower(models.Func(models.F('location_code'), models.Value(' '), function='RTRIM')), models.F('report_date'), name='fresh_guided_avail_loc')]


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
    fact_run = models.ForeignKey(CalculationRun, null=True, on_delete=models.PROTECT, related_name='+')
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
        indexes = [models.Index(fields=['run', 'fact_run', 'fact_ordinal'], name='fresh_guided_excess_fact'),
                   models.Index(fields=['run', 'report_date'],
                                name='fresh_guided_excess_date'),
                   models.Index(models.F('run'), Lower(models.Func(models.F('sku_code'), models.Value(' '), function='RTRIM')), models.F('report_date'), name='fresh_guided_excess_sku'),
                   models.Index(models.F('run'), Lower(models.Func(models.F('location_code'), models.Value(' '), function='RTRIM')), models.F('report_date'), name='fresh_guided_excess_loc')]


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
    # Existing legacy events may have no typed manifest. They remain sealed;
    # only record_command explicitly opens a new append owner in its transaction.
    state_sealed = models.BooleanField(default=True, db_default=False)
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


class RrrPreparedProjection(models.Model):
    """Immutable receipt for the retained RRR join membership."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    dimension_digest = models.CharField(max_length=64)
    pick_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()
    rows_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class RrrPreparedMembership(models.Model):
    """One exact Pick/source/dimension occurrence before live scope and filters."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    band_ordinal = models.PositiveBigIntegerField()
    rationed_ordinal = models.BigIntegerField()
    standard_ordinal = models.BigIntegerField()
    pair_ordinal = models.BigIntegerField()
    sku_ordinal = models.BigIntegerField()
    location_ordinal = models.BigIntegerField()
    left_pair_ordinal = models.BigIntegerField(null=True)
    sku_key = models.TextField()
    location_key = models.TextField()
    parent_key = models.TextField(null=True)
    virtual = models.BooleanField()
    dispatch_color_sequence = models.BigIntegerField(null=True)
    dispatch_pen = BprNumericField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'], name='rrr_prepared_member_ordinal')]
        indexes = [
            models.Index(fields=['run', 'sku_key', 'location_key'], name='rrr_prepared_scope_keys'),
            models.Index(fields=['run', 'dispatch_color_sequence', 'dispatch_pen'], name='rrr_prepared_order'),
        ]


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
        indexes = [models.Index(fields=['run', 'ReportDate'],
                               include=['SKUCode', 'WhCode'], name='fresh_excess_run_date')]


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


class PlanningGridProjection(models.Model):
    """Receipt for the two normal-grid occurrence grains, excluding charts/custom."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    excess_count = models.PositiveBigIntegerField()
    excess_digest = models.CharField(max_length=64)
    fulfillment_count = models.PositiveBigIntegerField()
    fulfillment_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class PlanningGridOccurrence(models.Model):
    """Shared columns only; each consumer has a distinct typed physical relation."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.BigIntegerField()
    fact_ordinal = models.BigIntegerField()
    sku_description_ordinal = models.BigIntegerField()
    location_description_ordinal = models.BigIntegerField()
    sku_ordinal = models.BigIntegerField()
    location_ordinal = models.BigIntegerField()
    pair_ordinal = models.BigIntegerField()
    sku_key = models.TextField(null=True)
    location_key = models.TextField(null=True)
    parent_key = models.TextField(null=True)
    sku_description = models.TextField(null=True)
    location_description = models.TextField(null=True)
    sl1 = models.TextField(null=True)
    sl2 = models.TextField(null=True)
    sl3 = models.TextField(null=True)
    sl4 = models.TextField(null=True)
    sl5 = models.TextField(null=True)
    ll1 = models.TextField(null=True)
    ll2 = models.TextField(null=True)
    ll3 = models.TextField(null=True)
    ll4 = models.TextField(null=True)
    ll5 = models.TextField(null=True)

    class Meta:
        abstract = True


class PlanningExcessGridRow(PlanningGridOccurrence):
    parent_description_ordinal = models.BigIntegerField(null=True)
    parent_description = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'], name='planning_excess_grid_ordinal')]
        indexes = [models.Index(fields=['run', 'sku_key', 'location_key'], name='planning_excess_grid_keys')]


class PlanningFulfillmentGridRow(PlanningGridOccurrence):
    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'ordinal'], name='planning_fulfill_grid_ordinal')]
        indexes = [models.Index(fields=['run', 'sku_key', 'location_key'], name='planning_fulfill_grid_keys')]


class PlanningChartProjection(models.Model):
    """Separate sealed description-membership and post-aggregate display grains."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    member_count = models.PositiveBigIntegerField()
    member_digest = models.CharField(max_length=64)
    display_count = models.PositiveBigIntegerField()
    display_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class PlanningChartMember(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    family = models.CharField(max_length=24)
    direction = models.CharField(max_length=8)
    ordinal = models.PositiveBigIntegerField()
    group_ordinal = models.PositiveBigIntegerField()
    fact_ordinal = models.PositiveBigIntegerField()
    description_ordinal = models.PositiveBigIntegerField()
    code = models.TextField(null=True)
    description = models.TextField(null=True)
    band = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','family','direction','ordinal'],name='fresh_planning_chart_member')]
        indexes = [models.Index(fields=['run','family','direction','group_ordinal'],name='fresh_plan_chart_member_group')]


class PlanningChartDisplay(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    family = models.CharField(max_length=24)
    direction = models.CharField(max_length=8)
    ordinal = models.PositiveBigIntegerField()
    group_ordinal = models.PositiveBigIntegerField()
    attribute_ordinal = models.PositiveBigIntegerField()
    h1 = models.TextField(null=True)
    h2 = models.TextField(null=True)
    h3 = models.TextField(null=True)
    h4 = models.TextField(null=True)
    h5 = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','family','direction','ordinal'],name='fresh_planning_chart_display')]
        indexes = [models.Index(fields=['run','family','direction','group_ordinal'],name='fresh_plan_chart_display_group')]


class PlanningCustomProjection(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    excess_count = models.PositiveBigIntegerField()
    excess_digest = models.CharField(max_length=64)
    fulfillment_count = models.PositiveBigIntegerField()
    fulfillment_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class PlanningCustomOccurrence(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    fact_ordinal = models.PositiveBigIntegerField()
    nms_ordinal = models.PositiveBigIntegerField(null=True)
    parent_description_ordinal = models.PositiveBigIntegerField(null=True)
    sku_key = models.TextField(null=True)
    location_key = models.TextField(null=True)
    parent_description = models.TextField(null=True)

    class Meta:
        abstract = True


class PlanningExcessCustomRow(PlanningCustomOccurrence):
    standard_ordinal = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='fresh_plan_excess_custom_ord')]
        indexes = [models.Index(fields=['run','sku_key','location_key'],name='fresh_plan_excess_custom_key')]


class PlanningFulfillmentCustomRow(PlanningCustomOccurrence):
    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='fresh_plan_fulfill_custom_ord')]
        indexes = [models.Index(fields=['run','sku_key','location_key'],name='fresh_plan_fulfill_custom_key')]


class PlanningGitProjection(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()
    rows_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class PlanningGitOccurrence(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    rationed_ordinal = models.PositiveBigIntegerField()
    standard_ordinal = models.PositiveBigIntegerField()
    sku_description_ordinal = models.PositiveBigIntegerField()
    location_description_ordinal = models.PositiveBigIntegerField()
    parent_description_ordinal = models.PositiveBigIntegerField(null=True)
    sku_ordinal = models.PositiveBigIntegerField()
    location_ordinal = models.PositiveBigIntegerField()
    pair_ordinal = models.PositiveBigIntegerField(null=True)
    sku_description = models.TextField(null=True)
    location_description = models.TextField(null=True)
    parent_description = models.TextField(null=True)
    grid_eligible = models.BooleanField()
    sl1 = models.TextField(null=True)
    sl2 = models.TextField(null=True)
    sl3 = models.TextField(null=True)
    sl4 = models.TextField(null=True)
    sl5 = models.TextField(null=True)
    ll1 = models.TextField(null=True)
    ll2 = models.TextField(null=True)
    ll3 = models.TextField(null=True)
    ll4 = models.TextField(null=True)
    ll5 = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='fresh_planning_git_occurrence')]


class PlanningExpediteGridProjection(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()
    rows_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class PlanningExpediteGridOccurrence(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    direction = models.CharField(max_length=8)
    branch = models.CharField(max_length=16)
    ordinal = models.PositiveBigIntegerField()
    fact_ordinal = models.PositiveBigIntegerField()
    standard_ordinal = models.PositiveBigIntegerField(null=True)
    sku_description_ordinal = models.PositiveBigIntegerField(null=True)
    location_description_ordinal = models.PositiveBigIntegerField(null=True)
    parent_description_ordinal = models.PositiveBigIntegerField(null=True)
    sku_ordinal = models.PositiveBigIntegerField(null=True)
    location_ordinal = models.PositiveBigIntegerField(null=True)
    pair_ordinal = models.PositiveBigIntegerField(null=True)
    master_ordinal = models.PositiveBigIntegerField(null=True)
    sku_description = models.TextField(null=True)
    location_description = models.TextField(null=True)
    parent_description = models.TextField(null=True)
    sl1 = models.TextField(null=True)
    sl2 = models.TextField(null=True)
    sl3 = models.TextField(null=True)
    sl4 = models.TextField(null=True)
    sl5 = models.TextField(null=True)
    ll1 = models.TextField(null=True)
    ll2 = models.TextField(null=True)
    ll3 = models.TextField(null=True)
    ll4 = models.TextField(null=True)
    ll5 = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','direction','branch','ordinal'],name='fresh_plan_expedite_grid_ord')]


class PlanningExpediteTransitProjection(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    pick_digest = models.CharField(max_length=64)
    base_count = models.PositiveBigIntegerField()
    base_digest = models.CharField(max_length=64)
    match_count = models.PositiveBigIntegerField()
    match_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class PlanningExpediteTransitBase(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    nms_ordinal = models.PositiveBigIntegerField()
    remark_ordinal = models.PositiveBigIntegerField(null=True)
    sku_code = models.TextField(null=True)
    location_code = models.TextField(null=True)
    sku_key = models.TextField(null=True)
    location_key = models.TextField(null=True)
    rlt = models.IntegerField(null=True)
    remark = models.TextField(null=True)
    remark_key = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='plan_exp_transit_base_ord')]


class PlanningExpediteTransitMatch(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    base_ordinal = models.PositiveBigIntegerField()
    branch = models.CharField(max_length=16)
    grid_ordinal = models.PositiveBigIntegerField()
    pick_ordinal = models.PositiveBigIntegerField(null=True)
    parent_stock = models.IntegerField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='plan_exp_transit_match_ord')]
        indexes = [models.Index(fields=['run','branch','grid_ordinal'],name='plan_exp_transit_grid')]


class PlanningExpediteCustomProjection(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()
    rows_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class PlanningExpediteCustomOccurrence(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    fact_ordinal = models.PositiveBigIntegerField()
    nms_ordinal = models.PositiveBigIntegerField(null=True)
    bpr_ordinal = models.PositiveBigIntegerField(null=True)
    parent_description_ordinal = models.PositiveBigIntegerField(null=True)
    sku_key = models.TextField(null=True)
    location_key = models.TextField(null=True)
    parent_description = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='plan_expedite_custom_ord')]


class PlanningExpediteChartProjection(models.Model):
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    source_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    pick_digest = models.CharField(max_length=64)
    member_count = models.PositiveBigIntegerField()
    member_digest = models.CharField(max_length=64)
    prepost_count = models.PositiveBigIntegerField()
    prepost_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class PlanningExpediteChartMember(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    direction = models.CharField(max_length=8)
    family = models.CharField(max_length=16)
    ordinal = models.PositiveBigIntegerField()
    scope_ordinal = models.PositiveBigIntegerField()
    fact_ordinal = models.PositiveBigIntegerField()
    master_ordinal = models.PositiveBigIntegerField(null=True)
    description_ordinal = models.PositiveBigIntegerField()
    location_ordinal = models.PositiveBigIntegerField(null=True)
    code = models.TextField(null=True)
    code_key = models.TextField(null=True)
    description = models.TextField(null=True)
    description_key = models.TextField(null=True)
    logisticslocation = models.TextField(null=True)
    ll1 = models.TextField(null=True)
    ll2 = models.TextField(null=True)
    ll3 = models.TextField(null=True)
    ll4 = models.TextField(null=True)
    ll5 = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','direction','family','ordinal'],name='plan_exp_chart_member_ord')]


class PlanningExpeditePrepostMember(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    scope_ordinal = models.PositiveBigIntegerField()
    fact_ordinal = models.PositiveBigIntegerField()
    multiplicity = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],name='plan_exp_prepost_member_ord')]


class HistoryPreparedProjection(models.Model):
    """Ready-only receipt for the retained Research and Buffer Trends grains."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, default='READY')
    source_digest = models.CharField(max_length=64)
    dimension_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    research_master_count = models.PositiveBigIntegerField()
    research_master_digest = models.CharField(max_length=64)
    research_history_count = models.PositiveBigIntegerField()
    research_history_digest = models.CharField(max_length=64)
    availability_count = models.PositiveBigIntegerField()
    availability_digest = models.CharField(max_length=64)
    graph_count = models.PositiveBigIntegerField()
    graph_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(status='READY'),
                                               name='history_prepared_ready_only')]


class ResearchPreparedMasterReference(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    owner_sku_key = models.TextField()
    owner_location_key = models.TextField()
    rationed_ordinal = models.BigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'], name='research_master_ref_ordinal')]
        indexes = [models.Index(fields=['run','owner_sku_key','owner_location_key'],
                                name='research_master_ref_owner')]


class ResearchPreparedHistoryReference(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    owner_sku_key = models.TextField()
    owner_location_key = models.TextField()
    family = models.CharField(max_length=16)
    history_ordinal = models.BigIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['run','ordinal'], name='research_history_ref_ordinal'),
            models.CheckConstraint(condition=models.Q(family__in=['physical','dispatch']),
                                   name='research_history_ref_family'),
        ]
        indexes = [models.Index(fields=['run','owner_sku_key','owner_location_key','family'],
                                name='research_history_ref_owner')]


class ResearchAvailabilityMembership(models.Model):
    """Physical history x SKU x location occurrences; deliberately no pair join."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    history_ordinal = models.BigIntegerField()
    sku_ordinal = models.BigIntegerField()
    location_ordinal = models.BigIntegerField()
    sku_key = models.TextField()
    location_key = models.TextField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'], name='research_availability_member_ord')]
        indexes = [models.Index(fields=['run','sku_key','location_key'],
                                name='research_availability_keys')]


class BufferGraphPreparedMembership(models.Model):
    """Raw graph history and dimension occurrence membership before live filters."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    family = models.CharField(max_length=16)
    history_ordinal = models.BigIntegerField()
    sku_ordinal = models.BigIntegerField()
    location_ordinal = models.BigIntegerField()
    pair_ordinal = models.BigIntegerField(null=True)
    sku_key = models.TextField()
    location_key = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['run','ordinal'], name='buffer_graph_member_ordinal'),
            models.CheckConstraint(condition=models.Q(family__in=['physical','dispatch']),
                                   name='buffer_graph_member_family'),
        ]
        indexes = [models.Index(fields=['run','family','sku_key','location_key'],
                                name='buffer_graph_member_keys')]


class ResearchAvailabilityBandProjection(models.Model):
    """Ready-only receipt for per-occurrence Research availability counts."""
    run = models.OneToOneField(CalculationRun, primary_key=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, default='READY')
    source_digest = models.CharField(max_length=64)
    membership_digest = models.CharField(max_length=64)
    recipe_digest = models.CharField(max_length=64)
    row_count = models.PositiveBigIntegerField()
    rows_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(status='READY'),
                                               name='research_availability_band_ready')]


class ResearchAvailabilityBand(models.Model):
    """Six band counts at the exact existing availability occurrence grain."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    history_ordinal = models.BigIntegerField()
    sku_code = models.TextField()
    location_code = models.TextField()
    black_01_30 = models.PositiveSmallIntegerField()
    recognized_01_30 = models.PositiveSmallIntegerField()
    black_31_60 = models.PositiveSmallIntegerField()
    recognized_31_60 = models.PositiveSmallIntegerField()
    black_61_90 = models.PositiveSmallIntegerField()
    recognized_61_90 = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run','ordinal'],
                                               name='research_availability_band_ord')]
        indexes = [models.Index(fields=['run','sku_code','location_code'],
                                name='research_avail_band_scope')]

# Additive BOR-OA publication models; calculation models above remain unchanged.
from mta.runtime.boroa_models import (BorOaSourceReceipt, BorOaSourceRow, BorOaRequirement, BorOaInitialRemark, BorOaLiveRemark, BorOaPreparedReceipt, BorOaPreparedRow)

from mta.runtime.mdm_models import (MdmSource, MdmSkuAttributes, MdmSkuDescription,
    MdmDraft, MdmDraftMaster, MdmDraftSku, MdmTask, MdmSubTask, MdmSkuRequested,
    MdmSkuHistory, MdmSkuApproved, MdmSkuUploadLog, MdmSkuUse,
    MdmFamilySource, MdmLocationAttributes, MdmLocationDescription,
    MdmLocationRequested, MdmLocationHistory, MdmLocationApproved,
    MdmDraftLocation, MdmLocationUploadLog, MdmLocationUse)

from mta.runtime.mdm_skuloc_models import (MdmSkuLocCurrent, MdmSkuLocPair,
    MdmSkuLocMasterPair, MdmSkuLocAddRequested, MdmSkuLocModifyRequested,
    MdmSkuLocRemoveRequested, MdmSkuLocHistory, MdmSkuLocAddApproved,
    MdmSkuLocModifyApproved, MdmSkuLocRemoveApproved, MdmDraftSkuLoc,
    MdmSkuLocAddUploadLog, MdmSkuLocModifyUploadLog, MdmSkuLocRemoveUploadLog)

from mta.runtime.mdm_daily_models import (MdmDailyInputCapture, MdmDailyInputOccurrence,
    MdmDailyInputTask, MdmDailyInputHistory, MdmDailySkuArchive, MdmDailyLocationArchive,
    MdmDailySkuLocAddArchive, MdmDailySkuLocModifyArchive, MdmDailySkuLocRemoveArchive,
    MdmPairExclusionSource, MdmPairExclusion, MdmDailyPairExclusion)
from mta.runtime.report_aggregate_models import (
    ReportAggregateReceipt, ReportScopeMember, GuidedHistoryAggregate)
from mta.runtime.publication_models import (DailySourceReceipt, DailyColorSequence, DailyOpeningSob,
    DailyUiPublication, DailyUiPublicationAttempt, DailyUiActivation, DailyPlanningExtension)
from mta.runtime.daily_request_models import (DailyRequestOwner, DailyOpenRequest,
    DailyRequestCapture, DailyCapturedRequest)
from mta.runtime.ancillary_models import (RemarkOwner, RemarkCapture,
    BprLiveRemark, BorLiveRemarkDaily, BorOaLiveRemarkDaily,
    BprCapturedRemark, BorCapturedRemark, BorOaCapturedRemark)
from mta.runtime.daily_transit_models import DailyTransitRaw, DailyTransitRow
from mta.runtime.logistics_models import (LogisticsHistoryOwner, TransitLiveGeneration,
    TransitAnnotation, TransitRemarkHistory, ExpediteRemarkHistory)
from mta.runtime.daily_rrr_models import DailyRrrColourReceipt, DailyRrrColourRow

from mta.runtime.offline_rrr_models import OfflineRrrColourSource, OfflineRrrColourRow

from mta.runtime.operational_models import (OperationalConfiguration, OperationalSetting,
    OperationalInputTable, OperationalAlertSetting, OperationalAttempt, OperationalOperation,
    OperationalFile, OperationalArchiveMember, OperationalAlertIntent,
    OperationalIntentAttachment, OperationalIntentEvaluation, OperationalBackup, OperationalRepairTarget)

from mta.runtime.operational_native import OperationalPopulation
from mta.runtime.operational_admission_models import OperationalAcceptance
from mta.runtime.operational_source_models import (
    OperationalCaptureAuthorization, OperationalCalculationSource, OperationalRequirementBand, OperationalAdvanceStock,
    OperationalInputSource, OperationalForceSource,
)
from mta.runtime.mdm_force_models import (MdmForceOwner, MdmForceQueue,
    MdmForceRequested, MdmForceHistory, MdmForceUploadLog, MdmDraftForce,
    MdmForceTaskRevision, MdmForceConsumed, MdmForceDisplayOwner, MdmForceDisplayRow)
from mta.runtime.mdm_supplier_models import (MdmSupplierConfiguration,
    MdmDraftSob, MdmDraftMoq, MdmSobRequested, MdmSobHistory, MdmMoqRequested,
    MdmMoqHistory, MdmSobApproved, MdmMoqWithDestinationApproved,
    MdmMoqWithoutDestinationApproved, MdmSobRaw, MdmMoqRaw1, MdmMoqRaw2,
    MdmSobUploadLog, MdmMoqUploadLog, MdmSobArchive,
    MdmMoqWithDestinationArchive, MdmMoqWithoutDestinationArchive, MdmSupplierTaskRevision)

from mta.runtime.mdm_season_models import (MdmSeasonOwner, MdmSeasonQueue,
    MdmSeasonCurrent, MdmSeasonRequested, MdmSeasonHistory,
    MdmSeasonStatusRequested, MdmSeasonStatusHistory, MdmSeasonTaskRevision,
    MdmSeasonEligibility, MdmSeasonConsumed, MdmDraftSeason)

from mta.runtime.mdm_stop_pipo_models import (MdmStopPipoOwner, MdmStopPipoQueue,
    MdmStopPipoRequested, MdmStopPipoHistory, MdmStopPipoTaskRevision,
    MdmStopPipoConsumed, MdmDraftStopPipo)

from mta.runtime.mdm_phase_controls_models import (MdmPhaseControlsOwner,
    MdmPhaseOutRequested, MdmPhaseOutHistory, MdmPhaseOutQueue, MdmPhaseOutConsumed,
    MdmPhaseInNormRequested, MdmPhaseInNormHistory, MdmPhaseInNormQueue,
    MdmPhaseInNormConsumed, MdmPhaseControlsTaskRevision, MdmDraftAddPipo)

from mta.runtime.mdm_integration_models import MdmSourceIntegration
from mta.runtime.mdm_target_fixture_models import (MdmTargetFixture,
    MdmFixturePhaseOut, MdmFixturePhaseIn, MdmFixturePhaseMap, MdmFixtureSeasonStatus)

from mta.runtime.planning_summary_models import (PlanningSummaryReceipt,
    PlanningSummaryContribution, PlanningSummaryAttempt)

from mta.runtime.initialization_models import ProductionInitialization
from mta.runtime.ingestion_models import (
    InitializationCertification, MasterInputRevision, IngestionReleaseCompatibility,
    IngestionRevisionState)
from mta.runtime.daily_feed_models import DailyFeedAttempt

from mta.runtime.mdm_projection_models import MdmClosingProjectionReceipt
from mta.runtime.native_audit_models import (NativeUploadAudit, NativeAuditAdd,
    NativeAuditModify, NativeAuditRemove, NativeAuditLocation, NativeAuditSku,
    NativeAuditSob, NativeAuditMoq, NativeAuditForce)

from mta.runtime.report_generation_models import DailyReportGeneration, DailyReportOrderRouteSource
