"""Immutable parent ingredients; remark appends never rebuild core occurrences."""
from contextlib import contextmanager
from dataclasses import dataclass,replace
from importlib import import_module
import inspect
from django.db import connection,transaction,DatabaseError
from django.utils import timezone
from mta.presentation import scoped_expedite_storage as core,scoped_remarks,scoped_expedite_pick_queries as queries
from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr_sql import equal
from mta.runtime import scope_expedite_parent_models as models
from mta.runtime.relational_state import quote
from mta.serialization import digest,storage,rows_digest
from mta.presentation.request_scope import validated_read,validation_reads
from mta.presentation import expedite_transit_join

SCHEMA='fresh-bpr-expedite-parent-generation-v1'
TABLES={'base':models.ScopeExpediteParentBase,'match':models.ScopeExpediteParentMatch}
RETAINED_RECIPE='93e9b676d014cdd6c05b66346e0d8b963b7d718a7aef1be6f44778cf7f7693a3'


def fields(name):
    return tuple(f.name for f in TABLES[name]._meta.local_fields if f.name not in ('id','generation'))


def recipe_digest():
    return digest(dict(schema=SCHEMA,builder=inspect.getsource(inspect.getmodule(recipe_digest)),
        models=inspect.getsource(models),base=inspect.getsource(queries.ExpeditePickQueries.parent_base_query),
        join=expedite_transit_join.recipe_digest(),
        fields={n:[m._meta.get_field(f).deconstruct() for f in fields(n)] for n,m in TABLES.items()}))


def verify_guards():
    frozen=import_module('mta.runtime.migrations.0216_scope_expedite_parent_guards')
    targets=[frozen.GENERATION,*frozen.TABLES.values()]
    expected=[]
    for table in targets:
        expected.append((table,'scope_expedite_parent_no_truncate',34,'deny_scope_expedite_parent_truncate',False,False,False,None,None))
        if table==frozen.GENERATION:
            expected.extend([(table,'scope_expedite_parent_complete',21,'require_scope_expedite_parent_complete',True,True,True,None,None),
                (table,'scope_expedite_parent_generation_guard',31,'guard_scope_expedite_parent_generation',False,False,False,None,None)])
        else:
            for op,kind,old,new in (('insert',4,None,'new_rows'),('update',16,'old_rows','new_rows'),
                                    ('delete',8,'old_rows',None)):
                expected.append((table,'scope_expedite_parent_rows_'+op,kind,'guard_scope_expedite_parent_rows',False,False,False,old,new))
    with connection.cursor() as cursor:
        cursor.execute("SELECT C.relname,T.tgname,T.tgtype,P.proname,T.tgdeferrable,T.tginitdeferred,"
            "T.tgconstraint<>0,T.tgoldtable,T.tgnewtable,T.tgenabled,N.nspname,T.tgnargs,T.tgqual::text,T.tgattr::text "
            "FROM pg_trigger T JOIN pg_class C ON C.oid=T.tgrelid "
            "JOIN pg_namespace CN ON CN.oid=C.relnamespace JOIN pg_proc P ON P.oid=T.tgfoid "
            "JOIN pg_namespace N ON N.oid=P.pronamespace "
            "WHERE CN.nspname='mta' AND C.relname=ANY(%s) AND NOT T.tgisinternal "
            "AND T.tgname NOT LIKE 'ingestion_watch_%%' ORDER BY 1,2",[targets])
        from mta.runtime.scoped_remark_ownership import verified_business_rows
        rows=verified_business_rows(cursor,cursor.fetchall(),name_index=1)
        from mta.runtime import scoped_action_ownership
        rows=scoped_action_ownership.verified_business_rows(cursor,rows)
        if rows!=[(*row,'O','mta',0,None,'') for row in sorted(expected)]:
            raise PublicationUnavailable('bpr_expedite_parent_generation_guard_coverage_differs')
        functions=('guard_scope_expedite_parent_generation','guard_scope_expedite_parent_rows',
                   'require_scope_expedite_parent_complete','deny_scope_expedite_parent_truncate')
        bodies={name:frozen.SQL.split('CREATE FUNCTION mta.'+name+'()',1)[1]
            .split('AS $guard$',1)[1].split('$guard$;',1)[0] for name in functions}
        from mta.runtime.scoped_action_ownership import migration as action_migration
        current=action_migration(cursor)
        if hasattr(current,'PARENT_GENERATION'):
            bodies['guard_scope_expedite_parent_generation']=current.PARENT_GENERATION
            bodies['guard_scope_expedite_parent_rows']=current.PARENT_ROWS
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,"
            "P.prorettype='trigger'::regtype,P.proowner=C.relowner,"
            "NOT EXISTS(SELECT 1 FROM aclexplode(COALESCE(P.proacl,acldefault('f',P.proowner))) A "
            "WHERE A.grantee<>P.proowner) FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C "
            "WHERE C.oid=to_regclass('mta.fresh_mta_scopeexpediteparentgeneration') "
            "AND N.nspname='mta' AND P.proname=ANY(%s) ORDER BY 1",[list(functions)])
        if cursor.fetchall()!=[(name,body,False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True)
                for name,body in sorted(bodies.items())]:
            raise PublicationUnavailable('bpr_expedite_parent_generation_guard_body_differs')
        from mta.runtime.ingestion_ownership import require_guard_coverage,scoped_derived_body
        require_guard_coverage(cursor)
        expected_body=scoped_derived_body(cursor,minimum='0216_scope_expedite_parent_guards')
        cursor.execute("SELECT prosrc,prosecdef,proconfig FROM pg_proc "
            "WHERE oid='mta.ingestion_watch()'::regprocedure")
        if cursor.fetchall()!=[(expected_body,True,['search_path=pg_catalog, mta'])]:
            raise PublicationUnavailable('bpr_expedite_parent_generation_revision_owner_differs')

@contextmanager
def _owner(identifier):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.scope_expedite_parent_generation',true)")
        previous=cursor.fetchone()[0] or ''
        cursor.execute("SELECT set_config('fresh.scope_expedite_parent_generation',%s,true)",[str(identifier)])
    try:yield
    except DatabaseError:
        transaction.set_rollback(True);raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.scope_expedite_parent_generation',%s,true)",[previous])


def _match_query(bound,remarks,identifier):
    grids,gp=bound.query('grid');rq,rp=remarks.query();pick,pp=bound.pick_query()
    facts,fp=bound.fact_query('ExpediteDispatches')
    return ('WITH G AS ('+grids+'),R AS ('+rq+'),P AS ('+pick+'),A AS ('+facts+'),candidates AS (SELECT '
        'B.ordinal AS base_ordinal,G.branch,G.ordinal AS grid_ordinal,'
        'P.vf_source_ordinal AS pick_ordinal,P."ParentStockForRationing" AS parent_stock '
        'FROM mta.fresh_mta_scopeexpediteparentbase B JOIN R ON R.vf_ordinal=B.remark_ordinal '
        'JOIN A ON '+equal('A."SKUCode"','R."SKUCode"')+' AND '+equal('A."WhCode"','R."WhCode"')+
        " JOIN G ON G.direction='parent' AND G.run_id=A.run_id AND G.fact_ordinal=A.ordinal "
        'LEFT JOIN P ON '+equal('P."SKUCode"','A."SKUCode"')+' AND '+equal('P."WhCode"','A."WhCode"')+
        ' WHERE B.generation_id=%s) SELECT '
        'row_number() OVER (ORDER BY base_ordinal,branch,grid_ordinal,pick_ordinal NULLS FIRST)-1 AS ordinal,'
        'base_ordinal,branch,grid_ordinal,pick_ordinal,parent_stock FROM candidates'),[*gp,*rp,*pp,*fp,identifier]


def _inserts(bound,remarks,identifier):
    prepared=replace(bound.prepared,remarks=remarks)
    context=queries.bind(prepared.sources.run,read_binding=prepared,pick_binding=bound.pick)
    for name in TABLES:
        query,params=context.parent_base_query() if name=='base' else _match_query(bound,remarks,identifier)
        columns=','.join(map(quote,fields(name)))
        yield name,('INSERT INTO mta.'+quote(TABLES[name]._meta.db_table)+' (generation_id,'+columns+
            ') SELECT %s,'+columns+' FROM ('+query+') occurrences'),[identifier,*params]


def _prepared_match(bound,remarks,identifier):
    return expedite_transit_join.prepared_match(
        base=('SELECT ordinal,remark_ordinal FROM mta.fresh_mta_scopeexpediteparentbase WHERE generation_id=%s',[identifier]),
        remarks=remarks.query(),facts=bound.fact_query('ExpediteDispatches'),
        grids=bound.query('grid'),pick=bound.pick_query())


def _records(identifier,name):
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT '+','.join(map(quote,fields(name)))+' FROM mta.'+quote(TABLES[name]._meta.db_table)+
            ' WHERE generation_id=%s ORDER BY ordinal',[identifier])
        ordinal=0
        while batch:=cursor.fetchmany(500):
            for values in batch:
                row=dict(zip(fields(name),values))
                if row['ordinal']!=ordinal:raise PublicationUnavailable('bpr_expedite_parent_order_differs:'+name)
                ordinal+=1;yield storage(row)


def _receipt(identifier,name):
    count=0
    def rows():
        nonlocal count
        for row in _records(identifier,name):count+=1;yield row
    checksum=rows_digest(rows())
    return dict(count=count,digest=checksum)


def _remark_fields(remarks):
    locator=remarks.provenance()
    return dict(remark_capture_id=remarks.capture_id,remark_watermark=remarks.watermark,remark_highwater=remarks.highwater,
        remark_cutoff=remarks.cutoff,remark_row_count=remarks.row_count,remark_rows_digest=remarks.rows_digest,
        remark_provenance_digest=locator['provenance_digest'],remark_digest=digest(locator))


def _identity(row,bound,remarks,images):
    sources=bound.prepared.sources
    bag=dict(schema='fresh-bpr-expedite-parent-occurrences-v1',core_generation_id=str(bound.generation.pk),
        core_generation_digest=bound.generation.digest,remarks=remarks.provenance(),remark_digest=digest(remarks.provenance()),images=images)
    return dict(schema=SCHEMA,generation_id=str(row.pk),run_id=str(row.run_id),phase_id=str(row.phase_id),
        phase_digest=sources.acceptance_digest,snapshot_digest=sources.snapshot_digest,input_digest=sources.run.input_digest,
        input_manifest_digest=sources.run.input_manifest_digest,action_revision=row.action_revision,source_digest=row.source_digest,
        configuration_digest=row.configuration_digest,recipe_digest=row.recipe_digest,occurrences=bag)


@dataclass(frozen=True)
class ParentBinding:
    generation: object
    core: object
    remarks: object

    @property
    def run_id(self):return self.generation.run_id

    @property
    def read_identity(self):
        return dict(schema=SCHEMA,generation_id=str(self.generation.pk),digest=self.generation.digest,
            core=self.core.read_identity,remarks=self.remarks.provenance())

    def query(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_expedite_parent_source_unavailable:'+name)
        return ('SELECT G.run_id,'+','.join('R.'+quote(f) for f in fields(name))+' FROM mta.'+
            quote(TABLES[name]._meta.db_table)+' R JOIN mta.fresh_mta_scopeexpediteparentgeneration G ON G.id=R.generation_id '
            'WHERE R.generation_id=%s',[self.generation.pk])

    def verify_rows(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_expedite_parent_source_unavailable:'+name)
        if _receipt(self.generation.pk,name)!=self.generation.metadata['occurrences']['images'][name]:
            raise PublicationUnavailable('bpr_expedite_parent_occurrence_digest_differs:'+name)

    def rows(self,name):
        self.verify_rows(name)
        return list(_records(self.generation.pk,name))


def _admit(row,bound,remarks,expected_digest,action_revision):
    verify_guards();generation=bound.generation
    if (not row.sealed or row.sealed_at is None or row.digest!=expected_digest or row.digest!=digest(row.metadata)
            or row.recipe_digest not in (recipe_digest(),RETAINED_RECIPE) or row.action_revision!=action_revision
            or row.run_id!=generation.run_id or row.phase_id!=generation.phase_id
            or row.source_digest!=generation.source_digest or row.configuration_digest!=generation.configuration_digest
            or row.core_generation_id!=generation.pk or row.core_generation_digest!=generation.digest
            or any(getattr(row,k)!=v for k,v in _remark_fields(remarks).items())
            or set(row.metadata.get('occurrences',{}).get('images',{}))!=set(TABLES)
            or row.metadata!=_identity(row,bound,remarks,row.metadata['occurrences']['images'])):
        raise PublicationUnavailable('bpr_expedite_parent_generation_identity_differs')
    return ParentBinding(row,bound,remarks)


@validated_read
def bind(generation_id,*,expected_digest,action_revision):
    from django.core.exceptions import ObjectDoesNotExist
    try:row=models.ScopeExpediteParentGeneration.objects.get(pk=generation_id)
    except ObjectDoesNotExist as error:raise PublicationUnavailable('bpr_expedite_parent_generation_missing') from error
    bound=core.bind(row.core_generation_id,expected_digest=row.core_generation_digest,action_revision=action_revision)
    remarks=scoped_remarks.bind(bound.prepared.sources,configuration_digest=row.configuration_digest)
    return _admit(row,bound,remarks,expected_digest,action_revision)


def require_binding(run,bound):
    if not isinstance(bound,ParentBinding) or bound.run_id!=run.pk:
        raise PublicationUnavailable('bpr_expedite_parent_phase_owner_differs')
    return bound


@transaction.atomic
def prepare(core_generation_id,*,expected_core_digest,action_revision):
    from mta.runtime.models import CalculationRun,ScopeExpediteGeneration
    generation=ScopeExpediteGeneration.objects.get(pk=core_generation_id)
    CalculationRun.objects.select_for_update().get(pk=generation.run_id)
    with validation_reads():
        bound=core.bind(generation.pk,expected_digest=expected_core_digest,action_revision=action_revision)
        remarks=scoped_remarks.bind(bound.prepared.sources,configuration_digest=generation.configuration_digest)
    return _prepare(bound,remarks,expected_core_digest=expected_core_digest,action_revision=action_revision).generation


def _prepare(bound,remarks,*,expected_core_digest,action_revision):
    # The public ID entry validates these handles itself. The remark command
    # supplies only its own freshly selected graph while retaining its locks.
    if (not connection.in_atomic_block or not isinstance(bound,core.ExpediteBinding)
            or not isinstance(remarks,scoped_remarks.RemarkBinding)
            or remarks.run.pk!=bound.run_id or bound.generation.digest!=expected_core_digest
            or bound.generation.action_revision!=action_revision):
        raise PublicationUnavailable('bpr_expedite_parent_prepared_owner_differs')
    generation=bound.generation
    verify_guards();recipe=recipe_digest();remark_fields=_remark_fields(remarks)
    for compatible_recipe in (recipe,RETAINED_RECIPE):
        existing=models.ScopeExpediteParentGeneration.objects.filter(core_generation=generation,
            remark_digest=remark_fields['remark_digest'],recipe_digest=compatible_recipe).first()
        if existing is not None:
            admitted=_admit(existing,bound,remarks,existing.digest,action_revision)
            for name in TABLES:admitted.verify_rows(name)
            return admitted
    row=models.ScopeExpediteParentGeneration(run_id=generation.run_id,phase_id=generation.phase_id,
        action_revision=action_revision,source_digest=generation.source_digest,configuration_digest=generation.configuration_digest,
        recipe_digest=recipe,core_generation=generation,core_generation_digest=expected_core_digest,**remark_fields)
    with _owner(row.pk):
        row.save(force_insert=True)
        for name,sql,params in _inserts(bound,remarks,row.pk):
            if name=='match':
                with _prepared_match(bound,remarks,row.pk) as (query,values):
                    columns=','.join(map(quote,fields(name)))
                    with connection.cursor() as cursor:
                        cursor.execute('INSERT INTO mta.'+quote(TABLES[name]._meta.db_table)+
                            ' (generation_id,'+columns+') SELECT %s,'+columns+' FROM ('+query+') occurrences',
                            [row.pk,*values])
            else:
                with connection.cursor() as cursor:cursor.execute(sql,params)
        images={name:_receipt(row.pk,name) for name in TABLES}
        row.metadata=_identity(row,bound,remarks,images);row.digest=digest(row.metadata)
        row.sealed=True;row.sealed_at=timezone.now()
        row.save(update_fields=['metadata','digest','sealed','sealed_at'])
    admitted=_admit(row,bound,remarks,row.digest,action_revision)
    for name in TABLES:admitted.verify_rows(name)
    return admitted
