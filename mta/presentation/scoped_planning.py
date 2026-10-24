"""Prepare the six distinct Excess/Fulfillment Planning grains once per owner.

This is a dependency of scope readiness, not an application selection. Full
tables, terminal admission and unrelated GIT/Expedite populations stay separate.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
import hashlib
import inspect

from django.db import connection,transaction,DatabaseError
from django.utils import timezone
from mta.presentation import scoped_prepared,scoped_planning_queries as queries
from mta.presentation.context import PublicationUnavailable
from mta.runtime import scope_planning_models as models
from mta.runtime.relational_state import quote
from mta.serialization import canonical_parts,digest,storage

SCHEMA='fresh-bpr-planning-projection-v1'
TABLES={
    'excess_grid':models.ScopePlanningExcessGrid,
    'fulfillment_grid':models.ScopePlanningFulfillmentGrid,
    'excess_custom':models.ScopePlanningExcessCustom,
    'fulfillment_custom':models.ScopePlanningFulfillmentCustom,
    'chart_members':models.ScopePlanningChartMember,
    'chart_displays':models.ScopePlanningChartDisplay,
}


def fields(name):
    return tuple(f.name for f in TABLES[name]._meta.local_fields if f.name not in ('id','generation'))


def recipe_digest():
    from mta.presentation import planning_grid_preparation,planning_custom_preparation,planning_chart_preparation
    return digest(dict(schema=SCHEMA,builder=inspect.getsource(inspect.getmodule(recipe_digest)),
        queries=inspect.getsource(queries),models=inspect.getsource(models),
        dimensions=queries.DIMENSIONS,families=list(queries.FAMILIES),
        field_contracts={name:[model._meta.get_field(field).deconstruct() for field in fields(name)]
                         for name,model in TABLES.items()},
        original_recipes=[module.production_recipe_digest() for module in
            (planning_grid_preparation,planning_custom_preparation,planning_chart_preparation)]))


def verify_guards():
    frozen=import_module('mta.runtime.migrations.0202_scope_planning_guards')
    # Same finite trigger/function contract as the source projection, with its
    # own relation roster and migration-frozen bodies. No prefix-only trust.
    expected=[]
    for table in (frozen.PROJECTION,*(t for t,_o,_d in frozen.TABLES.values())):
        expected.append((table,'scope_planning_no_truncate',34,'deny_scope_planning_truncate',False,False,False,None,None))
        if table==frozen.PROJECTION:
            expected.extend([(table,'scope_planning_complete',21,'require_scope_planning_complete',True,True,True,None,None),
                (table,'scope_planning_projection_guard',31,'guard_scope_planning_projection',False,False,False,None,None)])
        else:
            for op,kind,old,new in (('insert',4,None,'new_rows'),('update',16,'old_rows','new_rows'),('delete',8,'old_rows',None)):
                expected.append((table,'scope_planning_rows_'+op,kind,'guard_scope_planning_rows',False,False,False,old,new))
    with connection.cursor() as cursor:
        cursor.execute("SELECT C.relname,T.tgname,T.tgtype,P.proname,T.tgdeferrable,T.tginitdeferred,"
            "T.tgconstraint<>0,T.tgoldtable,T.tgnewtable,T.tgenabled,T.tgnargs,T.tgqual::text,T.tgattr::text,"
            "N.nspname FROM pg_trigger T JOIN pg_class C ON C.oid=T.tgrelid "
            "JOIN pg_proc P ON P.oid=T.tgfoid JOIN pg_namespace N ON N.oid=P.pronamespace "
            "WHERE C.relnamespace='mta'::regnamespace AND C.relname=ANY(%s) AND NOT T.tgisinternal "
            "AND T.tgname NOT LIKE 'ingestion_watch_%%'",[[row[0] for row in expected]])
        actual=cursor.fetchall()
        if sorted(row[:9] for row in actual)!=sorted(expected) or any(row[9:]!=('O',0,None,'','mta') for row in actual):
            raise PublicationUnavailable('bpr_planning_guard_roster_differs')
        bodies={name:frozen.SQL.split('CREATE FUNCTION mta.'+name+'()',1)[1].split('AS $guard$',1)[1].split('$guard$;',1)[0]
                for name in frozen.FUNCTIONS}
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,P.proowner=C.relowner,"
            "P.prorettype='trigger'::regtype,P.pronargs=0 FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C "
            "WHERE C.oid='mta.fresh_mta_scopeplanningprojection'::regclass AND N.nspname='mta' "
            "AND P.proname=ANY(%s) ORDER BY 1",[list(frozen.FUNCTIONS)])
        if cursor.fetchall()!=[(name,body,False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True) for name,body in sorted(bodies.items())]:
            raise PublicationUnavailable('bpr_planning_guard_body_differs')
        from mta.runtime.ingestion_ownership import require_guard_coverage,scoped_derived_body
        require_guard_coverage(cursor)
        cursor.execute("SELECT prosrc,prosecdef,proconfig FROM pg_proc WHERE oid='mta.ingestion_watch()'::regprocedure")
        if cursor.fetchall()!=[(scoped_derived_body(cursor,minimum='0202_scope_planning_guards'),True,['search_path=pg_catalog, mta'])]:
            raise PublicationUnavailable('bpr_planning_revision_owner_differs')


def _inserts(bound):
    run=bound.sources.run
    for family in ('excess','fulfillment'):
        for grain,builder in (('grid',queries.grid_occurrences),('custom',queries.custom_occurrences)):
            name=family+'_'+grain
            query,params=builder(run,family,bound)
            selected=[f for f in fields(name) if f!='ordinal']
            order=(['fact_ordinal','sku_description_ordinal','location_description_ordinal']+
                (['parent_description_ordinal'] if family=='excess' else [])+
                ['sku_ordinal','location_ordinal','pair_ordinal']) if grain=='grid' else (
                ['fact_ordinal','nms_ordinal','parent_description_ordinal']+(['standard_ordinal'] if family=='excess' else []))
            yield name,('INSERT INTO mta.'+quote(TABLES[name]._meta.db_table)+
                ' (generation_id,ordinal,'+','.join(map(quote,selected))+') SELECT %s,row_number() OVER (ORDER BY '+
                ','.join(quote(f)+' NULLS FIRST' for f in order)+')-1,'+','.join(map(quote,selected))+
                ' FROM ('+query+') occurrences'),[bound.reports.generation.pk,*params]
    for family in queries.FAMILIES:
        for direction in ('sku','location'):
            for grain,(query,params) in queries.chart_ingredients(run,family,direction,bound).items():
                name='chart_'+grain
                selected=[f for f in fields(name) if f not in ('family','direction')]
                yield name,('INSERT INTO mta.'+quote(TABLES[name]._meta.db_table)+
                    ' (generation_id,family,direction,'+','.join(map(quote,selected))+') SELECT %s,%s,%s,'+
                    ','.join(map(quote,selected))+' FROM ('+query+') ingredients'),[
                    bound.reports.generation.pk,family,direction,*params]


def _records(generation_id,name):
    order=('family','direction','ordinal') if name.startswith('chart_') else ('ordinal',)
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT '+','.join(map(quote,fields(name)))+' FROM mta.'+quote(TABLES[name]._meta.db_table)+
            ' WHERE generation_id=%s ORDER BY '+','.join(map(quote,order)),[generation_id])
        counters={}
        while batch:=cursor.fetchmany(500):
            for values in batch:
                row=dict(zip(fields(name),values))
                grain=(row['family'],row['direction']) if name.startswith('chart_') else ()
                n=counters.get(grain,0)
                if row['ordinal']!=n:raise PublicationUnavailable('bpr_planning_order_differs:'+name)
                counters[grain]=n+1
                yield row


def _receipt(generation_id,name):
    checksum=hashlib.sha256(b'[');count=0
    for record in _records(generation_id,name):
        if count:checksum.update(b',')
        for part in canonical_parts(record):checksum.update(part)
        count+=1
    checksum.update(b']')
    return dict(count=count,digest=checksum.hexdigest())


def _identity(bound,recipe,images):
    generation=bound.reports.generation
    return dict(schema=SCHEMA,generation_id=str(generation.pk),report_generation_digest=generation.digest,
        source_projection_digest=bound.projection.digest,phase_id=str(generation.phase_id),
        phase_digest=generation.metadata['phase_digest'],source_digest=generation.source_digest,
        nms_source=bound.sources.provenance('closing/consumer_context/NMSAllItems'),
        action_revision=generation.action_revision,recipe_digest=recipe,images=images)


@contextmanager
def _owner(generation_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.scope_planning_generation',true)")
        previous=cursor.fetchone()[0] or ''
        cursor.execute("SELECT set_config('fresh.scope_planning_generation',%s,true)",[str(generation_id)])
    try:yield
    except DatabaseError:
        transaction.set_rollback(True);raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.scope_planning_generation',%s,true)",[previous])


@dataclass(frozen=True)
class PlanningBinding:
    projection: object
    prepared: object

    @property
    def run_id(self):return self.prepared.run_id

    @property
    def read_identity(self):
        return dict(schema=SCHEMA,planning_digest=self.projection.digest,prepared=self.prepared.read_identity)

    def query(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_planning_source_unavailable:'+name)
        return ('SELECT G.run_id,'+','.join('R.'+quote(f) for f in fields(name))+' FROM mta.'+
            quote(TABLES[name]._meta.db_table)+' R JOIN mta.fresh_mta_scopereportgeneration G ON G.id=R.generation_id '
            'WHERE R.generation_id=%s',[self.projection.pk])

    def rows(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_planning_source_unavailable:'+name)
        if _receipt(self.projection.pk,name)!=self.projection.metadata['images'][name]:
            raise PublicationUnavailable('bpr_planning_rows_differ:'+name)
        return storage(list(_records(self.projection.pk,name)))

    def fact_query(self,name):return self.prepared.fact_query(name)

    def image_query(self,path):return self.prepared.image_query(path)

    def attributes(self):
        # Same exact source rows as the query side; no terminal projection.
        return {name:self.prepared.sources.rows('closing/importer/'+name)
                for name in ('SkuAttributeData','LocationAttributeData')}


def require_binding(run,bound):
    if not isinstance(bound,PlanningBinding) or bound.run_id!=run.pk:
        raise PublicationUnavailable('bpr_planning_phase_owner_differs')
    return bound


def bind(generation_id,*,expected_digest,expected_source_digest,expected_report_digest,action_revision):
    from django.core.exceptions import ObjectDoesNotExist
    prepared=scoped_prepared.bind(generation_id,expected_digest=expected_source_digest,
        expected_report_digest=expected_report_digest,action_revision=action_revision,include_nms=True)
    verify_guards()
    try:projection=models.ScopePlanningProjection.objects.get(generation_id=generation_id)
    except ObjectDoesNotExist as error:raise PublicationUnavailable('bpr_planning_projection_missing') from error
    if (not projection.sealed or projection.sealed_at is None or projection.digest!=expected_digest
            or projection.digest!=digest(projection.metadata) or projection.recipe_digest!=recipe_digest()
            or projection.report_generation_digest!=expected_report_digest
            or projection.source_projection_digest!=prepared.projection.digest
            or set(projection.metadata.get('images',{}))!=set(TABLES)
            or projection.metadata!=_identity(prepared,projection.recipe_digest,projection.metadata['images'])):
        raise PublicationUnavailable('bpr_planning_projection_identity_differs')
    return PlanningBinding(projection,prepared)


@transaction.atomic
def prepare(generation_id,*,expected_source_digest,expected_report_digest,action_revision):
    from mta.runtime.models import CalculationRun,ScopeReportGeneration
    generation=ScopeReportGeneration.objects.get(pk=generation_id)
    CalculationRun.objects.select_for_update().get(pk=generation.run_id)
    prepared=scoped_prepared.bind(generation_id,expected_digest=expected_source_digest,
        expected_report_digest=expected_report_digest,action_revision=action_revision,include_nms=True)
    verify_guards()
    existing=models.ScopePlanningProjection.objects.filter(generation_id=generation_id).first()
    if existing is not None:
        bound=bind(generation_id,expected_digest=existing.digest,expected_source_digest=expected_source_digest,
            expected_report_digest=expected_report_digest,action_revision=action_revision)
        for name in TABLES:
            if _receipt(generation_id,name)!=bound.projection.metadata['images'][name]:
                raise PublicationUnavailable('bpr_planning_repeat_differs:'+name)
        return existing
    projection=models.ScopePlanningProjection(generation=generation,report_generation_digest=generation.digest,
        source_projection_digest=prepared.projection.digest,recipe_digest=recipe_digest())
    with _owner(generation_id):
        projection.save(force_insert=True)
        inserted=dict.fromkeys(TABLES,0)
        with connection.cursor() as cursor:
            for name,query,params in _inserts(prepared):
                cursor.execute(query,params);inserted[name]+=cursor.rowcount
        images={name:_receipt(generation_id,name) for name in TABLES}
        if inserted!={name:item['count'] for name,item in images.items()}:
            raise PublicationUnavailable('bpr_planning_insert_readback_differs')
        projection.metadata=_identity(prepared,projection.recipe_digest,images)
        projection.digest=digest(projection.metadata);projection.sealed=True;projection.sealed_at=timezone.now()
        projection.save(update_fields=['metadata','digest','sealed','sealed_at'])
    bind(generation_id,expected_digest=projection.digest,expected_source_digest=expected_source_digest,
        expected_report_digest=expected_report_digest,action_revision=action_revision)
    return projection
