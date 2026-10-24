"""Explicit BPR consumer history baseline; never a calculation input recapture."""
from importlib import import_module
from django.db import connection
from mta.serialization import digest

SCHEMA='fresh-scoped-bpr-consumer-cut-v1'
FIELDS=('bpr_remark_operational_epoch','bpr_remark_action_epoch')


def lock_history_owners():
    """Match append's owner-before-revision lock order for scoped capture."""
    from mta.presentation import ancillary_live
    from mta.runtime.ancillary_models import RemarkOwner
    if not connection.in_atomic_block:raise ValueError('Scoped consumer locks require their capture transaction')
    return tuple(RemarkOwner.objects.select_for_update().filter(family__in=(
        ancillary_live.BPR,ancillary_live.BOR,ancillary_live.BOROA)).order_by('family').values_list('family',flat=True))


def verify_guards():
    from mta.runtime.ingestion_ownership import require_guard_coverage
    migration=import_module('mta.runtime.migrations.0204_scoped_bpr_consumer_ownership')
    recovery=import_module('mta.runtime.migrations.0205_scoped_bpr_consumer_recovery')
    expected={
        'ingestion_watch':(migration.NEW,True),
        'ingestion_authority_guard':(migration.NEW_AUTHORITY,False),
        'scope_native_cut':(migration.NEW_NATIVE.split('AS $body$',1)[1],False),
        'scope_retained_cut':(migration.NEW_RETAINED.split('AS $body$',1)[1],False),
        'scope_bpr_consumer_cut':(recovery.NEW,False),
    }
    with connection.cursor() as cursor:
        require_guard_coverage(cursor)
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,P.proowner=C.relowner,"
            "pg_get_function_identity_arguments(P.oid),pg_get_function_result(P.oid) "
            "FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C WHERE N.nspname='mta' "
            "AND C.oid='mta.fresh_mta_ingestionrevisionstate'::regclass AND P.proname=ANY(%s) ORDER BY 1",
            [list(expected)])
        signature=lambda name:('', 'trigger') if name.startswith('ingestion_') else (
            'target uuid, observed jsonb' if name=='scope_bpr_consumer_cut' else 'target uuid','jsonb')
        wanted=[(name,body,definer,['search_path=pg_catalog, mta'],'plpgsql',True,*signature(name))
            for name,(body,definer) in sorted(expected.items())]
        if cursor.fetchall()!=wanted:raise ValueError('Scoped BPR consumer guard contract differs')
        cursor.execute("SELECT T.tgname,T.tgtype,T.tgenabled,T.tgfoid='mta.ingestion_authority_guard()'::regprocedure,"
            "T.tgnargs,T.tgqual::text,T.tgattr::text,T.tgoldtable,T.tgnewtable,T.tgdeferrable,T.tginitdeferred "
            "FROM pg_trigger T JOIN pg_proc P ON P.oid=T.tgfoid "
            "WHERE T.tgrelid='mta.fresh_mta_ingestionrevisionstate'::regclass AND NOT T.tgisinternal ORDER BY 1")
        if cursor.fetchall()!=[('ingestion_authority',31,'O',True,0,None,'',None,None,False,False),
                ('ingestion_authority_truncate',34,'O',True,0,None,'',None,None,False,False)]:
            raise ValueError('Scoped BPR consumer authority triggers differ')
        cursor.execute("SELECT conname,pg_get_constraintdef(oid),convalidated FROM pg_constraint "
            "WHERE conrelid='mta.fresh_mta_ingestionrevisionstate'::regclass AND conname=ANY(%s) ORDER BY 1",
            [['bpr_consumer_action_bounded','bpr_consumer_operational_bounded']])
        if cursor.fetchall()!=[('bpr_consumer_action_bounded','CHECK ((bpr_remark_action_epoch <= action_epoch))',True),
                ('bpr_consumer_operational_bounded','CHECK ((bpr_remark_operational_epoch <= operational_epoch))',True)]:
            raise ValueError('Scoped BPR consumer counter constraints differ')


def capture(run,snapshot,initialization_id):
    """Called only at a new opted-in capture, under its revision-row lock.

    The existing snapshot writer already verified the complete persisted bag.
    Pin that exact immutable reference; do not hydrate the row estate again.
    """
    from datetime import datetime
    from mta.presentation import ancillary_live
    from mta.runtime.ancillary_models import RemarkCapture,RemarkOwner,BprLiveRemark
    from mta.runtime.ingestion_models import IngestionRevisionState
    from mta.runtime import input_v3
    from django.db.models import Max
    if not connection.in_atomic_block:raise ValueError('Scoped consumer capture requires its transaction')
    verify_guards()
    # The caller has locked this same revision row before observing aggregates.
    state=IngestionRevisionState.objects.values(*FIELDS).get(initialization_id=initialization_id)
    family=ancillary_live.BPR
    captured=RemarkCapture.objects.get(run=run,family=family)
    owner=RemarkOwner.objects.get(pk=family)
    if owner.provenance_receipt.get('schema')=='fresh-production-consumer-opening-v1':
        if (owner.provenance_receipt.get('initialization_id')!=str(initialization_id)
                or owner.provenance_receipt.get('source_digest')!=run.mdm_input_capture.source.digest):
            raise ValueError('Scoped BPR consumer initialization or source differs')
    node=input_v3._node_at(run.input_payload,'input/remark_inputs/'+family)
    raw=dict(node['object'])
    scalar=lambda name:raw[name]['scalar']
    image=run.input_payload['images'][raw['rows']['records']]
    if (digest(run.input_payload)!=run.input_manifest_digest
            or captured.provenance_digest!=snapshot['provenance_digest']
            or digest(snapshot['provenance_receipt'])!=captured.provenance_digest
            or owner.provenance_digest!=captured.provenance_digest
            or owner.provenance_receipt!=snapshot['provenance_receipt']
            or captured.watermark!=snapshot['watermark'] or owner.next_ordinal<captured.watermark
            or captured.cutoff!=datetime.fromisoformat(snapshot['cutoff'])
            or captured.row_count!=len(snapshot['rows']) or captured.rows_digest!=snapshot['rows_digest']
            or any(scalar(name)!=snapshot[name] for name in ('provenance_digest','watermark','cutoff','rows_digest'))
            or image['table']!='input/production_remark_bpr' or image['image']!=raw['rows']['records']
            or image['count']!=captured.row_count or image['digest']!=captured.rows_digest):
        raise ValueError('Scoped BPR consumer capture owner differs')
    last=BprLiveRemark.objects.filter(owner=owner).aggregate(value=Max('ordinal'))['value']
    if owner.next_ordinal!=(0 if last is None else last+1):
        raise ValueError('Scoped BPR consumer journal prefix is incomplete')
    return dict(schema=SCHEMA,capture_id=captured.pk,provenance_digest=captured.provenance_digest,
        watermark=captured.watermark,operational=state[FIELDS[0]],action=state[FIELDS[1]])
