"""Frozen child-Expedite request capture for one accepted BPR source owner.

Live workflow requests are independent. Missing ownership is unavailable;
explicitly captured empty input is an owned zero-row relation.
"""
from copy import deepcopy
from dataclasses import dataclass
import inspect
from django.db import connection
from mta.presentation import daily_requests
from mta.presentation.context import PublicationUnavailable
from mta.runtime import daily_request_models as models,input_storage,input_v3
from mta.runtime.relational_state import quote
from mta.serialization import digest,rows_digest

FIELDS=daily_requests.FIELDS
DATES=daily_requests.DATES
INPUT='input/request_inputs'


def _fail():raise PublicationUnavailable('bpr_phase_request_owner_differs')


def recipe_digest():
    return digest(dict(schema='fresh-bpr-request-read-v1',source=inspect.getsource(inspect.getmodule(recipe_digest)),
        fields=FIELDS,dates=sorted(DATES),schema_sha=daily_requests.SCHEMA_SHA,
        native_schema=inspect.getsource(daily_requests._schema)))


def verify_guards():
    from mta.runtime import daily_input_schema,daily_owner_schema,publication_schema
    from mta.runtime.ingestion_ownership import business_trigger_rows
    targets={
        'fresh_mta_dailyrequestcapture':[
            ('daily_capture_insert',7,'guard_daily_request_capture'),
            ('daily_capture_immutable',58,'deny_daily_source_mutation')],
        'fresh_mta_dailycapturedrequest':[
            ('daily_capture_insert',7,'guard_daily_request_capture'),
            ('daily_capture_immutable',58,'deny_daily_source_mutation')],
        'fresh_mta_dailyrequestowner':[
            ('daily_request_owner',27,'guard_daily_request_owner'),
            ('daily_request_owner_truncate',34,'deny_daily_source_mutation')],
    }
    functions={}
    for name,sql in (('guard_daily_request_capture',daily_input_schema.FORWARD),
            ('guard_daily_request_owner',daily_owner_schema.FORWARD),
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
            if (sorted(r[:3] for r in rows)!=sorted(expected)
                    or any(r[3:]!=('',0,'O',None,'',None,None,'mta',False,False) for r in rows)):_fail()
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,P.proowner=C.relowner,"
            "P.prorettype='trigger'::regtype,P.pronargs=0 FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C WHERE N.nspname='mta' "
            "AND C.oid='mta.fresh_mta_dailyrequestcapture'::regclass AND P.proname=ANY(%s) ORDER BY 1",[list(functions)])
        if cursor.fetchall()!=[(n,b,False,None,'plpgsql',True,True,True) for n,b in sorted(functions.items())]:_fail()
        cursor.execute("SELECT attname,format_type(atttypid,atttypmod),attnotnull FROM pg_attribute "
            "WHERE attrelid='mta.fresh_mta_dailycapturedrequest'::regclass AND attname=ANY(%s) AND NOT attisdropped ORDER BY 1",
            [sorted(DATES)])
        if cursor.fetchall()!=[(name,'timestamp with time zone',False) for name in sorted(DATES)]:_fail()


def _object(node):
    if type(node) is not dict or set(node)!={'object'}:_fail()
    value={}
    for key,item in node['object']:
        if type(key) is not str or key in value:_fail()
        value[key]=item
    return value


def _scalar(node):
    if type(node) is not dict or set(node)!={'scalar'}:_fail()
    return node['scalar']


@dataclass(frozen=True)
class RequestBinding:
    sources: object
    capture_id: object
    row_count: int
    rows_digest: str
    locator: dict

    def provenance(self):return deepcopy(self.locator)

    def _query(self,*,complete=False):
        # Existing capture columns encode native wall times as UTC instants.
        # Return native SQL datetime cells independently of session timezone.
        selected=[quote(f)+(" AT TIME ZONE 'UTC' AS "+quote(f) if f in DATES else '') for f in FIELDS]
        return ('SELECT ordinal AS vf_ordinal,'+','.join(selected)+
            ' FROM mta.fresh_mta_dailycapturedrequest WHERE capture_id=%s'+
            ('' if complete else ' AND ordinal>=0 AND ordinal<%s')),[self.capture_id,*(() if complete else (self.row_count,))]

    def query(self):return self._query()

    def _records(self,*,complete=False):
        query,params=self._query(complete=complete)
        with connection.chunked_cursor() as cursor:
            cursor.execute(query+' ORDER BY ordinal',params)
            count=0
            while batch:=cursor.fetchmany(500):
                for ordinal,*values in batch:
                    if ordinal!=count:_fail()
                    yield {name:(value.isoformat() if name in DATES and value is not None else value)
                        for name,value in zip(FIELDS,values)}
                    count+=1

    def rows(self):
        rows=list(self._records())
        if len(rows)!=self.row_count or digest(rows)!=self.rows_digest:_fail()
        return rows

    def verify_rows(self):
        count=0
        def records():
            nonlocal count
            for record in self._records(complete=True):count+=1;yield record
        checksum=rows_digest(records())
        if count!=self.row_count or checksum!=self.rows_digest:_fail()


def bind(sources):
    from mta.presentation.scoped_sources import BprSources
    from mta.runtime.captured_input import SCHEMAS,origin
    from django.core.exceptions import ObjectDoesNotExist
    if not isinstance(sources,BprSources):_fail()
    run=sources.run
    try:
        physical=origin(run) if run.input_payload.get('schema') in SCHEMAS else run
        input_storage.read_input(physical,components=())
        node=_object(input_v3._node_at(physical.input_payload,INPUT))
        if set(node)!={'owner','revision','provenance_digest','rows','rows_digest'}:_fail()
        expected={key:_scalar(value) for key,value in node.items() if key!='rows'}
        rows=node['rows']
        if (type(rows) is not dict or type(rows.get('records')) is not str or rows.get('children')!=[]):_fail()
        image=physical.input_payload['images'][rows['records']]
        if (image['image']!=rows['records'] or image['table']!='input/production_request'
                or type(image['count']) is not int or image['count']<0 or image['digest']!=expected['rows_digest']
                or 'count' in rows and (type(rows['count']) is not int or rows['count']!=image['count'])
                or image['count'] and set(f[0] for f in image['fields'])!=set(FIELDS)
                or expected['owner']!=daily_requests.OWNER or type(expected['revision']) is not int or expected['revision']<0):_fail()
        capture=models.DailyRequestCapture.objects.get(run=run)
        owner=models.DailyRequestOwner.objects.get(pk=daily_requests.OWNER)
        if (capture.run_id!=run.pk or capture.owner_id!=expected['owner'] or capture.revision!=expected['revision']
                or capture.provenance_digest!=expected['provenance_digest']
                or owner.provenance_digest!=capture.provenance_digest or digest(owner.provenance)!=owner.provenance_digest
                or owner.revision<capture.revision or capture.row_count!=image['count']
                or capture.rows_digest!=image['digest']):_fail()
        if owner.provenance.get('schema')=='fresh-production-consumer-opening-v1':
            if (owner.provenance.get('initialization_id')!=input_v3._run_initialization_id(physical,None)
                    or owner.provenance.get('source_digest')!=run.mdm_input_capture.source.digest):_fail()
        daily_requests._schema();verify_guards()
        locator=dict(schema='fresh-bpr-request-read-v1',run_id=str(run.pk),phase_id=str(sources.acceptance_id),
            phase_digest=sources.acceptance_digest,source_digest=sources.source_digest,action_revision=sources.action_revision,
            input_digest=run.input_digest,input_manifest_digest=run.input_manifest_digest,
            input_physical_owner_id=str(physical.pk),input_image=deepcopy(image),capture_id=str(capture.pk),
            owner=capture.owner_id,revision=capture.revision,provenance_digest=capture.provenance_digest,
            row_count=capture.row_count,rows_digest=capture.rows_digest,recipe_digest=recipe_digest())
        return RequestBinding(sources,capture.pk,capture.row_count,capture.rows_digest,locator)
    except (ObjectDoesNotExist,KeyError,TypeError,ValueError,OverflowError,OSError) as error:
        raise PublicationUnavailable('bpr_phase_request_owner_differs') from error
