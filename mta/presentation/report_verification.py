"""Finite, guarded read verification for post-calculation report operations.

Only successful immutable audits are reused. No graph, mutable action state or
permission result is retained; each new process/operation admits independently.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

from django.db import connection

from mta.serialization import digest

_current = ContextVar('native_report_verification', default=None)


def guard_stamp():
    """Live DDL/ACL/trigger generations, including change-and-restore of guards.

    The runtime cannot disable sealed-row guards or assume the owner. Fresh
    certified admission establishes those privileges before any reuse. Catalogue
    xmin detects replacement/restoration even when function text is identical.
    This needs SELECT privileges only, not table-owner SHARE locks.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(),(SELECT oid::text FROM pg_database "
            "WHERE datname=current_database()),session_user,current_user,"
            "current_setting('transaction_isolation'),current_setting('session_replication_role'),"
            "current_setting('search_path'),current_setting('row_security'),"
            "current_setting('TimeZone'),current_setting('DateStyle'),current_setting('client_encoding')")
        identity = cursor.fetchone()
        if identity[4:6] != ('read committed', 'origin'):
            raise ValueError('Report verification requires live guarded READ COMMITTED reads')
        generations = []
        for table, namespace, join in (
                ('pg_namespace', 'c', ''),
                ('pg_class', 'n', ' JOIN pg_namespace n ON n.oid=c.relnamespace'),
                ('pg_proc', 'n', ' JOIN pg_namespace n ON n.oid=c.pronamespace'),
                ('pg_type', 'n', ' JOIN pg_namespace n ON n.oid=c.typnamespace'),
                ('pg_trigger', 'n', ' JOIN pg_class r ON r.oid=c.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace'),
                ('pg_attrdef', 'n', ' JOIN pg_class r ON r.oid=c.adrelid JOIN pg_namespace n ON n.oid=r.relnamespace'),
                ('pg_policy', 'n', ' JOIN pg_class r ON r.oid=c.polrelid JOIN pg_namespace n ON n.oid=r.relnamespace'),
                ('pg_rewrite', 'n', ' JOIN pg_class r ON r.oid=c.ev_class JOIN pg_namespace n ON n.oid=r.relnamespace'),
                ('pg_constraint', 'n', ' JOIN pg_namespace n ON n.oid=c.connamespace')):
            cursor.execute('SELECT c.oid::bigint,c.xmin::text FROM pg_catalog.' + table +
                ' c' + join + ' WHERE ' + namespace + ".nspname !~ '^(pg_|information_schema$)' ORDER BY c.oid")
            generations.append(cursor.fetchall())
        cursor.execute('SELECT a.attrelid::bigint,a.attnum,a.xmin::text FROM pg_attribute a '
            'JOIN pg_class r ON r.oid=a.attrelid JOIN pg_namespace n ON n.oid=r.relnamespace '
            "WHERE n.nspname !~ '^(pg_|information_schema$)' ORDER BY 1,2")
        generations.append(cursor.fetchall())
        cursor.execute('SELECT i.indexrelid::bigint,i.xmin::text FROM pg_index i '
            'JOIN pg_class r ON r.oid=i.indrelid JOIN pg_namespace n ON n.oid=r.relnamespace '
            "WHERE n.nspname !~ '^(pg_|information_schema$)' ORDER BY 1")
        generations.append(cursor.fetchall())
        cursor.execute('SELECT rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,'
            'rolreplication,rolbypassrls,rolconfig FROM pg_roles ORDER BY oid')
        roles = cursor.fetchall()
        cursor.execute('SELECT roleid::bigint,member::bigint,grantor::bigint,admin_option,xmin::text '
            'FROM pg_auth_members ORDER BY roleid,member,grantor')
        return digest((identity, generations, roles, cursor.fetchall()))


@contextmanager
def verification_scope(run):
    from mta.presentation.native_publication import enabled
    if not enabled() or run.kind != 'DAILY_CHAIN':
        yield
        return
    active = _current.get()
    if active is not None:
        active['check'](run)
        yield
        return
    if connection.in_atomic_block:
        raise ValueError('Report verification admission must precede layer transactions')
    from mta.runtime.initialization_models import ProductionInitialization
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.ingestion_admission import readiness
    from mta.runtime.ingestion_models import InitializationCertification, MasterInputRevision, IngestionRevisionState
    from mta.runtime.opening_scope import opening_scope, sealed_identity
    from mta.mdm.production_families import certified_state_handle
    from mta.mdm.supplier_revisions import source_lock
    from mta.runtime.daily_feed import job_lock
    capture = MdmDailyInputCapture.objects.get(run=run)
    owner = ProductionInitialization.objects.select_related('source').get(source_id=capture.source_id)
    with job_lock(owner) as check_session, source_lock(owner.source_id), opening_scope():
        stamp = guard_stamp()
        admitted = readiness(owner.pk)
        certified_state_handle(owner, admitted)
        seal = sealed_identity(owner)
        certificate_fields = ('id', 'status', 'source_digest', 'content_digest',
            'configuration_digest', 'schema_digest', 'guard_digest', 'release_digest',
            'receipt_digest', 'authority_roles')
        certificate = InitializationCertification.objects.values_list(*certificate_fields).get(
            initialization=owner, status='CERTIFIED', receipt_digest=admitted.certification_digest)
        revision_fields = ('id', 'status', 'master_epoch', 'configuration_epoch', 'receipt_digest')
        revision = MasterInputRevision.objects.values_list(*revision_fields).get(
            pk=admitted.master_revision_id, initialization=owner, status='ACCEPTED')

        def check(node):
            check_session()  # Existing workflow check rejects reconnect/lost lock.
            owner.refresh_from_db()
            owner.source.refresh_from_db()
            if (sealed_identity(owner) != seal or guard_stamp() != stamp
                    or MdmDailyInputCapture.objects.get(run=node).source_id != owner.source_id
                    or InitializationCertification.objects.values_list(*certificate_fields).filter(
                        pk=certificate[0]).first() != certificate
                    or MasterInputRevision.objects.values_list(*revision_fields).filter(
                        pk=revision[0]).first() != revision
                    or IngestionRevisionState.objects.values_list('master_epoch',
                        'configuration_epoch').get(initialization=owner) != admitted.revisions.as_tuple()[:2]):
                raise ValueError('Report verification authority or initialization changed')

        check(run)
        token = _current.set(dict(check=check, audits={}))
        try:
            yield
            check(run)
        finally:
            _current.reset(token)


def report_operation(function):
    @wraps(function)
    def verified(run, *args, **kwargs):
        from mta.presentation.native_publication import enabled
        if not enabled():
            return function(run, *args, **kwargs)
        from mta.runtime.models import CalculationRun
        node = run if isinstance(run, CalculationRun) else CalculationRun.objects.get(pk=run)
        with verification_scope(node):
            return function(run, *args, **kwargs)
    return verified


def immutable_audit(run, name, audit):
    active = _current.get()
    if active is None:
        return audit()
    run.refresh_from_db()
    active['check'](run)
    key = (name, str(run.pk), run.status, run.input_digest, run.input_manifest_digest,
           run.output_digest, run.production_digest, digest(run.input_payload),
           digest(run.production_manifest))
    if key not in active['audits']:
        audit()
        active['check'](run)
        # Only a successful audit marker, never rows or a caller-supplied token.
        active['audits'][key] = True


def profile_reference(run, owner):
    """Authenticate a v3 same-opening alias without hydrating its policy graph.

    Legacy physical profiles keep their full comparison. Full native audits
    still read and hash the actual profile, independently in every operation.
    """
    from mta.runtime.captured_input import SCHEMAS, origin
    from mta.runtime import input_v3
    physical = origin(run) if run.input_payload.get('schema') in SCHEMAS else run
    manifest = physical.input_payload
    if manifest.get('schema') != input_v3.V3:
        return False
    reference = manifest.get('owner_references', {}).get('input/profile')
    if reference is None:
        return False
    expected = dict(kind='INITIALIZATION', path='input/profile', owner_id=str(owner.pk),
                    manifest_digest=owner.input_manifest_digest, content_digest=owner.input_digest)
    if (digest(manifest) != physical.input_manifest_digest
            or manifest.get('content_digest') != physical.input_digest
            or input_v3._owner_reference(reference, 'input/profile') != expected
            or input_v3._node_at(manifest, 'input/profile') != {'owner_reference': 'input/profile'}
            or digest(owner.input_payload) != owner.input_manifest_digest
            or owner.input_payload.get('content_digest') != owner.input_digest):
        raise ValueError('Native profile owner reference differs')
    from mta.runtime.input_storage import SCHEMA as V2
    physical_profile = (input_v3._physical(input_v3._node_at(owner.input_payload, 'input/profile'))
        if owner.input_payload.get('schema') == V2 else
        input_v3._initialization_component_is_physical(owner.input_payload, 'input/profile'))
    if not physical_profile:
        raise ValueError('Native profile must reference a physical one-hop opening')
    return True


def audit_native_rows(run, source):
    def audit():
        from mta.application.stage_observation import stage
        from mta.runtime.input_reader import read_input
        from mta.runtime.receipt_integrity import verify_root, audit_output
        from mta.runtime.initialization_models import ProductionInitialization
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        from mta.mdm.production_families import require_initialization
        capture = MdmDailyInputCapture.objects.select_related('source').get(run=run)
        owner = ProductionInitialization.objects.get(source=capture.source)
        with stage('native_certified_opening'):
            require_initialization(capture.source)
        with stage('native_profile_values'):
            if digest(read_input(run, components=('profile',))['profile']) != owner.configuration_digest:
                raise ValueError('Native initialization profile values changed')
        with stage('native_complete_input_audit'):
            verify_root(run)
            _audit_input(run)
        with stage('native_output_stream_audit'):
            audit_output(run)  # No returned graph/spool.
        from mta.presentation import daily_sources, daily_opening_sob, daily_transit, ancillary_live, daily_requests
        from mta.runtime.relational_state import iter_image
        special = {daily_opening_sob.PATH, daily_sources.COLOR_PATH, daily_requests.PATH,
                   *daily_transit.MODELS, *ancillary_live.PATHS.values()}
        for path, item in source.images.items():
            if path not in special:
                for _ in iter_image(run, item):
                    pass
    immutable_audit(run, ('complete-native-rows', source.images_digest,
                         source.recipe_digest), audit)
    # These readers include live requests/remarks. They are deliberately outside
    # the immutable audit marker, including when the immutable audit was reused.
    from mta.presentation import daily_sources, daily_opening_sob, daily_transit, ancillary_live, daily_requests
    special = {daily_opening_sob.PATH, daily_sources.COLOR_PATH, daily_requests.PATH,
               *daily_transit.MODELS, *ancillary_live.PATHS.values()}
    for path in source.images:
        if path in special:
            daily_sources.image_rows(run, path)


def _audit_input(run):
    """Audit new daily facts without reconstructing the certified opening.

    Only an exact INITIALIZATION one-hop subtree may consume this operation's
    private opening handle. Batch, daily/master and other run references keep
    their real row readers. Ordinary callers retain the exhaustive old audit.
    """
    from mta.runtime.receipt_integrity import audit_input
    active = _current.get()
    if active is None:
        return audit_input(run)
    active['check'](run)
    from mta.runtime.captured_input import SCHEMAS, origin
    from mta.runtime import input_v3, input_storage
    from mta.runtime.relational_state import iter_image
    from mta.runtime.opening_scope import current_certified_opening, require_certified_opening
    physical = origin(run) if run.input_payload.get('schema') in SCHEMAS else run
    manifest = physical.input_payload
    if manifest.get('schema') != input_v3.V3:
        return audit_input(run)
    # The actual v3 reader validates owner/database/source, content identity,
    # the whole reference/alias roster and node paths before component pruning.
    input_storage.read_input(physical, components=(), image_reader=iter_image)
    identity = input_v3._identity(physical, None, reading=True)
    for metadata in manifest['images'].values():
        for _ in iter_image(physical, metadata):
            pass
    for path, reference in manifest.get('batch_references', {}).items():
        for _ in input_v3._resolve_batch(physical, path, reference, identity, None,
                                        allow_owned_failed=True):
            pass
    for path, raw in manifest.get('owner_references', {}).items():
        reference = input_v3._owner_reference(raw, path)
        if reference['kind'] != 'INITIALIZATION':
            resolved = input_v3._resolve_owner(physical, path, reference, identity, None)
            if input_v3._collection(resolved):
                for _ in resolved:
                    pass
            continue
        target = input_v3._owner_target(physical, reference, None)
        target_identity = input_v3._identity(target, None, reading=True)
        handle = current_certified_opening(target)
        if handle is None:
            raise ValueError('Input opening reference has no certified operation handle')
        require_certified_opening(target, handle)
        value = target.input_payload
        if (reference['owner_id'] != str(target.pk)
                or target_identity['owner_kind'] != 'initialization'
                or any(target_identity[name] != identity[name] for name in
                       ('database_name', 'database_oid', 'source_digest'))
                or value.get('schema') not in (input_storage.SCHEMA, input_v3.V3)
                or digest(value) != reference['manifest_digest']
                or target.input_manifest_digest != reference['manifest_digest']
                or target.input_digest != reference['content_digest']
                or value.get('content_digest') != reference['content_digest']):
            raise ValueError('Certified input opening reference differs')
        physical_target = (input_v3._physical(input_v3._node_at(value, path))
            if value['schema'] == input_storage.SCHEMA else
            input_v3._initialization_component_is_physical(value, path))
        if not physical_target:
            raise ValueError('Certified input opening reference is not physical one-hop')
    for reference in manifest.get('derived_references', {}).values():
        for _ in input_v3._resolve_derived_master(physical, reference, identity, None):
            pass


def consumer_outputs(run, *, include_reports=True):
    """Private lazy graph for admission, after exhaustive guarded row audit.

    Consumer validators keep their complete inputs and hashes. Unlike the public
    read_outputs contract, discarded/unvisited large images need no disk spool.
    Every consumed image still uses its normal typed/digest-verifying iterator.
    """
    from mta.presentation.native_publication import identity
    if _current.get() is None:
        raise ValueError('Private consumer graph requires guarded verification scope')
    identity(run, verify_rows=True)
    if include_reports and run.production_manifest.get('version') == 3:
        from mta.presentation.operational_reports import generation, verify_rows
        derived = generation(run)
        immutable_audit(run, ('derived-report-rows', derived.digest),
                        lambda: verify_rows(run, derived.metadata))
    return _consumer_graph(run, include_reports=include_reports)


def _consumer_graph(run, *, include_reports=True):
    """Lossless reconstruction, separately differential-tested on persisted rows."""
    from mta.runtime.relational_state import iter_image, iter_export, load_image, load_export
    from mta.row_sequences import RecordRows
    manifest = run.production_manifest

    def image(item):
        return (RecordRows(item['count'], lambda: iter_image(run, item))
                if item['count'] > 10000 else load_image(run, item))

    def export(item):
        return (RecordRows(item['count'], lambda: iter_export(run, item))
                if item['count'] > 10000 else load_export(run, item))

    def resolve(node):
        if 'image' in node:
            return image(manifest['images'][node['image']])
        if 'metadata' in node:
            return node['metadata']
        if 'export' in node:
            return export(node['export'])
        if 'scratch_kind' in node:
            records = [(name, resolve(value)) for name, value in node['items']]
            return dict(records) if node['scratch_kind'] == 'dict' else [
                dict(table=name, rows=value) for name, value in records]
        return {name: resolve(value) for name, value in node['tables'].items()}

    closing = {name: resolve(value) for name, value in manifest['closing'].items()}
    reports = []
    for row in manifest['reports'] if include_reports else ():
        report = dict(stage=row['stage'], tables={name: resolve(value) for name, value in row['tables'].items()})
        if 'deferred' in row:
            report.update(deferred=row['deferred'], sources={name: resolve(value) for name, value in row['sources'].items()})
        reports.append(report)
    if manifest.get('version') == 3 and include_reports:
        from mta.presentation.operational_reports import generation
        derived = generation(run).metadata
        for path, item in derived['images'].items():
            closing['btr'][path.rsplit('/', 1)[1]] = image(item)
        for report in reports:
            if 'deferred' in report:
                report['tables'].update({name: export(item) for name, item in derived['exports'][report['stage']].items()})
                report.pop('deferred')
                report.pop('sources')
    result = dict(ClosingState=[closing], DBMFinal=[closing['dbm']], Reports=reports,
        BPRReports=[{name: resolve(value) for name, value in manifest['bpr'].items()}] if include_reports else [],
        Lineage=manifest['lineage'], PublicationContext=manifest['publication'])
    if 'btr' in closing:
        result['BTRFinal'] = [closing['btr']]
    return result

