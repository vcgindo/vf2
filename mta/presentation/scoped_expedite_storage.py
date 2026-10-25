"""Immutable core Expedite occurrences; remark/request/transit reads stay separate."""
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
import inspect
from django.db import connection,transaction,DatabaseError
from django.utils import timezone
from mta.presentation import scoped_prepared,scoped_pick_storage
from mta.presentation import scoped_expedite_queries as queries,scoped_expedite_pick_queries as pick_queries
from mta.presentation.context import PublicationUnavailable
from mta.runtime import scope_expedite_models as models
from mta.runtime.relational_state import quote
from mta.serialization import digest,storage,rows_digest

SCHEMA='fresh-bpr-expedite-generation-v1'
TABLES={'grid':models.ScopeExpediteGrid,'custom':models.ScopeExpediteCustom,
    'chart':models.ScopeExpediteChartMember,'prepost':models.ScopeExpeditePrepostMember}
GROUPS={'grid':('direction','branch'),'custom':(),'chart':('direction','family'),'prepost':()}
ORDERS={'grid':pick_queries.GRID_ORDER,'custom':('fact_ordinal','nms_ordinal','bpr_ordinal','parent_description_ordinal'),
    'chart':('scope_ordinal','fact_ordinal','master_ordinal','description_ordinal','location_ordinal'),
    'prepost':('scope_ordinal','fact_ordinal')}
GRAINS=(('parent','critical'),('parent','receiving'),('parent','nil_stock'),('parent','chronic'),
    ('child','critical'),('child','receiving'))


def fields(name):
    return tuple(f.name for f in TABLES[name]._meta.local_fields if f.name not in ('id','generation'))


def recipe_digest():
    return digest(dict(schema=SCHEMA,builder=inspect.getsource(inspect.getmodule(recipe_digest)),
        queries=queries.recipe_digest(),models=inspect.getsource(models),groups=GROUPS,orders=ORDERS,grains=GRAINS,
        prepost=inspect.getsource(pick_queries.ExpeditePickQueries.prepost_members),
        pick_owner=inspect.getsource(pick_queries.bind),
        fields={name:[model._meta.get_field(f).deconstruct() for f in fields(name)] for name,model in TABLES.items()}))


def verify_guards():
    frozen=import_module('mta.runtime.migrations.0214_scope_expedite_guards')
    targets=[frozen.GENERATION,*frozen.TABLES.values()]
    expected=[]
    for table in targets:
        expected.append((table,'scope_expedite_no_truncate',34,'deny_scope_expedite_truncate',False,False,False,None,None))
        if table==frozen.GENERATION:
            expected.extend([(table,'scope_expedite_complete',21,'require_scope_expedite_complete',True,True,True,None,None),
                (table,'scope_expedite_generation_guard',31,'guard_scope_expedite_generation',False,False,False,None,None)])
        else:
            for op,kind,old,new in (('insert',4,None,'new_rows'),('update',16,'old_rows','new_rows'),
                                    ('delete',8,'old_rows',None)):
                expected.append((table,'scope_expedite_rows_'+op,kind,'guard_scope_expedite_rows',False,False,False,old,new))
    with connection.cursor() as cursor:
        cursor.execute("SELECT C.relname,T.tgname,T.tgtype,P.proname,T.tgdeferrable,T.tginitdeferred,"
            "T.tgconstraint<>0,T.tgoldtable,T.tgnewtable,T.tgenabled,N.nspname,T.tgnargs,T.tgqual::text,T.tgattr::text "
            "FROM pg_trigger T JOIN pg_class C ON C.oid=T.tgrelid "
            "JOIN pg_namespace CN ON CN.oid=C.relnamespace JOIN pg_proc P ON P.oid=T.tgfoid "
            "JOIN pg_namespace N ON N.oid=P.pronamespace "
            "WHERE CN.nspname='mta' AND C.relname=ANY(%s) AND NOT T.tgisinternal "
            "AND T.tgname NOT LIKE 'ingestion_watch_%%' ORDER BY 1,2",[targets])
        from mta.runtime.scoped_action_ownership import verified_business_rows
        rows=verified_business_rows(cursor,cursor.fetchall())
        if rows!=[(*row,'O','mta',0,None,'') for row in sorted(expected)]:
            raise PublicationUnavailable('bpr_expedite_generation_guard_coverage_differs')
        functions=('guard_scope_expedite_generation','guard_scope_expedite_rows',
                   'require_scope_expedite_complete','deny_scope_expedite_truncate')
        bodies={name:frozen.SQL.split('CREATE FUNCTION mta.'+name+'()',1)[1]
            .split('AS $guard$',1)[1].split('$guard$;',1)[0] for name in functions}
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,"
            "P.prorettype='trigger'::regtype,P.proowner=C.relowner,"
            "NOT EXISTS(SELECT 1 FROM aclexplode(COALESCE(P.proacl,acldefault('f',P.proowner))) A "
            "WHERE A.grantee<>P.proowner) FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C "
            "WHERE C.oid=to_regclass('mta.fresh_mta_scopeexpeditegeneration') "
            "AND N.nspname='mta' AND P.proname=ANY(%s) ORDER BY 1",[list(functions)])
        if cursor.fetchall()!=[(name,body,False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True)
                for name,body in sorted(bodies.items())]:
            raise PublicationUnavailable('bpr_expedite_generation_guard_body_differs')
        from mta.runtime.ingestion_ownership import require_guard_coverage,scoped_derived_body
        require_guard_coverage(cursor)
        expected_body=scoped_derived_body(cursor,minimum='0214_scope_expedite_guards')
        cursor.execute("SELECT prosrc,prosecdef,proconfig FROM pg_proc "
            "WHERE oid='mta.ingestion_watch()'::regprocedure")
        if cursor.fetchall()!=[(expected_body,True,['search_path=pg_catalog, mta'])]:
            raise PublicationUnavailable('bpr_expedite_generation_revision_owner_differs')

@contextmanager
def _owner(identifier):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.scope_expedite_generation',true)")
        previous=cursor.fetchone()[0] or ''
        cursor.execute("SELECT set_config('fresh.scope_expedite_generation',%s,true)",[str(identifier)])
    try:yield
    except DatabaseError:
        transaction.set_rollback(True);raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.scope_expedite_generation',%s,true)",[previous])

def _inserts(bound,pick,identifier):
    context=pick_queries.bind(bound.sources.run,read_binding=bound,pick_binding=pick)
    for name in TABLES:
        grains=([(d,b) for d in ('parent','child') for b in ('dispatch','availability')] if name=='grid'
            else GRAINS if name=='chart' else [()])
        for grain in grains:
            if name=='grid':query,params=queries.grid_occurrences(bound.sources.run,*grain,read_binding=bound)
            elif name=='custom':query,params=queries.custom_occurrences(bound.sources.run,read_binding=bound)
            elif name=='chart':query,params=queries.members(bound.sources.run,*grain,read_binding=bound)
            else:query,params=context.prepost_members()
            selected=[f for f in fields(name) if f not in ('ordinal',*GROUPS[name])]
            groups=','.join(map(quote,GROUPS[name]))
            projection=(','.join(['%s']*(1+len(grain)))+',row_number() OVER (ORDER BY '+
                ','.join(quote(f)+' NULLS FIRST' for f in ORDERS[name])+')-1,'+','.join(map(quote,selected)))
            yield name,('INSERT INTO mta.'+quote(TABLES[name]._meta.db_table)+' (generation_id,'+
                (groups+',' if groups else '')+'ordinal,'+','.join(map(quote,selected))+') SELECT '+projection+
                ' FROM ('+query+') occurrences'),[identifier,*grain,*params]


def _records(identifier,name):
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT '+','.join(map(quote,fields(name)))+' FROM mta.'+quote(TABLES[name]._meta.db_table)+
            ' WHERE generation_id=%s ORDER BY '+','.join(map(quote,(*GROUPS[name],'ordinal'))),[identifier])
        counts={}
        while batch:=cursor.fetchmany(500):
            for values in batch:
                row=dict(zip(fields(name),values));group=tuple(row[f] for f in GROUPS[name])
                n=counts.get(group,0)
                if row['ordinal']!=n:raise PublicationUnavailable('bpr_expedite_source_grain_order_differs:'+name)
                counts[group]=n+1
                yield storage(row)


def _receipt(identifier,name):
    count=0
    def rows():
        nonlocal count
        for row in _records(identifier,name):count+=1;yield row
    checksum=rows_digest(rows())
    return dict(count=count,digest=checksum)


def _identity(row,prepared,pick,images):
    sources=prepared.sources
    bag=dict(schema='fresh-bpr-expedite-occurrences-v1',report_generation_id=str(row.report_generation_id),
        report_generation_digest=row.report_generation_digest,source_projection_digest=row.source_projection_digest,
        pick_generation_id=str(pick.generation.pk),pick_generation_digest=pick.generation.digest,
        nms=sources.provenance(pick_queries.NMS),images=images)
    return dict(schema=SCHEMA,generation_id=str(row.pk),run_id=str(row.run_id),phase_id=str(row.phase_id),
        phase_digest=sources.acceptance_digest,snapshot_digest=sources.snapshot_digest,input_digest=sources.run.input_digest,
        input_manifest_digest=sources.run.input_manifest_digest,action_revision=row.action_revision,source_digest=row.source_digest,
        configuration_digest=row.configuration_digest,recipe_digest=row.recipe_digest,occurrences=bag)


@dataclass(frozen=True)
class ExpediteBinding:
    generation: object
    prepared: object
    pick: object

    @property
    def run_id(self):return self.generation.run_id

    @property
    def read_identity(self):
        return dict(schema=SCHEMA,generation_id=str(self.generation.pk),digest=self.generation.digest,
            prepared=self.prepared.read_identity,pick=self.pick.provenance())

    def query(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_expedite_source_unavailable:'+name)
        return ('SELECT G.run_id,'+','.join('R.'+quote(f) for f in fields(name))+' FROM mta.'+
            quote(TABLES[name]._meta.db_table)+' R JOIN mta.fresh_mta_scopeexpeditegeneration G ON G.id=R.generation_id '
            'WHERE R.generation_id=%s',[self.generation.pk])

    def verify_rows(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_expedite_source_unavailable:'+name)
        if _receipt(self.generation.pk,name)!=self.generation.metadata['occurrences']['images'][name]:
            raise PublicationUnavailable('bpr_expedite_occurrence_digest_differs:'+name)

    def rows(self,name):
        self.verify_rows(name)
        return list(_records(self.generation.pk,name))

    def image_query(self,path):return self.prepared.image_query(path)

    def fact_query(self,name):return self.prepared.fact_query(name)

    def pick_query(self):return self.pick.pick_query()

    def attributes(self):
        return {name:self.prepared.sources.rows('closing/importer/'+name) for name in ('SkuAttributeData','LocationAttributeData')}


def require_binding(run,bound):
    if not isinstance(bound,ExpediteBinding) or bound.run_id!=run.pk:
        raise PublicationUnavailable('bpr_expedite_phase_owner_differs')
    return bound


def bind(generation_id,*,expected_digest,action_revision):
    from django.core.exceptions import ObjectDoesNotExist
    try:row=models.ScopeExpediteGeneration.objects.get(pk=generation_id)
    except ObjectDoesNotExist as error:raise PublicationUnavailable('bpr_expedite_generation_missing') from error
    prepared=scoped_prepared.bind(row.report_generation_id,expected_digest=row.source_projection_digest,
        expected_report_digest=row.report_generation_digest,action_revision=action_revision,include_nms=True)
    pick=scoped_pick_storage.bind(row.pick_generation_id,expected_digest=row.pick_generation_digest,action_revision=action_revision)
    pick_queries.bind(prepared.sources.run,read_binding=prepared,pick_binding=pick)
    verify_guards();reports=prepared.reports.generation
    if (not row.sealed or row.sealed_at is None or row.digest!=expected_digest or row.digest!=digest(row.metadata)
            or row.recipe_digest!=recipe_digest() or row.action_revision!=action_revision
            or row.run_id!=prepared.run_id or row.phase_id!=reports.phase_id
            or row.source_digest!=reports.source_digest or row.configuration_digest!=reports.configuration_digest
            or set(row.metadata.get('occurrences',{}).get('images',{}))!=set(TABLES)
            or row.metadata!=_identity(row,prepared,pick,row.metadata['occurrences']['images'])):
        raise PublicationUnavailable('bpr_expedite_generation_identity_differs')
    return ExpediteBinding(row,prepared,pick)


@transaction.atomic
def prepare(report_generation_id,*,expected_report_digest,expected_source_digest,
            pick_generation_id,expected_pick_digest,action_revision):
    from mta.runtime.models import CalculationRun,ScopeReportGeneration
    reports=ScopeReportGeneration.objects.get(pk=report_generation_id)
    CalculationRun.objects.select_for_update().get(pk=reports.run_id)
    prepared=scoped_prepared.bind(report_generation_id,expected_digest=expected_source_digest,
        expected_report_digest=expected_report_digest,action_revision=action_revision,include_nms=True)
    pick=scoped_pick_storage.bind(pick_generation_id,expected_digest=expected_pick_digest,action_revision=action_revision)
    pick_queries.bind(prepared.sources.run,read_binding=prepared,pick_binding=pick)
    verify_guards();recipe=recipe_digest()
    existing=models.ScopeExpediteGeneration.objects.filter(report_generation=reports,pick_generation_id=pick_generation_id,
        recipe_digest=recipe).first()
    if existing is not None:
        bound=bind(existing.pk,expected_digest=existing.digest,action_revision=action_revision)
        for name in TABLES:bound.verify_rows(name)
        return existing
    row=models.ScopeExpediteGeneration(run_id=reports.run_id,phase_id=reports.phase_id,action_revision=action_revision,
        source_digest=reports.source_digest,configuration_digest=reports.configuration_digest,recipe_digest=recipe,
        report_generation=reports,report_generation_digest=expected_report_digest,source_projection_digest=expected_source_digest,
        pick_generation_id=pick_generation_id,pick_generation_digest=expected_pick_digest)
    with _owner(row.pk):
        row.save(force_insert=True)
        for name,sql,params in _inserts(prepared,pick,row.pk):
            with connection.cursor() as cursor:cursor.execute(sql,params)
        images={name:_receipt(row.pk,name) for name in TABLES}
        row.metadata=_identity(row,prepared,pick,images);row.digest=digest(row.metadata)
        row.sealed=True;row.sealed_at=timezone.now()
        row.save(update_fields=['metadata','digest','sealed','sealed_at'])
    bound=bind(row.pk,expected_digest=row.digest,action_revision=action_revision)
    for name in TABLES:bound.verify_rows(name)
    return row
