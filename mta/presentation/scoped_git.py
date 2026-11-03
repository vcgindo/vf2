"""Prepare GIT location occurrences once, without terminal Full ownership."""
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
import inspect
from django.db import connection,transaction,DatabaseError
from django.utils import timezone
from mta.presentation import scoped_prepared,planning_git_preparation
from mta.presentation.context import PublicationUnavailable
from mta.presentation.registered_read_compatibility import compatible_guard_recipe
from mta.runtime import scope_git_models as models
from mta.runtime.relational_state import quote
from mta.serialization import digest,storage,rows_digest

SCHEMA='fresh-bpr-git-generation-v1'
FIELDS=tuple(f.name for f in models.ScopeGitOccurrence._meta.local_fields if f.name not in ('id','generation'))
ORDER=('rationed_ordinal','standard_ordinal','transporter_ordinal','sku_description_ordinal',
    'location_description_ordinal','parent_description_ordinal','sku_ordinal','location_ordinal','pair_ordinal')


def recipe_digest():
    return digest(dict(schema=SCHEMA,builder=inspect.getsource(inspect.getmodule(recipe_digest)),
        handoff=inspect.getsource(import_module('mta.presentation.scoped_preparation')),
        models=inspect.getsource(models),producer=planning_git_preparation.scoped_recipe_digest(),
        dimensions=planning_git_preparation.DIMENSIONS,
        fields=[models.ScopeGitOccurrence._meta.get_field(f).deconstruct() for f in FIELDS]))


def verify_guards():
    from mta.presentation.schema_reuse import action_guard
    if action_guard(__name__):
        return
    frozen=import_module('mta.runtime.migrations.0210_scope_git_guards')
    targets=[frozen.GENERATION,*frozen.TABLES.values()]
    expected=[]
    for table in targets:
        expected.append((table,'scope_git_no_truncate',34,'deny_scope_git_truncate',False,False,False,None,None))
        if table==frozen.GENERATION:
            expected.extend([(table,'scope_git_complete',21,'require_scope_git_complete',True,True,True,None,None),
                (table,'scope_git_generation_guard',31,'guard_scope_git_generation',False,False,False,None,None)])
        else:
            for op,kind,old,new in (('insert',4,None,'new_rows'),('update',16,'old_rows','new_rows'),
                                    ('delete',8,'old_rows',None)):
                expected.append((table,'scope_git_rows_'+op,kind,'guard_scope_git_rows',False,False,False,old,new))
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
            raise PublicationUnavailable('bpr_git_generation_guard_coverage_differs')
        functions=('guard_scope_git_generation','guard_scope_git_rows',
                   'require_scope_git_complete','deny_scope_git_truncate')
        bodies={name:frozen.SQL.split('CREATE FUNCTION mta.'+name+'()',1)[1]
            .split('AS $guard$',1)[1].split('$guard$;',1)[0] for name in functions}
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,"
            "P.prorettype='trigger'::regtype,P.proowner=C.relowner,"
            "NOT EXISTS(SELECT 1 FROM aclexplode(COALESCE(P.proacl,acldefault('f',P.proowner))) A "
            "WHERE A.grantee<>P.proowner) FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C "
            "WHERE C.oid=to_regclass('mta.fresh_mta_scopegitgeneration') "
            "AND N.nspname='mta' AND P.proname=ANY(%s) ORDER BY 1",[list(functions)])
        if cursor.fetchall()!=[(name,body,False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True)
                for name,body in sorted(bodies.items())]:
            raise PublicationUnavailable('bpr_git_generation_guard_body_differs')
        from mta.runtime.ingestion_ownership import require_guard_coverage,scoped_derived_body
        require_guard_coverage(cursor)
        expected_body=scoped_derived_body(cursor,minimum='0210_scope_git_guards')
        cursor.execute("SELECT prosrc,prosecdef,proconfig FROM pg_proc "
            "WHERE oid='mta.ingestion_watch()'::regprocedure")
        if cursor.fetchall()!=[(expected_body,True,['search_path=pg_catalog, mta'])]:
            raise PublicationUnavailable('bpr_git_generation_revision_owner_differs')


@contextmanager
def _owner(identifier):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.scope_git_generation',true)")
        previous=cursor.fetchone()[0] or ''
        cursor.execute("SELECT set_config('fresh.scope_git_generation',%s,true)",[str(identifier)])
    try:yield
    except DatabaseError:
        transaction.set_rollback(True);raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.scope_git_generation',%s,true)",[previous])


def _identity(row,prepared,image):
    reports=prepared.reports.generation
    return dict(schema=SCHEMA,generation_id=str(row.pk),run_id=str(row.run_id),
        phase_id=str(row.phase_id),phase_digest=prepared.sources.acceptance_digest,
        snapshot_digest=prepared.sources.snapshot_digest,input_digest=prepared.sources.run.input_digest,
        input_manifest_digest=prepared.sources.run.input_manifest_digest,action_revision=row.action_revision,
        source_digest=row.source_digest,configuration_digest=row.configuration_digest,recipe_digest=row.recipe_digest,
        occurrences=dict(schema='fresh-bpr-git-occurrences-v1',report_generation_id=str(reports.pk),
            report_generation_digest=reports.digest,source_projection_digest=prepared.projection.digest,
            transit_generation_id=str(prepared.transit.generation.pk),
            transit_generation_digest=prepared.transit.generation.digest,image=image))


def _records(identifier):
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT '+','.join(map(quote,FIELDS))+' FROM mta.fresh_mta_scopegitoccurrence '
            'WHERE generation_id=%s ORDER BY ordinal',[identifier])
        n=0
        while batch:=cursor.fetchmany(500):
            for record in batch:
                row=dict(zip(FIELDS,record))
                if row['ordinal']!=n:raise PublicationUnavailable('bpr_git_occurrence_order_differs')
                yield storage(row);n+=1


def _receipt(identifier):
    count=0
    def rows():
        nonlocal count
        for row in _records(identifier):
            count+=1;yield row
    checksum=rows_digest(rows())
    return dict(count=count,digest=checksum)


@dataclass(frozen=True)
class GitBinding:
    generation: object
    prepared: object

    @property
    def run_id(self):return self.generation.run_id

    @property
    def read_identity(self):
        return dict(schema=SCHEMA,generation_id=str(self.generation.pk),digest=self.generation.digest,
                    prepared=self.prepared.read_identity)

    def query(self):
        return ('SELECT G.run_id,'+','.join('R.'+quote(f) for f in FIELDS)+
            ' FROM mta.fresh_mta_scopegitoccurrence R JOIN mta.fresh_mta_scopegitgeneration G '
            'ON G.id=R.generation_id WHERE R.generation_id=%s',[self.generation.pk])

    def verify_rows(self):
        if _receipt(self.generation.pk)!=self.generation.metadata['occurrences']['image']:
            raise PublicationUnavailable('bpr_git_occurrence_digest_differs')

    def rows(self):
        self.verify_rows()
        return list(_records(self.generation.pk))

    def image_query(self,path):return self.prepared.image_query(path)

    def attributes(self):
        return {name:self.prepared.sources.rows('closing/importer/'+name)
            for name in ('SkuAttributeData','LocationAttributeData')}


def require_binding(run,bound):
    if not isinstance(bound,GitBinding) or bound.run_id!=run.pk:
        raise PublicationUnavailable('bpr_git_phase_owner_differs')
    return bound


def bind(generation_id,*,expected_digest,action_revision):
    from django.core.exceptions import ObjectDoesNotExist
    try:row=models.ScopeGitGeneration.objects.get(pk=generation_id)
    except ObjectDoesNotExist as error:raise PublicationUnavailable('bpr_git_generation_missing') from error
    prepared=scoped_prepared.bind(row.report_generation_id,expected_digest=row.source_projection_digest,
        expected_report_digest=row.report_generation_digest,action_revision=action_revision,
        transit_generation_id=row.transit_generation_id,expected_transit_digest=row.transit_generation_digest)
    verify_guards()
    return _binding(row,prepared,expected_digest=expected_digest,action_revision=action_revision)


def _binding(row,prepared,*,expected_digest,action_revision):
    reports=prepared.reports.generation
    if (not row.sealed or row.sealed_at is None or row.digest!=expected_digest or row.digest!=digest(row.metadata)
            or not compatible_guard_recipe('scoped_git',row.recipe_digest,recipe_digest()) or row.action_revision!=action_revision
            or row.run_id!=prepared.run_id or row.phase_id!=reports.phase_id
            or row.source_digest!=reports.source_digest or row.configuration_digest!=reports.configuration_digest
            or row.metadata!=_identity(row,prepared,row.metadata.get('occurrences',{}).get('image'))):
        raise PublicationUnavailable('bpr_git_generation_identity_differs')
    return GitBinding(row,prepared)


@transaction.atomic
def prepare(report_generation_id,*,expected_report_digest,expected_source_digest,
            transit_generation_id,expected_transit_digest,action_revision):
    from mta.runtime.models import CalculationRun,ScopeReportGeneration
    reports=ScopeReportGeneration.objects.get(pk=report_generation_id)
    CalculationRun.objects.select_for_update().get(pk=reports.run_id)
    prepared=scoped_prepared.bind(report_generation_id,expected_digest=expected_source_digest,
        expected_report_digest=expected_report_digest,action_revision=action_revision,
        transit_generation_id=transit_generation_id,expected_transit_digest=expected_transit_digest)
    bound=_prepare(prepared)
    bind(bound.generation.pk,expected_digest=bound.generation.digest,action_revision=action_revision).verify_rows()
    return bound.generation


def _prepare(prepared)->GitBinding:
    from mta.presentation.scoped_preparation import require_prepared,require_transit
    require_prepared(prepared);require_transit(prepared)
    reports=prepared.reports.generation
    expected_report_digest=reports.digest;expected_source_digest=prepared.projection.digest
    transit_generation_id=prepared.transit.generation.pk;expected_transit_digest=prepared.transit.generation.digest
    action_revision=reports.action_revision
    verify_guards();recipe=recipe_digest()
    existing=models.ScopeGitGeneration.objects.filter(report_generation=reports,
        transit_generation_id=transit_generation_id,recipe_digest=recipe).first()
    if existing is not None:
        bound=bind(existing.pk,expected_digest=existing.digest,action_revision=action_revision)
        bound.verify_rows();return bound
    row=models.ScopeGitGeneration(run_id=reports.run_id,phase_id=reports.phase_id,
        action_revision=action_revision,source_digest=reports.source_digest,
        configuration_digest=reports.configuration_digest,recipe_digest=recipe,
        report_generation=reports,report_generation_digest=expected_report_digest,
        source_projection_digest=expected_source_digest,transit_generation_id=transit_generation_id,
        transit_generation_digest=expected_transit_digest)
    with _owner(row.pk):
        row.save(force_insert=True)
        query,params=planning_git_preparation.scoped_git_occurrences(prepared.sources.run,read_binding=prepared)
        selected=[f for f in FIELDS if f!='ordinal']
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO mta.fresh_mta_scopegitoccurrence (generation_id,ordinal,'+
                ','.join(map(quote,selected))+') SELECT %s,row_number() OVER (ORDER BY '+
                ','.join(quote(f)+' NULLS FIRST' for f in ORDER)+')-1,'+','.join(map(quote,selected))+
                ' FROM ('+query+') occurrences',[row.pk,*params])
        image=_receipt(row.pk)
        row.metadata=_identity(row,prepared,image);row.digest=digest(row.metadata)
        row.sealed=True;row.sealed_at=timezone.now()
        row.save(update_fields=['metadata','digest','sealed','sealed_at'])
    bound=_binding(row,prepared,expected_digest=row.digest,action_revision=action_revision)
    bound.verify_rows()
    return bound

