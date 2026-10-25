"""Immutable phase-owned transit, with no terminal Full or serving selection.

Build once inside the owning transaction. A bound relation retains its exact
generation for an in-flight reader; fresh admission checks the action revision.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
import inspect

from django.db import connection,transaction,DatabaseError
from django.utils import timezone
from mta.presentation.context import PublicationUnavailable
from mta.presentation import scoped_sources,scoped_transit
from mta.application import daily_transit as processor
from mta.runtime import scope_transit_models as models
from mta.runtime.sql_datetime import SqlDateTimeField
from mta.runtime.relational_state import quote
from mta.serialization import digest,storage,rows_digest

SCHEMA='fresh-bpr-transit-generation-v1'
TABLES={
    'InTransitData':(models.ScopeTransitRow,processor.TRANSIT_FIELDS),
    'GoodsInTransitTransporterMaster':(models.ScopeTransporterRow,processor.TRANSPORTER_FIELDS),
    'TransitRejectedMaster':(models.ScopeTransitDiagnostic,
        ('SKUCode','WhCode','RejectionDate','ReasonCode','ReasonDescription')),
}
PATHS=dict(zip(('sources/bpr/InTransitData','sources/planning/GoodsInTransitTransporterMaster',
    'sources/importer/TransitRejectedMaster'),TABLES))



def recipe_digest():
    return digest(dict(schema=SCHEMA,builder=inspect.getsource(inspect.getmodule(recipe_digest)),
        producers=scoped_transit.recipe_digest(),models=inspect.getsource(models),
        sql_datetime=inspect.getsource(SqlDateTimeField)))


def verify_guards():
    frozen=import_module('mta.runtime.migrations.0207_scope_transit_guards')
    targets=[frozen.GENERATION,*frozen.TABLES.values()]
    expected=[]
    for table in targets:
        expected.append((table,'scope_transit_no_truncate',34,'deny_scope_transit_truncate',False,False,False,None,None))
        if table==frozen.GENERATION:
            expected.extend([(table,'scope_transit_complete',21,'require_scope_transit_complete',True,True,True,None,None),
                (table,'scope_transit_generation_guard',31,'guard_scope_transit_generation',False,False,False,None,None)])
        else:
            for op,kind,old,new in (('insert',4,None,'new_rows'),('update',16,'old_rows','new_rows'),
                                    ('delete',8,'old_rows',None)):
                expected.append((table,'scope_transit_rows_'+op,kind,'guard_scope_transit_rows',False,False,False,old,new))
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
            raise PublicationUnavailable('bpr_transit_generation_guard_coverage_differs')
        functions=('guard_scope_transit_generation','guard_scope_transit_rows',
                   'require_scope_transit_complete','deny_scope_transit_truncate')
        bodies={name:frozen.SQL.split('CREATE FUNCTION mta.'+name+'()',1)[1]
            .split('AS $guard$',1)[1].split('$guard$;',1)[0] for name in functions}
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,"
            "P.prorettype='trigger'::regtype,P.proowner=C.relowner,"
            "NOT EXISTS(SELECT 1 FROM aclexplode(COALESCE(P.proacl,acldefault('f',P.proowner))) A "
            "WHERE A.grantee<>P.proowner) FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C "
            "WHERE C.oid=to_regclass('mta.fresh_mta_scopetransitgeneration') "
            "AND N.nspname='mta' AND P.proname=ANY(%s) ORDER BY 1",[list(functions)])
        if cursor.fetchall()!=[(name,body,False,['search_path=pg_catalog, mta'],'plpgsql',True,True,True)
                for name,body in sorted(bodies.items())]:
            raise PublicationUnavailable('bpr_transit_generation_guard_body_differs')
        from mta.runtime.ingestion_ownership import require_guard_coverage,scoped_derived_body
        require_guard_coverage(cursor)
        expected_body=scoped_derived_body(cursor,minimum='0207_scope_transit_guards')
        cursor.execute("SELECT prosrc,prosecdef,proconfig FROM pg_proc "
            "WHERE oid='mta.ingestion_watch()'::regprocedure")
        if cursor.fetchall()!=[(expected_body,True,['search_path=pg_catalog, mta'])]:
            raise PublicationUnavailable('bpr_transit_generation_revision_owner_differs')
        # The actual datetime defect must deny at admission on an older or
        # altered physical column, including a generation with no diagnostics.
        cursor.execute("SELECT format_type(atttypid,atttypmod),attnotnull FROM pg_attribute "
            "WHERE attrelid='mta.fresh_mta_scopetransitdiagnostic'::regclass "
            "AND attname='RejectionDate' AND NOT attisdropped")
        if cursor.fetchall()!=[('timestamp without time zone',True)]:
            raise PublicationUnavailable('bpr_transit_diagnostic_datetime_contract_differs')


@contextmanager
def _owner(identifier):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.scope_transit_generation',true)")
        previous=cursor.fetchone()[0] or ''
        cursor.execute("SELECT set_config('fresh.scope_transit_generation',%s,true)",[str(identifier)])
    try:yield
    except DatabaseError:
        transaction.set_rollback(True)
        raise
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.scope_transit_generation',%s,true)",[previous])


def _identity(row,sources,reports):
    return dict(schema=SCHEMA,generation_id=str(row.pk),run_id=str(row.run_id),
        phase_id=str(row.phase_id),phase_digest=sources.acceptance_digest,
        snapshot_digest=sources.snapshot_digest,input_digest=sources.run.input_digest,
        input_manifest_digest=sources.run.input_manifest_digest,action_revision=row.action_revision,
        source_digest=row.source_digest,configuration_digest=row.configuration_digest,
        recipe_digest=row.recipe_digest,transit=reports)


@dataclass(frozen=True)
class TransitBinding:
    generation: object

    def _records(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_transit_source_unavailable:'+name)
        model,fields=TABLES[name]
        with connection.chunked_cursor() as cursor:
            cursor.execute('SELECT ordinal,'+','.join(map(quote,fields))+' FROM mta.'+
                quote(model._meta.db_table)+' WHERE generation_id=%s ORDER BY ordinal',[self.generation.pk])
            count=0
            while batch:=cursor.fetchmany(500):
                for ordinal,*values in batch:
                    if ordinal!=count:raise PublicationUnavailable('bpr_transit_row_order_differs:'+name)
                    yield storage(dict(zip(fields,values)))
                    count+=1

    def verify_rows(self,name):
        count=0
        def records():
            nonlocal count
            for row in self._records(name):
                count+=1
                yield row
        observed=rows_digest(records())
        if dict(count=count,digest=observed)!=self.generation.metadata['transit']['images'][name]:
            raise PublicationUnavailable('bpr_transit_row_digest_differs:'+name)

    def rows(self,name):
        rows=list(self._records(name))
        if dict(count=len(rows),digest=rows_digest(rows))!=self.generation.metadata['transit']['images'][name]:
            raise PublicationUnavailable('bpr_transit_row_digest_differs:'+name)
        return rows

    def query(self,name):
        if name not in TABLES:raise PublicationUnavailable('bpr_transit_source_unavailable:'+name)
        model,fields=TABLES[name]
        # Expose the actual run identity. The generation UUID is only a filter.
        return ('SELECT G.run_id,R.ordinal,'+
            ','.join('R.'+quote(field) for field in fields)+' FROM mta.'+quote(model._meta.db_table)+
            ' R JOIN mta.'+quote(models.ScopeTransitGeneration._meta.db_table)+
            ' G ON G.id=R.generation_id WHERE R.generation_id=%s',[self.generation.pk])

    def image_query(self,path):
        if path not in PATHS:raise PublicationUnavailable('bpr_transit_source_unavailable:'+path)
        name=PATHS[path];_model,fields=TABLES[name]
        query,params=self.query(name)
        return ('SELECT ordinal AS vf_ordinal,'+','.join(quote(field) for field in fields)+
            ' FROM ('+query+') transit_generation'),params

    def provenance(self):
        return dict(generation_id=str(self.generation.pk),digest=self.generation.digest,
            run_id=str(self.generation.run_id),phase_id=str(self.generation.phase_id),
            source_digest=self.generation.source_digest,recipe_digest=self.generation.recipe_digest)


def bind(generation_id,*,expected_digest,action_revision):
    """Fresh exact-generation admission, not whole-application selection."""
    from django.core.exceptions import ObjectDoesNotExist
    try:row=models.ScopeTransitGeneration.objects.select_related('phase__snapshot','run').get(pk=generation_id)
    except ObjectDoesNotExist as error:raise PublicationUnavailable('bpr_transit_generation_missing') from error
    verify_guards()
    sources=scoped_sources.bind(row.phase_id,expected_digest=row.metadata.get('phase_digest'),
                               action_revision=action_revision)
    configuration=row.phase.snapshot.manifest['references']['profile']
    reports=row.metadata.get('transit',{})
    if (not row.sealed or row.sealed_at is None or row.digest!=expected_digest
            or row.digest!=digest(row.metadata) or row.run_id!=sources.run.pk
            or row.action_revision!=action_revision or row.source_digest!=sources.source_digest
            or row.configuration_digest!=configuration or row.recipe_digest!=recipe_digest()
            or reports.get('recipe_digest')!=scoped_transit.recipe_digest()
            or reports.get('source_digest')!=sources.source_digest
            or row.metadata!=_identity(row,sources,reports) or set(reports.get('images',{}))!=set(TABLES)|{'InTransitDataRaw'}):
        raise PublicationUnavailable('bpr_transit_generation_identity_differs')
    return TransitBinding(row)


@transaction.atomic
def prepare(phase_id,*,expected_digest,action_revision):
    from mta.runtime.models import CalculationRun,RunPhaseAcceptance
    phase=RunPhaseAcceptance.objects.select_related('snapshot').get(pk=phase_id)
    CalculationRun.objects.select_for_update().get(pk=phase.run_id)
    verify_guards()
    sources=scoped_sources.bind(phase_id,expected_digest=expected_digest,action_revision=action_revision)
    recipe=recipe_digest()
    existing=models.ScopeTransitGeneration.objects.filter(phase=phase,action_revision=action_revision,
        source_digest=sources.source_digest,recipe_digest=recipe).first()
    if existing is not None:
        bound=bind(existing.pk,expected_digest=existing.digest,action_revision=action_revision)
        for name in TABLES:bound.verify_rows(name)
        return existing
    row=models.ScopeTransitGeneration(run=sources.run,phase=phase,action_revision=action_revision,
        source_digest=sources.source_digest,configuration_digest=phase.snapshot.manifest['references']['profile'],
        recipe_digest=recipe)
    with _owner(row.pk):
        row.save(force_insert=True)
        reports,bags=scoped_transit.produce(phase_id,expected_digest=expected_digest,action_revision=action_revision)
        if reports['source_digest']!=sources.source_digest:raise PublicationUnavailable('bpr_transit_source_changed')
        for name,(model,fields) in TABLES.items():
            bag=bags.pop(name)
            if any(set(record)!=set(fields) for record in bag):
                raise PublicationUnavailable('bpr_transit_producer_shape_differs:'+name)
            # Bounded model batches; no second full list of model instances.
            for start in range(0,len(bag),500):
                model.objects.bulk_create([model(generation=row,ordinal=i,**bag[i])
                    for i in range(start,min(start+500,len(bag)))],batch_size=500)
            del bag
        row.metadata=_identity(row,sources,reports)
        # Verify persisted types, NULLs, bag order and full checksums before seal.
        bound=TransitBinding(row)
        for name in TABLES:bound.verify_rows(name)
        row.digest=digest(row.metadata);row.sealed=True;row.sealed_at=timezone.now()
        row.save(update_fields=['metadata','digest','sealed','sealed_at'])
    bind(row.pk,expected_digest=row.digest,action_revision=action_revision)
    return row
