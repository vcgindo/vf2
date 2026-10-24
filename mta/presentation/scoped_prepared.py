"""Prepare immutable BPR candidates and Planning masters for one phase view.

This owns three prepared bags only. It does not admit a native application,
select a view, borrow terminal facts, or supply missing BTR/ancillary data.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
import hashlib,inspect

from django.db import connection,transaction,DatabaseError
from django.utils import timezone
from mta.presentation.context import PublicationUnavailable
from mta.presentation import scoped_report_storage as facts,scoped_sources,bpr_candidate_sql,planning_source_sql
from mta.presentation.bpr_prepared_fields import SOURCES,FIELDS,field_name,schema_digest
from mta.presentation.rrr_sql import key
from mta.runtime import scope_prepared_models as models,phase_state
from mta.runtime.relational_state import PG_TYPES,quote
from mta.serialization import canonical_parts,digest,storage

SCHEMA='fresh-bpr-source-projection-v1'
BPR_FIELDS=('ordinal','sku_key','location_key',*(owner.lower()+'_ordinal' for owner in SOURCES),
    *(field_name(owner,name) for owner,fields in FIELDS.items() for name in fields))
TABLES={
    'bpr_candidates':(models.ScopeBprCandidateRow,BPR_FIELDS,('ordinal',),True),
    'bpr_master':(models.ScopePlanningBprRow,('source_ordinal','sku_key','location_key','parent_key',
        *planning_source_sql.BPR_FIELDS),('source_ordinal',),True),
    'git_master':(models.ScopePlanningGitRow,('rationed_ordinal','standard_ordinal','sku_key','location_key','parent_key',
        *planning_source_sql.GIT_FIELDS),('rationed_ordinal','standard_ordinal'),False),
}


def recipe_digest():
    return digest(dict(schema=SCHEMA,builder=inspect.getsource(inspect.getmodule(recipe_digest)),
        models=inspect.getsource(models),numeric=inspect.getsource(models.BprNumericField),
        bpr_schema=schema_digest(),candidate=inspect.getsource(bpr_candidate_sql),
        planning=inspect.getsource(planning_source_sql)))


def verify_guards():
    frozen=import_module('mta.runtime.migrations.0200_scope_source_guards')
    expected=[];targets=[frozen.PROJECTION,*(item[0] for item in frozen.TABLES.values())]
    for table in targets:
        expected.append((table,'scope_source_no_truncate',34,'deny_scope_source_truncate',False,False,False,None,None))
        if table==frozen.PROJECTION:
            expected.extend([(table,'scope_source_complete',21,'require_scope_source_complete',True,True,True,None,None),
                (table,'scope_source_projection_guard',31,'guard_scope_source_projection',False,False,False,None,None)])
        else:
            for op,kind,old,new in (('insert',4,None,'new_rows'),('update',16,'old_rows','new_rows'),('delete',8,'old_rows',None)):
                expected.append((table,'scope_source_rows_'+op,kind,'guard_scope_source_rows',False,False,False,old,new))
    with connection.cursor() as cursor:
        cursor.execute("SELECT C.relname,T.tgname,T.tgtype,P.proname,T.tgdeferrable,T.tginitdeferred,"
            "T.tgconstraint<>0,T.tgoldtable,T.tgnewtable,T.tgenabled,N.nspname,T.tgnargs,T.tgqual::text,T.tgattr::text "
            "FROM pg_trigger T JOIN pg_class C ON C.oid=T.tgrelid JOIN pg_namespace CN ON CN.oid=C.relnamespace "
            "JOIN pg_proc P ON P.oid=T.tgfoid JOIN pg_namespace N ON N.oid=P.pronamespace "
            "WHERE CN.nspname='mta' AND C.relname=ANY(%s) AND NOT T.tgisinternal "
            "AND T.tgname NOT LIKE 'ingestion_watch_%%' ORDER BY 1,2",[targets])
        if cursor.fetchall()!=[(*row,'O','mta',0,None,'') for row in sorted(expected)]:
            raise PublicationUnavailable('bpr_source_projection_guard_coverage_differs')
        bodies={name:frozen.SQL.split('CREATE FUNCTION mta.'+name+'()',1)[1]
            .split('AS $guard$',1)[1].split('$guard$;',1)[0] for name in frozen.FUNCTIONS}
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,"
            "P.prorettype='trigger'::regtype,P.proowner=C.relowner,"
            "NOT EXISTS(SELECT 1 FROM aclexplode(COALESCE(P.proacl,acldefault('f',P.proowner))) A "
            "WHERE A.grantee<>P.proowner) FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C "
            "WHERE C.oid=to_regclass('mta.fresh_mta_scopesourceprojection') AND N.nspname='mta' "
            "AND P.proname=ANY(%s) ORDER BY 1",[list(frozen.FUNCTIONS)])
        if cursor.fetchall()!=[(name,body,False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True)
                for name,body in sorted(bodies.items())]:
            raise PublicationUnavailable('bpr_source_projection_guard_body_differs')
        from mta.runtime.ingestion_ownership import require_guard_coverage,scoped_derived_body
        require_guard_coverage(cursor)
        expected_body=scoped_derived_body(cursor,minimum='0200_scope_source_guards')
        cursor.execute("SELECT prosrc,prosecdef,proconfig FROM pg_proc WHERE oid='mta.ingestion_watch()'::regprocedure")
        if cursor.fetchall()!=[(expected_body,True,['search_path=pg_catalog, mta'])]:
            raise PublicationUnavailable('bpr_source_projection_revision_owner_differs')


def _bpr_insert(sources,generation):
    bindings={}
    for owner,path in SOURCES.items():
        item=sources.metadata(path)
        native=dict(phase_state.REGISTRY[item['table']])
        published={name:PG_TYPES[native[column]] for name,column,_kind in item['fields']}
        if item['count']==0 and not item['fields']:
            published={name:PG_TYPES[kind] for name,kind in native.items()}
        for name,kind in FIELDS[owner].items():
            if published.get(name)!=kind:
                raise PublicationUnavailable('bpr_phase_prepared_field_type_differs:'+owner+'.'+name)
        bindings[owner]=sources.query(path)
    ctes,selected,joins,params=bpr_candidate_sql.components(bindings)
    return ('WITH '+','.join(ctes)+' INSERT INTO mta.'+quote(models.ScopeBprCandidateRow._meta.db_table)+
        ' ('+','.join(quote(name) for name in ('generation_id',*BPR_FIELDS))+') SELECT '+
        ','.join(['%s',*selected])+joins,[*params,generation.pk])


def _planning_inserts(sources,generation):
    master,mp=sources.query('closing/importer/MasterData')
    rationed,rp=sources.query('reports/bpr/vf_RationedReqReport')
    standard,sp=sources.query('closing/dbm/SKULocStandardAttributes')
    for name,query,params,location in (
            ('bpr_master',planning_source_sql.bpr_master_query(master),mp,'WHCode'),
            ('git_master',planning_source_sql.git_master_query(rationed,standard),[*rp,*sp],'WhCode')):
        model,fields,ordinals,_dense=TABLES[name]
        selected=['%s',*map(quote,ordinals),key('"SKUCode"'),key(quote(location)),key('"ParentWhCode"'),
                  *map(quote,planning_source_sql.BPR_FIELDS if name=='bpr_master' else planning_source_sql.GIT_FIELDS)]
        yield name,('INSERT INTO mta.'+quote(model._meta.db_table)+' ('+
            ','.join(map(quote,('generation_id',*fields)))+') SELECT '+','.join(selected)+
            ' FROM ('+query+') derived'),[generation.pk,*params]


def _records(generation,name):
    model,fields,ordinals,dense=TABLES[name]
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT '+','.join(map(quote,fields))+' FROM mta.'+quote(model._meta.db_table)+
            ' WHERE generation_id=%s ORDER BY '+','.join(map(quote,ordinals)),[generation.pk])
        count=0
        while batch:=cursor.fetchmany(500):
            for record in batch:
                if dense and record[0]!=count:raise PublicationUnavailable('bpr_source_row_order_differs:'+name)
                row=dict(zip(fields,record))
                if name!='bpr_candidates':planning_source_sql.validate_target_lengths([row],fields)
                yield row
                count+=1


def _receipt(generation,name):
    checksum=hashlib.sha256(b'[');count=0
    for record in _records(generation,name):
        if count:checksum.update(b',')
        for part in canonical_parts(record):checksum.update(part)
        count+=1
    checksum.update(b']')
    return dict(count=count,digest=checksum.hexdigest())


def _identity(generation,recipe,images):
    return dict(schema=SCHEMA,generation_id=str(generation.pk),report_generation_digest=generation.digest,
        phase_id=str(generation.phase_id),phase_digest=generation.metadata['phase_digest'],
        source_digest=generation.source_digest,action_revision=generation.action_revision,
        recipe_digest=recipe,images=images)


@contextmanager
def _owner(generation_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.scope_source_generation',true)")
        previous=cursor.fetchone()[0] or ''
        cursor.execute("SELECT set_config('fresh.scope_source_generation',%s,true)",[str(generation_id)])
    try:yield
    except DatabaseError:
        transaction.set_rollback(True);raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.scope_source_generation',%s,true)",[previous])


@dataclass(frozen=True)
class PreparedBinding:
    projection: object
    reports: object
    sources: object

    @property
    def run_id(self):return self.reports.generation.run_id

    @property
    def read_identity(self):
        # The three prepared bags and five current facts do not consume BTR.
        # Pin the extra dependency in the dependent read contract, so preparing
        # a predecessor's reports cannot invalidate those independent bags.
        from mta.presentation import scoped_inherited_btr
        return dict(schema='fresh-bpr-prepared-read-v1',generation_id=str(self.reports.generation.pk),
            report_digest=self.reports.generation.digest,projection_digest=self.projection.digest,
            source_digest=self.sources.source_digest,inherited_recipe=scoped_inherited_btr.recipe_digest(),
            inherited_btr=None if self.sources.inherited_btr is None else self.sources.inherited_btr.provenance())

    def query(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_prepared_source_unavailable:'+name)
        model,fields,_ordinals,_dense=TABLES[name]
        return ('SELECT G.run_id,'+','.join('R.'+quote(field) for field in fields)+
            ' FROM mta.'+quote(model._meta.db_table)+' R JOIN mta.fresh_mta_scopereportgeneration G '
            'ON G.id=R.generation_id WHERE R.generation_id=%s',[self.reports.generation.pk])

    def rows(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_prepared_source_unavailable:'+name)
        actual=_receipt(self.reports.generation,name)
        if actual!=self.projection.metadata['images'][name]:
            raise PublicationUnavailable('bpr_prepared_source_rows_differ:'+name)
        return storage(list(_records(self.reports.generation,name)))

    def image_query(self,path):return self.sources.query(path)

    def fact_query(self,name):return self.reports.query(name)


def bind(generation_id,*,expected_digest,expected_report_digest,action_revision,include_inherited_btr=False):
    from django.core.exceptions import ObjectDoesNotExist
    reports=facts.bind(generation_id,expected_digest=expected_report_digest,action_revision=action_revision)
    try:projection=models.ScopeSourceProjection.objects.get(generation=reports.generation)
    except ObjectDoesNotExist as error:raise PublicationUnavailable('bpr_source_projection_missing') from error
    verify_guards()
    if (not projection.sealed or projection.sealed_at is None or projection.digest!=expected_digest
            or projection.digest!=digest(projection.metadata) or projection.recipe_digest!=recipe_digest()
            or projection.report_generation_digest!=reports.generation.digest
            or set(projection.metadata.get('images',{}))!=set(TABLES)
            or projection.metadata!=_identity(reports.generation,projection.recipe_digest,projection.metadata['images'])):
        raise PublicationUnavailable('bpr_source_projection_identity_differs')
    sources=scoped_sources.bind(reports.generation.phase_id,
        expected_digest=reports.generation.metadata['phase_digest'],action_revision=action_revision,
        include_inherited_btr=include_inherited_btr)
    return PreparedBinding(projection,reports,sources)


@transaction.atomic
def prepare(generation_id,*,expected_report_digest,action_revision):
    from mta.runtime.models import CalculationRun,ScopeReportGeneration
    generation=ScopeReportGeneration.objects.get(pk=generation_id)
    CalculationRun.objects.select_for_update().get(pk=generation.run_id)
    reports=facts.bind(generation_id,expected_digest=expected_report_digest,action_revision=action_revision)
    verify_guards()
    sources=scoped_sources.bind(generation.phase_id,expected_digest=generation.metadata['phase_digest'],action_revision=action_revision)
    existing=models.ScopeSourceProjection.objects.filter(generation=generation).first()
    if existing is not None:
        bound=bind(generation.pk,expected_digest=existing.digest,
            expected_report_digest=generation.digest,action_revision=action_revision)
        for name in TABLES:
            if _receipt(generation,name)!=bound.projection.metadata['images'][name]:
                raise PublicationUnavailable('bpr_source_projection_repeat_differs:'+name)
        return existing
    projection=models.ScopeSourceProjection(generation=reports.generation,
        report_generation_digest=expected_report_digest,recipe_digest=recipe_digest())
    with _owner(generation.pk):
        projection.save(force_insert=True)
        query,params=_bpr_insert(sources,generation)
        with connection.cursor() as cursor:
            cursor.execute(query,params);inserted={'bpr_candidates':cursor.rowcount}
            for name,query,params in _planning_inserts(sources,generation):
                cursor.execute(query,params);inserted[name]=cursor.rowcount
        images={name:_receipt(generation,name) for name in TABLES}
        if inserted!={name:item['count'] for name,item in images.items()}:
            raise PublicationUnavailable('bpr_prepared_insert_readback_differs')
        projection.metadata=_identity(generation,projection.recipe_digest,images)
        projection.digest=digest(projection.metadata);projection.sealed=True;projection.sealed_at=timezone.now()
        projection.save(update_fields=['metadata','digest','sealed','sealed_at'])
    bind(generation.pk,expected_digest=projection.digest,
        expected_report_digest=generation.digest,action_revision=action_revision)
    return projection
