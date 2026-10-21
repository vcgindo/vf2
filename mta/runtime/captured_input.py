"""One-hop reuse of an intact failed native capture, without copying its rows.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from uuid import UUID
from mta.serialization import digest

SCHEMA = 'fresh-captured-input-reference-v1'
SECOND = 'fresh-captured-input-reference-v2'
FINITE = 'fresh-captured-input-reference-v3'
SCHEMAS = (SCHEMA,SECOND,FINITE)
FIELDS = {'schema', 'identity', 'origin_run_id', 'origin_manifest_digest',
          'content_digest', 'images'}


def validate(value):
    if type(value) is not dict:
        raise ValueError('Captured input reference shape differs')
    extra = {'physical_origin_run_id','physical_origin_manifest_digest'} if value.get('schema') in (SECOND,FINITE) else set()
    if value.get('schema') == FINITE:
        extra |= {'prefix_digest','origin_attempt_id','execution_revision','packaged_source'}
    if (type(value) is not dict or set(value) != FIELDS | extra
            or value['schema'] not in SCHEMAS or value['images'] != {}):
        raise ValueError('Captured input reference shape differs')
    if str(UUID(value['origin_run_id'])) != value['origin_run_id']:
        raise ValueError('Captured input origin UUID differs')
    for key in ('origin_manifest_digest', 'content_digest'):
        if (type(value[key]) is not str or len(value[key]) != 64
                or any(c not in '0123456789abcdef' for c in value[key])):
            raise ValueError('Captured input origin digest differs')
    if value['schema'] in (SECOND,FINITE):
        if str(UUID(value['physical_origin_run_id'])) != value['physical_origin_run_id']:
            raise ValueError('Physical captured origin UUID differs')
        pin=value['physical_origin_manifest_digest']
        if type(pin) is not str or len(pin)!=64 or any(c not in '0123456789abcdef' for c in pin):
            raise ValueError('Physical captured origin manifest differs')
    if value['schema'] == FINITE:
        for key in ('prefix_digest','packaged_source'):
            pin=value[key]
            length=40 if key=='packaged_source' else 64
            if type(pin) is not str or len(pin)!=length or any(c not in '0123456789abcdef' for c in pin):
                raise ValueError('Finite captured prefix/package digest differs')
        if (str(UUID(value['origin_attempt_id'])) != value['origin_attempt_id']
                or value['execution_revision'] != 'native-finite-'+value['packaged_source']):
            raise ValueError('Finite captured execution identity differs')
    return value


def manifest(run, origin, *, final_interrupted_fourth_hop=False, final_failed_fifth_hop=False,
             final_interrupted_sixth_hop=False):
    from mta.runtime.input_v3 import _live_identity
    flags=(final_interrupted_fourth_hop,final_failed_fifth_hop,final_interrupted_sixth_hop)
    if any(type(flag) is not bool for flag in flags) or sum(flags)>1:
        raise ValueError('Explicit mutually exclusive terminal continuation flag required')
    if final_interrupted_sixth_hop and origin.status != 'FAILED':
        raise ValueError('Final interrupted continuation requires a reconciled FAILED fifth wrapper')
    if final_failed_fifth_hop and origin.status != 'FAILED':
        raise ValueError('Final failed continuation requires a FAILED fourth wrapper')
    value = dict(schema=SCHEMA, identity=_live_identity(run, reading=False),
        origin_run_id=str(origin.pk), origin_manifest_digest=origin.input_manifest_digest,
        content_digest=origin.input_digest, images={})
    if origin.input_payload.get('schema') in SCHEMAS:
        # Default writer3, interrupted4 and FAILED-fourth writer5 stay fixed.
        # Only the explicit human-interrupted fifth can create terminal6.
        physical=_origin(origin,second_allowed=True,
            third_allowed=any(flags),
            fourth_allowed=final_failed_fifth_hop or final_interrupted_sixth_hop,
            fifth_allowed=final_interrupted_sixth_hop)
        if final_interrupted_sixth_hop:
            try:
                _origin(origin,second_allowed=True,third_allowed=True,fourth_allowed=True)
            except ValueError as error:
                if str(error) != 'Captured reference exceeds the fixed third-hop boundary':
                    raise
            else:
                raise ValueError('Final interrupted continuation requires exactly five wrappers')
        if final_failed_fifth_hop:
            try:
                _origin(origin,second_allowed=True,third_allowed=True)
            except ValueError as error:
                if str(error) != 'Captured reference exceeds the fixed third-hop boundary':
                    raise
            else:
                raise ValueError('Final failed continuation requires exactly four wrappers')
        value.update(schema=SECOND,physical_origin_run_id=str(physical.pk),
            physical_origin_manifest_digest=physical.input_manifest_digest)
    elif final_interrupted_sixth_hop:
        raise ValueError('Final interrupted continuation requires exactly five wrappers')
    elif final_failed_fifth_hop:
        raise ValueError('Final failed continuation requires exactly four wrappers')
    elif origin.input_payload.get('schema') != 'fresh-daily-input-manifest-v3':
        raise ValueError('Only V3 or the bounded failed captured prefix can supply inputs')
    validate(value)
    return value


def origin(run):
    if run.input_payload.get('schema') == FINITE:
        return finite_origin(run)
    return _origin(run,second_allowed=True,third_allowed=True,fourth_allowed=True,fifth_allowed=True,sixth_allowed=True)


def _metadata(instance):
    """Complete bounded metadata, including original timestamps and error bodies."""
    return {field.attname:(str(value) if isinstance(value,UUID) else value)
            for field in instance._meta.concrete_fields
            for value in (getattr(instance,field.attname),)}


def _finite_prefix_digest(leaf):
    """Database-native complete metadata digest, fixed UTC/ISO in SQL owner."""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT mta.finite_capture_prefix_digest(%s)',[leaf.pk])
        return cursor.fetchone()[0]


def finite_prefix(leaf):
    """Authenticate exactly six old wrappers with the unchanged bounded reader."""
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.daily_feed_models import DailyFeedAttempt
    physical=_origin(leaf,second_allowed=True,third_allowed=True,fourth_allowed=True,
                     fifth_allowed=True,sixth_allowed=True)
    rows=[]; current=leaf; seen=set()
    for index in range(7):
        if current.pk in seen:
            raise ValueError('Finite captured prefix contains a cycle')
        seen.add(current.pk)
        capture=MdmDailyInputCapture.objects.select_related('origin__run').get(run=current)
        attempt=DailyFeedAttempt.objects.get(run=current)
        if (current.status != ('RUNNING' if index==0 else 'FAILED')
                or capture.status!='CAPTURED'
                or (index==0 and (attempt.status!='RUNNING' or attempt.phase!='CALCULATE'
                                  or attempt.accepted_facts))
                or (index>0 and attempt.status!='FAILED')
                or current.input_payload.get('schema') !=
                    (SECOND if index<5 else SCHEMA if index==5 else 'fresh-daily-input-manifest-v3')):
            raise ValueError('Finite captured prefix requires exact stopped six-wrapper ownership')
        rows.append(dict(run=_metadata(current),capture=_metadata(capture),attempt=_metadata(attempt)))
        if index==6:
            if capture.origin_id is not None or current.pk!=physical.pk:
                raise ValueError('Finite physical captured origin differs')
        else:
            if capture.origin is None:
                raise ValueError('Finite captured prefix requires exactly six wrappers')
            current=capture.origin.run
    return physical,rows,_finite_prefix_digest(leaf)


def finite_manifest(run, leaf, *, expected_prefix_digest, packaged_source):
    from mta.runtime.input_v3 import _live_identity
    physical,rows,prefix=finite_prefix(leaf)
    if prefix!=expected_prefix_digest:
        raise ValueError('Finite captured independently inspected prefix differs')
    value=dict(schema=FINITE,identity=_live_identity(run,reading=False),
        origin_run_id=str(leaf.pk),origin_manifest_digest=leaf.input_manifest_digest,
        origin_attempt_id=rows[0]['attempt']['attempt_id'],prefix_digest=prefix,
        content_digest=leaf.input_digest,images={},physical_origin_run_id=str(physical.pk),
        physical_origin_manifest_digest=physical.input_manifest_digest,
        execution_revision=run.execution_revision,packaged_source=packaged_source)
    return validate(value)


def finite_origin(run):
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.daily_feed_models import DailyFeedAttempt
    from mta.runtime.input_v3 import _live_identity
    value=validate(run.input_payload)
    if (value['schema']!=FINITE or digest(value)!=run.input_manifest_digest
            or value['content_digest']!=run.input_digest
            or value['identity']!=_live_identity(run,reading=True)
            or value['execution_revision']!=run.execution_revision):
        raise ValueError('Finite captured live owner/manifest differs')
    current=MdmDailyInputCapture.objects.select_related('origin__run').get(run=run)
    old=current.origin
    if old is None or str(old.run_id)!=value['origin_run_id'] or old.run_id==run.pk:
        raise ValueError('Finite captured canonical leaf differs')
    leaf=old.run
    physical,rows,prefix=finite_prefix(leaf)
    attempts=list(DailyFeedAttempt.objects.filter(run_id__in=(run.pk,leaf.pk))
                  .values('run_id','initialization_id','recovery_origin_id'))
    if (prefix!=value['prefix_digest'] or rows[0]['attempt']['attempt_id']!=value['origin_attempt_id']
            or leaf.input_manifest_digest!=value['origin_manifest_digest']
            or str(physical.pk)!=value['physical_origin_run_id']
            or physical.input_manifest_digest!=value['physical_origin_manifest_digest']
            or physical.input_digest!=run.input_digest or leaf.kind!=run.kind or run.kind!='DAILY_CHAIN'
            or leaf.business_date!=run.business_date or leaf.predecessor_id!=run.predecessor_id
            or leaf.execution_revision==run.execution_revision
            or current.source_id!=old.source_id or current.request_digest!=old.request_digest
            or current.revision_digest!=old.revision_digest
            or old.retries.exclude(pk=current.pk).exists()
            or len(attempts)!=2 or len({row['initialization_id'] for row in attempts})!=1
            or next((row['recovery_origin_id'] for row in attempts if row['run_id']==run.pk),None)
                != rows[0]['attempt']['id']
            or any(value['identity'][key]!=_live_identity(leaf,reading=True)[key]
                   for key in ('database_name','database_oid','source_digest'))):
        raise ValueError('Finite captured prefix/physical ownership differs')
    return physical


def _origin(run,*,second_allowed,third_allowed=False,fourth_allowed=False,fifth_allowed=False,sixth_allowed=False):
    """Resolve only the immutable direct origin named by canonical retry capture.

    This cannot reference an arbitrary run, cross an initialization, replace a
    predecessor, borrow a result or form a chain of recovery references.
    """
    from mta.runtime.models import CalculationRun
    from mta.runtime.input_v3 import V3, _live_identity
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    if sixth_allowed and not (third_allowed and fourth_allowed and fifth_allowed):
        raise ValueError('Sixth-hop read requires its complete fifth-hop prefix')
    if fifth_allowed and not (third_allowed and fourth_allowed):
        raise ValueError('Fifth-hop read requires its complete fourth-hop prefix')
    if fourth_allowed and not third_allowed:
        raise ValueError('Fourth-hop read requires its complete third-hop prefix')
    value = validate(run.input_payload)
    if value['schema'] == FINITE:
        raise ValueError('Finite captured reference cannot supply another continuation')
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
        # Fixed terminal6: V2 -> V2 -> V2 -> V2 -> V2 -> V1 -> physical V3.
        # Spend allowances once; no depth argument or seventh wrapper.
        physical=_origin(target,second_allowed=(target_schema==SECOND),
            third_allowed=fourth_allowed,fourth_allowed=fifth_allowed,
            fifth_allowed=sixth_allowed,sixth_allowed=False)
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
