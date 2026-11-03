"""Immutable raw Pick and RRR references for one accepted BPR generation."""
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
import inspect
from django.db import connection,transaction,DatabaseError
from django.utils import timezone
from mta.presentation import scoped_sources,scoped_pick_queries as queries
from mta.presentation.context import PublicationUnavailable
from mta.presentation.registered_read_compatibility import compatible_guard_recipe
from mta.runtime import scope_pick_models as models
from mta.runtime.relational_state import quote
from mta.serialization import digest,storage,rows_digest

SCHEMA='fresh-bpr-pick-generation-v1'
TABLES={'raw':models.ScopePickReference,'rrr':models.ScopeRrrReference}
ORDER=('band_ordinal','rationed_ordinal','standard_ordinal','pair_ordinal','sku_ordinal','location_ordinal','left_pair_ordinal')


def fields(name):
    return tuple(f.name for f in TABLES[name]._meta.local_fields if f.name not in ('id','generation'))


def recipe_digest():
    from mta.runtime.models import BprNumericField
    return digest(dict(schema=SCHEMA,builder=inspect.getsource(inspect.getmodule(recipe_digest)),
        handoff=inspect.getsource(import_module('mta.presentation.scoped_preparation')),
        source_queries=queries.recipe_digest(),models=inspect.getsource(models),numeric=inspect.getsource(BprNumericField),
        fields={name:[model._meta.get_field(f).deconstruct() for f in fields(name)] for name,model in TABLES.items()}))


def verify_guards():
    from mta.presentation.schema_reuse import action_guard
    if action_guard(__name__):
        return
    frozen=import_module('mta.runtime.migrations.0212_scope_pick_guards')
    targets=[frozen.GENERATION,*frozen.TABLES.values()]
    expected=[]
    for table in targets:
        expected.append((table,'scope_pick_view_no_truncate',34,'deny_scope_pick_view_truncate',False,False,False,None,None))
        if table==frozen.GENERATION:
            expected.extend([(table,'scope_pick_view_complete',21,'require_scope_pick_view_complete',True,True,True,None,None),
                (table,'scope_pick_view_generation_guard',31,'guard_scope_pick_view_generation',False,False,False,None,None)])
        else:
            for op,kind,old,new in (('insert',4,None,'new_rows'),('update',16,'old_rows','new_rows'),
                                    ('delete',8,'old_rows',None)):
                expected.append((table,'scope_pick_view_rows_'+op,kind,'guard_scope_pick_view_rows',False,False,False,old,new))
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
            raise PublicationUnavailable('bpr_pick_view_generation_guard_coverage_differs')
        functions=('guard_scope_pick_view_generation','guard_scope_pick_view_rows',
                   'require_scope_pick_view_complete','deny_scope_pick_view_truncate')
        bodies={name:frozen.SQL.split('CREATE FUNCTION mta.'+name+'()',1)[1]
            .split('AS $guard$',1)[1].split('$guard$;',1)[0] for name in functions}
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,"
            "P.prorettype='trigger'::regtype,P.proowner=C.relowner,"
            "NOT EXISTS(SELECT 1 FROM aclexplode(COALESCE(P.proacl,acldefault('f',P.proowner))) A "
            "WHERE A.grantee<>P.proowner) FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C "
            "WHERE C.oid=to_regclass('mta.fresh_mta_scopepickgeneration') "
            "AND N.nspname='mta' AND P.proname=ANY(%s) ORDER BY 1",[list(functions)])
        if cursor.fetchall()!=[(name,body,False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True)
                for name,body in sorted(bodies.items())]:
            raise PublicationUnavailable('bpr_pick_view_generation_guard_body_differs')
        from mta.runtime.ingestion_ownership import require_guard_coverage,scoped_derived_body
        require_guard_coverage(cursor)
        expected_body=scoped_derived_body(cursor,minimum='0212_scope_pick_guards')
        cursor.execute("SELECT prosrc,prosecdef,proconfig FROM pg_proc "
            "WHERE oid='mta.ingestion_watch()'::regprocedure")
        if cursor.fetchall()!=[(expected_body,True,['search_path=pg_catalog, mta'])]:
            raise PublicationUnavailable('bpr_pick_view_generation_revision_owner_differs')


@contextmanager
def _owner(identifier):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.scope_pick_view_generation',true)")
        previous=cursor.fetchone()[0] or ''
        cursor.execute("SELECT set_config('fresh.scope_pick_view_generation',%s,true)",[str(identifier)])
    try:yield
    except DatabaseError:
        transaction.set_rollback(True);raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.scope_pick_view_generation',%s,true)",[previous])


def _inputs(sources):
    return dict(schema='fresh-bpr-pick-query-sources-v1',recipe_digest=queries.recipe_digest(),
        run_id=str(sources.run.pk),source_digest=sources.source_digest,action_revision=sources.action_revision,
        images={path:sources.provenance(path) for path in (queries.PATH,*(p for _a,p in queries.rrr_preparation.SOURCES))})


def _identity(row,sources,pick):
    return dict(schema=SCHEMA,generation_id=str(row.pk),run_id=str(row.run_id),phase_id=str(row.phase_id),
        phase_digest=sources.acceptance_digest,snapshot_digest=sources.snapshot_digest,
        input_digest=sources.run.input_digest,input_manifest_digest=sources.run.input_manifest_digest,
        action_revision=row.action_revision,source_digest=row.source_digest,configuration_digest=row.configuration_digest,
        recipe_digest=row.recipe_digest,pick=pick)


def _records(identifier,name):
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT '+','.join(map(quote,fields(name)))+' FROM mta.'+
            quote(TABLES[name]._meta.db_table)+' WHERE generation_id=%s ORDER BY ordinal',[identifier])
        count=0
        while batch:=cursor.fetchmany(500):
            for values in batch:
                row=dict(zip(fields(name),values))
                if row['ordinal']!=count:raise PublicationUnavailable('bpr_pick_view_reference_order_differs:'+name)
                yield storage(row);count+=1


def _receipt(identifier,name):
    count=0
    def rows():
        nonlocal count
        for row in _records(identifier,name):
            count+=1;yield row
    checksum=rows_digest(rows())
    return dict(count=count,digest=checksum)


@dataclass(frozen=True)
class PickBinding:
    generation: object
    sources: object

    @property
    def run_id(self):return self.generation.run_id

    def query(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_pick_view_source_unavailable:'+name)
        return ('SELECT G.run_id,'+','.join('R.'+quote(f) for f in fields(name))+' FROM mta.'+
            quote(TABLES[name]._meta.db_table)+' R JOIN mta.fresh_mta_scopepickgeneration G ON G.id=R.generation_id '
            'WHERE R.generation_id=%s',[self.generation.pk])

    def rows(self,name):
        self.verify_rows(name)
        return list(_records(self.generation.pk,name))

    def verify_rows(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_pick_view_source_unavailable:'+name)
        if _receipt(self.generation.pk,name)!=self.generation.metadata['pick']['images'][name]:
            raise PublicationUnavailable('bpr_pick_view_reference_digest_differs:'+name)

    def pick_query(self):
        bands,_columns=queries.band_queries(self.sources)
        return queries.pick_query(self.sources.query(queries.RATIONED),self.query('raw'),bands)

    def image_query(self,path):return self.sources.query(path)

    def provenance(self):
        return dict(schema=SCHEMA,generation_id=str(self.generation.pk),digest=self.generation.digest,
            run_id=str(self.run_id),phase_id=str(self.generation.phase_id),source_digest=self.generation.source_digest,
            configuration_digest=self.generation.configuration_digest,action_revision=self.generation.action_revision,
            recipe_digest=self.generation.recipe_digest)


def bind(generation_id,*,expected_digest,action_revision):
    from django.core.exceptions import ObjectDoesNotExist
    try:row=models.ScopePickGeneration.objects.select_related('phase__snapshot').get(pk=generation_id)
    except ObjectDoesNotExist as error:raise PublicationUnavailable('bpr_pick_view_generation_missing') from error
    sources=scoped_sources.bind(row.phase_id,expected_digest=row.metadata.get('phase_digest'),action_revision=action_revision)
    verify_guards()
    return _binding(row,sources,expected_digest=expected_digest,action_revision=action_revision)


def _binding(row,sources,*,expected_digest,action_revision):
    pick=row.metadata.get('pick',{})
    if (not row.sealed or row.sealed_at is None or row.digest!=expected_digest or row.digest!=digest(row.metadata)
            or row.run_id!=sources.run.pk or row.action_revision!=action_revision
            or row.source_digest!=sources.source_digest or not compatible_guard_recipe('scoped_pick_storage',row.recipe_digest,recipe_digest())
            or row.configuration_digest!=row.phase.snapshot.manifest['references']['profile']
            or set(pick)!= {'schema','inputs','images'} or pick.get('schema')!='fresh-bpr-pick-references-v1'
            or pick.get('inputs')!=_inputs(sources) or set(pick.get('images',{}))!=set(TABLES)
            or row.metadata!=_identity(row,sources,pick)):
        raise PublicationUnavailable('bpr_pick_view_generation_identity_differs')
    return PickBinding(row,sources)


@transaction.atomic
def prepare(phase_id,*,expected_digest,action_revision):
    from mta.runtime.models import CalculationRun,RunPhaseAcceptance
    phase=RunPhaseAcceptance.objects.select_related('snapshot').get(pk=phase_id)
    CalculationRun.objects.select_for_update().get(pk=phase.run_id)
    verify_guards()
    sources=scoped_sources.bind(phase_id,expected_digest=expected_digest,action_revision=action_revision)
    bound=_prepare(phase,sources)
    bind(bound.generation.pk,expected_digest=bound.generation.digest,action_revision=action_revision)
    for name in TABLES:bound.verify_rows(name)
    return bound.generation


def _prepare(phase,sources)->PickBinding:
    from mta.presentation.scoped_preparation import require_sources
    require_sources(phase,sources)
    verify_guards()
    phase_id=phase.pk;expected_digest=sources.acceptance_digest;action_revision=sources.action_revision
    recipe=recipe_digest()
    existing=models.ScopePickGeneration.objects.filter(phase=phase,source_digest=sources.source_digest,
        action_revision=action_revision,recipe_digest=recipe).first()
    if existing is not None:
        bound=bind(existing.pk,expected_digest=existing.digest,action_revision=action_revision)
        for name in TABLES:bound.verify_rows(name)
        return bound
    context=queries.bind_sources(sources)
    row=models.ScopePickGeneration(run=sources.run,phase=phase,action_revision=action_revision,
        source_digest=sources.source_digest,configuration_digest=phase.snapshot.manifest['references']['profile'],recipe_digest=recipe)
    with _owner(row.pk):
        row.save(force_insert=True)
        for name,(query,params) in (('raw',context.raw_membership_query()),('rrr',context.rrr_membership_query())):
            selected=fields(name)
            if name=='raw':projection=','.join(map(quote,selected))
            else:
                projection=('row_number() OVER (ORDER BY '+','.join(quote(f)+' NULLS FIRST' for f in ORDER)+')-1,'+
                    ','.join(quote(f) for f in selected if f!='ordinal'))
            with connection.cursor() as cursor:
                cursor.execute('INSERT INTO mta.'+quote(TABLES[name]._meta.db_table)+' (generation_id,'+
                    ','.join(map(quote,selected))+') SELECT %s,'+projection+' FROM ('+query+') prepared',[row.pk,*params])
        pick=dict(schema='fresh-bpr-pick-references-v1',inputs=context.provenance(),
            images={name:_receipt(row.pk,name) for name in TABLES})
        row.metadata=_identity(row,sources,pick);row.digest=digest(row.metadata)
        row.sealed=True;row.sealed_at=timezone.now()
        row.save(update_fields=['metadata','digest','sealed','sealed_at'])
    bound=_binding(row,sources,expected_digest=row.digest,action_revision=action_revision)
    for name in TABLES:bound.verify_rows(name)
    return bound
