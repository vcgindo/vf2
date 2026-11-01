"""Database half of the standard upgrade command; no calculation or report build.

The host owns backup, filesystem lock, image switching and service readiness.
This process authenticates target source, original ownership, schema, and the
preserved accepted prefix. Only a real schema change appends a schema receipt.
"""
import argparse
import json
import os
from pathlib import Path
import uuid


def _save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_bytes((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
    temporary.replace(path)


def _rows(cursor, table, where, arguments):
    # Finite repository-owned identifiers/predicates only; values are parameters.
    cursor.execute('SELECT to_jsonb(T)-\'input_payload\' FROM '+table+' T WHERE '+where,
        arguments)
    rows=[(json.loads(row[0]) if isinstance(row[0],str) else row[0],)
        for row in cursor.fetchall()]
    return sorted(rows,key=lambda row:json.dumps(row[0],sort_keys=True))


def snapshot(owner):
    """Sealed metadata, not a second scan/materialization of business images."""
    from django.db import connection
    init = str(owner.pk)
    source = owner.source_id
    run_sql='SELECT run_id FROM mta.fresh_mta_dailyfeedattempt WHERE initialization_id=%s AND run_id IS NOT NULL'
    publication_sql='SELECT run_id FROM mta.fresh_mta_dailyuipublication WHERE run_id IN ('+run_sql+')'
    tables=[
        ('mta.fresh_mta_productioninitialization','id=%s',[init]),
        ('mta.fresh_mta_mdmsource','id=%s',[source]),
        ('mta.fresh_mta_mdmfamilysource','source_id=%s',[source]),
        ('mta.fresh_mta_mdmsourceintegration','source_id=%s',[source]),
        ('mta.fresh_mta_initializationcertification','initialization_id=%s',[init]),
        ('mta.fresh_mta_ingestionrevisionstate','initialization_id=%s',[init]),
        ('mta.fresh_mta_masterinputrevision','initialization_id=%s',[init]),
        ('mta.fresh_mta_dailyfeedattempt','initialization_id=%s',[init]),
        ('mta.fresh_mta_calculationrun','id IN ('+run_sql+')',[init]),
        ('mta.fresh_mta_mdmdailyinputcapture','source_id=%s',[source]),
        ('mta.fresh_mta_dailyuipublication','run_id IN ('+run_sql+')',[init]),
        ('mta.fresh_mta_dailyuipublicationattempt','publication_id IN ('+publication_sql+')',[init]),
        ('mta.fresh_mta_dailyreportgeneration','run_id IN ('+run_sql+')',[init]),
        ('mta.fresh_mta_btrreportinggeneration','run_id IN ('+run_sql+')',[init]),
        ('mta.fresh_mta_ingestionreleasecompatibility','initialization_id=%s',[init]),
        ('fresh_control.ingestion_release_authority','initialization_id=%s',[init]),
    ]
    with connection.cursor() as cursor:
        return {table:[row[0] for row in _rows(cursor,table,where,args)] for table,where,args in tables}


def preserved(before, after):
    """Existing row fields stay exact; explicit additive columns may be new."""
    for table, old_rows in before.items():
        new_rows=after.get(table,[])
        if len(old_rows) != len(new_rows):
            raise ValueError('Upgrade changed preserved metadata population: '+table)
        # Sort by stable existing fields, not a newly added column.
        columns=set().union(*(row.keys() for row in old_rows)) if old_rows else set()
        project=lambda rows:sorted([{k:row.get(k) for k in columns} for row in rows],
            key=lambda row:json.dumps(row,sort_keys=True))
        if project(old_rows) != project(new_rows):
            raise ValueError('Upgrade changed accepted metadata: '+table)


def selected(owner):
    from django.db import connection
    from mta.presentation.native_selection import read
    path=Path(os.environ.get('VF_MTA_SELECTION_FILE') or '/var/lib/vectorflow/selection.json')
    if not path.exists():
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM mta.fresh_mta_dailyfeedattempt "
                "WHERE initialization_id=%s AND status='PUBLISHED')",[owner.pk])
            if cursor.fetchone() != (False,):
                raise ValueError('Published installation has no selected publication file')
        return None
    value=read(path)
    with connection.cursor() as cursor:
        cursor.execute('SELECT R.business_date,R.output_digest,R.status,P.status '
            'FROM mta.fresh_mta_calculationrun R '
            'JOIN mta.fresh_mta_dailyfeedattempt A ON A.run_id=R.id '
            'JOIN mta.fresh_mta_dailyuipublication P ON P.run_id=R.id '
            'WHERE R.id=%s AND A.initialization_id=%s',[value['run_id'],owner.pk])
        row=cursor.fetchone()
    if row is None or row[1:] != (value['output_digest'],'SUCCEEDED','READY'):
        raise ValueError('Selected publication does not belong to the accepted installation')
    return dict(run_id=value['run_id'],output_digest=value['output_digest'],
        business_date=row[0].isoformat(),selection_digest=value['selection_digest'])


def migration_plan(previous):
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from mta.runtime.schema_admission import native_migrations
    from mta.serialization import digest
    executor=MigrationExecutor(connection)
    plan=executor.migration_plan(executor.loader.graph.leaf_nodes())
    applied={name for app,name in executor.loader.applied_migrations if app=='fresh_mta'}
    files=native_migrations()
    known={Path(name).stem for name in files if Path(name).stem!='__init__'}
    if not applied <= known:
        raise ValueError('Unknown applied migration history; explicit repair is required')
    old_files={name:pin for name,pin in files.items()
        if Path(name).stem=='__init__' or Path(name).stem in applied}
    if digest(old_files) != previous['migrations_digest']:
        raise ValueError('Applied historical migration bytes differ; never edit applied migrations')
    if any(backwards or migration.app_label!='fresh_mta' or not migration.atomic
            for migration,backwards in plan):
        raise ValueError('Only forward atomic MTA migrations are supported by routine upgrade')
    return executor,plan


def _target_grants(cursor, original, prior_tables):
    """New native tables keep existing read/guard policy; no public writers."""
    from psycopg import sql
    from mta.mdm.owned_namespace import _application_catalogue
    catalogue=_application_catalogue(cursor)
    owner=original['owner']['name'];runtime=original['consumer']['name']
    # These statements only confer the already-required SELECT scope. Business
    # actions/function EXECUTE grants belong to their actual feature migration.
    for item in catalogue['objects']:
        if (item['kind'] != 'S' and item['name'].startswith(('mta.','mta_state.','mta_opening.'))
                and tuple(item['name'].split('.',1)) not in prior_tables):
            schema,name=item['name'].split('.',1)
            cursor.execute(sql.SQL('GRANT SELECT ON {}.{} TO {}').format(
                sql.Identifier(schema),sql.Identifier(name),sql.Identifier(runtime)))
    # Only tables created by the declared forward migrations receive standard
    # revision watches. Old tables were checked before migration; never repair
    # missing old guards or replace a migration's conflicting declared guards.
    from mta.runtime.ingestion_ownership import require_guard_coverage, tables
    cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(owner)))
    for schema,table,domain in tables(cursor):
        if (schema,table) in prior_tables or domain=='authority':
            continue
        cursor.execute("SELECT count(*) FROM pg_trigger WHERE tgrelid=to_regclass(%s) "
            "AND tgname LIKE 'ingestion_watch_%%'",[schema+'.'+table])
        if cursor.fetchone()[0]:
            continue
        for suffix,operation,reference in (
                ('insert','INSERT','NEW TABLE AS new_rows'),
                ('update','UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),
                ('delete','DELETE','OLD TABLE AS old_rows'),('truncate','TRUNCATE','')):
            cursor.execute(sql.SQL('CREATE TRIGGER {} AFTER '+operation+' ON {}.{} '+
                ('REFERENCING '+reference+' ' if reference else '')+
                'FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch({})').format(
                    sql.Identifier('ingestion_watch_'+suffix),sql.Identifier(schema),
                    sql.Identifier(table),sql.Literal(domain)))
    cursor.execute('RESET ROLE')
    require_guard_coverage(cursor)
    from mta.mdm.owned_namespace import _check_application_grants
    _check_application_grants(_application_catalogue(cursor),original,
        logistics=True,production=True)


def _previous_schema(cursor, owner, previous):
    """One maintenance-only adoption of a genuinely admitted historical schema.

    Missing a schema checkpoint is not a reason to ignore a bad checkpoint or
    guard. Only absence takes this old verifier path. Later code patches use
    the stable migration-roster checkpoint and never append release authority.
    """
    from mta.runtime import schema_admission,ingestion_authority as authority
    from mta.runtime.ingestion_admission import _admit,validate_activation
    try:
        _admit(cursor,owner.pk,previous,pending=True)
        return False
    except schema_admission.SchemaUpgradeRequired:
        old=authority.read(cursor,owner.pk,previous['manifest_sha256'])
        if old['target_commit'] != previous['source_commit']:
            raise ValueError('Historical schema was admitted for another producer')
        validate_activation(cursor,old)
        return True


def run(phase, initialization, previous, receipt):
    import django
    django.setup()
    from django.db import connection,transaction
    from release.native_identity import require_current
    from mta.runtime import schema_admission,ingestion_authority as authority
    from mta.runtime.ingestion_admission import _admit
    from mta.runtime.initialization_models import ProductionInitialization
    from mta.runtime.daily_feed import job_lock
    from mta.mdm.supplier_revisions import source_lock
    from mta.serialization import digest
    target=require_current()
    if previous.get('schema') != target['schema']:
        raise ValueError('Previous native release descriptor is unsupported')
    owner=ProductionInitialization.objects.select_related('source').get(pk=initialization)
    root=Path(receipt).parent
    before_path=root/'database-before.json'
    selection_path=root/'selection-before.json'
    if phase=='inspect':
        with transaction.atomic(),connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            adoption=_previous_schema(cursor,owner,previous)
            _executor,plan=migration_plan(previous)
            current_selected=selected(owner)
        value=dict(status='UPGRADE_DATABASE_INSPECTED',initialization_id=str(owner.pk),
            source_digest=owner.source.digest,target_release=target,
            pending_migrations=[m.name for m,_backwards in plan],schema_adoption=adoption,
            selected=current_selected)
    elif phase=='apply':
        # A receipt/journal cannot grant permission to repeat accepted work.
        # Original DB owners, live guards and actual migration history decide.
        with job_lock(owner),source_lock(owner.source_id):
            with transaction.atomic(),connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                authority._provisioner(cursor)
                cursor.execute('SELECT 1 FROM pg_stat_activity WHERE datname=current_database() '
                    "AND pid<>pg_backend_pid() AND backend_type='client backend' LIMIT 1")
                if cursor.fetchone() is not None:
                    raise ValueError('Upgrade requires stopped MTA and no other database client writers')
                adoption=_previous_schema(cursor,owner,previous)
                executor,plan=migration_plan(previous)
                before=snapshot(owner);selection_before=selected(owner)
                from mta.mdm.owned_namespace import _application_catalogue
                prior_tables={tuple(item['name'].split('.',1))
                    for item in _application_catalogue(cursor)['objects']}
                if before_path.exists():
                    # An explicitly resumed atomic rollback retains the first
                    # snapshot. Never overwrite evidence or replay an already
                    # committed data migration merely because its response died.
                    preserved(json.loads(before_path.read_bytes()),before)
                    if selection_before != json.loads(selection_path.read_bytes()):
                        raise ValueError('Selected publication changed after failed atomic migration')
                else:
                    _save(before_path,before);_save(selection_path,selection_before)
                if plan:
                    from psycopg import sql
                    original,_capability=__import__('mta.runtime.ingestion_admission',fromlist=['registration']).registration(cursor)
                    cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(original['owner']['name'])))
                    executor.migrate(executor.loader.graph.leaf_nodes())
                    cursor.execute('RESET ROLE')
                    _target_grants(cursor,original,prior_tables)
                if plan or adoption:
                    schema_admission.append(cursor,owner.pk,target)
                _admit(cursor,owner.pk,target,pending=True)
                after=snapshot(owner);preserved(before,after)
                if selected(owner) != selection_before:
                    raise ValueError('Upgrade changed the selected publication')
        value=dict(status='UPGRADE_DATABASE_APPLIED',initialization_id=str(owner.pk),
            target_release=target,selected=selection_before,
            applied_migrations=[m.name for m,_backwards in plan],
            preserved_metadata_digest=digest(before),code_release_authority_appends=0)
    elif phase=='verify':
        with transaction.atomic(),connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            from django.db.migrations.executor import MigrationExecutor
            executor=MigrationExecutor(connection)
            if not before_path.exists() or not selection_path.exists():
                raise ValueError('Original upgrade preservation snapshot is missing')
            before=json.loads(before_path.read_bytes());preserved(before,snapshot(owner))
            current_selected=selected(owner)
            if current_selected != json.loads(selection_path.read_bytes()):
                raise ValueError('Selected publication changed during upgrade')
            pending=executor.migration_plan(executor.loader.graph.leaf_nodes())
            if pending:
                # Prove the whole old schema/migration prefix/metadata remains;
                # this is not permission to repair a partial/foreign migration.
                _previous_schema(cursor,owner,previous)
                migration_plan(previous)
            else:
                _admit(cursor,owner.pk,target,pending=True)
        value=dict(status='UPGRADE_DATABASE_APPLY_REQUIRED' if pending else 'UPGRADE_DATABASE_VERIFIED',initialization_id=str(owner.pk),
            target_release=target,selected=current_selected,preserved_metadata_digest=digest(before),
            code_release_authority_appends=0)
    else:
        raise ValueError('Unknown upgrade database phase')
    _save(receipt,value)
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('inspect','apply','verify'),required=True)
    parser.add_argument('--initialization',type=uuid.UUID,required=True)
    parser.add_argument('--previous-release',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=run(args.phase,args.initialization,json.loads(args.previous_release.read_bytes()),args.receipt)
        print(json.dumps(result,sort_keys=True))
    finally:
        from django.db import connections
        connections.close_all()
