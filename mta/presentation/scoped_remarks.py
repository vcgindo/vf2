"""Exact captured BPR history plus a fixed append-only live prefix.

This read adapter grants no write, native selection or calculation ownership.
Later journal events require a fresh binding; facts/prepared bags stay intact.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime,time,timedelta,timezone
import hashlib
import inspect

from django.db import connection
from mta.presentation import ancillary_live
from mta.presentation.context import PublicationUnavailable
from mta.runtime import ancillary_models as models,input_storage,input_v3
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts,digest,storage

FAMILY=ancillary_live.BPR
PATH=ancillary_live.PATHS[FAMILY]
INPUT='input/remark_inputs/'+FAMILY
FIELDS=('SKUCode','WhCode','Remark','Username','RemarkDate')


def recipe_digest():return digest(inspect.getsource(inspect.getmodule(recipe_digest)))


def _fail():raise PublicationUnavailable('bpr_phase_remark_owner_differs')


def verify_guards():
    from mta.runtime import daily_input_schema,daily_owner_schema,publication_schema
    from mta.runtime.ingestion_ownership import business_trigger_rows
    targets={
        'fresh_mta_remarkcapture':[
            ('daily_capture_insert',7,'guard_daily_remark_capture','',0),
            ('daily_capture_immutable',58,'deny_daily_source_mutation','',0)],
        'fresh_mta_bprcapturedremark':[
            ('daily_capture_insert',7,'guard_daily_remark_capture','',0),
            ('daily_capture_immutable',58,'deny_daily_source_mutation','',0)],
        'fresh_mta_bprliveremark':[
            ('daily_live_insert',7,'guard_daily_live_remark',FAMILY+'\\000',1),
            ('daily_live_immutable',58,'deny_daily_source_mutation','',0)],
        'fresh_mta_remarkowner':[
            ('daily_remark_owner_update',27,'guard_daily_remark_owner','',0),
            ('daily_remark_owner_no_truncate',34,'deny_daily_source_mutation','',0)],
    }
    functions={}
    for name,sql in (('guard_daily_remark_capture',daily_input_schema.FORWARD),
            ('guard_daily_live_remark',daily_owner_schema.FORWARD),
            ('guard_daily_remark_owner',daily_owner_schema.FORWARD),
            ('deny_daily_source_mutation',publication_schema.FORWARD)):
        functions[name]=sql.split('FUNCTION mta.'+name+'()',1)[1].split('AS $$',1)[1].split('$$;',1)[0]
    with connection.cursor() as cursor:
        for table,expected in targets.items():
            cursor.execute("SELECT T.tgname,T.tgtype,P.proname,encode(T.tgargs,'escape'),T.tgnargs,"
                "T.tgenabled,T.tgqual::text,T.tgattr::text,T.tgoldtable,T.tgnewtable,"
                "N.nspname,T.tgdeferrable,T.tginitdeferred FROM pg_trigger T JOIN pg_proc P ON P.oid=T.tgfoid "
                "JOIN pg_namespace N ON N.oid=P.pronamespace WHERE T.tgrelid=to_regclass(%s) AND NOT T.tgisinternal",
                ['mta.'+table])
            rows=business_trigger_rows(cursor,cursor.fetchall())
            from mta.runtime.scoped_remark_ownership import verified_business_rows
            rows=verified_business_rows(cursor,rows)
            if (sorted(r[:5] for r in rows)!=sorted(expected)
                    or any(r[5:]!=('O',None,'',None,None,'mta',False,False) for r in rows)):_fail()
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,P.proowner=C.relowner,"
            "P.prorettype='trigger'::regtype,P.pronargs=0 FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C WHERE N.nspname='mta' "
            "AND C.oid='mta.fresh_mta_remarkcapture'::regclass AND P.proname=ANY(%s) ORDER BY 1",[list(functions)])
        if cursor.fetchall()!=[(n,b,False,None,'plpgsql',True,True,True) for n,b in sorted(functions.items())]:_fail()


def _object(node):
    if type(node) is not dict or set(node)!={'object'}:_fail()
    result={}
    for key,value in node['object']:
        if type(key) is not str or key in result:_fail()
        result[key]=value
    return result


def _metadata_value(node):
    if type(node) is dict and set(node)=={'scalar'}:return node['scalar']
    return {key:_metadata_value(value) for key,value in _object(node).items()}


@dataclass(frozen=True)
class RemarkBinding:
    run: object
    capture_id: int
    watermark: int
    highwater: int
    cutoff: object
    row_count: int
    rows_digest: str
    locator: dict

    def provenance(self):return deepcopy(self.locator)

    def query(self):
        columns=','.join(map(quote,FIELDS))
        captured=('SELECT ordinal AS vf_ordinal,source_ordinal AS vf_source_ordinal,'+columns+
            ' FROM mta.fresh_mta_bprcapturedremark WHERE capture_id=%s AND ordinal>=0 AND ordinal<%s')
        live=('SELECT (%s+ordinal-%s) AS vf_ordinal,ordinal AS vf_source_ordinal,'+columns+
            ' FROM mta.fresh_mta_bprliveremark WHERE owner_id=%s AND ordinal>=%s AND ordinal<%s AND "RemarkDate">%s')
        return captured+' UNION ALL '+live,[self.capture_id,self.row_count,self.row_count,self.watermark,FAMILY,
            self.watermark,self.highwater,self.cutoff]

    def rows(self):
        query,params=self.query()
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM ('+query+') R ORDER BY vf_ordinal',params)
            names=[column[0] for column in cursor.description]
            return storage([{key:value for key,value in zip(names,row) if key in FIELDS} for row in cursor.fetchall()])

    def verify_rows(self):
        checksum=hashlib.sha256(b'[');count=0
        for record in models.BprCapturedRemark.objects.filter(capture_id=self.capture_id).order_by('ordinal').values(
                'ordinal','source_ordinal',*FIELDS).iterator(chunk_size=500):
            if record.pop('ordinal')!=count:_fail()
            if count:checksum.update(b',')
            for part in canonical_parts(record):checksum.update(part)
            count+=1
        checksum.update(b']')
        if count!=self.row_count or checksum.hexdigest()!=self.rows_digest:_fail()


def bind(sources,*,configuration_digest):
    from mta.presentation.scoped_sources import BprSources
    from mta.runtime.captured_input import SCHEMAS,origin
    from mta.runtime.input_reader import read_input
    from django.core.exceptions import ObjectDoesNotExist
    if not isinstance(sources,BprSources):_fail()
    run=sources.run
    try:
        physical=origin(run) if run.input_payload.get('schema') in SCHEMAS else run
        input_storage.read_input(physical,components=())
        node=_object(input_v3._node_at(physical.input_payload,INPUT))
        if set(node)!={'provenance_digest','provenance_receipt','watermark','cutoff','rows','rows_digest'}:_fail()
        expected={key:_metadata_value(value) for key,value in node.items() if key!='rows'}
        rows=node['rows']
        image=physical.input_payload['images'][rows['records']]
        if (image['image']!=rows['records'] or image['table']!='input/production_remark_bpr' or image['digest']!=expected['rows_digest']
                or type(image['count']) is not int or image['count']<0
                or (image['count'] and set(f[0] for f in image['fields'])!={'source_ordinal',*FIELDS})):_fail()
        capture=models.RemarkCapture.objects.get(run=run,family=FAMILY)
        owner=models.RemarkOwner.objects.get(pk=FAMILY)
        profile=read_input(run,components=('profile',))['profile']
        horizon=profile['daily_publication_config']['bpr_remark_horizon']
        if type(horizon) is not int or digest(profile)!=configuration_digest:_fail()
        cutoff=datetime.combine(run.business_date,time.min,tzinfo=timezone.utc)-timedelta(days=horizon)
        if (capture.provenance_digest!=expected['provenance_digest']
                or capture.provenance_digest!=digest(expected['provenance_receipt'])
                or owner.provenance_digest!=capture.provenance_digest
                or owner.provenance_receipt!=expected['provenance_receipt']
                or type(expected['watermark']) is not int or expected['watermark']<0
                or capture.watermark!=expected['watermark'] or owner.next_ordinal<capture.watermark
                or capture.cutoff!=cutoff or expected['cutoff']!=cutoff.isoformat()
                or capture.row_count!=image['count'] or capture.rows_digest!=expected['rows_digest']):_fail()
        if owner.provenance_receipt.get('schema')=='fresh-production-consumer-opening-v1':
            if (owner.provenance_receipt.get('initialization_id')!=input_v3._run_initialization_id(physical,None)
                    or owner.provenance_receipt.get('source_digest')!=run.mdm_input_capture.source.digest):_fail()
        verify_guards()
        locator=dict(schema='fresh-bpr-remark-read-v1',run_id=str(run.pk),input_digest=run.input_digest,
            input_manifest_digest=run.input_manifest_digest,phase_id=str(sources.acceptance_id),phase_digest=sources.acceptance_digest,
            input_physical_owner_id=str(physical.pk),input_image=deepcopy(image),capture_id=capture.pk,
            provenance_digest=capture.provenance_digest,watermark=capture.watermark,live_highwater=owner.next_ordinal,
            cutoff=cutoff.isoformat(),row_count=capture.row_count,rows_digest=capture.rows_digest,recipe_digest=recipe_digest())
        return RemarkBinding(run,capture.pk,capture.watermark,owner.next_ordinal,cutoff,capture.row_count,capture.rows_digest,locator)
    except (ObjectDoesNotExist,KeyError,TypeError,ValueError,OverflowError) as error:
        raise PublicationUnavailable('bpr_phase_remark_owner_differs') from error
