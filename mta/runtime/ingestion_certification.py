"""Explicit full-audit certification; no daily execution or implicit upgrade.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from uuid import uuid4
from django.db import connection, transaction
from mta.serialization import digest
from mta.runtime.ingestion_context import CONTRACT, FAMILIES
from mta.runtime.ingestion_admission import receipt, security_digest
from mta.runtime.opening_scope import opening_operation


@opening_operation
def certify_current(initialization_id):
    """Certify a fully initialized *current-release* opening exactly once.

    Both original native capability and all old typed seals must pass unchanged.
    Cross-release upgrades deliberately cannot call this as a hash bypass: the
    future controlled upgrade must audit under its pinned original producer
    before creating reviewed compatibility metadata. M1 does not run that upgrade.
    """
    if connection.in_atomic_block:
        raise ValueError('Certification owns its complete audit transaction')
    from release.native_identity import require_current
    release = require_current()
    from release.native_schema import schema_digest
    from mta.runtime.ingestion_models import InitializationCertification, IngestionRevisionState, MasterInputRevision
    from mta.runtime.initialization_models import ProductionInitialization
    from mta.runtime.models import CalculationRun
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.mdm import production_families as families
    from mta.mdm.initialization import verify_current_masters
    from mta.mdm.master_owners import owner_batches
    from mta.mdm.daily_input import _capture_pair_exclusions
    from mta.runtime.ingestion_admission import registration
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        cursor.execute('SELECT current_user,pg_get_userbyid(datdba),datname,oid::bigint '
            'FROM pg_database WHERE datname=current_database()')
        user, owner_role, database, oid = cursor.fetchone()
        if user != owner_role:
            raise ValueError('Certification requires the dedicated database owner')
        # Locks cover approved writers; the complete scan is an explicit one-off
        # maintenance operation, never a serving/readiness cost.
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended('fresh.production.initialization',0))")
        cursor.execute('LOCK TABLE mta.fresh_mta_productioninitialization IN SHARE ROW EXCLUSIVE MODE')
        original, capability = registration(cursor)
        if capability['release_identity'] != release:
            raise ValueError('Current certification cannot relabel an older capability')
        roles = [original[k]['name'] for k in ('owner', 'issuer', 'consumer')]
        from mta.runtime.ingestion_ownership import tables
        from psycopg import sql
        # SHARE blocks direct SQL writers as well as cooperating application locks.
        for schema, table, kind in tables(cursor):
            if kind != 'authority':
                cursor.execute(sql.SQL('LOCK TABLE {}.{} IN SHARE MODE').format(sql.Identifier(schema), sql.Identifier(table)))
        guard = security_digest(cursor, roles)
        if (InitializationCertification.objects.exists() or IngestionRevisionState.objects.exists()
                or MasterInputRevision.objects.exists()):
            raise ValueError('Certification exists; replacement/reseal prohibited')
        owner = ProductionInitialization.objects.select_related('source').get(pk=initialization_id)
        if CalculationRun.objects.exists() or MdmDailyInputCapture.objects.exists():
            raise ValueError('Opening certification must precede the first daily capture')
        checked, frame = families._verified_initialization(owner.source)
        if checked.pk != owner.pk:
            raise ValueError('Initialization audit owner differs')
        verify_current_masters(owner.source, owner_batches(frame['opening']['state'], strict=True))
        if _capture_pair_exclusions(owner.source)['rows'] != frame['pair_exclusions']:
            raise ValueError('Full pair-exclusion audit differs')
        integration = families.require_binding(owner.source, read_only=True)
        body = dict(id=uuid4(), initialization_id=owner.pk, contract=CONTRACT,
            database_name=database, database_oid=oid, namespace=original['registration_id'],
            source_digest=owner.source.digest, content_digest=owner.input_digest,
            configuration_digest=owner.configuration_digest, schema_digest=schema_digest(cursor),
            guard_digest=guard, release_digest=release['manifest_sha256'],
            populations=dict(opening_manifest=owner.input_manifest_digest, integration=integration.digest),
            families=list(FAMILIES), authority_roles=roles)
        cert = InitializationCertification.objects.create(**body, receipt_digest=receipt(body))
        IngestionRevisionState.objects.create(initialization=owner)
        revision = dict(id=uuid4(), initialization_id=owner.pk, parent_id=None, run_id=None,
            master_epoch=0, configuration_epoch=0, partitions=dict(opening_master_root=digest(integration.receipt['families'])))
        MasterInputRevision.objects.create(**revision, receipt_digest=receipt(revision), status='ACCEPTED')
        return cert
