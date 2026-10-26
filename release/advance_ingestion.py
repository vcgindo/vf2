"""Append an exact compatible release; keep original data and producer seals.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from mta.runtime.opening_scope import opening_operation


def catalogue(cursor):
    """Portable, complete changed-object description for an independent review.

    Object OIDs are checked separately for preservation; names and role names
    make the reviewed delta usable in a small proof and the loaded database.
    """
    from mta.mdm.owned_namespace import _application_catalogue
    cursor.execute('SELECT oid::bigint,rolname FROM pg_roles')
    roles=dict(cursor.fetchall());roles[0]='PUBLIC'
    cursor.execute('SELECT oid::bigint,lanname FROM pg_language')
    languages=dict(cursor.fetchall())
    raw=_application_catalogue(cursor);result={}
    for category,rows in raw.items():
        for item in rows:
            row={k:v for k,v in item.items() if k!='oid'}
            for field in ('owner','grantor','grantee'):
                if field in row:row[field]=roles[row[field]]
            if 'language' in row:row['language']=languages[row['language']]
            if row.get('scope')=='database':row['name']='<current_database>'
            key=category+':'+row['name']
            if category=='grants':key+=':'+str(row['column'])+':'+row['grantor']+':'+row['grantee']+':'+row['privilege']
            if key in result:raise ValueError('Ambiguous portable catalogue entry')
            result[key]=row
    queries={
        'column':"SELECT n.nspname||'.'||c.relname||'.'||a.attname,a.attnum,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum WHERE n.nspname IN ('mta','mta_state','mta_opening','fresh_control') AND a.attnum>0 AND NOT a.attisdropped ORDER BY 1",
        'constraint':"SELECT n.nspname||'.'||c.relname||'.'||t.conname,t.contype,t.convalidated,pg_get_constraintdef(t.oid) FROM pg_constraint t JOIN pg_class c ON c.oid=t.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('mta','mta_state','mta_opening','fresh_control') ORDER BY 1",
        'index':"SELECT schemaname||'.'||indexname,indexdef FROM pg_indexes WHERE schemaname IN ('mta','mta_state','mta_opening','fresh_control') ORDER BY 1",
        'trigger':"SELECT n.nspname||'.'||c.relname||'.'||t.tgname,t.tgenabled,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE NOT t.tgisinternal AND n.nspname IN ('mta','mta_state','mta_opening','fresh_control') ORDER BY 1"}
    for kind,query in queries.items():
        cursor.execute(query)
        for name,*values in cursor.fetchall():result[kind+':'+name]=values
    return result


def catalogue_delta(before,after):
    return {key:dict(before=before.get(key),after=after.get(key))
            for key in sorted(before.keys()|after.keys()) if before.get(key)!=after.get(key)}


def preservation(owner):
    """Bounded owner/capture metadata only; never reload the opening payload."""
    from release.upgrade_ingestion import retained
    from mta.runtime.models import CalculationRun
    from mta.runtime.daily_feed_models import DailyFeedAttempt
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.ingestion_models import IngestionRevisionState,MasterInputRevision,InitializationCertification
    from mta.serialization import digest
    from uuid import UUID
    runs=CalculationRun.objects.filter(csv_attempt__initialization=owner)
    def rows(query,exclude=()):
        fields=[f.attname for f in query.model._meta.concrete_fields if f.name not in exclude]
        return [{k:str(v) if isinstance(v,UUID) else v for k,v in row.items()}
                for row in query.order_by(query.model._meta.pk.attname).values(*fields)]
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM information_schema.columns WHERE table_schema='mta' AND table_name='fresh_mta_dailyfeedattempt' AND column_name='recovery_origin_id'")
        has_origin=cursor.fetchone() is not None
    attempts=rows(DailyFeedAttempt.objects.filter(initialization=owner),() if has_origin else ('recovery_origin',))
    for attempt in attempts:attempt.setdefault('recovery_origin_id',None)
    return dict(opening=retained(owner),certificate=rows(InitializationCertification.objects.filter(initialization=owner)),
        revisions=rows(IngestionRevisionState.objects.filter(initialization=owner)),
        masters=rows(MasterInputRevision.objects.filter(initialization=owner)),
        runs=rows(runs,('input_payload',)),attempts=attempts,
        captures=rows(MdmDailyInputCapture.objects.filter(run__in=runs)),
        manifests={str(pk):digest(payload) for pk,payload in runs.order_by('pk').values_list('pk','input_payload')})


def authority_history(cursor, initialization_id):
    """Full existing append-only rows, including prior schema admissions."""
    import json
    tables=('fresh_control.ingestion_release_authority',
            'fresh_control.ingestion_schema_compatibility',
            'mta.fresh_mta_ingestionreleasecompatibility')
    result={}
    for table in tables:
        cursor.execute('SELECT to_regclass(%s)',[table])
        if cursor.fetchone()[0] is None:
            result[table]={};continue
        cursor.execute('SELECT target_release,to_jsonb(T) FROM '+table+' T WHERE initialization_id=%s',
                       [initialization_id])
        result[table]={key:json.loads(row) if isinstance(row,str) else row for key,row in cursor.fetchall()}
    return result


def _qualify_owned_publications(owner, target, check_session):
    """Read-only full qualification before committing the ownership upgrade."""
    from django.db.models import Q
    from mta.runtime.models import CalculationRun, DailyUiPublication, BtrReportingGeneration
    from mta.presentation.admission import verify
    from mta.presentation.report_verification import _schema_transition_scope
    from mta.presentation.btr_reporting import source_identity, verify_generation
    from mta.presentation.native_publication import require_mode
    from mta.serialization import digest
    # verify() retains its ordinary configurable/non-native behavior. This
    # transition may qualify only the complete native publication path; missing
    # flags must fail rather than silently skip daily layers or native rows.
    require_mode()
    runs = CalculationRun.objects.filter(Q(mdm_input_capture__source_id=owner.source_id)
        | Q(csv_attempt__initialization=owner)).values('pk')
    publications = DailyUiPublication.objects.select_related('run').filter(
        status='READY', run_id__in=runs).order_by('run__business_date', 'run_id')
    qualified = []
    for publication in publications:
        run = publication.run
        with _schema_transition_scope(run, owner, target, check_session):
            verify(run)
            identifier = publication.layers.get('btr', {}).get('receipt', {}).get('generation')
            generation = BtrReportingGeneration.objects.get(pk=identifier, run=run, status='READY')
            if generation.source_digest != digest(source_identity(run, generation.version)):
                raise ValueError('Qualified BTR generation source differs')
            verify_generation(generation)
        qualified.append(dict(run_id=str(run.pk), output_digest=run.output_digest,
                              publication_seal=publication.seal_digest))
    return qualified


@opening_operation
def schema_transition(initialization_id, *, specification, expected_sha256):
    """Explicit atomic used-opening upgrade, never implicit startup recovery.

    The external reviewed specification pins exact release identities, migration
    bytes and the complete portable catalogue/ACL delta. All DDL and registrar
    appends roll back together. This operation changes no old owner or seal.
    """
    import hashlib,json
    from pathlib import Path
    from django.db import connection,transaction
    from django.db.migrations.executor import MigrationExecutor
    from psycopg import sql
    from release.native_identity import require_current
    from release.native_schema import schema_digest
    from mta.serialization import digest,storage
    from mta.runtime import ingestion_authority as authority
    from mta.runtime.ingestion_admission import _admit,registration,security_digest,_certificate
    from mta.runtime.models import ProductionInitialization
    from mta.runtime.ingestion_models import IngestionReleaseCompatibility
    raw=Path(specification).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError('Independent schema transition specification SHA256 differs')
    spec=json.loads(raw)
    fields={'contract','initialization_id','previous_release','target_release','migration_pins','catalogue_delta'}
    if (type(spec) is not dict or set(spec)!=fields or spec['contract']!=authority.SCHEMA_CONTRACT
            or spec['initialization_id']!=str(initialization_id) or spec['target_release']!=require_current()):
        raise ValueError('Exact reviewed schema transition specification required')
    target=spec['target_release'];previous=spec['previous_release']
    from mta.runtime import report_guard_transition as report_guard
    from mta.runtime import accepted_state_transition as ownership
    from mta.runtime import scoped_action_transition as scoped_action
    from mta.runtime import bpr_history_schema_transition as bpr_history
    from mta.runtime import scoped_dbm_transition as scoped_dbm
    from mta.runtime import scoped_read_transition as scoped_read
    from mta.runtime import runtime_report_schema_transition as publication
    from mta.runtime import runtime_placement_schema_transition as placement
    guard_migration=any(pin[0]==report_guard.MIGRATION_NAME for pin in spec['migration_pins'])
    ownership_migration=any(pin[0] in {name for name,_ in ownership.PINS} for pin in spec['migration_pins'])
    action_migration=any(pin[0]==scoped_action.MIGRATION_NAME for pin in spec['migration_pins'])
    history_migration=any(pin[0]==bpr_history.MIGRATION_NAME for pin in spec['migration_pins'])
    dbm_migration=any(pin[0] in {name for name,_ in scoped_dbm.PINS} for pin in spec['migration_pins'])
    read_migration=any(pin[0] in {name for name,_ in scoped_read.PINS} for pin in spec['migration_pins'])
    publication_migration=any(pin[0] in publication.NAMES for pin in spec['migration_pins'])
    placement_migration=any(pin[0] in placement.NAMES for pin in spec['migration_pins'])
    if placement_migration:
        placement.require_specification(spec)
    if publication_migration:
        publication.require_specification(spec)
    if guard_migration:
        report_guard.require_specification(spec)
    if ownership_migration:
        ownership.require_specification(spec)
    if action_migration:
        scoped_action.require_specification(spec)
    if history_migration:
        bpr_history.require_specification(spec)
    if dbm_migration:
        scoped_dbm.require_specification(spec)
    if read_migration:
        scoped_read.require_specification(spec)
    if target['manifest_sha256']==previous['manifest_sha256']:
        raise ValueError('Distinct reviewed previous/target releases required')
    from mta.runtime.daily_feed import job_lock
    from mta.mdm.supplier_revisions import source_lock
    prepared_owner=ProductionInitialization.objects.get(pk=initialization_id)
    if not transaction.get_autocommit():raise ValueError('Schema transition owns its outer transaction')
    # Session locks precede the repeatable-read snapshot. A cooperating daily or
    # master writer cannot connect after the client check and evade preservation.
    qualified = None
    with job_lock(prepared_owner) as check_session,source_lock(prepared_owner.source_id),transaction.atomic(),connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        authority._provisioner(cursor)
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('fresh.production.initialization',0))")
        cursor.execute("SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND backend_type='client backend' LIMIT 1")
        if cursor.fetchone() is not None:raise ValueError('Schema transition requires exclusive maintenance ownership')
        owner=ProductionInitialization.objects.select_for_update().select_related('source').get(pk=initialization_id)
        original,capability=registration(cursor)
        cursor.execute('SELECT to_regclass(%s)',[authority.SCHEMA_TABLE])
        has_schema_authority=cursor.fetchone()[0] is not None
        cursor.execute('SELECT 1 FROM fresh_control.ingestion_release_authority WHERE initialization_id=%s AND target_release=%s',[owner.pk,target['manifest_sha256']])
        if cursor.fetchone() is not None:
            body=authority.read(cursor,owner.pk,target['manifest_sha256'])
            extension=authority.read_schema_transition(cursor,body)
            if (extension is None or extension['migration_pins']!=spec['migration_pins']
                    or extension['catalogue_delta_digest']!=digest(spec['catalogue_delta'])
                    or extension['previous_release']!=previous['manifest_sha256']):
                raise ValueError('Existing schema transition differs; no replacement')
            _admit(cursor,owner.pk,target,pending=True)
            return dict(status='EXISTING_SCHEMA_TRANSITION_VERIFIED',target_release=target)
        admitted=_admit(cursor,owner.pk,previous,pending=True)
        if publication_migration:
            publication.require_start(cursor)
        if placement_migration:
            placement.require_start(cursor)
        before=storage(preservation(owner));before_catalogue=catalogue(cursor)
        old_history=authority_history(cursor,owner.pk)
        old=authority.read(cursor,owner.pk,previous['manifest_sha256'])
        before_schema=schema_digest(cursor);before_guard=security_digest(cursor,_certificate(owner.pk)['authority_roles'])
        if read_migration and (before_schema!=scoped_read.BEFORE_SCHEMA or before_guard!=scoped_read.BEFORE_GUARD):
            raise ValueError('Live-reference upgrade requires its exact admitted226 catalogue')
        if dbm_migration and (not has_schema_authority or before_schema!=scoped_dbm.BEFORE_SCHEMA
                or before_guard!=scoped_dbm.BEFORE_GUARD):
            raise ValueError('UptoDBM upgrade requires its exact admitted223 catalogue')
        if history_migration and (not has_schema_authority or before_schema!=bpr_history.BEFORE_SCHEMA
                or before_guard!=bpr_history.BEFORE_GUARD):
            raise ValueError('BPR history upgrade requires its exact admitted222 catalogue')
        if guard_migration and (not has_schema_authority or before_schema!=report_guard.BEFORE_SCHEMA
                or before_guard!=report_guard.BEFORE_GUARD):
            raise ValueError('Report guard migration requires its exact admitted predecessor catalogue')
        if ownership_migration and (not has_schema_authority or before_schema!=ownership.BEFORE_SCHEMA
                or before_guard!=ownership.BEFORE_GUARD):
            raise ValueError('Accepted-state migration requires its exact admitted predecessor catalogue')
        if action_migration:
            from mta.runtime.ingestion_ownership import migration_history_guard
            if (before_schema!=scoped_action.BEFORE_SCHEMA or before_guard!=scoped_action.BEFORE_GUARD
                    or not migration_history_guard(cursor)
                    or spec['catalogue_delta']!=scoped_action.catalogue_delta(bootstrap=not has_schema_authority)):
                raise ValueError('Recovered-action migration requires its exact admitted221 catalogue/history guard')
        cursor.execute('SELECT oid::bigint,rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolinherit,rolconfig FROM pg_roles ORDER BY oid')
        roles=cursor.fetchall()
        cursor.execute('SELECT roleid,member,grantor,admin_option FROM pg_auth_members ORDER BY roleid,member,grantor')
        memberships=cursor.fetchall()
        executor=MigrationExecutor(connection)
        plan=executor.migration_plan(executor.loader.graph.leaf_nodes())
        pins=[]
        for migration,backwards in plan:
            if backwards or migration.app_label!='fresh_mta':raise ValueError('Only forward MTA schema migrations supported')
            path=Path(__file__).resolve().parents[1]/'mta/runtime/migrations'/(migration.name+'.py')
            pins.append([migration.name,hashlib.sha256(path.read_bytes()).hexdigest()])
        allowed_migrations=([['0165'],['0166'],['0167']] if has_schema_authority else
                            [[f'{i:04}' for i in range(154,end)] for end in (165,166,167)])
        if guard_migration:
            allowed_migrations=[['0168']]
        if ownership_migration:
            allowed_migrations=[['0169','0170']]
        if action_migration:
            allowed_migrations=[['0222']]
        if history_migration:
            allowed_migrations=[['0223']]
        if dbm_migration:
            allowed_migrations=[['0224','0225','0226']]
        if read_migration:
            allowed_migrations=[['0227','0228']]
        if publication_migration:
            allowed_migrations=[['0229','0230']]
        if placement_migration:
            allowed_migrations=[['0231']]
        if (pins!=spec['migration_pins'] or [n[:4] for n,h in pins] not in allowed_migrations):
            raise ValueError('Exact reviewed report migration prefix and bytes required')
        from mta.mdm.owned_namespace import _application_catalogue
        old_objects=_application_catalogue(cursor)
        cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(original['owner']['name'])))
        # Install the same final pinned append guard BEFORE Django records any
        # migration. Migration bookkeeping cannot advance a business epoch;
        # no epoch is restored and no business writer guard is disabled.
        from importlib import import_module
        if not has_schema_authority and not action_migration and not publication_migration and not placement_migration:
            cursor.execute(import_module('mta.runtime.migrations.0164_migration_history_ownership').FORWARD)
        executor.migrate(executor.loader.graph.leaf_nodes())
        cursor.execute('RESET ROLE')
        if dbm_migration:
            scoped_dbm.upgrade_application_guard(cursor)
        if read_migration:
            scoped_read.upgrade_application_guard(cursor)
        if not has_schema_authority:
            authority.bootstrap_schema_transition(cursor,[original['owner']['name'],original['consumer']['name']])
        current=_application_catalogue(cursor)
        old_names={o['name'] for o in old_objects['objects']}
        for obj in current['objects']:
            if obj['name'] not in old_names and obj['kind']!='S':
                schema,name=obj['name'].split('.',1)
                cursor.execute(sql.SQL('GRANT SELECT ON {}.{} TO {}').format(sql.Identifier(schema),sql.Identifier(name),sql.Identifier(original['consumer']['name'])))
        old_functions={f['name'] for f in old_objects['functions']}
        for function in current['functions']:
            if function['name'] not in old_functions:
                cursor.execute('SELECT %s::oid::regprocedure::text',[function['oid']])
                cursor.execute('REVOKE EXECUTE ON FUNCTION '+cursor.fetchone()[0]+' FROM PUBLIC')
        grant_sets={
            '0163':('mta.finite_capture_prefix_digest(uuid)',),
            '0165':('mta.terminal_capture_prefix_digest(uuid)',
                    'mta.terminal_capture_admit(mta.fresh_mta_dailyfeedattempt)'),
            '0166':('mta.retry_capture_prefix_digest(uuid)',
                    'mta.retry_capture_admit(mta.fresh_mta_dailyfeedattempt)'),
            '0167':('mta.final_capture_prefix_digest(uuid)',
                    'mta.final_capture_admit(mta.fresh_mta_dailyfeedattempt)'),
            '0228':scoped_read.EXECUTE,
        }
        for grant in (grant for name,_ in pins for grant in grant_sets.get(name[:4],())):
            # Resolve exact argument types independently of search_path's
            # pretty-printing of composite-type identity arguments.
            cursor.execute('SELECT to_regprocedure(%s)',[grant])
            if cursor.fetchone()[0] is not None:
                cursor.execute(sql.SQL('GRANT EXECUTE ON FUNCTION '+grant+' TO {}').format(sql.Identifier(original['consumer']['name'])))
        delta=catalogue_delta(before_catalogue,catalogue(cursor))
        if storage(delta)!=spec['catalogue_delta']:raise ValueError('Reviewed schema/catalogue/ACL delta differs')
        if read_migration and schema_digest(cursor)!=scoped_read.AFTER_SCHEMA:
            raise ValueError('Live-reference target schema differs from the qualified catalogue')
        now=_application_catalogue(cursor)
        objects={o['name']:o for o in now['objects']}
        if any(objects.get(o['name'])!=o for o in old_objects['objects']):
            raise ValueError('Original object identity or owner changed')
        old_acl={(r['scope'],r['name']) for r in old_objects['grants']}
        if [r for r in now['grants'] if (r['scope'],r['name']) in old_acl]!=old_objects['grants']:
            raise ValueError('Original ACL changed')
        cursor.execute('SELECT oid::bigint,rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolinherit,rolconfig FROM pg_roles ORDER BY oid')
        if cursor.fetchall()!=roles:raise ValueError('Schema transition changed roles')
        cursor.execute('SELECT roleid,member,grantor,admin_option FROM pg_auth_members ORDER BY roleid,member,grantor')
        if cursor.fetchall()!=memberships:raise ValueError('Schema transition changed memberships')
        from mta.runtime.ingestion_admission import _certificate
        cert=_certificate(owner.pk)
        extension=dict(contract=authority.SCHEMA_CONTRACT,initialization_id=str(owner.pk),
            target_commit=target['source_commit'],target_release=target['manifest_sha256'],
            previous_release=previous['manifest_sha256'],previous_authority_digest=digest(old),
            certification_digest=cert['receipt_digest'],before_schema_digest=before_schema,before_guard_digest=before_guard,
            schema_digest=schema_digest(cursor),guard_digest=security_digest(cursor,cert['authority_roles']),
            migration_pins=pins,catalogue_delta_digest=digest(delta),preservation_digest=digest(before))
        authority.append_schema_transition(cursor,extension)
        body=dict(old,target_commit=target['source_commit'],target_release=target['manifest_sha256'])
        audit={key:body[key] for key in ('original_release','target_release','original_commit','target_commit',
            'contract','original_registration_digest','schema_digest','certification_digest')}
        cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(original['owner']['name'])))
        IngestionReleaseCompatibility.objects.create(initialization=owner,**audit,receipt_digest=digest(audit))
        cursor.execute('RESET ROLE')
        authority.append(cursor,body)
        _admit(cursor,owner.pk,target,pending=True)
        if ownership_migration:
            # These uncommitted authority rows cannot authorize a serving reader.
            # Any audit error rolls back DDL and authority appends together.
            qualified = _qualify_owned_publications(owner, target, check_session)
            _admit(cursor,owner.pk,target,pending=True)
            cursor.execute("SELECT 1 FROM pg_stat_activity WHERE datname=current_database() "
                "AND pid<>pg_backend_pid() AND backend_type='client backend' LIMIT 1")
            if cursor.fetchone() is not None:
                raise ValueError('Schema qualification lost exclusive maintenance ownership')
        new_history=authority_history(cursor,owner.pk)
        for table,rows in old_history.items():
            if (any(new_history[table].get(key)!=row for key,row in rows.items())
                    or set(new_history[table])-set(rows)!={target['manifest_sha256']}):
                raise ValueError('Schema transition changed a prior registrar or compatibility row')
        owner.refresh_from_db();owner.source.refresh_from_db()
        if storage(preservation(owner))!=before or registration(cursor)!=(original,capability):
            raise ValueError('Schema transition changed an original opening/owner/capture/certificate')
    result = dict(status='SCHEMA_TRANSITION_COMMITTED_ORIGINAL_STATE_PRESERVED',target_release=target,
                schema_transition_digest=digest(extension),catalogue_delta_digest=digest(delta))
    if qualified is not None:
        result['qualified_read_ready_runs'] = qualified
    return result


@opening_operation
def transition(initialization_id, *, previous_release, target_release):
    from django.db import connection, transaction
    from release.native_identity import require_current
    from mta.runtime.ingestion_admission import _admit, registration
    from mta.runtime import ingestion_authority as authority
    from mta.runtime.ingestion_models import IngestionReleaseCompatibility
    from mta.runtime.models import ProductionInitialization
    from mta.serialization import digest
    from release.upgrade_ingestion import retained
    release = require_current()
    if release != target_release or previous_release['manifest_sha256'] == release['manifest_sha256']:
        raise ValueError('Exact independently reviewed old/new releases required')
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        authority._provisioner(cursor)
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('fresh.production.initialization',0))")
        cursor.execute('SELECT 1 FROM pg_stat_activity WHERE datname=current_database() '
                       'AND pid<>pg_backend_pid() AND backend_type=\'client backend\' LIMIT 1')
        if cursor.fetchone() is not None:
            raise ValueError('Compatible transition requires exclusive maintenance ownership')
        owner = ProductionInitialization.objects.select_for_update().select_related('source').get(pk=initialization_id)
        before = retained(owner)
        previous = _admit(cursor, owner.pk, previous_release, pending=True)
        original, capability = registration(cursor)
        old = authority.read(cursor, owner.pk, previous_release['manifest_sha256'])
        body = dict(old, target_commit=release['source_commit'], target_release=release['manifest_sha256'])
        # No schema migrations, grants, registration, certification or population
        # writes. The current schema and security digests must remain exact.
        audit = {key:body[key] for key in ('original_release','target_release','original_commit','target_commit',
            'contract','original_registration_digest','schema_digest','certification_digest')}
        if IngestionReleaseCompatibility.objects.filter(initialization=owner, target_release=body['target_release']).exists():
            current = _admit(cursor, owner.pk, release, pending=True)
            return dict(status='EXISTING_COMPATIBLE_RELEASE_VERIFIED', certification_digest=current.certification_digest)
        from psycopg import sql
        authority.inherit_code_schema(cursor,body,old)
        cursor.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(original['owner']['name'])))
        IngestionReleaseCompatibility.objects.create(initialization=owner, **audit, receipt_digest=digest(audit))
        cursor.execute('RESET ROLE')
        authority.append(cursor, body)
        current = _admit(cursor, owner.pk, release, pending=True)
        owner.refresh_from_db(); owner.source.refresh_from_db()
        if (retained(owner) != before or registration(cursor) != (original, capability)
                or current.certification_digest != previous.certification_digest):
            raise ValueError('Compatible release changed a sealed producer or opening')
    return dict(status='COMPATIBLE_RELEASE_APPENDED_ORIGINAL_CERTIFICATE_PRESERVED',
        initialization_id=str(owner.pk), certification_digest=current.certification_digest,
        previous_release=previous_release, target_release=release)
