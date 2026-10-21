"""Append an exact compatible release; keep original data and producer seals.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from mta.runtime.opening_scope import opening_operation


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
