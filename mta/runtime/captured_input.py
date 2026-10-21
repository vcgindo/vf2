"""One-hop reuse of an intact failed native capture, without copying its rows.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from uuid import UUID
from mta.serialization import digest

SCHEMA = 'fresh-captured-input-reference-v1'
SECOND = 'fresh-captured-input-reference-v2'
SCHEMAS = (SCHEMA,SECOND)
FIELDS = {'schema', 'identity', 'origin_run_id', 'origin_manifest_digest',
          'content_digest', 'images'}


def validate(value):
    if type(value) is not dict:
        raise ValueError('Captured input reference shape differs')
    extra = {'physical_origin_run_id','physical_origin_manifest_digest'} if value.get('schema') == SECOND else set()
    if (type(value) is not dict or set(value) != FIELDS | extra
            or value['schema'] not in SCHEMAS or value['images'] != {}):
        raise ValueError('Captured input reference shape differs')
    if str(UUID(value['origin_run_id'])) != value['origin_run_id']:
        raise ValueError('Captured input origin UUID differs')
    for key in ('origin_manifest_digest', 'content_digest'):
        if (type(value[key]) is not str or len(value[key]) != 64
                or any(c not in '0123456789abcdef' for c in value[key])):
            raise ValueError('Captured input origin digest differs')
    if value['schema'] == SECOND:
        if str(UUID(value['physical_origin_run_id'])) != value['physical_origin_run_id']:
            raise ValueError('Physical captured origin UUID differs')
        pin=value['physical_origin_manifest_digest']
        if type(pin) is not str or len(pin)!=64 or any(c not in '0123456789abcdef' for c in pin):
            raise ValueError('Physical captured origin manifest differs')
    return value


def manifest(run, origin, *, final_interrupted_fourth_hop=False):
    from mta.runtime.input_v3 import _live_identity
    if type(final_interrupted_fourth_hop) is not bool:
        raise ValueError('Explicit final interrupted fourth-hop flag required')
    value = dict(schema=SCHEMA, identity=_live_identity(run, reading=False),
        origin_run_id=str(origin.pk), origin_manifest_digest=origin.input_manifest_digest,
        content_digest=origin.input_digest, images={})
    if origin.input_payload.get('schema') in SCHEMAS:
        # Default writer retains its existing maximum of three wrappers.
        # The explicit interrupted continuation may consume an intact third
        # wrapper, never a fourth origin; no fifth wrapper can be produced.
        physical=_origin(origin,second_allowed=True,
            third_allowed=final_interrupted_fourth_hop,fourth_allowed=False)
        value.update(schema=SECOND,physical_origin_run_id=str(physical.pk),
            physical_origin_manifest_digest=physical.input_manifest_digest)
    elif origin.input_payload.get('schema') != 'fresh-daily-input-manifest-v3':
        raise ValueError('Only V3 or the bounded failed captured prefix can supply inputs')
    validate(value)
    return value


def origin(run):
    return _origin(run,second_allowed=True,third_allowed=True,fourth_allowed=True)


def _origin(run,*,second_allowed,third_allowed=False,fourth_allowed=False):
    """Resolve only the immutable direct origin named by canonical retry capture.

    This cannot reference an arbitrary run, cross an initialization, replace a
    predecessor, borrow a result or form a chain of recovery references.
    """
    from mta.runtime.models import CalculationRun
    from mta.runtime.input_v3 import V3, _live_identity
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    if fourth_allowed and not third_allowed:
        raise ValueError('Fourth-hop read requires its complete third-hop prefix')
    value = validate(run.input_payload)
    if value['schema'] == SECOND and not second_allowed:
        raise ValueError('Captured reference exceeds the fixed two-hop boundary')
    if (digest(value) != run.input_manifest_digest or value['content_digest'] != run.input_digest
            or value['identity'] != _live_identity(run, reading=True)):
        raise ValueError('Captured input live owner/manifest differs')
    current = MdmDailyInputCapture.objects.select_related('source', 'origin__run').get(run=run)
    old = current.origin
    if old is None:
        raise ValueError('Captured input has no canonical retry origin')
    target = old.run
    if (str(target.pk) != value['origin_run_id'] or target.pk == run.pk
            or target.kind != 'DAILY_CHAIN' or run.kind != target.kind
            or target.status != 'FAILED' or old.status != 'CAPTURED'
            or current.source_id != old.source_id
            or current.revision_digest != old.revision_digest
            or current.request_digest != old.request_digest
            or target.business_date != run.business_date
            or target.predecessor_id != run.predecessor_id
            or target.execution_revision == run.execution_revision
            or target.output_digest or target.output_roster or target.production_digest
            or target.checkpoints.exists() or target.commands.exists()
            or target.successors.exists()
            or old.retries.exclude(pk=current.pk).exists()):
        raise ValueError('Captured input canonical origin differs')
    target_schema=target.input_payload.get('schema')
    if value['schema']==SECOND and target_schema==SECOND and not third_allowed:
        raise ValueError('Captured reference exceeds the fixed third-hop boundary')
    allowed=((V3,) if value['schema']==SCHEMA else (SCHEMA,SECOND) if third_allowed else (SCHEMA,))
    if (target_schema not in allowed
            or target.input_manifest_digest != value['origin_manifest_digest']
            or digest(target.input_payload) != value['origin_manifest_digest']
            or target.input_digest != value['content_digest']
            or target.input_payload.get('content_digest') != value['content_digest']):
        raise ValueError('Captured input original typed manifest differs')
    old_identity = _live_identity(target, reading=True)
    if any(old_identity[k] != value['identity'][k]
            for k in ('database_name', 'database_oid', 'source_digest')):
        raise ValueError('Captured input database/source differs')
    from mta.runtime.daily_feed_models import DailyFeedAttempt
    attempts = list(DailyFeedAttempt.objects.filter(run_id__in=(run.pk, target.pk))
        .values('run_id', 'initialization_id'))
    if (len(attempts) != 2 or len({v['initialization_id'] for v in attempts}) != 1):
        raise ValueError('Captured input initialization ownership differs')
    if value['schema'] == SECOND:
        # At most V2 -> V2 -> V2 -> V1 -> physical V3. Each call spends
        # its one explicit fourth allowance; the next call cannot extend it.
        # No new wire schema or arbitrary depth/loop is introduced.
        physical=_origin(target,second_allowed=(target_schema==SECOND),
            third_allowed=fourth_allowed,fourth_allowed=False)
        if (str(physical.pk)!=value['physical_origin_run_id']
                or physical.input_manifest_digest!=value['physical_origin_manifest_digest']
                or physical.input_digest!=value['content_digest']):
            raise ValueError('Fixed physical captured origin differs')
        return physical
    return CalculationRun.objects.get(pk=target.pk)


def read(run, *, components=None, **options):
    from mta.runtime.input_storage import read_input
    return read_input(origin(run), components=components, **options)


def audit(run):
    from mta.runtime.receipt_integrity import audit_input
    target = origin(run)
    audit_input(target)
    return dict(origin_run_id=str(target.pk), input_digest=target.input_digest,
                input_manifest_digest=target.input_manifest_digest)
